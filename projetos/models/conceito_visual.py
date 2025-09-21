# projetos/models/conceito_visual.py

from django.db import models
from django.utils import timezone
from core.storage import MinioStorage
from projetos.models import Projeto, Briefing

class ConceitoVisual(models.Model):
    """
    Modelo para armazenar conceitos visuais gerados por IA
    """
    
    STATUS_CHOICES = [
        ('processando', 'Processando'),
        ('concluido', 'Concluído'),
        ('erro', 'Erro'),
        ('aprovado', 'Aprovado pelo Cliente'),
        ('rejeitado', 'Rejeitado pelo Cliente'),
    ]
    
    MODELO_CHOICES = [
        ('dall-e-3', 'DALL-E 3'),
        ('dall-e-2', 'DALL-E 2'),
        ('midjourney', 'Midjourney'),
        ('stable-diffusion', 'Stable Diffusion'),
        ('stub', 'Imagem de Teste'),
    ]
    
    # Relacionamentos
    projeto = models.ForeignKey(
        Projeto,
        on_delete=models.CASCADE,
        related_name='conceitos_visuais'
    )
    briefing = models.ForeignKey(
        Briefing,
        on_delete=models.CASCADE,
        related_name='conceitos_visuais'
    )
    
    # Dados da geração
    prompt_usado = models.TextField(
        verbose_name="Prompt Utilizado",
        help_text="Prompt completo usado para gerar a imagem"
    )
    prompt_customizado = models.BooleanField(
        default=False,
        verbose_name="Prompt foi customizado",
        help_text="Se o usuário editou o prompt antes de gerar"
    )
    
    # Dados consolidados
    layout_usado = models.JSONField(
        default=dict,
        verbose_name="Layout do Esboço",
        help_text="Dados do layout (Etapa 1) usados na geração"
    )
    inspiracoes_usadas = models.JSONField(
        default=dict,
        verbose_name="Inspirações Visuais",
        help_text="Dados das inspirações (Etapa 2) usadas na geração"
    )
    dataset_consolidado = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Dataset Consolidado",
        help_text="Dados consolidados para debug"
    )
    
    # Imagem gerada
    image_url_original = models.URLField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name="URL Original da Imagem",
        help_text="URL retornada pelo serviço de geração"
    )
    imagem = models.ImageField(
        upload_to='conceitos_visuais/',
        storage=MinioStorage(),
        blank=True,
        null=True,
        verbose_name="Imagem Local",
        help_text="Cópia local da imagem gerada"
    )
    
    # Metadados da geração
    modelo_ia = models.CharField(
        max_length=50,
        choices=MODELO_CHOICES,
        default='dall-e-3',
        verbose_name="Modelo de IA Usado"
    )
    metricas_geracao = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Métricas da Geração",
        help_text="Tamanho do prompt, resolução, tempo, etc."
    )
    
    # Status e timestamps
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='processando',
        verbose_name="Status"
    )
    erro_detalhes = models.TextField(
        blank=True,
        null=True,
        verbose_name="Detalhes do Erro",
        help_text="Se houve erro na geração"
    )
    
    # Feedback do cliente
    aprovado_por = models.ForeignKey(
        'core.Usuario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='conceitos_aprovados'
    )
    data_aprovacao = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Data de Aprovação"
    )
    comentarios_cliente = models.TextField(
        blank=True,
        null=True,
        verbose_name="Comentários do Cliente"
    )
    
    # Versionamento
    versao = models.PositiveIntegerField(
        default=1,
        verbose_name="Versão do Conceito"
    )
    conceito_anterior = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='versoes_posteriores'
    )
    
    # Timestamps
    criado_em = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Data de Criação"
    )
    atualizado_em = models.DateTimeField(
        auto_now=True,
        verbose_name="Última Atualização"
    )
    
    class Meta:
        ordering = ['-criado_em']
        verbose_name = 'Conceito Visual'
        verbose_name_plural = 'Conceitos Visuais'
        indexes = [
            models.Index(fields=['projeto', '-versao']),
            models.Index(fields=['status', 'criado_em']),
        ]
    
    def __str__(self):
        return f"Conceito v{self.versao} - {self.projeto.nome}"
    
    def save(self, *args, **kwargs):
        # Auto-incrementar versão se for novo conceito do mesmo projeto
        if not self.pk and self.projeto_id:
            ultima_versao = ConceitoVisual.objects.filter(
                projeto=self.projeto
            ).aggregate(models.Max('versao'))['versao__max'] or 0
            self.versao = ultima_versao + 1
        
        super().save(*args, **kwargs)
    
    def aprovar(self, usuario, comentario=None):
        """Aprova o conceito visual"""
        self.status = 'aprovado'
        self.aprovado_por = usuario
        self.data_aprovacao = timezone.now()
        if comentario:
            self.comentarios_cliente = comentario
        self.save()
    
    def rejeitar(self, comentario):
        """Rejeita o conceito visual"""
        self.status = 'rejeitado'
        self.comentarios_cliente = comentario
        self.save()
    
    def gerar_nova_versao(self, novo_prompt=None):
        """Cria uma nova versão baseada neste conceito"""
        nova_versao = ConceitoVisual(
            projeto=self.projeto,
            briefing=self.briefing,
            prompt_usado=novo_prompt or self.prompt_usado,
            prompt_customizado=bool(novo_prompt),
            layout_usado=self.layout_usado,
            inspiracoes_usadas=self.inspiracoes_usadas,
            modelo_ia=self.modelo_ia,
            conceito_anterior=self,
            status='processando'
        )
        nova_versao.save()
        return nova_versao
    
    @property
    def eh_ultima_versao(self):
        """Verifica se é a versão mais recente"""
        return not self.versoes_posteriores.exists()
    
    def get_historico_versoes(self):
        """Retorna histórico de versões do conceito"""
        versoes = [self]
        anterior = self.conceito_anterior
        while anterior:
            versoes.insert(0, anterior)
            anterior = anterior.conceito_anterior
        
        # Adicionar versões posteriores
        for posterior in self.versoes_posteriores.all():
            versoes.append(posterior)
            
        return versoes