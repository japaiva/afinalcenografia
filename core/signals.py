from django.db.models.signals import post_save
from django.dispatch import receiver
from core.models import Usuario, PerfilUsuario
import logging

logger = logging.getLogger(__name__)

@receiver(post_save, sender=Usuario)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Cria automaticamente um PerfilUsuario quando um Usuario é criado
    """
    if created:
        try:
            # Criar perfil com os mesmos dados do usuário
            PerfilUsuario.objects.create(
                usuario=instance,
                empresa=instance.empresa,
                nivel=instance.nivel,
                telefone=instance.telefone
            )
            logger.info(f"Perfil criado para usuário {instance.username}")
        except Exception as e:
            logger.error(f"Erro ao criar perfil para {instance.username}: {str(e)}")

@receiver(post_save, sender=Usuario)
def save_user_profile(sender, instance, **kwargs):
    """
    Atualiza o PerfilUsuario quando o Usuario é atualizado
    """
    # Apenas atualiza se o perfil já existe
    if hasattr(instance, 'perfil'):
        try:
            instance.perfil.empresa = instance.empresa
            instance.perfil.nivel = instance.nivel
            instance.perfil.telefone = instance.telefone
            instance.perfil.save()
            logger.info(f"Perfil atualizado para usuário {instance.username}")
        except Exception as e:
            logger.error(f"Erro ao atualizar perfil para {instance.username}: {str(e)}")