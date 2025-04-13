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
    try:
        # Buscar o agente pelo nome
        agente = Agente.objects.get(nome=agent_name, ativo=True)
        
        # Configura o cliente com base no provider
        if agente.llm_provider.lower() == 'openai':
            try:
                import openai
                client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
            except ImportError:
                logger.error(f"Falha ao importar OpenAI. Verifique se a biblioteca está instalada.")
                return None, None, None, None, None
                
        elif agente.llm_provider.lower() == 'anthropic':
            try:
                from anthropic import Anthropic
                client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
            except ImportError:
                logger.error(f"Falha ao importar Anthropic. Verifique se a biblioteca está instalada.")
                return None, None, None, None, None
                
        elif agente.llm_provider.lower() == 'groq':
            try:
                from groq import Groq
                client = Groq(api_key=settings.GROQ_API_KEY)
            except ImportError:
                logger.error(f"Falha ao importar Groq. Verifique se a biblioteca está instalada.")
                return None, None, None, None, None
        else:
            logger.error(f"Provedor LLM não suportado: {agente.llm_provider}")
            return None, None, None, None, None
        
        return client, agente.llm_model, agente.llm_temperature, agente.llm_system_prompt, agente.task_instructions
    
    except Agente.DoesNotExist:
        logger.warning(f"Agente '{agent_name}' não encontrado ou inativo.")
        
        # Tentar usar agente padrão com nome 'default'
        try:
            agente = Agente.objects.get(nome='default', ativo=True)
            
            # Mesma lógica de criação do cliente
            if agente.llm_provider.lower() == 'openai':
                try:
                    import openai
                    client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
                except ImportError:
                    logger.error(f"Falha ao importar OpenAI. Verifique se a biblioteca está instalada.")
                    return None, None, None, None, None
                    
            elif agente.llm_provider.lower() == 'anthropic':
                try:
                    from anthropic import Anthropic
                    client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
                except ImportError:
                    logger.error(f"Falha ao importar Anthropic. Verifique se a biblioteca está instalada.")
                    return None, None, None, None, None
                    
            elif agente.llm_provider.lower() == 'groq':
                try:
                    from groq import Groq
                    client = Groq(api_key=settings.GROQ_API_KEY)
                except ImportError:
                    logger.error(f"Falha ao importar Groq. Verifique se a biblioteca está instalada.")
                    return None, None, None, None, None
            else:
                logger.error(f"Provedor LLM não suportado: {agente.llm_provider}")
                return None, None, None, None, None
            
            return client, agente.llm_model, agente.llm_temperature, agente.llm_system_prompt, agente.task_instructions
            
        except Agente.DoesNotExist:
            # Fallback para configurações padrão usando OpenAI
            try:
                import openai
                client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
                return client, "gpt-4o", 0.7, "Você é um assistente especializado em feiras e eventos.", None
            except ImportError:
                logger.error("Não foi possível inicializar nenhum cliente LLM.")
                return None, None, None, None, None
    
    except Exception as e:
        logger.error(f"Erro ao obter cliente LLM: {str(e)}")
        return None, None, None, None, None


def get_embedding_config():
    """
    Retorna a configuração para geração de embeddings
    
    Returns:
        Dicionário com as configurações para embeddings
    """
    try:
        # Primeiro tenta encontrar um agente específico para embeddings
        agente = Agente.objects.filter(nome__icontains='embedding', ativo=True).first()
        
        if not agente:
            # Fallback para o primeiro agente que tenha OpenAI como provider
            agente = Agente.objects.filter(llm_provider='openai', ativo=True).first()
        
        if agente:
            # Configurar com base no agente
            client, model, _, _, _ = get_llm_client(agente.nome)
            
            # Determinar modelo de embedding com base no provider
            if agente.llm_provider.lower() == 'openai':
                embedding_model = "text-embedding-3-small"  # Padrão
            else:
                embedding_model = "text-embedding-3-small"  # Fallback para OpenAI
            
            return {
                'provider': agente.llm_provider.lower(),
                'model': embedding_model,
                'client': client
            }
        
        # Fallback para OpenAI padrão
        import openai
        client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        
        return {
            'provider': 'openai',
            'model': 'text-embedding-3-small',
            'client': client
        }
    
    except Exception as e:
        logger.error(f"Erro ao obter configuração de embeddings: {str(e)}")
        return None