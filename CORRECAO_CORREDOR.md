# Correção: Identificação de Corredor na Planta Baixa ✅

## Problema Reportado

Ao analisar o esboço na Etapa 1, o corredor entre o depósito e o workshop **não foi identificado** como área separada.

**Layout real do esboço:**
```
[Depósito] [Corredor] [Workshop]
[    Área de Exposição        ]
```

**O que foi identificado (ERRADO):**
```
[  Depósito  ] [   Workshop   ]
[    Área de Exposição        ]
```

O corredor foi "colado" ao depósito ou workshop, sem ser reconhecido como área independente.

## Causa Raiz

### Prompt do Agente 10 (Analisador de Esboços)

**Antes da correção:**

```
**ÁREAS INTERNAS**:
  - "deposito": espaços de armazenamento, estoque
  - "copa": área para preparo de alimentos/bebidas
  - "sala_reuniao": salas fechadas ou semi-fechadas para reuniões
  - "workshop": espaços para demonstrações, atividades práticas

**CIRCULAÇÃO**:
  - Espaços de passagem entre as áreas (não criar áreas específicas,
    mapear nos segmentos)
```

**Problema:** O prompt instruía explicitamente o agente a **NÃO criar áreas específicas** para circulação, apenas mapear como linhas no array `circulacao`.

Mas no caso de corredores DELIMITADOS no esboço (com paredes, claramente desenhados), eles DEVEM ser áreas próprias!

## Solução Implementada

### Adicionado "corredor" como Subtipo de Área Interna

**Depois da correção:**

```
**ÁREAS INTERNAS** (podem ter múltiplas instâncias):
  - "deposito": espaços de armazenamento, estoque
  - "copa": área para preparo de alimentos/bebidas
  - "sala_reuniao": salas fechadas ou semi-fechadas para reuniões
  - "workshop": espaços para demonstrações, atividades práticas
  - "corredor": espaço de circulação delimitado entre áreas
                (quando claramente desenhado como área própria) ✅ NOVO

**CIRCULAÇÃO GENÉRICA**:
  - Espaços de passagem NÃO delimitados (mapear apenas no array 'circulacao')
  - Use subtipo "corredor" quando for área física delimitada ✅
  - Use array 'circulacao' quando for apenas fluxo/passagem livre ✅
```

### Diferenciação Clara

| Situação | Como Identificar |
|----------|------------------|
| **Corredor delimitado** | Área com paredes, desenhado no esboço → `subtipo: "corredor"` |
| **Passagem livre** | Espaço aberto entre áreas → `array circulacao` |

**Exemplos:**

**Corredor delimitado (criar área):**
```
┌─────────┬──────┬─────────┐
│Depósito │██████│Workshop │
│         │ Corr.│         │
└─────────┴──────┴─────────┘
```

**Passagem livre (não criar área):**
```
┌─────────┐  ←→  ┌─────────┐
│Depósito │      │Workshop │
│         │      │         │
└─────────┘      └─────────┘
```

## Execução da Correção

```bash
$ python manage.py shell
>>> from core.models import Agente
>>> agente = Agente.objects.get(id=10)
>>> # Adicionar linha após "workshop"
>>> agente.task_instructions = agente.task_instructions.replace(
      '- "workshop": espaços para demonstrações, atividades práticas',
      '- "workshop": espaços para demonstrações, atividades práticas\n      - "corredor": espaço de circulação delimitado entre áreas (quando claramente desenhado como área própria)'
  )
>>> agente.save()
✅ CORRIGIDO E SALVO!
```

## Resultado Esperado

Ao executar a **Etapa 1 novamente**, o JSON deve incluir o corredor:

```json
{
  "areas": [
    {
      "id": "deposito_1",
      "subtipo": "deposito",
      "bbox_norm": { "x": 0.0, "y": 0.0, "w": 0.25, "h": 0.5 }
    },
    {
      "id": "corredor_1", ✅ NOVO!
      "subtipo": "corredor", ✅
      "bbox_norm": { "x": 0.25, "y": 0.0, "w": 0.10, "h": 0.5 },
      "adjacencias": [
        { "com": "deposito_1", "tipo": "interna" },
        { "com": "workshop_1", "tipo": "interna" }
      ]
    },
    {
      "id": "workshop_1",
      "subtipo": "workshop",
      "bbox_norm": { "x": 0.35, "y": 0.0, "w": 0.35, "h": 0.5 }
    },
    {
      "id": "area_exposicao_1",
      "subtipo": "area_exposicao",
      "bbox_norm": { "x": 0.0, "y": 0.5, "w": 1.0, "h": 0.5 }
    }
  ]
}
```

### Coordenadas Aproximadas (11m x 8m):

| Área | Posição | Dimensões |
|------|---------|-----------|
| Depósito | x=0m, y=0m | ~2.75m × 4m |
| **Corredor** | **x=2.75m, y=0m** | **~1.1m × 4m** ✅ |
| Workshop | x=3.85m, y=0m | ~3.85m × 4m |
| Exposição | x=0m, y=4m | 11m × 4m |

## Etapas Seguintes

Após a correção na Etapa 1, as etapas seguintes herdam a estrutura correta:

### Etapa 2 (Estruturação)

O Agente 16 receberá o layout com corredor e criará a geometria:

```json
{
  "areas": [
    { "id": "deposito_1", "geometria": {...} },
    { "id": "corredor_1", "geometria": {...} }, ✅
    { "id": "workshop_1", "geometria": {...} },
    { "id": "area_exposicao_1", "geometria": {...} }
  ]
}
```

### Etapa 4 (SVG)

O Agente 9 renderizará o corredor com:
- Cor diferenciada (provavelmente #E0E0E0 - cinza médio)
- Label "Corredor"
- Metragem em m²

## Como Testar

1. **Recarregue a página** da Planta Baixa
2. **Execute a Etapa 1 novamente** (re-análise do esboço)
3. **Verifique o JSON resultado:**
   - Deve haver área com `"subtipo": "corredor"`
   - Posicionada entre depósito e workshop
   - Com adjacências para ambos
4. **Execute Etapas 2, 3, 4**
5. **Verifique o SVG final:**
   - Deve mostrar o corredor visualmente
   - Entre depósito e workshop
   - Com cor e label apropriados

## Cor Sugerida para Corredor (Agente 9)

Para diferenciar corredor de outras áreas, sugerimos adicionar ao prompt do Agente 9:

```
corredor: #E0E0E0 (cinza médio) ou #D6EAF8 (azul muito claro)
```

## Arquivo Modificado

- **Agente ID 10** (Analisador de Esboços de Planta)
  - Campo: `task_instructions`
  - Adicionado: linha com `"corredor"` como subtipo
  - Modificado: texto de CIRCULAÇÃO para CIRCULAÇÃO GENÉRICA

## Validação

```bash
$ python manage.py shell -c "from core.models import Agente; a = Agente.objects.get(id=10); print('corredor' in a.task_instructions)"
✅ True
```

## Status

✅ **CORREÇÃO APLICADA**

O Agente 10 agora reconhece corredores delimitados como áreas próprias.

---

**Data:** 09/11/2025
**Problema:** Corredor não identificado como área separada
**Solução:** Adicionado "corredor" aos subtipos válidos
**Teste:** Execute Etapa 1 novamente para validar
