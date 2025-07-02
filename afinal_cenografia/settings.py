# settings.py - INTEGRADO COM CREWAI PIPELINE

from pathlib import Path
import os
import dj_database_url
from dotenv import load_dotenv
import sys

# Debug para identificar problemas de logging
print("=== INICIANDO CONFIGURAÇÃO DE LOGGING ===")
print(f"Diretório de execução atual: {os.getcwd()}")

# Carrega variáveis do arquivo .env
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
print(f"BASE_DIR: {BASE_DIR}")

# Criar diretório de logs com notificação
logs_dir = os.path.join(BASE_DIR, 'logs')
print(f"Tentando criar diretório de logs em: {logs_dir}")
try:
    os.makedirs(logs_dir, exist_ok=True)
    print(f"✓ Diretório de logs criado/verificado com sucesso: {logs_dir}")
    print(f"  Permissões do diretório: {oct(os.stat(logs_dir).st_mode)[-3:]}")
except Exception as e:
    print(f"✗ ERRO ao criar diretório de logs: {str(e)}")

# Tentar criar arquivo de teste para verificar permissões
try:
    test_log_path = os.path.join(logs_dir, 'test_write.log')
    print(f"Tentando escrever arquivo de teste em: {test_log_path}")
    with open(test_log_path, 'w') as f:
        f.write('Teste de escrita de log - OK')
    print(f"✓ Teste de escrita no diretório de logs bem-sucedido")
except Exception as e:
    print(f"✗ ERRO ao escrever arquivo de teste: {str(e)}")

# Security
SECRET_KEY = os.getenv('SECRET_KEY')
DEBUG = os.getenv('DEBUG', 'False') == 'True'
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', '').split(',')

# Configuração MinIO (via django-storages)
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
AWS_STORAGE_BUCKET_NAME = os.getenv('AWS_STORAGE_BUCKET_NAME')
AWS_S3_ENDPOINT_URL = os.getenv('AWS_S3_ENDPOINT_URL')
AWS_S3_OBJECT_PARAMETERS = {'CacheControl': 'max-age=86400'}
AWS_DEFAULT_ACL = 'public-read'
AWS_QUERYSTRING_AUTH = False
AWS_S3_FILE_OVERWRITE = False
AWS_S3_SIGNATURE_VERSION = 's3v4'
AWS_S3_REGION_NAME = 'us-east-1'
AWS_S3_ADDRESSING_STYLE = 'path'

# Usa MinIO como armazenamento padrão
DEFAULT_FILE_STORAGE = 'core.storage.MinioStorage'
MEDIA_URL = '/media/'

# Static Files
STATIC_URL = '/static/'
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# ============================================================================
# API KEYS - MANTIDAS + CREWAI
# ============================================================================
PINECONE_API_KEY = os.environ.get('PINECONE_API_KEY', '')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
GROQ_API_KEY = os.getenv('GROQ_API_KEY', '')
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY', '')

# ============================================================================
# CONFIGURAÇÕES CREWAI PIPELINE
# ============================================================================

# CONTROLE DE FASES
# False = FASE 1 (simulação, não gasta tokens)
# True = FASE 2/3 (execução real com LLM)
CREWAI_USAR_EXECUCAO_REAL = os.getenv('CREWAI_USAR_EXECUCAO_REAL', 'True').lower() == 'true'

# PIPELINE COMPLETO
# False = Apenas 1 agente (para testes)
# True = Pipeline com 4 agentes (para produção)
CREWAI_USAR_PIPELINE_COMPLETO = os.getenv('CREWAI_USAR_PIPELINE_COMPLETO', 'True').lower() == 'true'

# CONFIGURAÇÕES DE PERFORMANCE
CREWAI_CACHE_TIMEOUT = int(os.getenv('CREWAI_CACHE_TIMEOUT', '7200'))  # 2 horas
CREWAI_AGENT_TIMEOUT = int(os.getenv('CREWAI_AGENT_TIMEOUT', '180'))  # 3 minutos
CREWAI_PIPELINE_TIMEOUT = int(os.getenv('CREWAI_PIPELINE_TIMEOUT', '600'))  # 10 minutos
CREWAI_MAX_ITERATIONS = int(os.getenv('CREWAI_MAX_ITERATIONS', '3'))
CREWAI_MAX_TOKENS = int(os.getenv('CREWAI_MAX_TOKENS', '2000'))
CREWAI_DEFAULT_TEMPERATURE = float(os.getenv('CREWAI_DEFAULT_TEMPERATURE', '0.1'))

# LOGS E DEBUG
CREWAI_VERBOSE_LOGS = os.getenv('CREWAI_VERBOSE_LOGS', 'True').lower() == 'true'
CREWAI_SAVE_EXECUTION_LOGS = os.getenv('CREWAI_SAVE_EXECUTION_LOGS', 'True').lower() == 'true'
CREWAI_LOG_POLLING_INTERVAL = int(os.getenv('CREWAI_LOG_POLLING_INTERVAL', '2000'))  # 2 segundos

print(f"🤖 CREWAI CONFIG:")
print(f"  - Execução Real: {CREWAI_USAR_EXECUCAO_REAL}")
print(f"  - Pipeline Completo: {CREWAI_USAR_PIPELINE_COMPLETO}")
print(f"  - OpenAI Key: {'✅ Configurada' if OPENAI_API_KEY else '❌ Não configurada'}")
print(f"  - Anthropic Key: {'✅ Configurada' if ANTHROPIC_API_KEY else '❌ Não configurada'}")

# Aplicações instaladas
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'storages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'django_extensions',
    'rest_framework',
    'core',
    'projetos',
    'storage',
    'cliente',
    'projetista',
    'gestor',
    'api',
]

# Middleware
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'afinal_cenografia.middleware.MensagensNotificacaoMiddleware',
    'afinal_cenografia.middleware.AppContextMiddleware',  
]

ROOT_URLCONF = 'afinal_cenografia.urls'

# Templates
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'afinal_cenografia.wsgi.application'

# Database
DATABASES = {
    'default': dj_database_url.config(
        default=os.getenv('DATABASE_URL'),
        conn_max_age=600,
        conn_health_checks=True,
    )
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internationalization
LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Sao_Paulo'
USE_I18N = True
USE_TZ = True

# Auth settings
AUTH_USER_MODEL = 'core.Usuario'
LOGIN_REDIRECT_URL = '/'
LOGIN_URL = '/login/'
LOGOUT_REDIRECT_URL = '/login/'

# Mensagens
MESSAGE_STORAGE = 'django.contrib.messages.storage.session.SessionStorage'

# Segurança
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SECURE = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
CSRF_TRUSTED_ORIGINS = [
    'https://afinal.spsystems.pro',
    'https://afinal-ia.com.br'
]

# Default primary key
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ============================================================================
# CACHE PARA CREWAI LOGS (INTEGRADO)
# ============================================================================

# Cache para logs em tempo real (usando memória local se não tiver Redis)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'crewai-logs-cache',
        'TIMEOUT': CREWAI_CACHE_TIMEOUT,
        'OPTIONS': {
            'MAX_ENTRIES': 2000,  # Aumentado para pipeline
        }
    }
}

# Se tiver Redis disponível, pode usar:
# CACHES = {
#     'default': {
#         'BACKEND': 'django.core.cache.backends.redis.RedisCache',
#         'LOCATION': os.getenv('REDIS_URL', 'redis://127.0.0.1:6379/1'),
#         'OPTIONS': {
#             'CLIENT_CLASS': 'django_redis.client.DefaultClient',
#         },
#         'KEY_PREFIX': 'afinal_crewai',
#         'TIMEOUT': CREWAI_CACHE_TIMEOUT,
#     }
# }

# ============================================================================
# LOGGING INTEGRADO COM CREWAI
# ============================================================================

# Verifica permissões no diretório de logs
LOG_DEBUG_PATH = os.path.join(logs_dir, 'debug.log')
LOG_DIAGNOSTIC_PATH = os.path.join(logs_dir, 'diagnostic.log')
LOG_CREWAI_PATH = os.path.join(logs_dir, 'crewai.log')  # ← NOVO

print(f"Arquivos de log que serão usados:")
print(f" - Debug: {LOG_DEBUG_PATH}")
print(f" - Diagnostic: {LOG_DIAGNOSTIC_PATH}")
print(f" - CrewAI: {LOG_CREWAI_PATH}")

# Testa escrita no arquivo de log do CrewAI
try:
    with open(LOG_CREWAI_PATH, 'a') as f:
        f.write('Teste de inicialização - crewai.log\n')
    print(f"✓ Teste de escrita em crewai.log bem-sucedido")
except Exception as e:
    print(f"✗ ERRO ao escrever em crewai.log: {str(e)}")

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{levelname}] {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'diagnostic': {
            'format': '[{levelname}] {asctime} {message}',
            'style': '{',
        },
        'simple': {
            'format': '[{levelname}] {message}',
            'style': '{',
        },
        'crewai': {  # ← NOVO FORMATTER
            'format': '[CREWAI-{levelname}] {asctime} {name} {message}',
            'style': '{',
        },
    },
    'filters': {
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue',
        },
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'diagnostic',
            'stream': sys.stdout,
        },
        'file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': LOG_DEBUG_PATH,
            'formatter': 'diagnostic',
        },
        'diagnostic_file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': LOG_DIAGNOSTIC_PATH,
            'formatter': 'diagnostic',
        },
        'crewai_file': {  # ← NOVO HANDLER
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': LOG_CREWAI_PATH,
            'formatter': 'crewai',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': True,
        },
        'django.db.backends': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'core': {
            'handlers': ['console', 'diagnostic_file'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'core.utils.pinecone_utils': {
            'handlers': ['console', 'diagnostic_file'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'core.services.rag': {
            'handlers': ['console', 'diagnostic_file'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'core.services.rag.embedding_service': {
            'handlers': ['console', 'diagnostic_file'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'core.services.rag.retrieval_service': {
            'handlers': ['console', 'diagnostic_file'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'core.services.rag.qa_service': {
            'handlers': ['console', 'diagnostic_file'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'django.setup': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        },
        
        # ============================================================================
        # LOGGERS CREWAI (NOVOS)
        # ============================================================================
        'core.services.crewai_planta_service': {
            'handlers': ['console', 'crewai_file'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'core.services.crewai_planta_baixa_service': {  # Nome alternativo
            'handlers': ['console', 'crewai_file'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'projetista.views.planta_baixa': {
            'handlers': ['console', 'crewai_file'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'projetista.views': {
            'handlers': ['console', 'diagnostic_file'],
            'level': 'DEBUG',
            'propagate': False,
        },
        # Logger para capturar saída do CrewAI framework
        'crewai': {
            'handlers': ['console', 'crewai_file'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'langchain': {
            'handlers': ['console', 'crewai_file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

print("=== CONFIGURAÇÃO DE LOGGING CONCLUÍDA ===")

# Teste final do sistema de logging
import logging
logger = logging.getLogger('django.setup')
logger.info("Teste de log durante inicialização do Django")

# Teste específico do CrewAI
crewai_logger = logging.getLogger('core.services.crewai_planta_service')
crewai_logger.info("🤖 Sistema de logging do CrewAI configurado")


# ADICIONAR NO FINAL DO SEU settings.py EXISTENTE

# ============================================================================
# CONFIGURAÇÕES CREWAI PIPELINE - ADICIONAR ESTAS LINHAS
# ============================================================================

# CONTROLE DE FASES
CREWAI_USAR_EXECUCAO_REAL = os.getenv('CREWAI_USAR_EXECUCAO_REAL', 'True').lower() == 'true'
CREWAI_USAR_PIPELINE_COMPLETO = os.getenv('CREWAI_USAR_PIPELINE_COMPLETO', 'True').lower() == 'true'

# CONFIGURAÇÕES DE PERFORMANCE
CREWAI_CACHE_TIMEOUT = int(os.getenv('CREWAI_CACHE_TIMEOUT', '7200'))
CREWAI_AGENT_TIMEOUT = int(os.getenv('CREWAI_AGENT_TIMEOUT', '180'))
CREWAI_PIPELINE_TIMEOUT = int(os.getenv('CREWAI_PIPELINE_TIMEOUT', '600'))
CREWAI_MAX_ITERATIONS = int(os.getenv('CREWAI_MAX_ITERATIONS', '3'))
CREWAI_MAX_TOKENS = int(os.getenv('CREWAI_MAX_TOKENS', '2000'))
CREWAI_DEFAULT_TEMPERATURE = float(os.getenv('CREWAI_DEFAULT_TEMPERATURE', '0.1'))

# LOGS E DEBUG
CREWAI_VERBOSE_LOGS = os.getenv('CREWAI_VERBOSE_LOGS', 'True').lower() == 'true'
CREWAI_SAVE_EXECUTION_LOGS = os.getenv('CREWAI_SAVE_EXECUTION_LOGS', 'True').lower() == 'true'
CREWAI_LOG_POLLING_INTERVAL = int(os.getenv('CREWAI_LOG_POLLING_INTERVAL', '2000'))

# ATUALIZAR O CACHE EXISTENTE PARA SUPORTAR CREWAI
CACHES['default']['TIMEOUT'] = CREWAI_CACHE_TIMEOUT
CACHES['default']['OPTIONS']['MAX_ENTRIES'] = 2000

# ADICIONAR LOGGERS CREWAI AO LOGGING EXISTENTE
LOGGING['loggers']['core.services.crewai_planta_service'] = {
    'handlers': ['console', 'diagnostic_file'],
    'level': 'DEBUG',
    'propagate': False,
}

# Criar arquivo de log específico para CrewAI
LOG_CREWAI_PATH = os.path.join(logs_dir, 'crewai.log')

# Adicionar handler específico para CrewAI
LOGGING['handlers']['crewai_file'] = {
    'level': 'DEBUG',
    'class': 'logging.FileHandler',
    'filename': LOG_CREWAI_PATH,
    'formatter': 'diagnostic',
}

# Atualizar logger do CrewAI para usar o arquivo específico
LOGGING['loggers']['core.services.crewai_planta_service']['handlers'] = ['console', 'crewai_file']

# Adicionar outros loggers relacionados ao CrewAI
LOGGING['loggers']['projetista.views.planta_baixa'] = {
    'handlers': ['console', 'crewai_file'],
    'level': 'DEBUG',
    'propagate': False,
}

# Logger para capturar outputs do CrewAI framework
LOGGING['loggers']['crewai'] = {
    'handlers': ['console', 'crewai_file'],
    'level': 'DEBUG',
    'propagate': False,
}

LOGGING['loggers']['langchain'] = {
    'handlers': ['console', 'crewai_file'],
    'level': 'INFO',
    'propagate': False,
}

# Mensagens de inicialização
print("🤖 CREWAI PIPELINE CONFIGURADO:")
print(f"  - Execução Real: {CREWAI_USAR_EXECUCAO_REAL}")
print(f"  - Pipeline Completo: {CREWAI_USAR_PIPELINE_COMPLETO}")
print(f"  - Timeout Pipeline: {CREWAI_PIPELINE_TIMEOUT}s")
print(f"  - Log CrewAI: {LOG_CREWAI_PATH}")

# Testar log do CrewAI
try:
    with open(LOG_CREWAI_PATH, 'a') as f:
        f.write(f'CrewAI configurado - {os.getenv("CREWAI_USAR_PIPELINE_COMPLETO", "False")}\n')
    print("✅ Log do CrewAI testado com sucesso")
except Exception as e:
    print(f"⚠️ Aviso: {str(e)}")

print("🚀 PRONTO PARA USAR PIPELINE COM 4 AGENTES!")