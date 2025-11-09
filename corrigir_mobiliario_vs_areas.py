#!/usr/bin/env python3
"""
Script para adicionar diferenciação entre ÁREAS e MOBILIÁRIO no Agente 10.

PROBLEMA: Agente está criando áreas separadas para mobiliário (balcão de vendas)
SOLUÇÃO: Instruir que mobiliário NÃO é área separada

Uso: python3 corrigir_mobiliario_vs_areas.py
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'afinal_cenografia.settings')
django.setup()

from core.models import Agente

def adicionar_diferenciacão_areas_mobiliario():
    """Adiciona instruções para diferenciar áreas de mobiliário"""

    try:
        agente = Agente.objects.get(id=10)
        instructions = agente.task_instructions

        # Texto a adicionar logo após a seção de ÁREAS EXTERNAS
        texto_diferenciacao = '''
⚠️ **DIFERENÇA CRÍTICA: ÁREAS vs MOBILIÁRIO/EQUIPAMENTOS**

**ÁREAS** = espaços funcionais delimitados (crie áreas para isso):
  - Depósito, workshop, copa, sala_reunião (com paredes/divisórias)
  - Área de exposição (espaço aberto para produtos)
  - Corredor (quando há evidência de passagem)

**MOBILIÁRIO/EQUIPAMENTOS** = elementos DENTRO das áreas (NÃO crie áreas para isso):
  - Balcão de vendas, balcão de atendimento → faz parte da área de exposição
  - Prateleiras, displays, vitrines → fazem parte da área de exposição
  - Mesas, cadeiras → fazem parte da copa ou sala_reunião
  - Bancadas → fazem parte do workshop
  - Armários → fazem parte do depósito

**REGRA:** Se é mobiliário/equipamento desenhado no esboço, NÃO crie área separada!
           Considere que faz parte da área funcional onde está localizado.

**Exemplo ERRADO:**
```json
{
  "id": "balcao_vendas_1",  ← ❌ ERRADO! Balcão não é área!
  "subtipo": "balcao_vendas",
  "bbox_norm": {...}
}
```

**Exemplo CORRETO:**
```json
{
  "id": "area_exposicao_1",  ← ✅ CORRETO! Balcão faz parte da exposição
  "subtipo": "area_exposicao",
  "bbox_norm": {...}  // Inclui o espaço do balcão
}
```
'''

        # Inserir após ÁREAS EXTERNAS
        if "ÁREAS EXTERNAS" in instructions and "DIFERENÇA CRÍTICA: ÁREAS vs MOBILIÁRIO" not in instructions:
            # Encontrar o final da seção ÁREAS EXTERNAS
            import re
            instructions = re.sub(
                r'(\*\*ÁREAS EXTERNAS\*\*.*?- "palco":.*?\n)',
                r'\1' + texto_diferenciacao,
                instructions,
                flags=re.DOTALL
            )

            agente.task_instructions = instructions
            agente.save()

            print("="*60)
            print("✅ CORREÇÃO APLICADA COM SUCESSO!")
            print("="*60)
            print("\n📋 O que foi adicionado:")
            print("   - Diferenciação clara entre ÁREAS e MOBILIÁRIO")
            print("   - Lista do que NÃO deve ser área (balcões, prateleiras, etc)")
            print("   - Exemplos de certo e errado")
            print("\n🎯 Agora o agente vai:")
            print("   - Identificar apenas ÁREAS funcionais delimitadas")
            print("   - NÃO criar áreas para mobiliário/equipamentos")
            print("   - Considerar mobiliário parte da área onde está")
            print("\n💡 Próximo passo:")
            print("   - Recarregue a página da Planta Baixa")
            print("   - Execute Etapa 1 novamente")
            print("   - Verifique que balcão de vendas não aparece como área separada")
            print("   - Área de exposição deve incluir o espaço do balcão")

            return True
        elif "DIFERENÇA CRÍTICA: ÁREAS vs MOBILIÁRIO" in instructions:
            print("⚠️  Diferenciação já existe nas instruções!")
            return False
        else:
            print("❌ Não foi possível localizar seção ÁREAS EXTERNAS")
            return False

    except Agente.DoesNotExist:
        print("❌ Agente 10 não encontrado!")
        return False
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("\n🔧 CORRIGINDO DIFERENCIAÇÃO ÁREAS vs MOBILIÁRIO\n")
    print("Problema: Agente criando áreas separadas para mobiliário")
    print("Solução: Instruir que mobiliário não é área\n")
    print("-" * 60 + "\n")

    adicionar_diferenciacão_areas_mobiliario()
