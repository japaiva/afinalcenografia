#core/models.py

from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from django.conf import settings
from core.storage import MinioStorage
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid
import os

class Feira(models.Model):
    # Campos gerais e identificação
    id = models.AutoField(primary_key=True)
    nome = models.CharField(max_length=200)
    descricao = models.TextField(blank=True, null=True, verbose_name="Descrição")
    local = models.TextField()
    data_horario = models.TextField()
    cidade = models.CharField(max_length=100)
    estado = models.CharField(max_length=2)
    data_inicio = models.DateField()
    data_fim = models.DateField()
    ativa = models.BooleanField(default=True)
    website = models.URLField(blank=True, null=True, verbose_name="Website")
    
    # Campos de informações adicionais sobre o evento
    publico_alvo = models.CharField(max_length=200, blank=True, null=True, verbose_name="Público-alvo")
    eventos_simultaneos = models.CharField(max_length=200, blank=True, null=True, verbose_name="Eventos Simultâneos")
    promotora = models.CharField(max_length=200, blank=True, null=True)
    
    # Bloco Montagem e Desmontagem
    periodo_montagem = models.TextField(blank=True, null=True, verbose_name="Período Montagem")
    portao_acesso = models.CharField(max_length=200, blank=True, null=True, verbose_name="Portão de Acesso")
    periodo_desmontagem = models.TextField(blank=True, null=True, verbose_name="Período Desmontagem")
    
    # Bloco Normas Técnicas
    altura_estande = models.TextField(blank=True, null=True, verbose_name="Altura Estande")
    palcos = models.TextField(blank=True, null=True)
    piso_elevado = models.TextField(blank=True, null=True, verbose_name="Piso Elevado")
    mezanino = models.TextField(blank=True, null=True)
    iluminacao = models.TextField(blank=True, null=True, verbose_name="Iluminação")
    materiais_permitidos_proibidos = models.TextField(blank=True, null=True, verbose_name="Materiais Permitidos e Proibidos")
    visibilidade_obrigatoria = models.TextField(blank=True, null=True, verbose_name="Visibilidade Obrigatória")
    paredes_vidro = models.TextField(blank=True, null=True, verbose_name="Paredes de Vidro")
    estrutura_aerea = models.TextField(blank=True, null=True, verbose_name="Estrutura Aérea")
    
    # Bloco Credenciamento
    documentos = models.TextField(blank=True, null=True, verbose_name="Documentos")
    credenciamento = models.TextField(blank=True, null=True)
    
    # Arquivo do manual
    def manual_upload_path(instance, filename):
        # Gerar caminho para o arquivo com UUID para evitar colisões
        ext = filename.split('.')[-1]
        filename = f"{uuid.uuid4()}.{ext}"
        return os.path.join('manuais', filename)
    
    manual = models.FileField(upload_to=manual_upload_path, blank=True, null=True)
    
    # Campos de controle de processamento
    namespace_base = models.CharField(max_length=100, blank=True, null=True)
    chunks_processados = models.BooleanField(default=False)
    chunks_processamento_status = models.CharField(max_length=20, default='pendente')
    chunks_progresso = models.IntegerField(default=0)
    chunks_total = models.IntegerField(default=0)
    total_paginas = models.IntegerField(default=0)
    mensagem_erro = models.TextField(blank=True, null=True)
    
    # Campos de controle para QA
    qa_processado = models.BooleanField(default=False)
    qa_processamento_status = models.CharField(max_length=20, default='pendente')
    qa_progresso = models.IntegerField(default=0)
    qa_total = models.IntegerField(default=0)
    qa_mensagem_erro = models.TextField(blank=True, null=True)
    
    # Controle de alterações
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.nome} ({self.cidade}/{self.estado})"

    def get_namespace_base(self):
        """Retorna o namespace base, criando se não existir"""
        if not self.namespace_base:
            # Usando apenas o ID como base
            self.namespace_base = f"{self.id}"
            self.save(update_fields=['namespace_base'])
        return self.namespace_base

    def get_chunks_namespace(self):
        """Retorna o namespace para chunks"""
        return f"feira_chunks_{self.get_namespace_base()}"

    def get_qa_namespace(self):
        """Retorna o namespace para Q&A"""
        return f"feira_qa_{self.get_namespace_base()}"

    def reset_processamento(self):
        """Reseta os campos de processamento para iniciar novamente"""
        self.namespace_base = None
        self.chunks_processados = False
        self.chunks_processamento_status = 'pendente'
        self.chunks_progresso = 0
        self.chunks_total = 0
        self.qa_processado = False
        self.qa_processamento_status = 'pendente'
        self.qa_progresso = 0
        self.qa_total = 0
        self.mensagem_erro = None
        self.total_paginas = 0
        self.save()

    def atualizar_status_chunks(self, status, progresso=None, total=None):
        """Atualiza o status do processamento de chunks"""
        self.chunks_processamento_status = status
        if progresso is not None:
            self.chunks_progresso = progresso
        if total is not None:
            self.chunks_total = total
        if status == 'concluido':
            self.chunks_processados = True
        self.save()

    def atualizar_status_qa(self, status, progresso=None, total=None):
        """Atualiza o status do processamento de Q&A"""
        self.qa_processamento_status = status
        if progresso is not None:
            self.qa_progresso = progresso
        if total is not None:
            self.qa_total = total
        if status == 'concluido':
            self.qa_processado = True
        self.save()

    class Meta:
        db_table = 'feiras'
        verbose_name = 'Feira'
        verbose_name_plural = 'Feiras'
        ordering = ['-data_inicio']
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

# Adicionar ao modelo FeiraManualQA em core/models.py

class FeiraManualQA(models.Model):
    """
    Modelo para armazenar perguntas e respostas extraídas do manual da feira
    """
    feira = models.ForeignKey(Feira, on_delete=models.CASCADE, related_name='qa_pairs')
    question = models.TextField(verbose_name="Pergunta Principal")
    answer = models.TextField(verbose_name="Resposta")
    context = models.TextField(verbose_name="Contexto Original", help_text="Trecho do manual de onde a resposta foi extraída")
    similar_questions = models.JSONField(verbose_name="Perguntas Similares", default=list, blank=True)
    
    # Novo campo para associação com campo do cadastro
    campo_relacionado = models.CharField(max_length=100, verbose_name="Campo Relacionado", blank=True, null=True,
                                        help_text="Nome do campo do cadastro ao qual esta pergunta está relacionada")
    confianca_extracao = models.FloatField(default=0.0, verbose_name="Confiança da Extração", 
                                        help_text="Nível de confiança para extração automática (0.0 a 1.0)")
    
    # Campos existentes
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
class CampoPergunta(models.Model):
    """
    Define perguntas padrão para extrair informações de campos específicos.
    """
    CAMPOS_CHOICES = [
        ('nome', 'Nome da Feira'),
        ('descricao', 'Descrição do Evento'),
        ('website', 'Site da Feira'),
        ('local', 'Local/Endereço Completo'),
        ('data_horario', 'Data e Horário'),
        ('publico_alvo', 'Público-alvo'),
        ('eventos_simultaneos', 'Eventos Simultâneos'),
        ('promotora', 'Promotora/Organizadora'),
        ('periodo_montagem', 'Período Montagem'),
        ('portao_acesso', 'Portão de Acesso'),
        ('periodo_desmontagem', 'Período Desmontagem'),
        ('altura_estande', 'Altura Estande'),
        ('palcos', 'Regras para Palcos'),
        ('piso_elevado', 'Regras para Piso Elevado'),
        ('mezanino', 'Regras para Mezanino'),
        ('iluminacao', 'Regras para Iluminação'),
        ('materiais_permitidos_proibidos', 'Materiais Permitidos/Proibidos'),
        ('visibilidade_obrigatoria', 'Visibilidade Obrigatória'),
        ('paredes_vidro', 'Paredes de Vidro'),
        ('estrutura_aerea', 'Estrutura Aérea'),
        ('documentos', 'Documentos para Credenciamento'),
        ('credenciamento', 'Datas Credenciamento'),
    ]
    
    campo = models.CharField(max_length=100, choices=CAMPOS_CHOICES, verbose_name="Campo de Cadastro")
    pergunta = models.TextField(verbose_name="Pergunta")
    ativa = models.BooleanField(default=True, verbose_name="Ativa")
    prioridade = models.IntegerField(default=1, verbose_name="Prioridade", 
                                     help_text="Maior valor = maior prioridade")
    
    def __str__(self):
        return f"{self.get_campo_display()}: {self.pergunta[:50]}..."
    
    class Meta:
        db_table = 'campo_perguntas'
        verbose_name = 'Pergunta para Campo'
        verbose_name_plural = 'Perguntas para Campos'
        ordering = ['campo', '-prioridade']