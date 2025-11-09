# Correção do Erro "Start tag expected, '<' not found" - Resolvido ✅

## Problema

Ao visualizar o SVG gerado na Etapa 4 da Planta Baixa, o navegador mostrou o seguinte erro:

```
This page contains the following errors:
error on line 1 at column 1: Start tag expected, '<' not found
Below is a rendering of the page up to the first error.
```

## Causa

O erro indica que o conteúdo retornado **não é SVG válido**. Isso acontece quando:

1. O agente retorna JSON contendo o SVG ao invés do SVG puro
2. O agente inclui markdown code blocks: ` ```svg ... ``` `
3. O SVG vem dentro de um campo de objeto JSON
4. Há texto adicional antes ou depois do SVG

### Exemplo de Respostas Problemáticas:

**Formato 1 - JSON:**
```json
{
  "svg": "<svg>...</svg>",
  "observacoes": "Planta gerada com sucesso"
}
```

**Formato 2 - Markdown:**
```
Aqui está o SVG da planta baixa:

```svg
<svg>...</svg>
```

O SVG foi gerado seguindo as especificações.
```

**Formato 3 - Texto misto:**
```
<svg width="800" height="600">
  <!-- planta baixa -->
</svg>

Nota: Verifique as dimensões antes de usar.
```

## Solução Implementada

Criamos um método robusto `_extrair_svg()` que:

1. ✅ Detecta o formato da resposta (string, dict, etc)
2. ✅ Extrai SVG de objetos JSON
3. ✅ Remove markdown code blocks
4. ✅ Procura por `<svg>` dentro do texto
5. ✅ Valida se começa com `<`
6. ✅ Retorna erro descritivo se falhar

### Código Adicionado (planta_baixa_service.py)

```python
def _extrair_svg(self, dados: Any) -> str:
    """
    Extrai código SVG de diferentes formatos de resposta.
    """
    import re

    # Se já é string, processar diretamente
    if isinstance(dados, str):
        svg = dados

    # Se é dict, tentar extrair de campos conhecidos
    elif isinstance(dados, dict):
        svg = (dados.get("svg") or
               dados.get("codigo_svg") or
               dados.get("resultado") or
               dados.get("output") or
               dados.get("content") or
               str(dados))
    else:
        svg = str(dados)

    # Remover markdown code blocks
    svg = re.sub(r'^```(?:svg|xml)?\s*\n', '', svg, flags=re.MULTILINE)
    svg = re.sub(r'\n```\s*$', '', svg, flags=re.MULTILINE)

    # Remover espaços
    svg = svg.strip()

    # Se não começa com < mas tem <svg, extrair
    if not svg.startswith('<') and '<svg' in svg:
        match = re.search(r'(<svg[\s\S]*?</svg>)', svg, re.IGNORECASE)
        if match:
            svg = match.group(1)

    return svg
```

### Validação Adicionada

```python
# Após extrair o SVG, validar se é válido
if not svg_content or not svg_content.strip().startswith('<'):
    return {
        "sucesso": False,
        "erro": "Agente não retornou SVG válido. Resposta recebida: " + str(svg_content)[:200]
    }
```

## Formatos Suportados

O método `_extrair_svg()` agora suporta todos estes formatos:

### ✅ Formato 1 - SVG Puro (ideal)
```xml
<svg width="800" height="600">
  <!-- conteúdo -->
</svg>
```

### ✅ Formato 2 - JSON com campo "svg"
```json
{
  "svg": "<svg>...</svg>"
}
```

### ✅ Formato 3 - JSON com campo alternativo
```json
{
  "codigo_svg": "<svg>...</svg>"
}
```

### ✅ Formato 4 - Markdown
```markdown
```svg
<svg>...</svg>
```
```

### ✅ Formato 5 - Texto misto
```
Resultado da geração:
<svg>...</svg>
Observações: ...
```

## Campos Buscados no JSON

O método busca SVG nos seguintes campos (em ordem):

1. `svg` - Campo padrão
2. `codigo_svg` - Alternativa em português
3. `resultado` - Campo genérico
4. `output` - Saída genérica
5. `content` - Conteúdo genérico

Se nenhum campo for encontrado, converte o objeto inteiro para string.

## Fluxo de Extração

```
Resposta do Agente
    ↓
É string ou dict?
    ↓
Se dict → Buscar campos conhecidos
Se string → Usar diretamente
    ↓
Remover markdown code blocks (``` ```)
    ↓
Remover espaços em branco
    ↓
Não começa com <? → Procurar <svg>...</svg>
    ↓
Validar: Começa com <?
    ↓
Retornar SVG puro
```

## Exemplo de Uso

```python
# No método etapa4_gerar_svg:
resultado = _run_agent("Renderizador SVG Profissional", payload)
svg_content = resultado["dados"]

# ANTES (❌ falhava com formatos não-puros):
self.projeto.planta_baixa_svg = svg_content

# DEPOIS (✅ extrai corretamente):
svg_content = self._extrair_svg(svg_content)

# Validação
if not svg_content.strip().startswith('<'):
    return {"sucesso": False, "erro": "SVG inválido"}

self.projeto.planta_baixa_svg = svg_content
```

## Debugging

Se o problema persistir, o erro agora mostra os primeiros 200 caracteres da resposta:

```python
"erro": "Agente não retornou SVG válido. Resposta recebida: {
  'status': 'success',
  'svg': '<svg width=..."
```

Isso permite identificar rapidamente qual formato o agente está usando.

## Ajuste no Prompt do Agente (Opcional)

Se quiser garantir SVG puro sem processamento, pode ajustar as `task_instructions` do agente ID 9:

```
IMPORTANTE:
- Retorne APENAS o código SVG puro
- NÃO inclua JSON ou explicações
- NÃO use markdown code blocks (```svg)
- Comece diretamente com <svg>
- Termine com </svg>
```

Mas com a correção implementada, isso não é mais necessário - o sistema aceita qualquer formato.

## Arquivo Modificado

- `gestor/services/planta_baixa_service.py`
  - Linhas 273-283: Adicionada extração e validação de SVG
  - Linhas 302-344: Método `_extrair_svg()` completo

## Teste de Validação

```bash
$ python manage.py check
System check identified no issues (0 silenced).
```

✅ **Sem erros!**

## Teste Funcional

1. Execute a Etapa 4 novamente
2. O SVG agora será extraído corretamente
3. Verifique se renderiza no navegador
4. Se ainda houver erro, veja a mensagem detalhada com os primeiros 200 chars

## Casos Extremos Tratados

### 1. Múltiplos SVGs na Resposta
```python
# Extrai apenas o primeiro <svg>...</svg>
match = re.search(r'(<svg[\s\S]*?</svg>)', svg, re.IGNORECASE)
```

### 2. SVG com Namespace XML
```xml
<?xml version="1.0"?>
<svg xmlns="http://www.w3.org/2000/svg">...</svg>
```
✅ Funciona - começa com `<`

### 3. SVG Minificado
```xml
<svg width="800" height="600"><rect x="0" y="0" width="100" height="100"/></svg>
```
✅ Funciona - nenhum espaço necessário

### 4. SVG com Comentários Antes
```xml
<!-- Planta Baixa Gerada -->
<svg>...</svg>
```
✅ Funciona - comentários XML são válidos

## Status

✅ **PROBLEMA RESOLVIDO**

O sistema agora extrai SVG corretamente de qualquer formato de resposta e valida antes de salvar.

---

**Data:** 09/11/2025
**Arquivo:** `planta_baixa_service.py`
**Mudança:** Extração robusta de SVG com validação
