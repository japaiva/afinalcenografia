"""
Configurações e utilitários de logging para o projeto
"""
import logging
import functools
import time

# Configuração dos loggers de serviços frequentemente utilizados
service_loggers = {
    'rag': logging.getLogger('core.services.rag'),
    'embedding': logging.getLogger('core.services.rag.embedding_service'),
    'qa': logging.getLogger('core.services.rag.qa_service'),
    'retrieval': logging.getLogger('core.services.rag.retrieval_service'),
    'vectordb': logging.getLogger('core.services.rag.vector_db_service'),
}

def silent_logger(name):
    """
    Retorna um logger configurado para nível WARNING,
    reduzindo a saída de logs para esse módulo.
    
    Args:
        name: Nome do logger
    
    Returns:
        Logger configurado para nível WARNING
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.WARNING)
    return logger

def timed_function(log_level=logging.DEBUG):
    """
    Decorador para medir e logar o tempo de execução de uma função
    
    Args:
        log_level: Nível de log para a mensagem do tempo (padrão: DEBUG)
    
    Returns:
        Função decorada que registra o tempo de execução
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            logger = logging.getLogger(func.__module__)
            
            start_time = time.time()
            result = func(*args, **kwargs)
            end_time = time.time()
            elapsed_time = end_time - start_time
            
            logger.log(
                log_level,
                f"Função {func.__name__} executada em {elapsed_time:.3f} segundos"
            )
            
            return result
        return wrapper
    return decorator

def configure_service_loggers(level=logging.INFO):
    """
    Configura os loggers de serviço para um determinado nível.
    Útil para reduzir temporariamente o nível de log durante desenvolvimento.
    
    Args:
        level: Nível de log a ser configurado (padrão: INFO)
    """
    for name, logger in service_loggers.items():
        logger.setLevel(level)
        logger.info(f"Logger para serviço '{name}' configurado para nível {level}")

def reduce_log_verbosity():
    """
    Reduz a verbosidade dos logs para serviços específicos,
    para melhorar o desempenho em produção.
    """
    # Configurar loggers mais verbosos para WARNING
    high_volume_loggers = [
        'core.services.rag.embedding_service',
        'core.services.rag.qa_service',
        'core.utils.pinecone_utils'
    ]
    
    for name in high_volume_loggers:
        logger = logging.getLogger(name)
        logger.setLevel(logging.WARNING)
    
    # Configurar nível INFO para loggers principais
    main_loggers = [
        'core.services',
        'gestor.views',
        'cliente.views'
    ]
    
    for name in main_loggers:
        logger = logging.getLogger(name)
        logger.setLevel(logging.INFO)