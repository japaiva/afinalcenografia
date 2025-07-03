# core/services/crewai/tools/base_tool.py - VERSÃO GENÉRICA

import logging
import time
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from crewai_tools import BaseTool

logger = logging.getLogger(__name__)

@dataclass
class ToolResult:
    """Resultado padronizado de todas as tools"""
    success: bool
    data: Any = None
    error: str = None
    metadata: Dict[str, Any] = None
    execution_time: float = 0
    
    def to_dict(self):
        return {
            'success': self.success,
            'data': self.data,
            'error': self.error,
            'metadata': self.metadata or {},
            'execution_time': self.execution_time
        }

class AfinalBaseTool(BaseTool, ABC):
    """
    Classe base genérica para todas as tools da Afinal Cenografia
    
    Funcionalidades:
    - Logging padronizado
    - Tratamento de erros consistente
    - Validação de entrada
    - Integração com verbose manager
    - Métricas de execução
    """
    
    def __init__(self, name: str, description: str, verbose_manager=None, **kwargs):
        super().__init__(name=name, description=description)
        self.logger = logging.getLogger(f"crewai_tools.{name}")
        self.verbose_manager = verbose_manager
        self.execution_count = 0
        
        # Configurações adicionais podem ser passadas via kwargs
        for key, value in kwargs.items():
            setattr(self, key, value)
    
    def _log_execution(self, input_data: Dict[str, Any], result: ToolResult) -> None:
        """Log padronizado de execução"""
        self.execution_count += 1
        
        # Log tradicional
        self.logger.info(f"🛠️ Tool '{self.name}' executada (#{self.execution_count})")
        self.logger.debug(f"📥 Input: {str(input_data)[:200]}...")
        
        if result.success:
            self.logger.debug(f"✅ Sucesso em {result.execution_time:.2f}s")
        else:
            self.logger.error(f"❌ Erro: {result.error}")
        
        # Log para verbose manager se disponível
        if self.verbose_manager:
            status = "✅ Sucesso" if result.success else "❌ Erro"
            summary = f"{status} em {result.execution_time:.2f}s"
            
            if result.error:
                summary += f" - {result.error[:50]}"
            elif result.data and hasattr(result.data, '__len__'):
                try:
                    summary += f" - {len(result.data)} caracteres"
                except:
                    summary += " - dados gerados"
            
            self.verbose_manager.log_tool_usage(
                tool_name=self.name,
                agent_name="Tool",  # Será sobrescrito pelo agente
                result_summary=summary
            )
    
    def _validate_input(self, input_data: Dict[str, Any], required_fields: List[str]) -> Dict[str, Any]:
        """
        Valida se todos os campos obrigatórios estão presentes
        
        Args:
            input_data: Dados de entrada
            required_fields: Lista de campos obrigatórios
            
        Returns:
            input_data validado
            
        Raises:
            ValueError: Se campos obrigatórios estiverem ausentes
        """
        missing_fields = [field for field in required_fields if field not in input_data]
        
        if missing_fields:
            error_msg = f"Campos obrigatórios ausentes: {missing_fields}"
            self.logger.error(f"❌ {error_msg}")
            raise ValueError(error_msg)
        
        return input_data
    
    def _validate_types(self, input_data: Dict[str, Any], type_spec: Dict[str, type]) -> Dict[str, Any]:
        """
        Valida tipos dos campos de entrada
        
        Args:
            input_data: Dados de entrada
            type_spec: Especificação de tipos {campo: tipo}
            
        Returns:
            input_data validado
            
        Raises:
            TypeError: Se tipos estiverem incorretos
        """
        for field, expected_type in type_spec.items():
            if field in input_data:
                if not isinstance(input_data[field], expected_type):
                    error_msg = f"Campo '{field}' deve ser do tipo {expected_type.__name__}, recebido {type(input_data[field]).__name__}"
                    self.logger.error(f"❌ {error_msg}")
                    raise TypeError(error_msg)
        
        return input_data
    
    def _create_error_result(self, error: Exception, context: str = "") -> ToolResult:
        """
        Cria resultado de erro padronizado
        
        Args:
            error: Exceção ocorrida
            context: Contexto adicional do erro
            
        Returns:
            ToolResult com erro
        """
        error_msg = str(error)
        if context:
            error_msg = f"{context}: {error_msg}"
            
        self.logger.error(f"❌ Erro na tool '{self.name}': {error_msg}")
        
        return ToolResult(
            success=False,
            error=error_msg,
            metadata={
                'tool_name': self.name,
                'context': context,
                'execution_count': self.execution_count,
                'error_type': type(error).__name__
            }
        )
    
    def _create_success_result(self, data: Any, metadata: Dict[str, Any] = None) -> ToolResult:
        """
        Cria resultado de sucesso padronizado
        
        Args:
            data: Dados do resultado
            metadata: Metadados adicionais
            
        Returns:
            ToolResult com sucesso
        """
        return ToolResult(
            success=True,
            data=data,
            metadata={
                'tool_name': self.name,
                'execution_count': self.execution_count,
                **(metadata or {})
            }
        )
    
    def _run(self, **kwargs) -> str:
        """
        Wrapper principal que chama o método de execução específico
        
        Este método é chamado pelo CrewAI e:
        1. Mede tempo de execução
        2. Chama o método _execute da tool específica
        3. Faz log da execução
        4. Retorna string para o CrewAI
        """
        start_time = time.time()
        
        try:
            # Executar tool específica
            result = self._execute(**kwargs)
            
            # Garantir que o resultado seja um ToolResult
            if not isinstance(result, ToolResult):
                result = self._create_success_result(result)
            
            # Calcular tempo de execução
            result.execution_time = time.time() - start_time
            
            # Log da execução
            self._log_execution(kwargs, result)
            
            # Retornar string para o CrewAI
            if result.success:
                return str(result.data) if result.data is not None else "Operação realizada com sucesso"
            else:
                return f"Erro: {result.error}"
                
        except Exception as e:
            # Criar resultado de erro
            execution_time = time.time() - start_time
            result = self._create_error_result(e, "Execução da tool")
            result.execution_time = execution_time
            
            # Log da execução
            self._log_execution(kwargs, result)
            
            # Retornar erro para o CrewAI
            return f"Erro: {result.error}"
    
    @abstractmethod
    def _execute(self, **kwargs) -> ToolResult:
        """
        Método principal que cada tool deve implementar
        
        Args:
            **kwargs: Argumentos passados pelo agente
            
        Returns:
            ToolResult com o resultado da execução
            
        Raises:
            Qualquer exceção será capturada pelo _run()
        """
        pass
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Retorna estatísticas de uso da tool
        
        Returns:
            Dicionário com estatísticas
        """
        return {
            'tool_name': self.name,
            'execution_count': self.execution_count,
            'has_verbose': self.verbose_manager is not None,
            'description': self.description
        }