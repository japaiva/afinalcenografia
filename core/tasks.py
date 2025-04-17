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

from core.models import Feira, FeiraManualChunk, ParametroIndexacao
from core.utils.pinecone_utils import init_pinecone, get_index, upsert_vectors, delete_namespace, query_vectors
from core.services.qa_generator import process_all_chunks_for_feira

# Configuração de logger
logger = logging.getLogger(__name__)

def get_param_value(nome, categoria, default):
    """Obtém o valor de um parâmetro de indexação, com fallback para valor padrão"""
    try:
        param = ParametroIndexacao.objects.get(nome=nome, categoria=categoria)
        return param.valor_convertido()
    except ParametroIndexacao.DoesNotExist:
        return default

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

def pesquisar_manual_feira(texto_consulta, feira_id=None, num_resultados=3):
    """
    Realiza uma pesquisa semântica nos manuais de feira usando Pinecone
    """
    # Verificar se a feira existe e está processada
    if feira_id:
        try:
            feira = Feira.objects.get(id=feira_id)
            # Atualizado para usar chunks_processados
            if not feira.chunks_processados:
                return {"status": "error", "message": "O manual desta feira ainda não foi processado."}
            
            # Usar o método do modelo para obter o namespace correto
            namespace = feira.get_chunks_namespace()
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

# Versão simplificada da função pesquisar_qa_feira 
def pesquisar_qa_feira(texto_consulta, feira_id=None, num_resultados=3):
    """
    Versão simplificada da pesquisa em QA que não usa o módulo RAG Service.
    """
    # Importar aqui para evitar dependência circular
    from core.models import FeiraManualQA
    from django.db.models import Q
    
    logger.info(f"Usando versão simplificada de pesquisar_qa_feira para query: '{texto_consulta}', feira_id: {feira_id}")
    
    try:
        # Verificar se a feira existe
        if feira_id:
            try:
                feira = Feira.objects.get(id=feira_id)
            except Feira.DoesNotExist:
                return {"status": "error", "message": f"Feira ID {feira_id} não encontrada"}
        else:
            return {"status": "error", "message": "É necessário especificar uma feira para a consulta."}
        
        # Pesquisa simples baseada em texto (sem vetores)
        query_lower = texto_consulta.lower()
        
        qa_pairs = FeiraManualQA.objects.filter(feira=feira).filter(
            Q(question__icontains=texto_consulta) |
            Q(answer__icontains=texto_consulta) |
            Q(similar_questions__contains=texto_consulta)
        )[:num_resultados]
        
        resultados = []
        
        for qa in qa_pairs:
            # Calcular um score simples
            score = 0.7  # Base score
            if query_lower in qa.question.lower():
                score += 0.2
            if query_lower in qa.answer.lower():
                score += 0.1
            
            resultados.append({
                'id': f"qa_{qa.id}",
                'score': score,
                'question': qa.question,
                'answer': qa.answer,
                'context': qa.context,
                'similar_questions': qa.similar_questions,
                'feira_id': str(qa.feira.id),
                'feira_nome': qa.feira.nome,
                'qa_id': str(qa.id)
            })
        
        # Ordenar por score
        resultados.sort(key=lambda x: x['score'], reverse=True)
        
        return resultados
    
    except Exception as e:
        logger.error(f"Erro ao pesquisar QA: {str(e)}")
        return {"status": "error", "message": f"Erro ao processar consulta QA: {str(e)}"}

# Função para processar apenas QA sem reprocessar o manual
def processar_qa_feira(feira_id):
    """
    Processa apenas a geração de QA para uma feira, sem reprocessar o manual completo.
    Esta é uma versão simplificada que não executa automaticamente.
    """
    return {"status": "info", "message": "Função temporariamente desabilitada para evitar loops. Use o processo manual."}

# Versão para ser usada quando Celery estiver configurado
# @shared_task
def verificar_processamento_pendente():
    """
    Verifica e processa feiras com processamento pendente
    """
    # Buscar feiras com processamento pendente
    # Atualizado para usar chunks_processamento_status
    feiras_pendentes = Feira.objects.filter(
        chunks_processamento_status='pendente', 
        manual__isnull=False
    )
    
    for feira in feiras_pendentes:
        # Iniciar processamento (sem Celery por enquanto)
        processar_manual_feira(feira.id)
    
    return f"Verificação concluída. {feiras_pendentes.count()} feiras com processamento pendente encontradas."

def processar_manual_feira_core(feira_id):
    """
    Função principal de processamento de manual de feira
    Esta função contém a lógica principal, compartilhada por ambas versões
    """
    try:
        feira = Feira.objects.get(id=feira_id)
    except Feira.DoesNotExist:
        return {"status": "error", "message": f"Feira ID {feira_id} não encontrada"}
    
    # Atualizar status para processando (atualizado para novos campos)
    feira.chunks_processamento_status = 'processando'
    feira.chunks_progresso = 0
    feira.chunks_processados = False
    feira.save(update_fields=['chunks_processamento_status', 'chunks_progresso', 'chunks_processados'])
    
    # Usar método do modelo para obter o namespace
    namespace = feira.get_chunks_namespace()
    
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
                    feira.chunks_progresso = progresso
                    feira.save(update_fields=['chunks_progresso'])
                    
                    # Verificar periodicamente se o status ainda está correto
                    if page_num % 5 == 0:
                        feira.refresh_from_db()
                        if feira.chunks_processamento_status != 'processando':
                            feira.chunks_processamento_status = 'processando'
                            feira.save(update_fields=['chunks_processamento_status'])
                    
                    texto_pagina = page.extract_text()
                    if texto_pagina:
                        texto_pagina_processado = f"\n\n=== PÁGINA {page_num + 1} ===\n\n{texto_pagina}"
                        texto_completo += texto_pagina_processado
                        texto_por_pagina.append((page_num + 1, texto_pagina))
        
        except Exception as e:
            feira.chunks_processamento_status = 'erro'
            feira.mensagem_erro = f"Erro ao ler PDF: {str(e)}"
            feira.save(update_fields=['chunks_processamento_status', 'mensagem_erro'])
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
        feira.chunks_total = len(chunks)
        feira.chunks_progresso = 50  # 50% concluído após chunking
        feira.save(update_fields=['chunks_total', 'chunks_progresso'])
        
        # 3. Inicializar conexão com Pinecone
        try:
            # Primeiro, excluir namespace existente se necessário
            if feira.chunks_processados and namespace:
                delete_namespace(namespace)
            
            # Limpar chunks antigos
            with transaction.atomic():
                FeiraManualChunk.objects.filter(feira=feira).delete()
                
                # NÃO LIMPAR QAs EXISTENTES
                # Essa linha foi removida para evitar problemas com dados existentes
            
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
                        feira.chunks_progresso = progresso
                        feira.save(update_fields=['chunks_progresso'])
                        
                        # Verificar periodicamente se o status ainda está correto
                        if idx % 10 == 0:
                            feira.refresh_from_db()
                            if feira.chunks_processamento_status != 'processando':
                                feira.chunks_processamento_status = 'processando'
                                feira.save(update_fields=['chunks_processamento_status'])
                        
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
                            upsert_vectors(pinecone_vectors, namespace)
                            pinecone_vectors = []
                        
                    except Exception as e:
                        logger.error(f"Erro ao processar chunk {chunk['posicao']}: {str(e)}")
                        continue
            
            # 5. Atualizar status da feira
            feira.chunks_processamento_status = 'concluido'
            feira.chunks_processados = True
            feira.chunks_progresso = 100
            feira.save(update_fields=['chunks_processamento_status', 'chunks_processados', 'chunks_progresso'])
            
            logger.info(f"✓ Processamento do manual da feira {feira_id} concluído com sucesso. Status atualizado")
            
            return {
                "status": "success", 
                "message": f"Manual processado com sucesso. {total_chunks} chunks gerados.",
                "namespace": namespace
            }
            
        except Exception as e:
            feira.chunks_processamento_status = 'erro'
            feira.mensagem_erro = f"Erro ao processar embeddings: {str(e)}"
            feira.save(update_fields=['chunks_processamento_status', 'mensagem_erro'])
            return {"status": "error", "message": str(e)}
            
    except Exception as e:
        feira.chunks_processamento_status = 'erro'
        feira.mensagem_erro = str(e)
        feira.save(update_fields=['chunks_processamento_status', 'mensagem_erro'])
        return {"status": "error", "message": str(e)}