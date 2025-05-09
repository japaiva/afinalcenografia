# projetos/templatetags/briefing_filters.py
from django import template
import os

register = template.Library()

@register.filter
def is_image(file_path):
    """Verifica se um arquivo é uma imagem com base na extensão"""
    if not file_path:
        return False
    
    # Obter a extensão do arquivo
    _, ext = os.path.splitext(file_path)
    if not ext:
        return False
    
    # Remover o ponto da extensão e converter para minúsculas
    ext = ext[1:].lower()
    
    # Lista de extensões de imagem comuns
    image_extensions = ['jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp', 'svg']
    
    return ext in image_extensions

@register.filter
def finditem(iterable, value):
    """
    Verifica se um item com determinado tipo existe na coleção
    """
    if not iterable:
        return False
    
    for item in iterable:
        if hasattr(item, 'tipo') and item.tipo == value:
            return True
    return False