# core/services/qa_generator.py

import json
import time
import logging
from typing import List, Dict, Any, Optional

from django.conf import settings

from core.models import Feira, FeiraManualChunk, ParametroIndexacao, FeiraManualQA, Agente
from core.utils.llm_utils import get_llm_client

logger = logging.getLogger(__name__)

def get_qa_param(nome, default):
    """
    Obtém um parâmetro de QA da tabela de parâmetros de indexação
    """
    try:
        param = ParametroIndexacao.objects.get(nome=nome, categoria='qa')
        return param.valor_convertido()
    except ParametroIndexacao.DoesNotExist:
        return default

class QAGenerator:
    def __init__(self, agent_name='Gerador de Q&A'):
        """
        Inicializa o gerador de perguntas e respostas usando um agente configurado.
        
        Args:
            agent_name: Nome do agente configurado a ser utilizado
        """
        self.agent_name = agent_name
        
        # Obter cliente LLM usando o utilitário
        self.client, self.model, self.temperature, self.system_prompt, self.task_instructions = get_llm_client(agent_name)
        
        # Determinar o provider com base no cliente
        if hasattr(self.client, 'chat'):  # OpenAI
            self.provider = 'openai'
        elif hasattr(self.client, 'messages'):  # Anthropic
            self.provider = 'anthropic'
        elif hasattr(self.client, 'completion'):  # Groq
            self.provider = 'groq'
        else:
            logger.warning(f"Não foi possível determinar o provedor do agente '{agent_name}'. Tentando usar parâmetros padrão.")
            # Fallback para parâmetros padrão se o agente não existir
            self.provider = get_qa_param('QA_PROVIDER', 'openai')
            self.model = get_qa_param('QA_MODEL', 'gpt-4o')
            self.temperature = get_qa_param('QA_TEMPERATURE', 0.3)
            self.task_instructions = None  # Adicionar fallback para task_instructions
            
            # Inicializar cliente com base no provider de fallback
            if self.provider == 'openai':
                import openai
                openai.api_key = settings.OPENAI_API_KEY
                self.client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
            elif self.provider == 'anthropic':
                from anthropic import Anthropic
                self.client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
            else:
                raise ValueError(f"Provedor não suportado: {self.provider}")
        
        # Obter outros parâmetros
        self.max_pairs_per_chunk = get_qa_param('QA_MAX_PAIRS_PER_CHUNK', 5)
        self.min_confidence = get_qa_param('QA_MIN_CONFIDENCE', 0.7)
        
        # Se o system_prompt não estiver definido no agente, usar um padrão
        if not self.system_prompt:
            self.system_prompt = "Você extrai perguntas e respostas de documentos e retorna em JSON válido."
    
    def generate_qa_from_chunk(self, chunk: FeiraManualChunk, feira_description: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Gera perguntas e respostas a partir de um chunk do manual da feira.
        
        Args:
            chunk: O chunk do manual da feira.
            feira_description: Uma descrição opcional da feira para contextualização.
            
        Returns:
            Uma lista de dicionários contendo perguntas e respostas.
        """
        # Construir a instrução para o modelo de IA
        instruction = self._build_instruction(chunk.texto, feira_description)
        
        # Gerar QA usando o provedor associado ao agente
        if self.provider == 'openai':
            return self._generate_with_openai(instruction, chunk)
        elif self.provider == 'anthropic':
            return self._generate_with_anthropic(instruction, chunk)
        elif self.provider == 'groq':
            return self._generate_with_groq(instruction, chunk)
        else:
            logger.error(f"Provedor não suportado: {self.provider}")
            return []
    
    def _build_instruction(self, text: str, description: Optional[str] = None) -> str:
        """
        Constrói as instruções para o modelo de IA.
        
        Args:
            text: O texto do chunk.
            description: Uma descrição opcional da feira.
            
        Returns:
            As instruções formatadas para o modelo de IA.
        """
        context = ""
        if description:
            context = f"Resumo do assunto do documento: {description}\n\n"
        
        # Usar task_instructions se disponível, caso contrário usar um template básico
        if self.task_instructions:
            # Substituir as variáveis no template
            instruction = self.task_instructions
            # Substituir {context} se presente no template
            instruction = instruction.replace("{context}", context)
            # Substituir {self.max_pairs_per_chunk} se presente no template
            instruction = instruction.replace("{self.max_pairs_per_chunk}", str(self.max_pairs_per_chunk))
        else:
            # Template básico e mínimo para fallback
            instruction = f"""Extraia informações deste texto e gere perguntas e respostas em formato JSON.
{context}Gere no máximo {self.max_pairs_per_chunk} pares de pergunta-resposta.
O formato deve ser: {{"results": [{{"q": "pergunta", "a": "resposta", "t": "trecho", "sq": ["perguntas similares"]}}]}}
"""
        
        # Adicionar o texto para análise
        instruction += f"\n\nChunk para análise:\n{text}"
        return instruction

    def _generate_with_openai(self, instruction: str, chunk: FeiraManualChunk) -> List[Dict[str, Any]]:
        """
        Gera QA usando a API do OpenAI.
        
        Args:
            instruction: As instruções para o modelo.
            chunk: O chunk do qual gerar QA.
            
        Returns:
            Uma lista de dicionários de QA.
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": instruction}
                ],
                temperature=self.temperature,
            )
            
            content = response.choices[0].message.content
            data = json.loads(content)
            
            # Limitar ao número máximo de pares por chunk, se necessário
            results = data.get("results", [])
            if len(results) > self.max_pairs_per_chunk:
                results = results[:self.max_pairs_per_chunk]
                
            return results
            
        except Exception as e:
            logger.error(f"Erro ao gerar QA com OpenAI: {str(e)}")
            return []

    def _generate_with_anthropic(self, instruction: str, chunk: FeiraManualChunk) -> List[Dict[str, Any]]:
        """
        Gera QA usando a API do Anthropic.
        
        Args:
            instruction: As instruções para o modelo.
            chunk: O chunk do qual gerar QA.
            
        Returns:
            Uma lista de dicionários de QA.
        """
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4000,
                temperature=self.temperature,
                system=self.system_prompt,
                messages=[
                    {"role": "user", "content": instruction}
                ],
            )
            
            content = response.content[0].text
            
            # Extrair o JSON da resposta (Claude pode adicionar texto antes/depois do JSON)
            try:
                # Tentar encontrar e extrair somente o JSON
                start_idx = content.find('{')
                end_idx = content.rfind('}') + 1
                if start_idx >= 0 and end_idx > start_idx:
                    json_str = content[start_idx:end_idx]
                    data = json.loads(json_str)
                else:
                    # Tentar analisar a resposta completa como JSON
                    data = json.loads(content)
                
                # Limitar ao número máximo de pares por chunk, se necessário
                results = data.get("results", [])
                if len(results) > self.max_pairs_per_chunk:
                    results = results[:self.max_pairs_per_chunk]
                    
                return results
                
            except json.JSONDecodeError:
                logger.error(f"Erro ao analisar JSON na resposta do Anthropic: {content}")
                return []
                
        except Exception as e:
            logger.error(f"Erro ao gerar QA com Anthropic: {str(e)}")
            return []

    def _generate_with_groq(self, instruction: str, chunk: FeiraManualChunk) -> List[Dict[str, Any]]:
        """
        Gera QA usando a API do Groq.
        
        Args:
            instruction: As instruções para o modelo.
            chunk: O chunk do qual gerar QA.
            
        Returns:
            Uma lista de dicionários de QA.
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": instruction}
                ],
                temperature=self.temperature,
            )
            
            content = response.choices[0].message.content
            
            # Tentar extrair o JSON da resposta
            try:
                # Procurar por blocos de código JSON
                if "```json" in content:
                    # Extrair conteúdo entre blocos de código markdown
                    start_idx = content.find("```json") + 7
                    end_idx = content.find("```", start_idx)
                    if start_idx >= 7 and end_idx > start_idx:
                        json_str = content[start_idx:end_idx].strip()
                        data = json.loads(json_str)
                    else:
                        # Tentar encontrar e extrair somente o JSON
                        start_idx = content.find('{')
                        end_idx = content.rfind('}') + 1
                        if start_idx >= 0 and end_idx > start_idx:
                            json_str = content[start_idx:end_idx]
                            data = json.loads(json_str)
                        else:
                            # Tentar analisar a resposta completa como JSON
                            data = json.loads(content)
                else:
                    # Tentar encontrar e extrair somente o JSON
                    start_idx = content.find('{')
                    end_idx = content.rfind('}') + 1
                    if start_idx >= 0 and end_idx > start_idx:
                        json_str = content[start_idx:end_idx]
                        data = json.loads(json_str)
                    else:
                        # Tentar analisar a resposta completa como JSON
                        data = json.loads(content)
                    
                # Limitar ao número máximo de pares por chunk, se necessário
                results = data.get("results", [])
                if len(results) > self.max_pairs_per_chunk:
                    results = results[:self.max_pairs_per_chunk]
                    
                return results
                
            except json.JSONDecodeError as e:
                logger.error(f"Erro ao analisar JSON na resposta do Groq: {e}")
                logger.debug(f"Conteúdo problemático: {content}")
                return []
                
        except Exception as e:
            logger.error(f"Erro ao gerar QA com Groq: {str(e)}")
            return []

    def save_qa_pairs(self, qa_pairs: List[Dict[str, Any]], feira: Feira, chunk: FeiraManualChunk) -> List[FeiraManualQA]:
        """
        Salva os pares QA no banco de dados.
        
        Args:
            qa_pairs: Lista de pares QA gerados.
            feira: O objeto Feira associado.
            chunk: O chunk do qual os QA foram gerados.
            
        Returns:
            Lista de objetos FeiraManualQA criados.
        """
        created_pairs = []
        
        for qa in qa_pairs:
            try:
                # Garantir que similar_questions seja uma lista
                similar_questions = qa.get('sq', [])
                if isinstance(similar_questions, str):
                    try:
                        similar_questions = json.loads(similar_questions)
                    except:
                        similar_questions = similar_questions.split(',')
                
                qa_obj = FeiraManualQA.objects.create(
                    feira=feira,
                    question=qa.get('q', ''),
                    answer=qa.get('a', ''),
                    context=qa.get('t', ''),
                    similar_questions=similar_questions,
                    chunk_id=str(chunk.id)
                )
                created_pairs.append(qa_obj)
            except Exception as e:
                logger.error(f"Erro ao salvar par QA: {str(e)}")
        
        return created_pairs
    
def process_all_chunks_for_feira(feira_id: int, delay: Optional[int] = None, agent_name: str = 'Gerador de Q&A') -> Dict[str, Any]:
    """
    Processa todos os chunks de uma feira para gerar pares QA.
    
    Args:
        feira_id: ID da feira.
        delay: Atraso entre chamadas à API (em segundos).
        agent_name: Nome do agente a ser utilizado.
        
    Returns:
        Dicionário com resultados do processamento.
    """
    
    # Obter delay dos parâmetros se não for especificado
    if delay is None:
        delay = get_qa_param('QA_DELAY', 2)
    
    try:
        # Obter a feira e seus chunks
        feira = Feira.objects.get(pk=feira_id)
        chunks = FeiraManualChunk.objects.filter(feira=feira)
        
        if not chunks.exists():
            return {"status": "error", "message": "Nenhum chunk encontrado para esta feira"}
        
        # Inicializar o gerador com o agente especificado
        generator = QAGenerator(agent_name=agent_name)
        
        total_chunks = chunks.count()
        processed = 0
        total_qa = 0
        errors = 0
        
        # Atualizar o status da feira
        feira.processamento_status = 'processando'
        feira.save()
        
        for i, chunk in enumerate(chunks):
            try:
                # Atualizar progresso
                progress = int((i / total_chunks) * 100)
                feira.progresso_processamento = progress
                feira.save(update_fields=['progresso_processamento'])
                
                # Gerar QA do chunk
                qa_pairs = generator.generate_qa_from_chunk(
                    chunk, 
                    feira.description if hasattr(feira, 'description') else None
                )
                
                # Salvar QA gerados
                saved_pairs = generator.save_qa_pairs(qa_pairs, feira, chunk)
                
                total_qa += len(saved_pairs)
                processed += 1
                
                # Adicionar atraso para evitar limites de taxa
                if i < total_chunks - 1:
                    time.sleep(delay)
                    
            except Exception as e:
                logger.error(f"Erro ao processar chunk {chunk.id}: {str(e)}")
                errors += 1
        
        # Atualizar o status final da feira
        feira.processamento_status = 'concluido'
        feira.progresso_processamento = 100
        feira.save()
        
        result = {
            "status": "success",
            "message": f"Processamento concluído. Gerados {total_qa} pares QA de {processed} chunks usando o agente '{agent_name}'.",
            "total_chunks": total_chunks,
            "processed_chunks": processed,
            "total_qa": total_qa,
            "errors": errors
        }
        
        # NOVA PARTE: Calcular embeddings para os Q&A gerados usando o serviço refatorado
        try:
            from core.services.rag_service import RAGService
            
            logger.info(f"Iniciando cálculo de embeddings para {total_qa} pares Q&A da feira {feira_id}")
            rag_service = RAGService()
            embeddings_result = rag_service.atualizar_embeddings_feira(feira_id)
            
            result["embeddings_result"] = embeddings_result
            logger.info(f"Cálculo de embeddings concluído para feira {feira_id}: {embeddings_result}")
        except Exception as e:
            logger.error(f"Erro ao calcular embeddings para QA da feira {feira_id}: {str(e)}")
            result["embeddings_error"] = str(e)
        
        return result
        
    except Feira.DoesNotExist:
        return {"status": "error", "message": f"Feira com ID {feira_id} não encontrada"}
    except Exception as e:
        logger.error(f"Erro ao processar feira {feira_id}: {str(e)}")
        return {"status": "error", "message": str(e)}