# core/services/crewai/tools/registry.py - ATUALIZADO PARA LANGCHAIN

import importlib
import logging
from typing import Dict, Type, Any
from langchain.tools import BaseTool

logger = logging.getLogger(__name__)

class ToolsRegistry:
    """Registry para tools LangChain compatíveis"""
    
    def __init__(self):
        self._tools: Dict[str, Type[BaseTool]] = {}
        self._load_default_tools()
    
    def register(self, name: str, tool_class: Type[BaseTool]):
        """Registra uma tool LangChain"""
        self._tools[name] = tool_class
        logger.info(f"✅ Tool '{name}' registrada no registry")
    
    def create_instance(self, name: str, **kwargs):
        """Cria instância da tool"""
        if name not in self._tools:
            logger.error(f"❌ Tool '{name}' não encontrada no registry")
            return None
        
        try:
            tool_class = self._tools[name]
            instance = tool_class(**kwargs)
            logger.info(f"✅ Instância da tool '{name}' criada")
            return instance
        except Exception as e:
            logger.error(f"❌ Erro ao criar instância da tool '{name}': {e}")
            return None
    
    def list_tools(self) -> Dict[str, str]:
        """Lista todas as tools registradas"""
        return {name: tool_class.__name__ for name, tool_class in self._tools.items()}
    
    def _load_default_tools(self):
        """Carrega tools padrão"""
        default_tools = {
            'svg_generator': {
                'module': 'svg_generator',
                'class': 'SVGGeneratorTool'
            }
        }
        
        for tool_name, config in default_tools.items():
            try:
                module_path = f'core.services.crewai.tools.{config["module"]}'
                mod = importlib.import_module(module_path)
                tool_class = getattr(mod, config['class'])
                
                # Verificar se é compatível com LangChain
                if issubclass(tool_class, BaseTool):
                    self.register(tool_name, tool_class)
                else:
                    logger.warning(f"⚠️ Tool '{tool_name}' não é compatível com LangChain BaseTool")
                    
            except Exception as e:
                logger.warning(f"⚠️ Tool '{tool_name}' não carregada: {e}")

# Instância global
tools_registry = ToolsRegistry()
