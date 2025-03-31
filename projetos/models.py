from django.db import models
from core.models import Usuario, Empresa
from django.utils import timezone

class Projeto(models.Model):
    STATUS_CHOICES = [
        ('pendente', 'Pendente'),
        ('ativo', 'Ativo'),
        ('pausado', 'Pausado'),
        ('concluido', 'Concluído'),
        ('cancelado', 'Cancelado'),
    ]

    nome = models.CharField(max_length=200)
    descricao = models.TextField(blank=True, null=True)
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='projetos')
    cliente = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='projetos')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pendente')
    data_inicio = models.DateField(blank=True, null=True)
    prazo_entrega = models.DateField(blank=True, null=True)
    orcamento = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    progresso = models.IntegerField(default=0, help_text="Progresso em porcentagem (0-100)")
    requisitos = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.nome
    
    class Meta:
        db_table = 'projetos'
        verbose_name = 'Projeto'
        verbose_name_plural = 'Projetos'
        ordering = ['-created_at']

class ArquivoReferencia(models.Model):
    projeto = models.ForeignKey(Projeto, on_delete=models.CASCADE, related_name='arquivos')
    nome = models.CharField(max_length=100)
    arquivo = models.FileField(upload_to='referencias/')
    tipo = models.CharField(max_length=50, blank=True, null=True)
    tamanho = models.PositiveIntegerField(default=0)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.nome
    
    class Meta:
        db_table = 'arquivos_referencia'
        verbose_name = 'Arquivo de Referência'
        verbose_name_plural = 'Arquivos de Referência'