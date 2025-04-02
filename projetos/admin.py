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