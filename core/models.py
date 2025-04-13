from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from django.conf import settings
from core.storage import MinioStorage

class Empresa(models.Model):
    nome = models.CharField(max_length=100)
    cnpj = models.CharField(max_length=18, unique=True)
    endereco = models.CharField(max_length=200, blank=True, null=True)
    telefone = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    logo = models.ImageField(upload_to='logos/', blank=True, null=True, storage=MinioStorage())
    ativa = models.BooleanField(default=True)
    data_cadastro = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.nome
    
    class Meta:
        db_table = 'empresas'
        verbose_name = 'Empresa'
        verbose_name_plural = 'Empresas'


class Usuario(AbstractUser):
    NIVEL_CHOICES = [
        ('admin', 'Admin'),
        ('gestor', 'Gestor'),
        ('projetista', 'Projetista'),
        ('cliente', 'Cliente'),
    ]

    # Desabilitar relacionamentos explicitamente
    groups = None  # Remove o relacionamento com grupos
    user_permissions = None  # Remove o relacionamento com permissões individuais
    
    nivel = models.CharField(max_length=20, choices=NIVEL_CHOICES)
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='usuarios', null=True, blank=True)
    is_superuser = models.BooleanField(default=False)
    last_name = models.CharField(max_length=150, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)
    telefone = models.CharField(max_length=20, blank=True, null=True)
    
    # Removido o campo foto_perfil para evitar duplicação
    # foto_perfil = models.ImageField(upload_to='perfil/', blank=True, null=True)

    def __str__(self):
        return self.username
    
    class Meta:
        db_table = 'usuarios'
        verbose_name = 'Usuário'
        verbose_name_plural = 'Usuários'

class Parametro(models.Model):
    parametro = models.CharField(max_length=50)
    valor = models.FloatField()

    def __str__(self):
        return self.parametro
    
    class Meta:
        db_table = 'parametros'


class PerfilUsuario(models.Model):
    usuario = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='perfil')
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, null=True, blank=True)
    telefone = models.CharField(max_length=20, blank=True, null=True)
    nivel = models.CharField(
        max_length=20,
        choices=[
            ('admin', 'Administrador'),
            ('gestor', 'Gestor'),
            ('projetista', 'Projetista'),
            ('cliente', 'Cliente')
        ],
        default='cliente'
    )
    foto = models.ImageField(upload_to='fotos_perfil/', null=True, blank=True, storage=MinioStorage())
    
    def __str__(self):
        return f"{self.usuario.username} - {self.get_nivel_display()}"

# Feiras
class Feira(models.Model):
    nome = models.CharField(max_length=255, verbose_name="Nome da Feira")
    local = models.CharField(max_length=255, verbose_name="Local/Centro de Exposições")
    cidade = models.CharField(max_length=100, verbose_name="Cidade")
    estado = models.CharField(max_length=2, verbose_name="UF")
    data_inicio = models.DateField(verbose_name="Data de Início")
    data_fim = models.DateField(verbose_name="Data de Término")
    website = models.URLField(blank=True, null=True, verbose_name="Website da Feira")
    contato_organizacao = models.CharField(max_length=255, blank=True, null=True, verbose_name="Contato da Organização")
    email_organizacao = models.EmailField(blank=True, null=True, verbose_name="Email da Organização")
    telefone_organizacao = models.CharField(max_length=20, blank=True, null=True, verbose_name="Telefone da Organização")
    manual = models.FileField(upload_to='manuais_feira/', storage=MinioStorage(), verbose_name="Manual da Feira")
    ativa = models.BooleanField(default=True, verbose_name="Ativa")
    
    # Campos para vetorização
    manual_processado = models.BooleanField(default=False, verbose_name="Manual Processado")
    ultima_atualizacao = models.DateTimeField(auto_now=True, verbose_name="Última Atualização")
    
    # Campos para controle de processamento
    processamento_status = models.CharField(
        max_length=20,
        choices=[
            ('pendente', 'Pendente'),
            ('processando', 'Processando'),
            ('concluido', 'Concluído'),
            ('erro', 'Erro')
        ],
        default='pendente',
        verbose_name="Status de Processamento"
    )
    progresso_processamento = models.IntegerField(default=0, verbose_name="Progresso (%)")
    mensagem_erro = models.TextField(blank=True, null=True, verbose_name="Mensagem de Erro")
    total_paginas = models.IntegerField(default=0, verbose_name="Total de Páginas")
    total_chunks = models.IntegerField(default=0, verbose_name="Total de Chunks")
    pinecone_namespace = models.CharField(max_length=100, blank=True, null=True, verbose_name="Namespace no Pinecone")
    
    def __str__(self):
        return f"{self.nome} ({self.cidade}/{self.estado})"
    
    def reset_processamento(self):
        """Reseta os campos de processamento para iniciar novamente"""
        self.manual_processado = False
        self.processamento_status = 'pendente'
        self.progresso_processamento = 0
        self.mensagem_erro = None
        self.total_paginas = 0
        self.total_chunks = 0
    
    class Meta:
        db_table = 'feiras'
        verbose_name = 'Feira'
        verbose_name_plural = 'Feiras'
        ordering = ['-data_inicio']

class FeiraManualChunk(models.Model):
    feira = models.ForeignKey(Feira, on_delete=models.CASCADE, related_name='chunks_manual')
    texto = models.TextField(verbose_name="Texto do Chunk")
    posicao = models.IntegerField(verbose_name="Posição no Documento")
    pagina = models.IntegerField(verbose_name="Número da Página", null=True, blank=True)
    
    # Removemos o campo embedding JSON pois agora usaremos o Pinecone
    pinecone_id = models.CharField(max_length=100, blank=True, null=True, verbose_name="ID no Pinecone")
    
    def __str__(self):
        return f"Chunk {self.posicao} - Feira {self.feira.nome}"
    
    class Meta:
        db_table = 'feira_manual_chunks'
        verbose_name = 'Chunk de Manual de Feira'
        verbose_name_plural = 'Chunks de Manuais de Feira'

class FeiraManualQA(models.Model):
    """
    Modelo para armazenar perguntas e respostas extraídas do manual da feira
    """
    feira = models.ForeignKey(Feira, on_delete=models.CASCADE, related_name='qa_pairs')
    question = models.TextField(verbose_name="Pergunta Principal")
    answer = models.TextField(verbose_name="Resposta")
    context = models.TextField(verbose_name="Contexto Original", help_text="Trecho do manual de onde a resposta foi extraída")
    similar_questions = models.JSONField(verbose_name="Perguntas Similares", default=list, blank=True)
    
    # Para tracking e análise
    chunk_id = models.CharField(max_length=100, null=True, blank=True, verbose_name="ID do Chunk de Origem")
    embedding_id = models.CharField(max_length=100, null=True, blank=True, verbose_name="ID do Embedding")
    score = models.FloatField(null=True, blank=True, verbose_name="Pontuação de Relevância")
    
    # Metadados
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"QA {self.id}: {self.question[:50]}..."
    
    class Meta:
        db_table = 'feira_manual_qa'
        verbose_name = 'Par Pergunta-Resposta'
        verbose_name_plural = 'Pares Pergunta-Resposta'
        ordering = ['-created_at']


# Parâmetros Banco Vetorial e Agentes

class ParametroIndexacao(models.Model):
    nome = models.CharField(max_length=100, unique=True, verbose_name="Nome do Parâmetro")
    descricao = models.TextField(blank=True, null=True, verbose_name="Descrição")
    valor = models.CharField(max_length=255, verbose_name="Valor")
    tipo = models.CharField(
        max_length=20,
        choices=[
            ('int', 'Inteiro'),
            ('float', 'Decimal'),
            ('str', 'Texto'),
            ('bool', 'Booleano')
        ],
        default='str',
        verbose_name="Tipo de Valor"
    )
    categoria = models.CharField(
        max_length=50,
        choices=[
            ('chunk', 'Chunking'),
            ('embedding', 'Embedding'),
            ('connection', 'Connection'),
            ('search', 'Search'),
            ('qa', 'Q&A')
        ],
        default='chunk',
        verbose_name="Categoria"
    )
    
    def __str__(self):
        return f"{self.nome} ({self.get_categoria_display()})"
    
    def valor_convertido(self):
        """Converte o valor para o tipo apropriado"""
        if self.tipo == 'int':
            return int(self.valor)
        elif self.tipo == 'float':
            return float(self.valor)
        elif self.tipo == 'bool':
            return self.valor.lower() in ('true', 'sim', 's', 'yes', 'y', '1')
        else:
            return self.valor
    
    class Meta:
        db_table = 'parametros_indexacao'
        verbose_name = 'Parâmetro do Banco Vetorial'
        verbose_name_plural = 'Parâmetros do Banco Vetorial'
class Agente(models.Model):
    nome = models.CharField(max_length=100, unique=True, verbose_name="Nome do Agente")
    descricao = models.TextField(blank=True, null=True, verbose_name="Descrição")
    llm_provider = models.CharField(
        max_length=50,
        verbose_name="Provedor LLM",
        help_text="Provedor do modelo de linguagem (ex: OpenAI, Anthropic)"
    )
    llm_model = models.CharField(
        max_length=100,
        verbose_name="Modelo LLM",
        help_text="Nome do modelo específico a ser usado"
    )
    llm_temperature = models.FloatField(
        default=0.7,
        verbose_name="Temperatura",
        help_text="Temperatura para geração de texto (0.0 - 1.0)"
    )
    llm_system_prompt = models.TextField(
        verbose_name="Prompt do Sistema",
        help_text="Prompt base que define o comportamento do agente"
    )
    task_instructions = models.TextField(
        blank=True, 
        null=True,
        verbose_name="Instruções de Tarefa",
        help_text="Instruções específicas para execução de tarefas pelo agente"
    )
    ativo = models.BooleanField(default=True, verbose_name="Ativo")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Atualizado em")
    
    def __str__(self):
        return self.nome
    
    class Meta:
        db_table = 'agentes'
        verbose_name = 'Agente'
        verbose_name_plural = 'Agentes'