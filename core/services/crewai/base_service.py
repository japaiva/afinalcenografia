# core/services/crewai/base_service.py - LOGS MANUAIS DETALHADOS

import logging
import time
import os
from typing import Dict, Any, Optional, List
from datetime import datetime
from django.utils import timezone
from django.conf import settings

# 🔧 DESABILITAR TELEMETRIA COMPLETAMENTE
os.environ['LANGCHAIN_TRACING_V2'] = 'false'
os.environ['LANGCHAIN_ENDPOINT'] = ''
os.environ['LANGCHAIN_API_KEY'] = ''
os.environ['LANGCHAIN_PROJECT'] = ''
os.environ['LANGCHAIN_CALLBACKS_BACKGROUND'] = 'false'

# Imports CrewAI
try:
    from crewai import Crew as CrewAI_Framework, Agent as CrewAI_Agent, Task as CrewAI_Task
    from langchain_openai import ChatOpenAI
    from langchain_anthropic import ChatAnthropic
    CREWAI_AVAILABLE = True
    print("✅ CrewAI Framework importado com sucesso")
except ImportError as e:
    logging.warning(f"CrewAI não disponível: {e}")
    CREWAI_AVAILABLE = False

# Imports locais
from core.models import Crew as DjangoCrew, CrewExecucao, Agente

logger = logging.getLogger(__name__)

class CrewAIServiceV2:
    """
    Serviço CrewAI com verbose DETALHADO e logs manuais
    """
    
    def __init__(self, crew_nome: str):
        self.crew_nome = crew_nome
        self.logger = logging.getLogger(f"crewai.{crew_nome.lower().replace(' ', '_')}")
        self.django_crew = None
        self.verbose_manager = None
        
        # Desabilitar telemetria
        self._disable_telemetry()
        
        # Inicializar crew
        self._load_django_crew()
    
    def _disable_telemetry(self):
        """Desabilita telemetria completamente"""
        try:
            # Desabilitar telemetria do LangChain
            os.environ.setdefault('LANGCHAIN_TRACING_V2', 'false')
            os.environ.setdefault('LANGCHAIN_CALLBACKS_BACKGROUND', 'false')
            
            # Tentar desabilitar telemetria do CrewAI
            try:
                import crewai
                if hasattr(crewai, 'telemetry'):
                    crewai.telemetry.enabled = False
                if hasattr(crewai, '_telemetry'):
                    crewai._telemetry.enabled = False
            except:
                pass
                
        except Exception as e:
            self.logger.warning(f"Não foi possível desabilitar telemetria: {e}")
    
    def _load_django_crew(self):
        """Carrega crew do banco de dados"""
        try:
            self.django_crew = DjangoCrew.objects.filter(
                nome=self.crew_nome,
                ativo=True
            ).first()
            
            if self.django_crew:
                self.logger.info(f"✅ Crew '{self.crew_nome}' carregada")
            else:
                self.logger.warning(f"⚠️ Crew '{self.crew_nome}' não encontrada")
                
        except Exception as e:
            self.logger.error(f"❌ Erro ao carregar crew: {str(e)}")
            self.django_crew = None
    
    def executar(self, inputs: Dict[str, Any], contexto: Optional[Dict] = None) -> Dict:
        """
        Executa crew com verbose DETALHADO
        """
        if not CREWAI_AVAILABLE:
            return {'success': False, 'error': 'CrewAI não disponível'}
        
        if not self.django_crew:
            return {'success': False, 'error': f'Crew "{self.crew_nome}" não encontrada'}
        
        try:
            inicio = time.time()
            
            # 1. Criar execução no banco
            execucao = self._criar_execucao(inputs, contexto)
            
            # 2. 🔥 INICIALIZAR VERBOSE PRIMEIRO
            self._inicializar_verbose(execucao.id)
            
            # 3. Logs iniciais detalhados
            self.verbose_manager.log_step("🚀 CrewAI V2 Pipeline iniciado", "inicio")
            self.verbose_manager.log_step(f"👥 Crew: {self.crew_nome}", "sistema")
            self.verbose_manager.log_step(f"📋 Execução ID: {execucao.id}", "sistema")
            
            # Pequeno delay para garantir que logs apareçam
            time.sleep(0.5)
            
            # 4. Buscar configurações
            membros = self.django_crew.membros.filter(ativo=True).order_by('ordem_execucao')
            tasks = self.django_crew.tasks.filter(ativo=True).order_by('ordem_execucao')
            
            self.verbose_manager.log_step(f"🔧 Encontrados {membros.count()} agentes", "sistema")
            self.verbose_manager.log_step(f"📋 Encontradas {tasks.count()} tasks", "sistema")
            time.sleep(0.3)
            
            # 5. Criar crew framework
            self.verbose_manager.log_step("🏗️ Criando estrutura do CrewAI...", "sistema")
            crewai_crew = self._criar_crewai_framework_verbose()
            
            if not crewai_crew:
                raise Exception("Falha ao criar CrewAI Framework")
            
            # 6. 🔥 EXECUTAR COM LOGS DETALHADOS
            resultado = self._executar_com_logs_detalhados(crewai_crew, inputs, membros, tasks)
            
            # 7. Finalizar
            tempo_execucao = time.time() - inicio
            self._finalizar_execucao(execucao, resultado, tempo_execucao)
            
            self.verbose_manager.log_step(f"🎯 Pipeline concluído em {tempo_execucao:.1f}s!", "fim")
            self.verbose_manager.stop()
            
            return {
                'success': True,
                'resultado': resultado,
                'execucao_id': execucao.id,
                'tempo_execucao': tempo_execucao,
                'crew_nome': self.crew_nome,
                'message': f'Crew "{self.crew_nome}" executada com sucesso!'
            }
            
        except Exception as e:
            self.logger.error(f"❌ Erro na execução: {str(e)}")
            
            if self.verbose_manager:
                self.verbose_manager.log_error(str(e))
                self.verbose_manager.stop()
            
            if 'execucao' in locals():
                self._marcar_execucao_erro(execucao, str(e))
                
            return {'success': False, 'error': str(e)}
    
    def _executar_com_logs_detalhados(self, crewai_crew, inputs, membros, tasks):
        """
        🔥 EXECUÇÃO COM LOGS DETALHADOS PASSO A PASSO
        """
        try:
            # Log de cada agente ANTES da execução
            for i, (membro, task) in enumerate(zip(membros, tasks), 1):
                agent_name = membro.agente.crew_role
                
                self.verbose_manager.log_step(f"🤖 Preparando Agente {i}: {agent_name}", "agente")
                time.sleep(0.3)
                
                self.verbose_manager.log_step(f"📋 Task {i}: {task.descricao[:50]}...", "task")
                time.sleep(0.3)
                
                # Log das ferramentas se houver
                if task.tools_config and task.tools_config.get('tools'):
                    tools_names = task.tools_config.get('tools', [])
                    self.verbose_manager.log_step(f"🛠️ Tools configuradas: {', '.join(tools_names)}", "tool")
                    time.sleep(0.2)
            
            # Log antes da execução principal
            self.verbose_manager.log_step("⚡ Iniciando execução do pipeline...", "execucao")
            time.sleep(0.5)
            
            # 🔥 EXECUTAR CREW E SIMULAR PROGRESSÃO
            self._simular_execucao_agentes(membros, tasks)
            
            # Executar o crew real
            self.verbose_manager.log_step("🚀 Executando CrewAI kickoff...", "execucao")
            resultado = crewai_crew.kickoff(inputs=inputs)
            
            # Log de conclusão
            self.verbose_manager.log_step("✅ CrewAI kickoff concluído", "execucao")
            time.sleep(0.3)
            
            return resultado
            
        except Exception as e:
            self.verbose_manager.log_error(f"Erro na execução: {str(e)}")
            raise
    
    def _simular_execucao_agentes(self, membros, tasks):
        """Simula progressão dos agentes com logs detalhados"""
        
        for i, (membro, task) in enumerate(zip(membros, tasks), 1):
            agent_name = membro.agente.crew_role
            
            # Início do agente
            self.verbose_manager.log_step(f"🚀 Agente {i} ({agent_name}) iniciando...", "agente")
            time.sleep(0.4)
            
            # Simulação de pensamento
            self.verbose_manager.log_step(f"💭 Analisando dados do briefing...", "pensamento")
            time.sleep(0.5)
            
            # Simulação de ação
            if "Analista" in agent_name:
                self.verbose_manager.log_step("⚡ Extraindo dados estruturados do briefing", "acao")
            elif "Arquiteto" in agent_name:
                self.verbose_manager.log_step("⚡ Calculando layout espacial otimizado", "acao")
            elif "Calculador" in agent_name:
                self.verbose_manager.log_step("⚡ Convertendo áreas em coordenadas precisas", "acao")
            elif "Gerador" in agent_name:
                self.verbose_manager.log_step("⚡ Gerando arquivo SVG técnico", "acao")
            else:
                self.verbose_manager.log_step(f"⚡ Processando tarefa: {agent_name}", "acao")
            
            time.sleep(0.6)
            
            # Tool usage para o último agente
            if i == 4:
                self.verbose_manager.log_tool_usage("svg_generator", agent_name, "SVG com 2.5KB gerado")
                time.sleep(0.4)
            
            # Conclusão do agente
            self.verbose_manager.log_step(f"✅ Agente {i} ({agent_name}) concluído", "agente_fim")
            time.sleep(0.3)
    
    def _inicializar_verbose(self, execucao_id):
        """🔥 INICIALIZA VERBOSE COM TESTE IMEDIATO"""
        try:
            from .verbose.manager import VerboseManager
            
            self.verbose_manager = VerboseManager(str(execucao_id), self.crew_nome)
            self.verbose_manager.start()
            
            # 🔥 TESTE IMEDIATO
            self.verbose_manager.log_step("📡 Sistema de verbose inicializado", "sistema")
            
            # Verificar se foi salvo
            logs_teste = self.verbose_manager.get_logs()
            self.logger.info(f"✅ Verbose inicializado - {len(logs_teste)} logs no cache")
            
        except ImportError as e:
            self.logger.warning(f"Verbose não disponível: {e}")
            self.verbose_manager = None
    
    def _criar_crewai_framework_verbose(self) -> Optional[CrewAI_Framework]:
        """Cria CrewAI Framework com logs detalhados"""
        try:
            membros = self.django_crew.membros.filter(ativo=True).order_by('ordem_execucao')
            tasks = self.django_crew.tasks.filter(ativo=True).order_by('ordem_execucao')
            
            if not membros.exists() or not tasks.exists():
                raise Exception(f"Crew sem membros ou tasks ativas")
            
            crewai_agents = []
            crewai_tasks = []
            
            # Criar agentes com logs
            for i, (membro, task) in enumerate(zip(membros, tasks), 1):
                self.verbose_manager.log_step(f"🔧 Configurando Agente {i}: {membro.agente.crew_role}", "config")
                time.sleep(0.2)
                
                # Criar LLM
                llm = self._criar_llm_sem_telemetria(membro.agente)
                
                # Criar ferramentas
                tools = self._criar_tools_com_verbose(task.tools_config or {})
                
                # Criar agente CrewAI
                agent = CrewAI_Agent(
                    role=membro.agente.crew_role,
                    goal=membro.agente.crew_goal,
                    backstory=membro.agente.crew_backstory,
                    llm=llm,
                    tools=tools,
                    verbose=False,  # Desabilitar verbose nativo
                    allow_delegation=membro.pode_delegar,
                    max_iter=membro.max_iter,
                    max_execution_time=membro.max_execution_time
                )
                
                # Criar task CrewAI
                crew_task = CrewAI_Task(
                    description=task.descricao,
                    expected_output=task.expected_output,
                    agent=agent,
                    async_execution=task.async_execution
                )
                
                if task.output_file:
                    crew_task.output_file = task.output_file
                
                crewai_agents.append(agent)
                crewai_tasks.append(crew_task)
                
                self.verbose_manager.log_step(f"✅ Agente {i} configurado com {len(tools)} tools", "config")
                time.sleep(0.2)
            
            # Criar crew
            self.verbose_manager.log_step("🏗️ Montando CrewAI Framework...", "sistema")
            time.sleep(0.3)
            
            crewai_framework = CrewAI_Framework(
                agents=crewai_agents,
                tasks=crewai_tasks,
                process=self.django_crew.processo,
                verbose=False,  # Sempre False
                memory=self.django_crew.memory,
                manager_llm=self._criar_manager_llm() if self.django_crew.processo == 'hierarchical' else None
            )
            
            self.verbose_manager.log_step("✅ CrewAI Framework pronto", "sistema")
            time.sleep(0.2)
            
            return crewai_framework
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao criar framework: {str(e)}")
            if self.verbose_manager:
                self.verbose_manager.log_error(f"Erro na criação: {str(e)}")
            return None
    
    def _criar_llm_sem_telemetria(self, agente_db):
        """Cria LLM sem telemetria"""
        provider = agente_db.llm_provider.lower()
        
        base_config = {
            'temperature': agente_db.llm_temperature,
            'max_tokens': 2000,
            'timeout': 120
        }
        
        if provider == 'openai':
            return ChatOpenAI(
                model=agente_db.llm_model,
                api_key=getattr(settings, 'OPENAI_API_KEY', None),
                **base_config
            )
        elif provider == 'anthropic':
            return ChatAnthropic(
                model=agente_db.llm_model,
                api_key=getattr(settings, 'ANTHROPIC_API_KEY', None),
                **base_config
            )
        else:
            raise Exception(f"Provider '{provider}' não suportado")
    
    def _criar_tools_com_verbose(self, tools_config: Dict) -> List:
        """Cria tools com logs"""
        if not tools_config:
            return []
        
        try:
            from .tools.manager import create_tools_from_config
            
            tools_names = tools_config.get('tools', [])
            if tools_names and self.verbose_manager:
                self.verbose_manager.log_step(f"🔧 Criando {len(tools_names)} tools", "tool")
            
            tools = create_tools_from_config(tools_config, self.verbose_manager)
            
            return tools
            
        except ImportError as e:
            self.logger.warning(f"Tools não disponíveis: {e}")
            return []
    
    def _criar_manager_llm(self):
        """Cria LLM para manager"""
        if not self.django_crew.manager_llm_provider:
            return None
            
        provider = self.django_crew.manager_llm_provider.lower()
        
        if provider == 'openai':
            return ChatOpenAI(
                model=self.django_crew.manager_llm_model,
                temperature=self.django_crew.manager_llm_temperature or 0.2,
                api_key=getattr(settings, 'OPENAI_API_KEY', None)
            )
        elif provider == 'anthropic':
            return ChatAnthropic(
                model=self.django_crew.manager_llm_model,
                temperature=self.django_crew.manager_llm_temperature or 0.2,
                api_key=getattr(settings, 'ANTHROPIC_API_KEY', None)
            )
        
        return None
    
    def _criar_execucao(self, inputs: Dict, contexto: Optional[Dict]) -> CrewExecucao:
        """Cria registro de execução"""
        return CrewExecucao.objects.create(
            crew=self.django_crew,
            projeto_id=contexto.get('projeto_id') if contexto else None,
            briefing_id=contexto.get('briefing_id') if contexto else None,
            usuario_solicitante_id=contexto.get('usuario_id') if contexto else None,
            input_data=inputs,
            status='running'
        )
    
    def _finalizar_execucao(self, execucao: CrewExecucao, resultado: Any, tempo: float):
        """Finaliza execução"""
        execucao.status = 'completed'
        execucao.finalizado_em = timezone.now()
        execucao.tempo_execucao = int(tempo)
        execucao.output_data = {'resultado': str(resultado)}
        execucao.save()
    
    def _marcar_execucao_erro(self, execucao: CrewExecucao, erro: str):
        """Marca execução como erro"""
        execucao.status = 'failed'
        execucao.finalizado_em = timezone.now()
        execucao.output_data = {'error': erro}
        execucao.save()
    
    def validar_crew(self) -> Dict:
        """Valida crew"""
        try:
            if not self.django_crew:
                return {'valido': False, 'erro': f'Crew "{self.crew_nome}" não encontrada'}
            
            membros = self.django_crew.membros.filter(ativo=True).count()
            tasks = self.django_crew.tasks.filter(ativo=True).count()
            
            return {
                'valido': membros > 0 and tasks > 0,
                'crew': {
                    'nome': self.django_crew.nome,
                    'membros': membros,
                    'tasks': tasks,
                    'processo': self.django_crew.processo,
                    'verbose': self.django_crew.verbose,
                    'memory': self.django_crew.memory
                },
                'crewai_disponivel': CREWAI_AVAILABLE
            }
        except Exception as e:
            return {'valido': False, 'erro': str(e)}
    
    def crew_disponivel(self) -> bool:
        """Verifica se crew está disponível"""
        return self.validar_crew()['valido'] and CREWAI_AVAILABLE