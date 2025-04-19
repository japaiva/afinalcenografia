# services/rag/qa_service.py

import logging
import time
from typing import List, Dict, Any, Optional

from django.conf import settings
from core.models import Feira, FeiraManualQA
from core.utils.pinecone_utils import upsert_vectors, get_namespace_stats, delete_namespace
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
        logger.debug("Inicializando QAService")
        
        # Usar embedding_service fornecido ou criar um novo
        if embedding_service:
            self.embedding_service = embedding_service
            logger.debug("Usando embedding_service fornecido")
        else:
            from core.services.rag.embedding_service import EmbeddingService
            self.embedding_service = EmbeddingService()
            logger.debug("Criado novo embedding_service")
    
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
                logger.debug(f"Feira encontrada: {feira.nome}")
            except Feira.DoesNotExist:
                logger.error(f"Feira com ID {feira_id} não encontrada.")
                return {
                    'status': 'error',
                    'message': f'Feira com ID {feira_id} não encontrada'
                }
            
            # Obter o namespace para esta feira
            namespace = feira.get_qa_namespace()
            
            # Limpar namespace antes de inserir novos vetores
            try:
                delete_namespace(namespace)
                logger.debug(f"Namespace '{namespace}' limpo")
            except Exception as e:
                logger.warning(f"Aviso ao limpar namespace: {str(e)}")
            
            # Obter QAs da feira
            qa_pairs = FeiraManualQA.objects.filter(feira=feira)
            total = qa_pairs.count()
            
            logger.info(f"Processando {total} pares QA para feira {feira.nome}")
            
            if not qa_pairs.exists():
                logger.warning(f"Nenhum par QA encontrado para a feira {feira_id}")
                return {
                    'status': 'error',
                    'message': 'Nenhum par QA encontrado para esta feira'
                }
            
            # Processamento de embeddings
            successes = 0
            errors = 0
            vectors = []
            
            # Processamento de 10% a cada log para reduzir volume
            progress_step = max(1, total // 10)
            
            for i, qa in enumerate(qa_pairs):
                # Log apenas a cada X% do progresso
                if i % progress_step == 0:
                    logger.info(f"Progresso: {i}/{total} ({(i/total)*100:.1f}%)")
                
                try:
                    embedding = self.embedding_service.gerar_embeddings_qa(qa)
                    
                    if embedding:
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
                        
                        vector_id = f"qa_{qa.id}"
                        vectors.append((vector_id, embedding, metadata))
                        qa.embedding_id = vector_id
                        successes += 1
                    else:
                        logger.error(f"Falha ao gerar embedding para QA {qa.id}")
                        errors += 1
                    
                except Exception as e:
                    logger.error(f"Erro ao processar QA {qa.id}: {str(e)}")
                    errors += 1
            
            # Realizar upsert em lote
            if vectors:
                logger.info(f"Enviando {len(vectors)} vetores para o banco de dados vetorial")
                upsert_result = upsert_vectors(vectors, namespace)
                
                if upsert_result:
                    # Atualizar embedding_ids em massa
                    qa_updates = []
                    for qa in qa_pairs:
                        if hasattr(qa, 'embedding_id') and qa.embedding_id:
                            qa_updates.append(qa)
                    
                    if qa_updates:
                        logger.info(f"Atualizando {len(qa_updates)} registros no banco de dados")
                        from django.db import transaction
                        with transaction.atomic():
                            FeiraManualQA.objects.bulk_update(qa_updates, ['embedding_id'])
                else:
                    logger.error(f"Falha ao inserir vetores no namespace '{namespace}'")
            
            # Log de sumário
            logger.info(f"Atualização concluída: {successes} sucessos, {errors} erros de {total} QAs")
            
            return {
                'status': 'success',
                'message': f'Atualização concluída: {successes} de {total} QA processados com sucesso',
                'total': total,
                'successful': successes,
                'errors': errors
            }
            
        except Exception as e:
            logger.error(f"Erro ao atualizar embeddings da feira {feira_id}: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }