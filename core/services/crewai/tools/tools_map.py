# =============================================================================
# 1. core/services/crewai/tools/tools_map.py - ARQUIVO NOVO
# =============================================================================

import logging

logger = logging.getLogger(__name__)

def get_tool(tool_name):
    
    try:
        if tool_name == 'svg_generator':
            from .svg_function import svg_generator_tool
            logger.debug(f"✅ Tool SVG Generator carregada")
            return svg_generator_tool
        
        elif tool_name == 'pdf_processor':
            # TODO: Implementar quando necessário
            # from .pdf_processor import pdf_processor_tool
            # return pdf_processor_tool
            logger.warning(f"⚠️ Tool 'pdf_processor' ainda não implementada")
            return None
        
        elif tool_name == 'cost_calculator':
            # TODO: Implementar quando necessário
            # from .cost_calculator import cost_calculator_tool
            # return cost_calculator_tool
            logger.warning(f"⚠️ Tool 'cost_calculator' ainda não implementada")
            return None
        
        elif tool_name == 'file_reader':
            # TODO: Implementar quando necessário
            # from .file_reader import file_reader_tool
            # return file_reader_tool
            logger.warning(f"⚠️ Tool 'file_reader' ainda não implementada")
            return None
        
        else:
            logger.warning(f"❌ Tool '{tool_name}' não reconhecida")
            return None
            
    except ImportError as e:
        logger.error(f"❌ Erro ao importar tool '{tool_name}': {e}")
        return None
    except Exception as e:
        logger.error(f"❌ Erro inesperado ao carregar tool '{tool_name}': {e}")
        return None


def list_available_tools():
    """
    Lista todas as tools disponíveis no sistema
    
    Returns:
        Lista de nomes das tools disponíveis
    """
    return [
        'svg_generator',     # ✅ Implementada e funcionando
        'pdf_processor',     # 🚧 Planejada para futuro
        'cost_calculator',   # 🚧 Planejada para futuro  
        'file_reader',       # 🚧 Planejada para futuro
    ]


def get_tool_info(tool_name):
    """
    Retorna informações sobre uma tool específica
    
    Args:
        tool_name: Nome da tool
        
    Returns:
        Dict com informações da tool ou None
    """
    tool = get_tool(tool_name)
    if not tool:
        return None
    
    return {
        'name': getattr(tool, 'name', tool_name),
        'description': getattr(tool, 'description', 'Sem descrição'),
        'type': type(tool).__name__,
        'available': True
    }
