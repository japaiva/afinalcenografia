#!/usr/bin/env python3
"""
Script para FORÇAR cobertura de 100% do espaço nas áreas identificadas.

PROBLEMA: Áreas somam apenas 80% da largura (faltam 20%)
SOLUÇÃO: Regra IMPERATIVA - áreas SEMPRE devem somar 100%

Uso: python3 forcar_cobertura_100porcento.py
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'afinal_cenografia.settings')
django.setup()

from core.models import Agente

def forcar_cobertura_completa():
    """Adiciona regra imperativa de cobertura 100%"""

    try:
        agente = Agente.objects.get(id=10)
        instructions = agente.task_instructions

        # Texto a adicionar após COORDENADAS NORMALIZADAS
        texto_cobertura = '''

🚨 **REGRA IMPERATIVA: COBERTURA 100% DO ESPAÇO** 🚨

**CRÍTICO:** As áreas identificadas na mesma linha horizontal DEVEM somar 100% da largura!

1. **Verificação Obrigatória:**
   - ANTES de gerar o JSON, SOME as larguras (w) das áreas na mesma linha
   - A soma DEVE ser = 1.0 (100%)
   - Se não for, AJUSTE as dimensões!

2. **Como Ajustar:**

   **Se identificou:** Depósito + Corredor + Workshop na mesma linha

   **E eles NÃO somam 100%:**
   ```
   Exemplo ERRADO:
   deposito_1: w=0.3 (30%)
   corredor_1: w=0.1 (10%)
   workshop_1: w=0.4 (40%)
   Total: 0.8 (80%) ← FALTAM 20%! ❌
   ```

   **CORREÇÃO - Opções:**

   a) **Se depósito e workshop têm tamanho similar no esboço:**
   ```json
   {
     "id": "deposito_1",
     "bbox_norm": {"x": 0.0, "w": 0.45}  // 45%
   },
   {
     "id": "corredor_1",
     "bbox_norm": {"x": 0.45, "w": 0.10}  // 10%
   },
   {
     "id": "workshop_1",
     "bbox_norm": {"x": 0.55, "w": 0.45}  // 45%
   }
   Total: 0.45 + 0.10 + 0.45 = 1.0 ✅
   ```

   b) **Se workshop é visivelmente maior:**
   ```json
   {
     "id": "deposito_1",
     "bbox_norm": {"x": 0.0, "w": 0.30}  // 30%
   },
   {
     "id": "corredor_1",
     "bbox_norm": {"x": 0.30, "w": 0.10}  // 10%
   },
   {
     "id": "workshop_1",
     "bbox_norm": {"x": 0.40, "w": 0.60}  // 60%
   }
   Total: 0.30 + 0.10 + 0.60 = 1.0 ✅
   ```

3. **Procedimento de Validação:**
   ```
   PARA cada linha horizontal:
     soma_w = 0
     PARA cada área nessa linha:
       soma_w += area.w

     SE soma_w != 1.0:
       ❌ ERRO! Ajuste as dimensões!

       SE soma_w < 1.0:
         → Falta espaço: aumente a última área OU adicione área faltante

       SE soma_w > 1.0:
         → Sobreposição: reduza áreas proporcionalmente
   ```

4. **Exemplo Completo (Stand 11m):**

   **Esboço diz:** Depósito e Workshop tamanho similar, corredor no meio

   **Cálculo:**
   - Corredor: ~1m (fixo, para circulação)
   - Restam: 11m - 1m = 10m para dividir
   - Depósito: 10m ÷ 2 = 5m
   - Workshop: 10m ÷ 2 = 5m

   **JSON Final:**
   ```json
   {
     "id": "deposito_1",
     "bbox_norm": {"x": 0.0, "w": 0.45}  // 5m de 11m
   },
   {
     "id": "corredor_1",
     "bbox_norm": {"x": 0.45, "w": 0.09}  // 1m de 11m
   },
   {
     "id": "workshop_1",
     "bbox_norm": {"x": 0.54, "w": 0.46}  // 5m de 11m (ajuste de arredondamento)
   }
   ```

   **Verificação:** 0.45 + 0.09 + 0.46 = 1.0 ✅

5. **NUNCA deixe espaço vazio!**
   - Se não há outra área identificada, ajuste as existentes
   - Depósito e Workshop devem preencher TODO o espaço (menos o corredor)

⚠️ **Esta regra é OBRIGATÓRIA - JSON será REJEITADO se não somar 100%!**
'''

        # Inserir após a seção COORDENADAS NORMALIZADAS
        if "COORDENADAS NORMALIZADAS (bbox_norm):" in instructions and "COBERTURA 100% DO ESPAÇO" not in instructions:
            import re
            # Encontrar final da seção COORDENADAS NORMALIZADAS
            instructions = re.sub(
                r'(\(3m/11m ≈ 0\.27, 4m/8m = 0\.5\))',
                r'\1' + texto_cobertura,
                instructions
            )

            agente.task_instructions = instructions
            agente.save()

            print("="*60)
            print("✅ CORREÇÃO APLICADA COM SUCESSO!")
            print("="*60)
            print("\n📋 O que foi adicionado:")
            print("   - REGRA IMPERATIVA: áreas devem somar 100%")
            print("   - Procedimento de verificação de soma")
            print("   - Como ajustar quando não soma 100%")
            print("   - Exemplo: depósito e workshop similares")
            print("\n🎯 Agora o agente vai:")
            print("   - SOMAR larguras das áreas na mesma linha")
            print("   - VERIFICAR se soma = 100%")
            print("   - AJUSTAR dimensões se necessário")
            print("\n💡 Layout esperado (11m):")
            print("   - Depósito:  0m → 5m    (w=0.45 = 45%)")
            print("   - Corredor:  5m → 6m    (w=0.10 = 10%)")
            print("   - Workshop:  6m → 11m   (w=0.45 = 45%)")
            print("   - SOMA: 45% + 10% + 45% = 100% ✅")
            print("\n🔄 Próximo passo:")
            print("   - Recarregue a página da Planta Baixa")
            print("   - Execute Etapa 1 novamente")
            print("   - Verifique que as 3 áreas somam 100% da largura")

            return True
        elif "COBERTURA 100% DO ESPAÇO" in instructions:
            print("⚠️  Regra de cobertura 100% já existe!")
            return False
        else:
            print("❌ Não foi possível localizar seção COORDENADAS NORMALIZADAS")
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
    print("\n🔧 FORÇANDO COBERTURA 100% DO ESPAÇO\n")
    print("Problema: Áreas somam apenas 80% (faltam 20%)")
    print("Solução: Regra IMPERATIVA - sempre somar 100%\n")
    print("-" * 60 + "\n")

    forcar_cobertura_completa()
