"""
Exemplos de uso dos utilitários de logging e performance
"""
import logging
from core.utils.log_config import timed_function, silent_logger

logger = logging.getLogger(__name__)

# Exemplo de uso do decorador para medir tempo de execução
@timed_function(log_level=logging.INFO)
def processar_dados_complexos(data_id, **kwargs):
    """
    Exemplo de função que pode ser monitorada para desempenho
    """
    import time
    
    # Simula processamento
    logger.info(f"Iniciando processamento de dados {data_id}")
    
    # Simulação de processamento demorado
    time.sleep(0.5)
    
    logger.info(f"Processamento de dados {data_id} concluído")
    return {"status": "success", "data_id": data_id}

# Exemplo de função que usa logging otimizado
def processar_em_lote(items):
    """
    Exemplo de processamento em lote com logging otimizado
    """
    total = len(items)
    logger.info(f"Iniciando processamento de {total} itens")
    
    # Log apenas a cada 10% do progresso
    progress_step = max(1, total // 10)
    results = []
    
    for i, item in enumerate(items):
        # Log apenas a cada X% do progresso
        if i % progress_step == 0:
            logger.info(f"Progresso: {i}/{total} ({(i/total)*100:.1f}%)")
            
        try:
            # Processamento
            result = processar_dados_complexos(item)
            results.append(result)
        except Exception as e:
            logger.error(f"Erro ao processar item {item}: {str(e)}")
    
    # Log de sumário final
    logger.info(f"Processamento concluído: {len(results)} de {total} itens processados")
    return results