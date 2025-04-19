from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)

class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
    
    def ready(self):
        """
        Configuração e inicialização na inicialização do aplicativo
        """
        # Evitar execução durante operações de migração
        import sys
        if 'migrate' not in sys.argv and 'makemigrations' not in sys.argv:
            try:
                # Configurar logging otimizado para produção
                from core.utils.log_config import reduce_log_verbosity
                
                # Verificar se estamos em modo de produção
                from django.conf import settings
                if not settings.DEBUG:
                    logger.info("Configurando logs otimizados para produção")
                    reduce_log_verbosity()
                else:
                    logger.info("Mantendo logs de desenvolvimento (modo DEBUG ativo)")
                    
                logger.info("Aplicativo Core inicializado com sucesso")
            except Exception as e:
                logger.error(f"Erro ao configurar logs: {str(e)}")