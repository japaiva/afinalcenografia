# core/services/rag/qa_service.py
import logging
import time
from typing import List, Dict, Any, Optional

from django.conf import settings
from core.models import Feira, FeiraManualQA
from core.utils.pinecone_utils import upsert_vectors, get_namespace_stats
from core.services.rag.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)

class QAService:
    """
    Serviço responsável por gerenciar pares Q&A e seus embeddings para o sistema RAG.
    """
    
    def __init__(self, embedding_service=None):
        """
        Inicializa o serviço de Q&A.
        
        Args:
            embedding_service: Instância opcional do EmbeddingService. Se não fornecido, será criado.
        """
        logger.info("Inicializando QAService")
        
        # Usar embedding_service fornecido ou criar um novo
        if embedding_service:
            self.embedding_service = embedding_service
            logger.info("✓ Usando embedding_service fornecido")
        else:
            from core.services.rag.embedding_service import EmbeddingService
            self.embedding_service = EmbeddingService()
            logger.info("✓ Criado novo embedding_service")
    
    def atualizar_embeddings_feira(self, feira_id: int) -> Dict[str, Any]:
        """
        Atualiza os embeddings dos QA de uma feira.
        
        Args:
            feira_id: ID da feira.
            
        Returns:
            Dicionário com os resultados da atualização.
        """
        logger.info(f"Iniciando atualização de embeddings para feira ID {feira_id}")
        
        try:
            # Verificar se a feira existe
            try:
                feira = Feira.objects.get(pk=feira_id)
                logger.info(f"✓ Feira encontrada: {feira.nome} (ID: {feira_id})")
            except Feira.DoesNotExist:
                logger.error(f"Feira com ID {feira_id} não encontrada.")
                return {
                    'status': 'error',
                    'message': f'Feira com ID {feira_id} não encontrada'
                }
            
            # Obter o namespace para esta feira
            namespace = f"feira_{feira_id}"
            
            # Verificar estatísticas do namespace (opcional)
            try:
                stats = get_namespace_stats(namespace)
                if stats and stats['exists']:
                    logger.info(f"✓ Namespace '{namespace}' já existe com {stats['vector_count']} vetores")
                else:
                    logger.info(f"✓ Namespace '{namespace}' será criado durante o processo de upsert")
            except Exception as e:
                logger.warning(f"Não foi possível verificar estatísticas do namespace: {str(e)}")
            
            # Obter QAs da feira - SEM LIMITAÇÃO
            qa_pairs = FeiraManualQA.objects.filter(feira=feira)
            total = qa_pairs.count()
            
            logger.info(f"✓ Encontrados {total} pares QA para a feira {feira_id}")
            
            if not qa_pairs.exists():
                logger.warning(f"Nenhum par QA encontrado para a feira {feira_id}.")
                return {
                    'status': 'error',
                    'message': 'Nenhum par QA encontrado para esta feira'
                }
            
            # Processamento com geração de embeddings real
            logger.info(f"Iniciando processamento de embeddings para {total} pares QA")
            successes = 0
            errors = 0
            vectors = []
            
            for qa in qa_pairs:
                logger.info(f"Processando QA {qa.id} ({successes+errors+1}/{total})")
                
                try:
                    # Gerar embedding usando o serviço de embeddings
                    embedding = self.embedding_service.gerar_embeddings_qa(qa)
                    
                    if embedding:
                        logger.info(f"✓ Embedding gerado para QA {qa.id}")
                        
                        # Preparar metadados
                        metadata = {
                            'q': qa.question,
                            'a': qa.answer,
                            't': qa.context,
                            'sq': qa.similar_questions,
                            'feira_id': str(qa.feira.id),
                            'feira_nome': qa.feira.nome,
                            'qa_id': str(qa.id)
                        }
                        
                        # Adicionar à lista de vetores para upsert em lote
                        vector_id = f"qa_{qa.id}"
                        vectors.append((vector_id, embedding, metadata))
                        
                        # Atualizar embedding_id no QA
                        qa.embedding_id = vector_id
                        qa.save(update_fields=['embedding_id'])
                        
                        successes += 1
                        logger.info(f"✓ QA {qa.id} processado com sucesso")
                    else:
                        logger.error(f"Falha ao gerar embedding para QA {qa.id}")
                        errors += 1
                    
                except Exception as e:
                    logger.error(f"Erro ao processar QA {qa.id}: {str(e)}")
                    errors += 1
            
            # Realizar upsert em lote
            if vectors:
                logger.info(f"Enviando {len(vectors)} vetores para o banco vetorial (namespace: {namespace})")
                upsert_result = upsert_vectors(vectors, namespace)
                
                if upsert_result:
                    logger.info(f"✓ Vetores inseridos com sucesso no namespace '{namespace}'")
                else:
                    logger.error(f"Falha ao inserir vetores no namespace '{namespace}'")
            
            # Verificar estatísticas após inserção (opcional)
            try:
                stats = get_namespace_stats(namespace)
                if stats and stats['exists']:
                    logger.info(f"✓ Namespace '{namespace}' agora contém {stats['vector_count']} vetores")
            except Exception as e:
                logger.warning(f"Não foi possível verificar estatísticas do namespace após inserção: {str(e)}")
            
            logger.info(f"✓ Atualização de embeddings concluída: {successes} sucessos, {errors} erros de {total} QAs")
            
            return {
                'status': 'success',
                'message': f'Atualização concluída: {successes} de {total} QA processados com sucesso',
                'total': total,
                'successful': successes,
                'errors': errors
            }
            
        except Exception as e:
            logger.error(f"Erro não tratado ao atualizar embeddings da feira {feira_id}: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }