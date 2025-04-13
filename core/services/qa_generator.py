import json
import time
import logging
from typing import List, Dict, Any, Optional

from django.conf import settings
import openai
from anthropic import Anthropic

from core.models import Feira, FeiraManualChunk, ParametroIndexacao
from core.models.qa import FeiraManualQA

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
    def __init__(self, provider=None):
        """
        Inicializa o gerador de perguntas e respostas.
        
        Args:
            provider (str): O provedor de IA a ser usado ('openai' ou 'anthropic')
        """
        # Se o provider não for especificado, buscar do parâmetro
        if provider is None:
            provider = get_qa_param('QA_PROVIDER', 'openai')
            
        self.provider = provider
        self.temperature = get_qa_param('QA_TEMPERATURE', 0.3)
        self.max_pairs_per_chunk = get_qa_param('QA_MAX_PAIRS_PER_CHUNK', 5)
        self.min_confidence = get_qa_param('QA_MIN_CONFIDENCE', 0.7)
        
        # Modelo específico a ser usado
        self.model = None
        if provider == 'openai':
            self.model = get_qa_param('QA_MODEL', 'gpt-4o')
            openai.api_key = settings.OPENAI_API_KEY
            self.client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        elif provider == 'anthropic':
            self.model = get_qa_param('QA_MODEL', 'claude-3-opus-20240229')
            self.client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        else:
            raise ValueError(f"Provedor não suportado: {provider}")
    
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
        
        # Gerar QA usando o provedor escolhido
        if self.provider == 'openai':
            return self._generate_with_openai(instruction, chunk)
        elif self.provider == 'anthropic':
            return self._generate_with_anthropic(instruction, chunk)
    
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
            
        return f"""Você é um agente interno de um sistema especializado em extrair perguntas e respostas de documentos. Sua tarefa é analisar o chunk fornecido, que representa um segmento de um documento completo, e gerar perguntas e respostas baseadas nas informações contidas nele.

{context}Diretrizes:
1. Extraia informações relevantes (respostas) do chunk fornecido. Essas informações devem ser associadas a perguntas principais, mantendo sempre o tom e o estilo de comunicação do texto base.
2. Para cada resposta extraída:
   - Crie uma pergunta principal (q) que tenha como resposta a informação extraída (a).
   - Identifique o trecho específico do documento (t) de onde a resposta foi retirada.
   - Formule perguntas alternativas (sq) que poderiam ser feitas para obter a mesma resposta (a).
3. Sempre que encontrar múltiplas informações relevantes no chunk, crie múltiplas perguntas e respostas.
4. Mantenha a maior originalidade possível no texto extraído, evitando interpretações fora do conteúdo fornecido.
5. Gere no máximo {self.max_pairs_per_chunk} pares de pergunta e resposta por chunk.
6. A saída deve ser estruturada em formato JSON compatível com o seguinte esquema:
{{
  "results": [
    {{
      "a": "A resposta ou informação extraída",
      "t": "O trecho exato do documento de onde a resposta foi retirada",
      "q": "A pergunta principal que leva à resposta",
      "sq": ["Pergunta alternativa 1", "Pergunta alternativa 2", ...]
    }},
    ...
  ]
}}

Chunk para análise:
{text}"""

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
                    {"role": "system", "content": "Você extrai perguntas e respostas de documentos e retorna em JSON válido."},
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
                system="Você extrai perguntas e respostas de documentos e retorna em JSON válido.",
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
                qa_obj = FeiraManualQA.objects.create(
                    feira=feira,
                    question=qa.get('q', ''),
                    answer=qa.get('a', ''),
                    context=qa.get('t', ''),
                    similar_questions=qa.get('sq', []),
                    chunk_id=str(chunk.id)
                )
                created_pairs.append(qa_obj)
            except Exception as e:
                logger.error(f"Erro ao salvar par QA: {str(e)}")
        
        return created_pairs


def process_all_chunks_for_feira(feira_id: int, delay: Optional[int] = None) -> Dict[str, Any]:
    """
    Processa todos os chunks de uma feira para gerar pares QA.
    
    Args:
        feira_id: ID da feira.
        delay: Atraso entre chamadas à API (em segundos).
        
    Returns:
        Dicionário com resultados do processamento.
    """
    # Verificar se QA está habilitado
    qa_habilitado = get_qa_param('QA_ENABLED', True)
    if not qa_habilitado:
        return {
            "status": "skipped", 
            "message": "Geração de QA desabilitada. Verifique o parâmetro QA_ENABLED."
        }
    
    # Obter delay dos parâmetros se não for especificado
    if delay is None:
        delay = get_qa_param('QA_DELAY', 2)
    
    try:
        # Obter a feira e seus chunks
        feira = Feira.objects.get(pk=feira_id)
        chunks = FeiraManualChunk.objects.filter(feira=feira)
        
        if not chunks.exists():
            return {"status": "error", "message": "Nenhum chunk encontrado para esta feira"}
        
        # Inicializar o gerador
        provider = get_qa_param('QA_PROVIDER', 'openai')
        generator = QAGenerator(provider=provider)
        
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
                qa_pairs = generator.generate_qa_from_chunk(chunk, feira.description if hasattr(feira, 'description') else None)
                
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
        
        return {
            "status": "success",
            "message": f"Processamento concluído. Gerados {total_qa} pares QA de {processed} chunks.",
            "total_chunks": total_chunks,
            "processed_chunks": processed,
            "total_qa": total_qa,
            "errors": errors
        }
        
    except Feira.DoesNotExist:
        return {"status": "error", "message": f"Feira com ID {feira_id} não encontrada"}
    except Exception as e:
        logger.error(f"Erro ao processar feira {feira_id}: {str(e)}")
        return {"status": "error", "message": str(e)}