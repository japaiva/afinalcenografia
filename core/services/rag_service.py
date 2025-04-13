import os
import json
import logging
from typing import List, Dict, Any, Optional

import numpy as np
from django.conf import settings

from core.models import Feira
from core.models.qa import FeiraManualQA

logger = logging.getLogger(__name__)

class RAGService:
    """
    Serviço para integrar os pares QA com o sistema RAG existente.
    """
    
    def __init__(self, provider='openai'):
        """
        Inicializa o serviço RAG.
        
        Args:
            provider: Provedor de embeddings ('openai' ou 'anthropic')
        """
        self.provider = provider
        
        # Inicializar cliente de API conforme provider
        if provider == 'openai':
            import openai
            openai.api_key = settings.OPENAI_API_KEY
            self.client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        elif provider == 'anthropic':
            from anthropic import Anthropic
            self.client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        else:
            raise ValueError(f"Provedor não suportado: {provider}")
    
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
            
            # Gerar embedding usando OpenAI
            if self.provider == 'openai':
                response = self.client.embeddings.create(
                    input=embedding_text,
                    model="text-embedding-3-small",  # ou outro modelo configurado
                    dimensions=1536
                )
                
                # Extrair o embedding da resposta
                embedding = response.data[0].embedding
                return embedding
            
            # Implementar outros provedores conforme necessário
            else:
                logger.warning(f"Geração de embeddings não implementada para o provedor {self.provider}")
                return None
                
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
            
            for qa in qa_pairs:
                try:
                    # Gerar embedding
                    embedding = self.gerar_embeddings_qa(qa)
                    
                    if embedding:
                        # Aqui você conectaria com seu sistema específico de armazenamento 
                        # de vetores (Pinecone, Milvus, etc.)
                        
                        # Exemplo: Armazenar no Pinecone
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
            # Implementar conforme sua solução específica (Pinecone, Milvus, etc.)
            
            # Exemplo para Pinecone
            if os.environ.get('PINECONE_API_KEY'):
                import pinecone
                
                # Inicializar Pinecone
                pinecone.init(
                    api_key=os.environ.get('PINECONE_API_KEY'),
                    environment=os.environ.get('PINECONE_ENVIRONMENT', 'gcp-starter')
                )
                
                # Obter o índice
                index_name = os.environ.get('PINECONE_INDEX_NAME', 'afinal-feira-index')
                namespace = f"feira_{qa.feira.id}"
                
                index = pinecone.Index(index_name)
                
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
                
                # Upsert do vetor
                index.upsert(
                    vectors=[(f"qa_{qa.id}", embedding, metadata)],
                    namespace=namespace
                )
                
                return True
            
            # Se não tiver configuração de banco vetorial, apenas logar
            logger.info(f"Embedding gerado para QA {qa.id}, mas nenhum banco vetorial configurado")
            return False
            
        except Exception as e:
            logger.error(f"Erro ao armazenar no banco vetorial: {str(e)}")
            return False
    
    def pesquisar_qa(self, query: str, feira_id: Optional[int] = None, top_k: int = 5) -> List[Dict[str, Any]]:
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
            # Gerar embedding para a consulta
            query_embedding = self._get_query_embedding(query)
            
            if not query_embedding:
                return []
            
            # Buscar no banco vetorial
            results = self._search_vector_db(query_embedding, feira_id, top_k)
            
            return results
            
        except Exception as e:
            logger.error(f"Erro ao pesquisar QA: {str(e)}")
            return []
    
    def _get_query_embedding(self, query: str) -> Optional[List[float]]:
        """
        Gera embedding para uma consulta.
        
        Args:
            query: A consulta do usuário.
            
        Returns:
            Lista de floats representando o embedding ou None em caso de erro.
        """
        try:
            # Gerar embedding usando OpenAI
            if self.provider == 'openai':
                response = self.client.embeddings.create(
                    input=query,
                    model="text-embedding-3-small",  # ou outro modelo configurado
                    dimensions=1536
                )
                
                # Extrair o embedding da resposta
                embedding = response.data[0].embedding
                return embedding
            
            # Implementar outros provedores conforme necessário
            else:
                logger.warning(f"Geração de embeddings não implementada para o provedor {self.provider}")
                return None
                
        except Exception as e:
            logger.error(f"Erro ao gerar embedding para consulta: {str(e)}")
            return None
    
    def _search_vector_db(self, query_embedding: List[float], feira_id: Optional[int], top_k: int) -> List[Dict[str, Any]]:
        """
        Busca vetores similares no banco de dados vetorial.
        
        Args:
            query_embedding: O embedding da consulta.
            feira_id: ID opcional da feira para restringir a busca.
            top_k: Número máximo de resultados.
            
        Returns:
            Lista de resultados com metadados e scores.
        """
        try:
            # Exemplo para Pinecone
            if os.environ.get('PINECONE_API_KEY'):
                import pinecone
                
                # Inicializar Pinecone
                pinecone.init(
                    api_key=os.environ.get('PINECONE_API_KEY'),
                    environment=os.environ.get('PINECONE_ENVIRONMENT', 'gcp-starter')
                )
                
                # Obter o índice
                index_name = os.environ.get('PINECONE_INDEX_NAME', 'afinal-feira-index')
                namespace = f"feira_{feira_id}" if feira_id else None
                
                index = pinecone.Index(index_name)
                
                # Buscar vetores similares
                filter_obj = {}
                if feira_id:
                    filter_obj = {"feira_id": {"$eq": str(feira_id)}}
                
                query_response = index.query(
                    vector=query_embedding,
                    top_k=top_k,
                    include_metadata=True,
                    namespace=namespace,
                    filter=filter_obj if filter_obj else None
                )
                
                # Processar resultados
                results = []
                for match in query_response.matches:
                    # Criar um dicionário com os dados do resultado
                    result = {
                        'id': match.id,
                        'score': match.score,
                        'question': match.metadata.get('q', ''),
                        'answer': match.metadata.get('a', ''),
                        'context': match.metadata.get('t', ''),
                        'similar_questions': match.metadata.get('sq', []),
                        'feira_id': match.metadata.get('feira_id', ''),
                        'feira_nome': match.metadata.get('feira_nome', ''),
                        'qa_id': match.metadata.get('qa_id', '')
                    }
                    results.append(result)
                
                return results
            
            # Implementar outras soluções vetoriais se necessário
            
            # Fallback: se não há banco vetorial, fazer busca textual simples no banco
            logger.warning("Sem banco vetorial configurado, usando busca textual simples")
            
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
            
        except Exception as e:
            logger.error(f"Erro na busca vetorial: {str(e)}")
            return []

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
            qa_results = self.pesquisar_qa(query, feira_id, top_k=3)
            
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
            
            # Preparar prompt para o LLM
            system_prompt = """
            Você é um assistente especializado em feiras e eventos. 
            Use as informações fornecidas nos contextos para responder à pergunta do usuário.
            Base sua resposta apenas nas informações fornecidas nos contextos e não adicione informações extras.
            Se os contextos não contiverem informações suficientes para responder à pergunta, informe ao usuário que não há informações específicas disponíveis.
            """
            
            context_text = "\n\n".join([
                f"Contexto {i+1}:\nPergunta: {ctx['question']}\nResposta: {ctx['answer']}" 
                for i, ctx in enumerate(contexts)
            ])
            
            user_prompt = f"""
            Contextos:
            {context_text}
            
            Pergunta do usuário: {query}
            
            Por favor, responda à pergunta do usuário com base nos contextos fornecidos.
            """
            
            # Gerar resposta com o provedor escolhido
            if self.provider == 'openai':
                response = self.client.chat.completions.create(
                    model="gpt-4o",  # ou outro modelo configurado
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.3,
                )
                
                resposta = response.choices[0].message.content
                
            elif self.provider == 'anthropic':
                response = self.client.messages.create(
                    model="claude-3-opus-20240229",  # ou outro modelo configurado
                    max_tokens=1000,
                    temperature=0.3,
                    system=system_prompt,
                    messages=[
                        {"role": "user", "content": user_prompt}
                    ],
                )
                
                resposta = response.content[0].text
            
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
        rag_service = RAGService()
        
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