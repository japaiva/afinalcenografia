# core/tasks.py

from django.conf import settings
import os
import re
import io
import numpy as np
from PyPDF2 import PdfReader
from openai import OpenAI
import tiktoken
import time
import uuid
from django.db import transaction
import logging

from core.models import Feira, FeiraManualChunk, ParametroIndexacao, FeiraManualQA 
from core.pinecone_utils import init_pinecone, get_index, upsert_vectors, delete_namespace, query_vectors
from core.services.qa_generator import process_all_chunks_for_feira, get_qa_param

# Configuração de logger
logger = logging.getLogger(__name__)

def get_param_value(nome, categoria, default):
    """Obtém o valor de um parâmetro de indexação, com fallback para valor padrão"""
    try:
        param = ParametroIndexacao.objects.get(nome=nome, categoria=categoria)
        return param.valor_convertido()
    except ParametroIndexacao.DoesNotExist:
        return default

def processar_manual_feira_core(feira_id):
    """
    Função principal de processamento de manual de feira
    Esta função contém a lógica principal, compartilhada por ambas versões
    """
    try:
        feira = Feira.objects.get(id=feira_id)
    except Feira.DoesNotExist:
        return {"status": "error", "message": f"Feira ID {feira_id} não encontrada"}
    
    # Atualizar status para processando
    feira.processamento_status = 'processando'
    feira.progresso_processamento = 0
    feira.manual_processado = False
    feira.save(update_fields=['processamento_status', 'progresso_processamento', 'manual_processado'])
    
    # Criar namespace único para a feira no Pinecone
    if not feira.pinecone_namespace:
        feira.pinecone_namespace = f"feira_{feira_id}_{uuid.uuid4().hex[:8]}"
        feira.save(update_fields=['pinecone_namespace'])
    
    try:
        # 1. Ler o arquivo PDF
        try:
            # Abrir o arquivo usando o método .open() do storage
            with feira.manual.open('rb') as file:
                pdf_reader = PdfReader(file)
                total_paginas = len(pdf_reader.pages)
                feira.total_paginas = total_paginas
                feira.save(update_fields=['total_paginas'])
                
                texto_completo = ""
                texto_por_pagina = []
                
                # Extrair texto de cada página
                for page_num, page in enumerate(pdf_reader.pages):
                    # Atualizar progresso - 50% do processo é leitura do PDF
                    progresso = int((page_num / total_paginas) * 50)
                    feira.progresso_processamento = progresso
                    feira.save(update_fields=['progresso_processamento'])
                    
                    texto_pagina = page.extract_text()
                    if texto_pagina:
                        texto_pagina_processado = f"\n\n=== PÁGINA {page_num + 1} ===\n\n{texto_pagina}"
                        texto_completo += texto_pagina_processado
                        texto_por_pagina.append((page_num + 1, texto_pagina))
        
        except Exception as e:
            feira.processamento_status = 'erro'
            feira.mensagem_erro = f"Erro ao ler PDF: {str(e)}"
            feira.save(update_fields=['processamento_status', 'mensagem_erro'])
            return {"status": "error", "message": f"Erro ao ler PDF: {str(e)}"}
        
        # 2. Dividir o texto em chunks
        chunks = []
        
        # Obter parâmetros de chunking
        tamanho_chunk = get_param_value('CHUNK_SIZE', 'chunk', 1000)
        overlap_tokens = get_param_value('CHUNK_OVERLAP', 'chunk', 100)
        
        # Determinar a estratégia de chunking
        estrategia = get_param_value('CHUNKING_STRATEGY', 'chunk', 'page')
        
        if estrategia == 'page':
            # Processa página por página
            for page_num, texto_pagina in texto_por_pagina:
                # Limpar texto da página
                texto_limpo = re.sub(r'\s+', ' ', texto_pagina).strip()
                
                # Estimar número de tokens
                encoding = tiktoken.get_encoding("cl100k_base")  # Para OpenAI
                tokens = encoding.encode(texto_limpo)
                
                # Se a página for muito grande, dividir em chunks
                if len(tokens) > tamanho_chunk:
                    # Dividir em chunks
                    for i in range(0, len(tokens), tamanho_chunk - overlap_tokens):
                        if i > 0:
                            # Incluir overlap
                            start_idx = i - overlap_tokens
                        else:
                            start_idx = 0
                        
                        end_idx = min(i + tamanho_chunk, len(tokens))
                        chunk_tokens = tokens[start_idx:end_idx]
                        chunk_texto = encoding.decode(chunk_tokens)
                        
                        chunks.append({
                            'texto': chunk_texto,
                            'posicao': len(chunks),
                            'pagina': page_num
                        })
                else:
                    # A página cabe em um único chunk
                    chunks.append({
                        'texto': texto_limpo,
                        'posicao': len(chunks),
                        'pagina': page_num
                    })
        else:
            # Estratégia padrão: dividir o texto completo
            texto_limpo = re.sub(r'\s+', ' ', texto_completo).strip()
            palavras = texto_limpo.split()
            
            for i in range(0, len(palavras), tamanho_chunk - overlap_tokens):
                if i > 0:
                    # Incluir overlap
                    start_idx = i - overlap_tokens
                else:
                    start_idx = 0
                
                chunk = ' '.join(palavras[start_idx:i+tamanho_chunk])
                # Tentar identificar a página
                pagina_match = re.search(r'=== PÁGINA (\d+) ===', chunk)
                pagina = int(pagina_match.group(1)) if pagina_match else None
                
                chunks.append({
                    'texto': chunk,
                    'posicao': i // (tamanho_chunk - overlap_tokens),
                    'pagina': pagina
                })
        
        # Atualizar total de chunks
        feira.total_chunks = len(chunks)
        feira.progresso_processamento = 50  # 50% concluído após chunking
        feira.save(update_fields=['total_chunks', 'progresso_processamento'])
        
        # 3. Inicializar conexão com Pinecone
        try:
            # Primeiro, excluir namespace existente se necessário
            if feira.manual_processado and feira.pinecone_namespace:
                delete_namespace(feira.pinecone_namespace)
            
            # Limpar chunks antigos
            with transaction.atomic():
                FeiraManualChunk.objects.filter(feira=feira).delete()
                
                # Limpar QAs antigos quando reprocessar o manual
                FeiraManualQA.objects.filter(feira=feira).delete()
            
            # Inicializar Pinecone
            client = OpenAI(api_key=settings.OPENAI_API_KEY)
            embedding_model = get_param_value('EMBEDDING_MODEL', 'embedding', "text-embedding-ada-002")
            
            # 4. Gerar embeddings para cada chunk e armazenar no Pinecone
            total_chunks = len(chunks)
            pinecone_vectors = []
            
            # Criar chunks no banco de dados e gerar embeddings
            with transaction.atomic():
                for idx, chunk in enumerate(chunks):
                    try:
                        # Atualizar progresso - 50% a 95%
                        progresso = 50 + int((idx / total_chunks) * 45)
                        feira.progresso_processamento = progresso
                        feira.save(update_fields=['progresso_processamento'])
                        
                        # Gerar embedding
                        response = client.embeddings.create(
                            input=chunk['texto'],
                            model=embedding_model
                        )
                        
                        embedding = response.data[0].embedding
                        
                        # Criar ID único para o Pinecone
                        pinecone_id = f"feira_{feira_id}_chunk_{chunk['posicao']}"
                        
                        # Criar no banco de dados
                        novo_chunk = FeiraManualChunk.objects.create(
                            feira=feira,
                            texto=chunk['texto'],
                            posicao=chunk['posicao'],
                            pagina=chunk['pagina'],
                            pinecone_id=pinecone_id
                        )
                        
                        # Adicionar à lista para inserção em lote no Pinecone
                        metadata = {
                            'texto': chunk['texto'][:1000],  # Limitando o tamanho dos metadados
                            'pagina': str(chunk['pagina']),
                            'posicao': str(chunk['posicao']),
                            'feira_id': str(feira_id),
                            'feira_nome': feira.nome
                        }
                        
                        pinecone_vectors.append((pinecone_id, embedding, metadata))
                        
                        # A cada 50 chunks, fazer upsert no Pinecone para evitar timeouts
                        if len(pinecone_vectors) >= 50 or idx == total_chunks - 1:
                            upsert_vectors(pinecone_vectors, feira.pinecone_namespace)
                            pinecone_vectors = []
                        
                    except Exception as e:
                        logger.error(f"Erro ao processar chunk {chunk['posicao']}: {str(e)}")
                        continue
            
            # 5. Atualizar status da feira
            feira.processamento_status = 'concluido'
            feira.manual_processado = True
            feira.progresso_processamento = 100
            feira.save(update_fields=['processamento_status', 'manual_processado', 'progresso_processamento'])
            
            # 6. Iniciar geração de QA se configurado
            gerar_qa_automaticamente = get_qa_param('QA_ENABLED', True)
            
            if gerar_qa_automaticamente:
                try:
                    logger.info(f"Iniciando geração de QA para feira ID {feira_id}")
                    
                    # Idealmente, em produção, isso seria executado em uma tarefa Celery
                    # process_all_chunks_for_feira.delay(feira_id)
                    
                    # Versão síncrona (para desenvolvimento)
                    qa_result = process_all_chunks_for_feira(feira_id)
                    logger.info(f"Geração de QA para feira {feira_id} concluída: {qa_result}")
                    
                except Exception as e:
                    logger.error(f"Erro ao gerar QA para feira {feira_id}: {str(e)}")
                    # Não falhar o processo principal se a geração de QA falhar
                    
            return {
                "status": "success", 
                "message": f"Manual processado com sucesso. {total_chunks} chunks gerados.",
                "namespace": feira.pinecone_namespace
            }
            
        except Exception as e:
            feira.processamento_status = 'erro'
            feira.mensagem_erro = f"Erro ao processar embeddings: {str(e)}"
            feira.save(update_fields=['processamento_status', 'mensagem_erro'])
            return {"status": "error", "message": str(e)}
            
    except Exception as e:
        feira.processamento_status = 'erro'
        feira.mensagem_erro = str(e)
        feira.save(update_fields=['processamento_status', 'mensagem_erro'])
        return {"status": "error", "message": str(e)}    

# Versão sem Celery (para uso síncrono)
def processar_manual_feira(feira_id):
    """
    Versão síncrona da função de processamento do manual de feira
    """
    return processar_manual_feira_core(feira_id)

# Manter esta função como referência para uso futuro com Celery
# Quando for implementar Celery, remova o comentário do decorator abaixo
# @shared_task
def processar_manual_feira_async(feira_id):
    """
    Versão assíncrona da função de processamento do manual de feira (para uso com Celery)
    """
    return processar_manual_feira_core(feira_id)

# Função auxiliar para compatibilidade com o código anterior
def processar_manual_feira_sync(feira_id):
    """
    Alias para processar_manual_feira (mantido para compatibilidade)
    """
    return processar_manual_feira(feira_id)

# [NOVO] Função para processar apenas QA sem reprocessar o manual
def processar_qa_feira(feira_id):
    """
    Processa apenas a geração de QA para uma feira, sem reprocessar o manual completo
    """
    try:
        feira = Feira.objects.get(id=feira_id)
        
        # Verificar se o manual já foi processado
        if not feira.manual_processado:
            return {
                "status": "error",
                "message": "O manual desta feira ainda não foi processado. É necessário processar o manual antes de gerar QA."
            }
        
        # Limpar QAs existentes
        FeiraManualQA.objects.filter(feira=feira).delete()
        
        # Iniciar processamento de QA
        result = process_all_chunks_for_feira(feira_id)
        
        return result
        
    except Feira.DoesNotExist:
        return {"status": "error", "message": f"Feira ID {feira_id} não encontrada"}
    except Exception as e:
        logger.error(f"Erro ao processar QA para feira {feira_id}: {str(e)}")
        return {"status": "error", "message": str(e)}

def pesquisar_manual_feira(texto_consulta, feira_id=None, num_resultados=3):
    """
    Realiza uma pesquisa semântica nos manuais de feira usando Pinecone
    """
    # Verificar se a feira existe e está processada
    if feira_id:
        try:
            feira = Feira.objects.get(id=feira_id)
            if not feira.manual_processado:
                return {"status": "error", "message": "O manual desta feira ainda não foi processado."}
            namespace = feira.pinecone_namespace
        except Feira.DoesNotExist:
            return {"status": "error", "message": f"Feira ID {feira_id} não encontrada"}
    else:
        # Se não for especificada uma feira, não podemos continuar
        return {"status": "error", "message": "É necessário especificar uma feira para a consulta."}
    
    try:
        # Gerar embedding para a consulta
        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        embedding_model = get_param_value('EMBEDDING_MODEL', 'embedding', "text-embedding-ada-002")
        
        response = client.embeddings.create(
            input=texto_consulta,
            model=embedding_model
        )
        
        query_embedding = response.data[0].embedding
        
        # Consultar no Pinecone
        resultados_pinecone = query_vectors(
            query_embedding, 
            namespace,
            top_k=num_resultados
        )
        
        # Formatar resultados
        resultados = []
        for result in resultados_pinecone:
            # Buscar o chunk no banco de dados
            try:
                chunk = FeiraManualChunk.objects.get(pinecone_id=result['id'])
                
                resultados.append({
                    'chunk': {
                        'id': chunk.id,
                        'posicao': chunk.posicao,
                        'texto': chunk.texto,
                        'pagina': chunk.pagina
                    },
                    'similaridade': result['score']
                })
            except FeiraManualChunk.DoesNotExist:
                # Se o chunk não existir no banco, usar os metadados do Pinecone
                metadata = result['metadata']
                resultados.append({
                    'chunk': {
                        'id': result['id'],
                        'posicao': int(metadata.get('posicao', 0)),
                        'texto': metadata.get('texto', 'Texto não disponível'),
                        'pagina': int(metadata.get('pagina', 0)) if metadata.get('pagina') else None
                    },
                    'similaridade': result['score']
                })
        
        return resultados
    
    except Exception as e:
        logger.error(f"Erro ao pesquisar: {str(e)}")
        return {"status": "error", "message": f"Erro ao processar consulta: {str(e)}"}

# [NOVO] Função para pesquisar nas perguntas e respostas geradas
def pesquisar_qa_feira(texto_consulta, feira_id=None, num_resultados=3):
    """
    Realiza uma pesquisa nas perguntas e respostas geradas para uma feira
    """
    from core.services.rag_integration import RAGService
    
    try:
        # Verificar se a feira existe
        if feira_id:
            try:
                feira = Feira.objects.get(id=feira_id)
                
                # Verificar se existem QA para esta feira
                qa_count = FeiraManualQA.objects.filter(feira=feira).count()
                if qa_count == 0:
                    return {
                        "status": "error", 
                        "message": "Não há perguntas e respostas geradas para esta feira."
                    }
                
            except Feira.DoesNotExist:
                return {"status": "error", "message": f"Feira ID {feira_id} não encontrada"}
        else:
            # Se não for especificada uma feira, não podemos continuar
            return {"status": "error", "message": "É necessário especificar uma feira para a consulta."}
        
        # Inicializar serviço RAG
        rag_service = RAGService()
        
        # Pesquisar QA
        resultados = rag_service.pesquisar_qa(texto_consulta, feira_id, num_resultados)
        
        return resultados
        
    except Exception as e:
        logger.error(f"Erro ao pesquisar QA: {str(e)}")
        return {"status": "error", "message": f"Erro ao processar consulta: {str(e)}"}

# Versão para ser usada quando Celery estiver configurado
# @shared_task
def verificar_processamento_pendente():
    """
    Verifica e processa feiras com processamento pendente
    """
    # Buscar feiras com processamento pendente
    feiras_pendentes = Feira.objects.filter(
        processamento_status='pendente', 
        manual__isnull=False
    )
    
    for feira in feiras_pendentes:
        # Iniciar processamento (sem Celery por enquanto)
        processar_manual_feira(feira.id)
    
    return f"Verificação concluída. {feiras_pendentes.count()} feiras com processamento pendente encontradas."