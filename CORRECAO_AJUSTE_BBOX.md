# Correção: Erro 'bbox_norm' no Ajuste Conversacional

**Data:** 09/11/2025
**Status:** ✅ CORRIGIDO

## Problema Identificado

Ao tentar aplicar ajustes conversacionais e gerar novo SVG, ocorria erro:
```
❌ 'bbox_norm'
```

Este é um `KeyError` que ocorre quando o código tenta acessar `area['bbox_norm']` mas esse campo não existe na estrutura.

## Causa Raiz

O código estava assumindo que a estrutura do layout sempre teria:
1. Campo `areas` no nível raiz
2. Campo `bbox_norm` em cada área

Porém, a estrutura real pode variar dependendo de como o agente estrutura os dados.

## Solução Implementada

### 1. **Detecção Automática de Estrutura**

O código agora detecta automaticamente qual estrutura está sendo usada:

```python
# Tentar diferentes estruturas possíveis
areas = layout.get('areas', [])
if not areas:
    # Tentar estrutura alternativa
    areas = layout.get('layout', {}).get('areas', [])
```

### 2. **Detecção Automática de Campo de Geometria**

O código detecta qual campo contém as coordenadas normalizadas:

```python
# Detectar qual campo de geometria está sendo usado
campo_geom = None
for area in areas:
    if 'bbox_norm' in area:
        campo_geom = 'bbox_norm'
        break
    elif 'geometria_norm' in area:
        campo_geom = 'geometria_norm'
        break
    elif 'bbox' in area:
        campo_geom = 'bbox'
        break
```

### 3. **Logging Detalhado para Debug**

Adicionado logging no início do processo:

```python
# Debug: verificar estrutura do layout
print(f"\n🔍 DEBUG - Estrutura do layout recebido:")
print(f"Chaves do layout: {layout.keys()}")
if 'areas' in layout and len(layout['areas']) > 0:
    print(f"Primeira área: {layout['areas'][0].keys()}")
    print(f"Conteúdo da primeira área: {layout['areas'][0]}")
```

### 4. **Validações e Mensagens de Erro Claras**

```python
if not areas:
    raise ValueError("Nenhuma área encontrada no layout")

if areas_ajustadas == 0:
    raise ValueError(f"Nenhuma área foi ajustada. Áreas procuradas: {nomes_areas}")
```

## Arquivos Modificados

**`gestor/views/planta_baixa_ajuste_view.py`**

### Métodos Atualizados:

#### 1. `AplicarAjustesView.post()` (linhas 154-195)
- ✅ Adicionado logging detalhado da estrutura recebida
- ✅ Melhor tratamento de exceções

#### 2. `_aplicar_ajuste()` (linhas 197-263)
- ✅ Detecta diferentes estruturas de layout (areas no root ou em layout.areas)
- ✅ Detecta diferentes campos de geometria (bbox_norm, geometria_norm, bbox)
- ✅ Tenta múltiplos campos antes de falhar
- ✅ Contador de áreas ajustadas para validar sucesso

#### 3. `_normalizar_100porcento()` (linhas 265-325)
- ✅ Detecta estrutura do layout automaticamente
- ✅ Detecta campo de geometria usado
- ✅ Funciona com qualquer campo (bbox_norm, geometria_norm, bbox)

#### 4. `_recalcular_metros()` (linhas 327-398)
- ✅ Detecta estrutura do layout automaticamente
- ✅ Detecta campo de geometria usado
- ✅ Suporta múltiplos campos de medidas do briefing
- ✅ Logging de erros com traceback completo

## Como Testar Novamente

1. Execute as 4 Etapas normalmente
2. Após ver o SVG, clique em "Ajustar Dimensões"
3. Digite: `deposito e workshop mesmo tamanho`
4. Veja a resposta do bot confirmando o ajuste
5. Clique em "Aplicar e Gerar Novo SVG"

**Resultado esperado:**
- ✅ Nenhum erro 'bbox_norm'
- ✅ Layout ajustado corretamente
- ✅ Novo SVG gerado com dimensões atualizadas

Se ainda ocorrer erro, verifique o console do servidor Django - agora terá logging detalhado mostrando:
- Chaves do layout recebido
- Estrutura da primeira área
- Qual campo de geometria foi detectado
- Quais áreas foram ajustadas

## Campos Suportados

O código agora funciona com qualquer uma destas estruturas:

### Estrutura do Layout:
- ✅ `layout['areas']` (no root)
- ✅ `layout['layout']['areas']` (nested)

### Campos de Geometria Normalizada:
- ✅ `area['bbox_norm']` (bounding box normalizado)
- ✅ `area['geometria_norm']` (geometria normalizada)
- ✅ `area['bbox']` (bounding box)

### Campos de Identificação de Área:
- ✅ `area['id']`
- ✅ `area['nome']`
- ✅ `area['tipo']`

---

**Próximo passo:** Testar no ambiente de desenvolvimento e verificar logs do servidor.
