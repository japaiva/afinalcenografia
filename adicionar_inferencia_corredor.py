#!/usr/bin/env python3
"""
Script para adicionar INFERÊNCIA DE CORREDORES ao Agente 10.

PROBLEMA: Corredor existe mas está mal desenhado - agente não identifica
SOLUÇÃO: Instruir agente a INFERIR corredor quando há evidências indiretas

Uso: python3 adicionar_inferencia_corredor.py
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'afinal_cenografia.settings')
django.setup()

from core.models import Agente

def adicionar_inferencia_corredor():
    """Adiciona capacidade de inferir corredores em esboços mal desenhados"""

    try:
        agente = Agente.objects.get(id=10)
        instructions = agente.task_instructions

        # Texto a adicionar após POSICIONAMENTO SEQUENCIAL
        texto_inferencia = '''

⚠️ **INFERÊNCIA DE CORREDORES (Esboços Mal Desenhados):**

Mesmo quando o corredor NÃO está claramente desenhado, você deve INFERIR sua existência se:

1. **Análise de Cobertura:**
   - Depósito + Workshop NÃO ocupam toda a largura da metade superior
   - Exemplo: Depósito ocupa ~30% + Workshop ~40% = 70% → **faltam 30%**
   - Se faltar espaço, considere que pode haver corredor mal desenhado

2. **Lógica de Circulação:**
   - Se depósito e workshop são áreas "fechadas" (não abertas ao público)
   - É lógico que haja passagem/corredor entre elas
   - Mesmo sem desenho claro, infira corredor de ~1m (ou espaço faltante)

3. **Proporção Suspeita:**
   - Se as áreas identificadas deixam espaço não contabilizado
   - E não há outra área óbvia para preencher o espaço
   - Considere que é corredor mal desenhado

**REGRA PRÁTICA - Stand 11m:**

Se você identificou:
- Depósito: ~3m (27%)
- Workshop: ~4m (36%)
- Total: 7m = apenas 64% da largura

→ **FALTAM 4m (36%)!** Onde estão?

**Opções:**
a) Corredor largo (2-3m) entre depósito e workshop
b) Outra área (exposição) na mesma linha
c) Workshop é maior do que parece no desenho

**Se NÃO houver outra área visível:** Infira corredor estreito (~1m) entre depósito
e workshop, e ajuste dimensões para somar 100%.

**EXEMPLO DE INFERÊNCIA:**

Esboço mal desenhado mostra:
```
[Depósito] [Workshop]  ← Parecem colados, mas não ocupam toda largura
```

**Análise:**
- Depósito aparenta ~3m
- Workshop aparenta ~4m
- Total: 7m de 11m → faltam 4m!

**Decisão de inferência:**
```json
{
  "id": "deposito_1",
  "bbox_norm": {"x": 0.0, "w": 0.27}  // 3m
},
{
  "id": "corredor_1",  ← INFERIDO (passagem entre áreas)
  "bbox_norm": {"x": 0.27, "w": 0.09}  // 1m
},
{
  "id": "workshop_1",
  "bbox_norm": {"x": 0.36, "w": 0.64}  // 7m (ajustado para 100%)
}
```

**Justificativa:**
- Corredor de 1m é proporcional para circulação
- Permite acesso entre depósito fechado e workshop
- Workshop ampliado (7m) usa o espaço restante

⚠️ **IMPORTANTE:**
- Sempre tente somar 100% da largura/profundidade
- Se faltar espaço, considere corredor ou ajuste dimensões
- Corredor é preferível quando conecta áreas funcionais distintas
'''

        # Inserir após POSICIONAMENTO SEQUENCIAL
        if "POSICIONAMENTO SEQUENCIAL DE CORREDORES:" in instructions and "INFERÊNCIA DE CORREDORES" not in instructions:
            import re
            # Encontrar final da seção POSICIONAMENTO SEQUENCIAL
            instructions = re.sub(
                r'(Esquerda → direita no esboço = valores crescentes de X no JSON)',
                r'\1' + texto_inferencia,
                instructions
            )

            agente.task_instructions = instructions
            agente.save()

            print("="*60)
            print("✅ CORREÇÃO APLICADA COM SUCESSO!")
            print("="*60)
            print("\n📋 O que foi adicionado:")
            print("   - Capacidade de INFERIR corredores em esboços mal desenhados")
            print("   - Análise de cobertura espacial (soma deve dar 100%)")
            print("   - Lógica: se falta espaço, considere corredor")
            print("\n🎯 Agora o agente vai:")
            print("   - Verificar se áreas somam 100% da largura")
            print("   - Se faltar espaço, inferir corredor (~1m)")
            print("   - Ajustar dimensões para preencher o stand")
            print("\n💡 Exemplo (Stand 11m):")
            print("   - Depósito ~3m + Workshop ~4m = 7m (faltam 4m!)")
            print("   - Inferir: Corredor 1m + ajustar Workshop para 7m")
            print("   - Resultado: 3m + 1m + 7m = 11m ✅")
            print("\n🔄 Próximo passo:")
            print("   - Recarregue a página da Planta Baixa")
            print("   - Execute Etapa 1 novamente")
            print("   - Verifique que corredor_1 foi inferido entre as áreas")

            return True
        elif "INFERÊNCIA DE CORREDORES" in instructions:
            print("⚠️  Instruções de inferência já existem!")
            return False
        else:
            print("❌ Não foi possível localizar seção POSICIONAMENTO SEQUENCIAL")
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
    print("\n🔧 ADICIONANDO INFERÊNCIA DE CORREDORES\n")
    print("Problema: Corredor existe mas está mal desenhado")
    print("Solução: Instruir agente a inferir corredor quando faltar espaço\n")
    print("-" * 60 + "\n")

    adicionar_inferencia_corredor()
