# models/projeto.py

from django.db import models
from core.models import Usuario, Empresa, Feira
from django.utils import timezone
from core.storage import MinioStorage

class Projeto(models.Model):
    STATUS_CHOICES = [
        ('pendente', 'Pendente'),
        ('ativo', 'Ativo'),
        ('pausado', 'Pausado'),
        ('concluido', 'Concluído'),
        ('cancelado', 'Cancelado'),
    ]

    # Campos básicos do projeto
    nome = models.CharField(max_length=200, verbose_name="Nome do Projeto")
    descricao = models.TextField(blank=True, null=True, verbose_name="Descrição")
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='projetos', verbose_name="Empresa")
    cliente = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='projetos', verbose_name="Cliente")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pendente', verbose_name="Status")
    
    # Campos financeiros
    orcamento = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Orçamento Total (R$)")
    progresso = models.IntegerField(default=0, help_text="Progresso em porcentagem (0-100)", verbose_name="Progresso")
    
    # Relação com a feira
    feira = models.ForeignKey(Feira, on_delete=models.SET_NULL, null=True, blank=True, 
                              related_name='projetos', verbose_name="Feira")
    
    # Campos preenchidos automaticamente a partir da feira selecionada
    local_evento = models.CharField(max_length=255, blank=True, null=True, verbose_name="Local do Evento")
    cidade_evento = models.CharField(max_length=100, blank=True, null=True, verbose_name="Cidade")
    estado_evento = models.CharField(max_length=2, blank=True, null=True, verbose_name="UF")
    
    # Metadados
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Data de Criação")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Última Atualização")
    
    # Campos de controle do briefing
    tem_briefing = models.BooleanField(default=False, verbose_name="Possui Briefing")
    briefing_status = models.CharField(max_length=20, default='nao_iniciado', 
                               choices=(
                                  ('nao_iniciado', 'Não Iniciado'),
                                  ('em_andamento', 'Em Andamento'),
                                  ('enviado', 'Enviado'),
                                  ('aprovado', 'Aprovado'),
                                  ('reprovado', 'Reprovado')
                               ),
                               verbose_name="Status do Briefing")
    
    def atualizar_dados_feira(self):
        """
        Atualiza os campos do projeto com base na feira selecionada.
        Este método deve ser chamado sempre que a feira for alterada.
        """
        if self.feira:
            self.local_evento = self.feira.local
            self.cidade_evento = self.feira.cidade
            self.estado_evento = self.feira.estado
    
    def save(self, *args, **kwargs):
        # Atualiza dados da feira ao salvar
        if self.feira:
            self.atualizar_dados_feira()
            
        # Atualiza status do briefing se necessário
        if hasattr(self, 'briefing') and self.briefing_status == 'nao_iniciado':
            self.briefing_status = 'em_andamento'
            self.tem_briefing = True
        
        super().save(*args, **kwargs)
    
    @property
    def has_briefing(self):
        """Verifica se o projeto tem um briefing associado."""
        return hasattr(self, 'briefing')
    
    @property
    def manual_feira(self):
        """Retorna o manual da feira, se disponível."""
        if self.feira and self.feira.manual:
            return self.feira.manual
        return None
        
    @property
    def data_inicio(self):
        """Retorna a data de início da feira."""
        if self.feira:
            return self.feira.data_inicio
        return None
        
    @property
    def data_termino(self):
        """Retorna a data de término da feira."""
        if self.feira:
            return self.feira.data_fim
        return None
    
    def __str__(self):
        return self.nome
    
    class Meta:
        db_table = 'projetos'
        verbose_name = 'Projeto'
        verbose_name_plural = 'Projetos'
        ordering = ['-created_at']


class ProjetoPlanta(models.Model):
    """
    Modelo para armazenar plantas do estande ou localização
    """
    projeto = models.ForeignKey(Projeto, on_delete=models.CASCADE, related_name='plantas')
    nome = models.CharField(max_length=255, verbose_name="Nome da Planta")
    arquivo = models.FileField(
        upload_to='projetos/plantas/', 
        storage=MinioStorage(),
        verbose_name="Arquivo da Planta"
    )
    tipo = models.CharField(
        max_length=50, 
        choices=(
            ('localizacao', 'Planta de Localização'),
            ('estande', 'Planta do Estande'),
            ('pavilhao', 'Planta do Pavilhão'),
            ('outro', 'Outro Tipo')
        ),
        verbose_name="Tipo de Planta"
    )
    observacoes = models.TextField(blank=True, null=True, verbose_name="Observações")
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name="Data de Upload")
    
    def __str__(self):
        return f"{self.nome} - {self.get_tipo_display()}"
    
    class Meta:
        db_table = 'projeto_plantas'
        verbose_name = 'Planta do Projeto'
        verbose_name_plural = 'Plantas do Projeto'


class ProjetoReferencia(models.Model):
    """
    Modelo para armazenar arquivos de referência visual do projeto
    """
    projeto = models.ForeignKey(Projeto, on_delete=models.CASCADE, related_name='referencias')
    nome = models.CharField(max_length=255, verbose_name="Nome da Referência")
    arquivo = models.FileField(
        upload_to='projetos/referencias/', 
        storage=MinioStorage(),
        verbose_name="Arquivo de Referência"
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
            ('outro', 'Outro')
        ),
        verbose_name="Tipo de Referência"
    )
    observacoes = models.TextField(blank=True, null=True, verbose_name="Observações")
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name="Data de Upload")
    
    def __str__(self):
        return f"{self.nome} - {self.get_tipo_display()}"
    
    class Meta:
        db_table = 'projeto_referencias'
        verbose_name = 'Referência do Projeto'
        verbose_name_plural = 'Referências do Projeto'