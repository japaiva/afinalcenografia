# Arquitetura: Visualização do Stand

**Data:** 09/11/2025
**Status:** 📋 Planejamento

---

## Visão Geral dos Módulos

```
┌─────────────────────────────────────────────────────────┐
│ 1. PLANTA BAIXA ✅ (IMPLEMENTADO)                        │
├─────────────────────────────────────────────────────────┤
│ • Análise do esboço                                     │
│ • Estruturação com coordenadas                          │
│ • Validação                                             │
│ • Ajuste conversacional de dimensões                    │
│ • Geração SVG                                           │
│                                                         │
│ OUTPUT: projeto.planta_baixa_json                       │
└─────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│ 2. RENDERIZAÇÃO AI ⏳ (A IMPLEMENTAR)                    │
├─────────────────────────────────────────────────────────┤
│ INPUT: planta_baixa_json + briefing + inspirações       │
│                                                         │
│ Etapas:                                                 │
│ 1. Enriquecimento do JSON                               │
│ 2. Geração de prompt DALL-E                             │
│ 3. Geração de imagem                                    │
│ 4. [Opcional] Ajuste conversacional                     │
│ 5. Regeneração (prompt + imagem)                        │
│                                                         │
│ OUTPUT: projeto.conceito_visual_json                    │
│         projeto.imagem_conceito_url                     │
└─────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│ 3. MODELO 3D ⏳ (A IMPLEMENTAR)                          │
├─────────────────────────────────────────────────────────┤
│ INPUT: conceito_visual_json                             │
│                                                         │
│ Etapas:                                                 │
│ 1. Conversão JSON → Geometria 3D                        │
│ 2. Aplicação de materiais e texturas                    │
│ 3. Exportação para SketchUp (.skp)                      │
│ 4. [Opcional] Outros formatos (.obj, .fbx)              │
│                                                         │
│ OUTPUT: arquivo_3d.skp                                  │
└─────────────────────────────────────────────────────────┘
```

---

## Estrutura do JSON Enriquecido

### `projeto.conceito_visual_json`

```json
{
  // ========================================
  // DADOS DA PLANTA (vem de planta_baixa_json)
  // ========================================
  "planta": {
    "tipo_stand": "ponta_ilha",
    "dimensoes_totais": {
      "largura": 11.0,
      "profundidade": 8.0,
      "altura": 3.0,
      "area_total": 88.0
    },
    "areas": [
      {
        "id": "deposito",
        "tipo": "area_apoio",
        "subtipo": "deposito",
        "bbox_norm": {"x": 0.0, "y": 0.0, "w": 0.45, "h": 1.0},
        "geometria": {
          "x": 0.0,
          "y": 0.0,
          "largura": 4.95,
          "profundidade": 8.0,
          "altura": 3.0,
          "area": 39.6
        }
      },
      // ... outras áreas
    ]
  },

  // ========================================
  // DADOS DO BRIEFING
  // ========================================
  "briefing": {
    "objetivo_principal": "aumentar vendas e brand awareness",
    "publico_alvo": "arquitetos e designers de interiores",
    "mensagem_chave": "inovação e sustentabilidade",
    "produtos_destaque": ["linha eco", "linha premium"],
    "atividades": ["demonstrações ao vivo", "consultorias"]
  },

  // ========================================
  // ESTILO VISUAL (vem de inspirações)
  // ========================================
  "estilo": {
    "paleta_cores": {
      "primaria": "#2E7D32",  // verde
      "secundaria": "#FFFFFF", // branco
      "acento": "#FFC107"      // amarelo
    },
    "materiais": ["madeira certificada", "vidro", "metal escovado"],
    "referencias_visuais": [
      {
        "url": "https://...",
        "tipo": "stand_similar",
        "nota": "iluminação e layout"
      }
    ]
  },

  // ========================================
  // ELEMENTOS VISUAIS (ajustável via conversacional)
  // ========================================
  "elementos_visuais": {
    "iluminacao": {
      "tipo": "natural e artificial combinados",
      "destaques": "spot lights nos produtos",
      "ambiente": "warm white (3000K)"
    },
    "mobiliario": {
      "estilo": "moderno minimalista",
      "balcoes": "madeira clara com tampo branco",
      "cadeiras": "design escandinavo"
    },
    "graficos": {
      "tipo": "painel LED interativo",
      "localizacao": "parede de fundo",
      "conteudo": "vídeos de produtos"
    },
    "vegetacao": {
      "tipo": "plantas suspensas",
      "especies": "samambaias e jiboias",
      "quantidade": "moderada"
    },
    "pisos": {
      "material": "porcelanato wood",
      "cor": "bege claro"
    },
    "paredes": {
      "acabamento": "branco acetinado",
      "detalhe": "painel ripado de madeira"
    }
  },

  // ========================================
  // PROMPT DALL-E (gerado automaticamente)
  // ========================================
  "prompt_dalle": "A modern minimalist exhibition booth for an eco-friendly furniture brand, 11m x 8m island stand layout with storage area (4.95m), corridor (1.1m), and workshop area (4.95m). Natural and artificial lighting with warm white spot lights highlighting products. Light wood furniture with white countertops, Scandinavian-style chairs. Interactive LED panel on the back wall showing product videos. Hanging plants (ferns and pothos) suspended from ceiling. Light beige wood-look porcelain tile flooring, white satin walls with wooden slat accent panel. Color palette: forest green (#2E7D32), white (#FFFFFF), yellow accent (#FFC107). Photorealistic architectural visualization, eye-level perspective.",

  // ========================================
  // HISTÓRICO DE AJUSTES
  // ========================================
  "historico_ajustes": [
    {
      "timestamp": "2025-11-09T14:30:00",
      "comando": "adiciona plantas suspensas",
      "campo_modificado": "elementos_visuais.vegetacao",
      "valor_anterior": null,
      "valor_novo": {"tipo": "plantas suspensas", "especies": "samambaias e jiboias"}
    },
    {
      "timestamp": "2025-11-09T14:35:00",
      "comando": "deixa a iluminação mais quente",
      "campo_modificado": "elementos_visuais.iluminacao.ambiente",
      "valor_anterior": "cool white (5000K)",
      "valor_novo": "warm white (3000K)"
    }
  ],

  // ========================================
  // METADADOS
  // ========================================
  "metadata": {
    "versao": "1.0",
    "data_criacao": "2025-11-09T14:00:00",
    "ultima_modificacao": "2025-11-09T14:35:00",
    "imagem_atual": "https://oaidalleapiprodscus.blob.core.windows.net/...",
    "total_regeneracoes": 2
  }
}
```

---

## Fluxo de Implementação

### **Módulo 2: Renderização AI**

#### **Etapa 1: Enriquecimento do JSON**
```python
# gestor/services/conceito_visual_service.py

def enriquecer_json(projeto):
    """
    Combina:
    - planta_baixa_json
    - dados do briefing
    - inspirações visuais

    Retorna: conceito_visual_json inicial
    """
    pass
```

#### **Etapa 2: Geração de Prompt DALL-E**
```python
def gerar_prompt_dalle(conceito_json):
    """
    Usa IA (GPT-4) para criar prompt detalhado:
    - Descreve layout físico
    - Inclui elementos visuais
    - Especifica cores e materiais
    - Define estilo e iluminação

    Retorna: prompt otimizado para DALL-E
    """
    pass
```

#### **Etapa 3: Geração de Imagem**
```python
def gerar_imagem_dalle(prompt):
    """
    Chama API DALL-E 3

    Retorna: URL da imagem
    """
    pass
```

#### **Etapa 4: Ajuste Conversacional**
```python
def interpretar_ajuste(comando, conceito_json):
    """
    Exemplos:
    - "adiciona plantas suspensas"
    - "deixa mais moderno"
    - "troca azul por verde"

    Modifica conceito_json.elementos_visuais

    Retorna: conceito_json modificado
    """
    pass
```

#### **Etapa 5: Regeneração**
```python
def regenerar_conceito(conceito_json):
    """
    1. Regenera prompt com JSON modificado
    2. Gera nova imagem DALL-E
    3. Salva no histórico

    Retorna: novo prompt + nova imagem
    """
    pass
```

---

### **Módulo 3: Modelo 3D**

#### **Etapa 1: Conversão para Geometria**
```python
# gestor/services/modelo_3d_service.py

def converter_para_3d(conceito_json):
    """
    Cria geometrias 3D:
    - Paredes baseadas em bbox_norm
    - Pisos e tetos
    - Mobiliário básico
    - Elementos decorativos

    Retorna: estrutura 3D intermediária
    """
    pass
```

#### **Etapa 2: Aplicar Materiais**
```python
def aplicar_materiais(geometria_3d, conceito_json):
    """
    Aplica:
    - Cores (conceito_json.estilo.paleta_cores)
    - Texturas (conceito_json.estilo.materiais)
    - Iluminação

    Retorna: modelo 3D completo
    """
    pass
```

#### **Etapa 3: Exportar SketchUp**
```python
def exportar_sketchup(modelo_3d, conceito_json):
    """
    Usa biblioteca (ex: IfcOpenShell, ou custom)

    Retorna: bytes do arquivo .skp
    """
    pass
```

---

## Campos Necessários no Modelo

### `projetos/models/projeto.py`

```python
# Adicionar campos:

conceito_visual_json = models.JSONField(
    default=dict, blank=True,
    verbose_name="Conceito Visual Enriquecido"
)

imagem_conceito_url = models.URLField(
    max_length=500, blank=True, null=True,
    verbose_name="URL da Imagem DALL-E"
)

prompt_dalle_atual = models.TextField(
    blank=True, null=True,
    verbose_name="Prompt DALL-E Atual"
)

arquivo_3d = models.FileField(
    upload_to='modelos_3d/', blank=True, null=True,
    verbose_name="Arquivo 3D (SketchUp)"
)
```

---

## Nome do Módulo - Decisão

### Opções:

1. **"Visualização do Stand"** (genérico)
2. **"Renderização e Modelo 3D"** (técnico)
3. **"Imagem e 3D do Stand"** (direto) ✅ Sugestão do usuário
4. **"Conceito Visual e 3D"** (mantém parte do nome atual)

### Recomendação:

**"Visualização do Stand"** com 2 sub-etapas:
- Etapa 1: Renderização AI (DALL-E)
- Etapa 2: Modelo 3D (SketchUp)

Ou separar em 2 módulos independentes:
- Módulo 2: **"Renderização AI"**
- Módulo 3: **"Modelo 3D"**

---

## Próximos Passos

### Prioridade 1: Renderização AI
- [ ] Criar `gestor/services/conceito_visual_service.py`
- [ ] Implementar enriquecimento do JSON
- [ ] Implementar geração de prompt DALL-E
- [ ] Implementar chamada API DALL-E
- [ ] Criar interface (template + view)
- [ ] Implementar ajuste conversacional
- [ ] Salvar conceito_visual_json no banco

### Prioridade 2: Modelo 3D
- [ ] Pesquisar bibliotecas Python para SketchUp
- [ ] Criar `gestor/services/modelo_3d_service.py`
- [ ] Implementar conversão JSON → 3D
- [ ] Implementar exportação .skp
- [ ] Criar interface de download

---

**Decisão Pendente:** Nome final do módulo (aguardando confirmação)
