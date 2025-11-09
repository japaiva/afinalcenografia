# Correção: Equilíbrio na Identificação de Corredores - Resolvido ✅

## Problema Reportado

Após as correções anteriores, o usuário notou:

> "mas cadê o corredor entre depósito e workshop??"

### JSON Gerado (SEM CORREDOR):
```json
{
  "areas": [
    {
      "id": "deposito_1",
      "bbox_norm": {"x": 0, "y": 0, "w": 0.3, "h": 0.5}
    },
    {
      "id": "workshop_1",
      "bbox_norm": {"x": 0.3, "y": 0, "w": 0.4, "h": 0.5}
    }
  ]
}
```

**Problema:** Depósito e workshop estão COLADOS (x=0 até 0.3, depois x=0.3 até 0.7), mas no esboço há um **corredor físico desenhado** entre eles!

## Análise da Causa Raiz

### Histórico de Correções:

1. **Primeira correção:** Adicionar "corredor" como subtipo válido ✅
2. **Segunda correção:** "Corredor = CIRCULAÇÃO, não espaço vazio" ✅
3. **Terceira correção:** "NÃO criar corredor para mobiliário" ✅

**Resultado:** As instruções ficaram **MUITO RESTRITIVAS** e agora o agente está ignorando até corredores REAIS desenhados no esboço!

### Conflito nas Instruções:

**Instruções Anteriores (muito restritivas):**
```
- "corredor": CRIE APENAS quando:
  * Houver RÓTULO explícito
  * ⚠️ NÃO criar corredor só porque "sobrou espaço"
```

**Problema:** O agente interpretou que precisa de rótulo explícito, e está ignorando corredores desenhados sem rótulo.

## Conceito Correto - Equilíbrio

### ✅ CRIAR corredor quando:

1. **Rótulo explícito** ("corredor", "passagem", "acesso")
2. **Desenho de passagem** entre áreas (mesmo sem rótulo)
3. **Espaço ESTREITO** entre áreas:
   - < 2 metros de largura
   - < 20% da largura total do stand
   - Proporcional para circulação
4. **Paredes/linhas** delimitando passagem

### ❌ NÃO criar corredor quando:

1. **Espaço LARGO** sem função clara (> 3m)
2. **Mobiliário** (balcões, prateleiras)
3. **Área grande** "sobrando" sem evidência de circulação

## Diferença Crítica

### Corredor REAL (Criar ✅):
```
[Depósito 3m] [espaço 1m] [Workshop 4m] [Exposição 3m]
                 ↑
            CORREDOR!

- Espaço estreito (1m = 9% da largura)
- Desproporcional às áreas (3m, 4m, 3m vs 1m)
- Claramente para passagem
```

### Espaço Grande (NÃO criar ❌):
```
[Depósito 3m] [espaço 5m] [Workshop 3m]
                 ↑
         NÃO é corredor!

- Espaço largo (5m = 45% da largura)
- Proporcional às áreas (mesmo tamanho)
- Provavelmente é outra área (exposição)
```

## Solução Implementada

### Nova Definição de Corredor:

```
- "corredor": espaço de CIRCULAÇÃO (passagem) entre áreas - CRIE quando:
  * Houver RÓTULO explícito: "corredor", "passagem", "acesso", "circulação"
  * Houver DESENHO de passagem entre áreas (mesmo sem rótulo)
  * Houver espaço ESTREITO entre áreas (< 2m ou < 20% da largura total)
  * Houver paredes/linhas delimitando uma passagem vertical ou horizontal

  ⚠️ DIFERENÇA IMPORTANTE:
  ✅ Espaço ESTREITO (1-2m) entre depósito e workshop = CORREDOR (criar!)
  ❌ Espaço LARGO (> 3m) sem função clara = parte de outra área (não criar)

  **Exemplo no esboço:**
  [Depósito 3m] [espaço 1m] [Workshop 4m] [Exposição 3m]
                  ↑ CRIAR corredor aqui!

  **Regra prática:** Se o espaço entre áreas é DESPROPORCIONAL (muito estreito
  comparado às áreas adjacentes), é provável que seja corredor para circulação.
```

## Critérios de Desproporção

| Espaço | % Largura | Largura (11m) | Decisão |
|--------|-----------|---------------|---------|
| < 1.5m | < 15% | < 1.5m | ✅ Provavelmente corredor |
| 1.5-2m | 15-20% | 1.5-2m | ⚠️ Analisar contexto |
| 2-3m | 20-30% | 2-3m | ❓ Pode ser área pequena |
| > 3m | > 30% | > 3m | ❌ Provavelmente área |

**Para stand 11m × 8m:**
- Corredor típico: 1m (9% da largura) ✅
- Área pequena: 2.5m (23% da largura) ✅
- Área média: 3.5m (32% da largura) ✅

## Resultado Esperado

### Layout Real do Esboço:
```
┌─────────┬──┬──────────┐
│Depósito │██│Workshop  │  Metade superior (4m)
│  3m     │1m│   4m     │  ██ = corredor
├─────────┴──┴──────────┤
│  Área de Exposição    │  Metade inferior (4m)
│        11m            │
└───────────────────────┘
```

### JSON Esperado (COM CORREDOR):
```json
{
  "areas": [
    {
      "id": "deposito_1",
      "subtipo": "deposito",
      "bbox_norm": {"x": 0.0, "y": 0.0, "w": 0.27, "h": 0.5}
      // 3m / 11m ≈ 0.27
    },
    {
      "id": "corredor_1",  ← ✅ CORREDOR APARECE!
      "subtipo": "corredor",
      "bbox_norm": {"x": 0.27, "y": 0.0, "w": 0.09, "h": 0.5}
      // 1m / 11m ≈ 0.09
    },
    {
      "id": "workshop_1",
      "subtipo": "workshop",
      "bbox_norm": {"x": 0.36, "y": 0.0, "w": 0.36, "h": 0.5}
      // 4m / 11m ≈ 0.36
    },
    {
      "id": "area_exposicao_1",
      "subtipo": "area_exposicao",
      "bbox_norm": {"x": 0.0, "y": 0.5, "w": 1.0, "h": 0.5}
    }
  ]
}
```

### Coordenadas Absolutas (11m × 8m):

| Área | x | y | largura | profundidade | m² |
|------|---|---|---------|--------------|-----|
| Depósito | 0m | 0m | 3m | 4m | 12m² |
| **Corredor** | **3m** | **0m** | **1m** | **4m** | **4m²** |
| Workshop | 4m | 0m | 4m | 4m | 16m² |
| Exposição | 0m | 4m | 11m | 4m | 44m² |
| **TOTAL** | | | | | **76m²** |

## Princípios de Equilíbrio

### 1. Corredor Real ≠ Espaço Vazio

- **Corredor:** Passagem funcional, estreita, para circulação
- **Espaço Vazio:** Área grande sem função identificada

### 2. Proporção é Indicador

- Espaço **desproporcional** (muito menor que áreas) = corredor
- Espaço **proporcional** (tamanho similar) = área

### 3. Contexto Visual Importa

- Desenhado no esboço como passagem = corredor
- Sem indicação visual = analisar proporção

### 4. Hierarquia de Decisão

1. Há rótulo? → usar rótulo
2. Há desenho de passagem? → criar corredor
3. É estreito (< 2m)? → provavelmente corredor
4. É largo (> 3m)? → provavelmente área

## Arquivo Modificado

- **Agente ID 10** (Analisador de Esboços de Planta)
  - Campo: `task_instructions`
  - Seção modificada: Definição de "corredor"
  - Adicionado: Critérios de espaço ESTREITO vs LARGO
  - Adicionado: Regra de desproporção
  - Adicionado: Exemplos práticos

## Como Testar

1. **Recarregue a página da Planta Baixa**
2. **Execute a Etapa 1 novamente**
3. **Verifique o JSON resultado:**
   - ✅ Deve haver "corredor_1" entre depósito e workshop
   - ✅ Coordenadas: x ≈ 0.27, w ≈ 0.09 (1m de largura)
   - ✅ Mesmo Y para depósito, corredor e workshop (y=0.0)
4. **Execute Etapas 2, 3, 4**
5. **Verifique o SVG final:**
   - Corredor visível entre depósito e workshop
   - Cor diferenciada (#E0E0E0 - cinza médio)
   - Label "Corredor" e metragem (~4m²)

## Validação

```bash
$ python3 equilibrar_corredor.py

✅ CORREÇÃO APLICADA COM SUCESSO!

📋 O que foi ajustado:
   - Corredor DESENHADO no esboço = criar (mesmo sem rótulo)
   - Espaço ESTREITO (< 2m) entre áreas = criar
   - Espaço LARGO (> 3m) sem função = não criar

🎯 Critérios equilibrados:
   ✅ Criar: passagem desenhada, espaço estreito, proporcional
   ❌ Não criar: espaço grande sem função, mobiliário

💡 Exemplo:
   - [Depósito 3m] [1m] [Workshop 4m] → 1m é CORREDOR ✅
   - [Depósito 3m] [5m vazio] [Workshop] → 5m é OUTRA ÁREA ❌
```

## Lições Aprendidas

### 1. Correções Incrementais Podem Conflitar

- Cada correção resolveu um problema específico
- Mas juntas ficaram muito restritivas
- Necessário revisar o efeito combinado

### 2. "Restritivo Demais" é Tão Ruim Quanto "Permissivo Demais"

- Antes: criava corredores para tudo (espaços vazios)
- Depois das correções: não criava corredor nenhum (nem reais)
- Solução: equilíbrio com critérios claros

### 3. Contexto Visual Importa

- Não podemos depender apenas de rótulos
- Desenho visual (linhas, proporções) é evidência válida
- Proporção é indicador forte de função

## Status

✅ **CORREÇÃO APLICADA**

O Agente 10 agora tem critérios equilibrados:
- Identifica corredores REAIS (desenhados, estreitos)
- NÃO cria corredores para espaços grandes sem função
- Usa proporção como indicador (< 2m = corredor, > 3m = área)

---

**Data:** 09/11/2025
**Reportado por:** Usuário ("mas cadê o corredor entre depósito e workshop??")
**Problema:** Instruções muito restritivas ignorando corredores reais
**Solução:** Critérios equilibrados (estreito vs largo, proporção)
**Teste:** Execute Etapa 1 e verifique corredor_1 entre depósito e workshop
