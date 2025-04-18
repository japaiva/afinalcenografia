# services/rag/embedding_service.py

import logging
import time
from typing import List, Dict, Any, Optional
import json

from django.conf import settings
import openai
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
        logger.info(f"Inicializando EmbeddingService")
        self.agent_name = agent_name
        
        # Obter cliente LLM usando o utilitário
        try:
            self.client, self.model, self.temperature, self.system_prompt, self.task_instructions = get_llm_client(agent_name)
        except Exception as e:
            logger.error(f"Erro ao obter cliente LLM: {str(e)}")
            raise
        
        # Determinar o provider com base no cliente
        try:
            if hasattr(self.client, 'chat'):  # OpenAI
                self.provider = 'openai'
            elif hasattr(self.client, 'messages'):  # Anthropic
                self.provider = 'anthropic'
            elif hasattr(self.client, 'completion'):  # Groq
                self.provider = 'groq'
            else:
                # Fallback para o Assistente de Briefing se o Assistente RAG de Feiras não existir
                self.client, self.model, self.temperature, self.system_prompt, self.task_instructions = get_llm_client('Assistente de Briefing')
                
                # Tentar determinar o provider novamente
                if hasattr(self.client, 'chat'):
                    self.provider = 'openai'
                elif hasattr(self.client, 'messages'):
                    self.provider = 'anthropic'
                elif hasattr(self.client, 'completion'):
                    self.provider = 'groq'
                else:
                    error_msg = f"Não foi possível determinar o provedor do agente alternativo"
                    logger.error(error_msg)
                    raise ValueError(error_msg)
        except Exception as e:
            logger.error(f"Erro ao determinar provider: {str(e)}")
            raise
        
        # Obter parâmetros de embedding
        try:
            self.embedding_dimension = self._get_param_value('EMBEDDING_DIMENSION', 'embedding', 1536)
            self.embedding_model = self._get_param_value('EMBEDDING_MODEL', 'embedding', "text-embedding-ada-002")
            self.embedding_provider = self._get_param_value('EMBEDDING_PROVIDER', 'embedding', 'openai')
            self.embedding_retry_count = self._get_param_value('EMBEDDING_RETRY_COUNT', 'embedding', 3)
            self.embedding_retry_delay = self._get_param_value('EMBEDDING_RETRY_DELAY', 'embedding', 2)
            
            logger.info(f"Parâmetros de embedding: dimensão={self.embedding_dimension}, modelo={self.embedding_model}, provider={self.embedding_provider}")
        except Exception as e:
            logger.error(f"Erro ao obter parâmetros de embedding: {str(e)}")
            # Usar valores padrão em caso de erro
            self.embedding_dimension = 1536
            self.embedding_model = "text-embedding-ada-002"
            self.embedding_provider = 'openai'
            self.embedding_retry_count = 3
            self.embedding_retry_delay = 2
            logger.info(f"Usando parâmetros padrão de embedding: dimensão={self.embedding_dimension}, modelo={self.embedding_model}, provider={self.embedding_provider}")
    
    def _get_dedicated_openai_client(self):
        """
        Cria um novo cliente OpenAI dedicado para embeddings,
        utilizando a chave API das configurações.
        """
        try:
            api_key = settings.OPENAI_API_KEY
            logger.info(f"[DIAGNÓSTICO] Criando cliente OpenAI com API key (primeiros 5 chars): {api_key[:5]}...")
            client = openai.OpenAI(api_key=api_key)
            return client
        except Exception as e:
            logger.error(f"[DIAGNÓSTICO] ✗ Erro ao criar cliente OpenAI dedicado: {str(e)}")
            return None
    
    def _get_param_value(self, nome, categoria, default):
        """Obtém o valor de um parâmetro de indexação, com fallback para valor padrão."""
        try:
            param = ParametroIndexacao.objects.get(nome=nome, categoria=categoria)
            valor = param.valor_convertido()
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
        logger.info(f"[DIAGNÓSTICO] Gerando embedding para QA {qa.id}")
        
        try:
            # Preparando similar_questions
            similar_questions = qa.similar_questions if qa.similar_questions else []
            if isinstance(similar_questions, str):
                try:
                    similar_questions = json.loads(similar_questions)
                except Exception as e:
                    similar_questions = similar_questions.split(',')
            
            # Concatenar informações
            embedding_text = f"Pergunta: {qa.question} "
            embedding_text += f"Resposta: {qa.answer} "
            embedding_text += f"Contexto: {qa.context} "
            
            if similar_questions:
                sq_text = " ".join([f"Pergunta similar: {sq}" for sq in similar_questions])
                embedding_text += sq_text
            
            logger.info(f"[DIAGNÓSTICO] Texto para embedding (primeiros 100 chars): {embedding_text[:100]}...")
            
            # Implementação de retry para resiliência
            for retry in range(self.embedding_retry_count):
                try:
                    # Gerar embedding usando o provedor específico de embeddings
                    if self.embedding_provider == 'openai':
                        # Usar um cliente dedicado para embeddings
                        embedding_client = self._get_dedicated_openai_client()
                        
                        if not embedding_client:
                            logger.error(f"[DIAGNÓSTICO] ✗ Falha ao criar cliente dedicado. Tentativa {retry+1}")
                            continue
                        
                        # Verificar se o modelo é válido e, em caso de falha, usar um fallback
                        try:
                            logger.info(f"[DIAGNÓSTICO] Chamando API OpenAI para gerar embedding (modelo: {self.embedding_model})")
                            response = embedding_client.embeddings.create(
                                input=embedding_text,
                                model=self.embedding_model
                            )
                            embedding = response.data[0].embedding
                            logger.info(f"[DIAGNÓSTICO] ✓ Embedding gerado para QA {qa.id} (tamanho: {len(embedding)})")
                            return embedding
                        except Exception as e:
                            # Tentar com modelo de fallback
                            fallback_model = "text-embedding-ada-002"
                            logger.warning(f"[DIAGNÓSTICO] ✗ Erro com modelo {self.embedding_model}: {str(e)}. Usando fallback: {fallback_model}")
                            
                            response = embedding_client.embeddings.create(
                                input=embedding_text,
                                model=fallback_model
                            )
                            embedding = response.data[0].embedding
                            logger.info(f"[DIAGNÓSTICO] ✓ Embedding gerado para QA {qa.id} com modelo fallback (tamanho: {len(embedding)})")
                            return embedding
                        
                    elif self.embedding_provider == 'groq':
                        if self.provider == 'groq':
                            embedding_client = self.client
                        else:
                            embedding_client = get_llm_client('Embedding Generator')[0]
                        
                        logger.info(f"[DIAGNÓSTICO] Chamando API Groq para gerar embedding")
                        response = embedding_client.embeddings.create(
                            input=embedding_text,
                            model=self.embedding_model,
                        )
                        embedding = response.data[0].embedding
                        logger.info(f"[DIAGNÓSTICO] ✓ Embedding gerado para QA {qa.id} (tamanho: {len(embedding)})")
                        return embedding
                        
                    else:
                        # Usar OpenAI como fallback
                        logger.warning(f"[DIAGNÓSTICO] Provider {self.embedding_provider} não suportado diretamente. Usando OpenAI como fallback.")
                        embedding_client = self._get_dedicated_openai_client()
                        if not embedding_client:
                            logger.error(f"[DIAGNÓSTICO] ✗ Falha ao criar cliente dedicado para fallback. Tentativa {retry+1}")
                            continue
                        
                        # Usar modelo mais seguro para fallback
                        fallback_model = "text-embedding-ada-002"
                        
                        response = embedding_client.embeddings.create(
                            input=embedding_text,
                            model=fallback_model,
                            dimension=self.embedding_dimension
                        )
                        embedding = response.data[0].embedding
                        logger.info(f"[DIAGNÓSTICO] ✓ Embedding gerado com fallback para QA {qa.id} (tamanho: {len(embedding)})")
                        return embedding
                
                except Exception as e:
                    logger.warning(f"[DIAGNÓSTICO] ✗ Tentativa {retry+1} falhou para QA {qa.id}: {str(e)}")
                    
                    if retry < self.embedding_retry_count - 1:
                        logger.info(f"[DIAGNÓSTICO] Aguardando {self.embedding_retry_delay} segundos antes da próxima tentativa...")
                        time.sleep(self.embedding_retry_delay)
                    else:
                        logger.error(f"[DIAGNÓSTICO] ✗ Todas as {self.embedding_retry_count} tentativas falharam para QA {qa.id}")
                        return None
                        
        except Exception as e:
            logger.error(f"[DIAGNÓSTICO] ✗ Erro não tratado ao gerar embedding para QA {qa.id}: {str(e)}")
            return None
    
    def gerar_embedding_consulta(self, query: str) -> Optional[List[float]]:
        """
        Gera embedding para uma consulta.
        
        Args:
            query: A consulta do usuário.
            
        Returns:
            Lista de floats representando o embedding ou None em caso de erro.
        """
        logger.info(f"[DIAGNÓSTICO CONSULTA] Gerando embedding para consulta: '{query}'")
        
        try:
            # Implementação de retry para resiliência
            max_retries = self.embedding_retry_count
            retry_delay = self.embedding_retry_delay
            
            for retry in range(max_retries):
                try:
                    if self.embedding_provider == 'openai':
                        # Usar um cliente dedicado para embeddings
                        embedding_client = self._get_dedicated_openai_client()
                        
                        if not embedding_client:
                            logger.error(f"[DIAGNÓSTICO CONSULTA] ✗ Falha ao criar cliente dedicado para consulta. Tentativa {retry+1}")
                            continue
                        
                        # Verificar se o modelo é válido e, em caso de falha, usar um fallback
                        try:
                            logger.info(f"[DIAGNÓSTICO CONSULTA] Chamando API OpenAI para consulta (modelo: {self.embedding_model})")
                            response = embedding_client.embeddings.create(
                                input=query,
                                model=self.embedding_model
                            )
                            embedding = response.data[0].embedding
                            logger.info(f"[DIAGNÓSTICO CONSULTA] ✓ Embedding gerado para consulta (tamanho: {len(embedding)})")
                            
                            # Log para os primeiros 5 valores do embedding para diagnóstico
                            logger.info(f"[DIAGNÓSTICO CONSULTA] Amostra do embedding: {embedding[:5]}")
                            
                            return embedding
                        except Exception as e:
                            # Tentar com modelo de fallback
                            fallback_model = "text-embedding-ada-002"
                            logger.warning(f"[DIAGNÓSTICO CONSULTA] ✗ Erro com modelo {self.embedding_model}: {str(e)}. Usando fallback: {fallback_model}")
                            
                            response = embedding_client.embeddings.create(
                                input=query,
                                model=fallback_model
                            )
                            embedding = response.data[0].embedding
                            logger.info(f"[DIAGNÓSTICO CONSULTA] ✓ Embedding gerado para consulta com modelo fallback (tamanho: {len(embedding)})")
                            
                            # Log para os primeiros 5 valores do embedding para diagnóstico
                            logger.info(f"[DIAGNÓSTICO CONSULTA] Amostra do embedding: {embedding[:5]}")
                            
                            return embedding
                        
                    elif self.embedding_provider == 'groq':
                        if self.provider == 'groq':
                            embedding_client = self.client
                        else:
                            embedding_client = get_llm_client('Embedding Generator')[0]
                        
                        logger.info(f"[DIAGNÓSTICO CONSULTA] Chamando API Groq para consulta")
                        response = embedding_client.embeddings.create(
                            input=query,
                            model=self.embedding_model,
                        )
                        embedding = response.data[0].embedding
                        logger.info(f"[DIAGNÓSTICO CONSULTA] ✓ Embedding gerado para consulta (tamanho: {len(embedding)})")
                        
                        # Log para os primeiros 5 valores do embedding para diagnóstico
                        logger.info(f"[DIAGNÓSTICO CONSULTA] Amostra do embedding: {embedding[:5]}")
                        
                        return embedding
                        
                    else:
                        # Usar OpenAI como fallback
                        logger.warning(f"[DIAGNÓSTICO CONSULTA] Provider {self.embedding_provider} não suportado diretamente. Usando OpenAI como fallback.")
                        embedding_client = self._get_dedicated_openai_client()
                        if not embedding_client:
                            logger.error(f"[DIAGNÓSTICO CONSULTA] ✗ Falha ao criar cliente dedicado para consulta fallback. Tentativa {retry+1}")
                            continue
                        
                        # Usar modelo mais seguro para fallback
                        fallback_model = "text-embedding-ada-002"
                        
                        response = embedding_client.embeddings.create(
                            input=query,
                            model=fallback_model,
                            dimension=self.embedding_dimension
                        )
                        embedding = response.data[0].embedding
                        logger.info(f"[DIAGNÓSTICO CONSULTA] ✓ Embedding gerado com fallback para consulta (tamanho: {len(embedding)})")
                        
                        # Log para os primeiros 5 valores do embedding para diagnóstico
                        logger.info(f"[DIAGNÓSTICO CONSULTA] Amostra do embedding: {embedding[:5]}")
                        
                        return embedding
            
                except Exception as e:
                    logger.warning(f"[DIAGNÓSTICO CONSULTA] ✗ Tentativa {retry+1} falhou ao gerar embedding para consulta: {str(e)}")
                    
                    if retry < max_retries - 1:
                        logger.info(f"[DIAGNÓSTICO CONSULTA] Aguardando {retry_delay} segundos antes da próxima tentativa...")
                        time.sleep(retry_delay)
                    else:
                        logger.error(f"[DIAGNÓSTICO CONSULTA] ✗ Todas as {max_retries} tentativas falharam ao gerar embedding para consulta")
                        return None
                    
        except Exception as e:
            logger.error(f"[DIAGNÓSTICO CONSULTA] ✗ Erro não tratado ao gerar embedding para consulta: {str(e)}")
            return None