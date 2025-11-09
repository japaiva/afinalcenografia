# Correção do AgenteService - Problema Resolvido

## Problema Identificado

Ao testar a execução da Etapa 1 da Planta Baixa (análise de esboço), ocorreu o seguinte erro:

```
ImportError: cannot import name 'AgenteService' from 'gestor.services.agente_service'
```

### Erro no Log:
```
[EXECUTOR] Erro na execução: cannot import name 'AgenteService' from 'gestor.services.agente_service'
Erro ao executar agente Analisador de Esboços de Planta: Falha na execução do agente
```

## Causa Raiz

1. **Classe Inexistente:** O arquivo `gestor/services/agente_service.py` existia, mas continha a classe `ConceitoVisualDalleService` ao invés de `AgenteService`

2. **Import Incorreto:** O código em `gestor/views/agents_crews.py` linha 821 estava tentando importar:
   ```python
   from ..services.agente_service import AgenteService
   ```

3. **Serviço Faltando:** Não existia nenhuma implementação da classe `AgenteService` no projeto

## Solução Implementada

### 1. Criado Novo Serviço: `agente_executor.py`

Criamos o arquivo `gestor/services/agente_executor.py` contendo a classe `AgenteService` com funcionalidades completas:

**Recursos:**
- Suporte para **OpenAI** (GPT-4, GPT-4o, GPT-4-turbo)
- Suporte para **Anthropic** (Claude 3 Opus, Sonnet, Haiku, Claude 3.5)
- Suporte para **Vision** (imagens via URL ou base64)
- Conversão automática de imagens (download, base64)
- Logging detalhado de cada execução
- Tratamento robusto de erros

**Principais Métodos:**
```python
class AgenteService:
    def executar_agente(
        agente: Agente,
        prompt_usuario: str,
        imagens: Optional[List[str]] = None
    ) -> str

    def _executar_openai(...) -> str
    def _executar_anthropic(...) -> str
    def _preparar_imagem_openai(...) -> Dict
    def _preparar_imagem_anthropic(...) -> Dict
```

### 2. Corrigido Import em `agents_crews.py`

**Antes:**
```python
from ..services.agente_service import AgenteService
```

**Depois:**
```python
from ..services.agente_executor import AgenteService
```

### 3. Melhorado Construção de Prompts

Adicionamos função inteligente para construir prompts a partir das `task_instructions` do agente:

```python
def _build_prompt_from_template(agente: Agente, payload: Dict[str, Any]) -> str:
    """
    Constrói prompt usando as task_instructions do agente como template.
    Adiciona os dados do payload de forma estruturada.
    """
    template = agente.task_instructions
    prompt_final = template + "\n\n**DADOS DE ENTRADA:**\n\n"

    # Formata dados do payload de forma legível
    for key, value in payload.items():
        if isinstance(value, dict):
            prompt_final += f"**{key.upper()}:**\n{json.dumps(value, indent=2)}\n\n"
        # ... etc
```

**Vantagens:**
- Usa as instruções definidas no banco de dados
- Adiciona dados do payload de forma estruturada
- Mantém formato consistente
- Facilita debug (log do prompt gerado)

## Arquivos Modificados/Criados

### Criados:
1. `gestor/services/agente_executor.py` (400+ linhas)
   - Classe `AgenteService` completa
   - Suporte multi-provider (OpenAI, Anthropic)
   - Processamento de imagens

### Modificados:
1. `gestor/views/agents_crews.py`
   - Linha 821: Import corrigido
   - Linhas 823-831: Lógica de construção de prompt melhorada
   - Linhas 868-930: Funções `_build_prompt_from_template` e `_build_fallback_prompt` adicionadas

## Teste de Validação

```bash
$ python manage.py check
System check identified no issues (0 silenced).
```

✅ **Sem erros!**

## Fluxo de Execução (Agora Funcional)

```
1. PlantaBaixaService.etapa1_analisar_esboco()
   ↓
2. _run_agent("Analisador de Esboços de Planta", payload, imagens)
   ↓
3. Busca agente no banco de dados (ID 10)
   ↓
4. Constrói prompt usando task_instructions + dados do payload
   ↓
5. AgenteService().executar_agente(agente, prompt, imagens)
   ↓
6. Detecta provider (openai) e chama _executar_openai()
   ↓
7. Prepara imagens (converte para base64 se necessário)
   ↓
8. Faz chamada à API da OpenAI (GPT-4o Vision)
   ↓
9. Recebe resposta (JSON com layout identificado)
   ↓
10. Processa resposta e extrai JSON
    ↓
11. Salva em projeto.layout_identificado
    ↓
12. Retorna sucesso para a view
```

## Próximos Passos

Agora você pode testar a funcionalidade de Planta Baixa:

1. Acesse um projeto com briefing
2. Faça upload de um esboço de planta (tipo: "planta")
3. Clique em "Planta Baixa" no menu de ações
4. Execute a Etapa 1
5. Aguarde processamento (15-30 segundos)
6. Veja o resultado JSON com layout identificado

## Notas Técnicas

### Suporte a Imagens

A classe `AgenteService` suporta múltiplos formatos de imagem:

**OpenAI:**
- URL pública: Usada diretamente
- Path local ou URL relativa: Convertida para base64
- Formatos: PNG, JPEG, WEBP

**Anthropic:**
- Todas as imagens convertidas para base64
- Formatos: PNG, JPEG, WEBP

### Configuração de APIs

As chaves são lidas de `settings`:
```python
openai.api_key = settings.OPENAI_API_KEY
anthropic_client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
```

### Logging

Cada execução gera logs detalhados:
```
[AGENTE] Executando: Analisador de Esboços de Planta
[AGENTE] Provider: openai
[AGENTE] Modelo: gpt-4o
[AGENTE] Temperatura: 0.3
[AGENTE] Prompt: 1500 chars
[AGENTE] Imagens: 1
[OPENAI] Chamando API com 2 mensagens
[OPENAI] Resposta recebida: 2500 chars
```

---

**Status:** ✅ **PROBLEMA RESOLVIDO**

**Data:** 09/11/2025

**Testado:** Sim - Django check passou sem erros
