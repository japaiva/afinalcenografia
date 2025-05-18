# projetista/models.py

from django.db import models
from django.utils import timezone
from core.storage import MinioStorage
from projetos.models import Projeto, Briefing
from core.models import Usuario, Agente

class ConceitoVisual(models.Model):
    # Relacionamentos
    projeto = models.ForeignKey(
        Projeto, on_delete=models.CASCADE,
        related_name='conceitos_visuais'
    )
    briefing = models.ForeignKey(
        Briefing, on_delete=models.CASCADE,
        related_name='conceitos_visuais'
    )
    projetista = models.ForeignKey(
        Usuario, on_delete=models.SET_NULL,
        null=True, related_name='conceitos_criados'
    )
    
    # Campos principais
    titulo = models.CharField(
        max_length=255, blank=True, null=True,
        verbose_name="Título do Conceito"
    )
    descricao = models.TextField(
        verbose_name="Descrição do Conceito"
    )
    paleta_cores = models.TextField(
        blank=True, null=True,
        verbose_name="Paleta de Cores"
    )
    materiais_principais = models.TextField(
        blank=True, null=True,
        verbose_name="Materiais Principais"
    )
    
    # Campos de controle e IA
    ia_gerado = models.BooleanField(
        default=False,
        verbose_name="Gerado por IA"
    )
    agente_usado = models.ForeignKey(
        Agente, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='conceitos_gerados',
        verbose_name="Agente Utilizado"
    )
    
    # Status
    STATUS_CHOICES = [
        ('em_elaboracao', 'Em Elaboração'),
        ('aguardando_imagens', 'Aguardando Imagens'),
        ('finalizado', 'Finalizado'),
        ('aprovado', 'Aprovado'),
        ('rejeitado', 'Rejeitado')
    ]
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='em_elaboracao',
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
        if self.titulo:
            return f"{self.titulo} - {self.projeto.nome}"
        return f"Conceito para {self.projeto.nome}"
    
    class Meta:
        verbose_name = "Conceito Visual"
        verbose_name_plural = "Conceitos Visuais"
        ordering = ['-criado_em']

class ImagemConceitoVisual(models.Model):
    # Vistas/ângulos pré-definidos para categorização
    ANGULOS_CHOICES = [
        ('frontal', 'Vista Frontal'),
        ('perspectiva', 'Perspectiva Externa'),
        ('lateral_esquerda', 'Lateral Esquerda'),
        ('lateral_direita', 'Lateral Direita'),
        ('interior', 'Vista Interior'),
        ('superior', 'Vista Superior/Planta'),
        ('detalhe', 'Detalhe'),
        ('outro', 'Outro Ângulo')
    ]
    
    conceito = models.ForeignKey(
        ConceitoVisual, on_delete=models.CASCADE,
        related_name='imagens'
    )
    imagem = models.ImageField(
        upload_to='conceitos_visuais/',
        storage=MinioStorage(),
        verbose_name="Imagem"
    )
    descricao = models.CharField(
        max_length=255,
        verbose_name="Descrição"
    )
    angulo_vista = models.CharField(
        max_length=50,
        choices=ANGULOS_CHOICES,
        default='outro',
        verbose_name="Ângulo/Vista"
    )
    ia_gerada = models.BooleanField(
        default=False,
        verbose_name="Gerada por IA"
    )
    ordem = models.PositiveSmallIntegerField(
        default=0,
        verbose_name="Ordem de Exibição"
    )
    criado_em = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Criado em"
    )
    
    def __str__(self):
        return f"{self.get_angulo_vista_display()} - {self.conceito}"
    
    class Meta:
        verbose_name = "Imagem de Conceito"
        verbose_name_plural = "Imagens de Conceito"
        ordering = ['ordem', 'criado_em']