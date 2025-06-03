# projetista/templatetags/projetista_filters.py

from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Obtém item do dicionário pela chave"""
    return dictionary.get(key, [])

@register.filter
def multiply(value, arg):
    """Multiplica dois valores"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def categoria_icon(categoria):
    """Retorna ícone para categoria"""
    icons = {
        'cliente': '👥',
        'tecnica_externa': '🏗️',
        'tecnica_interna': '🏠',
        'planta_elevacao': '📐',
        'detalhes': '🔍'
    }
    return icons.get(categoria, '📷')

@register.filter
def angulo_icon(angulo):
    """Retorna ícone para ângulo de vista"""
    icons = {
        'perspectiva_externa': '🏢',
        'entrada_recepcao': '🚪',
        'interior_principal': '🏠',
        'area_produtos': '📦',
        'elevacao_frontal': '📐',
        'elevacao_lateral_esquerda': '📐',
        'elevacao_lateral_direita': '📐',
        'elevacao_fundos': '📐',
        'planta_baixa': '🗺️',
        'vista_superior': '🔼',
        'interior_parede_norte': '🧱',
        'interior_parede_sul': '🧱',
        'interior_parede_leste': '🧱',
        'interior_parede_oeste': '🧱',
        'interior_perspectiva_1': '👁️',
        'interior_perspectiva_2': '👁️',
        'interior_perspectiva_3': '👁️',
        'quina_frontal_esquerda': '📐',
        'quina_frontal_direita': '📐',
        'detalhe_balcao': '🔍',
        'detalhe_display': '🔍',
        'detalhe_iluminacao': '💡',
        'detalhe_entrada': '🔍',
    }
    return icons.get(angulo, '📷')

@register.filter
def vista_priority(angulo):
    """Retorna prioridade da vista (1=alta, 3=baixa)"""
    priorities = {
        # Cliente (alta prioridade)
        'perspectiva_externa': 1,
        'entrada_recepcao': 1,
        'interior_principal': 1,
        'area_produtos': 1,
        
        # Técnicas importantes (média prioridade)
        'planta_baixa': 2,
        'elevacao_frontal': 2,
        'elevacao_lateral_esquerda': 2,
        'elevacao_lateral_direita': 2,
        'elevacao_fundos': 2,
        'vista_superior': 2,
    }
    return priorities.get(angulo, 3)

@register.filter
def vista_category_color(categoria):
    """Retorna cor CSS para categoria"""
    colors = {
        'cliente': 'info',
        'tecnica_externa': 'warning',
        'tecnica_interna': 'success',
        'planta_elevacao': 'secondary',
        'detalhes': 'dark'
    }
    return colors.get(categoria, 'light')

@register.simple_tag
def vista_progress_bar(categoria_count, categoria):
    """Calcula progresso para categoria específica"""
    # Definir metas por categoria
    metas = {
        'cliente': 4,
        'tecnica_externa': 6,
        'tecnica_interna': 7,
        'planta_elevacao': 2,
        'detalhes': 4
    }
    
    meta = metas.get(categoria, 5)
    if categoria_count == 0:
        return 0
    
    progresso = min(100, (categoria_count / meta) * 100)
    return round(progresso)

@register.filter
def fotogrametria_essencial(angulo):
    """Verifica se a vista é essencial para fotogrametria"""
    essenciais = [
        'perspectiva_externa', 'planta_baixa',
        'elevacao_frontal', 'elevacao_lateral_esquerda', 
        'elevacao_lateral_direita', 'elevacao_fundos',
        'interior_parede_norte', 'interior_parede_sul',
        'interior_parede_leste', 'interior_parede_oeste'
    ]
    return angulo in essenciais

@register.filter
def get_missing_essentials(imagens_existentes):
    """Retorna lista de vistas essenciais que estão faltando"""
    essenciais = [
        'perspectiva_externa', 'planta_baixa',
        'elevacao_frontal', 'elevacao_lateral_esquerda', 
        'elevacao_lateral_direita', 'elevacao_fundos',
        'interior_parede_norte', 'interior_parede_sul',
        'interior_parede_leste', 'interior_parede_oeste'
    ]
    
    existentes = [img.angulo_vista for img in imagens_existentes]
    faltando = [vista for vista in essenciais if vista not in existentes]
    return faltando