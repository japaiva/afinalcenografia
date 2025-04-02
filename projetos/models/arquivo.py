from django.db import models
from projetos.models.projeto import Projeto

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