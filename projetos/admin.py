# projetos/admin.py

from django.contrib import admin
from projetos.models.projeto import Projeto, ProjetoPlanta, ProjetoReferencia
from projetos.models.briefing import (
    Briefing, BriefingConversation, BriefingArquivoReferencia, BriefingValidacao
)
from projetos.models.mensagem import Mensagem, AnexoMensagem

# === Inlines para Briefing ===
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
    list_display = ['projeto', 'versao', 'status', 'etapa_atual', 'progresso', 'created_at', 'updated_at']
    list_filter = ['status']
    search_fields = ['projeto__nome']
    readonly_fields = ['versao', 'progresso', 'created_at', 'updated_at']
    fieldsets = [
        ('Informações Gerais', {
            'fields': ['projeto', 'versao', 'status', 'etapa_atual', 'progresso', 'created_at', 'updated_at']
        }),
        # Outros fieldsets conforme campos do briefing
    ]
    inlines = [BriefingValidacaoInline, BriefingArquivoReferenciaInline, BriefingConversationInline]

# === Inlines para Projeto ===
class ProjetoPlantaInline(admin.TabularInline):
    model = ProjetoPlanta
    extra = 0

class ProjetoReferenciaInline(admin.TabularInline):
    model = ProjetoReferencia
    extra = 0

class BriefingInline(admin.TabularInline):
    model = Briefing
    fields = ('versao', 'status', 'etapa_atual', 'progresso')
    readonly_fields = ('versao', 'progresso')
    extra = 0

@admin.register(Projeto)
class ProjetoAdmin(admin.ModelAdmin):
    list_display = ['numero', 'nome', 'criado_por', 'empresa', 'status', 'created_at']
    list_filter = ['status', 'empresa', 'feira']
    search_fields = ['numero', 'nome', 'criado_por__username', 'empresa__nome', 'feira__nome']
    readonly_fields = ['numero', 'created_at', 'updated_at']
    fieldsets = [
        ('Informações Básicas', {
            'fields': [
                'numero', 'nome', 'descricao',
                'empresa', 'criado_por', 'status',
                'orcamento', 'progresso'
            ]
        }),
        ('Feira', {
            'fields': [
                'feira', 'local_evento',
                'cidade_evento', 'estado_evento'
            ]
        }),
        # Seção de briefing removida
    ]
    inlines = [ProjetoPlantaInline, ProjetoReferenciaInline, BriefingInline]

# === Admin para Mensagem e AnexoMensagem ===
class AnexoMensagemInline(admin.TabularInline):
    model = AnexoMensagem
    extra = 0
    readonly_fields = ['nome_original', 'tipo_arquivo', 'tamanho', 'data_upload']
    fields = ['arquivo', 'nome_original', 'tipo_arquivo', 'tamanho', 'data_upload']

@admin.register(Mensagem)
class MensagemAdmin(admin.ModelAdmin):
    list_display = ['projeto', 'briefing', 'remetente', 'destinatario', 'data_envio', 'lida']
    list_filter = ['lida']
    search_fields = ['conteudo', 'remetente__username', 'destinatario__username', 'projeto__nome']
    readonly_fields = ['data_envio']
    fieldsets = [
        ('Informações da Mensagem', {
            'fields': ['projeto', 'briefing', 'remetente', 'destinatario', 'conteudo', 'data_envio', 'lida', 'destacada']
        }),
    ]
    inlines = [AnexoMensagemInline]

# Se quiser visualizar/anexar AnexoMensagem isoladamente:
@admin.register(AnexoMensagem)
class AnexoMensagemAdmin(admin.ModelAdmin):
    list_display = ['mensagem', 'nome_original', 'tipo_arquivo', 'tamanho', 'data_upload']
    search_fields = ['nome_original', 'tipo_arquivo', 'mensagem__conteudo']
