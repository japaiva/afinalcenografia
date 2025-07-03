# core/services/crewai/tools/manager.py
from typing import List
from .registry import tools_registry

def create_tools_from_config(tools_config: dict, verbose_manager=None) -> List:
    """Cria tools baseado na configuração com verbose integrado"""
    tools_instances = []
    
    if not tools_config:
        return tools_instances
    
    tools_names = tools_config.get('tools', [])
    
    for tool_name in tools_names:
        # Configurações específicas da tool
        tool_specific_config = tools_config.get(tool_name, {})
        
        # Injetar verbose manager
        if verbose_manager:
            tool_specific_config['verbose_manager'] = verbose_manager
        
        # Criar instância
        tool_instance = tools_registry.create_instance(tool_name, **tool_specific_config)
        
        if tool_instance:
            tools_instances.append(tool_instance)
            print(f"✅ Tool '{tool_name}' criada")
        else:
            print(f"❌ Tool '{tool_name}' não encontrada")
    
    return tools_instances