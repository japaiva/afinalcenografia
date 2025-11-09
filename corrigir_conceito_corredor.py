#!/usr/bin/env python3
"""
Script para CORRIGIR o conceito de corredor no Agente 10.

PROBLEMA: Estava criando corredores para "espaços vazios"
SOLUÇÃO: Corredor = CIRCULAÇÃO (passagem entre áreas), não preenchimento de espaço

Uso: python3 corrigir_conceito_corredor.py
"""

import os
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'afinal_cenografia.settings')
django.setup()

from core.models import Agente

def corrigir_conceito_corredor():
    """Remove análise de cobertura espacial e reforça conceito correto de corredor"""

    try:
        agente = Agente.objects.get(id=10)

        # Remover a seção problemática de ANÁLISE DE COBERTURA ESPACIAL
        instructions = agente.task_instructions

        # Verificar se a seção problemática existe
        if "ANÁLISE DE COBERTURA ESPACIAL" in instructions:
            print("⚠️  Encontrada seção problemática: ANÁLISE DE COBERTURA ESPACIAL")
            print("   Removendo conceito incorreto de 'preencher espaços vazios'...\n")

            # Remover toda a seção
            import re
            instructions = re.sub(
                r'\*\*ANÁLISE DE COBERTURA ESPACIAL.*?(?=\n\n\*\*|$)',
                '',
                instructions,
                flags=re.DOTALL
            )

        # Atualizar a definição de corredor para focar APENAS em circulação
        texto_corredor_antigo = '''- "corredor": espaço de circulação entre áreas - CRIE SEMPRE que:
        * Houver passagem/corredor desenhado entre duas áreas
        * O esboço mostrar um espaço separando áreas (mesmo que sem paredes explícitas)
        * Rótulos mencionarem "corredor", "passagem", "acesso" entre áreas
        * Houver lacuna/espaço no desenho entre áreas adjacentes'''

        texto_corredor_novo = '''- "corredor": espaço de CIRCULAÇÃO (passagem) entre áreas - CRIE APENAS quando:
        * Houver RÓTULO explícito: "corredor", "passagem", "acesso", "circulação"
        * Houver DESENHO claro de passagem (setas, linhas de fluxo)
        * Houver espaço ESTREITO desenhado entre áreas (claramente para passagem)
        * IMPORTANTE: NÃO criar corredor só porque "sobrou espaço" - espaço não identificado
          provavelmente faz parte de uma área adjacente ou é área de exposição!'''

        if texto_corredor_antigo in instructions:
            instructions = instructions.replace(texto_corredor_antigo, texto_corredor_novo)
            print("✅ Definição de corredor atualizada para focar em CIRCULAÇÃO")

        # Adicionar aviso importante após a seção de corredores
        aviso_importante = '''\n
⚠️ IMPORTANTE SOBRE IDENTIFICAÇÃO DE ÁREAS:

1. **TODO espaço do stand deve ter função definida:**
   - Ou é área específica (depósito, workshop, copa, sala_reuniao)
   - Ou é área de exposição
   - Ou é corredor (apenas se houver EVIDÊNCIA de circulação)

2. **NUNCA deixe espaços "vazios" sem identificação:**
   - Se não há evidência de corredor, considere parte da área adjacente
   - Áreas podem ter formas irregulares - não force corredores

3. **Corredor = CIRCULAÇÃO, não "espaço que sobrou":**
   - Corredor é para PASSAGEM entre áreas
   - Se não há indicação de fluxo/passagem, NÃO é corredor

4. **Prioridade de identificação:**
   - 1º: Identificar áreas principais (depósito, workshop, exposição)
   - 2º: Verificar se há EVIDÊNCIA de corredores (rótulos, setas, desenhos)
   - 3º: Espaços restantes = parte de área adjacente ou exposição
'''

        # Inserir o aviso após a seção de ÁREAS EXTERNAS
        if "ÁREAS EXTERNAS" in instructions and aviso_importante not in instructions:
            instructions = re.sub(
                r'(\*\*ÁREAS EXTERNAS\*\*.*?\n.*?\n)',
                r'\1' + aviso_importante + '\n',
                instructions,
                flags=re.DOTALL
            )
            print("✅ Aviso sobre identificação correta adicionado")

        # Salvar
        agente.task_instructions = instructions
        agente.save()

        print("\n" + "="*60)
        print("✅ CORREÇÃO CONCLUÍDA!")
        print("="*60)
        print("\n📋 Mudanças aplicadas:")
        print("   1. ❌ REMOVIDA: Análise de cobertura espacial")
        print("   2. ✅ ATUALIZADA: Definição de corredor (foco em circulação)")
        print("   3. ✅ ADICIONADO: Aviso sobre identificação correta")
        print("\n🎯 Conceito correto:")
        print("   - Corredor = CIRCULAÇÃO (passagem entre áreas)")
        print("   - NÃO criar corredor para 'espaços vazios'")
        print("   - Espaço não identificado = parte de área adjacente ou exposição")
        print("\n💡 Próximos passos:")
        print("   1. Recarregue a página da Planta Baixa")
        print("   2. Execute Etapa 1 novamente")
        print("   3. Verifique se corredor só aparece quando há EVIDÊNCIA de circulação")

        return True

    except Agente.DoesNotExist:
        print("❌ Agente 10 não encontrado!")
        return False

    except Exception as e:
        print(f"❌ Erro ao atualizar: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("\n🔧 CORRIGINDO CONCEITO DE CORREDOR NO AGENTE 10\n")
    print("Problema: Estava criando corredores para 'espaços vazios'")
    print("Solução: Corredor = CIRCULAÇÃO (passagem), não preenchimento\n")
    print("-" * 60 + "\n")

    corrigir_conceito_corredor()
