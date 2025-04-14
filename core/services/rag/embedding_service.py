# core/services/rag/embedding_service.py

import logging
import time
from typing import List, Dict, Any, Optional
import json

from django.conf import settings
# Importar OpenAI uma vez no início do arquivo
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
            # Usando modelo mais antigo e confiável como padrão
            self.embedding_model = self._get_param_value('EMBEDDING_MODEL', 'embedding', "text-embedding-ada-002")
            self.embedding_provider = self._get_param_value('EMBEDDING_PROVIDER', 'embedding', 'openai')
            self.embedding_retry_count = self._get_param_value('EMBEDDING_RETRY_COUNT', 'embedding', 3)
            self.embedding_retry_delay = self._get_param_value('EMBEDDING_RETRY_DELAY', 'embedding', 2)
            
            logger.info(f"✓ Parâmetros de embedding configurados: Dimensão={self.embedding_dimension}, Modelo={self.embedding_model}, Provider={self.embedding_provider}")
            
            # Log dos valores de parâmetros da tabela para diagnóstico
            all_params = ParametroIndexacao.objects.filter(categoria='embedding')
            for param in all_params:
                logger.info(f"[DEBUG-EMB] Parâmetro embedding na tabela: {param.nome} = {param.valor_convertido()}")
                
        except Exception as e:
            logger.error(f"Erro ao obter parâmetros de embedding: {str(e)}")
            # Usar valores padrão em caso de erro
            self.embedding_dimension = 1536
            self.embedding_model = "text-embedding-ada-002"  # Usando modelo mais antigo como padrão
            self.embedding_provider = 'openai'
            self.embedding_retry_count = 3
            self.embedding_retry_delay = 2
            logger.info(f"✓ Usando valores padrão para parâmetros de embedding após erro: Dimensão={self.embedding_dimension}, Modelo={self.embedding_model}")
    
    def _get_dedicated_openai_client(self):
        """
        Cria um novo cliente OpenAI dedicado para embeddings,
        utilizando a chave API das configurações.
        """
        try:
            client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
            # Verificar se temos uma API key válida
            if hasattr(client, 'api_key') and client.api_key:
                key_prefix = client.api_key[:4] if len(client.api_key) > 8 else "****"
                key_suffix = client.api_key[-4:] if len(client.api_key) > 8 else "****"
                logger.debug(f"[DEBUG-EMB] Cliente dedicado usando API key: {key_prefix}...{key_suffix}")
                
                # Validação extra para garantir que é uma API key OpenAI válida
                if not client.api_key.startswith('sk-'):
                    logger.warning(f"[DEBUG-EMB] A API key não parece ser uma chave OpenAI válida (não começa com 'sk-')")
            return client
        except Exception as e:
            logger.error(f"[DEBUG-EMB] Erro ao criar cliente OpenAI dedicado: {str(e)}")
            return None
    
    def _get_param_value(self, nome, categoria, default):
        """Obtém o valor de um parâmetro de indexação, com fallback para valor padrão."""
        logger.debug(f"Obtendo parâmetro '{nome}' da categoria '{categoria}'")
        try:
            param = ParametroIndexacao.objects.get(nome=nome, categoria=categoria)
            valor = param.valor_convertido()
            logger.debug(f"✓ Parâmetro '{nome}' encontrado com valor: {valor}")
            
            # Se for o modelo de embedding, verificar se é o problemático
            if nome == 'EMBEDDING_MODEL' and valor == 'text-embedding-3-small':
                logger.warning(f"Modelo problemático detectado na tabela, usando fallback: text-embedding-ada-002")
                return "text-embedding-ada-002"
                
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
            
            # NOVOS LOGS: Verificar configuração antes da chamada
            logger.info(f"[DEBUG-EMB] Provider determinado: {self.provider}")
            logger.info(f"[DEBUG-EMB] Embedding provider configurado: {self.embedding_provider}")
            logger.info(f"[DEBUG-EMB] Embedding model configurado: {self.embedding_model}")
            logger.info(f"[DEBUG-EMB] Embedding dimension configurado: {self.embedding_dimension}")
            
            # Implementação de retry para resiliência
            for retry in range(self.embedding_retry_count):
                try:
                    # Gerar embedding usando o provedor específico de embeddings
                    if self.embedding_provider == 'openai':
                        # MUDANÇA PRINCIPAL: Sempre usar um cliente dedicado para embeddings
                        embedding_client = self._get_dedicated_openai_client()
                        logger.debug(f"Usando cliente OpenAI dedicado para QA {qa.id}")
                        
                        if not embedding_client:
                            logger.error(f"[DEBUG-EMB] Falha ao criar cliente dedicado para embedding. Tentativa {retry+1}")
                            continue
                        
                        # Verificar API key (de forma segura, mostrando apenas o início e o fim)
                        try:
                            if hasattr(embedding_client, 'api_key') and embedding_client.api_key:
                                key_prefix = embedding_client.api_key[:4] if len(embedding_client.api_key) > 8 else "****"
                                key_suffix = embedding_client.api_key[-4:] if len(embedding_client.api_key) > 8 else "****"
                                logger.info(f"[DEBUG-EMB] Usando API key: {key_prefix}...{key_suffix}")
                        except Exception as e:
                            logger.warning(f"[DEBUG-EMB] Erro ao tentar verificar API key: {str(e)}")
                        
                        # NOVO LOG: Mostrar o modelo exato que será usado
                        logger.info(f"[DEBUG-EMB] Tentando chamada OpenAI com modelo: {self.embedding_model}")
                        
                        # NOVA VERIFICAÇÃO: Tentar listar modelos disponíveis
                        try:
                            models = embedding_client.models.list()
                            available_models = [model.id for model in models.data]
                            embedding_models = [m for m in available_models if 'embedding' in m]
                            logger.info(f"[DEBUG-EMB] Modelos de embedding disponíveis: {embedding_models}")
                            
                            # Verificar se o modelo solicitado está disponível
                            if not embedding_models or self.embedding_model not in embedding_models:
                                fallback_model = "text-embedding-ada-002"
                                logger.info(f"[DEBUG-EMB] Modelo {self.embedding_model} não disponível na lista. Usando fallback: {fallback_model}")
                                
                                # Usar modelo de fallback
                                logger.info(f"[DEBUG-EMB] Tentando chamada OpenAI com modelo fallback: {fallback_model}")
                                response = embedding_client.embeddings.create(
                                    input=embedding_text,
                                    model=fallback_model
                                )
                                embedding = response.data[0].embedding
                                logger.info(f"✓ Embedding gerado para QA {qa.id} com tamanho {len(embedding)} (OpenAI fallback model)")
                                return embedding
                        except Exception as e:
                            logger.warning(f"[DEBUG-EMB] Não foi possível listar modelos: {str(e)}")
                            # Tentativa de usar fallback após exceção na listagem
                            fallback_model = "text-embedding-ada-002"
                            logger.info(f"[DEBUG-EMB] Após erro na listagem, tentando modelo fallback: {fallback_model}")
                            
                            try:
                                response = embedding_client.embeddings.create(
                                    input=embedding_text,
                                    model=fallback_model
                                )
                                embedding = response.data[0].embedding
                                logger.info(f"✓ Embedding gerado para QA {qa.id} com tamanho {len(embedding)} (OpenAI fallback model após erro)")
                                return embedding
                            except Exception as nested_e:
                                logger.error(f"[DEBUG-EMB] Fallback também falhou: {str(nested_e)}")
                                # Continuar para próxima tentativa
                        
                        # Se não entrou em nenhum fallback, tenta com o modelo configurado
                        logger.info(f"Chamando API OpenAI para gerar embedding para QA {qa.id} (tentativa {retry+1})")
                        response = embedding_client.embeddings.create(
                            input=embedding_text,
                            model=self.embedding_model
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
                        
                        # NOVO LOG: Mostrar o modelo exato que será usado
                        logger.info(f"[DEBUG-EMB] Tentando chamada Groq com modelo: {self.embedding_model}")
                        
                        logger.info(f"Chamando API Groq para gerar embedding para QA {qa.id} (tentativa {retry+1})")
                        response = embedding_client.embeddings.create(
                            input=embedding_text,
                            model=self.embedding_model,
                        )
                        embedding = response.data[0].embedding
                        logger.info(f"✓ Embedding gerado para QA {qa.id} com tamanho {len(embedding)} (Groq)")
                        return embedding
                        
                    else:
                        # NOVO LOG: Mostrar que está usando fallback
                        logger.warning(f"[DEBUG-EMB] Geração de embeddings não implementada para o provedor {self.embedding_provider}. Usando OpenAI como fallback.")
                        
                        # Criar um cliente OpenAI dedicado para fallback
                        embedding_client = self._get_dedicated_openai_client()
                        if not embedding_client:
                            logger.error(f"[DEBUG-EMB] Falha ao criar cliente dedicado para fallback. Tentativa {retry+1}")
                            continue
                        
                        logger.info(f"Chamando API OpenAI (fallback) para gerar embedding para QA {qa.id} (tentativa {retry+1})")
                        
                        # Usar modelo mais seguro e antigo para fallback
                        fallback_model = "text-embedding-ada-002"
                        logger.info(f"[DEBUG-EMB] Tentando chamada OpenAI fallback com modelo: {fallback_model}")
                        
                        response = embedding_client.embeddings.create(
                            input=embedding_text,
                            model=fallback_model,
                            dimension=self.embedding_dimension
                        )
                        embedding = response.data[0].embedding
                        logger.info(f"✓ Embedding gerado com fallback para QA {qa.id} com tamanho {len(embedding)} (OpenAI fallback)")
                        return embedding
                
                except Exception as e:
                    logger.warning(f"Tentativa {retry+1} falhou para QA {qa.id}: {str(e)}")
                    # NOVO LOG: Adicionar detalhes do erro
                    logger.error(f"[DEBUG-EMB] Detalhes do erro na tentativa {retry+1}: {type(e).__name__}: {str(e)}")
                    
                    if retry < self.embedding_retry_count - 1:
                        logger.info(f"Aguardando {self.embedding_retry_delay} segundos antes da próxima tentativa para QA {qa.id}")
                        time.sleep(self.embedding_retry_delay)
                    else:
                        logger.error(f"Todas as {self.embedding_retry_count} tentativas falharam para QA {qa.id}")
                        return None
                        
        except Exception as e:
            logger.error(f"Erro não tratado ao gerar embedding para QA {qa.id}: {str(e)}")
            # NOVO LOG: Adicionar detalhes do erro
            logger.error(f"[DEBUG-EMB] Detalhes do erro não tratado: {type(e).__name__}: {str(e)}")
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
        
        # NOVOS LOGS: Verificar configuração antes da chamada
        logger.info(f"[DEBUG-EMB] Provider para consulta: {self.provider}")
        logger.info(f"[DEBUG-EMB] Embedding provider para consulta: {self.embedding_provider}")
        logger.info(f"[DEBUG-EMB] Embedding model para consulta: {self.embedding_model}")
        
        try:
            # Implementação de retry para resiliência
            max_retries = self.embedding_retry_count
            retry_delay = self.embedding_retry_delay
            
            for retry in range(max_retries):
                try:
                    if self.embedding_provider == 'openai':
                        # MUDANÇA PRINCIPAL: Sempre usar um cliente dedicado para embeddings
                        embedding_client = self._get_dedicated_openai_client()
                        logger.debug("Usando cliente OpenAI dedicado para query")
                        
                        if not embedding_client:
                            logger.error(f"[DEBUG-EMB] Falha ao criar cliente dedicado para query. Tentativa {retry+1}")
                            continue
                        
                        # Verificar API key (de forma segura)
                        try:
                            if hasattr(embedding_client, 'api_key') and embedding_client.api_key:
                                key_prefix = embedding_client.api_key[:4] if len(embedding_client.api_key) > 8 else "****"
                                key_suffix = embedding_client.api_key[-4:] if len(embedding_client.api_key) > 8 else "****"
                                logger.info(f"[DEBUG-EMB] Cliente de query usando API key: {key_prefix}...{key_suffix}")
                        except Exception as e:
                            logger.warning(f"[DEBUG-EMB] Erro ao verificar API key do cliente de query: {str(e)}")
                        
                        # NOVO LOG: Mostrar o modelo exato que será usado
                        logger.info(f"[DEBUG-EMB] Tentando chamada OpenAI para query com modelo: {self.embedding_model}")
                        
                        # Verificar modelos disponíveis
                        try:
                            models = embedding_client.models.list()
                            available_models = [model.id for model in models.data]
                            embedding_models = [m for m in available_models if 'embedding' in m]
                            logger.info(f"[DEBUG-EMB] Modelos de embedding disponíveis para query: {embedding_models}")
                            
                            # Verificar se o modelo solicitado está disponível
                            if not embedding_models or self.embedding_model not in embedding_models:
                                fallback_model = "text-embedding-ada-002"
                                logger.info(f"[DEBUG-EMB] Modelo {self.embedding_model} não disponível para query. Usando fallback: {fallback_model}")
                                
                                # Usar modelo de fallback
                                response = embedding_client.embeddings.create(
                                    input=query,
                                    model=fallback_model
                                )
                                embedding = response.data[0].embedding
                                logger.info(f"✓ Embedding gerado para query com tamanho {len(embedding)} (OpenAI fallback model)")
                                return embedding
                        except Exception as e:
                            logger.warning(f"[DEBUG-EMB] Não foi possível listar modelos para query: {str(e)}")
                            # Tentar fallback após erro na listagem
                            fallback_model = "text-embedding-ada-002"
                            logger.info(f"[DEBUG-EMB] Após erro na listagem para query, tentando modelo fallback: {fallback_model}")
                            
                            try:
                                response = embedding_client.embeddings.create(
                                    input=query,
                                    model=fallback_model
                                )
                                embedding = response.data[0].embedding
                                logger.info(f"✓ Embedding gerado para query com tamanho {len(embedding)} (OpenAI fallback model após erro)")
                                return embedding
                            except Exception as nested_e:
                                logger.error(f"[DEBUG-EMB] Fallback para query também falhou: {str(nested_e)}")
                                # Continuar para próxima tentativa
                        
                        # Se não entrou em nenhum fallback, tenta com o modelo configurado
                        logger.info(f"Chamando API OpenAI para gerar embedding para query (tentativa {retry+1})")
                        response = embedding_client.embeddings.create(
                            input=query,
                            model=self.embedding_model
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
                        
                        # NOVO LOG: Mostrar o modelo exato que será usado
                        logger.info(f"[DEBUG-EMB] Tentando chamada Groq para query com modelo: {self.embedding_model}")
                        
                        logger.info(f"Chamando API Groq para gerar embedding para query (tentativa {retry+1})")
                        response = embedding_client.embeddings.create(
                            input=query,
                            model=self.embedding_model,
                        )
                        embedding = response.data[0].embedding
                        logger.info(f"✓ Embedding gerado para query com tamanho {len(embedding)} (Groq)")
                        return embedding
                        
                    else:
                        # NOVO LOG: Mostrar que está usando fallback
                        logger.warning(f"[DEBUG-EMB] Geração de embeddings para query não implementada para o provedor {self.embedding_provider}. Usando OpenAI como fallback.")
                        
                        # Usar cliente dedicado para fallback
                        embedding_client = self._get_dedicated_openai_client()
                        if not embedding_client:
                            logger.error(f"[DEBUG-EMB] Falha ao criar cliente dedicado para query fallback. Tentativa {retry+1}")
                            continue
                        
                        logger.info(f"Chamando API OpenAI (fallback) para gerar embedding para query (tentativa {retry+1})")
                        
                        # Usar modelo mais seguro para fallback
                        fallback_model = "text-embedding-ada-002"
                        logger.info(f"[DEBUG-EMB] Tentando chamada OpenAI fallback para query com modelo: {fallback_model}")
                        
                        response = embedding_client.embeddings.create(
                            input=query,
                            model=fallback_model,
                            dimension=self.embedding_dimension
                        )
                        embedding = response.data[0].embedding
                        logger.info(f"✓ Embedding gerado com fallback para query com tamanho {len(embedding)} (OpenAI fallback)")
                        return embedding
            
                except Exception as e:
                    logger.warning(f"Tentativa {retry+1} falhou ao gerar embedding para query: {str(e)}")
                    # NOVO LOG: Adicionar detalhes do erro
                    logger.error(f"[DEBUG-EMB] Detalhes do erro na tentativa {retry+1} para query: {type(e).__name__}: {str(e)}")
                    
                    if retry < max_retries - 1:
                        logger.info(f"Aguardando {retry_delay} segundos antes da próxima tentativa")
                        time.sleep(retry_delay)
                    else:
                        logger.error(f"Todas as {max_retries} tentativas falharam ao gerar embedding para query")
                        return None
                    
        except Exception as e:
            logger.error(f"Erro não tratado ao gerar embedding para query: {str(e)}")
            # NOVO LOG: Adicionar detalhes do erro
            logger.error(f"[DEBUG-EMB] Detalhes do erro não tratado para query: {type(e).__name__}: {str(e)}")
            return None