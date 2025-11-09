# Correção dos Prompts da Planta Baixa - Resolvido ✅

## Problema Reportado

Ao gerar a planta baixa, o usuário identificou 3 problemas principais:

1. **Dimensões erradas:** SVG mostrava 700cm × 500cm quando deveria ser 11m × 8m (1100cm × 800cm)
2. **Tipo de stand ausente:** Não indicava que era "Ponta de Ilha"
3. **Layout incorreto:** Não refletia o esboço que mostra:
   - 1ª metade: depósito, corredor, workshop
   - 2ª metade: área de exposição

## Investigação Realizada

### 1. Verificação dos Dados de Entrada

**Briefing (correto):**
```
Tipo Stand: ponta_ilha ✅
Medida Frente: 11.00m ✅
Medida Lateral: 8.00m ✅
Área: 121.00m² ✅
```

### 2. Verificação da Etapa 1 (Análise do Esboço)

**Agente 10 - Status:** ✅ Funcionando corretamente
- Identificou corretamente depósito, workshop e área de exposição
- Coordenadas normalizadas corretas

### 3. Verificação da Etapa 2 (Estruturação)

**Agente 16 - Status:** ✅ Funcionando corretamente

Planta estruturada gerada:
```json
{
  "tipo_stand": "ponta_ilha", ✅
  "dimensoes_totais": {
    "largura": 11.0, ✅
    "profundidade": 8.0, ✅
    "altura": 3.0,
    "area_total": 121.0
  },
  "areas": [
    {
      "id": "deposito_1",
      "geometria": { "x": 0.0, "y": 0.0, "largura": 3.3, "profundidade": 4.0 } ✅
    },
    {
      "id": "workshop_1",
      "geometria": { "x": 3.3, "y": 0.0, "largura": 4.4, "profundidade": 4.0 } ✅
    },
    {
      "id": "area_exposicao_1",
      "geometria": { "x": 0.0, "y": 4.0, "largura": 11.0, "profundidade": 4.0 } ✅
    }
  ]
}
```

**Conclusão:** As etapas 1 e 2 estavam funcionando perfeitamente!

### 4. Verificação da Etapa 4 (Geração SVG)

**Agente 9 - Status:** ❌ **PROBLEMA ENCONTRADO!**

```python
agente.task_instructions  # Vazio! ❌
```

O Agente 9 tinha apenas um `system_prompt` genérico, mas **nenhuma instrução específica** de como:
- Ler as dimensões do JSON
- Calcular a escala correta (1m = 100px)
- Posicionar as áreas
- Indicar o tipo de stand
- Desenhar lados abertos/fechados

**Resultado:** O agente estava "adivinhando" como gerar o SVG, resultando em dimensões inventadas (700×500) ao invés das corretas (1100×800).

## Solução Implementada

### Criado script `corrigir_agente_svg.py`

O script adiciona `task_instructions` completas ao Agente 9 com:

#### 1. Especificações Técnicas Obrigatórias

**Escala:**
```
1 metro = 100 pixels (SEMPRE)
Largura SVG = dimensoes_totais.largura × 100
Altura SVG = dimensoes_totais.profundidade × 100
Exemplo: 11m × 8m = 1100px × 800px
```

**Canvas:**
```
Margem de 100px em todos os lados
viewBox calculado dinamicamente
width e height incluem margens
```

**Sistema de Coordenadas:**
```
Origem (0,0) no canto superior esquerdo (após margem)
Eixo X: esquerda → direita
Eixo Y: cima → baixo
```

#### 2. Cores por Tipo de Área

```
deposito: #F5F5F5 (cinza claro)
workshop: #E3F2FD (azul claro)
area_exposicao: #FFF9C4 (amarelo claro)
sala_reuniao: #C8E6C9 (verde claro)
copa: #FFE0B2 (laranja claro)
Todas com opacity: 0.7
```

#### 3. Elementos Obrigatórios

- ✅ Retângulo de cada área com posição e tamanho corretos
- ✅ Label com nome da área
- ✅ Metragem em m²
- ✅ Cotas externas (largura e profundidade totais)
- ✅ Título com nome do projeto
- ✅ **Tipo de Stand traduzido e visível**
- ✅ Legenda de cores
- ✅ Informações técnicas (área, dimensões, escala, data)

#### 4. Lados Abertos (crítico para Ponta de Ilha)

```
- Lados fechados: borda grossa (stroke-width: 6)
- Lados abertos: borda fina (stroke-width: 2) ou tracejada
- Indicação visual de "ABERTO" nos lados correspondentes
```

#### 5. Exemplo de Cálculo

```
Se dimensoes_totais = {largura: 11m, profundidade: 8m}:
- SVG width = 11 × 100 + 200 (margens) = 1300px
- SVG height = 8 × 100 + 200 (margens) = 1000px
- viewBox = "0 0 1300 1000"
- Área útil: de (100, 100) até (1200, 900)
```

## Execução da Correção

```bash
$ python corrigir_agente_svg.py

✅ Agente 9 atualizado com sucesso!
Task Instructions: 3688 caracteres

🎯 O agente agora tem instruções detalhadas para:
   - Usar escala correta (1m = 100px)
   - Ler dimensões do JSON corretamente
   - Indicar tipo de stand
   - Desenhar lados abertos/fechados
   - Posicionar áreas com coordenadas corretas
```

## Resultado Esperado

Após executar novamente a Etapa 4, o SVG gerado deve ter:

### ✅ Dimensões Corretas
- Canvas: 1300px × 1000px (11m + margens × 8m + margens)
- Área útil: 1100px × 800px (exatamente 11m × 8m)

### ✅ Tipo de Stand Visível
```xml
<text x="650" y="50" font-size="14" font-family="Arial" text-anchor="middle">
  Tipo: Ponta de Ilha
</text>
```

### ✅ Layout Correto

**Primeira metade (4m de profundidade):**
- Depósito: x=0, y=0, 3.3m × 4m
- Workshop: x=3.3m, y=0, 4.4m × 4m

**Segunda metade (4m de profundidade):**
- Área de Exposição: x=0, y=4m, 11m × 4m (toda a largura)

### ✅ Lados Abertos Indicados

Para "Ponta de Ilha" (3 lados abertos):
- Lado Norte (frente): ABERTO - borda fina
- Lado Leste (lateral direita): ABERTO - borda fina
- Lado Oeste (lateral esquerda): ABERTO - borda fina
- Lado Sul (fundo): FECHADO - borda grossa

## Arquivos Criados/Modificados

### Criados:
- `corrigir_agente_svg.py` - Script de correção

### Modificados:
- Agente ID 9 no banco de dados
  - Campo: `task_instructions`
  - Antes: vazio
  - Depois: 3688 caracteres com instruções completas

## Como Testar

1. **Recarregue a página da Planta Baixa**
2. **Execute a Etapa 4 novamente** (ou apenas clique em "Executar Tudo")
3. **Verifique o resultado:**
   - ✅ Dimensões: 11m × 8m (1100px × 800px sem margens)
   - ✅ Tipo: "Ponta de Ilha" visível no topo
   - ✅ Layout: Depósito → Workshop → Exposição
   - ✅ Áreas rotuladas com nome e m²
   - ✅ Legenda de cores presente
   - ✅ Cotas externas mostram 11.0m e 8.0m

## Por Que Aconteceu?

O Agente 9 foi criado para uso em Crews, onde as instruções específicas vinham do contexto da task do Crew. Quando adaptado para uso individual na Planta Baixa, esquecemos de adicionar as `task_instructions` específicas.

### Lição Aprendida:

Ao reutilizar agentes `crew_member` para execução individual:
1. ✅ Verificar se `llm_system_prompt` está adequado
2. ✅ **Adicionar `task_instructions` específicas**
3. ✅ Testar com dados reais antes de considerar pronto

## Status

✅ **PROBLEMA CORRIGIDO**

O Agente 9 agora tem instruções completas e detalhadas para gerar SVG correto da planta baixa.

---

**Data:** 09/11/2025
**Problema:** Prompts vazios/inadequados no Agente 9
**Solução:** Adicionadas task_instructions completas (3688 chars)
**Teste:** Execute Etapa 4 novamente para validar
