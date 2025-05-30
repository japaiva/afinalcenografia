# projetista/admin.py

from django.contrib import admin
from projetista.models import ConceitoVisual, ImagemConceitoVisual

class ImagemConceitoVisualInline(admin.TabularInline):
    model = ImagemConceitoVisual
    extra = 0
    readonly_fields = ['imagem_preview']
    fields = ['descricao', 'angulo_vista', 'principal', 'ia_gerada', 'versao', 'imagem', 'imagem_preview']
    
    def imagem_preview(self, obj):
        if obj.imagem:
            return format_html('<img src="{}" width="150" height="auto" />', obj.imagem.url)
        return "Sem imagem"
    imagem_preview.short_description = 'Prévia'

@admin.register(ConceitoVisual)
class ConceitoVisualAdmin(admin.ModelAdmin):
    list_display = ['titulo', 'projeto', 'projetista', 'etapa_atual', 'status', 'criado_em']
    list_filter = ['etapa_atual', 'status', 'ia_gerado']
    search_fields = ['titulo', 'descricao', 'projeto__nome']
    readonly_fields = ['criado_em', 'atualizado_em']
    inlines = [ImagemConceitoVisualInline]

@admin.register(ImagemConceitoVisual)
class ImagemConceitoVisualAdmin(admin.ModelAdmin):
    list_display = ['conceito', 'descricao', 'angulo_vista', 'principal', 'versao', 'ia_gerada', 'criado_em']
    list_filter = ['angulo_vista', 'principal', 'ia_gerada']
    search_fields = ['descricao', 'conceito__titulo', 'conceito__projeto__nome']
    readonly_fields = ['imagem_preview', 'criado_em']
    
    def imagem_preview(self, obj):
        if obj.imagem:
            return format_html('<img src="{}" width="300" height="auto" />', obj.imagem.url)
        return "Sem imagem"
    imagem_preview.short_description = 'Prévia da Imagem'