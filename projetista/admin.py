# projetista/admin.py

from django.contrib import admin
from django.utils.html import format_html
from projetista.models import PlantaBaixa, ConceitoVisualNovo, Modelo3D, ConceitoVisualLegado

# =============================================================================
# PLANTA BAIXA
# =============================================================================

@admin.register(PlantaBaixa)
class PlantaBaixaAdmin(admin.ModelAdmin):
    list_display = ('projeto', 'versao', 'status', 'algoritmo_usado', 'atualizado_em')
    list_filter = ('status', 'algoritmo_usado', 'atualizado_em')
    search_fields = ('projeto__nome', 'projeto__numero')
    readonly_fields = ('criado_em', 'atualizado_em')
    
    fieldsets = (
        ('Informações Básicas', {
            'fields': ('projeto', 'briefing', 'projetista', 'versao', 'status')
        }),
        ('Dados da Planta', {
            'fields': ('dados_json', 'algoritmo_usado', 'parametros_geracao')
        }),
        ('Arquivos', {
            'fields': ('arquivo_svg', 'arquivo_png')
        }),
        ('Versionamento', {
            'fields': ('planta_anterior',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('criado_em', 'atualizado_em'),
            'classes': ('collapse',)
        })
    )

# =============================================================================
# CONCEITO VISUAL NOVO
# =============================================================================

@admin.register(ConceitoVisualNovo)
class ConceitoVisualNovoAdmin(admin.ModelAdmin):
    list_display = ('projeto', 'versao', 'status', 'estilo_visualizacao', 'ia_gerado', 'atualizado_em')
    list_filter = ('status', 'estilo_visualizacao', 'iluminacao', 'ia_gerado', 'atualizado_em')
    search_fields = ('projeto__nome', 'projeto__numero', 'descricao')
    readonly_fields = ('criado_em', 'atualizado_em', 'imagem_preview')
    
    def imagem_preview(self, obj):
        if obj.imagem:
            return format_html('<img src="{}" width="300" height="auto" />', obj.imagem.url)
        return "Sem imagem"
    imagem_preview.short_description = 'Prévia da Imagem'
    
    fieldsets = (
        ('Informações Básicas', {
            'fields': ('projeto', 'briefing', 'planta_baixa', 'projetista', 'versao', 'status')
        }),
        ('Conceito Visual', {
            'fields': ('imagem', 'imagem_preview', 'descricao', 'estilo_visualizacao', 'iluminacao')
        }),
        ('IA e Geração', {
            'fields': ('ia_gerado', 'agente_usado', 'prompt_geracao', 'instrucoes_adicionais'),
            'classes': ('collapse',)
        }),
        ('Versionamento', {
            'fields': ('conceito_anterior',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('criado_em', 'atualizado_em'),
            'classes': ('collapse',)
        })
    )

# =============================================================================
# MODELO 3D
# =============================================================================

@admin.register(Modelo3D)
class Modelo3DAdmin(admin.ModelAdmin):
    list_display = ('projeto', 'versao', 'status', 'get_formatos_disponiveis', 'atualizado_em')
    list_filter = ('status', 'atualizado_em')
    search_fields = ('projeto__nome', 'projeto__numero')
    readonly_fields = ('criado_em', 'atualizado_em', 'preview_imagem')
    
    def preview_imagem(self, obj):
        if obj.imagem_preview:
            return format_html('<img src="{}" width="300" height="auto" />', obj.imagem_preview.url)
        return "Sem preview"
    preview_imagem.short_description = 'Preview do Modelo'
    
    fieldsets = (
        ('Informações Básicas', {
            'fields': ('projeto', 'briefing', 'planta_baixa', 'conceito_visual', 'projetista', 'versao', 'status')
        }),
        ('Arquivos 3D', {
            'fields': ('arquivo_gltf', 'arquivo_obj', 'arquivo_skp', 'imagem_preview', 'preview_imagem')
        }),
        ('Configurações da Cena', {
            'fields': ('dados_cena', 'componentes_usados', 'camera_inicial', 'pontos_interesse'),
            'classes': ('collapse',)
        }),
        ('Versionamento', {
            'fields': ('modelo_anterior',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('criado_em', 'atualizado_em'),
            'classes': ('collapse',)
        })
    )

# =============================================================================
# CONCEITO VISUAL LEGADO (para compatibilidade)
# =============================================================================

@admin.register(ConceitoVisualLegado)
class ConceitoVisualLegadoAdmin(admin.ModelAdmin):
    list_display = ('projeto', 'titulo', 'etapa_atual', 'status', 'ia_gerado', 'criado_em')
    list_filter = ('etapa_atual', 'status', 'ia_gerado')
    search_fields = ('titulo', 'descricao', 'projeto__nome')
    readonly_fields = ('criado_em', 'atualizado_em')
    
    fieldsets = (
        ('Informações Básicas', {
            'fields': ('projeto', 'briefing', 'projetista', 'titulo')
        }),
        ('Conceito', {
            'fields': ('descricao', 'paleta_cores', 'materiais_principais', 'elementos_interativos')
        }),
        ('Status e Etapa', {
            'fields': ('etapa_atual', 'status')
        }),
        ('IA', {
            'fields': ('ia_gerado', 'agente_usado'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('criado_em', 'atualizado_em'),
            'classes': ('collapse',)
        })
    )
    
    class Meta:
        verbose_name = "Conceito Visual (Sistema Antigo)"
        verbose_name_plural = "Conceitos Visuais (Sistema Antigo)"