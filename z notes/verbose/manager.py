# core/services/crewai/verbose/manager.py - CORREÇÃO DEFINITIVA TEMPO REAL

import logging
import time
import threading
from typing import Dict, Any, Callable, Optional
from django.core.cache import cache
from django.utils import timezone
import json

logger = logging.getLogger(__name__)

class VerboseManager:
    """
    Sistema de verbose CORRIGIDO para logs em TEMPO REAL
    """
    
    def __init__(self, execucao_id: str, crew_nome: str = "CrewAI"):
        self.execucao_id = execucao_id
        self.crew_nome = crew_nome
        self.cache_key = f"crewai_logs_{execucao_id}"
        self.is_active = False
        self.start_time = None
        self.callbacks = []
        self._lock = threading.Lock()
        
        # 🔥 CORREÇÃO CRÍTICA: SEM BUFFER - DIRETO PARA CACHE
        self.use_buffer = False
        
        self.logger = logging.getLogger(f"verbose_manager_{execucao_id}")
        
    def start(self):
        """Inicia captura de logs"""
        with self._lock:
            self.is_active = True
            self.start_time = time.time()
            
            # Limpar cache anterior
            cache.set(self.cache_key, [], timeout=7200)
            self.logger.info(f"✅ VerboseManager iniciado para execução {self.execucao_id}")
            
            # 🔥 CRITICAL: Log inicial IMEDIATO
            self._add_log_direct("🚀 Sistema de verbose iniciado", "inicio")
            
    def stop(self):
        """Para captura de logs"""
        with self._lock:
            if self.is_active:
                tempo_total = time.time() - self.start_time if self.start_time else 0
                self._add_log_direct(f"✅ Verbose finalizado em {tempo_total:.1f}s", "fim")
                self.is_active = False
                self.logger.info(f"✅ VerboseManager finalizado: {tempo_total:.1f}s")
                
    def log_step(self, message: str, step_type: str = "info", agent_name: str = None):
        """🔥 CORRIGIDO: Log direto sem buffer"""
        if agent_name:
            message = f"[{agent_name}] {message}"
        self._add_log_direct(message, step_type)
        
    def log_agent_start(self, agent_name: str, role: str):
        """Log início de agente"""
        self._add_log_direct(f"🤖 Agente '{agent_name}' iniciado", "agente", {
            'agent_name': agent_name,
            'role': role
        })
        
    def log_task_start(self, task_name: str, agent_name: str):
        """Log início de task"""
        self._add_log_direct(f"📋 Task '{task_name}' iniciada", "task", {
            'task_name': task_name,
            'agent_name': agent_name
        })
        
    def log_thinking(self, message: str, agent_name: str):
        """Log de pensamento do agente"""
        self._add_log_direct(f"💭 {message}", "pensamento", {
            'agent_name': agent_name
        })
        
    def log_action(self, action: str, agent_name: str):
        """Log de ação do agente"""
        self._add_log_direct(f"⚡ {action}", "acao", {
            'agent_name': agent_name,
            'action': action
        })
        
    def log_tool_usage(self, tool_name: str, agent_name: str, result_summary: str = None):
        """Log uso de tool"""
        message = f"🛠️ Tool '{tool_name}' executada"
        if result_summary:
            message += f" - {result_summary}"
        self._add_log_direct(message, "tool", {
            'tool_name': tool_name,
            'agent_name': agent_name
        })
        
    def log_response(self, response_summary: str, agent_name: str):
        """Log resposta do agente"""
        self._add_log_direct(f"📊 {response_summary}", "resposta", {
            'agent_name': agent_name
        })
        
    def log_error(self, error: str, agent_name: str = None):
        """Log de erro"""
        message = f"❌ Erro: {error}"
        if agent_name:
            message = f"[{agent_name}] {message}"
        self._add_log_direct(message, "erro")
        
    def _add_log_direct(self, message: str, tipo: str = "info", metadata: Dict = None):
        """🔥 NOVO: Adiciona log DIRETAMENTE no cache - SEM BUFFER"""
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
        
        # Log no console também
        self.logger.info(f"[{log_entry['timestamp']}] {message}")
        
        # Chamar callbacks
        for callback in self.callbacks:
            try:
                callback(log_entry)
            except Exception as e:
                logger.error(f"Erro no callback de log: {e}")
        
        # 🔥 CRITICAL: SALVAR DIRETAMENTE NO CACHE
        try:
            # Buscar logs atuais do cache
            logs_atuais = cache.get(self.cache_key, [])
            
            # Adicionar novo log
            logs_atuais.append(log_entry)
            
            # Manter últimos 200 logs para performance
            if len(logs_atuais) > 200:
                logs_atuais = logs_atuais[-200:]
                
            # 🔥 SALVAR IMEDIATAMENTE
            cache.set(self.cache_key, logs_atuais, timeout=7200)
            
            # Debug detalhado
            self.logger.debug(f"🔄 Log salvo diretamente no cache: {len(logs_atuais)} total")
            
        except Exception as e:
            self.logger.error(f"❌ ERRO CRÍTICO ao salvar log: {e}")
    
    # 🔥 MANTER MÉTODOS ANTIGOS PARA COMPATIBILIDADE
    def _add_log_immediate(self, message: str, tipo: str = "info", metadata: Dict = None):
        """Alias para _add_log_direct"""
        return self._add_log_direct(message, tipo, metadata)
    
    def _add_log(self, message: str, tipo: str = "info", metadata: Dict = None):
        """Alias para _add_log_direct"""
        return self._add_log_direct(message, tipo, metadata)
            
    def _flush_logs_immediate(self):
        """Método mantido para compatibilidade - não faz nada"""
        pass

    def _flush_logs(self):
        """Método mantido para compatibilidade - não faz nada"""
        pass

    def get_logs(self, desde: int = 0):
        """Recupera logs do cache"""
        try:
            logs = cache.get(self.cache_key, [])
            if desde < len(logs):
                return logs[desde:]
            return []
        except Exception as e:
            self.logger.error(f"❌ Erro ao recuperar logs: {e}")
            return []
    
    def get_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas do verbose manager"""
        logs = cache.get(self.cache_key, [])
        tempo_ativo = time.time() - self.start_time if self.start_time else 0
        
        return {
            'execucao_id': self.execucao_id,
            'crew_nome': self.crew_nome,
            'is_active': self.is_active,
            'total_logs': len(logs),
            'tempo_ativo': tempo_ativo,
            'cache_key': self.cache_key,
            'modo_direto': True  # Novo flag
        }
    
    def force_flush(self):
        """Não faz nada - logs já são diretos"""
        pass
    
    def clear_logs(self):
        """Limpa todos os logs"""
        cache.delete(self.cache_key)
        self.logger.info(f"🗑️ Logs limpos para execução {self.execucao_id}")

# 🔥 NOVA FUNÇÃO PARA TESTE DIRETO
def test_verbose_direct(execucao_id: str = "test_direct_123"):
    """Função para testar verbose DIRETO no cache"""
    print("🧪 Testando Verbose Manager DIRETO...")
    
    manager = VerboseManager(execucao_id, "Teste Direto")
    manager.start()
    
    # Simular logs diretos
    for i in range(5):
        manager.log_step(f"Teste direto {i+1}/5", "teste")
        
        # Verificar se logs estão no cache IMEDIATAMENTE
        logs = manager.get_logs()
        print(f"   📋 Logs no cache: {len(logs)} (deve ser {i+2})")  # +1 pelo log inicial + i+1
        
        time.sleep(0.5)  # Pequeno delay
    
    manager.stop()
    
    # Resultado final
    logs_finais = manager.get_logs()
    print(f"✅ Teste concluído: {len(logs_finais)} logs gerados")
    
    # Mostrar logs
    for log in logs_finais:
        print(f"   [{log['timestamp']}] {log['message']}")
    
    return logs_finais