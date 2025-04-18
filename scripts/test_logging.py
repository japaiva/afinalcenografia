"""
Script de teste para verificar se o logging está funcionando corretamente
Salve este arquivo na raiz do seu projeto e execute:
python test_logging.py
"""

import os
import logging
import django
import sys

# Configurar ambiente Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'afinal_cenografia.settings')
django.setup()

# Verificar diretório de logs
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
logs_dir = os.path.join(BASE_DIR, 'logs')
print(f"Verificando diretório de logs: {logs_dir}")

if os.path.exists(logs_dir):
    print(f"✓ Diretório de logs existe: {logs_dir}")
    print(f"  Permissões: {oct(os.stat(logs_dir).st_mode)[-3:]}")
    files = os.listdir(logs_dir)
    print(f"  Arquivos existentes: {files}")
else:
    print(f"✗ Diretório de logs NÃO existe: {logs_dir}")
    try:
        os.makedirs(logs_dir, exist_ok=True)
        print(f"  Diretório criado manualmente: {logs_dir}")
    except Exception as e:
        print(f"  ERRO ao criar diretório: {str(e)}")

# Tentar escrever logs diretamente
print("\nTentando escrever logs diretamente nos arquivos...")

try:
    debug_path = os.path.join(logs_dir, 'debug.log')
    with open(debug_path, 'a') as f:
        f.write('Teste de escrita manual - debug.log\n')
    print(f"✓ Escrita manual em debug.log bem-sucedida: {debug_path}")
except Exception as e:
    print(f"✗ ERRO ao escrever manualmente em debug.log: {str(e)}")

try:
    diagnostic_path = os.path.join(logs_dir, 'diagnostic.log')
    with open(diagnostic_path, 'a') as f:
        f.write('Teste de escrita manual - diagnostic.log\n')
    print(f"✓ Escrita manual em diagnostic.log bem-sucedida: {diagnostic_path}")
except Exception as e:
    print(f"✗ ERRO ao escrever manualmente em diagnostic.log: {str(e)}")

# Testar criação de logs via logging
print("\nTentando criar logs via sistema logging...")

# Verificar configuração do logging
print("Configurações de logging registradas:")
from django.conf import settings
if hasattr(settings, 'LOGGING'):
    handlers = settings.LOGGING.get('handlers', {})
    for name, config in handlers.items():
        if 'filename' in config:
            print(f"  Handler '{name}': {config['filename']}")
            # Verificar se o diretório existe
            log_dir = os.path.dirname(config['filename'])
            if not os.path.exists(log_dir):
                print(f"    ✗ Diretório para o arquivo não existe: {log_dir}")
                try:
                    os.makedirs(log_dir, exist_ok=True)
                    print(f"    Diretório criado: {log_dir}")
                except Exception as e:
                    print(f"    ERRO ao criar diretório: {str(e)}")
else:
    print("  Configurações de logging não encontradas!")

# Criar logs para testar
loggers_to_test = [
    'django',
    'django.db.backends',
    'core',
    'core.utils.pinecone_utils',
    'core.services.rag',
    'core.services.rag.embedding_service',
    'core.services.rag.retrieval_service',
    'core.services.rag.qa_service',
]

print("\nTestando loggers configurados:")
for logger_name in loggers_to_test:
    try:
        logger = logging.getLogger(logger_name)
        logger.info(f"TESTE_LOG: Mensagem de teste do logger '{logger_name}'")
        logger.debug(f"TESTE_LOG: Mensagem de debug do logger '{logger_name}'")
        logger.warning(f"TESTE_LOG: Mensagem de warning do logger '{logger_name}'")
        print(f"✓ Log enviado para '{logger_name}'")
    except Exception as e:
        print(f"✗ ERRO ao enviar log para '{logger_name}': {str(e)}")

# Verificar se os arquivos foram criados e contêm os logs
print("\nVerificando se os logs foram gravados...")

log_files = [
    os.path.join(logs_dir, 'debug.log'),
    os.path.join(logs_dir, 'diagnostic.log')
]

for log_file in log_files:
    if os.path.exists(log_file):
        print(f"✓ Arquivo de log existe: {log_file}")
        
        # Verificar tamanho
        size = os.path.getsize(log_file)
        print(f"  Tamanho: {size} bytes")
        
        # Mostrar últimas linhas
        try:
            with open(log_file, 'r') as f:
                lines = f.readlines()
                last_lines = lines[-10:] if len(lines) >= 10 else lines
                print(f"  Últimas {len(last_lines)} linhas:")
                for line in last_lines:
                    print(f"    {line.strip()}")
        except Exception as e:
            print(f"  ERRO ao ler arquivo: {str(e)}")
    else:
        print(f"✗ Arquivo de log NÃO existe: {log_file}")

print("\nTeste de logging concluído!")