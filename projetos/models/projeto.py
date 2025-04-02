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
    
    # Campos relacionados ao briefing
    tem_briefing = models.BooleanField(default=False)  # Restaurado para compatibilidade com templates
    briefing_status = models.CharField(max_length=20, default='nao_iniciado', choices=(
        ('nao_iniciado', 'Não Iniciado'),
        ('em_andamento', 'Em Andamento'),
        ('enviado', 'Enviado'),
        ('aprovado', 'Aprovado'),
        ('reprovado', 'Reprovado')
    ))

    def __str__(self):
        return self.nome
    
    @property
    def has_briefing(self):
        """Verifica se o projeto tem um briefing associado."""
        return hasattr(self, 'briefing')
    
    def save(self, *args, **kwargs):
        # Garante que tem_briefing reflita a existência de um briefing associado
        if self.pk:  # Se o projeto já existe no banco
            self.tem_briefing = self.has_briefing
            
            # Atualiza o status do briefing se necessário
            if self.tem_briefing and self.briefing_status == 'nao_iniciado':
                self.briefing_status = 'em_andamento'
        
        super().save(*args, **kwargs)
    
    class Meta:
        db_table = 'projetos'
        verbose_name = 'Projeto'
        verbose_name_plural = 'Projetos'
        ordering = ['-created_at']