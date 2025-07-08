# =============================================================================
# 2. core/services/crewai/tools/manager.py - SIMPLIFICADO
# =============================================================================

from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

def create_tools_from_config(tools_config: dict, verbose_manager=None) -> List:
    """
    Cria lista de tools baseada na configuração do banco
    
    Args:
        tools_config: Configuração vinda do banco {"tools": ["svg_generator"]}
        verbose_manager: Sistema de logs verbose (opcional)
        
    Returns:
        Lista de instâncias de tools prontas para usar
    """
    if not tools_config:
        logger.debug("Nenhuma configuração de tools fornecida")
        return []
    
    from .tools_map import get_tool
    
    tools_instances = []
    tools_names = tools_config.get('tools', [])
    
    if not tools_names:
        logger.debug("Lista de tools vazia na configuração")
        return []
    
    logger.info(f"🛠️ Carregando {len(tools_names)} tools: {tools_names}")
    
    for tool_name in tools_names:
        try:
            if verbose_manager:
                verbose_manager.log_step(f"🔧 Carregando tool '{tool_name}'", "tool")
            
            tool_instance = get_tool(tool_name)
            
            if tool_instance:
                tools_instances.append(tool_instance)
                logger.info(f"✅ Tool '{tool_name}' carregada com sucesso")
                
                if verbose_manager:
                    verbose_manager.log_step(f"✅ Tool '{tool_name}' ativa", "tool")
            else:
                logger.warning(f"❌ Tool '{tool_name}' não encontrada")
                
                if verbose_manager:
                    verbose_manager.log_step(f"❌ Tool '{tool_name}' não encontrada", "tool")
                
        except Exception as e:
            logger.error(f"❌ Erro ao carregar tool '{tool_name}': {str(e)}")
            
            if verbose_manager:
                verbose_manager.log_step(f"❌ Erro na tool '{tool_name}': {str(e)}", "tool")
    
    logger.info(f"🎯 Total de tools carregadas: {len(tools_instances)}")
    return tools_instances


def get_available_tools() -> Dict[str, Any]:
    """
    Lista tools disponíveis com informações detalhadas
    
    Returns:
        Dict com informações das tools
    """
    from .tools_map import list_available_tools, get_tool_info
    
    available_tools = {}
    
    for tool_name in list_available_tools():
        tool_info = get_tool_info(tool_name)
        if tool_info:
            available_tools[tool_name] = tool_info
        else:
            available_tools[tool_name] = {
                'name': tool_name,
                'description': 'Tool não implementada',
                'available': False
            }
    
    return available_tools


def validate_tools_config(tools_config: Dict) -> Dict[str, Any]:
    """
    Valida configuração de tools
    
    Args:
        tools_config: Configuração para validar
        
    Returns:
        Resultado da validação
    """
    validation_result = {
        'valid': True,
        'errors': [],
        'warnings': [],
        'tools_found': [],
        'tools_missing': []
    }
    
    try:
        if not isinstance(tools_config, dict):
            validation_result['valid'] = False
            validation_result['errors'].append("tools_config deve ser um dicionário")
            return validation_result
        
        tools_names = tools_config.get('tools', [])
        
        if not isinstance(tools_names, list):
            validation_result['valid'] = False
            validation_result['errors'].append("'tools' deve ser uma lista")
            return validation_result
        
        from .tools_map import get_tool
        
        for tool_name in tools_names:
            tool = get_tool(tool_name)
            if tool:
                validation_result['tools_found'].append(tool_name)
            else:
                validation_result['tools_missing'].append(tool_name)
                validation_result['warnings'].append(f"Tool '{tool_name}' não encontrada")
        
    except Exception as e:
        validation_result['valid'] = False
        validation_result['errors'].append(f"Erro na validação: {str(e)}")
    
    return validation_result
