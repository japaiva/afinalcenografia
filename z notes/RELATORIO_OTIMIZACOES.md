# Relatório de Otimizações Arquiteturais
**Data:** 09/11/2025
**Projeto:** AFinal Cenografia

## 📊 Análise Estrutural

### Estrutura de Apps
```
afinal_cenografia/    # Settings e configuração
├── api/              # REST API
├── cliente/          # Portal do cliente (806 linhas briefing.py)
├── core/             # Funcionalidades core (RAG, Agentes)
├── gestor/           # Portal do gestor
├── projetista/       # Portal do projetista
├── projetos/         # Models centrais (Projeto, Briefing)
└── storage/          # Gestão de arquivos MinIO
```

### Métricas de Código
- **Total de linhas Python:** ~50.000
- **Arquivos maiores:**
  - `gestor/views/agents_crews.py`: 991 linhas ⚠️
  - `core/services/qa_generator.py`: 828 linhas
  - `cliente/views/briefing.py`: 806 linhas
  - `projetos/views/briefing_views.py`: 772 linhas ⚠️ **DUPLICADO**

---

## 🔴 PROBLEMAS CRÍTICOS

### 1. **Código Duplicado de Briefing** ⚠️⚠️⚠️

**Problema:**
Existem DUAS implementações de briefing:
- `cliente/views/briefing.py` (806 linhas) - Versão principal atual
- `projetos/views/briefing_views.py` (772 linhas) - Versão antiga/alternativa

**Evidência:**
```python
# cliente/urls.py
from cliente.views import briefing as briefing_views  # Versão atual
from projetos.views.briefing_views import (           # Versão antiga (3 funções)
    limpar_conversas_briefing,
    perguntar_manual,
    enviar_mensagem_ia
)
```

**Impacto:**
- ❌ Confusão sobre qual versão usar
- ❌ Manutenção duplicada
- ❌ Risco de bugs (alteração em um lugar, esquecimento no outro)
- ❌ +772 linhas desnecessárias

**Solução:**
1. Mover as 3 funções de `projetos/views/briefing_views.py` para `cliente/views/briefing.py`
2. Deletar `projetos/views/briefing_views.py`
3. Atualizar imports em `cliente/urls.py`

---

### 2. **CrewAI Não Utilizado** ⚠️⚠️

**Problema:**
- 991 linhas de CRUD de Crews em `gestor/views/agents_crews.py`
- Models `Crew`, `CrewMembro`, `CrewTask`, `CrewExecucao` no banco
- **NÃO está sendo usado** no fluxo principal

**Evidência:**
```python
# Conceito Visual NÃO usa CrewAI:
✓ Etapa 1: Agente individual "Analisador de Esboços"
✓ Etapa 2: Agente individual "Analisador de Referências"
✓ Etapa 3: DALL-E direto

# PlantaBaixaServiceV2 existe mas NÃO está nas views ativas
```

**Impacto:**
- ❌ 991 linhas de código não usado
- ❌ Dependências pesadas (crewai==0.140.0, crewai-tools, langchain-*)
- ❌ Tabelas no banco ocupando espaço
- ❌ Confusão sobre arquitetura

**Decisão já tomada:**
✅ MANTER por enquanto (discussão anterior)
❌ Não adicionar ao fluxo de Planta Baixa (usar agentes sequenciais)

---

### 3. **Separação Inconsistente de Lógica** ⚠️

**Problema:**
Lógica de negócio misturada entre views e services.

**Exemplo - Conceito Visual:**
```python
# gestor/views/conceito_visual.py (460 linhas)
def gerar_prompt_completo(projeto: Projeto, ...) -> str:
    """148 linhas de lógica dentro da VIEW!"""
    # Deveria estar em gestor/services/conceito_visual_service.py
```

**Comparação:**
```
✅ BOM:  projetos/services/briefing_areas_processor.py (217 linhas)
        Lógica isolada, testável, reutilizável

❌ RUIM: gestor/views/conceito_visual.py
        Função gerar_prompt_completo() dentro da view
```

**Solução:**
Mover `gerar_prompt_completo()` para `gestor/services/conceito_visual_service.py`

---

## 🟡 PROBLEMAS MODERADOS

### 4. **Falta de Paginação em Listas**

**Problema:**
Listas sem paginação podem causar problemas com muitos registros.

**Verificar:**
```python
# gestor/views/projeto.py
projetos = Projeto.objects.all()  # Sem .order_by() ou paginação
```

**Solução:**
```python
from django.core.paginator import Paginator

projetos = Projeto.objects.select_related('empresa', 'feira').order_by('-created_at')
paginator = Paginator(projetos, 25)
```

---

### 5. **Queries N+1 Potenciais**

**Problema:**
Acesso a ForeignKey sem `select_related()` ou `prefetch_related()`.

**Exemplo hipotético:**
```python
# ❌ RUIM
projetos = Projeto.objects.all()
for projeto in projetos:
    print(projeto.empresa.nome)  # N+1 query!
    print(projeto.feira.nome)     # N+1 query!

# ✅ BOM
projetos = Projeto.objects.select_related('empresa', 'feira').all()
for projeto in projetos:
    print(projeto.empresa.nome)  # Já carregado
    print(projeto.feira.nome)     # Já carregado
```

**Ação:**
Auditoria manual ou usar Django Debug Toolbar para identificar.

---

### 6. **Campos JSON Sem Validação**

**Problema:**
Campos JSONField sem schema definido.

**Exemplo:**
```python
# projetos/models/projeto.py
layout_identificado = models.JSONField(null=True, blank=True)
inspiracoes_visuais = models.JSONField(null=True, blank=True)
```

**Risco:**
- Dados inconsistentes
- Erros em runtime ao acessar chaves
- Dificulta manutenção

**Solução:**
```python
from django.core.exceptions import ValidationError
import jsonschema

LAYOUT_SCHEMA = {
    "type": "object",
    "properties": {
        "areas": {"type": "array"},
        "acessos": {"type": "object"},
        "tipo_estande": {"type": "string"}
    },
    "required": ["areas"]
}

def validar_layout(value):
    try:
        jsonschema.validate(value, LAYOUT_SCHEMA)
    except jsonschema.ValidationError as e:
        raise ValidationError(f"JSON inválido: {e.message}")

class Projeto(models.Model):
    layout_identificado = models.JSONField(
        null=True,
        blank=True,
        validators=[validar_layout]
    )
```

---

## 🟢 OTIMIZAÇÕES RECOMENDADAS

### 7. **Implementar Caching**

**Redis** para dados frequentemente acessados:

```python
# Adicionar ao settings.py
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}

# Usar em views:
from django.views.decorators.cache import cache_page

@cache_page(60 * 15)  # 15 minutos
def projeto_list(request):
    ...
```

---

### 8. **Consolidar Serviços de Imagem**

**Problema:**
Múltiplos serviços fazendo coisas similares:

```
gestor/services/
├── conceito_visual_dalle.py      # Gera imagens
├── dalle_service.py               # Gera imagens
└── agente_service.py              # Executa agentes (alguns geram imagens)
```

**Solução:**
Criar `core/services/image_generation_service.py` unificado.

---

### 9. **Adicionar Índices no Banco**

```python
class Projeto(models.Model):
    class Meta:
        indexes = [
            models.Index(fields=['empresa', '-created_at']),
            models.Index(fields=['status']),
            models.Index(fields=['feira']),
        ]

class Briefing(models.Model):
    class Meta:
        indexes = [
            models.Index(fields=['projeto', '-updated_at']),
            models.Index(fields=['status']),
        ]
```

---

### 10. **Async Views para Processos Longos**

**Problema:**
Geração de imagens/PDFs bloqueia o request.

**Solução:**
```python
# Usar Celery para tasks assíncronas
from celery import shared_task

@shared_task
def gerar_conceito_visual_async(projeto_id):
    # Processamento longo
    ...

# Na view:
def conceito_etapa3(request, projeto_id):
    task = gerar_conceito_visual_async.delay(projeto_id)
    return JsonResponse({'task_id': task.id})
```

---

## 📋 PLANO DE AÇÃO PRIORITÁRIO

### Fase 1: Limpeza (2-3 horas) 🔥
1. ✅ **Consolidar briefing** (mover 3 funções, deletar arquivo duplicado)
2. ✅ **Mover gerar_prompt_completo()** para service
3. ✅ **Adicionar docstrings** em services principais

### Fase 2: Performance (1-2 horas) ⚡
4. ✅ **Adicionar select_related/prefetch_related** nas views principais
5. ✅ **Adicionar índices** nos models
6. ✅ **Implementar paginação** nas listas

### Fase 3: Robustez (2-3 horas) 🛡️
7. ✅ **Validação de JSON** com schemas
8. ✅ **Testes unitários** para services críticos
9. ✅ **Logging estruturado** (já iniciado)

### Fase 4: Escalabilidade (opcional) 🚀
10. ⏸️ **Redis caching**
11. ⏸️ **Celery para tasks longas**
12. ⏸️ **Django Debug Toolbar** (apenas dev)

---

## ✅ O QUE JÁ ESTÁ BOM

1. ✅ **Separação de apps clara** (cliente, gestor, projetista)
2. ✅ **Models centralizados** em `projetos/`
3. ✅ **Storage MinIO** configurado
4. ✅ **RAG/Pinecone** funcionando
5. ✅ **Decorators de permissão** (`@cliente_required`, `@gestor_required`)
6. ✅ **Briefing refatorado** com `BriefingAreasProcessor`
7. ✅ **Logs estruturados** (DEBUG mode)

---

## 🎯 RECOMENDAÇÃO FINAL

**ANTES de implementar Planta Baixa:**

### Crítico (fazer AGORA):
1. ✅ Consolidar código duplicado de briefing
2. ✅ Mover lógica de views para services

### Importante (fazer logo):
3. ✅ Adicionar select_related nas views principais
4. ✅ Validar JSONFields com schemas

### Nice-to-have (depois):
5. ⏸️ Implementar caching
6. ⏸️ Async tasks com Celery

---

**Tempo estimado para Fase 1 + Fase 2:** ~4 horas
**Impacto:** 🚀 Alto (código mais limpo, manutenível e performático)

**Decisão:** Executar Fases 1 e 2 ANTES da Planta Baixa? ✅ SIM / ❌ NÃO
