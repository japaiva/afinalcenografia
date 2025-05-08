"""
Utilitários para views e templates
"""
import logging
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django import forms
from datetime import datetime

logger = logging.getLogger(__name__)

# Adicione a nova classe aqui
class CustomDateInput(forms.DateInput):
    input_type = 'date'
    
    def format_value(self, value):
        # Se o valor for None, retornar vazio
        if value is None:
            return ''
        # Se já for uma string, verificar se está no formato correto
        if isinstance(value, str):
            try:
                # Tentar converter para datetime e depois para o formato esperado
                parsed = datetime.strptime(value, '%Y-%m-%d')
                return parsed.strftime('%Y-%m-%d')
            except ValueError:
                # Se não for possível converter, retornar o valor como está
                return value
        # Se for um objeto date/datetime, converter para string no formato correto
        return value.strftime('%Y-%m-%d')

# Classe base para formulários com campos de data
class DateAwareModelForm(forms.ModelForm):
    """
    Um ModelForm que trata automaticamente campos de data para garantir
    que eles sejam formatados corretamente para widgets HTML5.
    """
    def __init__(self, *args, **kwargs):
        super(DateAwareModelForm, self).__init__(*args, **kwargs)
        
        # Para cada campo que é DateField, use o CustomDateInput como widget
        for field_name, field in self.fields.items():
            if isinstance(field, forms.DateField) and not isinstance(field.widget, CustomDateInput):
                self.fields[field_name].widget = CustomDateInput(
                    attrs=getattr(field.widget, 'attrs', {'class': 'form-control'})
                )

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
    