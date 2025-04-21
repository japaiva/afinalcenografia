# projetos/models/projeto.py

from django.db import models
from django.db.models import Max
from core.models import Usuario, Empresa, Feira
from core.storage import MinioStorage
from django.utils import timezone

class Projeto(models.Model):
    STATUS_CHOICES = [
        ('briefing_pendente', 'Briefing Pendente'),
        ('briefing_validado', 'Briefing Validado'),
        ('briefing_enviado', 'Briefing Enviado'),
        ('projeto_em_desenvolvimento', 'Projeto em Desenvolvimento'),
        ('projeto_enviado', 'Projeto Enviado'),
        ('projeto_em_analise', 'Projeto em Análise'),
        ('projeto_aprovado', 'Projeto Aprovado'),
        ('em_producao', 'Em Produção'),
        ('concluido', 'Concluído'),
        ('cancelado', 'Cancelado'),
    ]

    numero = models.PositiveIntegerField(
        verbose_name="Número do Projeto", editable=False,
        help_text="Sequência única por empresa"
    )
    nome = models.CharField(max_length=200, verbose_name="Nome do Projeto")

    descricao = models.TextField(blank=True, null=True, verbose_name="Descrição")
    empresa = models.ForeignKey(
        Empresa, on_delete=models.CASCADE,
        related_name='projetos', verbose_name="Empresa"
    )
    criado_por = models.ForeignKey(
        Usuario, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='projetos_criados', verbose_name="Criado por"
    )
    status = models.CharField(
        max_length=30, choices=STATUS_CHOICES,
        default='pendente', verbose_name="Status"
    )
    orcamento = models.DecimalField(
        max_digits=10, decimal_places=2,
        default=0, verbose_name="Orçamento Total (R$)"
    )
    progresso = models.IntegerField(
        default=0, help_text="Progresso em porcentagem (0-100)",
        verbose_name="Progresso"
    )

    feira = models.ForeignKey(
        Feira, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='projetos', verbose_name="Feira"
    )
    local_evento = models.CharField(
        max_length=255, blank=True, null=True,
        verbose_name="Local do Evento"
    )
    cidade_evento = models.CharField(
        max_length=100, blank=True, null=True,
        verbose_name="Cidade"
    )
    estado_evento = models.CharField(
        max_length=2, blank=True, null=True,
        verbose_name="UF"
    )

    data_envio_briefing = models.DateTimeField(
        blank=True, null=True, verbose_name="Data de Envio do Briefing",
        help_text="Data em que o último briefing foi enviado"
    )
    data_aprovacao_projeto = models.DateTimeField(
        blank=True, null=True, verbose_name="Data de Aprovação do Projeto",
        help_text="Data em que o projeto foi aprovado pelo cliente"
    )
    data_inicio_producao = models.DateTimeField(
        blank=True, null=True, verbose_name="Data de Início da Produção",
        help_text="Data em que a produção física do estande foi iniciada"
    )
    data_entrega_estande = models.DateTimeField(
        blank=True, null=True, verbose_name="Data de Entrega do Estande",
        help_text="Data em que o estande foi entregue finalizado"
    )

    # Campos para métricas
    tempo_projeto = models.DurationField(
        blank=True, null=True, verbose_name="Tempo de Projeto",
        help_text="Tempo entre o envio do briefing e a aprovação do projeto"
    )
    tempo_producao = models.DurationField(
        blank=True, null=True, verbose_name="Tempo de Produção",
        help_text="Tempo entre a aprovação do projeto e a conclusão"
    )

    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name="Data de Criação"
    )
    updated_at = models.DateTimeField(
        auto_now=True, verbose_name="Última Atualização"
    )

    class Meta:
        db_table = 'projetos'
        verbose_name = 'Projeto'
        verbose_name_plural = 'Projetos'
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        # Sequência por empresa na criação
        if not self.pk:
            ultimo = Projeto.objects.filter(
                empresa=self.empresa
            ).aggregate(Max('numero'))['numero__max'] or 0
            self.numero = ultimo + 1
        # Preenche dados do evento pela feira
        if self.feira:
            self.local_evento = self.feira.local
            self.cidade_evento = self.feira.cidade
            self.estado_evento = self.feira.estado
        super().save(*args, **kwargs)

    def atualizar_metricas(self):
        """Atualiza os campos de métrica baseado nas datas"""
        # Calcula tempo de projeto
        if self.data_envio_briefing and self.data_aprovacao_projeto:
            self.tempo_projeto = self.data_aprovacao_projeto - self.data_envio_briefing
        
        # Calcula tempo de produção
        if self.data_aprovacao_projeto and self.data_entrega_estande:
            self.tempo_producao = self.data_entrega_estande - self.data_aprovacao_projeto
        
        self.save(update_fields=['tempo_projeto', 'tempo_producao'])


    @property
    def has_briefing(self):
        return self.briefings.exists()


class ProjetoPlanta(models.Model):
    projeto = models.ForeignKey(
        Projeto, on_delete=models.CASCADE,
        related_name='plantas'
    )
    nome = models.CharField(max_length=255, verbose_name="Nome da Planta")
    arquivo = models.FileField(
        upload_to='projetos/plantas/',
        storage=MinioStorage(), verbose_name="Arquivo da Planta"
    )
    tipo = models.CharField(
        max_length=50,
        choices=(
            ('localizacao', 'Planta de Localização'),
            ('estande', 'Planta do Estande'),
            ('pavilhao', 'Planta do Pavilhão'),
            ('outro', 'Outro Tipo'),
        ), verbose_name="Tipo de Planta"
    )
    observacoes = models.TextField(
        blank=True, null=True, verbose_name="Observações"
    )
    uploaded_at = models.DateTimeField(
        auto_now_add=True, verbose_name="Data de Upload"
    )

    class Meta:
        db_table = 'projeto_plantas'
        verbose_name = 'Planta do Projeto'
        verbose_name_plural = 'Plantas do Projeto'

    def __str__(self):
        return f"{self.nome} - {self.get_tipo_display()}"


class ProjetoReferencia(models.Model):
    projeto = models.ForeignKey(
        Projeto, on_delete=models.CASCADE,
        related_name='referencias'
    )
    nome = models.CharField(max_length=255, verbose_name="Nome da Referência")
    arquivo = models.FileField(
        upload_to='projetos/referencias/',
        storage=MinioStorage(), verbose_name="Arquivo de Referência"
    )
    tipo = models.CharField(
        max_length=50,
        choices=(
            ('estande_anterior', 'Estande Anterior'),
            ('estilo_visual', 'Estilo Visual'),
            ('logotipo', 'Logotipo'),
            ('campanha', 'Material de Campanha'),
            ('imagem', 'Imagem de Referência'),
            ('documento', 'Documento'),
            ('outro', 'Outro'),
        ), verbose_name="Tipo de Referência"
    )
    observacoes = models.TextField(
        blank=True, null=True, verbose_name="Observações"
    )
    uploaded_at = models.DateTimeField(
        auto_now_add=True, verbose_name="Data de Upload"
    )

    class Meta:
        db_table = 'projeto_referencias'
        verbose_name = 'Referência do Projeto'
        verbose_name_plural = 'Referências do Projeto'

    def __str__(self):
        return f"{self.nome} - {self.get_tipo_display()}"


class ArquivoProjeto(models.Model):
    projeto = models.ForeignKey(
        Projeto, on_delete=models.CASCADE,
        related_name='arquivos'
    )
    arquivo = models.FileField(upload_to='projetos/arquivos/')
    nome_original = models.CharField(max_length=255)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'projeto_arquivos'
        verbose_name = 'Arquivo do Projeto'
        verbose_name_plural = 'Arquivos do Projeto'

    def __str__(self):
        return self.nome_original