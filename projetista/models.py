# projetista/models.py - VERSÃO ATUALIZADA

from django.db import models
from django.utils import timezone
from django.utils.text import slugify
from core.storage import MinioStorage
from projetos.models import Projeto, Briefing
from core.models import Usuario, Agente
import json

class PlantaBaixa(models.Model):
    """
    Modelo para plantas baixas geradas algoritmicamente
    """
    # Relacionamentos
    projeto = models.ForeignKey(
        Projeto, on_delete=models.CASCADE,
        related_name='plantas_baixas'
    )
    briefing = models.ForeignKey(
        Briefing, on_delete=models.CASCADE,
        related_name='plantas_baixas'
    )
    projetista = models.ForeignKey(
        Usuario, on_delete=models.SET_NULL,
        null=True, related_name='plantas_criadas'
    )
    
    # Arquivos gerados
    arquivo_svg = models.FileField(
        upload_to='plantas_baixas/svg/',
        storage=MinioStorage(),
        verbose_name="Arquivo SVG da Planta"
    )
    arquivo_png = models.FileField(
        upload_to='plantas_baixas/png/',
        storage=MinioStorage(),
        null=True, blank=True,
        verbose_name="Preview PNG"
    )
    
    # Dados estruturados
    dados_json = models.JSONField(
        verbose_name="Dados Estruturados",
        help_text="Coordenadas, áreas, componentes da planta"
    )
    
    # Metadados de geração
    algoritmo_usado = models.CharField(
        max_length=100,
        default='layout_generator_v1',
        verbose_name="Algoritmo Utilizado"
    )
    parametros_geracao = models.JSONField(
        null=True, blank=True,
        verbose_name="Parâmetros de Geração"
    )
    
    # Versionamento
    versao = models.PositiveSmallIntegerField(
        default=1,
        verbose_name="Versão"
    )
    planta_anterior = models.ForeignKey(
        'self', on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='versoes_posteriores',
        verbose_name="Versão Anterior"
    )
    
    # Status
    STATUS_CHOICES = [
        ('gerando', 'Gerando'),
        ('pronta', 'Pronta'),
        ('erro', 'Erro na Geração'),
        ('refinada_ia', 'Refinada por IA')
    ]
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='gerando',
        verbose_name="Status"
    )
    
    # Campos de auditoria
    criado_em = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Criado em"
    )
    atualizado_em = models.DateTimeField(
        auto_now=True,
        verbose_name="Atualizado em"
    )
    
    def __str__(self):
        return f"Planta Baixa v{self.versao} - {self.projeto.nome}"
    
    def get_area_total(self):
        """Retorna área total calculada"""
        if self.dados_json and 'area_total' in self.dados_json:
            return self.dados_json['area_total']
        return None
    
    def get_ambientes(self):
        """Retorna lista de ambientes da planta"""
        if self.dados_json and 'ambientes' in self.dados_json:
            return self.dados_json['ambientes']
        return []
    
    class Meta:
        verbose_name = "Planta Baixa"
        verbose_name_plural = "Plantas Baixas"
        ordering = ['-criado_em']


class ConceitoVisualNovo(models.Model):
    """
    Novo modelo para conceitos visuais baseados em planta baixa
    """
    # Relacionamentos
    projeto = models.ForeignKey(
        Projeto, on_delete=models.CASCADE,
        related_name='conceitos_visuais_novos'
    )
    briefing = models.ForeignKey(
        Briefing, on_delete=models.CASCADE,
        related_name='conceitos_visuais_novos'
    )
    planta_baixa = models.ForeignKey(
        PlantaBaixa, on_delete=models.CASCADE,
        related_name='conceitos_visuais',
        verbose_name="Planta Baixa Base"
    )
    projetista = models.ForeignKey(
        Usuario, on_delete=models.SET_NULL,
        null=True, related_name='conceitos_novos_criados'
    )
    
    # Imagem principal
    imagem = models.ImageField(
        upload_to='conceitos_novos/',
        storage=MinioStorage(),
        verbose_name="Imagem do Conceito"
    )
    
    # Metadados da imagem
    descricao = models.CharField(
        max_length=255,
        verbose_name="Descrição do Conceito"
    )
    estilo_visualizacao = models.CharField(
        max_length=50,
        choices=[
            ('fotorrealista', 'Fotorrealista'),
            ('artistico', 'Artístico'),
            ('tecnico', 'Técnico'),
            ('conceitual', 'Conceitual')
        ],
        default='fotorrealista',
        verbose_name="Estilo de Visualização"
    )
    iluminacao = models.CharField(
        max_length=50,
        choices=[
            ('diurna', 'Iluminação Diurna'),
            ('noturna', 'Iluminação Noturna'),
            ('feira', 'Iluminação de Feira'),
            ('dramatica', 'Iluminação Dramática')
        ],
        default='feira',
        verbose_name="Tipo de Iluminação"
    )
    
    # IA e geração
    ia_gerado = models.BooleanField(
        default=True,
        verbose_name="Gerado por IA"
    )
    agente_usado = models.ForeignKey(
        Agente, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='conceitos_novos_gerados',
        verbose_name="Agente Utilizado"
    )
    prompt_geracao = models.TextField(
        blank=True, null=True,
        verbose_name="Prompt de Geração"
    )
    instrucoes_adicionais = models.TextField(
        blank=True, null=True,
        verbose_name="Instruções Adicionais"
    )
    
    # Versionamento
    versao = models.PositiveSmallIntegerField(
        default=1,
        verbose_name="Versão"
    )
    conceito_anterior = models.ForeignKey(
        'self', on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='versoes_posteriores',
        verbose_name="Versão Anterior"
    )
    
    # Status
    STATUS_CHOICES = [
        ('gerando', 'Gerando'),
        ('pronto', 'Pronto'),
        ('erro', 'Erro na Geração'),
        ('aprovado', 'Aprovado pelo Cliente')
    ]
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='gerando',
        verbose_name="Status"
    )
    
    # Campos de auditoria
    criado_em = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Criado em"
    )
    atualizado_em = models.DateTimeField(
        auto_now=True,
        verbose_name="Atualizado em"
    )
    
    def __str__(self):
        return f"Conceito v{self.versao} - {self.projeto.nome}"
    
    class Meta:
        verbose_name = "Conceito Visual Novo"
        verbose_name_plural = "Conceitos Visuais Novos"
        ordering = ['-criado_em']


class Modelo3D(models.Model):
    """
    Modelo para cenas 3D navegáveis
    """
    # Relacionamentos
    projeto = models.ForeignKey(
        Projeto, on_delete=models.CASCADE,
        related_name='modelos_3d'
    )
    briefing = models.ForeignKey(
        Briefing, on_delete=models.CASCADE,
        related_name='modelos_3d'
    )
    planta_baixa = models.ForeignKey(
        PlantaBaixa, on_delete=models.CASCADE,
        related_name='modelos_3d',
        verbose_name="Planta Baixa Base"
    )
    conceito_visual = models.ForeignKey(
        ConceitoVisualNovo, on_delete=models.CASCADE,
        related_name='modelos_3d',
        verbose_name="Conceito Visual Base"
    )
    projetista = models.ForeignKey(
        Usuario, on_delete=models.SET_NULL,
        null=True, related_name='modelos_3d_criados'
    )
    
    # Arquivos 3D
    arquivo_gltf = models.FileField(
        upload_to='modelos_3d/gltf/',
        storage=MinioStorage(),
        verbose_name="Arquivo GLTF/GLB"
    )
    arquivo_obj = models.FileField(
        upload_to='modelos_3d/obj/',
        storage=MinioStorage(),
        null=True, blank=True,
        verbose_name="Arquivo OBJ (opcional)"
    )
    arquivo_skp = models.FileField(
        upload_to='modelos_3d/skp/',
        storage=MinioStorage(),
        null=True, blank=True,
        verbose_name="Arquivo SketchUp (opcional)"
    )
    
    # Preview
    imagem_preview = models.ImageField(
        upload_to='modelos_3d/previews/',
        storage=MinioStorage(),
        null=True, blank=True,
        verbose_name="Imagem de Preview"
    )
    
    # Configurações da cena 3D
    dados_cena = models.JSONField(
        verbose_name="Dados da Cena 3D",
        help_text="Posições de câmera, iluminação, materiais, etc."
    )
    
    # Biblioteca de componentes usados
    componentes_usados = models.JSONField(
        null=True, blank=True,
        verbose_name="Componentes Utilizados",
        help_text="Lista de componentes da biblioteca MinIO usados"
    )
    
    # Configurações de navegação
    camera_inicial = models.JSONField(
        null=True, blank=True,
        verbose_name="Posição Inicial da Câmera"
    )
    pontos_interesse = models.JSONField(
        null=True, blank=True,
        verbose_name="Pontos de Interesse",
        help_text="Posições de câmera pré-definidas para navegação"
    )
    
    # Versionamento
    versao = models.PositiveSmallIntegerField(
        default=1,
        verbose_name="Versão"
    )
    modelo_anterior = models.ForeignKey(
        'self', on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='versoes_posteriores',
        verbose_name="Versão Anterior"
    )
    
    # Status
    STATUS_CHOICES = [
        ('gerando', 'Gerando Modelo'),
        ('processando', 'Processando Componentes'),
        ('pronto', 'Pronto'),
        ('erro', 'Erro na Geração'),
        ('exportado', 'Exportado')
    ]
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='gerando',
        verbose_name="Status"
    )
    
    # Campos de auditoria
    criado_em = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Criado em"
    )
    atualizado_em = models.DateTimeField(
        auto_now=True,
        verbose_name="Atualizado em"
    )
    
    def __str__(self):
        return f"Modelo 3D v{self.versao} - {self.projeto.nome}"
    
    def get_formatos_disponiveis(self):
        """Retorna lista de formatos disponíveis para download"""
        formatos = []
        if self.arquivo_gltf:
            formatos.append('GLTF/GLB')
        if self.arquivo_obj:
            formatos.append('OBJ')
        if self.arquivo_skp:
            formatos.append('SketchUp')
        return formatos
    
    def get_estatisticas_modelo(self):
        """Retorna estatísticas do modelo 3D"""
        if self.dados_cena and 'estatisticas' in self.dados_cena:
            return self.dados_cena['estatisticas']
        return {}
    
    class Meta:
        verbose_name = "Modelo 3D"
        verbose_name_plural = "Modelos 3D"
        ordering = ['-criado_em']


# Manter o modelo antigo para compatibilidade (renomeado)
class ConceitoVisualLegado(models.Model):
    """
    Modelo legado do conceito visual (antigo sistema de 3 etapas)
    Mantido para compatibilidade com dados existentes
    """
    # [Manter toda a estrutura do ConceitoVisual original]
    projeto = models.ForeignKey(
        Projeto, on_delete=models.CASCADE,
        related_name='conceitos_visuais_legados'
    )
    briefing = models.ForeignKey(
        Briefing, on_delete=models.CASCADE,
        related_name='conceitos_visuais_legados'
    )
    projetista = models.ForeignKey(
        Usuario, on_delete=models.SET_NULL,
        null=True, related_name='conceitos_legados_criados'
    )
    
    # Campos principais do sistema antigo
    titulo = models.CharField(max_length=255, blank=True, null=True)
    descricao = models.TextField()
    paleta_cores = models.TextField(blank=True, null=True)
    materiais_principais = models.TextField(blank=True, null=True)
    elementos_interativos = models.TextField(blank=True, null=True)
    
    ia_gerado = models.BooleanField(default=False)
    agente_usado = models.ForeignKey(
        Agente, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='conceitos_legados_gerados'
    )
    
    etapa_atual = models.PositiveSmallIntegerField(default=1)
    status = models.CharField(max_length=20, default='em_elaboracao')
    
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Conceito Visual (Legado)"
        verbose_name_plural = "Conceitos Visuais (Legados)"
        db_table = 'projetista_conceitovisual'  # Manter tabela original