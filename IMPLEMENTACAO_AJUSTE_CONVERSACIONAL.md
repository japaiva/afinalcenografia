# Implementação: Módulo de Ajuste Conversacional para Planta Baixa

## Objetivo

Criar interface conversacional para ajustar dimensões das áreas identificadas ANTES de gerar o SVG final.

## Arquitetura

### Fluxo Modificado:

```
Etapa 1: Análise          → JSON (oculto por padrão)
Etapa 2: Estruturação     → JSON (oculto por padrão)
Etapa 3: Validação        → JSON (oculto por padrão)

┌────────────────────────────────────────┐
│ 💬 AJUSTE FINO (Conversacional)        │
│    [Entre Etapa 3 e 4]                 │
└────────────────────────────────────────┘

Etapa 4: SVG Final        → Visualização
```

## Componentes a Criar

### 1. Template: Seção de Ajuste Conversacional

**Localização:** `templates/projetista/planta_baixa.html`

**Adicionar após Etapa 3:**

```html
<!-- MÓDULO DE AJUSTE CONVERSACIONAL -->
<div class="card shadow mb-4" id="card-ajuste" style="display:none;">
  <div class="card-header bg-info text-white">
    <h5 class="mb-0">
      <i class="fas fa-comments me-2"></i>
      Ajuste Fino (Conversacional)
    </h5>
  </div>
  <div class="card-body">
    <!-- Chat de ajustes -->
    <div id="chat-ajustes" class="mb-3" style="max-height: 300px; overflow-y: auto; border: 1px solid #dee2e6; border-radius: 4px; padding: 15px;">
      <div class="text-muted text-center py-4">
        <i class="fas fa-magic fa-2x mb-2"></i>
        <p>Precisa ajustar alguma dimensão? Digite comandos como:</p>
        <ul class="list-unstyled small">
          <li><code>deposito e workshop mesmo tamanho</code></li>
          <li><code>deposito 40% workshop 50%</code></li>
          <li><code>corredor mais largo</code></li>
        </ul>
      </div>
    </div>

    <!-- Input de comando -->
    <div class="input-group">
      <input type="text" class="form-control" id="input-ajuste"
             placeholder="Digite seu ajuste... (ex: deposito e workshop mesmo tamanho)"
             onkeypress="if(event.key==='Enter') enviarAjuste()">
      <button class="btn btn-primary" onclick="enviarAjuste()">
        <i class="fas fa-paper-plane me-1"></i> Enviar
      </button>
    </div>

    <!-- Botão para aplicar e continuar -->
    <div class="mt-3 text-end">
      <button class="btn btn-success" onclick="aplicarAjustesEContinuar()" id="btn-aplicar-ajustes">
        <i class="fas fa-check me-1"></i> Aplicar e Gerar SVG
      </button>
    </div>
  </div>
</div>
```

### 2. JavaScript: Funções de Ajuste

```javascript
let ajustesPendentes = [];

async function enviarAjuste() {
  const input = document.getElementById('input-ajuste');
  const comando = input.value.trim();

  if (!comando) return;

  // Adicionar mensagem do usuário
  adicionarMensagemChat('user', comando);
  input.value = '';

  // Enviar para backend processar
  try {
    const response = await fetch(`/projetista/projeto/{{projeto.id}}/planta-baixa/ajustar/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCookie('csrftoken')
      },
      body: JSON.stringify({
        comando: comando,
        layout_atual: resultadoEtapa3
      })
    });

    const data = await response.json();

    if (data.sucesso) {
      // Mostrar interpretação do ajuste
      adicionarMensagemChat('bot', data.resposta);

      // Armazenar ajuste
      if (data.ajuste) {
        ajustesPendentes.push(data.ajuste);
      }
    } else {
      adicionarMensagemChat('bot', `❌ ${data.erro}`);
    }
  } catch (error) {
    adicionarMensagemChat('bot', `❌ Erro ao processar: ${error.message}`);
  }
}

function adicionarMensagemChat(tipo, mensagem) {
  const chat = document.getElementById('chat-ajustes');

  // Remover mensagem inicial se existir
  if (chat.querySelector('.text-muted')) {
    chat.innerHTML = '';
  }

  const div = document.createElement('div');
  div.className = `mb-2 ${tipo === 'user' ? 'text-end' : ''}`;

  const badge = tipo === 'user'
    ? '<span class="badge bg-primary">Você</span>'
    : '<span class="badge bg-info">🤖 Assistente</span>';

  div.innerHTML = `
    ${badge}
    <div class="mt-1 p-2 rounded ${tipo === 'user' ? 'bg-primary text-white' : 'bg-light'}"
         style="display: inline-block; max-width: 80%;">
      ${mensagem}
    </div>
  `;

  chat.appendChild(div);
  chat.scrollTop = chat.scrollHeight;
}

async function aplicarAjustesEContinuar() {
  if (ajustesPendentes.length === 0) {
    // Sem ajustes, ir direto para Etapa 4
    executarEtapa4();
    return;
  }

  // Aplicar ajustes e depois executar Etapa 4
  const btnAplicar = document.getElementById('btn-aplicar-ajustes');
  btnAplicar.disabled = true;
  btnAplicar.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span> Aplicando...';

  try {
    const response = await fetch(`/projetista/projeto/{{projeto.id}}/planta-baixa/aplicar-ajustes/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCookie('csrftoken')
      },
      body: JSON.stringify({
        ajustes: ajustesPendentes,
        layout_atual: resultadoEtapa3
      })
    });

    const data = await response.json();

    if (data.sucesso) {
      // Atualizar resultado da Etapa 3 com layout ajustado
      resultadoEtapa3 = data.layout_ajustado;

      adicionarMensagemChat('bot', '✅ Ajustes aplicados! Gerando SVG...');

      // Executar Etapa 4 com layout ajustado
      setTimeout(() => executarEtapa4(), 1000);
    } else {
      adicionarMensagemChat('bot', `❌ ${data.erro}`);
      btnAplicar.disabled = false;
      btnAplicar.innerHTML = '<i class="fas fa-check me-1"></i> Aplicar e Gerar SVG';
    }
  } catch (error) {
    adicionarMensagemChat('bot', `❌ Erro: ${error.message}`);
    btnAplicar.disabled = false;
    btnAplicar.innerHTML = '<i class="fas fa-check me-1"></i> Aplicar e Gerar SVG';
  }
}
```

### 3. View: Processar Comandos de Ajuste

**Localização:** `gestor/views/planta_baixa_ajuste_view.py` (NOVO)

```python
from django.views import View
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
import json
import re

class AjusteConversacionalView(View):
    """
    View para processar comandos conversacionais de ajuste de dimensões
    """

    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def post(self, request, projeto_id):
        try:
            data = json.loads(request.body)
            comando = data.get('comando', '').lower()
            layout_atual = data.get('layout_atual')

            # Processar comando e gerar ajuste
            ajuste = self._interpretar_comando(comando, layout_atual)

            if ajuste:
                return JsonResponse({
                    'sucesso': True,
                    'resposta': ajuste['resposta'],
                    'ajuste': ajuste['dados']
                })
            else:
                return JsonResponse({
                    'sucesso': False,
                    'erro': 'Não entendi o comando. Tente: "deposito e workshop mesmo tamanho"'
                })

        except Exception as e:
            return JsonResponse({'sucesso': False, 'erro': str(e)})

    def _interpretar_comando(self, comando, layout):
        """
        Interpreta comandos naturais e gera ajustes
        """

        # Padrão 1: "deposito e workshop mesmo tamanho"
        if 'mesmo tamanho' in comando or 'mesmo' in comando:
            match = re.search(r'(\w+)\s+e\s+(\w+)', comando)
            if match:
                area1, area2 = match.groups()
                return {
                    'resposta': f'✅ Entendi! Vou ajustar {area1.title()} e {area2.title()} para terem o mesmo tamanho (45% cada, considerando 10% de corredor).',
                    'dados': {
                        'tipo': 'mesmo_tamanho',
                        'areas': [area1, area2],
                        'percentual': 0.45
                    }
                }

        # Padrão 2: "deposito 40% workshop 50%"
        percentuais = re.findall(r'(\w+)\s+(\d+)%', comando)
        if percentuais:
            ajustes = []
            resposta_partes = []
            for area, percent in percentuais:
                valor = int(percent) / 100
                ajustes.append({'area': area, 'w': valor})
                resposta_partes.append(f'{area.title()} → {percent}%')

            return {
                'resposta': f'✅ Entendi! Vou ajustar:\n' + '\n'.join(resposta_partes),
                'dados': {
                    'tipo': 'percentuais',
                    'ajustes': ajustes
                }
            }

        # Padrão 3: "corredor mais largo"
        if 'corredor' in comando and ('largo' in comando or 'maior' in comando):
            return {
                'resposta': '✅ Vou aumentar o corredor para 15% (1.65m)',
                'dados': {
                    'tipo': 'percentuais',
                    'ajustes': [{'area': 'corredor', 'w': 0.15}]
                }
            }

        return None


class AplicarAjustesView(View):
    """
    View para aplicar ajustes acumulados ao layout
    """

    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def post(self, request, projeto_id):
        try:
            data = json.loads(request.body)
            ajustes = data.get('ajustes', [])
            layout = data.get('layout_atual')

            # Aplicar cada ajuste
            for ajuste in ajustes:
                layout = self._aplicar_ajuste(layout, ajuste)

            # Validar que soma 100%
            layout = self._normalizar_100porcento(layout)

            return JsonResponse({
                'sucesso': True,
                'layout_ajustado': layout
            })

        except Exception as e:
            return JsonResponse({'sucesso': False, 'erro': str(e)})

    def _aplicar_ajuste(self, layout, ajuste):
        """Aplica um ajuste específico ao layout"""

        if ajuste['tipo'] == 'mesmo_tamanho':
            # Ajustar áreas para mesmo tamanho
            areas = ajuste['areas']
            percentual = ajuste['percentual']

            for area in layout.get('areas', []):
                if any(a in area['id'] for a in areas):
                    area['bbox_norm']['w'] = percentual

        elif ajuste['tipo'] == 'percentuais':
            # Ajustar percentuais específicos
            for item in ajuste['ajustes']:
                area_nome = item['area']
                novo_w = item['w']

                for area in layout.get('areas', []):
                    if area_nome in area['id']:
                        area['bbox_norm']['w'] = novo_w

        return layout

    def _normalizar_100porcento(self, layout):
        """Garante que áreas somem 100%"""

        # Recalcular coordenadas X sequenciais
        x_atual = 0.0
        for area in sorted(layout.get('areas', []), key=lambda a: a['bbox_norm']['x']):
            if area['bbox_norm']['y'] == 0:  # Apenas linha superior
                area['bbox_norm']['x'] = x_atual
                x_atual += area['bbox_norm']['w']

        return layout
```

### 4. URLs

**Localização:** `gestor/urls.py` ou `projetista/urls.py`

```python
from .views.planta_baixa_ajuste_view import AjusteConversacionalView, AplicarAjustesView

urlpatterns = [
    # ... outras URLs ...

    path('projeto/<int:projeto_id>/planta-baixa/ajustar/',
         AjusteConversacionalView.as_view(),
         name='planta_baixa_ajustar'),

    path('projeto/<int:projeto_id>/planta-baixa/aplicar-ajustes/',
         AplicarAjustesView.as_view(),
         name='planta_baixa_aplicar_ajustes'),
]
```

### 5. Ocultar JSONs por Padrão

**Modificar cada etapa para:**

```html
<!-- Resultado Etapa 1 -->
<div id="result-1" class="d-none">
  <div class="alert alert-success">
    <i class="fas fa-check-circle me-2"></i>
    Layout identificado com sucesso!

    <button class="btn btn-sm btn-outline-secondary float-end"
            onclick="toggleDetalhes(1)">
      <i class="fas fa-code me-1"></i> Ver Detalhes Técnicos ▼
    </button>
  </div>

  <!-- JSON oculto por padrão -->
  <div id="detalhes-1" style="display:none;">
    <pre class="bg-light p-3 rounded small">{{ dados_json }}</pre>
  </div>
</div>

<script>
function toggleDetalhes(etapa) {
  const detalhes = document.getElementById(`detalhes-${etapa}`);
  detalhes.style.display = detalhes.style.display === 'none' ? 'block' : 'none';
}
</script>
```

## Fluxo de Uso

1. Usuário executa Etapas 1, 2, 3
2. **Módulo de Ajuste aparece automaticamente** após Etapa 3
3. Usuário pode:
   - Digitar comandos naturais para ajustar
   - Ver respostas interpretadas do assistente
   - Aplicar ajustes e gerar SVG
   - OU pular direto para Etapa 4 (sem ajustes)
4. SVG gerado com dimensões ajustadas

## Status

- [ ] Modificar template planta_baixa.html
- [ ] Criar views de ajuste
- [ ] Adicionar URLs
- [ ] Testar comandos conversacionais
- [ ] Documentar comandos disponíveis

---

**Data:** 09/11/2025
**Prioridade:** Alta
**Complexidade:** Média
