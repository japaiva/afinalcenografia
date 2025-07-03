# core/services/crewai/tools/registry.py
import importlib
from typing import Dict, Type
from .base_tool import AfinalBaseTool

class ToolsRegistry:
    def __init__(self):
        self._tools: Dict[str, Type[AfinalBaseTool]] = {}
        self._load_default_tools()
    
    def _load_default_tools(self):
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
                self.register(tool_name, tool_class)
            except Exception as e:
                print(f"⚠️ Tool '{tool_name}' não carregada: {e}")

# Instância global
tools_registry = ToolsRegistry()