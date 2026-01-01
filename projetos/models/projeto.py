# projetos/models/projeto.py

from django.db import models
from django.db.models import Max
from core.models import Usuario, Empresa, Feira
from core.storage import MinioStorage
from django.utils import timezone

import logging
logger = logging.getLogger(__name__)
class Projeto(models.Model):
    TIPO_PROJETO_CHOICES = [
        ('feira_negocios', 'Feira de Negócios'),
        ('outros', 'Outros'),
    ]
    

    STATUS_CHOICES = [
        ('aguardando_manual', 'Aguardando Manual'),
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

    STATUS_DESENVOLVIMENTO_CHOICES = [
        ('nao_iniciado', 'Não Iniciado'),
        ('conceito_visual', 'Conceito Visual'),
        ('renderizacao_3d', 'Renderização 3D'),
        ('projeto_executivo', 'Projeto Executivo'),
        ('calculo_custos', 'Cálculo de Custos'),
        ('detalhamento', 'Detalhamento'),
        ('concluido', 'Concluído'),
    ]


    numero = models.PositiveIntegerField(
        verbose_name="Número do Projeto", editable=False,
        help_text="Sequência única por empresa"
    )
    tipo_projeto = models.CharField(
        max_length=20, 
        choices=TIPO_PROJETO_CHOICES,
        default='feira_negocios',
        verbose_name="Tipo de Projeto"
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

    # Metadados de análise visual (preparação para automação futura)
    layout_identificado = models.JSONField(
        default=dict, blank=True,
        verbose_name="Layout do Esboço Identificado",
        help_text="Estrutura JSON com áreas identificadas no esboço da planta"
    )

    inspiracoes_visuais = models.JSONField(
        default=dict, blank=True, 
        verbose_name="Inspirações das Referências",
        help_text="Análise das imagens de referência enviadas pelo cliente"
    )

    # Controle de processamento
    analise_visual_processada = models.BooleanField(
        default=False,
        verbose_name="Análise Visual Processada"
    )

    data_analise_visual = models.DateTimeField(
        blank=True, null=True,
        verbose_name="Data da Análise Visual"
    )

    # Planta Baixa (gerada em 4 etapas)
    planta_baixa_json = models.JSONField(
        default=dict, blank=True,
        verbose_name="Planta Baixa Estruturada",
        help_text="Dados estruturados da planta baixa (layout, áreas, dimensões)"
    )

    planta_baixa_svg = models.TextField(
        blank=True, null=True,
        verbose_name="Representação SVG da Planta",
        help_text="Desenho técnico em formato SVG para visualização"
    )

    planta_baixa_processada = models.BooleanField(
        default=False,
        verbose_name="Planta Baixa Processada"
    )

    data_planta_baixa = models.DateTimeField(
        blank=True, null=True,
        verbose_name="Data de Geração da Planta Baixa"
    )

    # Renderização AI (Módulo 2)
    renderizacao_ai_json = models.JSONField(
        default=dict, blank=True,
        verbose_name="Conceito Visual Enriquecido",
        help_text="JSON enriquecido com planta + briefing + elementos visuais"
    )

    imagem_conceito_url = models.URLField(
        max_length=500, blank=True, null=True,
        verbose_name="URL da Imagem DALL-E",
        help_text="Link da imagem conceitual gerada pela IA"
    )

    prompt_dalle_atual = models.TextField(
        blank=True, null=True,
        verbose_name="Prompt DALL-E Atual",
        help_text="Último prompt usado para gerar a imagem"
    )

    renderizacao_ai_processada = models.BooleanField(
        default=False,
        verbose_name="Renderização AI Processada"
    )

    data_renderizacao_ai = models.DateTimeField(
        blank=True, null=True,
        verbose_name="Data da Renderização AI"
    )

    # Modelo 3D (Módulo 3)
    arquivo_3d = models.FileField(
        upload_to='modelos_3d/', blank=True, null=True,
        storage=MinioStorage(),
        verbose_name="Arquivo 3D (SketchUp)",
        help_text="Modelo 3D exportado (.skp)"
    )

    modelo_3d_processado = models.BooleanField(
        default=False,
        verbose_name="Modelo 3D Processado"
    )

    data_modelo_3d = models.DateTimeField(
        blank=True, null=True,
        verbose_name="Data de Geração do Modelo 3D"
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

    projetista = models.ForeignKey(
        'core.Usuario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='projetos_atribuidos'
    )
  
    status_desenvolvimento = models.CharField(
        max_length=30, 
        choices=STATUS_DESENVOLVIMENTO_CHOICES,
        default='nao_iniciado', 
        verbose_name="Status de Desenvolvimento"
    )
    
    class Meta:
        db_table = 'projetos'
        verbose_name = 'Projeto'
        verbose_name_plural = 'Projetos'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['empresa', '-created_at'], name='idx_proj_emp_created'),
            models.Index(fields=['status'], name='idx_proj_status'),
            models.Index(fields=['feira'], name='idx_proj_feira'),
            models.Index(fields=['tipo_projeto'], name='idx_proj_tipo'),
        ]

    def definir_status_inicial(self):
        if self.tipo_projeto == 'feira_negocios':
            tem_manual = False
            manual_name = ''
            if self.feira and self.feira.manual:
                manual_name = self.feira.manual.name
                try:
                    tem_manual = bool(manual_name and self.feira.manual.storage.exists(manual_name))
                except Exception as e:
                    logger.error(f"[ERRO] Ao verificar existência do manual: {e}")
                    tem_manual = False

            logger.info(f"[STATUS-INICIAL] Projeto: {self.nome}, Feira: {self.feira}, Manual: '{manual_name}', Tem manual válido? {tem_manual}")
            self.status = 'briefing_pendente' if tem_manual else 'aguardando_manual'
        else:
            self.status = 'briefing_pendente'
            logger.info(f"[STATUS-INICIAL] Projeto: {self.nome}, Tipo: {self.tipo_projeto}, Status: briefing_pendente")

    def save(self, *args, **kwargs):
        # Garante que o status sempre será definido pela lógica
        self.definir_status_inicial()

        if not self.pk:
            ultimo = Projeto.objects.filter(empresa=self.empresa).aggregate(Max('numero'))['numero__max'] or 0
            self.numero = ultimo + 1
    
        # Nome automático se feira_negocios
        if self.tipo_projeto == 'feira_negocios' and self.feira:
            self.nome = self.feira.nome

        if not self.pk and self.tipo_projeto == 'feira_negocios' and not self.feira and not self.nome:
            self.nome = "Feira Sem Nome"

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
        # Verifica se o objeto já está salvo antes de fazer a consulta
        if not self.pk:
            return False
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