"""
Utilitários para views e templates
"""
import logging
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

logger = logging.getLogger(__name__)

def paginar_lista(queryset, request, itens_por_pagina=10):
    """
    Função utilitária para paginação de querysets
    
    Args:
        queryset: QuerySet a ser paginado
        request: Objeto request do Django
        itens_por_pagina: Número de itens por página (padrão: 10)
    
    Returns:
        Objeto Page contendo os itens da página atual
    """
    paginator = Paginator(queryset, itens_por_pagina)
    page = request.GET.get('page', 1)
    
    try:
        items = paginator.page(page)
    except PageNotAnInteger:
        # Se page não for um inteiro, retornar a primeira página
        items = paginator.page(1)
    except EmptyPage:
        # Se page estiver fora do intervalo, retornar a última página
        items = paginator.page(paginator.num_pages)
    
    return items

class PaginacaoMixin:
    """
    Mixin para adicionar funcionalidade de paginação a class-based views
    """
    itens_por_pagina = 10
    
    def paginar_queryset(self, queryset):
        """
        Pagina o queryset fornecido
        
        Args:
            queryset: QuerySet a ser paginado
            
        Returns:
            Objeto Page contendo os itens da página atual
        """
        return paginar_lista(queryset, self.request, self.itens_por_pagina)