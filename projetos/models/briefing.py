# projetos/models/briefing.py

from django.db import models
from django.db.models import Max
from projetos.models.projeto import Projeto
from core.models import Feira
from core.storage import MinioStorage
import uuid
import os

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

    # Informações gerais do projeto - preenchidas automaticamente
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
    objetivo_evento = models.TextField(
        blank=True, null=True,
        verbose_name="Objetivo do Evento"

    )




    # TELA 1: EVENTO - Datas e Localização
    # Localização do Estande (ÚNICO CAMPO REALMENTE NECESSÁRIO)
    endereco_estande = models.CharField(
        max_length=255,
        blank=True, null=True,
        verbose_name="Endereço do Estande",
        help_text="Localização do estande dentro do pavilhão"
    )
    mapa_estande = models.FileField(
        upload_to='briefing/mapas/',
        storage=MinioStorage(),
        blank=True, null=True,
        verbose_name="Mapa do Estande"
    )

    # TELA 2: ESTANDE - Características Físicas
    
    # Informações do Estande
    medida_frente = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        blank=True, null=True,
        verbose_name="Medida Frente (m)"
    )
    medida_fundo = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        blank=True, null=True,
        verbose_name="Medida Fundo (m)"
    )
    medida_lateral_esquerda = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        blank=True, null=True,
        verbose_name="Medida Lateral Esquerda (m)"
    )
    medida_lateral_direita = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        blank=True, null=True,
        verbose_name="Medida Lateral Direita (m)"
    )
    area_estande = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        blank=True, null=True,
        verbose_name="Área Total do Estande (m²)",
        help_text="Calculada automaticamente"
    )
    estilo_estande = models.TextField(
        blank=True, null=True,
        verbose_name="Estilo do Estande",
        help_text="Ex: Moderno, Clean, Futurista, Rústico, etc."
    )
    material = models.CharField(
        max_length=20,
        choices=(
            ('customizado', 'Customizado'),
            ('misto', 'Misto'),
            ('padrao', 'Padrão (alumínio, vidro)'),
        ),
        blank=True, null=True,
        verbose_name="Materiais"
    )
    
    # Estrutura do Estande
    piso_elevado = models.CharField(
        max_length=20,
        choices=(
            ('sem_elevacao', 'Sem Elevação'),
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
            ('curva', 'Curva'),
            ('outro', 'Outro'),
        ),
        blank=True, null=True,
        verbose_name="Tipo Testeira"
    )
    
    # Funcionalidades / Objetivo do Estande
    tipo_venda = models.CharField(
        max_length=50,
        choices=(
            ('nao', 'Não haverá venda'),
            ('loja', 'Loja'),
            ('balcao', 'Balcão'),
            ('ambos', 'Loja e Balcão'),
        ),
        default='nao',
        verbose_name="Tipo de Venda"
    )
    tipo_ativacao = models.CharField(
        max_length=255,
        blank=True, null=True,
        verbose_name="Tipo de Ativação",
        help_text="Área instagramável, Glorify, Games, etc."
    )
    objetivo_estande = models.TextField(
        blank=True, null=True,
        verbose_name="Objetivo do Estande",
        help_text="Lançamento da coleção, etc."
    )

    # TELA 3: ÁREAS DO ESTANDE - Divisões Funcionais

    # TELA 4: DADOS COMPLEMENTARES
    
    # Referências Visuais
    referencias_dados = models.TextField(
        blank=True, null=True,
        verbose_name="Referências - Dados",
        help_text="Descreva referências de estandes anteriores ou estilos desejados"
    )
    
    # Logotipo e Campanha
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

    # Campos para o relatório PDF
    pdf_file = models.FileField(
        upload_to='briefings/',
        storage=MinioStorage(),
        null=True, blank=True,
        verbose_name="Arquivo PDF do Relatório"
    )
    pdf_generated_at = models.DateTimeField(
        null=True, blank=True,
        verbose_name="Data de Geração do PDF"
    )
    
    
    def precisa_atualizar_pdf(self):
        """Verifica se o relatório PDF precisa ser atualizado"""
        if not self.pdf_file or not self.pdf_generated_at:
            return True
        return self.updated_at > self.pdf_generated_at
    
    def get_pdf_url(self):
        """Retorna a URL do PDF, se existir"""
        if self.pdf_file:
            return self.pdf_file.url
        return None

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
            
            # Copiar dados do projeto
            self.feira = self.projeto.feira
            self.orcamento = self.projeto.orcamento
            self.objetivo_evento = self.projeto.descricao
            
        # Calcula área total se tiver dimensões
        if self.medida_frente and self.medida_fundo:
            self.area_estande = self.medida_frente * self.medida_fundo
            
        # Calcula progresso automático
        etapas_completas = 0
        total_etapas = 4
        if self.endereco_estande:
            etapas_completas += 1
        if self.area_estande and self.estilo_estande:
            etapas_completas += 1
        if self.tem_qualquer_area_estande():
            etapas_completas += 1
        if (self.referencias_dados or self.logotipo or self.campanha_dados):
            etapas_completas += 1
        self.progresso = min(100, int((etapas_completas / total_etapas) * 100))
        super().save(*args, **kwargs)

    def tem_qualquer_area_estande(self):
        """Verifica se pelo menos uma área do estande foi configurada"""
        # Verifica se existe alguma área de exposição, sala, copa ou depósito
        return AreaExposicao.objects.filter(briefing=self).exists() or \
               SalaReuniao.objects.filter(briefing=self).exists() or \
               Copa.objects.filter(briefing=self).exists() or \
               Deposito.objects.filter(briefing=self).exists()

    def __str__(self):
        return f"Briefing v{self.versao} - {self.projeto.nome}"


class AreaExposicao(models.Model):
    """Modelo para áreas de exposição do estande (múltiplas possíveis)"""
    briefing = models.ForeignKey(Briefing, on_delete=models.CASCADE, related_name='areas_exposicao')
    
    # Items disponíveis (checkboxes)
    tem_lounge = models.BooleanField(default=False, verbose_name="Lounge")
    tem_vitrine_exposicao = models.BooleanField(default=False, verbose_name="Vitrine Exposição")
    tem_balcao_recepcao = models.BooleanField(default=False, verbose_name="Balcão Recepção")
    tem_mesas_atendimento = models.BooleanField(default=False, verbose_name="Mesas de Atendimento")
    tem_balcao_cafe = models.BooleanField(default=False, verbose_name="Balcão para Café/Bar")
    tem_balcao_vitrine = models.BooleanField(default=False, verbose_name="Balcão Vitrine")
    tem_caixa_vendas = models.BooleanField(default=False, verbose_name="Caixa para Vendas")
    
    # Outros campos
    equipamentos = models.TextField(
        blank=True, null=True,
        verbose_name="Equipamentos",
        help_text="LED, TVs, etc."
    )
    observacoes = models.TextField(
        blank=True, null=True,
        verbose_name="Observações",
        help_text="Coloque aqui como você imagina a área de exposição"
    )
    metragem = models.DecimalField(
        max_digits=8, decimal_places=2,
        blank=True, null=True,
        verbose_name="Metragem (m²)"
    )
    
    class Meta:
        verbose_name = 'Área de Exposição'
        verbose_name_plural = 'Áreas de Exposição'


class SalaReuniao(models.Model):
    """Modelo para salas de reunião do estande (múltiplas possíveis)"""
    briefing = models.ForeignKey(Briefing, on_delete=models.CASCADE, related_name='salas_reuniao')
    
    capacidade = models.PositiveSmallIntegerField(default=0, verbose_name="Capacidade (pessoas)")
    equipamentos = models.TextField(
        blank=True, null=True,
        verbose_name="Equipamentos",
        help_text="Prateleira, TV, armário, estilo mesa, etc."
    )
    metragem = models.DecimalField(
        max_digits=8, decimal_places=2,
        blank=True, null=True,
        verbose_name="Metragem (m²)"
    )
    
    class Meta:
        verbose_name = 'Sala de Reunião'
        verbose_name_plural = 'Salas de Reunião'


class Copa(models.Model):
    """Modelo para copa do estande"""
    briefing = models.ForeignKey(Briefing, on_delete=models.CASCADE, related_name='copas')
    
    equipamentos = models.TextField(
        blank=True, null=True,
        verbose_name="Equipamentos",
        help_text="Pia, geladeira, bancada, prateleiras, etc."
    )
    metragem = models.DecimalField(
        max_digits=8, decimal_places=2,
        blank=True, null=True,
        verbose_name="Metragem (m²)"
    )
    
    class Meta:
        verbose_name = 'Copa'
        verbose_name_plural = 'Copas'


class Deposito(models.Model):
    """Modelo para depósito do estande"""
    briefing = models.ForeignKey(Briefing, on_delete=models.CASCADE, related_name='depositos')
    
    equipamentos = models.TextField(
        blank=True, null=True,
        verbose_name="Equipamentos",
        help_text="Prateleiras, etc."
    )
    metragem = models.DecimalField(
        max_digits=8, decimal_places=2,
        blank=True, null=True,
        verbose_name="Metragem (m²)"
    )
    
    class Meta:
        verbose_name = 'Depósito'
        verbose_name_plural = 'Depósitos'


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
            ('evento', 'Local Estande'),
            ('estande', 'Características'),
            ('areas_estande', 'Divisões'),
            ('dados_complementares', 'Referências Visuais')
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
        return f"{self.get_secao_display()} - {self.get_status_display()}"


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