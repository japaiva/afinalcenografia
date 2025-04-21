# projetos/models/briefing.py

from django.db import models
from django.db.models import Max
from projetos.models.projeto import Projeto
from core.models import Feira
from core.storage import MinioStorage

class Briefing(models.Model):
    STATUS_CHOICES = (
        ('rascunho', 'Rascunho'),
        ('em_validacao', 'Em Validação'),
        ('validado', 'Validado'),
        ('enviado', 'Enviado'),
        ('revisao', 'Em Revisão'),
        ('aprovado', 'Aprovado'),
    )

    projeto = models.ForeignKey(
        Projeto,
        on_delete=models.CASCADE,
        related_name='briefings',
        verbose_name="Projeto"
    )
    versao = models.PositiveSmallIntegerField(
        default=1,
        verbose_name="Versão do Briefing"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='rascunho',
        verbose_name="Status"
    )
    etapa_atual = models.PositiveSmallIntegerField(
        default=1,
        verbose_name="Etapa Atual"
    )
    progresso = models.PositiveSmallIntegerField(
        default=0,
        verbose_name="Progresso"
    )

    # TELA 1: PROJETO (dados gerais)
    nome_projeto = models.CharField(
        max_length=200,
        blank=True, null=True,
        verbose_name="Nome do Projeto"
    )
    feira = models.ForeignKey(
        Feira,
        on_delete=models.SET_NULL,
        blank=True, null=True,
        related_name='briefings',
        verbose_name="Feira/Evento"
    )
    orcamento = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True, null=True,
        verbose_name="Orçamento"
    )
    objetivo = models.TextField(
        blank=True, null=True,
        verbose_name="Objetivo do Projeto"
    )

    # TELA 2: EVENTO (datas e localização)
    local_evento = models.CharField(
        max_length=255,
        blank=True, null=True,
        verbose_name="Local do Evento"
    )
    data_feira_inicio = models.DateField(
        blank=True, null=True,
        verbose_name="Data Início da Feira"
    )
    data_feira_fim = models.DateField(
        blank=True, null=True,
        verbose_name="Data Término da Feira"
    )
    horario_feira = models.CharField(
        max_length=100,
        blank=True, null=True,
        verbose_name="Horário da Feira"
    )
    data_montagem_inicio = models.DateTimeField(
        blank=True, null=True,
        verbose_name="Início da Montagem"
    )
    data_montagem_fim = models.DateTimeField(
        blank=True, null=True,
        verbose_name="Término da Montagem"
    )
    data_desmontagem_inicio = models.DateTimeField(
        blank=True, null=True,
        verbose_name="Início da Desmontagem"
    )
    data_desmontagem_fim = models.DateTimeField(
        blank=True, null=True,
        verbose_name="Término da Desmontagem"
    )
    endereco_estande = models.TextField(
        blank=True, null=True,
        verbose_name="Endereço do Estande",
        help_text="Localização do estande dentro do pavilhão"
    )

    # TELA 3: ESTANDE (características físicas)
    area_estande = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        blank=True, null=True,
        verbose_name="Área do Estande (m²)"
    )
    estilo_estande = models.CharField(
        max_length=100,
        blank=True, null=True,
        verbose_name="Estilo do Estande",
        help_text="Ex: Moderno, Clean, Futurista, Rústico, etc."
    )
    cores = models.TextField(
        blank=True, null=True,
        verbose_name="Cores",
        help_text="Cores principais, referências Pantone, amadeirado, etc."
    )
    material = models.TextField(
        blank=True, null=True,
        verbose_name="Materiais",
        help_text="Materiais predominantes a serem utilizados"
    )
    piso_elevado = models.CharField(
        max_length=20,
        choices=(
            ('nao', 'Sem Elevação'),
            ('3cm', 'Elevado 3cm'),
            ('10cm', 'Elevado 10cm'),
            ('outro', 'Outra Elevação'),
        ),
        blank=True, null=True,
        verbose_name="Piso Elevado"
    )
    tipo_testeira = models.CharField(
        max_length=20,
        choices=(
            ('reta', 'Reta'),
            ('curvada', 'Curvada'),
            ('outro', 'Outro Estilo'),
        ),
        blank=True, null=True,
        verbose_name="Tipo de Testeira"
    )
    havera_venda = models.BooleanField(
        default=False,
        verbose_name="Haverá venda no estande?"
    )
    havera_ativacao = models.BooleanField(
        default=False,
        verbose_name="Haverá ativação no estande?"
    )
    observacoes_estande = models.TextField(
        blank=True, null=True,
        verbose_name="Observações"
    )

    # TELA 4: ÁREAS DO ESTANDE (divisões funcionais)
    area_aberta_tamanho = models.DecimalField(
        max_digits=8, decimal_places=2,
        blank=True, null=True,
        verbose_name="Metragem Área Aberta (m²)"
    )
    tem_mesas_atendimento = models.BooleanField(default=False, verbose_name="Mesas de Atendimento")
    qtd_mesas_atendimento = models.PositiveSmallIntegerField(default=0, verbose_name="Quantidade de Mesas")
    tem_lounge = models.BooleanField(default=False, verbose_name="Lounge")
    tem_balcao_cafe = models.BooleanField(default=False, verbose_name="Balcão para Café/Bar")
    tem_vitrine = models.BooleanField(default=False, verbose_name="Vitrine para Exposição")
    tem_balcao_vitrine = models.BooleanField(default=False, verbose_name="Balcão Vitrine")
    tem_balcao_recepcao = models.BooleanField(default=False, verbose_name="Balcão Recepção")
    tem_caixa = models.BooleanField(default=False, verbose_name="Caixa para Vendas")
    equipamentos = models.TextField(
        blank=True, null=True,
        verbose_name="Equipamentos",
        help_text="Painel de LED, TV, etc."
    )

    tem_sala_reuniao = models.BooleanField(default=False, verbose_name="Sala de Reunião")
    sala_reuniao_capacidade = models.PositiveSmallIntegerField(default=0, verbose_name="Capacidade (pessoas)")
    sala_reuniao_equipamentos = models.TextField(
        blank=True, null=True,
        verbose_name="Equipamentos da Sala",
        help_text="Prateleira, TV, Armário, etc."
    )
    sala_reuniao_tamanho = models.DecimalField(
        max_digits=8, decimal_places=2,
        blank=True, null=True,
        verbose_name="Metragem Sala de Reunião (m²)"
    )

    tem_copa = models.BooleanField(default=False, verbose_name="Copa")
    copa_equipamentos = models.TextField(
        blank=True, null=True,
        verbose_name="Equipamentos da Copa",
        help_text="Pia, geladeira, bancada, prateleiras, etc."
    )
    copa_tamanho = models.DecimalField(
        max_digits=8, decimal_places=2,
        blank=True, null=True,
        verbose_name="Metragem Copa (m²)"
    )

    tem_deposito = models.BooleanField(default=False, verbose_name="Depósito")
    deposito_equipamentos = models.TextField(
        blank=True, null=True,
        verbose_name="Equipamentos do Depósito",
        help_text="Prateleiras, etc."
    )
    deposito_tamanho = models.DecimalField(
        max_digits=8, decimal_places=2,
        blank=True, null=True,
        verbose_name="Metragem Depósito (m²)"
    )

    # DADOS COMPLEMENTARES
    referencias_dados = models.TextField(
        blank=True, null=True,
        verbose_name="Referências - Dados",
        help_text="Descreva referências de estandes anteriores ou estilos desejados"
    )
    logotipo = models.TextField(
        blank=True, null=True,
        verbose_name="Informações sobre o Logotipo",
        help_text="Descreva detalhes sobre a aplicação do logotipo no estande"
    )
    campanha_dados = models.TextField(
        blank=True, null=True,
        verbose_name="Campanha - Dados",
        help_text="Informações sobre a campanha atual e como deve ser aplicada no estande"
    )

    # Metadados
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Atualizado em")
    validado_por_ia = models.BooleanField(default=False, verbose_name="Validado por IA")

    class Meta:
        unique_together = ('projeto', 'versao')
        ordering = ['projeto', '-versao']
        verbose_name = 'Briefing'
        verbose_name_plural = 'Briefings'

    def save(self, *args, **kwargs):
        # Versão incremental
        if not self.pk:
            ultima = Briefing.objects.filter(projeto=self.projeto).aggregate(Max('versao'))['versao__max'] or 0
            self.versao = ultima + 1
        # Calcula progresso automático
        etapas_completas = 0
        total_etapas = 4
        if self.local_evento and self.data_feira_inicio and self.data_feira_fim:
            etapas_completas += 1
        if self.area_estande and self.estilo_estande:
            etapas_completas += 1
        if (self.area_aberta_tamanho or self.tem_sala_reuniao or self.tem_copa or self.tem_deposito):
            etapas_completas += 1
        if (self.referencias_dados or self.logotipo or self.campanha_dados):
            etapas_completas += 1
        self.progresso = min(100, int((etapas_completas / total_etapas) * 100))
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Briefing v{self.versao} - {self.projeto.nome}"


class BriefingArquivoReferencia(models.Model):
    briefing = models.ForeignKey(Briefing, on_delete=models.CASCADE, related_name='arquivos')
    nome = models.CharField(max_length=255)
    arquivo = models.FileField(upload_to='briefing/referencias/', storage=MinioStorage())
    tipo = models.CharField(
        max_length=50,
        choices=(
            ('imagem', 'Imagem'),
            ('planta', 'Planta'),
            ('logo', 'Logo'),
            ('campanha', 'Imagem de Campanha'),
            ('referencia', 'Referência de Estande'),
            ('documento', 'Documento'),
            ('outro', 'Outro')
        )
    )
    observacoes = models.TextField(blank=True, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Arquivo de Referência'
        verbose_name_plural = 'Arquivos de Referência'

    def __str__(self):
        return self.nome


class BriefingValidacao(models.Model):
    briefing = models.ForeignKey(Briefing, on_delete=models.CASCADE, related_name='validacoes')
    secao = models.CharField(
        max_length=50,
        choices=(
            ('evento', 'Evento - Datas e Localização'),
            ('estande', 'Estande - Características Físicas'),
            ('areas_estande', 'Áreas do Estande - Divisões Funcionais'),
            ('dados_complementares', 'Dados Complementares - Referências Visuais')
        )
    )
    status = models.CharField(
        max_length=20,
        choices=(
            ('pendente', 'Pendente'),
            ('atencao', 'Atenção'),
            ('aprovado', 'Aprovado'),
            ('reprovado', 'Reprovado')
        )
    )
    mensagem = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('briefing', 'secao')
        verbose_name = 'Validação de Briefing'
        verbose_name_plural = 'Validações de Briefing'

    def __str__(self):
        return f"{self.secao} - {self.status}"


class BriefingConversation(models.Model):
    briefing = models.ForeignKey(Briefing, on_delete=models.CASCADE, related_name='conversas')
    mensagem = models.TextField()
    origem = models.CharField(
        max_length=10,
        choices=(('cliente', 'Cliente'), ('ia', 'IA'))
    )
    etapa = models.PositiveSmallIntegerField(default=1)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Conversa de Briefing'
        verbose_name_plural = 'Conversas de Briefing'

    def __str__(self):
        return f"{self.origem.capitalize()} - {self.timestamp:%d/%m/%Y %H:%M}"
