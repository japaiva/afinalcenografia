# core/services/rag_service.py
import os
import json
import logging
from typing import List, Dict, Any, Optional
import numpy as np
from django.conf import settings
from django.db.models import Q

from core.models import Feira, FeiraManualQA, ParametroIndexacao, Agente
from core.utils.llm_utils import get_llm_client
from core.utils.pinecone_utils import upsert_vectors, query_vectors

logger = logging.getLogger(__name__)

class RAGService:
    """
    Serviço para integrar os pares QA com o sistema RAG existente.
    """
    
    def __init__(self, agent_name='Assistente RAG de Feiras'):
        """
        Inicializa o serviço RAG.
        
        Args:
            agent_name: Nome do agente configurado a ser utilizado
        """
        self.agent_name = agent_name
        
        # Obter cliente LLM usando o utilitário
        self.client, self.model, self.temperature, self.system_prompt = get_llm_client(agent_name)
        
        # Determinar o provider com base no cliente
        if hasattr(self.client, 'chat'):  # OpenAI
            self.provider = 'openai'
        elif hasattr(self.client, 'messages'):  # Anthropic
            self.provider = 'anthropic'
        elif hasattr(self.client, 'completion'):  # Groq
            self.provider = 'groq'
        else:
            logger.warning(f"Não foi possível determinar o provedor do agente '{agent_name}'. Tentando usar agente alternativo 'Assistente de Briefing'")
            # Fallback para o Assistente de Briefing se o Assistente RAG de Feiras não existir
            self.client, self.model, self.temperature, self.system_prompt = get_llm_client('Assistente de Briefing')
            
            # Tentar determinar o provider novamente
            if hasattr(self.client, 'chat'):
                self.provider = 'openai'
            elif hasattr(self.client, 'messages'):
                self.provider = 'anthropic'
            elif hasattr(self.client, 'completion'):
                self.provider = 'groq'
            else:
                raise ValueError(f"Não foi possível determinar o provedor do agente alternativo")
        
        # Obter parâmetros de embedding
        self.embedding_dimension = self._get_param_value('EMBEDDING_DIMENSION', 'embedding', 1536)
        self.embedding_model = self._get_param_value('EMBEDDING_MODEL', 'embedding', "text-embedding-3-small")
        
        # Obter o provedor específico para embeddings (pode ser diferente do provedor LLM)
        self.embedding_provider = self._get_param_value('EMBEDDING_PROVIDER', 'embedding', 'openai')
    
    def _get_param_value(self, nome, categoria, default):
        """Obtém o valor de um parâmetro de indexação, com fallback para valor padrão"""
        try:
            param = ParametroIndexacao.objects.get(nome=nome, categoria=categoria)
            return param.valor_convertido()
        except ParametroIndexacao.DoesNotExist:
            logger.warning(f"Parâmetro '{nome}' não encontrado. Usando valor padrão: {default}")
            return default
    
    def gerar_embeddings_qa(self, qa: FeiraManualQA) -> Optional[List[float]]:
        """
        Gera embeddings para um par QA específico.
        
        Args:
            qa: O par QA para o qual gerar embeddings.
            
        Returns:
            Lista de floats representando o embedding ou None em caso de erro.
        """
        try:
            # Construir o texto para o embedding
            similar_questions = qa.similar_questions if qa.similar_questions else []
            if isinstance(similar_questions, str):
                # Garantir que é uma lista
                try:
                    similar_questions = json.loads(similar_questions)
                except:
                    similar_questions = similar_questions.split(',')
            
            # Concatenar todas as informações do QA
            embedding_text = f"Pergunta: {qa.question} "
            embedding_text += f"Resposta: {qa.answer} "
            embedding_text += f"Contexto: {qa.context} "
            
            if similar_questions:
                sq_text = " ".join([f"Pergunta similar: {sq}" for sq in similar_questions])
                embedding_text += sq_text
            
            # Gerar embedding usando o provedor específico de embeddings
            if self.embedding_provider == 'openai':
                # Usar cliente OpenAI para embeddings
                # Verificar se o cliente atual é OpenAI para reutilizar
                if self.provider == 'openai':
                    embedding_client = self.client
                else:
                    # Obter cliente OpenAI específico para embeddings
                    embedding_client = get_llm_client('Embedding Generator')[0]
                
                response = embedding_client.embeddings.create(
                    input=embedding_text,
                    model=self.embedding_model,
                    dimensions=self.embedding_dimension
                )
                
                # Extrair o embedding da resposta
                embedding = response.data[0].embedding
                return embedding
                
            elif self.embedding_provider == 'groq':
                # Usar cliente Groq para embeddings
                # Verificar se o cliente atual é Groq para reutilizar
                if self.provider == 'groq':
                    embedding_client = self.client
                else:
                    # Obter cliente Groq específico para embeddings
                    embedding_client = get_llm_client('Embedding Generator')[0]
                
                response = embedding_client.embeddings.create(
                    input=embedding_text,
                    model=self.embedding_model,
                )
                embedding = response.data[0].embedding
                return embedding
                
            else:
                logger.warning(f"Geração de embeddings não implementada para o provedor {self.embedding_provider}")
                # Fallback para OpenAI como provedor de embeddings
                openai_client = get_llm_client('Embedding Generator')[0]
                response = openai_client.embeddings.create(
                    input=embedding_text,
                    model="text-embedding-3-small",
                    dimensions=self.embedding_dimension
                )
                embedding = response.data[0].embedding
                return embedding
                
        except Exception as e:
            logger.error(f"Erro ao gerar embedding para QA {qa.id}: {str(e)}")
            return None
    
    def atualizar_embeddings_feira(self, feira_id: int) -> Dict[str, Any]:
        """
        Atualiza todos os embeddings dos QA de uma feira.
        
        Args:
            feira_id: ID da feira.
            
        Returns:
            Dicionário com resultados da atualização.
        """
        try:
            feira = Feira.objects.get(pk=feira_id)
            qa_pairs = FeiraManualQA.objects.filter(feira=feira)
            
            if not qa_pairs.exists():
                return {
                    'status': 'error',
                    'message': 'Nenhum par QA encontrado para esta feira'
                }
            
            total = qa_pairs.count()
            successes = 0
            errors = 0
            
            # Obter parâmetros de atraso para evitar limites de API
            qa_delay = self._get_param_value('QA_DELAY', 'qa', 2)
            
            for qa in qa_pairs:
                try:
                    # Gerar embedding
                    embedding = self.gerar_embeddings_qa(qa)
                    
                    if embedding:
                        # Armazenar no banco de dados vetorial
                        self._store_in_vector_db(qa, embedding)
                        
                        # Atualizar metadados no QA
                        qa.embedding_id = f"qa_{qa.id}"  # ID do embedding no seu banco de vetores
                        qa.save(update_fields=['embedding_id'])
                        
                        successes += 1
                    else:
                        errors += 1
                        
                except Exception as e:
                    logger.error(f"Erro ao processar QA {qa.id}: {str(e)}")
                    errors += 1
            
            return {
                'status': 'success',
                'message': f'Embeddings atualizados: {successes} de {total} QA',
                'total': total,
                'successful': successes,
                'errors': errors
            }
            
        except Feira.DoesNotExist:
            return {
                'status': 'error',
                'message': f'Feira com ID {feira_id} não encontrada'
            }
        except Exception as e:
            logger.error(f"Erro ao atualizar embeddings da feira {feira_id}: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def _store_in_vector_db(self, qa: FeiraManualQA, embedding: List[float]) -> bool:
        """
        Armazena um embedding no banco de dados vetorial.
        
        Args:
            qa: O par QA associado ao embedding.
            embedding: O embedding vetorial.
            
        Returns:
            True se armazenado com sucesso, False caso contrário.
        """
        try:
            # Obter parâmetros do banco vetorial
            vector_provider = self._get_param_value('VECTOR_DB_PROVIDER', 'connection', 'pinecone')
            
            # Implementação para Pinecone
            if vector_provider.lower() == 'pinecone':
                # Obter namespace - usando o padrão "feira_{id}"
                namespace = f"feira_{qa.feira.id}"
                
                # Metadados para o vetor
                metadata = {
                    'q': qa.question,
                    'a': qa.answer,
                    't': qa.context,
                    'sq': qa.similar_questions,
                    'feira_id': str(qa.feira.id),
                    'feira_nome': qa.feira.nome,
                    'qa_id': str(qa.id)
                }
                
                # Usar o utilitário para upsert
                upsert_vectors([(f"qa_{qa.id}", embedding, metadata)], namespace)
                
                return True
            
            # Se não tiver configuração de banco vetorial, apenas logar
            logger.info(f"Embedding gerado para QA {qa.id}, mas nenhum banco vetorial configurado")
            return False
            
        except Exception as e:
            logger.error(f"Erro ao armazenar no banco vetorial: {str(e)}")
            return False
    
    def pesquisar_qa(self, query: str, feira_id: Optional[int] = None, top_k: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Pesquisa QA relevantes para uma consulta.
        
        Args:
            query: A consulta do usuário.
            feira_id: ID opcional da feira para restringir a busca.
            top_k: Número máximo de resultados.
            
        Returns:
            Lista de pares QA relevantes com scores.
        """
        try:
            # Obter parâmetro top_k se não foi fornecido
            if top_k is None:
                top_k = self._get_param_value('SEARCH_TOP_K', 'search', 3)
            
            # Obter threshold de similaridade
            similarity_threshold = self._get_param_value('SEARCH_THRESHOLD', 'search', 0.7)
            
            # Gerar embedding para a consulta
            query_embedding = self._get_query_embedding(query)
            
            if not query_embedding:
                return []
            
            # Buscar no banco vetorial
            namespace = f"feira_{feira_id}" if feira_id else None
            filter_obj = {"feira_id": {"$eq": str(feira_id)}} if feira_id else None
            
            results = query_vectors(query_embedding, namespace, top_k, filter_obj)
            
            # Filtrar resultados abaixo do threshold
            filtered_results = []
            for result in results:
                if result['score'] >= similarity_threshold:
                    # Criar um dicionário com os dados do resultado
                    formatted_result = {
                        'id': result['id'],
                        'score': result['score'],
                        'question': result['metadata'].get('q', ''),
                        'answer': result['metadata'].get('a', ''),
                        'context': result['metadata'].get('t', ''),
                        'similar_questions': result['metadata'].get('sq', []),
                        'feira_id': result['metadata'].get('feira_id', ''),
                        'feira_nome': result['metadata'].get('feira_nome', ''),
                        'qa_id': result['metadata'].get('qa_id', '')
                    }
                    filtered_results.append(formatted_result)
            
            return filtered_results
            
        except Exception as e:
            logger.error(f"Erro ao pesquisar QA: {str(e)}")
            # Fallback para busca por texto
            return self._text_search_fallback(query, feira_id, top_k)
    
    def _text_search_fallback(self, query: str, feira_id: Optional[int] = None, top_k: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Método de fallback para busca baseada em texto quando a busca vetorial falha.
        """
        if top_k is None:
            top_k = self._get_param_value('SEARCH_TOP_K', 'search', 3)
            
        query_lower = query.lower()
        
        # Buscar QAs contendo termos da consulta
        queryset = FeiraManualQA.objects.all()
        
        if feira_id:
            queryset = queryset.filter(feira_id=feira_id)
        
        queryset = queryset.filter(
            Q(question__icontains=query) |
            Q(answer__icontains=query) |
            Q(similar_questions__contains=query)
        )
        
        # Limitar e retornar resultados
        queryset = queryset[:top_k]
        
        results = []
        for qa in queryset:
            # Calcular um score simples baseado na frequência dos termos
            score = 0.5  # score padrão
            
            if query_lower in qa.question.lower():
                score += 0.3
            
            if query_lower in qa.answer.lower():
                score += 0.2
            
            # Criar resultado
            result = {
                'id': f"qa_{qa.id}",
                'score': score,
                'question': qa.question,
                'answer': qa.answer,
                'context': qa.context,
                'similar_questions': qa.similar_questions,
                'feira_id': str(qa.feira.id),
                'feira_nome': qa.feira.nome,
                'qa_id': str(qa.id)
            }
            results.append(result)
        
        # Ordenar por score
        results.sort(key=lambda x: x['score'], reverse=True)
        
        return results
    
    def _get_query_embedding(self, query: str) -> Optional[List[float]]:
        """
        Gera embedding para uma consulta.
        
        Args:
            query: A consulta do usuário.
            
        Returns:
            Lista de floats representando o embedding ou None em caso de erro.
        """
        try:
            # Gerar embedding usando o provedor específico de embeddings
            if self.embedding_provider == 'openai':
                # Usar cliente OpenAI para embeddings
                # Verificar se o cliente atual é OpenAI para reutilizar
                if self.provider == 'openai':
                    embedding_client = self.client
                else:
                    # Obter cliente OpenAI específico para embeddings
                    embedding_client = get_llm_client('Embedding Generator')[0]
                
                response = embedding_client.embeddings.create(
                    input=query,
                    model=self.embedding_model,
                    dimensions=self.embedding_dimension
                )
                
                # Extrair o embedding da resposta
                embedding = response.data[0].embedding
                return embedding
                
            elif self.embedding_provider == 'groq':
                # Usar cliente Groq para embeddings
                # Verificar se o cliente atual é Groq para reutilizar
                if self.provider == 'groq':
                    embedding_client = self.client
                else:
                    # Obter cliente Groq específico para embeddings
                    embedding_client = get_llm_client('Embedding Generator')[0]
                
                response = embedding_client.embeddings.create(
                    input=query,
                    model=self.embedding_model,
                )
                embedding = response.data[0].embedding
                return embedding
                
            else:
                logger.warning(f"Geração de embeddings não implementada para o provedor {self.embedding_provider}")
                # Fallback para OpenAI como provedor de embeddings
                openai_client = get_llm_client('Embedding Generator')[0]
                response = openai_client.embeddings.create(
                    input=query,
                    model="text-embedding-3-small",
                    dimensions=self.embedding_dimension
                )
                embedding = response.data[0].embedding
                return embedding
                
        except Exception as e:
            logger.error(f"Erro ao gerar embedding para consulta: {str(e)}")
            return None

    def gerar_resposta_rag(self, query: str, feira_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Gera uma resposta usando RAG com base na consulta e nos QA disponíveis.
        
        Args:
            query: A consulta do usuário.
            feira_id: ID opcional da feira para restringir a busca.
            
        Returns:
            Dicionário com a resposta gerada e os contextos utilizados.
        """
        try:
            # Buscar QA relevantes
            qa_results = self.pesquisar_qa(query, feira_id)
            
            if not qa_results:
                return {
                    'resposta': "Não encontrei informações específicas para responder a essa pergunta.",
                    'contextos': [],
                    'status': 'no_results'
                }
            
            # Preparar contextos para a resposta
            contexts = []
            for result in qa_results:
                context = {
                    'question': result['question'],
                    'answer': result['answer'],
                    'score': result['score']
                }
                contexts.append(context)
            
            # Usar o System Prompt do agente ou um padrão específico para RAG
            system_prompt = self.system_prompt
            if not system_prompt:
                system_prompt = """
                Você é um assistente especializado em feiras e eventos, especificamente treinado para o sistema RAG. 
                Seu objetivo é fornecer informações precisas e relevantes com base nos contextos disponíveis.
                
                Diretrizes:
                1. Use APENAS as informações fornecidas nos contextos para responder à pergunta do usuário.
                2. Não invente ou adicione informações que não estejam explicitamente nos contextos.
                3. Se os contextos não contiverem informações suficientes, informe claramente que não há dados disponíveis.
                4. Priorize informações dos contextos com pontuação (score) mais alta.
                5. Mantenha suas respostas concisas e diretas, focando nos pontos principais.
                6. Formate a informação de maneira estruturada e de fácil leitura quando apropriado.
                
                Lembre-se: sua função é recuperar e apresentar conhecimento existente, não criar novo conteúdo.
                """
            
            context_text = "\n\n".join([
                f"Contexto {i+1} (Relevância: {ctx['score']:.2f}):\nPergunta: {ctx['question']}\nResposta: {ctx['answer']}" 
                for i, ctx in enumerate(contexts)
            ])
            
            user_prompt = f"""
            Contextos recuperados do banco de conhecimento:
            {context_text}
            
            Pergunta do usuário: {query}
            
            Por favor, responda à pergunta do usuário baseando-se exclusivamente nos contextos fornecidos acima.
            """
            
            # Gerar resposta com o provedor escolhido
            if self.provider == 'openai':
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=self.temperature,
                )
                
                resposta = response.choices[0].message.content
                
            elif self.provider == 'anthropic':
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=1000,
                    temperature=self.temperature,
                    system=system_prompt,
                    messages=[
                        {"role": "user", "content": user_prompt}
                    ],
                )
                
                resposta = response.content[0].text
                
            elif self.provider == 'groq':
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=self.temperature,
                )
                
                resposta = response.choices[0].message.content
            
            else:
                resposta = "Provedor não suportado."
            
            return {
                'resposta': resposta,
                'contextos': contexts,
                'status': 'success'
            }
            
        except Exception as e:
            logger.error(f"Erro ao gerar resposta RAG: {str(e)}")
            return {
                'resposta': f"Desculpe, ocorreu um erro ao processar sua consulta.",
                'contextos': [],
                'status': 'error',
                'error': str(e)
            }

# Integração com o sistema de briefing
def integrar_feira_com_briefing(briefing_id, feira_id):
    """
    Integra os QA de uma feira com um briefing específico.
    
    Args:
        briefing_id: ID do briefing.
        feira_id: ID da feira.
        
    Returns:
        Dicionário com resultados da integração.
    """
    from projetos.models.briefing import Briefing, BriefingConversation
    
    try:
        # Obter o briefing
        briefing = Briefing.objects.get(pk=briefing_id)
        feira = Feira.objects.get(pk=feira_id)
        
        # Vincular a feira ao briefing
        briefing.feira = feira
        briefing.save()
        
        # Inicializar serviço RAG
        rag_service = RAGService()  # Vai usar o Assistente RAG de Feiras por padrão
        
        # Atualizar embeddings da feira (se necessário)
        rag_service.atualizar_embeddings_feira(feira_id)
        
        # Criar mensagem informativa no histórico do briefing
        BriefingConversation.objects.create(
            briefing=briefing,
            mensagem=f"Manual da feira '{feira.nome}' integrado ao briefing. Agora você pode fazer perguntas específicas sobre esta feira.",
            origem='sistema',
            etapa=briefing.etapa_atual
        )
        
        return {
            'status': 'success',
            'message': f"Feira '{feira.nome}' integrada ao briefing com sucesso."
        }
        
    except Briefing.DoesNotExist:
        return {
            'status': 'error',
            'message': f'Briefing com ID {briefing_id} não encontrado.'
        }
    except Feira.DoesNotExist:
        return {
            'status': 'error',
            'message': f'Feira com ID {feira_id} não encontrada.'
        }
    except Exception as e:
        logger.error(f"Erro ao integrar feira com briefing: {str(e)}")
        return {
            'status': 'error',
            'message': str(e)
        }