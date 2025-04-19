"""
Factory pattern para criar e gerenciar clientes LLM
"""
import logging
import functools
from typing import Tuple, Optional, Dict, Any

from django.conf import settings

logger = logging.getLogger(__name__)

# Singleton para armazenar clientes já inicializados
_client_cache = {}

class LLMClientFactory:
    """
    Fábrica para criar e gerenciar clientes LLM
    """
    
    @staticmethod
    @functools.lru_cache(maxsize=8)
    def get_client(provider: str, api_key: Optional[str] = None) -> Tuple[Any, bool]:
        """
        Retorna um cliente LLM para o provedor especificado
        
        Args:
            provider: Nome do provedor ('openai', 'anthropic', 'groq')
            api_key: Chave API opcional. Se não fornecida, usa a configuração do Django
            
        Returns:
            Tuple contendo (cliente, success_flag)
        """
        cache_key = f"{provider}:{api_key or 'default'}"
        
        # Verificar cache para evitar inicializações repetidas
        if cache_key in _client_cache:
            logger.debug(f"Usando cliente {provider} em cache")
            return _client_cache[cache_key], True
        
        try:
            # Determinar a chave API a ser usada
            if not api_key:
                if provider.lower() == 'openai':
                    api_key = settings.OPENAI_API_KEY
                elif provider.lower() == 'anthropic':
                    api_key = settings.ANTHROPIC_API_KEY
                elif provider.lower() == 'groq':
                    api_key = settings.GROQ_API_KEY
                
            # Criar o cliente apropriado
            if provider.lower() == 'openai':
                try:
                    import openai
                    client = openai.OpenAI(api_key=api_key)
                    _client_cache[cache_key] = client
                    logger.info(f"Cliente OpenAI inicializado com sucesso")
                    return client, True
                except ImportError:
                    logger.error("Falha ao importar biblioteca OpenAI")
                    return None, False
                    
            elif provider.lower() == 'anthropic':
                try:
                    from anthropic import Anthropic
                    client = Anthropic(api_key=api_key)
                    _client_cache[cache_key] = client
                    logger.info(f"Cliente Anthropic inicializado com sucesso")
                    return client, True
                except ImportError:
                    logger.error("Falha ao importar biblioteca Anthropic")
                    return None, False
                    
            elif provider.lower() == 'groq':
                try:
                    from groq import Groq
                    client = Groq(api_key=api_key)
                    _client_cache[cache_key] = client
                    logger.info(f"Cliente Groq inicializado com sucesso")
                    return client, True
                except ImportError:
                    logger.error("Falha ao importar biblioteca Groq")
                    return None, False
            else:
                logger.error(f"Provedor LLM não suportado: {provider}")
                return None, False
                
        except Exception as e:
            logger.error(f"Erro ao inicializar cliente {provider}: {str(e)}")
            return None, False
    
    @staticmethod
    def get_client_for_agent(agent_name: str) -> Tuple[Any, str, float, str, Optional[str]]:
        """
        Obtém um cliente LLM para o agente especificado
        
        Args:
            agent_name: Nome do agente configurado no banco de dados
            
        Returns:
            Tupla com (client, model_name, temperature, system_prompt, task_instructions)
        """
        from core.models import Agente
        
        try:
            # Buscar o agente pelo nome
            logger.info(f"Buscando agente '{agent_name}' no banco de dados")
            agente = Agente.objects.get(nome=agent_name, ativo=True)
            logger.info(f"Agente '{agent_name}' encontrado (provider: {agente.llm_provider}, modelo: {agente.llm_model})")
            
            # Obter cliente
            client, success = LLMClientFactory.get_client(agente.llm_provider)
            
            if success:
                return client, agente.llm_model, agente.llm_temperature, agente.llm_system_prompt, agente.task_instructions
            
            # Tentar fallback
            logger.warning(f"Não foi possível criar cliente para o agente '{agent_name}'. Tentando fallback")
            return LLMClientFactory._get_fallback_client(agent_name)
            
        except Agente.DoesNotExist:
            logger.warning(f"Agente '{agent_name}' não encontrado. Tentando agente padrão 'default'")
            return LLMClientFactory._get_fallback_client(agent_name)
        except Exception as e:
            logger.error(f"Erro ao obter cliente LLM para agente '{agent_name}': {str(e)}")
            return None, None, None, None, None
            
    @staticmethod
    def _get_fallback_client(original_agent_name: str) -> Tuple[Any, str, float, str, Optional[str]]:
        """
        Obtém um cliente de fallback quando o cliente principal falha
        
        Args:
            original_agent_name: Nome do agente original que falhou
            
        Returns:
            Tupla com (client, model_name, temperature, system_prompt, task_instructions)
        """
        from core.models import Agente
        
        try:
            # Tentar usar o agente padrão
            logger.info("Tentando usar agente padrão 'default'")
            agente = Agente.objects.get(nome='default', ativo=True)
            
            # Obter cliente
            client, success = LLMClientFactory.get_client(agente.llm_provider)
            
            if success:
                logger.info(f"Usando agente padrão 'default' como fallback para '{original_agent_name}'")
                return client, agente.llm_model, agente.llm_temperature, agente.llm_system_prompt, agente.task_instructions
                
        except Agente.DoesNotExist:
            logger.warning("Agente padrão 'default' não encontrado")
        except Exception as e:
            logger.error(f"Erro ao obter agente padrão: {str(e)}")
            
        # Fallback final: configurações OpenAI hardcoded
        try:
            logger.warning("Usando configurações OpenAI hardcoded como último recurso")
            client, success = LLMClientFactory.get_client('openai')
            
            if success:
                return client, "gpt-4o", 0.7, "Você é um assistente especializado em feiras e eventos.", None
            else:
                logger.error("Não foi possível inicializar nenhum cliente LLM.")
                return None, None, None, None, None
                
        except Exception as e:
            logger.error(f"Erro ao inicializar cliente de fallback: {str(e)}")
            return None, None, None, None, None