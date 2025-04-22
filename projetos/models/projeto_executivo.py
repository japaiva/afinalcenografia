# projetos/models/projeto_executivo.py

from django.db import models
from django.utils import timezone
from projetos.models.projeto import Projeto

class ProjetoExecutivo(models.Model):
    projeto    = models.ForeignKey(Projeto, on_delete=models.CASCADE, related_name='executivos')
    versao     = models.PositiveIntegerField(editable=False, verbose_name="Versão")
    arquivo    = models.FileField(upload_to='projetos/executivos/')

    STATUS_CHOICES = (
        ('em_andamento', 'Em Andamento'),
        ('enviado', 'Enviado'),
        ('revisao', 'Em Revisão'),
        ('aprovado', 'Aprovado'),
    )
    status     = models.CharField(max_length=20, choices=STATUS_CHOICES, default='em_andamento')
    criado_em  = models.DateTimeField(auto_now_add=True)
    enviado_em = models.DateTimeField(blank=True, null=True)
    aprovado_em= models.DateTimeField(blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.pk:
            last = ProjetoExecutivo.objects.filter(projeto=self.projeto) \
                                           .aggregate(max_ver=models.Max('versao'))['max_ver'] or 0
            self.versao = last + 1

        now = timezone.now()
        if self.status == 'enviado' and not self.enviado_em:
            self.enviado_em = now
        elif self.status == 'aprovado' and not self.aprovado_em:
            self.aprovado_em = now

        super().save(*args, **kwargs)

    def __str__(self):
        return f"Execução v{self.versao} – {self.projeto}"

    class Meta:
        db_table = 'projeto_executivos'
        verbose_name = 'Projeto Executivo'
        verbose_name_plural = 'Projetos Executivos'
        unique_together = (('projeto', 'versao'),)
        ordering = ['projeto', '-versao']