# Progresso: Módulo 3 - Modelo 3D

**Data:** 09/11/2025
**Status:** 📋 Planejamento

---

## Visão Geral

Módulo responsável por converter o JSON enriquecido (da Renderização AI) em um modelo 3D exportável para SketchUp (.skp).

---

## ✅ Implementado (Estrutura Básica)

### 1. Views
**Arquivo:** `gestor/views/modelo_3d.py`

- `modelo_3d_wizard()` - Tela principal (placeholder)
- `modelo_3d_gerar()` - Endpoint de geração (retorna "não implementado")

### 2. Template
**Arquivo:** `templates/gestor/modelo_3d_wizard.html`

- Interface wizard
- Roadmap de implementação
- Mensagem informativa de "em desenvolvimento"

### 3. URLs
**Arquivo:** `gestor/urls.py`

- `/projeto/<id>/modelo-3d/` - Wizard
- `/projeto/<id>/modelo-3d/gerar/` - Geração

### 4. Link na Interface
**Arquivo:** `templates/gestor/projeto_detail.html`

- Botão "Modelo 3D" (só aparece se renderização AI foi processada)

---

## ⏳ Próximos Passos (Implementação Real)

### 1. Pesquisar Bibliotecas Python

Opções a investigar:

#### A. **IfcOpenShell** (IFC → SketchUp)
```python
# Vantagens:
# - Padrão BIM (IFC)
# - Compatível com SketchUp (via plugins)
# - Geometria paramétrica

# Desvantagens:
# - Curva de aprendizado
# - Requer plugin no SketchUp
```

#### B. **py3dmol** (Visualização 3D)
```python
# Vantagens:
# - Visualização web 3D
# - Fácil integração

# Desvantagens:
# - Não gera .skp diretamente
```

#### C. **OBJ/FBX Export** (Formato Intermediário)
```python
# Vantagens:
# - Formato universal
# - SketchUp importa OBJ

# Desvantagens:
# - Perde metadados
# - Precisa conversão manual
```

#### D. **API Ruby do SketchUp** (Direto)
```python
# Vantagens:
# - Controle total
# - Arquivo .skp nativo

# Desvantagens:
# - Requer SketchUp instalado (ou SDK)
# - Complexo de integrar
```

**Decisão Recomendada:** Começar com **OBJ export** (mais simples) e evoluir para IFC/SketchUp API.

---

### 2. Criar Service de Conversão

**Arquivo:** `gestor/services/modelo_3d_service.py`

```python
class Modelo3DService:
    def __init__(self, projeto):
        self.projeto = projeto
        self.conceito_json = projeto.renderizacao_ai_json

    def gerar_modelo_3d(self):
        """
        Converte JSON → Modelo 3D

        Etapas:
        1. Extrair geometrias do JSON (áreas)
        2. Criar malha 3D (vértices, faces)
        3. Aplicar materiais
        4. Exportar para .skp (ou .obj)
        """
        pass

    def _criar_geometria_area(self, area):
        """Converte área do JSON em geometria 3D"""
        pass

    def _aplicar_materiais(self, geometria):
        """Aplica cores e texturas"""
        pass

    def _exportar_skp(self, geometria):
        """Exporta para formato SketchUp"""
        pass
```

---

### 3. Estrutura do JSON (Entrada)

O JSON enriquecido (`projeto.renderizacao_ai_json`) contém:

```json
{
  "planta": {
    "tipo_stand": "ponta_ilha",
    "dimensoes_totais": {
      "largura": 11.0,
      "profundidade": 8.0,
      "altura": 3.0
    },
    "areas": [
      {
        "id": "deposito",
        "tipo": "area_apoio",
        "bbox_norm": {"x": 0.0, "y": 0.0, "w": 0.45, "h": 1.0},
        "geometria": {
          "x": 0.0,
          "y": 0.0,
          "largura": 4.95,
          "profundidade": 8.0,
          "altura": 3.0,
          "area": 39.6
        }
      }
    ]
  },
  "estilo": {
    "paleta_cores": {
      "primaria": "#2E7D32",
      "secundaria": "#FFFFFF",
      "acento": "#FFC107"
    },
    "materiais": ["madeira", "vidro", "metal"]
  },
  "elementos_visuais": {
    "pisos": {"material": "porcelanato wood"},
    "paredes": {"acabamento": "branco acetinado"}
  }
}
```

---

### 4. Conversão JSON → 3D (Pseudocódigo)

```python
def gerar_modelo_3d(conceito_json):
    # 1. Extrair dimensões totais
    largura = conceito_json['planta']['dimensoes_totais']['largura']
    profundidade = conceito_json['planta']['dimensoes_totais']['profundidade']
    altura = conceito_json['planta']['dimensoes_totais']['altura']

    # 2. Criar base (piso)
    piso = criar_retangulo_3d(0, 0, 0, largura, profundidade)
    aplicar_material(piso, conceito_json['elementos_visuais']['pisos'])

    # 3. Criar paredes para cada área
    for area in conceito_json['planta']['areas']:
        x = area['geometria']['x']
        y = area['geometria']['y']
        w = area['geometria']['largura']
        d = area['geometria']['profundidade']
        h = area['geometria']['altura']

        # Criar caixa 3D (paredes)
        parede = criar_caixa_3d(x, y, 0, w, d, h)
        aplicar_material(parede, conceito_json['estilo']['paleta_cores'])

    # 4. Exportar para .skp
    exportar_para_sketchup('modelo.skp')
```

---

### 5. Bibliotecas Necessárias

```bash
# Opção 1: OBJ Export (mais simples)
pip install trimesh
pip install numpy

# Opção 2: IFC (BIM)
pip install ifcopenshell

# Opção 3: Visualização Web (opcional)
pip install py3dmol
```

---

## 🎯 Checklist de Implementação

- [x] Criar estrutura básica (views, template, URLs)
- [x] Adicionar link no projeto_detail
- [ ] Pesquisar e escolher biblioteca 3D
- [ ] Instalar dependências
- [ ] Criar `modelo_3d_service.py`
  - [ ] `gerar_modelo_3d()`
  - [ ] `_criar_geometria_area()`
  - [ ] `_aplicar_materiais()`
  - [ ] `_exportar_skp()` ou `_exportar_obj()`
- [ ] Implementar conversão JSON → geometria 3D
- [ ] Implementar aplicação de materiais/cores
- [ ] Implementar exportação para formato
- [ ] Atualizar view `modelo_3d_gerar()`
- [ ] Atualizar template com resultado real
- [ ] Testar importação no SketchUp
- [ ] Documentar processo de importação

---

## 📊 Campos no Banco (já existem)

```python
# projetos/models/projeto.py

arquivo_3d = models.FileField(
    upload_to='modelos_3d/', blank=True, null=True,
    storage=MinioStorage(),
    verbose_name="Arquivo 3D (SketchUp)",
    help_text="Modelo 3D exportado (.skp)"
)

modelo_3d_processado = models.BooleanField(
    default=False,
    verbose_name="Modelo 3D Processado"
)

data_modelo_3d = models.DateTimeField(
    blank=True, null=True,
    verbose_name="Data de Geração do Modelo 3D"
)
```

---

## 🚀 Estratégia de Implementação

### Fase 1: MVP (OBJ Export)
1. Usar **trimesh** para criar geometria básica
2. Exportar em formato .OBJ
3. Usuário importa manualmente no SketchUp

### Fase 2: Refinamento
1. Adicionar materiais e texturas
2. Melhorar geometria (arredondamentos, detalhes)
3. Suporte a mobiliário básico

### Fase 3: SketchUp Nativo (futuro)
1. Integrar com API Ruby do SketchUp
2. Gerar .skp diretamente
3. Incluir layers e componentes

---

**Próxima ação:** Pesquisar e testar bibliotecas Python para geração 3D
