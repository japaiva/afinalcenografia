# core/utils/llm_utils.py
import logging
from django.conf import settings
from core.models import Agente

logger = logging.getLogger(__name__)

def get_llm_client(agent_name):
    """
    Retorna o cliente LLM apropriado com base no nome do agente
    
    Args:
        agent_name: Nome do agente configurado no banco de dados
    
    Returns:
        Tupla com (client, model_name, temperature, system_prompt, task_instructions)
        Se não encontrar o agente, retorna (None, None, None, None, None)
    """
    from core.utils.llm_factory import LLMClientFactory
    return LLMClientFactory.get_client_for_agent(agent_name)


def get_embedding_config():
    """
    Retorna a configuração para geração de embeddings
    
    Returns:
        Dicionário com as configurações para embeddings
    """
    from core.utils.parametro_utils import ParametroManager
    
    try:
        # Obter parâmetros de embedding da cache ou banco de dados
        embedding_params = ParametroManager.get_param_values_for_category('embedding')
        
        provider = embedding_params.get('EMBEDDING_PROVIDER', 'openai')
        model = embedding_params.get('EMBEDDING_MODEL', 'text-embedding-3-small')
        
        # Obter cliente para o provider
        from core.utils.llm_factory import LLMClientFactory
        client, success = LLMClientFactory.get_client(provider)
        
        if success:
            logger.info(f"✓ Configuração de embeddings: provider={provider}, model={model}")
            return {
                'provider': provider,
                'model': model,
                'client': client
            }
        
        # Fallback para OpenAI
        logger.warning(f"Não foi possível criar cliente para provider {provider}. Usando OpenAI como fallback.")
        client, success = LLMClientFactory.get_client('openai')
        
        if success:
            logger.info("✓ Usando cliente OpenAI fallback para embeddings")
            return {
                'provider': 'openai',
                'model': 'text-embedding-3-small',
                'client': client
            }
        
        logger.error("Não foi possível criar nenhum cliente para embeddings")
        return None
    
    except Exception as e:
        logger.error(f"Erro ao obter configuração de embeddings: {str(e)}")
        return None