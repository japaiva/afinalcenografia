# core/services/crewai/base_service.py - VERSÃO SEM VERBOSE

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
    Serviço CrewAI SIMPLES sem verbose - foco na execução direta
    """
    
    def __init__(self, crew_nome: str):
        self.crew_nome = crew_nome
        self.logger = logging.getLogger(f"crewai.{crew_nome.lower().replace(' ', '_')}")
        self.django_crew = None
        
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
        Executa crew de forma DIRETA - sem logs verbose
        """
        if not CREWAI_AVAILABLE:
            return {'success': False, 'error': 'CrewAI não disponível'}
        
        if not self.django_crew:
            return {'success': False, 'error': f'Crew "{self.crew_nome}" não encontrada'}
        
        try:
            inicio = time.time()
            
            # 1. Criar execução no banco
            execucao = self._criar_execucao(inputs, contexto)
            
            # 2. Log simples de início
            self.logger.info(f"🚀 Iniciando crew '{self.crew_nome}' - Execução ID: {execucao.id}")
            
            # 3. Criar crew framework
            crewai_crew = self._criar_crewai_framework()
            
            if not crewai_crew:
                raise Exception("Falha ao criar CrewAI Framework")
            
            # 4. EXECUTAR CREW DIRETAMENTE
            self.logger.info("⚡ Executando CrewAI kickoff...")
            resultado = crewai_crew.kickoff(inputs=inputs)
            self.logger.info("✅ CrewAI kickoff concluído")
            
            # 5. Finalizar
            tempo_execucao = time.time() - inicio
            self._finalizar_execucao(execucao, resultado, tempo_execucao)
            
            self.logger.info(f"🎯 Pipeline concluído em {tempo_execucao:.1f}s!")
            
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
            
            if 'execucao' in locals():
                self._marcar_execucao_erro(execucao, str(e))
                
            return {'success': False, 'error': str(e)}
    
    def _criar_crewai_framework(self) -> Optional[CrewAI_Framework]:
        """Cria CrewAI Framework de forma DIRETA"""
        try:
            membros = self.django_crew.membros.filter(ativo=True).order_by('ordem_execucao')
            tasks = self.django_crew.tasks.filter(ativo=True).order_by('ordem_execucao')
            
            if not membros.exists() or not tasks.exists():
                raise Exception(f"Crew sem membros ou tasks ativas")
            
            self.logger.info(f"🔧 Criando {membros.count()} agentes e {tasks.count()} tasks")
            
            crewai_agents = []
            crewai_tasks = []
            
            # Criar agentes e tasks
            for i, (membro, task) in enumerate(zip(membros, tasks), 1):
                try:
                    # Validar campos obrigatórios
                    campos_obrigatorios = {
                        'crew_role': membro.agente.crew_role,
                        'crew_goal': membro.agente.crew_goal,
                        'crew_backstory': membro.agente.crew_backstory,
                        'llm_provider': membro.agente.llm_provider,
                        'llm_model': membro.agente.llm_model
                    }
                    
                    for campo, valor in campos_obrigatorios.items():
                        if not valor or str(valor).strip() == '':
                            raise Exception(f"Agente {membro.agente.nome}: campo '{campo}' está vazio")
                    
                    # Criar LLM
                    llm = self._criar_llm_sem_telemetria(membro.agente)
                    
                    # Criar ferramentas
                    tools = self._criar_tools_simples(task.tools_config or {})
                    
                    # Criar agente CrewAI
                    agent = CrewAI_Agent(
                        role=str(membro.agente.crew_role),
                        goal=str(membro.agente.crew_goal),
                        backstory=str(membro.agente.crew_backstory),
                        llm=llm,
                        tools=tools,
                        verbose=True,  # Manter verbose interno do CrewAI
                        allow_delegation=bool(membro.pode_delegar),
                        max_iter=int(membro.max_iter),
                        max_execution_time=int(membro.max_execution_time)
                    )
                    
                    # Validar campos da task
                    if not task.descricao or str(task.descricao).strip() == '':
                        raise Exception(f"Task {task.nome}: campo 'descricao' está vazio")
                    
                    if not task.expected_output or str(task.expected_output).strip() == '':
                        raise Exception(f"Task {task.nome}: campo 'expected_output' está vazio")
                    
                    # Criar task CrewAI
                    crew_task = CrewAI_Task(
                        description=str(task.descricao),
                        expected_output=str(task.expected_output),
                        agent=agent,
                        async_execution=bool(task.async_execution)
                    )
                    
                    if task.output_file:
                        crew_task.output_file = str(task.output_file)
                    
                    crewai_agents.append(agent)
                    crewai_tasks.append(crew_task)
                    
                    self.logger.info(f"✅ Agente {i} ({membro.agente.crew_role}) criado com {len(tools)} tools")
                    
                except Exception as agent_error:
                    self.logger.error(f"❌ Erro ao criar agente {i}: {str(agent_error)}")
                    raise Exception(f"Erro no agente {i} ({membro.agente.nome}): {str(agent_error)}")
            
            # Criar crew
            self.logger.info("🏗️ Montando CrewAI Framework...")
            
            crewai_framework = CrewAI_Framework(
                agents=crewai_agents,
                tasks=crewai_tasks,
                process=str(self.django_crew.processo),
                verbose=True,  # Manter verbose interno
                memory=bool(self.django_crew.memory),
                manager_llm=self._criar_manager_llm() if self.django_crew.processo == 'hierarchical' else None
            )
            
            self.logger.info("✅ CrewAI Framework criado com sucesso")
            
            return crewai_framework
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao criar framework: {str(e)}")
            return None
    
    def _criar_llm_sem_telemetria(self, agente_db):
        """Cria LLM sem telemetria"""
        provider = agente_db.llm_provider.lower()
        
        base_config = {
            'temperature': float(agente_db.llm_temperature),
            'max_tokens': 2000,
            'timeout': 120
        }
        
        if provider == 'openai':
            return ChatOpenAI(
                model=str(agente_db.llm_model),
                api_key=getattr(settings, 'OPENAI_API_KEY', None),
                **base_config
            )
        elif provider == 'anthropic':
            return ChatAnthropic(
                model=str(agente_db.llm_model),
                api_key=getattr(settings, 'ANTHROPIC_API_KEY', None),
                **base_config
            )
        else:
            raise Exception(f"Provider '{provider}' não suportado")
    
    def _criar_tools_simples(self, tools_config: Dict) -> List:
        """Cria tools de forma simples - sem verbose"""
        if not tools_config:
            return []
        
        try:
            from .tools.manager import create_tools_from_config
            
            tools_names = tools_config.get('tools', [])
            if tools_names:
                self.logger.info(f"🔧 Carregando {len(tools_names)} tools: {tools_names}")
            
            # Passar None em vez do verbose_manager
            tools = create_tools_from_config(tools_config, verbose_manager=None)
            
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