# Correção do Erro llm_max_tokens - Resolvido ✅

## Problema

Ao executar a Etapa 1 da Planta Baixa, ocorreu o seguinte erro:

```
Erro na Etapa 1: Erro ao executar agente: Falha na execução do agente:
Falha ao executar agente: 'Agente' object has no attribute 'llm_max_tokens'
```

## Causa

O código em `gestor/services/agente_executor.py` estava tentando acessar um atributo `llm_max_tokens` que **não existe** no modelo `Agente`:

```python
# CÓDIGO COM ERRO:
max_tokens=agente.llm_max_tokens or 4096  # ❌ Atributo não existe!
```

### Campos Disponíveis no Modelo Agente:

```python
class Agente(models.Model):
    nome = models.CharField(max_length=200)
    tipo = models.CharField(max_length=20)
    descricao = models.TextField(blank=True)

    # Configurações LLM
    llm_provider = models.CharField(max_length=50)
    llm_model = models.CharField(max_length=100)
    llm_temperature = models.FloatField(default=0.3)

    # ❌ llm_max_tokens NÃO EXISTE!

    llm_system_prompt = models.TextField()
    task_instructions = models.TextField(blank=True)
    # ... outros campos
```

## Solução Implementada

Usamos `getattr()` com valor padrão para acessar o atributo de forma segura:

### Correção em OpenAI (linha 139):

**Antes:**
```python
max_tokens=agente.llm_max_tokens or 4096  # ❌ Erro se não existir
```

**Depois:**
```python
max_tokens=getattr(agente, 'llm_max_tokens', 4096) or 4096  # ✅ Usa 4096 se não existir
```

### Correção em Anthropic (linha 182):

**Antes:**
```python
max_tokens=agente.llm_max_tokens or 4096  # ❌ Erro se não existir
```

**Depois:**
```python
max_tokens=getattr(agente, 'llm_max_tokens', 4096) or 4096  # ✅ Usa 4096 se não existir
```

## Como `getattr()` Funciona

```python
getattr(objeto, 'atributo', valor_padrao)
```

- **Se o atributo existe:** Retorna o valor do atributo
- **Se o atributo não existe:** Retorna `valor_padrao` ao invés de lançar `AttributeError`

### Exemplo:

```python
# Com atributo existente:
agente.llm_temperature  # 0.3
getattr(agente, 'llm_temperature', 1.0)  # 0.3 (usa valor do modelo)

# Sem atributo:
agente.llm_max_tokens  # ❌ AttributeError
getattr(agente, 'llm_max_tokens', 4096)  # ✅ 4096 (usa valor padrão)
```

## Valores Padrão Definidos

| Provider | max_tokens Padrão | Nota |
|----------|-------------------|------|
| OpenAI | 4096 | Suficiente para GPT-4, GPT-4o |
| Anthropic | 4096 | Suficiente para Claude 3 |

**Observação:** 4096 tokens é um valor conservador e seguro para ambos os providers.

## Alternativa: Adicionar Campo ao Modelo (Futuro)

Se quiser controlar `max_tokens` por agente, pode adicionar o campo ao modelo:

### Migration necessária:

```python
# core/migrations/0023_agente_llm_max_tokens.py

from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('core', '0022_feira_data_extracao_regras_feira_regras_extraidas_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='agente',
            name='llm_max_tokens',
            field=models.PositiveIntegerField(
                default=4096,
                help_text="Máximo de tokens na resposta"
            ),
        ),
    ]
```

### Após adicionar o campo:

Pode voltar ao código original:
```python
max_tokens=agente.llm_max_tokens or 4096  # Funcionará normalmente
```

## Arquivos Modificados

- `gestor/services/agente_executor.py`
  - Linha 139: Corrigido acesso em `_executar_openai()`
  - Linha 182: Corrigido acesso em `_executar_anthropic()`

## Teste de Validação

```bash
$ python manage.py check
System check identified no issues (0 silenced).
```

✅ **Sem erros!**

## Status

✅ **PROBLEMA RESOLVIDO**

Agora você pode testar novamente a Etapa 1 da Planta Baixa sem erros!

---

**Data:** 09/11/2025
**Arquivo:** `gestor/services/agente_executor.py`
**Método:** Uso de `getattr()` com valor padrão
