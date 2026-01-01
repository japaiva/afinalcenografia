# Progresso: Módulo 2 - Renderização AI

**Data:** 09/11/2025
**Status:** 🚧 Em Implementação

---

## ✅ Implementado

### 1. Campos no Banco de Dados
**Arquivo:** `projetos/models/projeto.py`

Adicionados 8 novos campos:

**Renderização AI:**
- `renderizacao_ai_json` - JSON enriquecido (planta + briefing + elementos visuais)
- `imagem_conceito_url` - URL da imagem DALL-E
- `prompt_dalle_atual` - Prompt usado para gerar a imagem
- `renderizacao_ai_processada` - Flag booleana
- `data_renderizacao_ai` - Timestamp

**Modelo 3D (preparação para Módulo 3):**
- `arquivo_3d` - Arquivo .skp (SketchUp)
- `modelo_3d_processado` - Flag booleana
- `data_modelo_3d` - Timestamp

✅ Migration criada e aplicada: `0032_projeto_arquivo_3d_projeto_data_modelo_3d_and_more.py`

---

### 2. Service de Renderização AI
**Arquivo:** `gestor/services/renderizacao_ai_service.py`

**Classe:** `RenderizacaoAIService`

**Métodos Implementados:**

#### `etapa1_enriquecer_json()`
```python
# Combina:
# - planta_baixa_json
# - dados do briefing
# - inspirações visuais
#
# Cria estrutura:
# {
#   "planta": {...},
#   "briefing": {...},
#   "estilo": {...},
#   "elementos_visuais": {...},
#   "historico_ajustes": [],
#   "metadata": {...}
# }
```

#### `etapa2_gerar_prompt()`
```python
# Usa agente IA (GPT-4) para criar prompt DALL-E
# Input: conceito_visual_json
# Output: prompt otimizado e detalhado
```

#### `etapa3_gerar_imagem()`
```python
# Chama API DALL-E 3
# Model: dall-e-3
# Size: 1792x1024 (landscape)
# Quality: hd
# Output: URL da imagem
```

**Métodos Auxiliares:**
- `_extrair_dados_briefing()` - Extrai dados do briefing
- `_extrair_inspiracoes()` - Extrai paleta, materiais, referências
- `_criar_elementos_default()` - Estrutura padrão de elementos visuais
- `_resumir_briefing()` - Resume briefing em texto

---

## ⏳ Próximos Passos

### 3. Criar Agente "Gerador de Prompt DALL-E"
**Tipo:** Individual
**LLM:** GPT-4o
**Função:** Receber JSON enriquecido e gerar prompt detalhado para DALL-E

**Task Instructions (esboço):**
```
Você é um especialista em prompts para DALL-E 3.

INPUT: JSON com dados da planta baixa + briefing + elementos visuais

TAREFA:
1. Analisar layout físico (dimensões, áreas)
2. Incorporar estilo visual (cores, materiais)
3. Descrever elementos específicos (iluminação, mobiliário, etc.)
4. Criar prompt em inglês, detalhado e técnico

OUTPUT: Prompt otimizado para DALL-E 3
```

---

### 4. Criar Views
**Arquivo:** `gestor/views/renderizacao_ai.py`

**Views Necessárias:**

```python
# View principal (wizard)
def renderizacao_ai_wizard(request, projeto_id):
    """Tela principal do módulo de Renderização AI"""
    pass

# Etapa 1: Enriquecimento
@require_POST
def renderizacao_etapa1_enriquecer(request, projeto_id):
    """Enriquece JSON com dados do briefing"""
    pass

# Etapa 2: Gerar Prompt
@require_POST
def renderizacao_etapa2_prompt(request, projeto_id):
    """Gera prompt DALL-E usando IA"""
    pass

# Etapa 3: Gerar Imagem
@require_POST
def renderizacao_etapa3_imagem(request, projeto_id):
    """Gera imagem usando DALL-E 3"""
    pass
```

---

### 5. Criar Template
**Arquivo:** `templates/gestor/renderizacao_ai_wizard.html`

**Estrutura (similar à Planta Baixa):**

```html
<!-- CABEÇALHO -->
<div class="card">
  <h4>Renderização AI - {{ projeto.nome }}</h4>
  <button>Executar Tudo</button>
</div>

<!-- ETAPA 1: ENRIQUECIMENTO -->
<div class="card">
  <h5>1. Enriquecimento do JSON</h5>
  <button onclick="executarEtapa1()">Executar</button>

  <!-- Resultado (escondido) -->
  <button onclick="toggleJson('json-etapa1')">Ver Detalhes Técnicos</button>
  <div id="json-etapa1" class="d-none">
    <pre id="json-enriquecido"></pre>
  </div>
</div>

<!-- ETAPA 2: PROMPT -->
<div class="card">
  <h5>2. Geração do Prompt DALL-E</h5>
  <button onclick="executarEtapa2()">Executar</button>

  <!-- Resultado -->
  <div class="alert alert-success">
    <i class="fas fa-check-circle"></i> Prompt gerado com sucesso
  </div>

  <button onclick="togglePrompt()">Ver Prompt</button>
  <div id="prompt-container" class="d-none">
    <pre id="prompt-dalle"></pre>
  </div>
</div>

<!-- ETAPA 3: IMAGEM -->
<div class="card">
  <h5>3. Geração da Imagem</h5>
  <button onclick="executarEtapa3()">Gerar Imagem</button>

  <!-- Resultado -->
  <div class="alert alert-success">
    <i class="fas fa-check-circle"></i> Imagem gerada com sucesso!
  </div>

  <div class="text-center">
    <img id="imagem-conceito" src="" class="img-fluid">
  </div>

  <div class="mt-3">
    <button onclick="baixarImagem()">Baixar Imagem</button>
    <button onclick="mostrarAjusteFino()">Ajustar Conceito</button>
  </div>
</div>

<!-- MÓDULO DE AJUSTE CONVERSACIONAL -->
<div id="card-ajuste" class="d-none">
  <!-- Similar ao ajuste da Planta Baixa -->
</div>
```

---

### 6. Implementar Ajuste Conversacional

**Arquivo:** `gestor/views/renderizacao_ai_ajuste.py`

**Comandos Suportados:**
- "adiciona plantas suspensas"
- "deixa mais moderno"
- "troca azul por verde"
- "adiciona iluminação quente"
- "mobiliário minimalista"

**Fluxo:**
1. Interpretar comando
2. Modificar `renderizacao_ai_json.elementos_visuais`
3. Salvar no banco
4. Regenerar prompt (Etapa 2)
5. Regenerar imagem (Etapa 3)

---

### 7. Registrar URLs

**Arquivo:** `gestor/urls.py`

```python
# Renderização AI
path('projeto/<int:projeto_id>/renderizacao-ai/',
     views.renderizacao_ai_wizard,
     name='renderizacao_ai_wizard'),

path('projeto/<int:projeto_id>/renderizacao-ai/etapa1/',
     views.renderizacao_etapa1_enriquecer,
     name='renderizacao_etapa1'),

path('projeto/<int:projeto_id>/renderizacao-ai/etapa2/',
     views.renderizacao_etapa2_prompt,
     name='renderizacao_etapa2'),

path('projeto/<int:projeto_id>/renderizacao-ai/etapa3/',
     views.renderizacao_etapa3_imagem,
     name='renderizacao_etapa3'),

# Ajuste conversacional
path('projeto/<int:projeto_id>/renderizacao-ai/ajustar/',
     views.RenderizacaoAjusteView.as_view(),
     name='renderizacao_ajustar'),
```

---

### 8. Link na Interface do Projeto

**Arquivo:** `templates/gestor/projeto_detail.html`

Adicionar card:
```html
<div class="card">
  <h5>2. Renderização AI</h5>
  {% if projeto.planta_baixa_processada %}
    <a href="{% url 'gestor:renderizacao_ai_wizard' projeto.id %}">
      <i class="fas fa-image"></i> Gerar Conceito Visual
    </a>
  {% else %}
    <span class="text-muted">Complete a Planta Baixa primeiro</span>
  {% endif %}
</div>
```

---

## 📊 Estrutura de Dados

### JSON Enriquecido (renderizacao_ai_json)

```json
{
  "planta": {
    // Cópia de planta_baixa_json
    "tipo_stand": "ponta_ilha",
    "dimensoes_totais": {...},
    "areas": [...]
  },

  "briefing": {
    "objetivo_principal": "aumentar vendas",
    "publico_alvo": "arquitetos",
    "mensagem_chave": "inovação sustentável",
    "produtos_destaque": "...",
    "atividades": "..."
  },

  "estilo": {
    "paleta_cores": {
      "primaria": "#2E7D32",
      "secundaria": "#FFFFFF",
      "acento": "#FFC107"
    },
    "materiais": ["madeira", "vidro", "metal"],
    "referencias_visuais": [
      {"url": "...", "tipo": "stand_similar"}
    ]
  },

  "elementos_visuais": {  // ← AJUSTÁVEL VIA CONVERSACIONAL
    "iluminacao": {...},
    "mobiliario": {...},
    "graficos": {...},
    "vegetacao": {...},
    "pisos": {...},
    "paredes": {...}
  },

  "historico_ajustes": [
    {
      "timestamp": "2025-11-09T15:00:00",
      "comando": "adiciona plantas suspensas",
      "campo_modificado": "elementos_visuais.vegetacao",
      "valor_anterior": null,
      "valor_novo": {"tipo": "plantas suspensas"}
    }
  ],

  "metadata": {
    "versao": "1.0",
    "data_criacao": "2025-11-09T14:00:00",
    "ultima_modificacao": "2025-11-09T15:00:00",
    "imagem_atual": "https://...",
    "total_regeneracoes": 2
  }
}
```

---

## 🎯 Checklist de Implementação

- [x] Adicionar campos no modelo Projeto
- [x] Criar migration e aplicar
- [x] Criar RenderizacaoAIService
  - [x] etapa1_enriquecer_json()
  - [x] etapa2_gerar_prompt_e_imagem() (usa agente existente)
- [x] ~~Criar agente "Gerador de Prompt DALL-E"~~ (já existe: "Agente de Imagem Principal")
- [x] Criar views
  - [x] renderizacao_ai_wizard
  - [x] renderizacao_etapa1_enriquecer
  - [x] renderizacao_etapa2_gerar (combina prompt + imagem)
  - [x] renderizacao_executar_tudo
- [x] Criar template wizard
- [ ] Implementar ajuste conversacional
- [x] Registrar URLs
- [x] Adicionar link no projeto_detail
- [x] Criar template de erro
- [ ] Testar fluxo completo

---

## ✅ Status Atual (09/11/2025)

**Módulo 2 - Renderização AI: IMPLEMENTADO (aguardando testes)**

### Arquivos Criados/Modificados:

1. **Backend:**
   - ✅ `gestor/services/renderizacao_ai_service.py` - Service completo
   - ✅ `gestor/views/renderizacao_ai.py` - Views do wizard
   - ✅ `gestor/views/__init__.py` - Imports atualizados
   - ✅ `gestor/urls.py` - URLs registradas
   - ✅ `projetos/models/projeto.py` - 8 campos adicionados
   - ✅ `projetos/migrations/0032_*.py` - Migration aplicada

2. **Frontend:**
   - ✅ `templates/gestor/renderizacao_ai_wizard.html` - Interface completa
   - ✅ `templates/gestor/projeto_detail.html` - Link adicionado
   - ✅ `templates/gestor/erro.html` - Template de erro

3. **Agente:**
   - ✅ Reusa "Agente de Imagem Principal" (ID 6, gpt-image-1)

### Funcionalidades Implementadas:

- ✅ Etapa 1: Enriquecimento do JSON (planta + briefing + inspirações)
- ✅ Etapa 2: Geração de prompt estruturado + imagem DALL-E
- ✅ Botão "Executar Tudo" (sequencial)
- ✅ JSON enriquecido escondido com toggle
- ✅ Prompt escondido com toggle
- ✅ Exibição da imagem gerada
- ✅ Download de imagem
- ✅ Validação de dependências (planta baixa + briefing)
- ✅ Mensagens de erro
- ✅ Loading states

---

**Próxima ação:** Testar fluxo completo ou implementar ajuste conversacional?
