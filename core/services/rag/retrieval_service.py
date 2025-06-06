# services/rag/retrieval_service.py

import logging
import time
from typing import List, Dict, Any, Optional

from django.conf import settings
from django.db.models import Q

from core.models import Feira, FeiraManualQA, ParametroIndexacao
from core.utils.pinecone_utils import query_vectors, get_index, get_namespace_stats
from core.utils.llm_utils import get_llm_client
from core.services.rag.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)

class RetrievalService:
    """
    Serviço responsável pela recuperação de informações do banco vetorial para o sistema RAG.
    """
    
    def __init__(self, embedding_service=None, agent_name='Assistente RAG de Feiras'):
        """
        Inicializa o serviço de recuperação.
        
        Args:
            embedding_service: Instância opcional do EmbeddingService. Se não fornecido, será criado.
            agent_name: Nome do agente configurado a ser utilizado para geração de respostas.
        """
        logger.info(f"Inicializando RetrievalService com agente '{agent_name}'")
        self.agent_name = agent_name
        
        # Usar embedding_service fornecido ou criar um novo
        if embedding_service:
            self.embedding_service = embedding_service
            logger.info("✓ Usando embedding_service fornecido")
        else:
            from core.services.rag.embedding_service import EmbeddingService
            self.embedding_service = EmbeddingService()
            logger.info("✓ Criado novo embedding_service")
        
        # Obter cliente LLM para responder às consultas
        self.client, self.model, self.temperature, self.system_prompt, self.task_instructions = get_llm_client(agent_name)
        
        # Determinar o provider com base no cliente
        if hasattr(self.client, 'chat'):  # OpenAI
            self.provider = 'openai'
        elif hasattr(self.client, 'messages'):  # Anthropic
            self.provider = 'anthropic'
        elif hasattr(self.client, 'completion'):  # Groq
            self.provider = 'groq'
        else:
            logger.warning(f"Não foi possível determinar o provedor do agente '{agent_name}'")
            self.provider = 'unknown'
            
        # Obter parâmetros de busca
        self.search_threshold = self._get_param_value('SEARCH_THRESHOLD', 'search', 0.4)
        self.search_top_k = self._get_param_value('SEARCH_TOP_K', 'search', 3)
        
        logger.info(f"Parâmetros de busca: threshold={self.search_threshold}, top_k={self.search_top_k}")
        
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
        start_time = time.time()
        logger.info(f"[DIAGNÓSTICO QA] Iniciando pesquisa para query: '{query}' (feira_id: {feira_id}, top_k: {top_k})")
        
        try:
            # Definir o namespace antes de qualquer processamento
            qa_namespace = None
            if feira_id:
                try:
                    feira = Feira.objects.get(pk=feira_id)
                    # IMPORTANTE: Obter o namespace correto aqui
                    qa_namespace = feira.get_qa_namespace()  # Deve retornar algo como 'feira_qa_1'
                    logger.info(f"[DIAGNÓSTICO QA] ✓ Namespace QA para feira {feira_id}: '{qa_namespace}'")
                except Feira.DoesNotExist:
                    logger.warning(f"[DIAGNÓSTICO QA] ✗ Feira ID {feira_id} não encontrada")
                    return self._text_search_fallback(query, feira_id, top_k)
            
            if top_k is None:
                top_k = self.search_top_k
                logger.info(f"[DIAGNÓSTICO QA] ✓ Usando top_k padrão: {top_k}")
            
            similarity_threshold = self.search_threshold
            logger.info(f"[DIAGNÓSTICO QA] ✓ Threshold de similaridade: {similarity_threshold}")
            
            logger.info(f"[DIAGNÓSTICO QA] Gerando embedding para query: '{query}'")
            query_embedding = self.embedding_service.gerar_embedding_consulta(query)
            
            if not query_embedding:
                logger.error("[DIAGNÓSTICO QA] ✗ FALHA ao gerar embedding para a consulta. Realizando fallback para busca por texto.")
                return self._text_search_fallback(query, feira_id, top_k)
            
            logger.info(f"[DIAGNÓSTICO QA] ✓ Embedding gerado para query (tamanho: {len(query_embedding)})")
            
            # Verificar se o namespace existe e tem vetores
            if qa_namespace:
                try:
                    stats = get_namespace_stats(qa_namespace)
                    if stats and stats['exists']:
                        logger.info(f"[DIAGNÓSTICO QA] ✓ Namespace '{qa_namespace}' encontrado com {stats['vector_count']} vetores")
                    else:
                        logger.warning(f"[DIAGNÓSTICO QA] ✗ Namespace '{qa_namespace}' não encontrado ou vazio. Usando fallback de texto.")
                        return self._text_search_fallback(query, feira_id, top_k)
                except Exception as e:
                    logger.error(f"[DIAGNÓSTICO QA] ✗ Erro ao verificar estatísticas do namespace: {str(e)}")
            
            # O filtro ainda é útil se houver diversos QAs no mesmo namespace
            filter_obj = {"feira_id": {"$eq": str(feira_id)}} if feira_id else None
            
            logger.info(f"[DIAGNÓSTICO QA] Consultando banco vetorial (namespace: {qa_namespace}, filtro: {filter_obj})")
            
            try:
                # Verificar o índice Pinecone
                index = get_index()
                if not index:
                    logger.error("[DIAGNÓSTICO QA] ✗ Não foi possível obter o índice Pinecone. Fallback para texto.")
                    return self._text_search_fallback(query, feira_id, top_k)
                
                # CRÍTICO: Usar o namespace QA específico aqui
                results = query_vectors(
                    query_embedding=query_embedding,
                    namespace=qa_namespace,  # Este é o namespace correto (feira_qa_1)
                    top_k=top_k,
                    filter_dict=filter_obj
                )
                
                logger.info(f"[DIAGNÓSTICO QA] ✓ Consulta no namespace '{qa_namespace}' retornou {len(results)} resultados")
                
                # Imprimir detalhes dos resultados para diagnóstico
                for i, result in enumerate(results):
                    logger.info(f"[DIAGNÓSTICO QA] Resultado {i+1}: ID={result['id']}, Score={result['score']:.4f}")
                
            except Exception as e:
                logger.error(f"[DIAGNÓSTICO QA] ✗ Erro ao consultar banco vetorial: {str(e)}. Realizando fallback para busca por texto.")
                return self._text_search_fallback(query, feira_id, top_k)
            
            # O resto da função permanece igual
            filtered_results = []
            for result in results:
                score = result['score']
                if score >= similarity_threshold:
                    logger.info(f"[DIAGNÓSTICO QA] ✓ Resultado {result['id']} com score {score:.4f} incluído (acima do threshold {similarity_threshold})")
                    formatted_result = {
                        'id': result['id'],
                        'score': score,
                        'question': result['metadata'].get('q', ''),
                        'answer': result['metadata'].get('a', ''),
                        'context': result['metadata'].get('t', ''),
                        'similar_questions': result['metadata'].get('sq', []),
                        'feira_id': result['metadata'].get('feira_id', ''),
                        'feira_nome': result['metadata'].get('feira_nome', ''),
                        'qa_id': result['metadata'].get('qa_id', '')
                    }
                    filtered_results.append(formatted_result)
                else:
                    logger.warning(f"[DIAGNÓSTICO QA] ✗ Resultado {result['id']} com score {score:.4f} descartado (abaixo do threshold {similarity_threshold})")
            
            # Se não houver resultados após filtrar, tente busca por texto
            if not filtered_results:
                logger.warning("[DIAGNÓSTICO QA] ✗ Nenhum resultado acima do threshold de similaridade. Realizando fallback para busca por texto.")
                return self._text_search_fallback(query, feira_id, top_k)
            
            elapsed_time = time.time() - start_time
            logger.info(f"[DIAGNÓSTICO QA] ✓ Pesquisa semântica concluída em {elapsed_time:.2f} segundos com {len(filtered_results)} resultados acima do threshold")
            
            return filtered_results
            
        except Exception as e:
            logger.error(f"[DIAGNÓSTICO QA] ✗ Erro não tratado na pesquisa: {str(e)}. Realizando fallback para busca por texto.")
            return self._text_search_fallback(query, feira_id, top_k)
    
    def _text_search_fallback(self, query: str, feira_id: Optional[int] = None, top_k: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Método de fallback para busca baseada em texto quando a busca vetorial falha.
        
        Args:
            query: A consulta do usuário.
            feira_id: ID opcional da feira para restringir a busca.
            top_k: Número máximo de resultados.
            
        Returns:
            Lista de pares QA relevantes com scores.
        """
        logger.info(f"[DIAGNÓSTICO FALLBACK] Iniciando busca por texto para query: '{query}'")
        
        if top_k is None:
            top_k = self.search_top_k
            
        query_lower = query.lower()
        queryset = FeiraManualQA.objects.all()
        
        if feira_id:
            logger.info(f"[DIAGNÓSTICO FALLBACK] Filtrando por feira_id: {feira_id}")
            queryset = queryset.filter(feira_id=feira_id)
        
        logger.info(f"[DIAGNÓSTICO FALLBACK] Aplicando filtros de texto na busca")
        queryset = queryset.filter(
            Q(question__icontains=query) |
            Q(answer__icontains=query) |
            Q(similar_questions__contains=query)
        )
        
        # Contar resultados antes de limitar
        total_encontrado = queryset.count()
        logger.info(f"[DIAGNÓSTICO FALLBACK] Total de resultados encontrados: {total_encontrado}")
        
        # Limitar resultados
        queryset = queryset[:top_k]
        logger.info(f"[DIAGNÓSTICO FALLBACK] ✓ Busca por texto retornou {queryset.count()} resultados (limitados a top_k={top_k})")
        
        results = []
        for qa in queryset:
            # Calcular um score simples baseado em correspondência de texto
            score = 0.5  # score base
            if query_lower in qa.question.lower():
                score += 0.3
            if query_lower in qa.answer.lower():
                score += 0.2
                
            logger.info(f"[DIAGNÓSTICO FALLBACK] ✓ QA {qa.id} obteve score {score:.2f} na busca por texto")
            
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
        logger.info(f"[DIAGNÓSTICO FALLBACK] ✓ Busca por texto concluída com {len(results)} resultados ordenados por relevância")
        
        return results

    def gerar_resposta_rag(self, query: str, feira_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Gera uma resposta usando RAG com base na consulta e nos QA disponíveis.
        
        Args:
            query: A consulta do usuário.
            feira_id: ID opcional da feira para restringir a busca.
            
        Returns:
            Dicionário com a resposta gerada e os contextos utilizados.
        """
        start_time = time.time()
        logger.info(f"Iniciando geração de resposta RAG para query: '{query}' (feira_id: {feira_id})")
        
        try:
            # Recuperar QAs relevantes
            logger.info("Buscando contextos relevantes para a consulta")
            qa_results = self.pesquisar_qa(query, feira_id)
            
            if not qa_results:
                logger.warning("Nenhum resultado encontrado para a consulta")
                return {
                    'resposta': "Não encontrei informações específicas para responder a essa pergunta.",
                    'contextos': [],
                    'status': 'no_results'
                }
            
            logger.info(f"✓ Encontrados {len(qa_results)} resultados relevantes para a consulta")
            
            # Preparar contextos para o prompt
            contexts = []
            for result in qa_results:
                context = {
                    'question': result['question'],
                    'answer': result['answer'],
                    'score': result['score']
                }
                contexts.append(context)
                logger.debug(f"✓ Adicionando contexto: Q='{result['question']}', score={result['score']:.3f}")
            
            # Obter ou configurar o prompt do sistema
            system_prompt = self.system_prompt
            if not system_prompt:
                system_prompt = """
                Você é um assistente especializado em feiras e eventos, especificamente treinado para o sistema RAG. 
                Seu objetivo é fornecer informações precisas e relevantes com base nos contextos disponíveis.
                
                Diretrizes:
                1. Use APENAS as informações fornecidas nos contextos para responder à pergunta do usuário.
                2. Não invente ou adicione informações que não estejam explicitamente nos contextos.
                3. Se os contextos não contiverem informações suficientes, informe que não há dados disponíveis.
                4. Priorize informações dos contextos com pontuação (score) mais alta.
                5. Mantenha suas respostas concisas e diretas.
                6. Formate as informações de forma estruturada quando necessário.
                """
                logger.debug("Usando system prompt padrão para RAG")
            else:
                logger.debug("Usando system prompt do agente para RAG")
            
            # Formatar os contextos para o prompt
            context_text = "\n\n".join([
                f"Contexto {i+1} (Relevância: {ctx['score']:.2f}):\nPergunta: {ctx['question']}\nResposta: {ctx['answer']}" 
                for i, ctx in enumerate(contexts)
            ])
            
            # Construir o prompt completo
            user_prompt = f"""
            Contextos recuperados do banco de conhecimento:
            {context_text}
            
            Pergunta do usuário: {query}
            
            Por favor, responda à pergunta baseando-se exclusivamente nos contextos fornecidos.
            """
            
            logger.info("✓ Prompt construído com contextos relevantes")
            
            # Chamar a API de acordo com o provedor
            try:
                if self.provider == 'openai':
                    logger.info(f"Chamando API OpenAI (modelo: {self.model}, temperatura: {self.temperature})")
                    response = self.client.chat.completions.create(
                        model=self.model,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ],
                        temperature=self.temperature,
                    )
                    resposta = response.choices[0].message.content
                    logger.info("✓ Resposta gerada com sucesso via OpenAI")
                    
                elif self.provider == 'anthropic':
                    logger.info(f"Chamando API Anthropic (modelo: {self.model}, temperatura: {self.temperature})")
                    response = self.client.messages.create(
                        model=self.model,
                        max_tokens=1000,
                        temperature=self.temperature,
                        system=system_prompt,
                        messages=[{"role": "user", "content": user_prompt}],
                    )
                    resposta = response.content[0].text
                    logger.info("✓ Resposta gerada com sucesso via Anthropic")
                    
                elif self.provider == 'groq':
                    logger.info(f"Chamando API Groq (modelo: {self.model}, temperatura: {self.temperature})")
                    response = self.client.chat.completions.create(
                        model=self.model,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ],
                        temperature=self.temperature,
                    )
                    resposta = response.choices[0].message.content
                    logger.info("✓ Resposta gerada com sucesso via Groq")
                
                else:
                    error_msg = f"Provedor '{self.provider}' não suportado"
                    logger.error(error_msg)
                    resposta = "Provedor não suportado para geração de resposta."
                
                logger.debug(f"Tamanho da resposta: {len(resposta)} caracteres")
                
            except Exception as e:
                error_msg = f"Erro ao chamar API do provedor {self.provider}: {str(e)}"
                logger.error(error_msg)
                resposta = "Desculpe, ocorreu um erro ao gerar a resposta."
                
            elapsed_time = time.time() - start_time
            logger.info(f"✓ Resposta RAG gerada em {elapsed_time:.2f} segundos")
            
            return {
                'resposta': resposta,
                'contextos': contexts,
                'status': 'success'
            }
            
        except Exception as e:
            error_msg = f"Erro não tratado ao gerar resposta RAG: {str(e)}"
            logger.error(error_msg)
            return {
                'resposta': "Desculpe, ocorreu um erro ao processar sua consulta.",
                'contextos': [],
                'status': 'error',
                'error': str(e)
            }