import os
import django
import sys

# Configurar o ambiente Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'afinal_cenografia.settings')
django.setup()

from django.contrib.auth.models import User
from accounts.models import PerfilUsuario
from core.models import Empresa

def criar_superuser():
    # Criar empresa para o admin
    empresa, created = Empresa.objects.get_or_create(
        nome='Afinal Cenografia',
        defaults={
            'cnpj': '12.345.678/0001-90',
            'email': 'admin@afinalcenografia.com.br',
            'ativa': True
        }
    )
    
    # Verificar se já existe um superusuário
    if User.objects.filter(is_superuser=True).exists():
        print("Um superusuário já existe.")
        return
    
    # Criar superusuário
    superuser = User.objects.create_superuser(
        username='admin',
        email='admin@afinalcenografia.com.br',
        password='Sps2025pos'
    )
    
    # Criar perfil para o superusuário
    PerfilUsuario.objects.create(
        usuario=superuser,
        empresa=empresa,
        nivel='admin'
    )
    
    print("Superusuário criado com sucesso!")

if __name__ == "__main__":
    criar_superuser()