#!/usr/bin/env python
"""
Script para adicionar 'corredor' como subtipo válido no Agente 10.
Uso: python corrigir_agente_10_corredor.py
"""

import os
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'afinal_cenografia.settings')
django.setup()

from core.models import Agente

def corrigir_agente_10():
    """Adiciona 'corredor' como subtipo válido nas instruções"""

    try:
        agente = Agente.objects.get(id=10)

        # Texto atual que precisa ser modificado
        texto_antigo = """     **ÁREAS INTERNAS** (podem ter múltiplas instâncias):
      - "deposito": espaços de armazenamento, estoque
      - "copa": área para preparo de alimentos/bebidas
      - "sala_reuniao": salas fechadas ou semi-fechadas para reuniões
      - "workshop": espaços para demonstrações, atividades práticas

      **ÁREAS EXTERNAS** (podem ter múltiplas instâncias):
      - "area_exposicao": espaços abertos de exposição de produtos
      - "palco": área elevada para apresentações

      **CIRCULAÇÃO**:
      - Espaços de passagem entre as áreas (não criar áreas específicas,
   mapear nos segmentos)"""

        # Texto novo com corredor incluído
        texto_novo = """     **ÁREAS INTERNAS** (podem ter múltiplas instâncias):
      - "deposito": espaços de armazenamento, estoque
      - "copa": área para preparo de alimentos/bebidas
      - "sala_reuniao": salas fechadas ou semi-fechadas para reuniões
      - "workshop": espaços para demonstrações, atividades práticas
      - "corredor": espaço de circulação delimitado entre áreas (quando claramente desenhado como área própria)

      **ÁREAS EXTERNAS** (podem ter múltiplas instâncias):
      - "area_exposicao": espaços abertos de exposição de produtos
      - "palco": área elevada para apresentações

      **CIRCULAÇÃO GENÉRICA**:
      - Espaços de passagem NÃO delimitados (mapear apenas no array 'circulacao' com coordenadas)
      - Use subtipo "corredor" quando for uma ÁREA física delimitada
      - Use array 'circulacao' quando for apenas fluxo/passagem livre"""

        # Substituir
        if texto_antigo in agente.task_instructions:
            agente.task_instructions = agente.task_instructions.replace(texto_antigo, texto_novo)
            agente.save()

            print("✅ Agente 10 corrigido com sucesso!")
            print()
            print("📝 Mudanças aplicadas:")
            print("   1. Adicionado 'corredor' como subtipo de ÁREA INTERNA")
            print("   2. Diferenciado corredor delimitado vs circulação genérica")
            print()
            print("🎯 Agora o agente vai:")
            print("   - Identificar corredor como ÁREA quando for delimitado no esboço")
            print("   - Usar 'circulacao' apenas para fluxos livres")
            print()
            print("✨ Também atualizar lista de IDs nas linhas 70-76")

            # Também atualizar a lista de exemplos de IDs (linhas 70-76)
            texto_ids_antigo = """     Quando houver múltiplas áreas do mesmo subtipo, organize assim:
      - deposito_1, deposito_2, deposito_3...
      - sala_reuniao_1, sala_reuniao_2...
      - area_exposicao_1, area_exposicao_2...
      - workshop_1, workshop_2...
      - copa_1, copa_2...
      - palco_1, palco_2..."""

            texto_ids_novo = """     Quando houver múltiplas áreas do mesmo subtipo, organize assim:
      - deposito_1, deposito_2, deposito_3...
      - corredor_1, corredor_2, corredor_3...
      - sala_reuniao_1, sala_reuniao_2...
      - area_exposicao_1, area_exposicao_2...
      - workshop_1, workshop_2...
      - copa_1, copa_2...
      - palco_1, palco_2..."""

            if texto_ids_antigo in agente.task_instructions:
                agente.task_instructions = agente.task_instructions.replace(texto_ids_antigo, texto_ids_novo)
                agente.save()
                print("   ✅ Lista de IDs também atualizada")

            return True
        else:
            print("⚠️  Texto exato não encontrado. Instruções podem ter sido modificadas.")
            print()
            print("Verifique manualmente se 'corredor' já está incluído ou se houve mudanças no prompt.")
            return False

    except Agente.DoesNotExist:
        print("❌ Agente 10 não encontrado!")
        return False

    except Exception as e:
        print(f"❌ Erro ao atualizar: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("\n🔧 Corrigindo Agente 10 (Analisador de Esboços)...\n")

    if corrigir_agente_10():
        print("\n✅ Correção concluída!")
        print()
        print("📋 Próximos passos:")
        print("   1. Execute a Etapa 1 novamente para re-analisar o esboço")
        print("   2. Verifique se agora identifica 3 áreas na primeira metade:")
        print("      - deposito_1")
        print("      - corredor_1")
        print("      - workshop_1")
        print("   3. Se correto, execute as Etapas 2, 3 e 4")
        print()
        print("💡 Dica: Para forçar re-análise, você pode:")
        print("   - Limpar projeto.layout_identificado no Django Admin")
        print("   - Ou apenas clicar em 'Executar' na Etapa 1 de novo")
    else:
        print("\n❌ Correção falhou. Verifique os erros acima.")
