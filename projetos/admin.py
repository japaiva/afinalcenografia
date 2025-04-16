from django.contrib import admin
from projetos.models.briefing import (
    Briefing, BriefingConversation, BriefingArquivoReferencia, BriefingValidacao
)

class BriefingConversationInline(admin.TabularInline):
    model = BriefingConversation
    extra = 0
    readonly_fields = ['timestamp']
    fields = ['origem', 'mensagem', 'etapa', 'timestamp']

class BriefingValidacaoInline(admin.TabularInline):
    model = BriefingValidacao
    extra = 0
    fields = ['secao', 'status', 'mensagem']

class BriefingArquivoReferenciaInline(admin.TabularInline):
    model = BriefingArquivoReferencia
    extra = 0
    fields = ['nome', 'tipo', 'arquivo', 'uploaded_at']
    readonly_fields = ['uploaded_at']

@admin.register(Briefing)
class BriefingAdmin(admin.ModelAdmin):
    list_display = ['projeto', 'status', 'etapa_atual', 'progresso', 'validado_por_ia', 'updated_at']
    list_filter = ['status', 'validado_por_ia']
    search_fields = ['projeto__nome']
    readonly_fields = ['created_at', 'updated_at', 'progresso']
    fieldsets = [
        ('Informações Gerais', {
            'fields': ['projeto', 'status', 'etapa_atual', 'progresso', 'validado_por_ia', 'created_at', 'updated_at']
        }),
        ('Informações Básicas', {
            'fields': ['categoria', 'descricao_detalhada', 'objetivos']
        }),
        ('Detalhes Técnicos', {
            'fields': ['dimensoes', 'altura', 'paleta_cores']
        }),
        ('Materiais e Acabamentos', {
            'fields': ['materiais_preferidos', 'acabamentos']
        }),
        ('Requisitos Técnicos', {
            'fields': ['iluminacao', 'eletrica', 'mobiliario']
        }),
    ]
    inlines = [BriefingValidacaoInline, BriefingArquivoReferenciaInline, BriefingConversationInline]

    # projetos/admin.py

from django.contrib import admin
from projetos.models.briefing import (
    Briefing, BriefingConversation, BriefingArquivoReferencia, BriefingValidacao
)
from projetos.models.projeto import Projeto, ProjetoPlanta, ProjetoReferencia

class ProjetoPlantaInline(admin.TabularInline):
    model = ProjetoPlanta
    extra = 0
    
class ProjetoReferenciaInline(admin.TabularInline):
    model = ProjetoReferencia
    extra = 0

@admin.register(Projeto)
class ProjetoAdmin(admin.ModelAdmin):
    list_display = ['nome', 'empresa', 'cliente', 'feira', 'status', 'briefing_status', 'created_at']
    list_filter = ['status', 'briefing_status', 'empresa', 'feira']
    search_fields = ['nome', 'cliente__username', 'empresa__nome', 'feira__nome']
    inlines = [ProjetoPlantaInline, ProjetoReferenciaInline]
    fieldsets = [
        ('Informações Básicas', {
            'fields': ['nome', 'descricao', 'empresa', 'cliente', 'status', 'orcamento', 'progresso']
        }),
        ('Feira', {
            'fields': ['feira', 'local_evento', 'cidade_evento', 'estado_evento']
        }),
        ('Briefing', {
            'fields': ['tem_briefing', 'briefing_status']
        }),
    ]
    readonly_fields = ['created_at', 'updated_at']