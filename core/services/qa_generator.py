# core/services/qa_generator.py

import json
import time
import logging
from typing import List, Dict, Any, Optional

from django.conf import settings

from core.models import Feira, FeiraManualChunk, ParametroIndexacao, FeiraManualQA, Agente, CampoPergunta
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
            # Fallback para parâmetros padrão se o agente não existir
            self.provider = get_qa_param('QA_PROVIDER', 'openai')
            self.model = get_qa_param('QA_MODEL', 'gpt-4o')
            self.temperature = get_qa_param('QA_TEMPERATURE', 0.3)
            self.task_instructions = None
            
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
        # CORREÇÃO: Primeiro gerar QA específicos para campos do cadastro
        field_qa_pairs = self._generate_field_qa_from_chunk(chunk)
        
        # Depois gerar QA gerais
        general_qa_pairs = self._generate_general_qa_from_chunk(chunk, feira_description)
        
        # Unir os resultados, colocando os field_qa_pairs primeiro
        all_qa_pairs = field_qa_pairs + general_qa_pairs
        
        return all_qa_pairs
    
    def _generate_general_qa_from_chunk(self, chunk: FeiraManualChunk, feira_description: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Gera perguntas e respostas gerais a partir de um chunk.
        
        Args:
            chunk: O chunk do manual da feira.
            feira_description: Uma descrição opcional da feira para contextualização.
            
        Returns:
            Uma lista de dicionários contendo perguntas e respostas gerais.
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
    
    def _generate_field_qa_from_chunk(self, chunk: FeiraManualChunk) -> List[Dict[str, Any]]:
        """
        Gera perguntas e respostas específicas para campos do cadastro a partir de um chunk.
        
        Args:
            chunk: O chunk do manual da feira.
            
        Returns:
            Uma lista de dicionários contendo perguntas e respostas para campos específicos.
        """
        field_qa_pairs = []
        
        # Obter todas as perguntas ativas para campos
        campo_perguntas = CampoPergunta.objects.filter(ativa=True).order_by('campo', '-prioridade')
        
        # Agrupar perguntas por campo e pegar apenas a de maior prioridade de cada campo
        campos_processados = set()
        perguntas_por_campo = {}
        
        for cp in campo_perguntas:
            if cp.campo not in campos_processados:
                campos_processados.add(cp.campo)
                perguntas_por_campo[cp.campo] = {
                    'pergunta_principal': cp.pergunta,
                    'perguntas_similares': []
                }
            else:
                # Adicionar como pergunta similar para este campo
                perguntas_por_campo[cp.campo]['perguntas_similares'].append(cp.pergunta)
        
        # Verificar relevância do texto para cada campo e gerar respostas
        for campo, info in perguntas_por_campo.items():
            # Verificar se o chunk contém conteúdo relevante para este campo
            relevancia = self._verificar_relevancia_campo(chunk.texto, campo)
            
            # CORREÇÃO: Reduzi o limiar de relevância para capturar mais campos
            if relevancia >= 0.3:  # Antes era 0.4
                pergunta = info['pergunta_principal']
                perguntas_similares = info['perguntas_similares'][:3]  # Limitando a 3 perguntas similares
                
                # Gerar resposta para este campo usando o texto do chunk
                resposta = self._gerar_resposta_para_campo(chunk.texto, pergunta, campo)
                
                # CORREÇÃO: Critério menos restritivo para considerar uma resposta válida
                if resposta and len(resposta.strip()) > 5:  # Antes era 10
                    # Calcular confiança baseada na relevância e comprimento da resposta
                    # CORREÇÃO: Ajuste na fórmula para priorizar relevância
                    confianca = relevancia * min(1.0, len(resposta) / 150)  # Antes era 200
                    
                    qa_pair = {
                        'q': pergunta,
                        'a': resposta,
                        't': chunk.texto,  # contexto original
                        'sq': perguntas_similares,
                        'campo_relacionado': campo,
                        'confianca_extracao': confianca
                    }
                    
                    field_qa_pairs.append(qa_pair)
        
        return field_qa_pairs
    
    def _verificar_relevancia_campo(self, texto: str, campo: str) -> float:
        """
        Verifica a relevância do texto para um campo específico.
        
        Args:
            texto: O texto do chunk.
            campo: O nome do campo a verificar.
            
        Returns:
            Um valor entre 0.0 e 1.0 indicando a relevância.
        """
        # Mapeamento de campos para palavras-chave relacionadas
        keywords = {
            'nome': ['nome', 'título', 'evento', 'feira', 'denominação'],
            'local': ['local', 'endereço', 'pavilhão', 'centro', 'exposição', 'localização'],
            'data_horario': ['data', 'hora', 'período', 'funcionamento', 'abertura', 'realização'],
            'publico_alvo': ['público', 'visitante', 'audiência', 'profissional', 'perfil'],
            'eventos_simultaneos': ['simultâneo', 'paralelo', 'conjunto', 'concomitante'],
            'promotora': ['promotora', 'organizadora', 'organização', 'responsável', 'realização'],
            'periodo_montagem': ['montagem', 'montar', 'instalação', 'construção'],
            'portao_acesso': ['portão', 'acesso', 'entrada', 'carga', 'descarga'],
            'periodo_desmontagem': ['desmontagem', 'desmontar', 'retirada', 'saída'],
            'altura_estande': ['altura', 'elevação', 'pé direito', 'metros', 'limite'],
            'palcos': ['palco', 'piso', 'elevado', 'apresentação', 'tablado'],
            'piso_elevado': ['piso', 'elevado', 'plataforma', 'desnível'],
            'mezanino': ['mezanino', 'segundo piso', 'segundo andar', 'sobrado'],
            'iluminacao': ['iluminação', 'luz', 'lâmpada', 'holofote', 'luminária'],
            'outros': ['regulamento', 'norma', 'regra', 'exigência', 'proibição', 'requisito', 'obrigatório', 'obrigatória'],
            'materiais': ['material', 'proibido', 'permitido', 'construção', 'inflamável', 'madeira', 'vidro', 'metal'],
            'credenciamento': ['credenciamento', 'credencial', 'cadastro', 'registro', 'crachá', 'identificação']
        }
        
        # CORREÇÃO: Expandir palavras-chave para todos os campos padrão
        campo_keywords = keywords.get(campo, [campo])
        
        # Verificar presença das palavras-chave no texto
        texto_lower = texto.lower()
        count = 0
        
        for kw in campo_keywords:
            if kw.lower() in texto_lower:
                count += 1
        
        # CORREÇÃO: Aumentar o multiplicador para melhorar a captura de campos relevantes
        if len(campo_keywords) > 0:
            return min(1.0, count / len(campo_keywords) * 2.0)  # Antes era 1.5
        return 0.0
    
    def _gerar_resposta_para_campo(self, texto: str, pergunta: str, campo: str) -> Optional[str]:
        """
        Gera uma resposta específica para um campo.
        
        Args:
            texto: O texto do chunk.
            pergunta: A pergunta a ser respondida.
            campo: O nome do campo relacionado.
            
        Returns:
            A resposta gerada ou None se não for possível gerar.
        """
        # CORREÇÃO: Melhorar o prompt para gerar respostas mais completas
        prompt = f"""
        Com base no seguinte texto extraído de um manual de feira ou evento, responda à pergunta abaixo.
        A pergunta está relacionada ao campo '{campo}' do cadastro da feira.
        
        TEXTO:
        {texto}
        
        PERGUNTA:
        {pergunta}
        
        INSTRUÇÕES IMPORTANTES:
        1. Responda de forma completa e detalhada, incluindo TODAS as informações relevantes encontradas no texto.
        2. NÃO resuma excessivamente a resposta. Inclua todos os detalhes importantes.
        3. Se a informação não estiver disponível no texto, responda apenas "Informação não disponível no texto fornecido."
        4. Se houver datas, horários, locais, dimensões ou requisitos específicos mencionados, inclua-os na resposta.
        5. Não invente informações nem use conhecimento externo ao texto fornecido.
        """
        
        try:
            # CORREÇÃO: Aumentar o limite de tokens para respostas mais completas
            max_tokens = 1000  # Antes não era especificado ou era menor
            
            # Enviar requisição ao provedor correto
            if self.provider == 'openai':
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "Você é um assistente especializado em extrair informações completas e detalhadas de documentos."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3,  # Menor temperatura para respostas mais precisas
                    max_tokens=max_tokens
                )
                resposta = response.choices[0].message.content
                
            elif self.provider == 'anthropic':
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=max_tokens,
                    temperature=0.3,
                    system="Você é um assistente especializado em extrair informações completas e detalhadas de documentos.",
                    messages=[
                        {"role": "user", "content": prompt}
                    ],
                )
                resposta = response.content[0].text
                
            elif self.provider == 'groq':
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "Você é um assistente especializado em extrair informações completas e detalhadas de documentos."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3,
                    max_tokens=max_tokens
                )
                resposta = response.choices[0].message.content
                
            else:
                logger.error(f"Provedor não suportado: {self.provider}")
                return None
            
            # Verificar se há resposta válida
            if "não disponível" in resposta.lower() or "não foi fornecido" in resposta.lower() or "não menciona" in resposta.lower():
                return None
            
            return resposta.strip()
            
        except Exception as e:
            logger.error(f"Erro ao gerar resposta para campo {campo}: {str(e)}")
            return None
    
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
            # CORREÇÃO: Template melhorado para garantir respostas mais detalhadas
            instruction = f"""Extraia informações deste texto e gere perguntas e respostas em formato JSON.
{context}Gere no máximo {self.max_pairs_per_chunk} pares de pergunta-resposta.
O formato deve ser: {{"results": [{{"q": "pergunta", "a": "resposta", "t": "trecho", "sq": ["perguntas similares"]}}]}}

INSTRUÇÕES IMPORTANTES:
1. As respostas devem ser detalhadas e completas, NÃO resumidas.
2. Inclua todos os detalhes relevantes encontrados no texto em cada resposta.
3. Quando houver datas, horários, locais ou requisitos específicos, certifique-se de incluí-los.
4. Não invente informações nem use conhecimento externo ao texto fornecido.
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
            # CORREÇÃO: Aumentar o limite de tokens para respostas mais completas
            response = self.client.chat.completions.create(
                model=self.model,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": instruction}
                ],
                temperature=self.temperature,
                max_tokens=4000  # Garantir espaço para respostas mais completas
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
            # CORREÇÃO: Aumentar o limite de tokens para respostas mais completas
            response = self.client.messages.create(
                model=self.model,
                max_tokens=8000,  # Aumentado para permitir respostas mais longas
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
                logger.error(f"Erro ao analisar JSON na resposta do Anthropic")
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
            # CORREÇÃO: Aumentar o limite de tokens para respostas mais completas
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": instruction}
                ],
                temperature=self.temperature,
                max_tokens=4000  # Garantir espaço para respostas mais completas
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
                logger.error(f"Erro ao analisar JSON na resposta do Groq")
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
                
                # Verificar se tem campo relacionado e confiança de extração
                campo_relacionado = qa.get('campo_relacionado', None)
                confianca_extracao = qa.get('confianca_extracao', 0.0)
                
                qa_obj = FeiraManualQA.objects.create(
                    feira=feira,
                    question=qa.get('q', ''),
                    answer=qa.get('a', ''),
                    context=qa.get('t', ''),
                    similar_questions=similar_questions,
                    chunk_id=str(chunk.id),
                    campo_relacionado=campo_relacionado,
                    confianca_extracao=confianca_extracao
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
        
        # Variáveis para estatísticas
        total_chunks = chunks.count()
        processed = 0
        total_qa = 0
        errors = 0
        
        # Limite QAs
        MAX_QA_TOTAL = 0  # CORREÇÃO: Valor zero significa sem limite
        if MAX_QA_TOTAL <= 0:
            MAX_QA_TOTAL = float('inf')  # ou um número muito alto

        
        # Atualizar o status da feira para processando
        feira.qa_processamento_status = 'processando'
        if hasattr(feira, 'qa_progresso_processamento'):
            feira.qa_progresso_processamento = 0
        feira.save()
        
        logger.info(f"Iniciando processamento de Q&A para feira {feira_id} (limite: {MAX_QA_TOTAL} QAs)")
        
        # Remover QAs existentes se estiverem reprocessando
        FeiraManualQA.objects.filter(feira=feira).delete()

        # ADICIONADO: Limpar o namespace do Pinecone antes de reprocessar
        try:
            from core.utils.pinecone_utils import delete_namespace
            feira = Feira.objects.get(pk=feira_id)
            namespace = feira.get_qa_namespace()
            delete_namespace(namespace)
            logger.info(f"✓ Namespace '{namespace}' limpo antes do reprocessamento de Q&A")
        except Exception as e:
            logger.warning(f"Aviso ao limpar namespace para feira {feira_id}: {str(e)}")
        
        # CORREÇÃO: Estruturas para QAs de campos em dicionário comum
        # Mapeamos por (campo, chunk_id) para permitir múltiplos QAs por campo de chunks diferentes
        field_qa_by_campo_chunk = {}
        
        # CORREÇÃO: Processar primeiro os QAs de campos específicos para todos os chunks
        # Isso garante que coletamos todos os QAs específicos de campos antes de processar os gerais
        logger.info(f"FASE 1: Processando QAs específicos de campos para todos os chunks")
        
        for i, chunk in enumerate(chunks):
            try:
                # Gerar QAs específicos para campos
                logger.info(f"Gerando QAs para campos do chunk {i+1}/{total_chunks}")
                field_qa_pairs = generator._generate_field_qa_from_chunk(chunk)
                
                # Registrar os QAs por campo e chunk
                for qa in field_qa_pairs:
                    campo = qa['campo_relacionado']
                    confianca = qa.get('confianca_extracao', 0.0)
                    chunk_id = str(chunk.id)
                    key = (campo, chunk_id)
                    
                    if key not in field_qa_by_campo_chunk or confianca > field_qa_by_campo_chunk[key]['confianca']:
                        field_qa_by_campo_chunk[key] = {
                            'qa_pair': qa,
                            'chunk': chunk,
                            'confianca': confianca
                        }
                
                # Atualizar progresso fase 1 (50% do progresso total)
                if hasattr(feira, 'qa_progresso_processamento'):
                    progress = min(47, int((i + 1) / total_chunks * 47))
                    feira.qa_progresso_processamento = progress
                    feira.save(update_fields=['qa_progresso_processamento'])
                
                # ADICIONAR: Forçar atualização da feira a cada chunk para manter o status atualizado
                feira.refresh_from_db()
                if feira.qa_processamento_status != 'processando':
                    feira.qa_processamento_status = 'processando'
                    feira.save(update_fields=['qa_processamento_status'])
                
                # Adicionar atraso entre processamentos para não sobrecarregar as APIs
                if i < total_chunks - 1:
                    time.sleep(delay)
            
            except Exception as e:
                logger.error(f"Erro ao processar QAs de campos para chunk {chunk.id}: {str(e)}")
                errors += 1
                # Continuar com o próximo chunk mesmo em caso de erro
        
        # CORREÇÃO: Agora processar os melhores QAs de campos primeiro
        logger.info(f"FASE 1.5: Salvando os melhores QAs de campos ({len(field_qa_by_campo_chunk)} pares)")
        
        # Salvar os QAs específicos de campos antes de prosseguir
        for (campo, chunk_id), info in field_qa_by_campo_chunk.items():
            qa_pair = info['qa_pair']
            chunk = info['chunk']
            
            try:
                # Garantir que similar_questions seja uma lista
                similar_questions = qa_pair.get('sq', [])
                if isinstance(similar_questions, str):
                    try:
                        similar_questions = json.loads(similar_questions)
                    except:
                        similar_questions = similar_questions.split(',')
                
                qa_obj = FeiraManualQA.objects.create(
                    feira=feira,
                    question=qa_pair.get('q', ''),
                    answer=qa_pair.get('a', ''),
                    context=qa_pair.get('t', ''),
                    similar_questions=similar_questions,
                    chunk_id=chunk_id,
                    campo_relacionado=campo,
                    confianca_extracao=info['confianca']
                )
                
                total_qa += 1
                logger.info(f"Salvo QA específico para o campo '{campo}' do chunk {chunk_id} com confiança {info['confianca']:.2f}")
                
            except Exception as e:
                logger.error(f"Erro ao salvar QA para campo {campo}: {str(e)}")
        
        # FASE 2: Agora processar os QAs gerais
        logger.info(f"FASE 2: Processando QAs gerais para todos os chunks")
        
        # Processar chunks até atingir o limite, gerando QAs gerais
        for i, chunk in enumerate(chunks):
            # Verificar se já alcançamos o limite
            if total_qa >= MAX_QA_TOTAL:
                logger.info(f"Limite de {MAX_QA_TOTAL} QAs atingido. Interrompendo o processamento.")
                break
                
            try:
                # Calcular quantos QAs ainda podemos gerar
                qa_space_remaining = MAX_QA_TOTAL - total_qa
                
                if qa_space_remaining <= 0:
                    break
                
                # Gerar QA gerais do chunk
                logger.info(f"Gerando QAs gerais para chunk {i+1}/{total_chunks} (QAs: {total_qa}/{MAX_QA_TOTAL})")
                general_qa_pairs = generator._generate_general_qa_from_chunk(
                    chunk, 
                    feira.description if hasattr(feira, 'description') else None
                )
                
                # Limitar número de pares para não exceder o limite
                pairs_to_save = min(len(general_qa_pairs), qa_space_remaining)
                if pairs_to_save < len(general_qa_pairs):
                    general_qa_pairs = general_qa_pairs[:pairs_to_save]
                
                # Salvar QAs gerais
                saved_pairs = generator.save_qa_pairs(general_qa_pairs, feira, chunk)
                
                # Atualizar contadores
                total_qa += len(saved_pairs)
                processed += 1
                
                # ATUALIZAÇÃO: Atualizar progresso do Q&A (começa em 50% e vai até 95%)
                if hasattr(feira, 'qa_progresso_processamento'):
                    # Calcular progresso com base no número de chunks processados
                    progress = min(95, 48 + int((i + 1) / total_chunks * 47))
                    feira.qa_progresso_processamento = progress
                    feira.save(update_fields=['qa_progresso_processamento'])
                
                logger.info(f"Salvos {len(saved_pairs)} pares Q&A gerais do chunk {i+1}. Total atual: {total_qa}/{MAX_QA_TOTAL}")
                
                # ADICIONAR: Forçar atualização da feira a cada chunk para manter o status atualizado
                feira.refresh_from_db()
                if feira.qa_processamento_status != 'processando':
                    feira.qa_processamento_status = 'processando'
                    feira.save(update_fields=['qa_processamento_status'])
                
                # Adicionar atraso entre processamentos
                if i < total_chunks - 1 and total_qa < MAX_QA_TOTAL:
                    time.sleep(delay)
                    
            except Exception as e:
                logger.error(f"Erro ao processar chunk {chunk.id}: {str(e)}")
                errors += 1
                
                # Continuar com o próximo chunk mesmo em caso de erro
                continue
        
        # Atualizar o status final da feira
        feira.qa_processamento_status = 'concluido'
        feira.qa_processado = True
        feira.qa_total_itens = total_qa
        if hasattr(feira, 'qa_progresso_processamento'):
            feira.qa_progresso_processamento = 100
        feira.save()
        
        # MELHORIA: Registrar uma mensagem no log
        logger.info(f"✓ Status da feira {feira_id} atualizado: qa_processado=True, status='concluido', progresso=100%")
        
        logger.info(f"Processamento de Q&A concluído para feira {feira_id}. Total: {total_qa} QAs, incluindo {len(field_qa_by_campo_chunk)} específicos para campos")
        
        # Estruturar resultado
        result = {
            "status": "success",
            "message": f"Processamento concluído. Gerados {total_qa} pares QA usando o agente '{agent_name}'.",
            "total_chunks": total_chunks,
            "processed_chunks": processed,
            "total_qa": total_qa,
            "field_qa_count": len(field_qa_by_campo_chunk),
            "errors": errors
        }
        
        # Calcular embeddings para os Q&A gerados
        try:
            from core.services.rag_service import RAGService
            
            logger.info(f"Iniciando cálculo de embeddings para {total_qa} pares Q&A da feira {feira_id}")
            rag_service = RAGService()
            embeddings_result = rag_service.atualizar_embeddings_feira(feira_id)
            
            result["embeddings_result"] = embeddings_result
            logger.info(f"Cálculo de embeddings concluído para feira {feira_id}")
            
            # MELHORIA: Garantir que o status ainda está correto após o embedding
            feira.refresh_from_db()
            if feira.qa_processamento_status != 'concluido':
                feira.qa_processamento_status = 'concluido'
                feira.qa_processado = True
                feira.save(update_fields=['qa_processamento_status', 'qa_processado'])
                logger.info(f"✓ Status da feira {feira_id} corrigido após embeddings: qa_processamento_status='concluido'")
            
        except Exception as e:
            logger.error(f"Erro ao calcular embeddings para QA da feira {feira_id}: {str(e)}")
            result["embeddings_error"] = str(e)
        
        return result
        
    except Feira.DoesNotExist:
        return {"status": "error", "message": f"Feira com ID {feira_id} não encontrada"}
    except Exception as e:
        logger.error(f"Erro ao processar feira {feira_id}: {str(e)}")
        
        # Tentar atualizar o status da feira em caso de erro
        try:
            feira = Feira.objects.get(pk=feira_id)
            feira.qa_processamento_status = 'erro'
            feira.qa_mensagem_erro = str(e)
            feira.save()
            logger.info(f"✓ Status de erro atualizado para feira {feira_id}: {str(e)}")
        except Exception as inner_e:
            logger.error(f"Erro ao atualizar status de erro: {str(inner_e)}")
            
        return {"status": "error", "message": str(e)}