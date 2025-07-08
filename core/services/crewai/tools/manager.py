# core/services/crewai/tools/manager.py - CORRIGIDO PARA LANGCHAIN

from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

def create_tools_from_config(tools_config: dict, verbose_manager=None) -> List:
    """
    Cria tools baseado na configuração com verbose integrado
    
    Args:
        tools_config: Configuração das tools do banco de dados
        verbose_manager: Manager de verbose para logs em tempo real
        
    Returns:
        Lista de tools LangChain prontas para uso
    """
    tools_instances = []
    
    if not tools_config:
        logger.warning("⚠️ Nenhuma configuração de tools fornecida")
        return tools_instances
    
    tools_names = tools_config.get('tools', [])
    
    if not tools_names:
        logger.warning("⚠️ Lista de tools vazia na configuração")
        return tools_instances
    
    logger.info(f"🛠️ Criando {len(tools_names)} tools: {tools_names}")
    
    for tool_name in tools_names:
        try:
            # Log do verbose
            if verbose_manager:
                verbose_manager.log_step(f"🔧 Criando tool '{tool_name}'", "tool")
            
            # Configurações específicas da tool
            tool_specific_config = tools_config.get(tool_name, {})
            
            # Injetar verbose manager
            if verbose_manager:
                tool_specific_config['verbose_manager'] = verbose_manager
            
            # Criar instância da tool
            tool_instance = _create_tool_instance(tool_name, **tool_specific_config)
            
            if tool_instance:
                tools_instances.append(tool_instance)
                logger.info(f"✅ Tool '{tool_name}' criada com sucesso")
                
                if verbose_manager:
                    verbose_manager.log_step(f"✅ Tool '{tool_name}' ativa", "tool")
            else:
                logger.error(f"❌ Falha ao criar tool '{tool_name}'")
                
                if verbose_manager:
                    verbose_manager.log_error(f"Tool '{tool_name}' falhou ao ser criada")
                    
        except Exception as e:
            logger.error(f"❌ Erro ao criar tool '{tool_name}': {str(e)}")
            
            if verbose_manager:
                verbose_manager.log_error(f"Erro na tool '{tool_name}': {str(e)}")
    
    logger.info(f"🎯 Total de tools criadas: {len(tools_instances)}")
    return tools_instances

def _create_tool_instance(tool_name: str, **kwargs):
    """
    Cria instância específica de uma tool
    
    Args:
        tool_name: Nome da tool a ser criada
        **kwargs: Argumentos de configuração
        
    Returns:
        Instância da tool ou None se falhar
    """
    try:
        if tool_name == 'svg_generator':
            return _create_svg_generator_tool(**kwargs)
        elif tool_name == 'file_processor':
            return _create_file_processor_tool(**kwargs)
        elif tool_name == 'data_analyzer':
            return _create_data_analyzer_tool(**kwargs)
        else:
            logger.warning(f"⚠️ Tool '{tool_name}' não reconhecida")
            return None
            
    except Exception as e:
        logger.error(f"❌ Erro ao instanciar tool '{tool_name}': {str(e)}")
        return None

def _create_svg_generator_tool(**kwargs):
    """Cria instância da SVGGeneratorTool"""
    try:
        from .svg_generator import SVGGeneratorTool
        
        # Extrair verbose manager se fornecido
        verbose_manager = kwargs.pop('verbose_manager', None)
        
        # Criar instância
        tool = SVGGeneratorTool(verbose_manager=verbose_manager, **kwargs)
        
        logger.info("✅ SVGGeneratorTool criada")
        return tool
        
    except ImportError as e:
        logger.error(f"❌ Erro ao importar SVGGeneratorTool: {e}")
        return None
    except Exception as e:
        logger.error(f"❌ Erro ao criar SVGGeneratorTool: {e}")
        return None

def _create_file_processor_tool(**kwargs):
    """Cria instância da FileProcessorTool (placeholder)"""
    logger.warning("⚠️ FileProcessorTool ainda não implementada")
    return None

def _create_data_analyzer_tool(**kwargs):
    """Cria instância da DataAnalyzerTool (placeholder)"""
    logger.warning("⚠️ DataAnalyzerTool ainda não implementada")
    return None

# Função de utilitário para listar tools disponíveis
def get_available_tools() -> Dict[str, Dict[str, Any]]:
    """
    Retorna dicionário com todas as tools disponíveis e suas descrições
    
    Returns:
        Dict com informações das tools disponíveis
    """
    return {
        'svg_generator': {
            'name': 'SVGGeneratorTool',
            'description': 'Gera arquivos SVG de plantas baixas baseado em dados estruturados',
            'status': 'available',
            'input_schema': {
                'dados': 'Dict - Dados estruturados do briefing',
                'tipo': 'str - Tipo de SVG (planta_baixa, diagrama, etc)',
                'config': 'Dict - Configurações opcionais'
            },
            'output': 'str - Código SVG completo'
        },
        'file_processor': {
            'name': 'FileProcessorTool',
            'description': 'Processa e manipula arquivos (em desenvolvimento)',
            'status': 'planned',
            'input_schema': {},
            'output': 'str'
        },
        'data_analyzer': {
            'name': 'DataAnalyzerTool', 
            'description': 'Analisa e processa dados estruturados (em desenvolvimento)',
            'status': 'planned',
            'input_schema': {},
            'output': 'str'
        }
    }

def validate_tool_config(tools_config: Dict) -> Dict[str, Any]:
    """
    Valida configuração de tools
    
    Args:
        tools_config: Configuração a ser validada
        
    Returns:
        Dict com resultado da validação
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
        
        available_tools = get_available_tools()
        
        for tool_name in tools_names:
            if tool_name in available_tools:
                if available_tools[tool_name]['status'] == 'available':
                    validation_result['tools_found'].append(tool_name)
                else:
                    validation_result['warnings'].append(f"Tool '{tool_name}' está em desenvolvimento")
            else:
                validation_result['tools_missing'].append(tool_name)
                validation_result['warnings'].append(f"Tool '{tool_name}' não reconhecida")
        
        if validation_result['tools_missing']:
            validation_result['valid'] = False
            validation_result['errors'].append(f"Tools não encontradas: {validation_result['tools_missing']}")
        
    except Exception as e:
        validation_result['valid'] = False
        validation_result['errors'].append(f"Erro na validação: {str(e)}")
    
    return validation_result