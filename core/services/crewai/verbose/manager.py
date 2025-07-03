# core/services/crewai_verbose/verbose_manager.py

import logging
import time
import threading
import queue
from typing import Dict, Any, Callable, Optional
from django.core.cache import cache
from django.utils import timezone
import json

logger = logging.getLogger(__name__)

class VerboseManager:
    """
    Sistema de verbose melhorado para CrewAI com callbacks em tempo real
    """
    
    def __init__(self, execucao_id: str, crew_nome: str = "CrewAI"):
        self.execucao_id = execucao_id
        self.crew_nome = crew_nome
        self.cache_key = f"crewai_logs_{execucao_id}"
        self.is_active = False
        self.start_time = None
        self.callbacks = []
        self._logs_buffer = []
        self._lock = threading.Lock()
        
    def add_callback(self, callback: Callable):
        """Adiciona callback para logs em tempo real"""
        self.callbacks.append(callback)
        
    def start(self):
        """Inicia captura de logs"""
        with self._lock:
            self.is_active = True
            self.start_time = time.time()
            
            # Limpar cache anterior
            cache.set(self.cache_key, [], timeout=7200)
            
            # Log inicial
            self._add_log("🚀 Iniciando execução", "inicio")
            
    def stop(self):
        """Para captura de logs"""
        with self._lock:
            if self.is_active:
                tempo_total = time.time() - self.start_time if self.start_time else 0
                self._add_log(f"✅ Execução concluída em {tempo_total:.1f}s", "fim")
                self.is_active = False
                
                # Flush final dos logs
                self._flush_logs()
                
    def log_step(self, message: str, step_type: str = "info", agent_name: str = None):
        """Log de etapa específica"""
        if agent_name:
            message = f"[{agent_name}] {message}"
        self._add_log(message, step_type)
        
    def log_agent_start(self, agent_name: str, role: str):
        """Log início de agente"""
        self._add_log(f"🤖 Agente '{agent_name}' iniciado", "agente", {
            'agent_name': agent_name,
            'role': role
        })
        
    def log_task_start(self, task_name: str, agent_name: str):
        """Log início de task"""
        self._add_log(f"📋 Task '{task_name}' iniciada", "task", {
            'task_name': task_name,
            'agent_name': agent_name
        })
        
    def log_thinking(self, message: str, agent_name: str):
        """Log de pensamento do agente"""
        self._add_log(f"💭 {message}", "pensamento", {
            'agent_name': agent_name
        })
        
    def log_action(self, action: str, agent_name: str):
        """Log de ação do agente"""
        self._add_log(f"⚡ {action}", "acao", {
            'agent_name': agent_name,
            'action': action
        })
        
    def log_tool_usage(self, tool_name: str, agent_name: str, result_summary: str = None):
        """Log uso de tool"""
        message = f"🛠️ Tool '{tool_name}' executada"
        if result_summary:
            message += f" - {result_summary}"
        self._add_log(message, "tool", {
            'tool_name': tool_name,
            'agent_name': agent_name
        })
        
    def log_response(self, response_summary: str, agent_name: str):
        """Log resposta do agente"""
        self._add_log(f"📊 {response_summary}", "resposta", {
            'agent_name': agent_name
        })
        
    def log_error(self, error: str, agent_name: str = None):
        """Log de erro"""
        message = f"❌ Erro: {error}"
        if agent_name:
            message = f"[{agent_name}] {message}"
        self._add_log(message, "erro")
        
    def _add_log(self, message: str, tipo: str = "info", metadata: Dict = None):
        """Adiciona log interno"""
        if not self.is_active:
            return
            
        log_entry = {
            'timestamp': time.strftime("%H:%M:%S"),
            'message': message.strip(),
            'tipo': tipo,
            'execucao_id': self.execucao_id,
            'crew_nome': self.crew_nome,
            'tempo_relativo': time.time() - self.start_time if self.start_time else 0,
            'metadata': metadata or {}
        }
        
        # Adicionar ao buffer
        self._logs_buffer.append(log_entry)
        
        # Chamar callbacks
        for callback in self.callbacks:
            try:
                callback(log_entry)
            except Exception as e:
                logger.error(f"Erro no callback de log: {e}")
        
        # Flush periódico
        if len(self._logs_buffer) >= 5:
            self._flush_logs()
            
    def _flush_logs(self):
        """Flush logs para cache"""
        if not self._logs_buffer:
            return
            
        try:
            # Buscar logs atuais
            logs_atuais = cache.get(self.cache_key, [])
            logs_atuais.extend(self._logs_buffer)
            
            # Manter últimos 500 logs
            if len(logs_atuais) > 500:
                logs_atuais = logs_atuais[-500:]
                
            # Salvar no cache
            cache.set(self.cache_key, logs_atuais, timeout=7200)
            
            # Limpar buffer
            self._logs_buffer.clear()
            
        except Exception as e:
            logger.error(f"Erro ao fazer flush dos logs: {e}")

    def get_logs(self, desde: int = 0):
        """Recupera logs do cache"""
        logs = cache.get(self.cache_key, [])
        if desde < len(logs):
            return logs[desde:]
        return []

# core/services/crewai_verbose/crew_callbacks.py

from crewai.agent import BaseAgent
from crewai.task import Task
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class VerboseCallbackHandler:
    """
    Handler de callbacks para interceptar eventos do CrewAI
    """
    
    def __init__(self, verbose_manager):
        self.verbose_manager = verbose_manager
        
    def on_agent_start(self, agent: BaseAgent, **kwargs):
        """Callback quando agente inicia"""
        self.verbose_manager.log_agent_start(
            agent_name=getattr(agent, 'role', 'Unknown'),
            role=getattr(agent, 'role', 'Unknown')
        )
        
    def on_task_start(self, task: Task, agent: BaseAgent, **kwargs):
        """Callback quando task inicia"""
        self.verbose_manager.log_task_start(
            task_name=getattr(task, 'description', 'Unknown Task')[:50],
            agent_name=getattr(agent, 'role', 'Unknown')
        )
        
    def on_agent_thinking(self, agent: BaseAgent, message: str, **kwargs):
        """Callback quando agente está "pensando" """
        self.verbose_manager.log_thinking(
            message=message[:100],
            agent_name=getattr(agent, 'role', 'Unknown')
        )
        
    def on_tool_use(self, agent: BaseAgent, tool_name: str, tool_input: Dict, **kwargs):
        """Callback quando tool é usada"""
        self.verbose_manager.log_tool_usage(
            tool_name=tool_name,
            agent_name=getattr(agent, 'role', 'Unknown')
        )
        
    def on_agent_response(self, agent: BaseAgent, response: str, **kwargs):
        """Callback quando agente responde"""
        response_summary = response[:100] + "..." if len(response) > 100 else response
        self.verbose_manager.log_response(
            response_summary=response_summary,
            agent_name=getattr(agent, 'role', 'Unknown')
        )
        
    def on_error(self, error: Exception, agent: BaseAgent = None, **kwargs):
        """Callback para erros"""
        agent_name = getattr(agent, 'role', 'Unknown') if agent else None
        self.verbose_manager.log_error(
            error=str(error),
            agent_name=agent_name
        )