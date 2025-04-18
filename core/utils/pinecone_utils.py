# core/utils/pinecone_utils.py

import logging
import time
import sys
from django.conf import settings
from core.models import ParametroIndexacao

# Adicionar a importação da biblioteca Pinecone
from pinecone import Pinecone, ServerlessSpec

logger = logging.getLogger(__name__)

# Cliente global do Pinecone
_pinecone_client = None
_pinecone_index = None

def get_param_value(nome, categoria, default):
    """Obtém o valor de um parâmetro de indexação, com fallback para valor padrão"""
    try:
        param = ParametroIndexacao.objects.get(nome=nome, categoria=categoria)
        valor = param.valor_convertido()
        logger.info(f"✓ Parâmetro '{nome}' encontrado na categoria '{categoria}' com valor: {valor}")
        return valor
    except ParametroIndexacao.DoesNotExist:
        logger.warning(f"Parâmetro '{nome}' não encontrado na categoria '{categoria}'. Usando valor padrão: {default}")
        return default
    except Exception as e:
        logger.error(f"Erro ao obter parâmetro '{nome}': {str(e)}")
        return default
    
def init_pinecone():
    """Inicializa a conexão com o Pinecone"""
    global _pinecone_client, _pinecone_index
    
    try:
        # Obter API key
        api_key = settings.PINECONE_API_KEY
        logger.info("[DIAGNÓSTICO PINECONE] ✓ PINECONE_API_KEY encontrada nas configurações do Django")
        logger.info(f"[DIAGNÓSTICO PINECONE] API Key (primeiros 5 chars): {api_key[:5]}...")
        
        if not api_key:
            logger.error("[DIAGNÓSTICO PINECONE] ✗ API Key do Pinecone não encontrada. Verifique as configurações ou a tabela de parâmetros.")
            return None
        
        # Criar instância do cliente Pinecone
        _pinecone_client = Pinecone(api_key=api_key)
        logger.info("[DIAGNÓSTICO PINECONE] ✓ Cliente Pinecone inicializado com sucesso")
        
        # Verificar se o índice existe, caso contrário criar
        # Primeiro tenta obter da tabela, depois das configurações
        index_name = get_param_value('VECTOR_DB_INDEX_NAME', 'connection', None)
        if not index_name:
            index_name = 'afinal-feira-index'  # Nome padrão como fallback
            logger.warning(f"[DIAGNÓSTICO PINECONE] ✗ Nome do índice não encontrado. Usando padrão: {index_name}")
            
        dimension = get_param_value('EMBEDDING_DIMENSION', 'embedding', 1536)
        metric = get_param_value('VECTOR_DB_METRIC', 'connection', 'cosine')
        
        # Verificar se o índice já existe
        logger.info("[DIAGNÓSTICO PINECONE] Listando índices Pinecone existentes...")
        existing_indexes = _pinecone_client.list_indexes()
        
        existing_index_names = [idx.name for idx in existing_indexes.indexes]
        logger.info(f"[DIAGNÓSTICO PINECONE] ✓ Índices existentes encontrados: {existing_index_names}")
        
        if index_name not in existing_index_names:
            # Criar um novo índice
            logger.info(f"[DIAGNÓSTICO PINECONE] Índice {index_name} não encontrado. Iniciando criação...")
            cloud = 'aws'  # Valor padrão
            region = 'us-west-2'  # Valor padrão
            
            try:
                _pinecone_client.create_index(
                    name=index_name,
                    dimension=dimension,
                    metric=metric,
                    spec=ServerlessSpec(cloud=cloud, region=region)
                )
                logger.info(f"[DIAGNÓSTICO PINECONE] ✓ Índice Pinecone '{index_name}' criado com sucesso (dimensão: {dimension}, métrica: {metric})")
                
                # Aguardar um pouco para que o índice seja totalmente criado
                logger.info(f"[DIAGNÓSTICO PINECONE] Aguardando 5 segundos para a propagação do índice...")
                time.sleep(5)
                logger.info(f"[DIAGNÓSTICO PINECONE] ✓ Tempo de espera concluído")
            except Exception as e:
                logger.error(f"[DIAGNÓSTICO PINECONE] ✗ Erro ao criar índice Pinecone: {str(e)}")
                # Continuar para tentar obter o índice mesmo assim, caso ele já exista
        else:
            logger.info(f"[DIAGNÓSTICO PINECONE] ✓ Índice '{index_name}' já existe no Pinecone")
        
        # Obter o índice
        logger.info(f"[DIAGNÓSTICO PINECONE] Obtendo índice '{index_name}'...")
        _pinecone_index = _pinecone_client.Index(index_name)
        logger.info(f"[DIAGNÓSTICO PINECONE] ✓ Índice Pinecone '{index_name}' obtido com sucesso")
        
        return _pinecone_index
    
    except Exception as e:
        logger.error(f"[DIAGNÓSTICO PINECONE] ✗ Erro ao inicializar Pinecone: {str(e)}")
        return None

def get_index():
    """Obtém a instância do índice Pinecone"""
    global _pinecone_client, _pinecone_index
    
    try:
        if _pinecone_index is None:
            logger.debug("[DIAGNÓSTICO PINECONE] Índice Pinecone não inicializado")
            if _pinecone_client is None:
                logger.debug("[DIAGNÓSTICO PINECONE] Cliente Pinecone não inicializado, inicializando...")
                return init_pinecone()
            else:
                index_name = get_param_value('VECTOR_DB_INDEX_NAME', 'connection', 'afinal-feira-index')
                logger.debug(f"[DIAGNÓSTICO PINECONE] Cliente já inicializado, obtendo índice '{index_name}'")
                _pinecone_index = _pinecone_client.Index(index_name)
                logger.info(f"[DIAGNÓSTICO PINECONE] ✓ Índice '{index_name}' obtido do cliente existente")
                return _pinecone_index
        else:
            logger.debug("[DIAGNÓSTICO PINECONE] Retornando índice Pinecone já inicializado")
            return _pinecone_index
    except Exception as e:
        logger.error(f"[DIAGNÓSTICO PINECONE] ✗ Erro ao obter índice Pinecone: {str(e)}")
        # Tentar inicializar novamente
        return init_pinecone()

def upsert_vectors(vectors, namespace, batch_size=100):
    """
    Insere/atualiza vetores no Pinecone
    
    Args:
        vectors: Lista de tuplas (id, embedding, metadata)
        namespace: Namespace para usar
        batch_size: Tamanho do lote para inserção
        
    Returns:
        True se bem-sucedido, False caso contrário
    """
    logger.info(f"[DIAGNÓSTICO PINECONE] Iniciando upsert de {len(vectors)} vetores no namespace '{namespace}'")
    
    # Obter o índice Pinecone
    index = get_index()
    
    if not index:
        logger.error("[DIAGNÓSTICO PINECONE] ✗ Não foi possível obter o índice Pinecone.")
        return False
    
    # Processar em lotes para evitar exceder limites da API
    batches = [vectors[i:i + batch_size] for i in range(0, len(vectors), batch_size)]
    logger.info(f"[DIAGNÓSTICO PINECONE] ✓ Vetores divididos em {len(batches)} lotes de até {batch_size} cada")
    
    successful_batches = 0
    failed_batches = 0
    
    for i, batch in enumerate(batches):
        try:
            logger.info(f"[DIAGNÓSTICO PINECONE] Processando lote {i+1}/{len(batches)} com {len(batch)} vetores")
            
            # Formatar para o formato do Pinecone
            pinecone_vectors = []
            valid_vectors = 0
            for item in batch:
                # Verificar formato de item
                if len(item) != 3:
                    logger.warning(f"[DIAGNÓSTICO PINECONE] ✗ Item com formato inválido: {item}. Pulando.")
                    continue
                    
                id_str, embedding, metadata = item
                
                # Verificar se embedding é uma lista ou array
                if not isinstance(embedding, (list, tuple)) or len(embedding) == 0:
                    logger.warning(f"[DIAGNÓSTICO PINECONE] ✗ Embedding inválido para id {id_str}. Pulando.")
                    continue
                
                # Verificar se metadata é um dicionário
                if not isinstance(metadata, dict):
                    logger.warning(f"[DIAGNÓSTICO PINECONE] ✗ Metadata inválido para id {id_str}. Pulando.")
                    metadata = {"error": "metadata_invalid"}
                
                # Adicionar ao lote
                pinecone_vectors.append({
                    'id': str(id_str),  # Garantir que id é string
                    'values': embedding,
                    'metadata': metadata
                })
                valid_vectors += 1
            
            if not pinecone_vectors:
                logger.warning(f"[DIAGNÓSTICO PINECONE] ✗ Lote {i+1} não contém vetores válidos. Pulando.")
                continue
            
            logger.info(f"[DIAGNÓSTICO PINECONE] ✓ Lote {i+1} preparado com {valid_vectors} vetores válidos")
                
            # Executar o upsert
            logger.info(f"[DIAGNÓSTICO PINECONE] Realizando upsert de {len(pinecone_vectors)} vetores no namespace '{namespace}'")
            index.upsert(vectors=pinecone_vectors, namespace=namespace)
            
            logger.info(f"[DIAGNÓSTICO PINECONE] ✓ Lote {i+1} inserido com sucesso no namespace '{namespace}'")
            successful_batches += 1
            
            # Pausa entre lotes para evitar limitações de taxa
            if i < len(batches) - 1:
                time.sleep(0.5)
                
        except Exception as e:
            logger.error(f"[DIAGNÓSTICO PINECONE] ✗ Erro ao inserir lote {i+1} no Pinecone: {str(e)}")
            failed_batches += 1
    
    logger.info(f"[DIAGNÓSTICO PINECONE] ✓ Upsert concluído: {successful_batches} lotes bem-sucedidos, {failed_batches} falhas")
    
    # Retornar True se pelo menos 1 lote foi bem-sucedido
    return successful_batches > 0

def delete_vectors(ids, namespace):
    """
    Exclui vetores específicos do Pinecone
    
    Args:
        ids: Lista de ids de vetores a excluir
        namespace: Namespace onde os vetores estão
        
    Returns:
        True se bem-sucedido, False caso contrário
    """
    try:
        index = get_index()
        if not index:
            logger.error("[DIAGNÓSTICO PINECONE] ✗ Não foi possível obter o índice Pinecone para exclusão.")
            return False
            
        # Converter ids para strings
        str_ids = [str(id) for id in ids]
        logger.info(f"[DIAGNÓSTICO PINECONE] Preparando para excluir {len(str_ids)} vetores do namespace '{namespace}'")
        
        # Excluir os vetores
        index.delete(ids=str_ids, namespace=namespace)
        logger.info(f"[DIAGNÓSTICO PINECONE] ✓ {len(ids)} vetores excluídos com sucesso do namespace '{namespace}'")
        return True
        
    except Exception as e:
        logger.error(f"[DIAGNÓSTICO PINECONE] ✗ Erro ao excluir vetores do Pinecone: {str(e)}")
        return False


def delete_namespace(namespace):
    """
    Exclui um namespace inteiro do Pinecone
    
    Args:
        namespace: Namespace a excluir
        
    Returns:
        True se bem-sucedido, False caso contrário
    """
    try:
        index = get_index()
        if not index:
            logger.error("[DIAGNÓSTICO PINECONE] ✗ Não foi possível obter o índice Pinecone para exclusão de namespace.")
            return False
        
        logger.info(f"[DIAGNÓSTICO PINECONE] Preparando para excluir o namespace '{namespace}'")
            
        # Usar o método delete com delete_all=True
        index.delete(delete_all=True, namespace=namespace)
        logger.info(f"[DIAGNÓSTICO PINECONE] ✓ Namespace '{namespace}' excluído com sucesso")
        return True
        
    except Exception as e:
        logger.error(f"[DIAGNÓSTICO PINECONE] ✗ Erro ao excluir namespace {namespace} do Pinecone: {str(e)}")
        return False
    
    
def query_vectors(query_embedding, namespace, top_k=3, filter_dict=None):

    import sys
    print(f"\n[PRINT DIRETO] PINECONE: Consultando vetores no namespace '{namespace}' com top_k={top_k}", file=sys.stderr)
    print(f"[PRINT DIRETO] PINECONE: Filtro aplicado: {filter_dict}", file=sys.stderr)
    
    try:
        index = get_index()
        if not index:
            print(f"[PRINT DIRETO] PINECONE: ERRO - Não foi possível obter o índice Pinecone para consulta.", file=sys.stderr)
            logger.error("[DIAGNÓSTICO PINECONE] ✗ Não foi possível obter o índice Pinecone para consulta.")
            return []
        
        # Caso não tenha sido especificado, obter top_k dos parâmetros
        if top_k is None:
            top_k = get_param_value('SEARCH_TOP_K', 'search', 3)
        
        # Verificar se query_embedding é válido
        if not query_embedding or not isinstance(query_embedding, (list, tuple)) or len(query_embedding) == 0:
            print(f"[PRINT DIRETO] PINECONE: ERRO - Embedding de consulta inválido", file=sys.stderr)
            logger.error("[DIAGNÓSTICO PINECONE] ✗ Embedding de consulta inválido")
            return []
            
        # Verificar estatísticas do namespace antes da consulta
        try:
            stats = get_namespace_stats(namespace)
            if stats and stats['exists']:
                print(f"[PRINT DIRETO] PINECONE: Namespace '{namespace}' existe e contém {stats['vector_count']} vetores", file=sys.stderr)
            else:
                print(f"[PRINT DIRETO] PINECONE: ALERTA - Namespace '{namespace}' não existe ou está vazio.", file=sys.stderr)
        except Exception as e:
            print(f"[PRINT DIRETO] PINECONE: Erro ao verificar estatísticas do namespace: {str(e)}", file=sys.stderr)
        
        # Realizar a consulta
        print(f"[PRINT DIRETO] PINECONE: Executando query com embedding de tamanho {len(query_embedding)}", file=sys.stderr)
        
        results = index.query(
            vector=query_embedding,
            top_k=top_k,
            namespace=namespace,
            filter=filter_dict,
            include_metadata=True
        )
        
        print(f"[PRINT DIRETO] PINECONE: Consulta retornou {len(results.matches)} resultados", file=sys.stderr)
        
        # Formatar os resultados
        formatted_results = []
        for i, match in enumerate(results.matches):
            formatted_results.append({
                'id': match.id,
                'score': match.score,
                'metadata': match.metadata
            })
            print(f"[PRINT DIRETO] PINECONE: Resultado {i+1}: ID={match.id}, Score={match.score:.4f}", file=sys.stderr)
        
        if formatted_results:
            print(f"[PRINT DIRETO] PINECONE: Melhor score: {formatted_results[0]['score']}", file=sys.stderr)
        else:
            print(f"[PRINT DIRETO] PINECONE: Nenhum resultado encontrado", file=sys.stderr)
            
        return formatted_results
    
    except Exception as e:
        print(f"[PRINT DIRETO] PINECONE: ERRO ao consultar Pinecone: {str(e)}", file=sys.stderr)
        logger.error(f"[DIAGNÓSTICO PINECONE] ✗ Erro ao consultar Pinecone: {str(e)}")
        return []

def fetch_vector(id, namespace):
    """
    Busca um vetor específico pelo ID
    
    Args:
        id: ID do vetor
        namespace: Namespace onde o vetor está
        
    Returns:
        Dicionário com o vetor ou None se não encontrado
    """
    try:
        index = get_index()
        if not index:
            logger.error("[DIAGNÓSTICO PINECONE] ✗ Não foi possível obter o índice Pinecone para busca de vetor.")
            return None
            
        # Buscar o vetor
        logger.info(f"[DIAGNÓSTICO PINECONE] Buscando vetor com ID '{id}' no namespace '{namespace}'")
        result = index.fetch(ids=[str(id)], namespace=namespace)
        
        if not result.vectors or str(id) not in result.vectors:
            logger.warning(f"[DIAGNÓSTICO PINECONE] ✗ Vetor com ID '{id}' não encontrado no namespace '{namespace}'")
            return None
            
        vector_data = result.vectors[str(id)]
        logger.info(f"[DIAGNÓSTICO PINECONE] ✓ Vetor com ID '{id}' encontrado com sucesso")
        
        return {
            'id': id,
            'values': vector_data.values,
            'metadata': vector_data.metadata
        }
        
    except Exception as e:
        logger.error(f"[DIAGNÓSTICO PINECONE] ✗ Erro ao buscar vetor do Pinecone: {str(e)}")
        return None

def get_namespace_stats(namespace):
    """
    Obtém estatísticas sobre um namespace
    
    Args:
        namespace: Namespace para obter estatísticas
        
    Returns:
        Dicionário com estatísticas ou None em caso de erro
    """
    try:
        index = get_index()
        if not index:
            logger.error("[DIAGNÓSTICO PINECONE] ✗ Não foi possível obter o índice Pinecone para estatísticas.")
            return None
            
        # Obter estatísticas
        logger.info(f"[DIAGNÓSTICO PINECONE] Obtendo estatísticas do namespace '{namespace}'")
        stats = index.describe_index_stats()
        
        # Verificar se o namespace existe
        namespaces = stats.namespaces
        if namespace not in namespaces:
            logger.warning(f"[DIAGNÓSTICO PINECONE] ✗ Namespace '{namespace}' não encontrado no índice")
            return {
                'namespace': namespace,
                'vector_count': 0,
                'exists': False
            }
        
        vector_count = namespaces[namespace].vector_count
        logger.info(f"[DIAGNÓSTICO PINECONE] ✓ Estatísticas obtidas: namespace '{namespace}' contém {vector_count} vetores")
            
        # Retornar estatísticas do namespace
        return {
            'namespace': namespace,
            'vector_count': vector_count,
            'exists': True
        }
        
    except Exception as e:
        logger.error(f"[DIAGNÓSTICO PINECONE] ✗ Erro ao obter estatísticas do Pinecone: {str(e)}")
        return None