from django.db import models
from django.contrib.auth.models import User

class PerfilUsuario(models.Model):
    NIVEL_CHOICES = [
        ('admin', 'Admin'),
        ('gestor', 'Gestor'),
        ('projetista', 'Projetista'),
        ('cliente', 'Cliente'),
    ]
    
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil')
    empresa = models.ForeignKey('core.Empresa', on_delete=models.CASCADE, null=True, blank=True)
    nivel = models.CharField(max_length=20, choices=NIVEL_CHOICES, default='cliente')
    telefone = models.CharField(max_length=20, blank=True, null=True)
    foto_perfil = models.CharField(max_length=500, blank=True, null=True)  # Caminho para o MinIO
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'perfis_usuarios'
        verbose_name = 'Perfil de Usuário'
        verbose_name_plural = 'Perfis de Usuários'
    
    def __str__(self):
        return f"{self.usuario.username} - {self.get_nivel_display()}"