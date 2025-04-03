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