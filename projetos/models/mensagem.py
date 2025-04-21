# projetos/models/mensagem.py

from django.db import models
from django.conf import settings
from core.storage import MinioStorage

class Mensagem(models.Model):
    projeto = models.ForeignKey(
        'projetos.Projeto', on_delete=models.CASCADE,
        related_name='mensagens'
    )
    briefing = models.ForeignKey(
        'projetos.Briefing', on_delete=models.CASCADE,
        related_name='mensagens', null=True, blank=True,
        verbose_name="Briefing"
    )
    remetente = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='mensagens_enviadas'
    )
    destinatario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='mensagens_recebidas', null=True, blank=True
    )
    conteudo = models.TextField(verbose_name="Conteúdo")
    data_envio = models.DateTimeField(auto_now_add=True, verbose_name="Data de Envio")
    lida = models.BooleanField(default=False, verbose_name="Lida")
    destacada = models.BooleanField(default=False, verbose_name="Destacada")

    class Meta:
        ordering = ['-data_envio']
        verbose_name = 'Mensagem'
        verbose_name_plural = 'Mensagens'

    def __str__(self):
        return f"Mensagem de {self.remetente} em {self.data_envio:%d/%m/%Y %H:%M}"

class AnexoMensagem(models.Model):
    mensagem = models.ForeignKey(Mensagem, on_delete=models.CASCADE, related_name='anexos')
    arquivo = models.FileField(upload_to='mensagens/anexos/', storage=MinioStorage())
    nome_original = models.CharField(max_length=255)
    tipo_arquivo = models.CharField(max_length=100, blank=True, null=True)
    tamanho = models.PositiveIntegerField(default=0, verbose_name="Tamanho (bytes)")
    data_upload = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Anexo: {self.nome_original} ({self.tipo_arquivo})"