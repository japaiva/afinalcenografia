# projetista/models.py

from django.db import models
from django.utils import timezone
from django.utils.text import slugify
from core.storage import MinioStorage
from projetos.models import Projeto, Briefing
from core.models import Usuario, Agente

class ConceitoVisual(models.Model):
    """
    Modelo principal para armazenar conceitos visuais de estandes
    """
    # Relacionamentos
    projeto = models.ForeignKey(
        Projeto, on_delete=models.CASCADE,
        related_name='conceitos_visuais'
    )
    briefing = models.ForeignKey(
        Briefing, on_delete=models.CASCADE,
        related_name='conceitos_visuais'
    )
    projetista = models.ForeignKey(
        Usuario, on_delete=models.SET_NULL,
        null=True, related_name='conceitos_criados'
    )
    
    # Campos principais
    titulo = models.CharField(
        max_length=255, blank=True, null=True,
        verbose_name="Título do Conceito"
    )
    descricao = models.TextField(
        verbose_name="Descrição do Conceito"
    )
    paleta_cores = models.TextField(
        blank=True, null=True,
        verbose_name="Paleta de Cores"
    )
    materiais_principais = models.TextField(
        blank=True, null=True,
        verbose_name="Materiais Principais"
    )
    elementos_interativos = models.TextField(
        blank=True, null=True,
        verbose_name="Elementos Interativos",
        help_text="Descrição de como os visitantes interagirão com o espaço"
    )
    
    # Campos de controle e IA
    ia_gerado = models.BooleanField(
        default=False,
        verbose_name="Gerado por IA"
    )
    agente_usado = models.ForeignKey(
        Agente, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='conceitos_gerados',
        verbose_name="Agente Utilizado"
    )
    
    # Campos de processo em etapas
    ETAPA_CHOICES = [
        (1, 'Conceito Textual'),
        (2, 'Imagem Principal'),
        (3, 'Múltiplas Vistas'),
        (4, 'Concluído')
    ]
    etapa_atual = models.PositiveSmallIntegerField(
        choices=ETAPA_CHOICES,
        default=1,
        verbose_name="Etapa Atual"
    )
    
    # Status
    STATUS_CHOICES = [
        ('em_elaboracao', 'Em Elaboração'),
        ('aguardando_imagens', 'Aguardando Imagens'),
        ('finalizado', 'Finalizado'),
        ('aprovado', 'Aprovado'),
        ('rejeitado', 'Rejeitado')
    ]
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='em_elaboracao',
        verbose_name="Status"
    )
    
    # Campos para IA de imagem
    imagem_principal_prompt = models.TextField(
        blank=True, null=True,
        verbose_name="Prompt para Imagem Principal"
    )
    imagem_principal_id = models.CharField(
        max_length=255,
        blank=True, null=True,
        verbose_name="ID da Imagem Principal"
    )
    
    # Campos de auditoria
    criado_em = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Criado em"
    )
    atualizado_em = models.DateTimeField(
        auto_now=True,
        verbose_name="Atualizado em"
    )
    
    def __str__(self):
        if self.titulo:
            return f"{self.titulo} - {self.projeto.nome}"
        return f"Conceito para {self.projeto.nome}"
    
    def gerar_slug(self):
        """Gera um slug único para o conceito visual"""
        if self.titulo:
            base_slug = slugify(self.titulo)
        else:
            base_slug = slugify(f"conceito-{self.projeto.nome}")
        return f"{base_slug}-{self.id}"
    
    def etapa1_concluida(self):
        """Verifica se a etapa 1 está concluída"""
        return self.etapa_concluida(1)

    def etapa2_concluida(self):
        """Verifica se a etapa 2 está concluída"""
        return self.etapa_concluida(2)

    def etapa3_concluida(self):
        """Verifica se a etapa 3 está concluída"""
        return self.etapa_concluida(3)
    
    def etapa_concluida(self, etapa):
        """Verifica se uma determinada etapa está concluída"""
        if etapa == 1:
            # Etapa 1: Conceito Textual está completo quando tem título e descrição
            return bool(self.titulo and self.descricao)
        elif etapa == 2:
            # Etapa 2: Imagem Principal está completa quando existe uma imagem principal
            return self.imagens.filter(principal=True).exists()
        elif etapa == 3:
            # Etapa 3: Múltiplas Vistas está completa quando tem pelo menos 3 ângulos diferentes
            return self.imagens.values('angulo_vista').distinct().count() >= 3
        return False
    
    def get_vistas_cliente(self):
        """Retorna vistas importantes para apresentação ao cliente"""
        vistas_prioritarias = [
            'perspectiva_externa',
            'entrada_recepcao', 
            'interior_principal',
            'area_produtos'
        ]
        return self.imagens.filter(angulo_vista__in=vistas_prioritarias)
    
    def get_vistas_tecnicas(self):
        """Retorna todas as vistas técnicas para fotogrametria"""
        vistas_tecnicas = [
            'planta_baixa',
            'elevacao_frontal',
            'elevacao_lateral_esquerda',
            'elevacao_lateral_direita', 
            'elevacao_fundos'
        ]
        return self.imagens.filter(angulo_vista__in=vistas_tecnicas)
    
    def get_completude_fotogrametria(self):
        """Calcula percentual de completude para fotogrametria"""
        vistas_essenciais = [
            'perspectiva_externa', 'planta_baixa',
            'elevacao_frontal', 'elevacao_lateral_esquerda', 
            'elevacao_lateral_direita', 'elevacao_fundos',
            'interior_parede_norte', 'interior_parede_sul',
            'interior_parede_leste', 'interior_parede_oeste'
        ]
        
        vistas_existentes = self.imagens.filter(
            angulo_vista__in=vistas_essenciais
        ).values_list('angulo_vista', flat=True).distinct()
        
        return (len(vistas_existentes) / len(vistas_essenciais)) * 100
    
    class Meta:
        verbose_name = "Conceito Visual"
        verbose_name_plural = "Conceitos Visuais"
        ordering = ['-criado_em']

class ImagemConceitoVisual(models.Model):
    """
    Modelo para armazenar imagens do conceito visual, incluindo a principal e múltiplas vistas
    """
    # Vistas/ângulos expandidos para fotogrametria
    ANGULOS_CHOICES = [
        # VISTAS PARA CLIENTE (Impactantes)
        ('perspectiva_externa', 'Perspectiva Externa Principal'),
        ('entrada_recepcao', 'Vista da Entrada/Recepção'),
        ('interior_principal', 'Vista Interna Principal'),
        ('area_produtos', 'Área de Produtos/Destaque'),
        
        # VISTAS TÉCNICAS EXTERNAS
        ('elevacao_frontal', 'Elevação Frontal'),
        ('elevacao_lateral_esquerda', 'Elevação Lateral Esquerda'),
        ('elevacao_lateral_direita', 'Elevação Lateral Direita'),
        ('elevacao_fundos', 'Elevação Fundos'),
        ('quina_frontal_esquerda', 'Quina Frontal-Esquerda'),
        ('quina_frontal_direita', 'Quina Frontal-Direita'),
        
        # PLANTA E VISTAS SUPERIORES
        ('planta_baixa', 'Planta Baixa'),
        ('vista_superior', 'Vista Superior'),
        
        # VISTAS INTERNAS SISTEMÁTICAS
        ('interior_parede_norte', 'Interior - Parede Norte'),
        ('interior_parede_sul', 'Interior - Parede Sul'),
        ('interior_parede_leste', 'Interior - Parede Leste'),
        ('interior_parede_oeste', 'Interior - Parede Oeste'),
        ('interior_perspectiva_1', 'Interior - Perspectiva 1'),
        ('interior_perspectiva_2', 'Interior - Perspectiva 2'),
        ('interior_perspectiva_3', 'Interior - Perspectiva 3'),
        
        # DETALHES ESPECÍFICOS
        ('detalhe_balcao', 'Detalhe do Balcão'),
        ('detalhe_display', 'Detalhe dos Displays'),
        ('detalhe_iluminacao', 'Detalhe da Iluminação'),
        ('detalhe_entrada', 'Detalhe da Entrada'),
        
        # OUTROS
        ('outro', 'Outro Ângulo'),
    ]
    
    # Categorias para organização
    CATEGORIA_CHOICES = [
        ('cliente', 'Apresentação para Cliente'),
        ('tecnica_externa', 'Técnica Externa'),
        ('tecnica_interna', 'Técnica Interna'),
        ('planta_elevacao', 'Plantas e Elevações'),
        ('detalhes', 'Detalhes Específicos'),
    ]
    
    conceito = models.ForeignKey(
        ConceitoVisual, on_delete=models.CASCADE,
        related_name='imagens'
    )
    imagem = models.ImageField(
        upload_to='conceitos_visuais/',
        storage=MinioStorage(),
        verbose_name="Imagem"
    )
    descricao = models.CharField(
        max_length=255,
        verbose_name="Descrição"
    )
    angulo_vista = models.CharField(
        max_length=50,
        choices=ANGULOS_CHOICES,
        default='outro',
        verbose_name="Ângulo/Vista"
    )
    categoria = models.CharField(
        max_length=20,
        choices=CATEGORIA_CHOICES,
        default='cliente',
        verbose_name="Categoria"
    )
    principal = models.BooleanField(
        default=False,
        verbose_name="Imagem Principal"
    )
    ia_gerada = models.BooleanField(
        default=False,
        verbose_name="Gerada por IA"
    )
    ordem = models.PositiveSmallIntegerField(
        default=0,
        verbose_name="Ordem de Exibição"
    )
    
    # Campos para controle de versões
    versao = models.PositiveSmallIntegerField(
        default=1,
        verbose_name="Versão"
    )
    imagem_anterior = models.ForeignKey(
        'self', on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='versoes_posteriores',
        verbose_name="Versão Anterior"
    )
    
    # Campos para IA
    prompt_geracao = models.TextField(
        blank=True, null=True,
        verbose_name="Prompt de Geração"
    )
    
    # Campos para fotogrametria
    essencial_fotogrametria = models.BooleanField(
        default=False,
        verbose_name="Essencial para Fotogrametria"
    )
    coordenada_x = models.FloatField(
        null=True, blank=True,
        verbose_name="Coordenada X (opcional)"
    )
    coordenada_y = models.FloatField(
        null=True, blank=True,
        verbose_name="Coordenada Y (opcional)"
    )
    coordenada_z = models.FloatField(
        null=True, blank=True,
        verbose_name="Coordenada Z (opcional)"
    )
    
    criado_em = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Criado em"
    )
    
    def __str__(self):
        return f"{self.get_angulo_vista_display()} - {self.conceito}"
    
    def save(self, *args, **kwargs):
        # Auto-categorizar baseado no ângulo da vista
        if not self.categoria:
            if self.angulo_vista in ['perspectiva_externa', 'entrada_recepcao', 'interior_principal', 'area_produtos']:
                self.categoria = 'cliente'
            elif self.angulo_vista.startswith('elevacao_') or self.angulo_vista.startswith('quina_'):
                self.categoria = 'tecnica_externa'
            elif self.angulo_vista.startswith('interior_'):
                self.categoria = 'tecnica_interna'
            elif self.angulo_vista in ['planta_baixa', 'vista_superior']:
                self.categoria = 'planta_elevacao'
            elif self.angulo_vista.startswith('detalhe_'):
                self.categoria = 'detalhes'
        
        # Marcar como essencial para fotogrametria
        vistas_essenciais = [
            'perspectiva_externa', 'planta_baixa',
            'elevacao_frontal', 'elevacao_lateral_esquerda', 
            'elevacao_lateral_direita', 'elevacao_fundos',
            'interior_parede_norte', 'interior_parede_sul',
            'interior_parede_leste', 'interior_parede_oeste'
        ]
        self.essencial_fotogrametria = self.angulo_vista in vistas_essenciais
        
        super().save(*args, **kwargs)
    
    class Meta:
        verbose_name = "Imagem de Conceito"
        verbose_name_plural = "Imagens de Conceito"
        ordering = ['categoria', 'ordem', 'criado_em']
        
class PackageVistasPreset(models.Model):
    """
    Modelo para definir pacotes pré-definidos de vistas
    """
    nome = models.CharField(max_length=100, verbose_name="Nome do Pacote")
    descricao = models.TextField(verbose_name="Descrição")
    vistas_incluidas = models.JSONField(
        verbose_name="Vistas Incluídas",
        help_text="Lista dos angulos_vista incluídos neste pacote"
    )
    tipo = models.CharField(
        max_length=20,
        choices=[
            ('cliente', 'Apresentação Cliente'),
            ('tecnico', 'Técnico Completo'),
            ('fotogrametria', 'Fotogrametria'),
            ('basico', 'Básico')
        ],
        verbose_name="Tipo do Pacote"
    )
    ativo = models.BooleanField(default=True)
    ordem = models.PositiveSmallIntegerField(default=0)
    
    class Meta:
        verbose_name = "Pacote de Vistas"
        verbose_name_plural = "Pacotes de Vistas"
        ordering = ['tipo', 'ordem']