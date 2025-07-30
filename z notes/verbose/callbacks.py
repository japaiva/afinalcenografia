# core/services/crewai/verbose/callbacks.py

import logging
from typing import Dict, Any, Optional
import time

logger = logging.getLogger(__name__)

class VerboseCallbackHandler:
    """
    Handler de callbacks para interceptar eventos do CrewAI e enviar para VerboseManager
    
    Este sistema captura eventos nativos do CrewAI e os converte em logs estruturados
    para o sistema de verbose em tempo real.
    """
    
    def __init__(self, verbose_manager):
        self.verbose_manager = verbose_manager
        self.current_agent = None
        self.current_task = None
        self.task_start_time = None
        self.agent_start_time = None
        
    # =========================================================================
    # CALLBACKS DE AGENTES
    # =========================================================================
    
    def on_agent_start(self, agent, **kwargs):
        """Callback quando um agente inicia"""
        try:
            agent_name = self._extract_agent_name(agent)
            agent_role = self._extract_agent_role(agent)
            
            self.current_agent = agent_name
            self.agent_start_time = time.time()
            
            self.verbose_manager.log_agent_start(
                agent_name=agent_name,
                role=agent_role
            )
            
            logger.debug(f"📍 Agente iniciado: {agent_name}")
            
        except Exception as e:
            logger.error(f"Erro no callback on_agent_start: {e}")
    
    def on_agent_finish(self, agent, output=None, **kwargs):
        """Callback quando um agente termina"""
        try:
            agent_name = self._extract_agent_name(agent)
            
            # Calcular tempo de execução do agente
            execution_time = 0
            if self.agent_start_time:
                execution_time = time.time() - self.agent_start_time
            
            # Resumir output se disponível
            output_summary = self._summarize_output(output)
            
            self.verbose_manager.log_step(
                f"✅ Agente '{agent_name}' concluído em {execution_time:.1f}s",
                "agente_fim"
            )
            
            if output_summary:
                self.verbose_manager.log_response(
                    response_summary=output_summary,
                    agent_name=agent_name
                )
            
            logger.debug(f"🎯 Agente finalizado: {agent_name} ({execution_time:.1f}s)")
            
        except Exception as e:
            logger.error(f"Erro no callback on_agent_finish: {e}")
    
    # =========================================================================
    # CALLBACKS DE TASKS
    # =========================================================================
    
    def on_task_start(self, task, agent, **kwargs):
        """Callback quando uma task inicia"""
        try:
            task_name = self._extract_task_name(task)
            agent_name = self._extract_agent_name(agent)
            
            self.current_task = task_name
            self.task_start_time = time.time()
            
            self.verbose_manager.log_task_start(
                task_name=task_name,
                agent_name=agent_name
            )
            
            # Log adicional com descrição da task se disponível
            task_description = self._extract_task_description(task)
            if task_description:
                self.verbose_manager.log_step(
                    f"📋 Objetivo: {task_description[:100]}...",
                    "task_objetivo"
                )
            
            logger.debug(f"📋 Task iniciada: {task_name} por {agent_name}")
            
        except Exception as e:
            logger.error(f"Erro no callback on_task_start: {e}")
    
    def on_task_finish(self, task, agent, output=None, **kwargs):
        """Callback quando uma task termina"""
        try:
            task_name = self._extract_task_name(task)
            agent_name = self._extract_agent_name(agent)
            
            # Calcular tempo de execução da task
            execution_time = 0
            if self.task_start_time:
                execution_time = time.time() - self.task_start_time
            
            # Resumir output
            output_summary = self._summarize_output(output)
            
            self.verbose_manager.log_step(
                f"✅ Task '{task_name}' concluída em {execution_time:.1f}s",
                "task_fim"
            )
            
            if output_summary:
                self.verbose_manager.log_response(
                    response_summary=output_summary,
                    agent_name=agent_name
                )
            
            logger.debug(f"🎯 Task finalizada: {task_name} ({execution_time:.1f}s)")
            
        except Exception as e:
            logger.error(f"Erro no callback on_task_finish: {e}")
    
    # =========================================================================
    # CALLBACKS DE PENSAMENTO E AÇÃO
    # =========================================================================
    
    def on_agent_thinking(self, agent, message: str, **kwargs):
        """Callback quando agente está 'pensando'"""
        try:
            agent_name = self._extract_agent_name(agent)
            
            # Limitar tamanho da mensagem
            thinking_message = message[:150] + "..." if len(message) > 150 else message
            
            self.verbose_manager.log_thinking(
                message=thinking_message,
                agent_name=agent_name
            )
            
            logger.debug(f"💭 {agent_name}: {thinking_message}")
            
        except Exception as e:
            logger.error(f"Erro no callback on_agent_thinking: {e}")
    
    def on_agent_action(self, agent, action: str, **kwargs):
        """Callback quando agente executa uma ação"""
        try:
            agent_name = self._extract_agent_name(agent)
            
            self.verbose_manager.log_action(
                action=action,
                agent_name=agent_name
            )
            
            logger.debug(f"⚡ {agent_name}: {action}")
            
        except Exception as e:
            logger.error(f"Erro no callback on_agent_action: {e}")
    
    # =========================================================================
    # CALLBACKS DE TOOLS
    # =========================================================================
    
    def on_tool_start(self, tool_name: str, tool_input: Dict, agent=None, **kwargs):
        """Callback quando uma tool inicia"""
        try:
            agent_name = self._extract_agent_name(agent) if agent else "Unknown"
            
            # Resumir input da tool
            input_summary = self._summarize_tool_input(tool_input)
            
            self.verbose_manager.log_step(
                f"🛠️ Executando tool '{tool_name}' - {input_summary}",
                "tool_start"
            )
            
            logger.debug(f"🛠️ Tool iniciada: {tool_name} por {agent_name}")
            
        except Exception as e:
            logger.error(f"Erro no callback on_tool_start: {e}")
    
    def on_tool_finish(self, tool_name: str, tool_output: Any, agent=None, **kwargs):
        """Callback quando uma tool termina"""
        try:
            agent_name = self._extract_agent_name(agent) if agent else "Unknown"
            
            # Resumir output da tool
            output_summary = self._summarize_tool_output(tool_output)
            
            self.verbose_manager.log_tool_usage(
                tool_name=tool_name,
                agent_name=agent_name,
                result_summary=output_summary
            )
            
            logger.debug(f"🎯 Tool finalizada: {tool_name} - {output_summary}")
            
        except Exception as e:
            logger.error(f"Erro no callback on_tool_finish: {e}")
    
    def on_tool_error(self, tool_name: str, error: Exception, agent=None, **kwargs):
        """Callback quando uma tool gera erro"""
        try:
            agent_name = self._extract_agent_name(agent) if agent else "Unknown"
            
            self.verbose_manager.log_error(
                error=f"Tool '{tool_name}': {str(error)}",
                agent_name=agent_name
            )
            
            logger.error(f"❌ Erro na tool {tool_name}: {error}")
            
        except Exception as e:
            logger.error(f"Erro no callback on_tool_error: {e}")
    
    # =========================================================================
    # CALLBACKS DE ERRO
    # =========================================================================
    
    def on_agent_error(self, agent, error: Exception, **kwargs):
        """Callback quando agente gera erro"""
        try:
            agent_name = self._extract_agent_name(agent)
            
            self.verbose_manager.log_error(
                error=str(error),
                agent_name=agent_name
            )
            
            logger.error(f"❌ Erro no agente {agent_name}: {error}")
            
        except Exception as e:
            logger.error(f"Erro no callback on_agent_error: {e}")
    
    def on_task_error(self, task, agent, error: Exception, **kwargs):
        """Callback quando task gera erro"""
        try:
            task_name = self._extract_task_name(task)
            agent_name = self._extract_agent_name(agent)
            
            self.verbose_manager.log_error(
                error=f"Task '{task_name}': {str(error)}",
                agent_name=agent_name
            )
            
            logger.error(f"❌ Erro na task {task_name}: {error}")
            
        except Exception as e:
            logger.error(f"Erro no callback on_task_error: {e}")
    
    # =========================================================================
    # MÉTODOS AUXILIARES
    # =========================================================================
    
    def _extract_agent_name(self, agent) -> str:
        """Extrai nome do agente de forma segura"""
        if not agent:
            return "Unknown Agent"
        
        # Tentar diferentes atributos
        for attr in ['role', 'name', 'agent_name', '__class__.__name__']:
            try:
                if hasattr(agent, attr):
                    value = getattr(agent, attr)
                    if value and isinstance(value, str):
                        return value
            except:
                continue
        
        return f"Agent_{id(agent)}"
    
    def _extract_agent_role(self, agent) -> str:
        """Extrai role do agente"""
        try:
            return getattr(agent, 'role', 'Unknown Role')
        except:
            return 'Unknown Role'
    
    def _extract_task_name(self, task) -> str:
        """Extrai nome da task de forma segura"""
        if not task:
            return "Unknown Task"
        
        # Tentar diferentes atributos
        for attr in ['description', 'name', 'task_name']:
            try:
                if hasattr(task, attr):
                    value = getattr(task, attr)
                    if value and isinstance(value, str):
                        # Limitar tamanho
                        return value[:50] + "..." if len(value) > 50 else value
            except:
                continue
        
        return f"Task_{id(task)}"
    
    def _extract_task_description(self, task) -> Optional[str]:
        """Extrai descrição da task"""
        try:
            return getattr(task, 'description', None)
        except:
            return None
    
    def _summarize_output(self, output) -> str:
        """Resume output de forma segura"""
        if not output:
            return "Sem output"
        
        try:
            output_str = str(output)
            if len(output_str) > 100:
                return output_str[:100] + "..."
            return output_str
        except:
            return "Output não serializável"
    
    def _summarize_tool_input(self, tool_input: Dict) -> str:
        """Resume input da tool"""
        try:
            if not tool_input:
                return "sem parâmetros"
            
            # Contar parâmetros
            param_count = len(tool_input)
            
            # Mostrar principais keys
            main_keys = list(tool_input.keys())[:3]
            keys_summary = ", ".join(main_keys)
            
            if param_count > 3:
                keys_summary += f" (+{param_count - 3} mais)"
            
            return f"{param_count} parâmetros ({keys_summary})"
            
        except:
            return "parâmetros complexos"
    
    def _summarize_tool_output(self, tool_output) -> str:
        """Resume output da tool"""
        try:
            if tool_output is None:
                return "sem retorno"
            
            output_str = str(tool_output)
            
            # Se for SVG, mencionar
            if "svg" in output_str.lower() and "<svg" in output_str:
                return f"SVG gerado ({len(output_str)} caracteres)"
            
            # Se for JSON, mencionar
            if output_str.strip().startswith('{') or output_str.strip().startswith('['):
                return f"JSON gerado ({len(output_str)} caracteres)"
            
            # Resumo genérico
            if len(output_str) > 100:
                return f"Dados gerados ({len(output_str)} caracteres)"
            
            return output_str[:100]
            
        except:
            return "output gerado"


# =========================================================================
# CALLBACK HANDLER PARA CREWAI FRAMEWORK
# =========================================================================

class CrewAICallbackManager:
    """
    Manager que registra callbacks no CrewAI Framework
    
    Usado para conectar o VerboseCallbackHandler aos eventos do CrewAI
    """
    
    def __init__(self, verbose_manager):
        self.callback_handler = VerboseCallbackHandler(verbose_manager)
        self.registered_callbacks = []
    
    def register_callbacks(self, crew_framework):
        """
        Registra callbacks no crew framework do CrewAI
        
        NOTA: Dependendo da versão do CrewAI, os métodos de callback podem variar.
        Este é um template que deve ser adaptado à versão específica.
        """
        try:
            # Tentar registrar callbacks se o CrewAI suportar
            if hasattr(crew_framework, 'add_callback'):
                crew_framework.add_callback('agent_start', self.callback_handler.on_agent_start)
                crew_framework.add_callback('agent_finish', self.callback_handler.on_agent_finish)
                crew_framework.add_callback('task_start', self.callback_handler.on_task_start)
                crew_framework.add_callback('task_finish', self.callback_handler.on_task_finish)
                
                logger.info("✅ Callbacks registrados no CrewAI Framework")
                return True
                
            else:
                logger.warning("⚠️ CrewAI Framework não suporta callbacks diretos")
                return False
                
        except Exception as e:
            logger.error(f"❌ Erro ao registrar callbacks: {e}")
            return False
    
    def manual_log_events(self, event_type: str, **kwargs):
        """
        Método para log manual de eventos quando callbacks automáticos não funcionam
        """
        try:
            if event_type == 'agent_start':
                self.callback_handler.on_agent_start(**kwargs)
            elif event_type == 'agent_finish':
                self.callback_handler.on_agent_finish(**kwargs)
            elif event_type == 'task_start':
                self.callback_handler.on_task_start(**kwargs)
            elif event_type == 'task_finish':
                self.callback_handler.on_task_finish(**kwargs)
            elif event_type == 'tool_start':
                self.callback_handler.on_tool_start(**kwargs)
            elif event_type == 'tool_finish':
                self.callback_handler.on_tool_finish(**kwargs)
            elif event_type == 'error':
                self.callback_handler.on_agent_error(**kwargs)
                
        except Exception as e:
            logger.error(f"Erro no log manual de evento {event_type}: {e}")