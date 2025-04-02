from django.db import models
from projetos.models import Projeto

class Briefing(models.Model):
    """
    Modelo para armazenar os dados do briefing de um projeto.
    Cada projeto terá um briefing associado.
    """
    STATUS_CHOICES = (
        ('rascunho', 'Rascunho'),
        ('em_validacao', 'Em Validação'),
        ('validado', 'Validado'),
        ('enviado', 'Enviado'),
        ('revisao', 'Em Revisão'),
        ('aprovado', 'Aprovado'),
    )
    
    projeto = models.OneToOneField(Projeto, on_delete=models.CASCADE, related_name='briefing')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='rascunho')
    etapa_atual = models.PositiveSmallIntegerField(default=1)
    progresso = models.PositiveSmallIntegerField(default=0)  # 0-100%
    
    # Informações básicas
    categoria = models.CharField(max_length=50, blank=True, null=True)
    descricao_detalhada = models.TextField(blank=True, null=True)
    objetivos = models.TextField(blank=True, null=True)
    
    # Detalhes técnicos
    dimensoes = models.PositiveIntegerField(blank=True, null=True)  # em m²
    altura = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)  # em metros
    paleta_cores = models.CharField(max_length=200, blank=True, null=True)
    
    # Materiais e acabamentos
    materiais_preferidos = models.TextField(blank=True, null=True)
    acabamentos = models.TextField(blank=True, null=True)
    
    # Requisitos técnicos
    iluminacao = models.TextField(blank=True, null=True)
    eletrica = models.TextField(blank=True, null=True)
    mobiliario = models.TextField(blank=True, null=True)
    
    # Datas e validações
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    validado_por_ia = models.BooleanField(default=False)
    
    def __str__(self):
        return f"Briefing - {self.projeto.nome}"
    
    def calcular_progresso(self):
        """
        Calcula o progresso do briefing com base nos campos preenchidos.
        Retorna uma porcentagem de 0 a 100.
        """
        # Implementação simplificada - cada seção vale 20%
        progresso = 0
        
        # Informações básicas (20%)
        if self.categoria and self.descricao_detalhada and self.objetivos:
            progresso += 20
        
        # Detalhes técnicos (20%)
        if self.dimensoes and self.altura and self.paleta_cores:
            progresso += 20
        
        # Materiais e acabamentos (20%)
        if self.materiais_preferidos and self.acabamentos:
            progresso += 20
        
        # Requisitos técnicos (20%)
        if self.iluminacao and self.eletrica and self.mobiliario:
            progresso += 20
        
        # Status geral (20%)
        if self.status in ['validado', 'enviado', 'aprovado']:
            progresso += 20
        
        self.progresso = progresso
        return progresso
    
    def save(self, *args, **kwargs):
        self.calcular_progresso()
        super().save(*args, **kwargs)


class BriefingConversation(models.Model):
    """
    Modelo para armazenar a conversa entre o cliente e a IA durante o briefing.
    Cada mensagem é associada a um briefing específico.
    """
    briefing = models.ForeignKey(Briefing, on_delete=models.CASCADE, related_name='conversas')
    mensagem = models.TextField()
    origem = models.CharField(max_length=10, choices=(('cliente', 'Cliente'), ('ia', 'IA')))
    etapa = models.PositiveSmallIntegerField(default=1)  # Para saber em qual etapa a mensagem foi enviada
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['timestamp']
    
    def __str__(self):
        return f"{self.origem.capitalize()} - {self.timestamp.strftime('%d/%m/%Y %H:%M')}"


class BriefingArquivoReferencia(models.Model):
    """
    Modelo para armazenar arquivos de referência associados ao briefing.
    """
    briefing = models.ForeignKey(Briefing, on_delete=models.CASCADE, related_name='arquivos')
    nome = models.CharField(max_length=255)
    arquivo = models.FileField(upload_to='briefing/referencias/')
    tipo = models.CharField(max_length=50, choices=(
        ('imagem', 'Imagem'),
        ('planta', 'Planta'),
        ('documento', 'Documento'),
        ('outro', 'Outro')
    ))
    observacoes = models.TextField(blank=True, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.nome


class BriefingValidacao(models.Model):
    """
    Modelo para armazenar as validações da IA para cada seção do briefing.
    """
    briefing = models.ForeignKey(Briefing, on_delete=models.CASCADE, related_name='validacoes')
    secao = models.CharField(max_length=50)
    status = models.CharField(max_length=20, choices=(
        ('pendente', 'Pendente'),
        ('atencao', 'Atenção'),
        ('aprovado', 'Aprovado'),
        ('reprovado', 'Reprovado')
    ))
    mensagem = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('briefing', 'secao')
    
    def __str__(self):
        return f"{self.secao} - {self.status}"