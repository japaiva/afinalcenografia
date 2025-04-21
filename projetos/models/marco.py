#project/models/marco.py

from django.db import models
from django.conf import settings
from django.utils import timezone

class ProjetoMarco(models.Model):
    """Registra eventos importantes (marcos) do projeto"""
    TIPO_CHOICES = [
        ('criacao_projeto', 'Criação do Projeto'),
        ('envio_briefing', 'Envio do Briefing'),
        ('validacao_briefing', 'Validação do Briefing'),
        ('inicio_desenvolvimento', 'Início do Desenvolvimento'),
        ('envio_projeto', 'Envio do Projeto'),
        ('analise_projeto', 'Análise do Projeto'),
        ('aprovacao_projeto', 'Aprovação do Projeto'),
        ('inicio_producao', 'Início da Produção'),
        ('entrega_estande', 'Entrega do Estande'),
        ('cancelamento', 'Cancelamento do Projeto'),
        ('outro', 'Outro')
    ]
    
    projeto = models.ForeignKey(
        'projetos.Projeto', on_delete=models.CASCADE,
        related_name='marcos'
    )
    tipo = models.CharField(
        max_length=30, choices=TIPO_CHOICES,
        verbose_name="Tipo de Marco"
    )
    data = models.DateTimeField(
        default=timezone.now,
        verbose_name="Data do Evento"
    )
    observacao = models.TextField(
        blank=True, null=True,
        verbose_name="Observação"
    )
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='marcos_registrados',
        verbose_name="Registrado por"
    )
    
    class Meta:
        db_table = 'projeto_marcos'
        verbose_name = 'Marco do Projeto'
        verbose_name_plural = 'Marcos do Projeto'
        ordering = ['-data']
    
    def __str__(self):
        return f"{self.get_tipo_display()} - {self.data:%d/%m/%Y %H:%M}"
    
    def save(self, *args, **kwargs):
        # Se for um novo registro, atualiza o status do projeto
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        if is_new:
            # Mapeia tipos de marco para status do projeto

            status_map = {
                'criacao_projeto': 'briefing_pendente',  # Alterado de 'pendente'
                'envio_briefing': 'briefing_enviado',
                'validacao_briefing': 'briefing_validado',
                'inicio_desenvolvimento': 'projeto_em_desenvolvimento',
                'envio_projeto': 'projeto_enviado',
                'analise_projeto': 'projeto_em_analise',
                'aprovacao_projeto': 'projeto_aprovado',
                'inicio_producao': 'em_producao',
                'entrega_estande': 'concluido',
                'cancelamento': 'cancelado'  # Alterado de 'projeto_cancelado'
            }
            
            if self.tipo in status_map:
                self.projeto.status = status_map[self.tipo]
                
                # Atualiza datas principais no projeto
                if self.tipo == 'envio_briefing':
                    self.projeto.data_envio_briefing = self.data
                elif self.tipo == 'aprovacao_projeto':
                    self.projeto.data_aprovacao_projeto = self.data
                elif self.tipo == 'inicio_producao':
                    self.projeto.data_inicio_producao = self.data
                elif self.tipo == 'entrega_estande':
                    self.projeto.data_entrega_estande = self.data
                
                self.projeto.save()
                # Recalcula métricas
                self.projeto.atualizar_metricas()