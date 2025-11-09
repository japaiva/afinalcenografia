#!/usr/bin/env python
"""
Script para corrigir as task_instructions do Agente 9 (Renderizador SVG).
Uso: python corrigir_agente_svg.py
"""

import os
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'afinal_cenografia.settings')
django.setup()

from core.models import Agente

def atualizar_agente_9():
    """Atualiza task_instructions do Agente 9 com instruções corretas"""

    task_instructions = """Gere uma representação SVG profissional da planta baixa estruturada.

**ENTRADA ESPERADA:**
Você receberá um JSON com a estrutura da planta baixa contendo:
- `dimensoes_totais`: { largura, profundidade, altura, area_total }
- `tipo_stand`: tipo do estande (ponta_ilha, esquina, corredor, ilha)
- `lados_abertos`: lista de lados abertos (norte, sul, leste, oeste)
- `areas`: array de áreas com geometria (x, y, largura, profundidade)

**ESPECIFICAÇÕES TÉCNICAS OBRIGATÓRIAS:**

1. **ESCALA:**
   - **1 metro = 100 pixels** (SEMPRE)
   - Largura SVG = dimensoes_totais.largura × 100
   - Altura SVG = dimensoes_totais.profundidade × 100
   - Exemplo: 11m × 8m = 1100px × 800px

2. **CANVAS:**
   - Adicione margem de 100px em todos os lados para legendas
   - viewBox: "0 0 [largura_total] [altura_total]"
   - width e height devem incluir as margens

3. **SISTEMA DE COORDENADAS:**
   - Origem (0,0) no canto superior esquerdo da área útil (após margem)
   - Eixo X: esquerda → direita
   - Eixo Y: cima → baixo (como SVG padrão)

4. **CORES POR TIPO DE ÁREA:**
   - deposito: #F5F5F5 (cinza claro)
   - workshop: #E3F2FD (azul claro)
   - area_exposicao: #FFF9C4 (amarelo claro)
   - sala_reuniao: #C8E6C9 (verde claro)
   - copa: #FFE0B2 (laranja claro)
   - Todas com opacity: 0.7

5. **ELEMENTOS OBRIGATÓRIOS:**

   a) **Retângulo de cada área:**
      - x = geometria.x × 100 + margem
      - y = geometria.y × 100 + margem
      - width = geometria.largura × 100
      - height = geometria.profundidade × 100
      - fill = cor correspondente
      - stroke = #333333
      - stroke-width = 2

   b) **Label de cada área:**
      - Texto: area.nome
      - Posição: centro do retângulo
      - Font: Arial, 14px, bold
      - Cor: #333333
      - text-anchor: middle

   c) **Metragem de cada área:**
      - Texto: area.geometria.area + "m²"
      - Posição: abaixo do nome
      - Font: Arial, 12px
      - Cor: #666666

   d) **Cotas externas:**
      - Largura total na parte superior
      - Profundidade total na lateral esquerda
      - Linhas tracejadas
      - Setas nas extremidades

   e) **Título:**
      - Texto: "PLANTA BAIXA - " + nome_projeto
      - Posição: topo, centralizado
      - Font: Arial, 18px, bold

   f) **Tipo de Stand:**
      - Texto: "Tipo: " + tipo_stand (traduzido)
      - Posição: abaixo do título
      - Font: Arial, 14px
      - Traduções: ponta_ilha → "Ponta de Ilha", esquina → "Esquina", etc

   g) **Legenda de cores:**
      - Canto inferior direito
      - Lista com quadrado colorido + texto para cada tipo presente

   h) **Informações técnicas:**
      - Área total
      - Dimensões (largura × profundidade)
      - Escala (1:100)
      - Data de geração

6. **LADOS ABERTOS (importante para ponta de ilha):**
   - Desenhar bordas mais grossas nos lados fechados (stroke-width: 6)
   - Lados abertos: borda fina (stroke-width: 2) ou tracejada
   - Adicionar indicação visual de "ABERTO" nos lados correspondentes

**FORMATO DE SAÍDA:**

Retorne APENAS o código SVG completo, começando com:
```xml
<svg xmlns="http://www.w3.org/2000/svg" width="..." height="..." viewBox="...">
  <!-- conteúdo aqui -->
</svg>
```

**IMPORTANTE:**
- NÃO invente dimensões - use EXATAMENTE as do JSON recebido
- NÃO use valores fixos - calcule baseado nos dados
- NÃO adicione texto explicativo - apenas o SVG
- SEMPRE respeite a escala 1m = 100px
- SEMPRE mostre o tipo de stand claramente

**EXEMPLO DE CÁLCULO:**
Se dimensoes_totais.largura = 11m e profundidade = 8m:
- SVG width = 11 × 100 + 200 (margens) = 1300px
- SVG height = 8 × 100 + 200 (margens) = 1000px
- viewBox = "0 0 1300 1000"
- Área útil começa em (100, 100) e vai até (1200, 900)
"""

    try:
        agente = Agente.objects.get(id=9)
        agente.task_instructions = task_instructions
        agente.save()

        print("✅ Agente 9 atualizado com sucesso!")
        print(f"\nNome: {agente.nome}")
        print(f"Task Instructions: {len(task_instructions)} caracteres")
        print("\n🎯 O agente agora tem instruções detalhadas para:")
        print("   - Usar escala correta (1m = 100px)")
        print("   - Ler dimensões do JSON corretamente")
        print("   - Indicar tipo de stand")
        print("   - Desenhar lados abertos/fechados")
        print("   - Posicionar áreas com coordenadas corretas")

    except Agente.DoesNotExist:
        print("❌ Agente 9 não encontrado!")
        return False

    except Exception as e:
        print(f"❌ Erro ao atualizar: {str(e)}")
        return False

    return True


if __name__ == "__main__":
    print("\n🔧 Corrigindo Agente 9 (Renderizador SVG)...\n")

    if atualizar_agente_9():
        print("\n✅ Correção concluída! Você pode executar a Etapa 4 novamente.")
        print("   O SVG agora será gerado com:")
        print("   - Dimensões corretas (11m x 8m = 1100px x 800px)")
        print("   - Tipo 'Ponta de Ilha' visível")
        print("   - Layout correto (depósito, workshop, exposição)")
    else:
        print("\n❌ Correção falhou. Verifique os erros acima.")
