from django.db import models
from django.conf import settings  # Importe settings em vez de User diretamente

class Projeto(models.Model):
    STATUS_CHOICES = [
        ('novo', 'Novo'),
        ('em_analise', 'Em Análise'),
        ('aprovado', 'Aprovado'),
        ('em_producao', 'Em Produção'),
        ('concluido', 'Concluído'),
        ('cancelado', 'Cancelado'),
    ]
    
    titulo = models.CharField(max_length=200)
    descricao = models.TextField(blank=True, null=True)
    cliente = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='projetos_cliente')
    empresa = models.ForeignKey('core.Empresa', on_delete=models.CASCADE)
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_modificacao = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='novo')
    projetista = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='projetos_projetista'
    )
    gestor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='projetos_gestor'
    )
    prazo = models.DateField(null=True, blank=True)
    valor_estimado = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    def __str__(self):
        return self.titulo
    
class Briefing(models.Model):
    projeto = models.OneToOneField(Projeto, on_delete=models.CASCADE, related_name='briefing')
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_modificacao = models.DateTimeField(auto_now=True)
    aprovado = models.BooleanField(default=False)
    data_aprovacao = models.DateTimeField(null=True, blank=True)
    
    # Campos específicos do briefing serão armazenados como JSON
    dados = models.JSONField(default=dict)
    
    def aprovar(self):
        from django.utils import timezone
        self.aprovado = True
        self.data_aprovacao = timezone.now()
        self.save()
    
    def __str__(self):
        return f"Briefing do projeto {self.projeto.titulo}"

class ArquivoProjeto(models.Model):
    TIPO_CHOICES = [
        ('referencia', 'Referência'),
        ('planta', 'Planta'),
        ('render', 'Render'),
        ('briefing', 'Briefing'),
        ('contrato', 'Contrato'),
        ('outro', 'Outro'),
    ]
    
    projeto = models.ForeignKey(Projeto, on_delete=models.CASCADE, related_name='arquivos')
    nome = models.CharField(max_length=255)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    descricao = models.TextField(blank=True, null=True)
    arquivo_path = models.CharField(max_length=500)  # Caminho no Minio
    upload_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    data_upload = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.nome