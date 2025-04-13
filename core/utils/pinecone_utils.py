#core/utils/pinecone_utils.py
"""
Utilitários para integração com o Pinecone
"""
import logging
from django.conf import settings
from core.models import ParametroIndexacao

logger = logging.getLogger(__name__)

# Cliente global do Pinecone
_pinecone_client = None
_pinecone_index = None

def get_param_value(nome, categoria, default):
    """Obtém o valor de um parâmetro de indexação, com fallback para valor padrão"""
    try:
        param = ParametroIndexacao.objects.get(nome=nome, categoria=categoria)
        return param.valor_convertido()
    except ParametroIndexacao.DoesNotExist:
        logger.warning(f"Parâmetro '{nome}' não encontrado na categoria '{categoria}'. Usando valor padrão: {default}")
        return default

def init_pinecone():
    """Inicializa a conexão com o Pinecone"""
    global _pinecone_client, _pinecone_index
    
    try:
        # Importar Pinecone
        try:
            from pinecone import Pinecone, ServerlessSpec
        except ImportError:
            logger.error("Falha ao importar Pinecone. Verifique se a biblioteca está instalada.")
            return None
        
        # Obter a API key dos parâmetros ou das configurações
        api_key = get_param_value('PINECONE_API_KEY', 'connection', settings.PINECONE_API_KEY)
        
        if not api_key:
            logger.error("API Key do Pinecone não encontrada.")
            return None
            
        # Criar instância do cliente Pinecone
        _pinecone_client = Pinecone(api_key=api_key)
        
        # Verificar se o índice existe, caso contrário criar
        index_name = get_param_value('VECTOR_DB_INDEX_NAME', 'connection', settings.PINECONE_INDEX_NAME)
        dimension = get_param_value('EMBEDDING_DIMENSION', 'embedding', 1536)  # padrão para ada-002
        metric = get_param_value('VECTOR_DB_METRIC', 'connection', 'cosine')
        
        # Verificar se o índice já existe
        existing_indexes = _pinecone_client.list_indexes()
        
        if index_name not in [idx.name for idx in existing_indexes.indexes]:
            # Obter parâmetros para criação do índice
            cloud = get_param_value('PINECONE_CLOUD', 'connection', 'aws')
            region = get_param_value('PINECONE_REGION', 'connection', 'us-west-2')
            
            # Criar um novo índice
            _pinecone_client.create_index(
                name=index_name,
                dimension=dimension,
                metric=metric,
                spec=ServerlessSpec(cloud=cloud, region=region)
            )
            
            logger.info(f"Índice Pinecone '{index_name}' criado com sucesso.")
        
        # Obter o índice
        _pinecone_index = _pinecone_client.Index(index_name)
        
        return _pinecone_index
    
    except Exception as e:
        logger.error(f"Erro ao inicializar Pinecone: {str(e)}")
        return None

def get_index():
    """Obtém a instância do índice Pinecone"""
    global _pinecone_client, _pinecone_index
    
    try:
        if _pinecone_index is None:
            if _pinecone_client is None:
                init_pinecone()
            else:
                index_name = get_param_value('VECTOR_DB_INDEX_NAME', 'connection', settings.PINECONE_INDEX_NAME)
                _pinecone_index = _pinecone_client.Index(index_name)
        
        return _pinecone_index
    except Exception as e:
        logger.error(f"Erro ao obter índice Pinecone: {str(e)}")
        # Tentar inicializar novamente
        return init_pinecone()

def upsert_vectors(vectors, namespace, batch_size=100):
    """
    Insere/atualiza vetores no Pinecone
    
    Args:
        vectors: Lista de tuplas (id, embedding, metadata)
        namespace: Namespace para usar
        batch_size: Tamanho do lote para inserção
    """
    index = get_index()
    
    if not index:
        logger.error("Não foi possível obter o índice Pinecone.")
        return False
    
    # Processar em lotes
    batches = [vectors[i:i + batch_size] for i in range(0, len(vectors), batch_size)]
    
    for batch in batches:
        try:
            # Formatar para o formato do Pinecone
            pinecone_vectors = []
            for item in batch:
                pinecone_vectors.append({
                    'id': item[0],
                    'values': item[1],
                    'metadata': item[2]
                })
            
            # Na nova API, precisamos passar os vetores como uma lista de dicionários
            index.upsert(vectors=pinecone_vectors, namespace=namespace)
            logger.debug(f"Lote de {len(batch)} vetores inserido com sucesso no namespace '{namespace}'.")
        except Exception as e:
            logger.error(f"Erro ao inserir batch no Pinecone: {str(e)}")
            raise

def delete_namespace(namespace):
    """Exclui um namespace inteiro do Pinecone"""
    try:
        index = get_index()
        if not index:
            return False
            
        # Usar o método delete com filtro de namespace
        index.delete(delete_all=True, namespace=namespace)
        logger.info(f"Namespace '{namespace}' excluído com sucesso.")
        return True
    except Exception as e:
        logger.error(f"Erro ao excluir namespace {namespace} do Pinecone: {str(e)}")
        return False

def query_vectors(query_embedding, namespace, top_k=3, filter_dict=None):
    """
    Consulta os vetores mais próximos no Pinecone
    
    Args:
        query_embedding: O embedding de consulta
        namespace: Namespace para pesquisar
        top_k: Número de resultados para retornar
        filter_dict: Filtros adicionais para a consulta
    
    Returns:
        Lista de resultados (id, score, metadata)
    """
    try:
        index = get_index()
        if not index:
            logger.error("Não foi possível obter o índice Pinecone para consulta.")
            return []
        
        # Caso não tenha sido especificado, obter top_k dos parâmetros
        if top_k is None:
            top_k = get_param_value('SEARCH_TOP_K', 'search', 3)
        
        # Realizar a consulta com a nova API
        results = index.query(
            vector=query_embedding,
            top_k=top_k,
            namespace=namespace,
            filter=filter_dict,
            include_metadata=True
        )
        
        # Formatar os resultados para o formato antigo para manter compatibilidade
        formatted_results = []
        for match in results.matches:
            formatted_results.append({
                'id': match.id,
                'score': match.score,
                'metadata': match.metadata
            })
        
        return formatted_results
    
    except Exception as e:
        logger.error(f"Erro ao consultar Pinecone: {str(e)}")
        return []