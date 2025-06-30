#core/models.py

from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from django.conf import settings
from core.storage import MinioStorage
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid
import os
import json

class Agente(models.Model):
    """
    Modelo para agentes individuais (podem ser usados sozinhos ou em crews)
    """
    TIPO_AGENTE_CHOICES = [
        ('individual', 'Agente Individual'),
        ('crew_member', 'Membro de Crew'),
    ]
    
    nome = models.CharField(max_length=200, help_text="Nome descritivo do agente")
    tipo = models.CharField(max_length=20, choices=TIPO_AGENTE_CHOICES, default='individual')
    descricao = models.TextField(blank=True, help_text="Descrição da função do agente")
    
    # Configurações LLM
    llm_provider = models.CharField(max_length=50, default='openai')
    llm_model = models.CharField(max_length=100, help_text="Ex: gpt-4, claude-3-opus")
    llm_temperature = models.FloatField(
        default=0.3,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)]
    )
    
    # Prompts e instruções
    llm_system_prompt = models.TextField(help_text="Prompt base do agente")
    task_instructions = models.TextField(blank=True, help_text="Instruções específicas para tarefas")
    
    # CrewAI específico (para agentes que fazem parte de crews)
    crew_role = models.CharField(max_length=200, blank=True, help_text="Papel específico dentro do crew")
    crew_goal = models.TextField(blank=True, help_text="Objetivo específico dentro do crew")
    crew_backstory = models.TextField(blank=True, help_text="Background do agente no contexto do crew")
    
    # Status e configurações
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['nome']
        verbose_name = 'Agente'
        verbose_name_plural = 'Agentes'
    
    def __str__(self):
        return f"{self.nome} ({self.get_tipo_display()})"
    
    def is_crew_member(self):
        return self.tipo == 'crew_member'


class Crew(models.Model):
    """
    Modelo para crews (grupos de agentes trabalhando juntos)
    """
    PROCESSO_CHOICES = [
        ('sequential', 'Sequencial'),
        ('hierarchical', 'Hierárquico'),
    ]
    
    nome = models.CharField(max_length=200, help_text="Nome do crew")
    descricao = models.TextField(help_text="Descrição do que o crew faz")
    
    # Configurações do CrewAI
    processo = models.CharField(max_length=20, choices=PROCESSO_CHOICES, default='sequential')
    verbose = models.BooleanField(default=True, help_text="Logs detalhados durante execução")
    memory = models.BooleanField(default=True, help_text="Usar memória entre execuções")
    
    # Manager (para processo hierárquico)
    manager_llm_provider = models.CharField(max_length=50, default='openai', blank=True)
    manager_llm_model = models.CharField(max_length=100, blank=True, help_text="Modelo para o manager")
    manager_llm_temperature = models.FloatField(
        default=0.2,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        blank=True, null=True
    )
    
    # Status
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['nome']
        verbose_name = 'Crew'
        verbose_name_plural = 'Crews'
    
    def __str__(self):
        return self.nome


class CrewMembro(models.Model):
    """
    Relacionamento entre Crew e Agentes com configurações específicas
    """
    crew = models.ForeignKey(Crew, on_delete=models.CASCADE, related_name='membros')
    agente = models.ForeignKey(Agente, on_delete=models.CASCADE, related_name='crews')
    
    # Configurações específicas dentro do crew
    ordem_execucao = models.PositiveIntegerField(default=1, help_text="Ordem de execução no crew")
    pode_delegar = models.BooleanField(default=False, help_text="Pode delegar tarefas para outros agentes")
    max_iter = models.PositiveIntegerField(default=15, help_text="Máximo de iterações para este agente")
    max_execution_time = models.PositiveIntegerField(default=300, help_text="Tempo máximo de execução em segundos")
    
    # Status
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['crew', 'ordem_execucao']
        unique_together = ['crew', 'agente']
        verbose_name = 'Membro do Crew'
        verbose_name_plural = 'Membros do Crew'
    
    def __str__(self):
        return f"{self.crew.nome} → {self.agente.nome} (#{self.ordem_execucao})"


class CrewTask(models.Model):
    """
    Tarefas específicas dentro de um Crew
    """
    crew = models.ForeignKey(Crew, on_delete=models.CASCADE, related_name='tasks')
    agente_responsavel = models.ForeignKey(Agente, on_delete=models.CASCADE, related_name='tasks_responsavel')
    
    nome = models.CharField(max_length=200, help_text="Nome da tarefa")
    descricao = models.TextField(help_text="Descrição detalhada da tarefa")
    expected_output = models.TextField(help_text="Descrição do output esperado")
    
    # Configurações da tarefa
    ordem_execucao = models.PositiveIntegerField(default=1)
    async_execution = models.BooleanField(default=False, help_text="Execução assíncrona")
    
    # Dependências (tarefas que devem ser executadas antes)
    dependencias = models.ManyToManyField('self', blank=True, symmetrical=False, related_name='dependentes')
    
    # Context e ferramentas
    context_template = models.TextField(blank=True, help_text="Template para contexto da tarefa")
    tools_config = models.JSONField(default=dict, blank=True, help_text="Configuração de ferramentas específicas")
    
    # Status
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['crew', 'ordem_execucao']
        verbose_name = 'Tarefa do Crew'
        verbose_name_plural = 'Tarefas do Crew'
    
    def __str__(self):
        return f"{self.crew.nome} → {self.nome} ({self.agente_responsavel.nome})"


class CrewExecucao(models.Model):
    """
    Log de execuções de crews
    """
    STATUS_CHOICES = [
        ('running', 'Executando'),
        ('completed', 'Concluído'),
        ('failed', 'Falhou'),
        ('timeout', 'Timeout'),
    ]
    
    crew = models.ForeignKey(Crew, on_delete=models.CASCADE, related_name='execucoes')
    
    # Identificação da execução
    projeto_id = models.PositiveIntegerField(null=True, blank=True)
    briefing_id = models.PositiveIntegerField(null=True, blank=True)
    usuario_solicitante = models.ForeignKey('Usuario', on_delete=models.SET_NULL, null=True, blank=True)
    
    # Status e controle
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='running')
    iniciado_em = models.DateTimeField(auto_now_add=True)
    finalizado_em = models.DateTimeField(null=True, blank=True)
    tempo_execucao = models.PositiveIntegerField(null=True, blank=True, help_text="Tempo em segundos")
    
    # Input e output
    input_data = models.JSONField(help_text="Dados de entrada para o crew")
    output_data = models.JSONField(default=dict, blank=True, help_text="Resultado da execução")
    
    # Logs e debugging
    logs_execucao = models.TextField(blank=True, help_text="Logs detalhados da execução")
    erro_detalhado = models.TextField(blank=True, help_text="Detalhes do erro se houver")
    
    # Métricas
    tokens_utilizados = models.PositiveIntegerField(default=0)
    custo_estimado = models.DecimalField(max_digits=10, decimal_places=4, default=0)
    
    class Meta:
        ordering = ['-iniciado_em']
        verbose_name = 'Execução de Crew'
        verbose_name_plural = 'Execuções de Crew'
    
    def __str__(self):
        return f"{self.crew.nome} - {self.get_status_display()} ({self.iniciado_em.strftime('%d/%m/%Y %H:%M')})"

def manual_upload_path(instance, filename):
    """
    Gera um caminho para o arquivo do manual com UUID para evitar colisões
    """
    ext = filename.split('.')[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    return os.path.join('manuais', filename)
    

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
    
    # IMPORTANTE: Manter como método estático dentro da classe para compatibilidade com migrações
    # Arquivo do manual - CORRIGIDO: usando MinioStorage explicitamente
    manual = models.FileField(
        upload_to=manual_upload_path, 
        storage=MinioStorage(),  # Usando explicitamente o MinioStorage
        blank=True, 
        null=True
    )
    
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
    
    # CORRIGIDO: Método get_manual_url movido da classe Usuario para a classe Feira
    def get_manual_url(self):
        """
        Retorna a URL correta para o manual da feira.
        """
        if not self.manual:
            return None
            
        # Obter a URL direta do MinIO
        from django.conf import settings
        return f"{settings.AWS_S3_ENDPOINT_URL}/{settings.AWS_STORAGE_BUCKET_NAME}/{self.manual.name}"

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
    
    # NOVO CAMPO ADICIONADO
    descricao = models.TextField(
        blank=True, null=True, 
        verbose_name="Descrição da Empresa",
        help_text="Descrição da empresa que pode ser editada por projeto"
    )
    # NOVO CAMPO: Razão Social
    razao_social = models.CharField(max_length=200, blank=True, null=True, verbose_name="Razão Social")
    
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
    
    SEXO_CHOICES = [
        ('M', 'Masculino'),
        ('F', 'Feminino'),
        ('O', 'Outro/Não Informar'),
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
    # NOVO CAMPO: Sexo
    sexo = models.CharField(max_length=1, choices=SEXO_CHOICES, blank=True, null=True, verbose_name="Sexo")
    

        # No modelo Feira (models.py)

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