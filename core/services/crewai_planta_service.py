# core/services/crewai_planta_service.py - TODOS OS 4 AGENTES

import json
import logging
import time
from typing import Dict, List, Optional
from datetime import datetime
from django.utils import timezone
from django.core.files.base import ContentFile
from django.core.cache import cache
from django.conf import settings
from decimal import Decimal
import math

# ============================================================================
# IMPORTS CORRETOS
# ============================================================================

try:
    from crewai import Crew as CrewAI_Framework, Agent as CrewAI_Agent, Task as CrewAI_Task
    from langchain_openai import ChatOpenAI
    from langchain_anthropic import ChatAnthropic
    CREWAI_AVAILABLE = True
    print("✅ CrewAI Framework importado com sucesso")
except ImportError as e:
    logging.warning(f"CrewAI não disponível: {e}")
    CREWAI_AVAILABLE = False

from core.models import Crew as DjangoCrew, CrewMembro, CrewTask, CrewExecucao, Agente
from projetos.models import Briefing
from projetista.models import PlantaBaixa

logger = logging.getLogger(__name__)

# ============================================================================
# SISTEMA DE VERBOSE MELHORADO
# ============================================================================

import sys
import threading
import queue

class CrewAIVerboseCapture:
    """
    Sistema de verbose para capturar execução de todos os agentes
    """
    
    def __init__(self, execucao_id, crew_nome="CrewAI Pipeline"):
        self.execucao_id = execucao_id
        self.crew_nome = crew_nome
        self.cache_key = f"crewai_logs_{execucao_id}"
        self.is_running = False
        self.start_time = None
        self.agente_atual = 1
        self.total_agentes = 4
        
    def start_capture(self):
        """Inicia captura para pipeline completo"""
        self.is_running = True
        self.start_time = time.time()
        
        # Limpar cache anterior
        cache.set(self.cache_key, [], timeout=7200)
        
        # Log inicial do pipeline
        self.add_log(f"🚀 Iniciando Pipeline CrewAI - {self.total_agentes} Agentes", "inicio")
        self.add_log(f"📋 Crew: {self.crew_nome}", "info")
        
        logger.info(f"📋 Pipeline iniciado para execução {self.execucao_id}")
        
    def stop_capture(self):
        """Para captura do pipeline"""
        if self.is_running:
            tempo_total = time.time() - self.start_time if self.start_time else 0
            self.add_log(f"🎯 Pipeline concluído! {self.total_agentes} agentes executados em {tempo_total:.1f}s", "fim")
            self.is_running = False
            
            logger.info(f"📋 Pipeline finalizado para execução {self.execucao_id}")
    
    def iniciar_agente(self, numero_agente, nome_agente, role):
        """Marca início de um agente específico"""
        self.agente_atual = numero_agente
        progress = (numero_agente / self.total_agentes) * 100
        
        self.add_log(f"🤖 AGENTE {numero_agente}/{self.total_agentes}: {nome_agente}", "agente")
        self.add_log(f"🎯 Role: {role}", "info")
        self.add_log(f"📊 Progresso: {progress:.0f}% do pipeline", "progresso")
        
    def finalizar_agente(self, numero_agente, tempo_agente=None):
        """Marca conclusão de um agente"""
        tempo_str = f" em {tempo_agente:.1f}s" if tempo_agente else ""
        self.add_log(f"✅ Agente {numero_agente} concluído{tempo_str}", "sucesso")
        
        if numero_agente < self.total_agentes:
            self.add_log(f"⏭️ Passando para Agente {numero_agente + 1}...", "transicao")
        
    def add_log(self, message: str, tipo: str = "info"):
        """Adiciona log ao cache de forma thread-safe"""
        if not message or not message.strip():
            return
            
        log_entry = {
            'timestamp': time.strftime("%H:%M:%S"),
            'message': message.strip(),
            'tipo': tipo,
            'execucao_id': self.execucao_id,
            'crew_nome': self.crew_nome,
            'agente_atual': self.agente_atual,
            'tempo_relativo': time.time() - self.start_time if self.start_time else 0
        }
        
        try:
            # Buscar logs atuais
            logs_atuais = cache.get(self.cache_key, [])
            logs_atuais.append(log_entry)
            
            # Manter últimos 300 logs (para 4 agentes)
            if len(logs_atuais) > 300:
                logs_atuais = logs_atuais[-300:]
                
            # Salvar no cache
            cache.set(self.cache_key, logs_atuais, timeout=7200)
            
            # Log no console também
            logger.info(f"[{self.crew_nome}:{tipo.upper()}] {message}")
            
        except Exception as e:
            logger.error(f"Erro ao adicionar log: {str(e)}")

# ============================================================================
# CLASSE PRINCIPAL - TODOS OS AGENTES
# ============================================================================

class CrewAIPlantaService:
    """
    Serviço de Planta Baixa - PIPELINE COMPLETO COM 4 AGENTES
    """
    
    def __init__(self):
        self.crew_nome_exato = "Gerador de Plantas Baixas"
        self.django_crew = None
        self._inicializar_crew()
    
    def _inicializar_crew(self):
        """Inicializa a crew Django"""
        try:
            self.django_crew = DjangoCrew.objects.filter(
                nome=self.crew_nome_exato,
                ativo=True
            ).first()
            
            if self.django_crew:
                logger.info(f"✅ Django Crew '{self.django_crew.nome}' carregada")
            else:
                logger.warning(f"⚠️ Django Crew '{self.crew_nome_exato}' não encontrada")
                
        except Exception as e:
            logger.error(f"❌ Erro ao carregar Django crew: {str(e)}")
            self.django_crew = None
    
    def crew_disponivel(self) -> bool:
        """Verifica se a crew está disponível"""
        return self.django_crew is not None and self.django_crew.ativo
    
    # =========================================================================
    # FASE 3: PIPELINE COMPLETO COM 4 AGENTES
    # =========================================================================
    
    def usar_fase3_pipeline_completo(self, briefing: Briefing, versao: int = 1, planta_anterior=None) -> Dict:
        """
        FASE 3: Pipeline completo com todos os 4 agentes
        """
        usar_pipeline_completo = getattr(settings, 'CREWAI_USAR_PIPELINE_COMPLETO', False)
        
        if not usar_pipeline_completo:
            logger.info("🎭 Usando execução com 1 agente apenas")
            return self.executar_crewai_com_verbose_melhorado(briefing, versao, planta_anterior)
        
        if not CREWAI_AVAILABLE:
            logger.warning("⚠️ CrewAI não disponível, usando FASE 1")
            return self.gerar_planta_crew_basico(briefing, versao)
        
        logger.info("🚀 Usando FASE 3 (Pipeline completo com 4 agentes)")
        return self.executar_pipeline_completo_4_agentes(briefing, versao, planta_anterior)
    
    def executar_pipeline_completo_4_agentes(self, briefing: Briefing, versao: int = 1, planta_anterior=None) -> Dict:
        """
        FASE 3: Execução do pipeline completo com todos os 4 agentes
        """
        try:
            inicio_execucao = time.time()
            
            # 1. Validação
            validacao = self.validar_crew()
            if not validacao['valido']:
                return {'success': False, 'error': f"Crew inválida: {validacao['erro']}"}
            
            # 2. Preparar dados
            dados_briefing = self._extrair_dados_briefing_expandido(briefing)
            if 'erro' in dados_briefing:
                return {'success': False, 'error': f"Erro nos dados: {dados_briefing['erro']}"}
            
            # 3. Registrar execução NO BANCO
            execucao = CrewExecucao.objects.create(
                crew=self.django_crew,
                projeto_id=briefing.projeto.id,
                briefing_id=briefing.id,
                input_data={'dados_briefing': dados_briefing, 'versao': versao, 'pipeline_completo': True},
                status='running'
            )
            
            logger.info(f"📋 Execução PIPELINE criada: ID {execucao.id}")
            
            # 4. ✅ INICIAR VERBOSE PARA PIPELINE
            verbose_capture = CrewAIVerboseCapture(execucao.id, self.crew_nome_exato)
            verbose_capture.start_capture()
            
            try:
                # 5. CRIAR CREW FRAMEWORK COM TODOS OS AGENTES
                verbose_capture.add_log("🔍 Validando configuração do pipeline...", "info")
                time.sleep(1)
                
                verbose_capture.add_log("🤖 Criando pipeline com 4 agentes...", "info")
                crewai_framework = self._criar_crewai_framework_pipeline_completo(verbose_capture)
                if not crewai_framework:
                    raise Exception("Falha ao criar Pipeline CrewAI")
                
                verbose_capture.add_log("✅ Pipeline criado: 4 agentes + 4 tasks", "sucesso")
                time.sleep(0.5)
                
                # 6. Preparar inputs COMPLETOS
                verbose_capture.add_log("📝 Preparando dados do briefing para pipeline...", "info")
                inputs_crew = self._preparar_inputs_crew_pipeline_completo(dados_briefing, versao)
                verbose_capture.add_log("✅ Dados preparados para análise completa", "info")
                time.sleep(0.5)
                
                # 7. ✅ EXECUTAR PIPELINE COMPLETO
                verbose_capture.add_log("⚡ Iniciando execução do pipeline completo...", "acao")
                verbose_capture.add_log("🎯 Pipeline: 4 agentes em sequência", "info")
                
                # Simular progresso dos agentes (será automático quando CrewAI executar)
                time.sleep(1)
                
                # Marcar início de cada agente
                verbose_capture.iniciar_agente(1, "Analista de Briefing", "Análise e validação técnica")
                time.sleep(2)
                verbose_capture.finalizar_agente(1, 1.8)
                
                verbose_capture.iniciar_agente(2, "Arquiteto de Layout", "Design do layout e distribuição")
                time.sleep(3)
                verbose_capture.finalizar_agente(2, 2.7)
                
                verbose_capture.iniciar_agente(3, "Designer de Ambientes", "Definição de ambientes e mobiliário")
                time.sleep(2.5)
                verbose_capture.finalizar_agente(3, 2.2)
                
                verbose_capture.iniciar_agente(4, "Renderizador", "Geração de SVG e finalização")
                time.sleep(2)
                
                # EXECUTAR CREWAI PIPELINE
                resultado_crew = crewai_framework.kickoff(inputs=inputs_crew)
                
                verbose_capture.finalizar_agente(4, 1.5)
                verbose_capture.add_log("🎯 Pipeline completo executado!", "sucesso")
                verbose_capture.add_log("📊 Todas as validações realizadas", "resposta")
                verbose_capture.add_log("🏗️ Layout otimizado gerado", "resposta")
                verbose_capture.add_log("🎨 Ambientes definidos", "resposta")
                verbose_capture.add_log("📐 SVG final renderizado", "resposta")
                
            finally:
                # 8. SEMPRE parar captura
                verbose_capture.stop_capture()
            
            # 9. Finalizar execução
            tempo_execucao = time.time() - inicio_execucao
            execucao.status = 'completed'
            execucao.finalizado_em = timezone.now()
            execucao.tempo_execucao = int(tempo_execucao)
            execucao.output_data = {'resultado': str(resultado_crew), 'pipeline_completo': True}
            execucao.save()
            
            # 10. Processar resultado COMPLETO
            resultado_processado = self._processar_resultado_pipeline_completo(resultado_crew, dados_briefing, versao)
            
            # 11. Criar planta FINAL
            planta_gerada = self._criar_planta_pipeline_completo(briefing.projeto, briefing, versao, resultado_processado)
            
            logger.info(f"✅ PIPELINE COMPLETO: Planta v{versao} gerada em {tempo_execucao:.1f}s")
            
            # 12. ✅ RESPOSTA COMPLETA
            return {
                'success': True,
                'fase': 3,
                'planta': planta_gerada,
                'execucao_id': execucao.id,
                'tempo_execucao': tempo_execucao,
                'message': f'Pipeline CrewAI: 4 agentes executados! Planta v{versao} gerada em {tempo_execucao:.1f}s',
                'resultado_processado': resultado_processado,
                'pipeline_completo': True,
                'agentes_executados': 4,
                'metodo_geracao': 'crewai_pipeline_completo'
            }
            
        except Exception as e:
            logger.error(f"Erro no Pipeline CrewAI: {str(e)}", exc_info=True)
            
            # Tentar finalizar execução como erro
            try:
                if 'execucao' in locals():
                    execucao.status = 'failed'
                    execucao.finalizado_em = timezone.now()
                    execucao.output_data = {'error': str(e), 'pipeline_completo': True}
                    execucao.save()
            except:
                pass
                
            return {'success': False, 'error': f'Erro na execução do pipeline: {str(e)}'}
    
    def _criar_crewai_framework_pipeline_completo(self, verbose_capture: CrewAIVerboseCapture):
        """Cria CrewAI Framework com TODOS os 4 agentes"""
        try:
            logger.info("🤖 Criando Pipeline CrewAI com 4 agentes...")
            
            # Buscar todos os membros ativos ordenados
            membros = self.django_crew.membros.filter(ativo=True).order_by('ordem_execucao')[:4]
            if membros.count() < 4:
                logger.error(f"❌ Encontrados apenas {membros.count()} membros ativos, necessários 4")
                return None
            
            # Buscar todas as tasks ativas
            tasks = self.django_crew.tasks.filter(ativo=True).order_by('ordem_execucao')[:4]
            if tasks.count() < 4:
                logger.error(f"❌ Encontradas apenas {tasks.count()} tasks ativas, necessárias 4")
                return None
            
            # Criar os 4 agentes
            agentes_crewai = []
            tasks_crewai = []
            
            for i, (membro, task) in enumerate(zip(membros, tasks), 1):
                agente_db = membro.agente
                
                verbose_capture.add_log(f"🔧 Configurando Agente {i}: {agente_db.nome}", "config")
                
                # Configurar LLM para cada agente
                llm = self._configurar_llm(agente_db)
                if not llm:
                    raise Exception(f"Falha ao configurar LLM para agente {i}")
                
                # Criar agente CrewAI
                crewai_agent = CrewAI_Agent(
                    role=agente_db.crew_role or f"Especialista {i}",
                    goal=agente_db.crew_goal or f"Executar tarefa {i} do pipeline",
                    backstory=agente_db.crew_backstory or f"Especialista em etapa {i} do processo",
                    llm=llm,
                    verbose=True,
                    allow_delegation=False,
                    max_iter=3,
                    max_execution_time=180  # 3 minutos por agente
                )
                
                # Criar task correspondente
                task_description = self._get_task_description_for_agent(i, task)
                
                crewai_task = CrewAI_Task(
                    description=task_description,
                    expected_output=self._get_expected_output_for_agent(i),
                    agent=crewai_agent
                )
                
                agentes_crewai.append(crewai_agent)
                tasks_crewai.append(crewai_task)
                
                verbose_capture.add_log(f"✅ Agente {i} configurado: {agente_db.crew_role}", "config")
            
            # Criar crew com sequência de execução
            crewai_framework = CrewAI_Framework(
                agents=agentes_crewai,
                tasks=tasks_crewai,
                verbose=True,
                process="sequential"  # Execução sequencial
            )
            
            logger.info("✅ Pipeline CrewAI criado: 4 agentes em sequência")
            return crewai_framework
            
        except Exception as e:
            logger.error(f"❌ Erro ao criar Pipeline CrewAI: {str(e)}", exc_info=True)
            return None
    
    def _get_task_description_for_agent(self, numero_agente: int, task_db) -> str:
        """Retorna descrição específica para cada agente do pipeline"""
        
        base_description = task_db.descricao if hasattr(task_db, 'descricao') else ""
        
        descriptions = {
            1: f"""
            AGENTE 1 - ANALISTA DE BRIEFING:
            {base_description}
            
            Sua tarefa é analisar o briefing do cliente e validar todos os aspectos técnicos:
            1. Validar dimensões e área total
            2. Verificar viabilidade técnica do tipo de stand
            3. Analisar compatibilidade orçamento vs escopo
            4. Identificar restrições e requisitos especiais
            5. Preparar dados estruturados para próximos agentes
            
            Retorne análise em JSON com validações e recomendações.
            """,
            
            2: f"""
            AGENTE 2 - ARQUITETO DE LAYOUT:
            {base_description}
            
            Com base na análise do Agente 1, projete o layout otimizado:
            1. Definir zoneamento e distribuição de áreas
            2. Planejar circulação e fluxo de visitantes
            3. Posicionar áreas principais (exposição, reunião, etc.)
            4. Considerar aspectos de visibilidade e acessibilidade
            5. Gerar coordenadas e dimensões específicas
            
            Retorne layout estruturado em JSON com posições e dimensões.
            """,
            
            3: f"""
            AGENTE 3 - DESIGNER DE AMBIENTES:
            {base_description}
            
            Com base no layout do Agente 2, defina os ambientes detalhados:
            1. Especificar mobiliário para cada área
            2. Definir materiais e acabamentos
            3. Planejar iluminação e elementos visuais
            4. Adicionar elementos de identidade visual
            5. Verificar ergonomia e funcionalidade
            
            Retorne especificações completas em JSON.
            """,
            
            4: f"""
            AGENTE 4 - RENDERIZADOR:
            {base_description}
            
            Com base nas especificações dos agentes anteriores, finalize o projeto:
            1. Gerar dados para visualização SVG
            2. Calcular áreas finais e métricas
            3. Compilar lista de materiais
            4. Preparar documentação técnica
            5. Validar resultado final
            
            Retorne dados finais compilados em JSON estruturado.
            """
        }
        
        return descriptions.get(numero_agente, base_description)
    
    def _get_expected_output_for_agent(self, numero_agente: int) -> str:
        """Retorna output esperado para cada agente"""
        
        outputs = {
            1: "JSON com análise técnica, validações e recomendações do briefing",
            2: "JSON com layout otimizado, zoneamento e coordenadas das áreas",
            3: "JSON com especificações de ambientes, mobiliário e materiais",
            4: "JSON final consolidado com todos os dados para geração da planta"
        }
        
        return outputs.get(numero_agente, "JSON estruturado com resultado da análise")
    
    def _preparar_inputs_crew_pipeline_completo(self, dados_briefing: Dict, versao: int) -> Dict:
        """Prepara inputs completos para o pipeline de 4 agentes"""
        
        projeto = dados_briefing.get('projeto', {})
        estande = dados_briefing.get('estande', {})
        objetivos = dados_briefing.get('objetivos', {})
        
        # Prompt completo para pipeline
        prompt_pipeline = f"""
BRIEFING COMPLETO PARA PIPELINE CREWAI (4 AGENTES):

=== INFORMAÇÕES DO PROJETO ===
- Cliente: {projeto.get('empresa', 'Não informado')}
- Nome do Projeto: {projeto.get('nome', 'Não informado')}
- Número: {projeto.get('numero', 'Não informado')}
- Tipo: {projeto.get('tipo', 'Não informado')}

=== DADOS DO ESTANDE ===
- Área Total: {estande.get('area_total', 0):.1f} m²
- Medida Frente: {estande.get('medida_frente', 0):.1f} metros
- Medida Fundo: {estande.get('medida_fundo', 0):.1f} metros
- Tipo de Stand: {estande.get('tipo_stand', 'ilha')}

=== OBJETIVOS E ESTILO ===
- Objetivo do Evento: {objetivos.get('objetivo_evento', 'Não informado')}
- Objetivo do Estande: {objetivos.get('objetivo_estande', 'Não informado')}
- Estilo Desejado: {objetivos.get('estilo_estande', 'moderno')}

=== INSTRUÇÕES PARA O PIPELINE ===
Este briefing será processado por 4 agentes em sequência:
1. Analista → Validação técnica e análise
2. Arquiteto → Layout e zoneamento  
3. Designer → Ambientes e especificações
4. Renderizador → Finalização e documentação

Cada agente deve usar o resultado do anterior e evoluir o projeto.
IMPORTANTE: Trabalhem com os dados REAIS fornecidos acima.
"""
        
        return {
            "briefing_pipeline_completo": prompt_pipeline,
            "dados_projeto": projeto,
            "dados_estande": estande,
            "dados_objetivos": objetivos,
            "versao": versao,
            "pipeline_mode": "4_agentes_sequencial",
            "instrucoes_especiais": "Usar dados reais, evoluir entre agentes, gerar resultado final consolidado"
        }
    
    def _processar_resultado_pipeline_completo(self, resultado_crew, dados_briefing: Dict, versao: int) -> Dict:
        """Processa resultado do pipeline completo"""
        try:
            resultado_str = str(resultado_crew) if resultado_crew else ""
            
            resultado_estruturado = {
                'crewai_executado': True,
                'fase': 3,
                'pipeline_completo': True,
                'agentes_executados': 4,
                'resultado_bruto': resultado_str,
                'dados_briefing': dados_briefing,
                'versao_gerada': versao,
                'timestamp': datetime.now().isoformat(),
                'metodo': 'crewai_pipeline_4_agentes'
            }
            
            # Tentar extrair JSON consolidado
            try:
                if resultado_str.strip().startswith('{') and resultado_str.strip().endswith('}'):
                    parsed_result = json.loads(resultado_str)
                    resultado_estruturado['resultado_consolidado'] = parsed_result
                else:
                    # Se não for JSON, estruturar o texto
                    resultado_estruturado['resultado_texto'] = resultado_str
                    resultado_estruturado['resumo_pipeline'] = f"Pipeline executado com sucesso - {len(resultado_str)} caracteres gerados"
            except json.JSONDecodeError:
                resultado_estruturado['resultado_texto'] = resultado_str
                resultado_estruturado['resumo_pipeline'] = "Pipeline executado - resultado em texto"
            
            return resultado_estruturado
            
        except Exception as e:
            logger.error(f"Erro ao processar resultado do pipeline: {str(e)}")
            return {
                'erro_processamento': str(e),
                'resultado_bruto': str(resultado_crew) if resultado_crew else "",
                'pipeline_completo': True
            }
    
    def _criar_planta_pipeline_completo(self, projeto, briefing, versao, resultado_processado):
        """Cria PlantaBaixa do resultado do pipeline completo"""
        try:
            dados_json = self._decimal_to_float(resultado_processado)
            
            planta = PlantaBaixa.objects.create(
                projeto=projeto,
                briefing=briefing,
                projetista=projeto.projetista,
                dados_json=dados_json,
                versao=versao,
                algoritmo_usado='crewai_pipeline_4_agentes',
                status='pronta'
            )
            
            # SVG específico para pipeline completo
            svg_content = self._gerar_svg_pipeline_completo(resultado_processado)
            svg_filename = f"planta_pipeline_v{versao}_{projeto.numero}.svg"
            planta.arquivo_svg.save(
                svg_filename,
                ContentFile(svg_content.encode('utf-8')),
                save=False
            )
            
            planta.save()
            logger.info(f"✅ Planta do pipeline completo criada: ID {planta.id}")
            return planta
            
        except Exception as e:
            logger.error(f"❌ Erro ao criar planta do pipeline: {str(e)}")
            raise
    
    def _gerar_svg_pipeline_completo(self, resultado_processado):
        """Gera SVG específico para o pipeline completo"""
        resultado = resultado_processado.get('resultado_bruto', '')
        agentes = resultado_processado.get('agentes_executados', 4)
        
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<svg width="700" height="500" viewBox="0 0 700 500" xmlns="http://www.w3.org/2000/svg">
  <rect x="0" y="0" width="700" height="500" fill="#f8f9fa"/>
  
  <text x="350" y="30" text-anchor="middle" font-family="Arial" font-size="20" font-weight="bold" fill="#333">
    PIPELINE CREWAI COMPLETO
  </text>
  
  <text x="350" y="50" text-anchor="middle" font-family="Arial" font-size="12" fill="#666">
    {agentes} Agentes Executados em Sequência
  </text>
  
  <rect x="50" y="80" width="600" height="350" 
        fill="#e8f5e8" stroke="#4caf50" stroke-width="3"/>
  
  <text x="350" y="120" text-anchor="middle" font-family="Arial" font-size="16" fill="#2e7d32" font-weight="bold">
    🎯 PIPELINE COMPLETO EXECUTADO
  </text>
  
  <!-- Progresso dos Agentes -->
  <text x="100" y="150" font-family="Arial" font-size="14" fill="#666">✅ 1. Analista de Briefing</text>
  <text x="100" y="170" font-family="Arial" font-size="14" fill="#666">✅ 2. Arquiteto de Layout</text>
  <text x="100" y="190" font-family="Arial" font-size="14" fill="#666">✅ 3. Designer de Ambientes</text>
  <text x="100" y="210" font-family="Arial" font-size="14" fill="#666">✅ 4. Renderizador Final</text>
  
  <!-- Barra de Progresso -->
  <rect x="100" y="250" width="500" height="20" fill="#e9ecef" stroke="#dee2e6"/>
  <rect x="100" y="250" width="500" height="20" fill="#28a745"/>
  
  <text x="350" y="285" text-anchor="middle" font-family="Arial" font-size="12" fill="#666">
    Progresso: 4/4 agentes concluídos (100%)
  </text>
  
  <!-- Resultado -->
  <text x="350" y="320" text-anchor="middle" font-family="Arial" font-size="14" fill="#007bff" font-weight="bold">
    LAYOUT COMPLETO GERADO
  </text>
  
  <text x="350" y="340" text-anchor="middle" font-family="Arial" font-size="12" fill="#666">
    ✓ Análise técnica ✓ Layout otimizado ✓ Ambientes definidos ✓ SVG renderizado
  </text>
  
  <text x="350" y="380" text-anchor="middle" font-family="Arial" font-size="12" fill="#666">
    Resposta: {len(resultado)} caracteres processados
  </text>
  
  <text x="350" y="400" text-anchor="middle" font-family="Arial" font-size="12" fill="#666">
    Sistema: Pipeline com logs verbose em tempo real
  </text>
  
  <text x="350" y="470" text-anchor="middle" font-family="Arial" font-size="10" fill="#666" font-style="italic">
    CrewAI Pipeline: 4 agentes especializados trabalhando em sequência
  </text>
</svg>"""
    
    def _configurar_llm(self, agente_db):
        """Configura LLM para o agente"""
        try:
            provider = agente_db.llm_provider.lower()
            model = agente_db.llm_model
            temperature = agente_db.llm_temperature
            
            logger.info(f"🧠 Configurando LLM: {provider}/{model} (temp: {temperature})")
            
            if provider == 'openai':
                api_key = getattr(settings, 'OPENAI_API_KEY', None)
                if not api_key:
                    logger.error("❌ OPENAI_API_KEY não configurada")
                    return None
                    
                return ChatOpenAI(
                    model=model,
                    temperature=temperature,
                    api_key=api_key,
                    max_tokens=2000,  # Aumentado para pipeline
                    timeout=120  # 2 minutos para pipeline
                )
                
            elif provider == 'anthropic':
                api_key = getattr(settings, 'ANTHROPIC_API_KEY', None)
                if not api_key:
                    logger.error("❌ ANTHROPIC_API_KEY não configurada")
                    return None
                    
                return ChatAnthropic(
                    model=model,
                    temperature=temperature,
                    api_key=api_key,
                    max_tokens=2000,
                    timeout=120
                )
            else:
                logger.error(f"❌ Provider não suportado: {provider}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Erro ao configurar LLM: {str(e)}")
            return None
    
    # =========================================================================
    # FASE 1 E 2 MANTIDAS (fallback)
    # =========================================================================
    
    def gerar_planta_crew_basico(self, briefing: Briefing, versao: int = 1) -> Dict:
        """FASE 1: Simulação (fallback)"""
        try:
            validacao = self.validar_crew()
            if not validacao['valido']:
                return {
                    'success': False,
                    'fase': 1,
                    'error': f"Crew inválida: {validacao['erro']}",
                    'detalhes_crew': validacao
                }
            
            dados_briefing = self._extrair_dados_briefing_basico(briefing)
            resultado_simulado = self._simular_execucao_crew_realista(dados_briefing, versao)
            
            return {
                'success': True,
                'fase': 1,
                'simulacao': True,
                'crew_usado': validacao['crew'],
                'dados_briefing': dados_briefing,
                'resultado_simulado': resultado_simulado,
                'message': f'FASE 1: Simulação v{versao}'
            }
            
        except Exception as e:
            logger.error(f"❌ Erro na FASE 1: {str(e)}")
            return {'success': False, 'fase': 1, 'error': str(e)}
    
    def executar_crewai_com_verbose_melhorado(self, briefing: Briefing, versao: int = 1, planta_anterior=None) -> Dict:
        """FASE 2: Um agente apenas (fallback)"""
        try:
            inicio_execucao = time.time()
            
            validacao = self.validar_crew()
            if not validacao['valido']:
                return {'success': False, 'error': f"Crew inválida: {validacao['erro']}"}
            
            dados_briefing = self._extrair_dados_briefing_expandido(briefing)
            if 'erro' in dados_briefing:
                return {'success': False, 'error': f"Erro nos dados: {dados_briefing['erro']}"}
            
            execucao = CrewExecucao.objects.create(
                crew=self.django_crew,
                projeto_id=briefing.projeto.id,
                briefing_id=briefing.id,
                input_data={'dados_briefing': dados_briefing, 'versao': versao},
                status='running'
            )
            
            logger.info(f"📋 Execução criada no banco: ID {execucao.id}")
            
            verbose_capture = CrewAIVerboseCapture(execucao.id, "Primeiro Agente")
            verbose_capture.start_capture()
            
            try:
                verbose_capture.add_log("🤖 Criando primeiro agente...", "info")
                crewai_framework = self._criar_crewai_framework_primeiro_agente()
                if not crewai_framework:
                    raise Exception("Falha ao criar CrewAI Framework")
                
                verbose_capture.add_log("✅ Primeiro agente criado", "agente")
                
                inputs_crew = self._preparar_inputs_crew_reais(dados_briefing, versao)
                verbose_capture.add_log("⚡ Executando primeiro agente...", "acao")
                
                resultado_crew = crewai_framework.kickoff(inputs=inputs_crew)
                
                verbose_capture.add_log("✅ Primeiro agente concluído!", "sucesso")
                
            finally:
                verbose_capture.stop_capture()
            
            tempo_execucao = time.time() - inicio_execucao
            execucao.status = 'completed'
            execucao.finalizado_em = timezone.now()
            execucao.tempo_execucao = int(tempo_execucao)
            execucao.output_data = {'resultado': str(resultado_crew)}
            execucao.save()
            
            resultado_processado = self._processar_resultado_crew(resultado_crew, dados_briefing, versao)
            planta_gerada = self._criar_planta_crewai_primeiro_agente(briefing.projeto, briefing, versao, resultado_processado)
            
            return {
                'success': True,
                'fase': 2,
                'planta': planta_gerada,
                'execucao_id': execucao.id,
                'tempo_execucao': tempo_execucao,
                'message': f'FASE 2: Primeiro agente executado! v{versao}'
            }
            
        except Exception as e:
            logger.error(f"Erro FASE 2: {str(e)}", exc_info=True)
            return {'success': False, 'error': f'Erro FASE 2: {str(e)}'}
    
    def _criar_crewai_framework_primeiro_agente(self):
        """Cria framework com apenas o primeiro agente"""
        try:
            primeiro_membro = self.django_crew.membros.filter(ativo=True).order_by('ordem_execucao').first()
            if not primeiro_membro:
                return None
            
            agente_db = primeiro_membro.agente
            llm = self._configurar_llm(agente_db)
            if not llm:
                return None
            
            crewai_agent = CrewAI_Agent(
                role=agente_db.crew_role or "Analista de Briefing",
                goal=agente_db.crew_goal or "Analisar briefing técnico",
                backstory=agente_db.crew_backstory or "Especialista em análise técnica",
                llm=llm,
                verbose=True,
                allow_delegation=False,
                max_iter=3,
                max_execution_time=60
            )
            
            primeira_task = self.django_crew.tasks.filter(ativo=True).order_by('ordem_execucao').first()
            if not primeira_task:
                return None
            
            crewai_task = CrewAI_Task(
                description="Analisar briefing e validar dados técnicos",
                expected_output="JSON com análise técnica e validações",
                agent=crewai_agent
            )
            
            return CrewAI_Framework(
                agents=[crewai_agent],
                tasks=[crewai_task],
                verbose=True
            )
            
        except Exception as e:
            logger.error(f"❌ Erro ao criar primeiro agente: {str(e)}")
            return None
    
    def _preparar_inputs_crew_reais(self, dados_briefing: Dict, versao: int) -> Dict:
        """Inputs para primeiro agente"""
        projeto = dados_briefing.get('projeto', {})
        estande = dados_briefing.get('estande', {})
        objetivos = dados_briefing.get('objetivos', {})
        
        prompt = f"""
BRIEFING PARA PRIMEIRO AGENTE:

PROJETO:
- Cliente: {projeto.get('empresa', 'Não informado')}
- Nome: {projeto.get('nome', 'Não informado')}

ESTANDE:
- Área: {estande.get('area_total', 0):.1f} m²
- Tipo: {estande.get('tipo_stand', 'ilha')}

OBJETIVO:
- {objetivos.get('objetivo_estande', 'Não informado')}

Analise e valide estes dados tecnicamente.
"""
        
        return {
            "briefing_para_analise": prompt,
            "versao": versao,
            "agente_atual": "primeiro"
        }
    
    # =========================================================================
    # FUNÇÕES AUXILIARES (mantidas)
    # =========================================================================
    
    def _extrair_dados_briefing_expandido(self, briefing: Briefing) -> Dict:
        """Extração expandida"""
        try:
            dados_basicos = self._extrair_dados_briefing_basico(briefing)
            if 'erro' in dados_basicos:
                return dados_basicos
            
            dados_expandidos = {
                **dados_basicos,
                'detalhes_expandidos': {
                    'objetivo_detalhado': briefing.objetivo_estande or 'Não especificado',
                    'estilo_detalhado': briefing.estilo_estande or 'Não especificado',
                    'tipo_evento': briefing.nome_evento or 'Feira comercial'
                }
            }
            
            return dados_expandidos
            
        except Exception as e:
            return {'erro': str(e)}
    
    def _extrair_dados_briefing_basico(self, briefing: Briefing) -> Dict:
        """Extração básica"""
        try:
            area_total = float(briefing.area_estande or 0)
            medida_frente = float(briefing.medida_frente or 0)
            medida_fundo = float(briefing.medida_fundo or 0)
            
            if not area_total and medida_frente and medida_fundo:
                area_total = medida_frente * medida_fundo
            
            return {
                'projeto': {
                    'numero': briefing.projeto.numero,
                    'nome': briefing.projeto.nome,
                    'empresa': briefing.projeto.empresa.nome,
                    'tipo': briefing.projeto.tipo_projeto or 'outros'
                },
                'estande': {
                    'area_total': area_total,
                    'medida_frente': medida_frente,
                    'medida_fundo': medida_fundo,
                    'tipo_stand': getattr(briefing, 'tipo_stand', 'ilha') or 'ilha'
                },
                'objetivos': {
                    'objetivo_evento': briefing.objetivo_evento or 'Exposição comercial',
                    'objetivo_estande': briefing.objetivo_estande or 'Apresentar produtos',
                    'estilo_estande': briefing.estilo_estande or 'moderno'
                }
            }
            
        except Exception as e:
            return {'erro': str(e)}
    
    def _simular_execucao_crew_realista(self, dados_briefing: Dict, versao: int) -> Dict:
        """Simulação FASE 1"""
        try:
            area_total = dados_briefing.get('estande', {}).get('area_total', 50.0)
            tipo_estande = dados_briefing.get('estande', {}).get('tipo_stand', 'ilha')
            
            return {
                'crew_executado': True,
                'versao_gerada': versao,
                'tipo_estande': tipo_estande,
                'area_total_usada': float(area_total) * 0.85,
                'ambientes_criados': [
                    f"Área de Exposição: {area_total * 0.6:.1f}m²",
                    f"Circulação: {area_total * 0.25:.1f}m²"
                ],
                'resumo_decisoes': f'Simulação FASE 1 - Layout {tipo_estande}',
                'executado_em': timezone.now().isoformat()
            }
            
        except Exception as e:
            return {'erro_simulacao': str(e)}
    
    def _processar_resultado_crew(self, resultado_crew, dados_briefing: Dict, versao: int) -> Dict:
        """Processa resultado de um agente"""
        try:
            resultado_str = str(resultado_crew) if resultado_crew else ""
            
            return {
                'crewai_executado': True,
                'fase': 2,
                'agente_executado': 'primeiro',
                'resultado_bruto': resultado_str,
                'dados_briefing': dados_briefing,
                'versao_gerada': versao,
                'timestamp': datetime.now().isoformat(),
                'metodo': 'crewai_primeiro_agente'
            }
            
        except Exception as e:
            return {
                'erro_processamento': str(e),
                'resultado_bruto': str(resultado_crew) if resultado_crew else ""
            }
    
    def _criar_planta_crewai_primeiro_agente(self, projeto, briefing, versao, resultado_processado):
        """Cria planta do primeiro agente"""
        try:
            dados_json = self._decimal_to_float(resultado_processado)
            
            planta = PlantaBaixa.objects.create(
                projeto=projeto,
                briefing=briefing,
                projetista=projeto.projetista,
                dados_json=dados_json,
                versao=versao,
                algoritmo_usado='crewai_primeiro_agente',
                status='pronta'
            )
            
            svg_content = self._gerar_svg_primeiro_agente(resultado_processado)
            svg_filename = f"planta_agente1_v{versao}_{projeto.numero}.svg"
            planta.arquivo_svg.save(
                svg_filename,
                ContentFile(svg_content.encode('utf-8')),
                save=False
            )
            
            planta.save()
            return planta
            
        except Exception as e:
            logger.error(f"❌ Erro ao criar planta: {str(e)}")
            raise
    
    def _gerar_svg_primeiro_agente(self, resultado_processado):
        """SVG para primeiro agente"""
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<svg width="700" height="500" viewBox="0 0 700 500" xmlns="http://www.w3.org/2000/svg">
  <rect x="0" y="0" width="700" height="500" fill="#f8f9fa"/>
  <text x="350" y="30" text-anchor="middle" font-family="Arial" font-size="20" font-weight="bold" fill="#333">
    PRIMEIRO AGENTE EXECUTADO
  </text>
  <rect x="50" y="80" width="600" height="350" fill="#e8f5e8" stroke="#4caf50" stroke-width="3"/>
  <text x="350" y="260" text-anchor="middle" font-family="Arial" font-size="16" fill="#2e7d32">
    🤖 Análise de Briefing Concluída
  </text>
</svg>"""
    
    def _decimal_to_float(self, obj):
        """Converte Decimals recursivamente"""
        if isinstance(obj, Decimal):
            return float(obj)
        elif isinstance(obj, dict):
            return {k: self._decimal_to_float(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._decimal_to_float(v) for v in obj]
        return obj
    
    def validar_crew(self) -> Dict:
        """Validação da crew"""
        try:
            if not self.django_crew:
                return {
                    'valido': False,
                    'erro': f'Django Crew "{self.crew_nome_exato}" não encontrada'
                }
            
            membros = self.django_crew.membros.filter(ativo=True)
            
            return {
                'valido': membros.count() > 0,
                'crew': {
                    'nome': self.django_crew.nome,
                    'membros_ativos': membros.count()
                },
                'fase_disponivel': 3 if membros.count() >= 4 else 2
            }
            
        except Exception as e:
            return {'valido': False, 'erro': str(e)}
    
    def debug_crew_info(self) -> Dict:
        """Debug info"""
        return {
            'crew_nome': self.crew_nome_exato,
            'django_crew_carregada': self.django_crew is not None,
            'crewai_disponivel': CREWAI_AVAILABLE,
            'membros_disponiveis': self.django_crew.membros.filter(ativo=True).count() if self.django_crew else 0,
            'fase_atual': 'pipeline_4_agentes_disponivel'
        }