#!/usr/bin/env python3
"""
Script para adicionar instruções sobre POSICIONAMENTO SEQUENCIAL de corredores.

PROBLEMA: Agente identifica corredor mas coloca na posição errada (x=0.7 ao invés de x=0.27)
SOLUÇÃO: Instruir que corredor ENTRE áreas deve ter coordenada X entre elas

Uso: python3 corrigir_posicionamento_corredor.py
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'afinal_cenografia.settings')
django.setup()

from core.models import Agente

def adicionar_posicionamento_sequencial():
    """Adiciona instruções sobre posicionamento sequencial de corredores"""

    try:
        agente = Agente.objects.get(id=10)
        instructions = agente.task_instructions

        # Texto a adicionar após a REGRA DE OURO
        texto_posicionamento = '''

⚠️ **POSICIONAMENTO SEQUENCIAL DE CORREDORES:**

Se o corredor está ENTRE duas áreas (conecta depósito e workshop), então:

1. **Ordem Espacial:** A coordenada X do corredor deve refletir sua posição ENTRE as áreas

2. **Cálculo Correto:**
   ```
   Se no esboço: [Depósito] [Corredor] [Workshop]

   Então no JSON:
   - deposito_1:  x = 0.0,  w = largura_deposito
   - corredor_1:  x = x_deposito + w_deposito,  w = largura_corredor
   - workshop_1:  x = x_corredor + w_corredor,  w = largura_workshop
   ```

3. **Exemplo Concreto (Stand 11m):**
   ```
   Esboço: [Dep 3m] [Corr 1m] [Work 7m]

   JSON CORRETO:
   - deposito_1:  x=0.0,  w=0.27  (0m → 3m)
   - corredor_1:  x=0.27, w=0.09  (3m → 4m)  ← Logo após depósito!
   - workshop_1:  x=0.36, w=0.64  (4m → 11m)

   JSON ERRADO:
   - deposito_1:  x=0.0,  w=0.3   (0m → 3.3m)
   - workshop_1:  x=0.3,  w=0.4   (3.3m → 7.7m)
   - corredor_1:  x=0.7,  w=0.3   (7.7m → 11m) ← ❌ No final! ERRADO!
   ```

4. **REGRA CRÍTICA:**
   - Se corredor está ENTRE A e B visualmente no esboço
   - Então coordenada do corredor = coordenada_final_de_A
   - E coordenada de B = coordenada_final_do_corredor
   - NÃO coloque o corredor em posição diferente da sequência visual!

5. **Validação:**
   - Verifique se a ORDEM no JSON corresponde à ORDEM no esboço
   - Esquerda → direita no esboço = valores crescentes de X no JSON'''

        # Inserir após a REGRA DE OURO PARA CORREDORES
        if "REGRA DE OURO PARA CORREDORES:" in instructions and "POSICIONAMENTO SEQUENCIAL DE CORREDORES" not in instructions:
            import re
            # Encontrar o fim da seção REGRA DE OURO
            instructions = re.sub(
                r'(NÃO coloque o corredor em outra linha \(y diferente\) se ele conecta áreas na mesma linha!)',
                r'\1' + texto_posicionamento,
                instructions
            )

            agente.task_instructions = instructions
            agente.save()

            print("="*60)
            print("✅ CORREÇÃO APLICADA COM SUCESSO!")
            print("="*60)
            print("\n📋 O que foi adicionado:")
            print("   - Instruções sobre posicionamento sequencial")
            print("   - Regra: corredor ENTRE áreas tem X entre elas")
            print("   - Exemplo concreto com coordenadas corretas")
            print("   - Exemplo do erro (corredor no final)")
            print("\n🎯 Agora o agente vai:")
            print("   - Calcular X do corredor = X_final do depósito")
            print("   - Calcular X do workshop = X_final do corredor")
            print("   - Respeitar ordem visual do esboço")
            print("\n💡 Layout esperado (11m):")
            print("   - Depósito:  0m → 3m    (x=0.0, w=0.27)")
            print("   - Corredor:  3m → 4m    (x=0.27, w=0.09)")
            print("   - Workshop:  4m → 11m   (x=0.36, w=0.64)")
            print("\n🔄 Próximo passo:")
            print("   - Recarregue a página da Planta Baixa")
            print("   - Execute Etapa 1 novamente")
            print("   - Verifique que corredor_1 tem x ≈ 0.27 (não 0.7!)")

            return True
        elif "POSICIONAMENTO SEQUENCIAL DE CORREDORES" in instructions:
            print("⚠️  Instruções de posicionamento sequencial já existem!")
            return False
        else:
            print("❌ Não foi possível localizar REGRA DE OURO PARA CORREDORES")
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
    print("\n🔧 CORRIGINDO POSICIONAMENTO SEQUENCIAL DE CORREDORES\n")
    print("Problema: Corredor identificado mas na posição errada (x=0.7 ao invés de x=0.27)")
    print("Solução: Instruir que corredor ENTRE áreas deve ter coordenada X entre elas\n")
    print("-" * 60 + "\n")

    adicionar_posicionamento_sequencial()
