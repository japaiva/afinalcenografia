# core/services/rag/vector_db_service.py
import logging
from typing import List, Dict, Any, Optional, Tuple

from django.conf import settings
from core.models import ParametroIndexacao
from core.utils.pinecone_utils import init_pinecone, get_index, upsert_vectors, delete_namespace, query_vectors, get_namespace_stats

logger = logging.getLogger(__name__)

class VectorDBService:
    """
    Serviço responsável pela interação com o banco de dados vetorial (Pinecone).
    Abstrai as operações comuns de armazenamento e recuperação de vetores.
    """
    
    def __init__(self):
        """
        Inicializa o serviço do banco de dados vetorial.
        """
        logger.info("Inicializando VectorDBService")
        
        # Obter parâmetros de configuração do banco vetorial
        self.vector_db_provider = self._get_param_value('VECTOR_DB_PROVIDER', 'connection', 'pinecone')
        self.pinecone_index = self._get_param_value('PINECONE_INDEX', 'connection', 'rag-index')
        self.vector_dimension = self._get_param_value('EMBEDDING_DIMENSION', 'embedding', 1536)
        
        # Inicializar conexão
        self._init_connection()
        
    def _get_param_value(self, nome, categoria, default):
        """Obtém o valor de um parâmetro de indexação, com fallback para valor padrão."""
        try:
            param = ParametroIndexacao.objects.get(nome=nome, categoria=categoria)
            return param.valor_convertido()
        except ParametroIndexacao.DoesNotExist:
            return default
        except Exception as e:
            logger.error(f"Erro ao obter parâmetro '{nome}': {str(e)}")
            return default
    
    def _init_connection(self):
        """Inicializa a conexão com o banco de dados vetorial."""
        if self.vector_db_provider.lower() == 'pinecone':
            try:
                # Verificar se temos API key configurada
                pinecone_api_key = getattr(settings, 'PINECONE_API_KEY', None)
                if not pinecone_api_key:
                    logger.error("PINECONE_API_KEY não configurada nas settings")
                    raise ValueError("PINECONE_API_KEY não configurada")
                
                # Inicializar Pinecone
                init_pinecone()
                logger.info(f"✓ Conexão com Pinecone inicializada com sucesso")
                
                # Verificar se o índice existe
                index = get_index(self.pinecone_index)
                if index:
                    logger.info(f"✓ Índice Pinecone '{self.pinecone_index}' encontrado")
                else:
                    logger.warning(f"Índice Pinecone '{self.pinecone_index}' não encontrado. Operações podem falhar.")
            
            except Exception as e:
                logger.error(f"Erro ao inicializar conexão com Pinecone: {str(e)}")
        else:
            logger.warning(f"Provider {self.vector_db_provider} não implementado para banco vetorial")
    
    def armazenar_vetores(self, vectors: List[Tuple[str, List[float], Dict]], namespace: str) -> bool:
        """
        Armazena vetores no banco de dados vetorial.
        
        Args:
            vectors: Lista de tuplas (id, embedding, metadata)
            namespace: Namespace para armazenar os vetores
            
        Returns:
            True se bem-sucedido, False caso contrário
        """
        logger.info(f"Armazenando {len(vectors)} vetores no namespace '{namespace}'")
        
        try:
            if self.vector_db_provider.lower() == 'pinecone':
                result = upsert_vectors(vectors, namespace)
                if result:
                    logger.info(f"✓ {len(vectors)} vetores armazenados com sucesso no namespace '{namespace}'")
                    return True
                else:
                    logger.error(f"Falha ao armazenar vetores no namespace '{namespace}'")
                    return False
            else:
                logger.warning(f"Provider {self.vector_db_provider} não implementado para armazenamento vetorial")
                return False
        
        except Exception as e:
            logger.error(f"Erro ao armazenar vetores: {str(e)}")
            return False
        
    def consultar_vetores(self, query_vector: List[float], namespace: Optional[str] = None, 
                      top_k: int = 3, filter_obj: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """
        Consulta vetores similares no banco de dados vetorial.
        """
        # Use o logger Django padrão
        from django.core.handlers.wsgi import logger as django_logger
        
        django_logger.info(f"[DIAGNÓSTICO] VectorDB consultando namespace '{namespace}'")
        
        # Forçar threshold para diagnóstico
        threshold = self._get_param_value('SEARCH_THRESHOLD', 'search', 0.4)
        test_threshold = 0.4  # Valor de teste forçado
        
        django_logger.info(f"[DIAGNÓSTICO] Threshold configurado: {threshold}, Forçado: {test_threshold}")
        
        try:
            if self.vector_db_provider.lower() == 'pinecone':
                results = query_vectors(query_vector, namespace, top_k, filter_obj)
                
                if results:
                    django_logger.info(f"[DIAGNÓSTICO] VectorDB recebeu {len(results)} resultados")
                    
                    # Analisar resultados com base nos thresholds
                    for i, result in enumerate(results):
                        score = result['score']
                        if score >= threshold:
                            django_logger.info(f"[DIAGNÓSTICO] Resultado {i+1} (score {score:.4f}) passa pelo threshold original ({threshold})")
                        elif score >= test_threshold:
                            django_logger.info(f"[DIAGNÓSTICO] Resultado {i+1} (score {score:.4f}) passa apenas pelo threshold de teste ({test_threshold})")
                        else:
                            django_logger.info(f"[DIAGNÓSTICO] Resultado {i+1} (score {score:.4f}) abaixo de ambos thresholds")
                else:
                    django_logger.warning("[DIAGNÓSTICO] VectorDB não obteve resultados")
                    
                return results
            else:
                django_logger.warning(f"[DIAGNÓSTICO] Provider {self.vector_db_provider} não suportado")
                return []
        
        except Exception as e:
            django_logger.error(f"[DIAGNÓSTICO] Erro na consulta VectorDB: {str(e)}")
            return []
        
    
    def consultar_vetores1(self, query_vector: List[float], namespace: Optional[str] = None, 
                          top_k: int = 3, filter_obj: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """
        Consulta vetores similares no banco de dados vetorial.
        
        Args:
            query_vector: Vetor de consulta
            namespace: Namespace opcional para restringir a consulta
            top_k: Número máximo de resultados
            filter_obj: Filtro opcional para a consulta
            
        Returns:
            Lista de resultados com IDs, scores e metadados
        """
        logger.info(f"Consultando vetores no namespace '{namespace}' (top_k={top_k})")
        
        try:
            if self.vector_db_provider.lower() == 'pinecone':
                results = query_vectors(query_vector, namespace, top_k, filter_obj)
                if results:
                    logger.info(f"✓ Consulta retornou {len(results)} resultados")
                    return results
                else:
                    logger.warning(f"Consulta não retornou resultados")
                    return []
            else:
                logger.warning(f"Provider {self.vector_db_provider} não implementado para consulta vetorial")
                return []
        
        except Exception as e:
            logger.error(f"Erro ao consultar vetores: {str(e)}")
            return []
    
    def excluir_namespace(self, namespace: str) -> bool:
        """
        Exclui um namespace do banco de dados vetorial.
        
        Args:
            namespace: Namespace a ser excluído
            
        Returns:
            True se bem-sucedido, False caso contrário
        """
        logger.info(f"Excluindo namespace '{namespace}'")
        
        try:
            if self.vector_db_provider.lower() == 'pinecone':
                result = delete_namespace(namespace)
                if result:
                    logger.info(f"✓ Namespace '{namespace}' excluído com sucesso")
                    return True
                else:
                    logger.error(f"Falha ao excluir namespace '{namespace}'")
                    return False
            else:
                logger.warning(f"Provider {self.vector_db_provider} não implementado para exclusão de namespace")
                return False
        
        except Exception as e:
            logger.error(f"Erro ao excluir namespace: {str(e)}")
            return False
    
    def obter_estatisticas_namespace(self, namespace: str) -> Dict[str, Any]:
        """
        Obtém estatísticas de um namespace.
        
        Args:
            namespace: Namespace para obter estatísticas
            
        Returns:
            Dicionário com estatísticas do namespace
        """
        logger.info(f"Obtendo estatísticas do namespace '{namespace}'")
        
        try:
            if self.vector_db_provider.lower() == 'pinecone':
                stats = get_namespace_stats(namespace)
                if stats:
                    logger.info(f"✓ Estatísticas obtidas para namespace '{namespace}'")
                    return stats
                else:
                    logger.warning(f"Não foi possível obter estatísticas para namespace '{namespace}'")
                    return {'exists': False, 'vector_count': 0}
            else:
                logger.warning(f"Provider {self.vector_db_provider} não implementado para obtenção de estatísticas")
                return {'exists': False, 'vector_count': 0}
        
        except Exception as e:
            logger.error(f"Erro ao obter estatísticas do namespace: {str(e)}")
            return {'exists': False, 'vector_count': 0, 'error': str(e)}