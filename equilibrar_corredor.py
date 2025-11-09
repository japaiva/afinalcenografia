#!/usr/bin/env python3
"""
Script para EQUILIBRAR as instruções de corredor no Agente 10.

PROBLEMA: Instruções muito restritivas - corredor real no esboço não está sendo identificado
SOLUÇÃO: Diferenciar entre corredor DESENHADO vs espaço vazio grande

Uso: python3 equilibrar_corredor.py
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'afinal_cenografia.settings')
django.setup()

from core.models import Agente

def equilibrar_instrucoes_corredor():
    """Atualiza instruções para identificar corredores reais mas não espaços grandes"""

    try:
        agente = Agente.objects.get(id=10)
        instructions = agente.task_instructions

        # Encontrar e substituir a definição de corredor
        texto_corredor_antigo = '''  - "corredor": espaço de CIRCULAÇÃO (passagem) entre áreas - CRIE APENAS quando:
      * Houver RÓTULO explícito no esboço: "corredor", "passagem", "acesso", "circulação"
      * Houver DESENHO claro de passagem (setas indicando fluxo, linhas de movimento)
      * Houver espaço ESTREITO desenhado entre áreas (claramente para passagem)
      * Houver paredes delimitando uma passagem
      * ⚠️ IMPORTANTE: NÃO criar corredor só porque "sobrou espaço não identificado"!
         Espaço não identificado provavelmente faz parte de uma área adjacente ou é exposição.'''

        texto_corredor_novo = '''  - "corredor": espaço de CIRCULAÇÃO (passagem) entre áreas - CRIE quando:
      * Houver RÓTULO explícito: "corredor", "passagem", "acesso", "circulação"
      * Houver DESENHO de passagem entre áreas (mesmo sem rótulo)
      * Houver espaço ESTREITO entre áreas (< 2m ou < 20% da largura total)
      * Houver paredes/linhas delimitando uma passagem vertical ou horizontal

      ⚠️ DIFERENÇA IMPORTANTE:
      ✅ Espaço ESTREITO (1-2m) entre depósito e workshop = CORREDOR (criar!)
      ❌ Espaço LARGO (> 3m) sem função clara = parte de outra área (não criar)

      **Exemplo no esboço:**
      ```
      [Depósito 3m] [espaço 1m] [Workshop 4m] [Exposição 3m]
                      ↑ CRIAR corredor aqui!
      ```

      **Regra prática:** Se o espaço entre áreas é DESPROPORCIONAL (muito estreito
      comparado às áreas adjacentes), é provável que seja corredor para circulação.'''

        if texto_corredor_antigo in instructions:
            instructions = instructions.replace(texto_corredor_antigo, texto_corredor_novo)

            agente.task_instructions = instructions
            agente.save()

            print("="*60)
            print("✅ CORREÇÃO APLICADA COM SUCESSO!")
            print("="*60)
            print("\n📋 O que foi ajustado:")
            print("   - Corredor DESENHADO no esboço = criar (mesmo sem rótulo)")
            print("   - Espaço ESTREITO (< 2m) entre áreas = criar")
            print("   - Espaço LARGO (> 3m) sem função = não criar")
            print("\n🎯 Critérios equilibrados:")
            print("   ✅ Criar: passagem desenhada, espaço estreito, proporcional")
            print("   ❌ Não criar: espaço grande sem função, mobiliário")
            print("\n💡 Exemplo:")
            print("   - [Depósito 3m] [1m] [Workshop 4m] → 1m é CORREDOR ✅")
            print("   - [Depósito 3m] [5m vazio] [Workshop] → 5m é OUTRA ÁREA ❌")
            print("\n🔄 Próximo passo:")
            print("   - Recarregue a página da Planta Baixa")
            print("   - Execute Etapa 1 novamente")
            print("   - Verifique que o corredor entre depósito e workshop aparece")

            return True
        else:
            print("⚠️  Texto não encontrado - instruções podem ter sido modificadas")
            print("\nVerificando se já tem o novo texto...")
            if "ESTREITO (< 2m)" in instructions:
                print("✅ Novo texto já está presente!")
                return True
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
    print("\n🔧 EQUILIBRANDO INSTRUÇÕES DE CORREDOR\n")
    print("Problema: Corredor real no esboço não está sendo identificado")
    print("Solução: Distinguir corredor real (1-2m) de espaço grande (> 3m)\n")
    print("-" * 60 + "\n")

    equilibrar_instrucoes_corredor()
