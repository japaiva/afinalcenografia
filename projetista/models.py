# projetista/models.py

from django.db import models
from django.utils import timezone

from core.models import Usuario
from projetos.models import Projeto, Briefing

# Caso você não tenha o modelo ConceitoVisual ainda, aqui está um exemplo:
class ConceitoVisual(models.Model):
    briefing = models.OneToOneField('projetos.Briefing', on_delete=models.CASCADE, related_name='conceito_visual')
    projeto = models.ForeignKey('projetos.Projeto', on_delete=models.CASCADE, related_name='conceitos_visuais')
    projetista = models.ForeignKey('core.Usuario', on_delete=models.CASCADE, related_name='conceitos_criados')
    descricao = models.TextField(verbose_name="Descrição do Conceito")
    referencias_utilizadas = models.TextField(verbose_name="Referências Utilizadas", blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Conceito Visual"
        verbose_name_plural = "Conceitos Visuais"
        ordering = ['-criado_em']
    
    def __str__(self):
        return f"Conceito para {self.projeto.nome} (v{self.briefing.versao})"

# Caso deseje um modelo para imagens do conceito
class ImagemConceitoVisual(models.Model):
    conceito = models.ForeignKey(ConceitoVisual, on_delete=models.CASCADE, related_name='imagens')
    imagem = models.ImageField(upload_to='conceitos_visuais/%Y/%m/%d/')
    descricao = models.CharField(max_length=255, blank=True)
    ordem = models.PositiveSmallIntegerField(default=0)
    
    class Meta:
        verbose_name = "Imagem do Conceito"
        verbose_name_plural = "Imagens do Conceito"
        ordering = ['ordem']
    
    def __str__(self):
        return f"Imagem {self.ordem} para Conceito {self.conceito.id}"