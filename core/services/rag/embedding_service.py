# core/services/rag/embedding_service.py
import logging
import time
from typing import List, Dict, Any, Optional
import json

from django.conf import settings
from core.utils.llm_utils import get_llm_client
from core.models import ParametroIndexacao, FeiraManualQA

logger = logging.getLogger(__name__)

class EmbeddingService:
    """
    Serviço responsável pela geração e gerenciamento de embeddings para o sistema RAG.
    """
    
    def __init__(self, agent_name='Assistente RAG de Feiras'):
        """
        Inicializa o serviço de embeddings.
        
        Args:
            agent_name: Nome do agente configurado a ser utilizado.
        """
        logger.info(f"Inicializando EmbeddingService com agente '{agent_name}'")
        self.agent_name = agent_name
        
        # Obter cliente LLM usando o utilitário
        try:
            logger.info(f"Tentando obter cliente LLM para agente '{agent_name}'")
            self.client, self.model, self.temperature, self.system_prompt, self.task_instructions = get_llm_client(agent_name)
            logger.info(f"✓ Cliente LLM obtido com sucesso. Modelo: {self.model}, Temperatura: {self.temperature}")
        except Exception as e:
            logger.error(f"Erro ao obter cliente LLM para agente '{agent_name}': {str(e)}")
            raise
        
        # Determinar o provider com base no cliente
        try:
            if hasattr(self.client, 'chat'):  # OpenAI
                self.provider = 'openai'
                logger.info(f"✓ Provider determinado: OpenAI")
            elif hasattr(self.client, 'messages'):  # Anthropic
                self.provider = 'anthropic'
                logger.info(f"✓ Provider determinado: Anthropic")
            elif hasattr(self.client, 'completion'):  # Groq
                self.provider = 'groq'
                logger.info(f"✓ Provider determinado: Groq")
            else:
                logger.warning(f"Não foi possível determinar o provedor do agente '{agent_name}'. Tentando usar agente alternativo 'Assistente de Briefing'")
                # Fallback para o Assistente de Briefing se o Assistente RAG de Feiras não existir
                self.client, self.model, self.temperature, self.system_prompt, self.task_instructions = get_llm_client('Assistente de Briefing')
                logger.info(f"✓ Cliente alternativo obtido com sucesso. Modelo: {self.model}")
                
                # Tentar determinar o provider novamente
                if hasattr(self.client, 'chat'):
                    self.provider = 'openai'
                    logger.info(f"✓ Provider alternativo determinado: OpenAI")
                elif hasattr(self.client, 'messages'):
                    self.provider = 'anthropic'
                    logger.info(f"✓ Provider alternativo determinado: Anthropic")
                elif hasattr(self.client, 'completion'):
                    self.provider = 'groq'
                    logger.info(f"✓ Provider alternativo determinado: Groq")
                else:
                    error_msg = f"Não foi possível determinar o provedor do agente alternativo"
                    logger.error(error_msg)
                    raise ValueError(error_msg)
        except Exception as e:
            logger.error(f"Erro ao determinar provider: {str(e)}")
            raise
        
        # Obter parâmetros de embedding
        try:
            logger.info("Obtendo parâmetros de embedding do sistema")
            self.embedding_dimension = self._get_param_value('EMBEDDING_DIMENSION', 'embedding', 1536)
            self.embedding_model = self._get_param_value('EMBEDDING_MODEL', 'embedding', "text-embedding-3-small")
            self.embedding_provider = self._get_param_value('EMBEDDING_PROVIDER', 'embedding', 'openai')
            self.embedding_retry_count = self._get_param_value('EMBEDDING_RETRY_COUNT', 'embedding', 3)
            self.embedding_retry_delay = self._get_param_value('EMBEDDING_RETRY_DELAY', 'embedding', 2)
            
            logger.info(f"✓ Parâmetros de embedding configurados: Dimensão={self.embedding_dimension}, Modelo={self.embedding_model}, Provider={self.embedding_provider}")
        except Exception as e:
            logger.error(f"Erro ao obter parâmetros de embedding: {str(e)}")
            # Usar valores padrão em caso de erro
            self.embedding_dimension = 1536
            self.embedding_model = "text-embedding-3-small"
            self.embedding_provider = 'openai'
            self.embedding_retry_count = 3
            self.embedding_retry_delay = 2
            logger.info(f"✓ Usando valores padrão para parâmetros de embedding após erro: Dimensão={self.embedding_dimension}, Modelo={self.embedding_model}")
    
    def _get_param_value(self, nome, categoria, default):
        """Obtém o valor de um parâmetro de indexação, com fallback para valor padrão."""
        logger.debug(f"Obtendo parâmetro '{nome}' da categoria '{categoria}'")
        try:
            param = ParametroIndexacao.objects.get(nome=nome, categoria=categoria)
            valor = param.valor_convertido()
            logger.debug(f"✓ Parâmetro '{nome}' encontrado com valor: {valor}")
            return valor
        except ParametroIndexacao.DoesNotExist:
            logger.warning(f"Parâmetro '{nome}' não encontrado. Usando valor padrão: {default}")
            return default
        except Exception as e:
            logger.error(f"Erro ao obter parâmetro '{nome}': {str(e)}")
            return default
    
    def gerar_embeddings_qa(self, qa: FeiraManualQA) -> Optional[List[float]]:
        """
        Gera embeddings para um par QA específico.
        
        Args:
            qa: O par QA para o qual gerar embeddings.
            
        Returns:
            Lista de floats representando o embedding ou None em caso de erro.
        """
        logger.info(f"Iniciando geração de embedding para QA {qa.id}")
        
        try:
            # Preparando similar_questions
            similar_questions = qa.similar_questions if qa.similar_questions else []
            if isinstance(similar_questions, str):
                try:
                    similar_questions = json.loads(similar_questions)
                    logger.debug(f"✓ Similar questions carregadas do JSON para QA {qa.id}")
                except Exception as e:
                    logger.debug(f"Erro ao decodificar similar_questions para QA {qa.id}: {e}")
                    similar_questions = similar_questions.split(',')
                    logger.debug(f"✓ Similar questions divididas por vírgula para QA {qa.id}")
            
            # Concatenar informações
            embedding_text = f"Pergunta: {qa.question} "
            embedding_text += f"Resposta: {qa.answer} "
            embedding_text += f"Contexto: {qa.context} "
            
            if similar_questions:
                sq_text = " ".join([f"Pergunta similar: {sq}" for sq in similar_questions])
                embedding_text += sq_text
            
            logger.info(f"✓ Texto para embedding preparado para QA {qa.id} (tamanho: {len(embedding_text)} caracteres)")
            
            # Implementação de retry para resiliência
            for retry in range(self.embedding_retry_count):
                try:
                    # Gerar embedding usando o provedor específico de embeddings
                    if self.embedding_provider == 'openai':
                        if self.provider == 'openai':
                            embedding_client = self.client
                            logger.debug(f"Usando cliente OpenAI existente para QA {qa.id}")
                        else:
                            logger.debug(f"Obtendo novo cliente OpenAI para QA {qa.id}")
                            embedding_client = get_llm_client('Embedding Generator')[0]
                        
                        logger.info(f"Chamando API OpenAI para gerar embedding para QA {qa.id} (tentativa {retry+1})")
                        response = embedding_client.embeddings.create(
                            input=embedding_text,
                            model=self.embedding_model,
                            dimensions=self.embedding_dimension
                        )
                        embedding = response.data[0].embedding
                        logger.info(f"✓ Embedding gerado para QA {qa.id} com tamanho {len(embedding)} (OpenAI)")
                        return embedding
                        
                    elif self.embedding_provider == 'groq':
                        if self.provider == 'groq':
                            embedding_client = self.client
                            logger.debug(f"Usando cliente Groq existente para QA {qa.id}")
                        else:
                            logger.debug(f"Obtendo novo cliente Groq para QA {qa.id}")
                            embedding_client = get_llm_client('Embedding Generator')[0]
                        
                        logger.info(f"Chamando API Groq para gerar embedding para QA {qa.id} (tentativa {retry+1})")
                        response = embedding_client.embeddings.create(
                            input=embedding_text,
                            model=self.embedding_model,
                        )
                        embedding = response.data[0].embedding
                        logger.info(f"✓ Embedding gerado para QA {qa.id} com tamanho {len(embedding)} (Groq)")
                        return embedding
                        
                    else:
                        logger.warning(f"Geração de embeddings não implementada para o provedor {self.embedding_provider}. Usando OpenAI como fallback.")
                        openai_client = get_llm_client('Embedding Generator')[0]
                        logger.info(f"Chamando API OpenAI (fallback) para gerar embedding para QA {qa.id} (tentativa {retry+1})")
                        response = openai_client.embeddings.create(
                            input=embedding_text,
                            model="text-embedding-3-small",
                            dimensions=self.embedding_dimension
                        )
                        embedding = response.data[0].embedding
                        logger.info(f"✓ Embedding gerado com fallback para QA {qa.id} com tamanho {len(embedding)} (OpenAI fallback)")
                        return embedding
                
                except Exception as e:
                    logger.warning(f"Tentativa {retry+1} falhou para QA {qa.id}: {str(e)}")
                    if retry < self.embedding_retry_count - 1:
                        logger.info(f"Aguardando {self.embedding_retry_delay} segundos antes da próxima tentativa para QA {qa.id}")
                        time.sleep(self.embedding_retry_delay)
                    else:
                        logger.error(f"Todas as {self.embedding_retry_count} tentativas falharam para QA {qa.id}")
                        return None
                        
        except Exception as e:
            logger.error(f"Erro não tratado ao gerar embedding para QA {qa.id}: {str(e)}")
            return None
    
    def gerar_embedding_consulta(self, query: str) -> Optional[List[float]]:
        """
        Gera embedding para uma consulta.
        
        Args:
            query: A consulta do usuário.
            
        Returns:
            Lista de floats representando o embedding ou None em caso de erro.
        """
        logger.debug(f"Gerando embedding para query: '{query}'")
        
        try:
            # Implementação de retry para resiliência
            max_retries = self.embedding_retry_count
            retry_delay = self.embedding_retry_delay
            
            for retry in range(max_retries):
                try:
                    if self.embedding_provider == 'openai':
                        if self.provider == 'openai':
                            embedding_client = self.client
                            logger.debug("Usando cliente OpenAI existente para query")
                        else:
                            logger.debug("Obtendo novo cliente OpenAI para query")
                            embedding_client = get_llm_client('Embedding Generator')[0]
                        
                        logger.info(f"Chamando API OpenAI para gerar embedding para query (tentativa {retry+1})")
                        response = embedding_client.embeddings.create(
                            input=query,
                            model=self.embedding_model,
                            dimensions=self.embedding_dimension
                        )
                        embedding = response.data[0].embedding
                        logger.info(f"✓ Embedding gerado para query com tamanho {len(embedding)} (OpenAI)")
                        return embedding
                        
                    elif self.embedding_provider == 'groq':
                        if self.provider == 'groq':
                            embedding_client = self.client
                            logger.debug("Usando cliente Groq existente para query")
                        else:
                            logger.debug("Obtendo novo cliente Groq para query")
                            embedding_client = get_llm_client('Embedding Generator')[0]
                        
                        logger.info(f"Chamando API Groq para gerar embedding para query (tentativa {retry+1})")
                        response = embedding_client.embeddings.create(
                            input=query,
                            model=self.embedding_model,
                        )
                        embedding = response.data[0].embedding
                        logger.info(f"✓ Embedding gerado para query com tamanho {len(embedding)} (Groq)")
                        return embedding
                        
                    else:
                        logger.warning(f"Geração de embeddings não implementada para o provedor {self.embedding_provider}. Usando OpenAI como fallback.")
                        openai_client = get_llm_client('Embedding Generator')[0]
                        logger.info(f"Chamando API OpenAI (fallback) para gerar embedding para query (tentativa {retry+1})")
                        response = openai_client.embeddings.create(
                            input=query,
                            model="text-embedding-3-small",
                            dimensions=self.embedding_dimension
                        )
                        embedding = response.data[0].embedding
                        logger.info(f"✓ Embedding gerado com fallback para query com tamanho {len(embedding)} (OpenAI fallback)")
                        return embedding
                
                except Exception as e:
                    logger.warning(f"Tentativa {retry+1} falhou ao gerar embedding para query: {str(e)}")
                    if retry < max_retries - 1:
                        logger.info(f"Aguardando {retry_delay} segundos antes da próxima tentativa")
                        time.sleep(retry_delay)
                    else:
                        logger.error(f"Todas as {max_retries} tentativas falharam ao gerar embedding para query")
                        return None
                        
        except Exception as e:
            logger.error(f"Erro não tratado ao gerar embedding para query: {str(e)}")
            return None