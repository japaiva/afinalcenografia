# teste_prompt.py - Execute com: python manage.py shell < teste_prompt.py

from core.models import Agente
from projetos.models import Projeto

# Carregar dados
projeto = Projeto.objects.get(id=57)
briefing = projeto.briefings.first()
layout = projeto.layout_identificado
inspiracoes = projeto.inspiracoes_visuais

# Pegar o template
agente = Agente.objects.get(nome="Agente de Imagem Principal", ativo=True)
template = agente.task_instructions

print("=== DADOS DISPONÍVEIS ===")
print(f"Empresa: {projeto.empresa.nome}")
print(f"Dimensões: {briefing.medida_frente}m x {briefing.medida_fundo}m")
print(f"Tipo: {briefing.tipo_stand}")
print(f"Objetivo: {briefing.objetivo_evento}")
print(f"Estilo: {briefing.estilo_estande}")

# Processar áreas do layout
areas_internas = []
areas_externas = []

for area in layout.get('areas', []):
    nome = area.get('subtipo', '').replace('_', ' ')
    m2 = area.get('m2_estimado', 0)
    categoria = area.get('categoria', '')
    
    texto = f"{nome} ({m2:.0f}m²)"
    if categoria == 'interna':
        areas_internas.append(texto)
    else:
        areas_externas.append(texto)

# Processar cores
cores = []
for cor in inspiracoes.get('cores_predominantes', [])[:4]:
    if 'hex' in cor:
        cores.append(cor['hex'])

# Processar materiais
materiais = []
for mat in inspiracoes.get('materiais_sugeridos', []):
    if 'material' in mat:
        materiais.append(mat['material'].replace('_', ' '))

# Processar estilo
estilo = inspiracoes.get('estilo_identificado', {})
estilo_principal = estilo.get('principal', 'moderno').replace('_', ' ')

print(f"\n=== DADOS PROCESSADOS ===")
print(f"Áreas internas: {', '.join(areas_internas)}")
print(f"Áreas externas: {', '.join(areas_externas)}")
print(f"Cores: {', '.join(cores)}")
print(f"Materiais: {', '.join(materiais)}")
print(f"Estilo: {estilo_principal}")

# Fazer as substituições
replacements = {
    "[OBJETIVO_ESTANDE]": briefing.objetivo_estande or briefing.objetivo_evento or "exposição",
    "[DESCRICAO_EMPRESA]": projeto.empresa.descricao or f"Empresa do setor de {projeto.empresa.nome}",
    "[SETOR]": "cosméticos",
    "[LARGURA]": str(briefing.medida_frente),
    "[PROFUNDIDADE]": str(briefing.medida_fundo),
    "[ALTURA]": "3",
    "[TIPO]": briefing.get_tipo_stand_display(),
    "[POSICIONAMENTO]": "posição estratégica na feira",
    "[AREAS_INTERNAS]": ", ".join(areas_internas) or "depósito, copa, reunião",
    "[TIPO_ESTRUTURA]": "misto" if briefing.material == 'misto' else briefing.material,
    "[PISO_ELEVADO]": "com" if briefing.piso_elevado != 'sem_elevacao' else "sem",
    "[ALTURA_PISO]": briefing.piso_elevado.replace('cm', '') if 'cm' in str(briefing.piso_elevado) else "0",
    "[MATERIAL_PISO]": "carpete grafite",
    "[TIPO_TESTEIRA]": briefing.tipo_testeira or "reta",
    "[MATERIAL_TESTEIRA]": "acrílico iluminado com logo",
    "[ALTURA_DIVISORIAS]": "2.5",
    "[AREAS_FUNCIONAIS]": ", ".join(areas_externas) or "área de exposição, balcão",
    "[REFERENCIAS]": f"Estilo {estilo_principal}, cores {', '.join(cores[:2])}",
    "[CONCEITO_INTEGRADO]": f"Estande {estilo_principal} para {projeto.empresa.nome}",
    "[TIPO_ESTANDE]": briefing.get_tipo_stand_display(),
    "[LISTA_AREAS_INTERNAS]": ", ".join(areas_internas),
    "[LARGURA_CIRCULACAO]": "1.5",
    "[AREAS_EXTERNAS]": ", ".join(areas_externas),
    "[MATERIAIS_PRINCIPAIS]": ", ".join(materiais) or "madeira, vidro, metal",
    "[TIPO_PISO]": "elevado" if briefing.piso_elevado != 'sem_elevacao' else "nivelado",
    "[ELEVACAO_PISO]": f"{briefing.piso_elevado.replace('cm', '')}cm de" if 'cm' in str(briefing.piso_elevado) else "sem",
    "[TIPO_ILUMINACAO]": "LED profissional",
    "[CORES_PRINCIPAIS]": ", ".join(cores) or "#FFFFFF, #0066CC",
    "[SETOR_EMPRESA]": "cosméticos",
    "[LISTA_MOBILIARIO]": "balcão recepção, expositores, mesas, sofás",
    "[LISTA_EQUIPAMENTOS]": "TVs LED, tablets, sistema de som",
    "[ELEMENTOS_DECORATIVOS]": ", ".join(inspiracoes.get('elementos_destaque', ['plantas', 'displays'])[:3]),
    "[CARACTERISTICAS_ESPECIFICAS]": estilo_principal
}

# Substituir no template
prompt_final = template
for placeholder, valor in replacements.items():
    prompt_final = prompt_final.replace(placeholder, str(valor))

# Verificar se ainda tem placeholders não substituídos
import re
placeholders_restantes = re.findall(r'\[[A-Z_]+\]', prompt_final)
if placeholders_restantes:
    print(f"\n⚠️  PLACEHOLDERS NÃO SUBSTITUÍDOS: {placeholders_restantes}")

print("\n=== PROMPT GERADO ===")
print("=" * 50)
print(prompt_final)
print("=" * 50)
print(f"\nTamanho: {len(prompt_final)} caracteres")

# Salvar em arquivo
with open('prompt_gerado.txt', 'w') as f:
    f.write(prompt_final)
    print("\n✓ Prompt salvo em 'prompt_gerado.txt'")