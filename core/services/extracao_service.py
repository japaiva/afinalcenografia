# core/services/extracao_service.py

import logging
from django.db import models
from core.models import Feira, FeiraManualQA

from core.services.rag.embedding_service import EmbeddingService
from core.utils.pinecone_utils import query_vectors, get_index

logger = logging.getLogger(__name__)

class ExtracaoService:
    """
    Serviço para extrair informações dos Q&As existentes e preencher campos do cadastro.
    """
    
    def extrair_dados_feira(self, feira_id):
        """
        Extrai dados para o cadastro a partir dos Q&As existentes.
        Usa apenas os Q&As associados a campos específicos.
        """
        try:
            feira = Feira.objects.get(pk=feira_id)
            
            # Verificar se existem Q&As
            if not FeiraManualQA.objects.filter(feira_id=feira_id).exists():
                return {
                    'status': 'error',
                    'message': 'Não existem perguntas e respostas geradas para esta feira.'
                }
            
            # Obter todos os Q&As associados a campos
            field_qas = FeiraManualQA.objects.filter(
                feira_id=feira_id,
                campo_relacionado__isnull=False
            ).exclude(campo_relacionado='').order_by('-confianca_extracao')
            
            if not field_qas.exists():
                return {
                    'status': 'error',
                    'message': 'Não foram encontradas perguntas associadas a campos do cadastro.'
                }
            
            # Agrupar por campo e obter o melhor para cada campo
            resultados = {}
            campos_processados = set()
            
            for qa in field_qas:
                campo = qa.campo_relacionado
                
                if campo not in campos_processados:
                    campos_processados.add(campo)
                    
                    resultados[campo] = {
                        'valor': qa.answer,
                        'confianca': qa.confianca_extracao,
                        'pergunta': qa.question,
                        'id': qa.id
                    }
            
            if not resultados:
                return {
                    'status': 'empty',
                    'message': 'Não foi possível extrair dados relevantes.'
                }
            
            return {
                'status': 'success',
                'data': resultados
            }
            
        except Feira.DoesNotExist:
            return {
                'status': 'error',
                'message': 'Feira não encontrada.'
            }
        except Exception as e:
            logger.error(f"Erro ao extrair dados: {str(e)}")
            return {
                'status': 'error',
                'message': f'Erro ao processar extração: {str(e)}'
            }
    
    def aplicar_dados(self, feira_id, dados_selecionados):
        """
        Aplica os dados extraídos ao cadastro da feira.
        """
        try:
            feira = Feira.objects.get(pk=feira_id)
            campos_atualizados = []
            
            for nome_campo, valor in dados_selecionados.items():
                if hasattr(feira, nome_campo):
                    setattr(feira, nome_campo, valor)
                    campos_atualizados.append(nome_campo)
            
            if campos_atualizados:
                feira.save(update_fields=campos_atualizados)
                
                return {
                    'status': 'success',
                    'message': f'Dados aplicados com sucesso: {", ".join(campos_atualizados)}',
                    'campos_atualizados': campos_atualizados
                }
            else:
                return {
                    'status': 'warning',
                    'message': 'Nenhum campo foi atualizado.'
                }
                
        except Feira.DoesNotExist:
            return {
                'status': 'error',
                'message': 'Feira não encontrada.'
            }
        except Exception as e:
            logger.error(f"Erro ao aplicar dados: {str(e)}")
            return {
                'status': 'error',
                'message': f'Erro ao aplicar dados: {str(e)}'
            }
        
def eh_pergunta_relacionada_a_feira(pergunta: str, feira_id: int, threshold: float = 0.65) -> bool:
    logger.info(f"[feira_utils] Iniciando verificação de pergunta relacionada à feira. ID: {feira_id}, Pergunta: '{pergunta}'")
    
    # Verificação explícita para menções à feira
    palavras_chave_feira = ['feira', 'evento', 'exposição', 'manual', 'regras', 'pavilhão', 'montagem', 
                            'desmontagem', 'stand', 'estande', 'altura', 'dimensão', 'limite', 'promotora']
    
    # Se a pergunta menciona explicitamente a feira, retorna verdadeiro imediatamente
    if any(palavra in pergunta.lower() for palavra in palavras_chave_feira):
        palavra_encontrada = next(palavra for palavra in palavras_chave_feira if palavra in pergunta.lower())
        logger.info(f"[feira_utils] Palavra-chave encontrada: '{palavra_encontrada}' na pergunta: '{pergunta}'")
        return True
    
    # Caso contrário, continua com a verificação baseada em embedding
    try:
        logger.info(f"[feira_utils] Nenhuma palavra-chave encontrada. Verificando via embedding para: '{pergunta}'")
        embedding_service = EmbeddingService()
        query_embedding = embedding_service.gerar_embedding_consulta(pergunta)

        if not query_embedding:
            logger.warning(f"[feira_utils] Não foi possível gerar embedding para: '{pergunta}'")
            return False

        logger.info(f"[feira_utils] Embedding gerado com sucesso. Dimensão: {len(query_embedding)}")
        
        index = get_index()
        if not index:
            logger.warning("[feira_utils] Não foi possível obter o índice Pinecone")
            return False

        logger.info(f"[feira_utils] Índice Pinecone obtido. Consultando namespace 'feira_{feira_id}'")
        
        namespace = f"feira_{feira_id}"
        top_k = 3
        filter_obj = {"feira_id": {"$eq": str(feira_id)}}

        logger.debug(f"[feira_utils] Parâmetros da consulta: namespace={namespace}, top_k={top_k}, filter={filter_obj}")
        resultados = query_vectors(query_embedding, namespace, top_k, filter_obj)

        if not resultados:
            logger.info(f"[feira_utils] Nenhum resultado encontrado para a consulta: '{pergunta}'")
            return False

        logger.info(f"[feira_utils] {len(resultados)} resultados encontrados")
        
        scores = [result.get('score', 0) for result in resultados if 'score' in result]
        if not scores:
            logger.warning("[feira_utils] Nenhum score encontrado nos resultados")
            return False
            
        maior_score = max(scores)
        is_related = maior_score >= threshold
        
        logger.info(f"[feira_utils] Pergunta '{pergunta}' - maior score: {maior_score:.4f}, threshold: {threshold}, relacionada: {is_related}")
        
        if is_related:
            logger.info(f"[feira_utils] Pergunta considerada relacionada à feira (score: {maior_score:.4f} >= threshold: {threshold})")
        else:
            logger.info(f"[feira_utils] Pergunta NÃO relacionada à feira (score: {maior_score:.4f} < threshold: {threshold})")
            
        return is_related

    except Exception as e:
        import traceback
        logger.error(f"[feira_utils] Erro na verificação de pergunta sobre a feira: {str(e)}")
        logger.error(f"[feira_utils] Traceback: {traceback.format_exc()}")
        return False