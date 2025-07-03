# core/services/crewai/base_service.py

import logging
import time
from typing import Dict, Any, Optional, List
from datetime import datetime
from django.utils import timezone
from django.conf import settings

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
    Serviço CrewAI melhorado com arquitetura escalável
    """
    
    def __init__(self, crew_nome: str):
        self.crew_nome = crew_nome
        self.logger = logging.getLogger(f"crewai.{crew_nome.lower().replace(' ', '_')}")
        self.django_crew = None
        self.verbose_manager = None
        self.callback_manager = None
        
        # Inicializar crew
        self._load_django_crew()
    
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
        Executa crew com verbose melhorado
        """
        if not CREWAI_AVAILABLE:
            return {'success': False, 'error': 'CrewAI não disponível'}
        
        if not self.django_crew:
            return {'success': False, 'error': f'Crew "{self.crew_nome}" não encontrada'}
        
        try:
            inicio = time.time()
            
            # 1. Criar execução no banco
            execucao = self._criar_execucao(inputs, contexto)
            
            # 2. Inicializar sistema de verbose
            self._inicializar_verbose(execucao.id)
            
            # 3. Criar crew framework
            self.verbose_manager.log_step("🏗️ Criando estrutura do crew...", "sistema")
            crewai_crew = self._criar_crewai_framework()
            
            if not crewai_crew:
                raise Exception("Falha ao criar CrewAI Framework")
            
            # 4. Executar crew
            self.verbose_manager.log_step("🚀 Iniciando execução do pipeline...", "sistema")
            resultado = crewai_crew.kickoff(inputs=inputs)
            
            # 5. Finalizar execução
            tempo_execucao = time.time() - inicio
            self._finalizar_execucao(execucao, resultado, tempo_execucao)
            
            self.verbose_manager.log_step("🎯 Pipeline concluído com sucesso!", "sistema")
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
    
    def _inicializar_verbose(self, execucao_id):
        """Inicializa sistema de verbose"""
        try:
            # Import aqui para evitar circular import
            from .verbose.manager import VerboseManager
            from .verbose.callbacks import CrewAICallbackManager
            
            self.verbose_manager = VerboseManager(str(execucao_id), self.crew_nome)
            self.callback_manager = CrewAICallbackManager(self.verbose_manager)
            self.verbose_manager.start()
            
        except ImportError as e:
            self.logger.warning(f"Verbose não disponível: {e}")
            self.verbose_manager = None
            self.callback_manager = None
    
    def _criar_crewai_framework(self) -> Optional[CrewAI_Framework]:
        """
        Cria CrewAI Framework com verbose integrado
        """
        try:
            # Buscar agentes e tasks
            membros = self.django_crew.membros.filter(ativo=True).order_by('ordem_execucao')
            tasks = self.django_crew.tasks.filter(ativo=True).order_by('ordem_execucao')
            
            if not membros.exists() or not tasks.exists():
                raise Exception(f"Crew sem membros ou tasks ativas")
            
            if self.verbose_manager:
                self.verbose_manager.log_step(f"👥 {membros.count()} agentes encontrados", "sistema")
                self.verbose_manager.log_step(f"📋 {tasks.count()} tasks configuradas", "sistema")
            
            crewai_agents = []
            crewai_tasks = []
            
            # Criar agentes e tasks
            for i, (membro, task) in enumerate(zip(membros, tasks), 1):
                # Log do agente sendo criado
                if self.verbose_manager:
                    self.verbose_manager.log_step(
                        f"🤖 Configurando Agente {i}: {membro.agente.crew_role}", 
                        "agente"
                    )
                
                # Criar LLM
                llm = self._criar_llm(membro.agente)
                
                # Criar ferramentas com verbose manager
                tools = self._criar_tools_com_verbose(task.tools_config or {})
                
                # Criar agente CrewAI
                agent = CrewAI_Agent(
                    role=membro.agente.crew_role,
                    goal=membro.agente.crew_goal,
                    backstory=membro.agente.crew_backstory,
                    llm=llm,
                    tools=tools,
                    verbose=True,
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
                
                # Output file se especificado
                if task.output_file:
                    crew_task.output_file = task.output_file
                
                crewai_agents.append(agent)
                crewai_tasks.append(crew_task)
                
                if self.verbose_manager:
                    self.verbose_manager.log_step(
                        f"✅ Agente {i} configurado: {len(tools)} tools", 
                        "agente"
                    )
            
            # Criar crew
            crewai_framework = CrewAI_Framework(
                agents=crewai_agents,
                tasks=crewai_tasks,
                process=self.django_crew.processo,
                verbose=self.django_crew.verbose,
                memory=self.django_crew.memory,
                # Manager LLM para processo hierárquico
                manager_llm=self._criar_manager_llm() if self.django_crew.processo == 'hierarchical' else None
            )
            
            if self.verbose_manager:
                self.verbose_manager.log_step("🏗️ Crew framework criado com sucesso", "sistema")
            
            return crewai_framework
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao criar framework: {str(e)}")
            if self.verbose_manager:
                self.verbose_manager.log_error(f"Erro na criação do framework: {str(e)}")
            return None
    
    def _criar_tools_com_verbose(self, tools_config: Dict) -> List:
        """
        Cria tools injetando verbose manager
        """
        if not tools_config:
            return []
        
        try:
            # Import aqui para evitar circular import
            from .tools.manager import create_tools_from_config
            
            # Log das tools sendo criadas
            tools_names = tools_config.get('tools', [])
            if tools_names and self.verbose_manager:
                self.verbose_manager.log_step(f"🛠️ Configurando {len(tools_names)} tools", "tool")
            
            # Criar tools usando o sistema existente
            tools = create_tools_from_config(tools_config, self.verbose_manager)
            
            # Log das tools criadas
            if self.verbose_manager:
                for tool in tools:
                    if hasattr(tool, 'name'):
                        self.verbose_manager.log_step(f"🔧 Tool '{tool.name}' configurada", "tool")
            
            return tools
            
        except ImportError as e:
            self.logger.warning(f"Tools não disponíveis: {e}")
            return []
    
    def _criar_llm(self, agente_db):
        """Cria LLM para agente"""
        provider = agente_db.llm_provider.lower()
        
        if provider == 'openai':
            return ChatOpenAI(
                model=agente_db.llm_model,
                temperature=agente_db.llm_temperature,
                api_key=getattr(settings, 'OPENAI_API_KEY', None),
                max_tokens=2000,
                timeout=120
            )
        elif provider == 'anthropic':
            return ChatAnthropic(
                model=agente_db.llm_model,
                temperature=agente_db.llm_temperature,
                api_key=getattr(settings, 'ANTHROPIC_API_KEY', None),
                max_tokens=2000,
                timeout=120
            )
        else:
            raise Exception(f"Provider '{provider}' não suportado")
    
    def _criar_manager_llm(self):
        """Cria LLM para manager (processo hierárquico)"""
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
        """Finaliza execução com sucesso"""
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
        """Valida se crew está configurada corretamente"""
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