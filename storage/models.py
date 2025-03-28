from django.db import models

class ArquivoRastreamento(models.Model):
    """Modelo para rastrear arquivos no Minio e seus metadados"""
    nome_original = models.CharField(max_length=255)
    path_minio = models.CharField(max_length=500, unique=True)
    bucket = models.CharField(max_length=100)
    tipo_arquivo = models.CharField(max_length=50)
    tamanho = models.BigIntegerField(default=0)  # tamanho em bytes
    data_upload = models.DateTimeField(auto_now_add=True)
    md5_hash = models.CharField(max_length=32, blank=True, null=True)  # para verificação de integridade
    
    class Meta:
        db_table = 'arquivos_rastreamento'
        verbose_name = 'Arquivo Rastreado'
        verbose_name_plural = 'Arquivos Rastreados'
    
    def __str__(self):
        return self.nome_original