# settings.py

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
AWS_S3_REGION_NAME = 'us-east-1'  # Região padrão para compatibilidade
AWS_S3_ADDRESSING_STYLE = 'path'  # Importante: usar 'path' em vez de 'virtual'

# Usa MinIO como armazenamento padrão
DEFAULT_FILE_STORAGE = 'core.storage.MinioStorage'
MEDIA_URL = '/media/'

# Static Files
STATIC_URL = '/static/'
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# API KEYS
PINECONE_API_KEY = os.environ.get('PINECONE_API_KEY', '')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
GROQ_API_KEY = os.getenv('GROQ_API_KEY', '')
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY', '')


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
CSRF_TRUSTED_ORIGINS = ['https://afinal.spsystems.pro']

# Default primary key
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Configurações de logging - Versão mais direta para encontrar problemas
print("Configurando sistema de logging...")

# Verifica permissões no diretório de logs
LOG_DEBUG_PATH = os.path.join(logs_dir, 'debug.log')
LOG_DIAGNOSTIC_PATH = os.path.join(logs_dir, 'diagnostic.log')

print(f"Arquivos de log que serão usados:")
print(f" - Debug: {LOG_DEBUG_PATH}")
print(f" - Diagnostic: {LOG_DIAGNOSTIC_PATH}")

# Tenta escrever nos arquivos de log diretamente para testar permissões
try:
    with open(LOG_DEBUG_PATH, 'a') as f:
        f.write('Teste de inicialização de log - debug.log\n')
    print(f"✓ Teste de escrita em debug.log bem-sucedido")
except Exception as e:
    print(f"✗ ERRO ao escrever em debug.log: {str(e)}")

try:
    with open(LOG_DIAGNOSTIC_PATH, 'a') as f:
        f.write('Teste de inicialização de log - diagnostic.log\n')
    print(f"✓ Teste de escrita em diagnostic.log bem-sucedido")
except Exception as e:
    print(f"✗ ERRO ao escrever em diagnostic.log: {str(e)}")

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
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],  # Adicionado 'file' para capturar logs do Django
            'level': 'INFO',
            'propagate': True,
        },
        'django.db.backends': {
            'handlers': ['console', 'file'],  # Adicionado 'file' para capturar logs do DB
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
        # Logger de diagnóstico para configuração
        'django.setup': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}

print("=== CONFIGURAÇÃO DE LOGGING CONCLUÍDA ===")

# Teste final do sistema de logging - Isso escreve no console e deve escrever no arquivo
import logging
logger = logging.getLogger('django.setup')
logger.info("Teste de log durante inicialização do Django")