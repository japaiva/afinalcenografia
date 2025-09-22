# gestor/services/prompt_formatters.py
# VERSÃO FINAL SIMPLIFICADA

from typing import Dict, Any, Optional

# ========== REGRAS DE INTERPRETAÇÃO FIXAS ==========

INTERPRETACAO_TIPOS_STAND = {
    'ilha': 'ilha (4 lados abertos, circulação 360°)',
    'ponta_ilha': 'ponta de ilha (3 lados abertos, fundo fechado)',
    'esquina': 'esquina (2 lados abertos em L)',
    'corredor': 'corredor (1 lado aberto frontal)',
    'box': 'box modular simples'
}

INTERPRETACAO_ESTRUTURA = {
    'padrao': 'modular (alumínio e vidro octanorm)',
    'misto': 'híbrida (frente construída + fundo modular)',
    'construido': 'totalmente construída (marcenaria personalizada)'
}

INTERPRETACAO_PISO = {
    'sem_elevacao': 'nivelado com pavilhão',
    '3cm': 'elevado 3cm com carpete (passagem de cabos)',
    '10cm': 'elevado 10cm com rampa de acessibilidade',
    'livre': 'conforme necessidade técnica'
}

# ========== FUNÇÕES DE INTERPRETAÇÃO ==========

def interpretar_tipo_stand(tipo: str) -> str:
    """Aplica interpretação ao tipo de stand."""
    return INTERPRETACAO_TIPOS_STAND.get(tipo, tipo)

def interpretar_estrutura(material: str) -> str:
    """Aplica interpretação ao tipo de estrutura."""
    return INTERPRETACAO_ESTRUTURA.get(material, material)

def interpretar_piso(piso: str) -> str:
    """Aplica interpretação ao tipo de piso."""
    return INTERPRETACAO_PISO.get(piso, piso)

# ========== FUNÇÕES DE FORMATAÇÃO ==========

def formatar_layout_areas_detalhado(layout: Dict) -> str:
    """
    Converte JSON do layout em descrição textual organizada.
    """
    if not layout or 'areas' not in layout:
        return "Área de exposição ampla ocupando toda a frente"
    
    areas = layout.get('areas', [])
    if not areas:
        return "Layout aberto sem divisões"
    
    # Organizar por posição
    areas_por_posicao = {'fundo': [], 'centro': [], 'frente': []}
    
    for area in areas:
        subtipo = area.get('subtipo', 'área').replace('_', ' ')
        m2 = area.get('m2_estimado', 0)
        categoria = area.get('categoria', 'externa')
        y_pos = area.get('bbox_norm', {}).get('y', 0.5)
        
        descricao = f"{subtipo} ({m2:.0f}m²)"
        if categoria == 'interna':
            descricao += " [fechada]"
        
        if y_pos < 0.35:
            areas_por_posicao['fundo'].append(descricao)
        elif y_pos < 0.65:
            areas_por_posicao['centro'].append(descricao)
        else:
            areas_por_posicao['frente'].append(descricao)
    
    # Montar texto
    resultado = []
    if areas_por_posicao['fundo']:
        resultado.append("FUNDO: " + ", ".join(areas_por_posicao['fundo']))
    if areas_por_posicao['centro']:
        resultado.append("CENTRO: " + ", ".join(areas_por_posicao['centro']))
    if areas_por_posicao['frente']:
        resultado.append("FRENTE: " + ", ".join(areas_por_posicao['frente']))
    
    return "\n".join(resultado)

def formatar_cores_aplicadas(inspiracoes: Dict) -> str:
    """
    Formata cores com suas aplicações.
    """
    if not inspiracoes or 'cores_predominantes' not in inspiracoes:
        return "• Cores corporativas padrão\n• Branco para acabamentos"
    
    cores = inspiracoes.get('cores_predominantes', [])
    if not cores:
        return "• Paleta neutra"
    
    texto = []
    for cor in cores[:5]:  # Máximo 5 cores
        if 'hex' in cor:
            uso = cor.get('uso', 'geral')
            texto.append(f"• {cor['hex']} - {uso}")
    
    return "\n".join(texto) if texto else "• Cores padrão"

def formatar_materiais_detalhados(inspiracoes: Dict) -> str:
    """
    Formata lista de materiais.
    """
    if not inspiracoes or 'materiais_sugeridos' not in inspiracoes:
        return "• MDF com pintura - estrutura\n• Vidro temperado - divisórias"
    
    materiais = inspiracoes.get('materiais_sugeridos', [])
    if not materiais:
        return "• Materiais padrão de feira"
    
    texto = []
    for mat in materiais[:6]:  # Máximo 6 materiais
        if 'material' in mat:
            material = mat['material'].replace('_', ' ').title()
            aplicacao = mat.get('aplicacao', 'acabamento')
            texto.append(f"• {material} - {aplicacao}")
    
    return "\n".join(texto) if texto else "• Materiais padrão"

def formatar_elementos_destaque(inspiracoes: Dict) -> str:
    """
    Lista elementos visuais de destaque.
    """
    if not inspiracoes or 'elementos_destaque' not in inspiracoes:
        return "• Logo corporativo iluminado\n• Displays de produtos"
    
    elementos = inspiracoes.get('elementos_destaque', [])
    if not elementos:
        return "• Elementos visuais padrão"
    
    return "\n".join([f"• {elem}" for elem in elementos[:6] if isinstance(elem, str)])

def formatar_iluminacao(inspiracoes: Dict) -> str:
    """
    Especifica iluminação.
    """
    if not inspiracoes or 'iluminacao' not in inspiracoes:
        return "LED geral 4000K"
    
    ilum = inspiracoes.get('iluminacao', {})
    if isinstance(ilum, dict):
        tipos = ilum.get('tipos', ['LED'])
        temp = ilum.get('temperatura', '4000K')
        tipos_texto = ", ".join(tipos) if isinstance(tipos, list) else str(tipos)
        return f"{tipos_texto} - {temp}"
    
    return "LED profissional"

def formatar_estilo(inspiracoes: Dict) -> str:
    """
    Formata estilo arquitetônico.
    """
    if not inspiracoes or 'estilo_identificado' not in inspiracoes:
        return "moderno e funcional"
    
    estilo = inspiracoes.get('estilo_identificado', {})
    if isinstance(estilo, dict):
        principal = estilo.get('principal', 'moderno').replace('_', ' ')
        secundario = estilo.get('secundario', '').replace('_', ' ')
        return f"{principal} com elementos {secundario}" if secundario else principal
    
    return "contemporâneo"

def extrair_areas_por_categoria(layout: Dict, categoria: str) -> str:
    """
    Lista áreas por categoria (interna/externa).
    """
    if not layout or 'areas' not in layout:
        return "depósito, copa" if categoria == 'interna' else "área de exposição"
    
    areas = []
    for area in layout.get('areas', []):
        if area.get('categoria') == categoria:
            subtipo = area.get('subtipo', '').replace('_', ' ')
            if subtipo:
                areas.append(subtipo)
    
    return ", ".join(areas) if areas else ("áreas de apoio" if categoria == 'interna' else "área principal")

def determinar_lado_perspectiva(layout: Dict) -> str:
    """
    Determina melhor lado para perspectiva.
    """
    if not layout or 'acessos' not in layout:
        return "direita"
    
    acessos = layout.get('acessos', {})
    if acessos.get('direita'):
        return "direita"
    elif acessos.get('esquerda'):
        return "esquerda"
    return "direita"

def formatar_lados_abertos(layout: Dict) -> str:
    """
    Lista lados abertos do estande.
    """
    if not layout or 'acessos' not in layout:
        return "frente"
    
    acessos = layout.get('acessos', {})
    lados = []
    
    nomes = {'frente': 'frente', 'direita': 'lateral direita', 
             'esquerda': 'lateral esquerda', 'fundo': 'fundo'}
    
    for lado, nome in nomes.items():
        if acessos.get(lado):
            lados.append(nome)
    
    if len(lados) == 0:
        return "frente"
    elif len(lados) == 1:
        return lados[0]
    elif len(lados) == 2:
        return f"{lados[0]} e {lados[1]}"
    else:
        return ", ".join(lados[:-1]) + f" e {lados[-1]}"

def formatar_mobiliario(briefing: Any, layout: Dict) -> str:
    """
    Lista mobiliário baseado no briefing.
    """
    mobiliario = []
    
    if briefing and hasattr(briefing, 'areas_exposicao'):
        for area in briefing.areas_exposicao.all():
            if area.tem_balcao_recepcao:
                mobiliario.append("balcão de recepção")
            if area.tem_mesas_atendimento:
                mobiliario.append("mesas de atendimento")
            if area.tem_lounge:
                mobiliario.append("lounge com sofás")
    
    if briefing and hasattr(briefing, 'salas_reuniao'):
        for sala in briefing.salas_reuniao.all():
            if sala.capacidade:
                mobiliario.append(f"mesa reunião ({sala.capacidade} lugares)")
    
    return ", ".join(mobiliario[:5]) if mobiliario else "balcão, expositores, mesas"

def formatar_equipamentos(briefing: Any) -> str:
    """
    Lista equipamentos tecnológicos.
    """
    equip = ["TVs LED", "tablets"]
    
    if briefing and hasattr(briefing, 'palcos'):
        for palco in briefing.palcos.all():
            if palco.tem_telao_tv:
                equip.append("telão")
            if palco.tem_sistema_som:
                equip.append("som profissional")
    
    return ", ".join(list(set(equip))[:5])  # Remove duplicatas