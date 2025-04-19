# Otimização de Logging no Projeto AFinal Cenografia

Este documento descreve as melhorias implementadas para reduzir o excesso de logs e melhorar o desempenho do sistema.

## Modificações Implementadas

### 1. Redução de Logs de Diagnóstico
- Removidos logs com prefixo `[DIAGNÓSTICO]`
- Reduzidos logs redundantes em operações repetitivas
- Substituídos múltiplos logs detalhados por logs de sumário
- Implementado logging de progresso percentual em processos longos

### 2. Mudança de Níveis de Log
- Alterados logs de DEBUG para INFO apenas para eventos importantes
- Alterados logs menos importantes de INFO para DEBUG
- Mantidos logs de ERROR para falhas críticas
- Logs de WARNING apenas para situações excepcionais mas não críticas

### 3. Utilitários de Logging Centralizados
- Criado arquivo `core/utils/log_config.py` com configurações e utilitários
- Implementado decorador `timed_function` para medir desempenho de funções
- Adicionada função `reduce_log_verbosity()` para produção
- Adicionada função `configure_service_loggers()` para desenvolvimento

### 4. Logs de Progresso
- Implementado logging de progresso percentual (a cada 10%)
- Substituída mensagem detalhada por linha única com percentual
- Adicionado log de sumário ao final de processos longos

## Arquivos Modificados

1. `/core/services/rag/embedding_service.py`:
   - Reduzidos logs na inicialização
   - Reduzidos logs na geração de embeddings
   - Eliminados logs de diagnóstico de baixo nível

2. `/core/services/rag/qa_service.py`:
   - Implementado log de progresso percentual
   - Reduzidos logs redundantes para operações de banco de dados
   - Melhorados logs de sumário

3. `/gestor/views/feira.py`:
   - Reduzidos logs de baixo nível

## Como Usar

### Para Reduzir Verbosidade em Produção
Adicione ao arquivo de inicialização da aplicação ou na configuração principal:

```python
from core.utils.log_config import reduce_log_verbosity

# Chame esta função ao iniciar a aplicação
reduce_log_verbosity()
```

### Para Medir Desempenho de Funções
Decore funções críticas para monitorar desempenho:

```python
from core.utils.log_config import timed_function
import logging

@timed_function(log_level=logging.INFO)
def minha_funcao_critica():
    # código da função
    pass
```

### Para Desenvolvimento e Debugging
Aumente temporariamente o nível de log para DEBUG:

```python
from core.utils.log_config import configure_service_loggers
import logging

# Durante desenvolvimento/debugging
configure_service_loggers(level=logging.DEBUG)
```

## Benefícios

1. **Desempenho**: Redução de operações I/O (escrita de logs) em processos críticos
2. **Legibilidade**: Logs mais concisos e significativos
3. **Armazenamento**: Arquivos de log mais compactos
4. **Monitoramento**: Facilidade para identificar problemas reais (sem "ruído" de logs)