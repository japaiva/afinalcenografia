# gestor/services/conceito_visual_service.py
"""
Serviço para geração de prompts de conceito visual.

Este módulo contém a lógica de negócio para construir prompts completos
para geração de imagens de conceitos visuais usando DALL-E.
"""

import logging
from typing import Optional

from core.models import Agente
from projetos.models import Projeto

logger = logging.getLogger(__name__)


def gerar_prompt_completo(projeto: Projeto, prompt_customizado: Optional[str] = None) -> str:
    """
    Gera prompt final para DALL-E usando template de agente e dados do projeto.

    Esta função consolida informações de múltiplas fontes (briefing, layout identificado,
    inspirações visuais) em um prompt estruturado para geração de imagens.

    Args:
        projeto: Instância do modelo Projeto contendo todos os dados necessários
        prompt_customizado: Prompt opcional para substituir o template padrão

    Returns:
        String contendo o prompt completo formatado para DALL-E

    Raises:
        Não lança exceções - retorna fallback em caso de erros

    Example:
        >>> projeto = Projeto.objects.get(id=1)
        >>> prompt = gerar_prompt_completo(projeto)
        >>> print(len(prompt))
        1500

    Notes:
        - Usa template do agente "Agente de Imagem Principal" se disponível
        - Importa formatadores de gestor.services.prompt_formatters
        - Dimensões: usa medida_lateral ao invés de medida_fundo
        - Retorna template fallback mínimo se agente não encontrado
    """

    # 1. Se forneceu prompt customizado, retornar ele
    if prompt_customizado:
        return prompt_customizado

    # 2. Buscar APENAS o template (task_instructions)
    try:
        agente = Agente.objects.get(
            nome="Agente de Imagem Principal",
            tipo="individual",
            ativo=True
        )
        template = agente.task_instructions  # NÃO concatena com system_prompt

        if not template:
            raise ValueError("Template vazio")

    except (Agente.DoesNotExist, ValueError) as e:
        logger.error(f"Erro ao buscar template: {e}")
        # Template fallback mínimo mas completo
        template = """Estande [TIPO_STAND] para [EMPRESA], [LARGURA]×[PROFUNDIDADE]×3m.
Layout: [LAYOUT_AREAS_DETALHADO]
Design: [ESTILO_VISUAL]
Cores: [CORES_APLICADAS]
Materiais: [MATERIAIS_DETALHADOS]
Perspectiva 3/4 fotorrealística."""

    # 3. Carregar os 3 conjuntos de dados
    briefing = projeto.briefings.first()
    layout = projeto.layout_identificado or {}
    inspiracoes = projeto.inspiracoes_visuais or {}

    # 4. Importar TODOS os formatadores do arquivo correto
    try:
        from gestor.services.prompt_formatters import (
            interpretar_tipo_stand,
            interpretar_estrutura,
            interpretar_piso,
            formatar_layout_areas_detalhado,
            formatar_cores_aplicadas,
            formatar_materiais_detalhados,
            formatar_elementos_destaque,
            formatar_iluminacao,
            formatar_estilo,
            extrair_areas_por_categoria,
            determinar_lado_perspectiva,
            formatar_lados_abertos,
            formatar_mobiliario,
            formatar_equipamentos
        )
    except ImportError as e:
        logger.error(f"Erro ao importar formatadores: {e}")
        # Se não conseguir importar, usar funções inline básicas
        def interpretar_tipo_stand(t): return t
        def interpretar_estrutura(e): return e
        def interpretar_piso(p): return p
        def formatar_layout_areas_detalhado(l): return "Layout padrão"
        def formatar_cores_aplicadas(i): return "Cores padrão"
        def formatar_materiais_detalhados(i): return "Materiais padrão"
        def formatar_elementos_destaque(i): return "Elementos padrão"
        def formatar_iluminacao(i): return "LED 4000K"
        def formatar_estilo(i): return "moderno"
        def extrair_areas_por_categoria(l, c): return "áreas padrão"
        def determinar_lado_perspectiva(l): return "direita"
        def formatar_lados_abertos(l): return "frente"
        def formatar_mobiliario(b, l): return "mobiliário padrão"
        def formatar_equipamentos(b): return "equipamentos padrão"

    # 5. Processar dados básicos
    empresa = projeto.empresa.nome if projeto.empresa else ""
    feira = projeto.feira.nome if projeto.feira else ""
    local_evento = ""

    if projeto.feira:
        local_evento = f"{projeto.feira.local}, {projeto.feira.cidade}/{projeto.feira.estado}"

    # Dados do briefing com defaults
    if briefing:
        largura = str(briefing.medida_frente or 6)
        # Usar lateral (priorizar esquerda, depois direita)
        lateral = briefing.medida_lateral_esquerda or briefing.medida_lateral_direita or 8
        profundidade = str(lateral)
        area_total = str(briefing.area_estande or 48)
        objetivo = briefing.objetivo_estande or "exposição de produtos"
        tipo_stand = briefing.tipo_stand or "ilha"
        tipo_estrutura = briefing.material or "misto"
        piso_elevado = briefing.piso_elevado or "sem_elevacao"
    else:
        largura = "6"
        profundidade = "8"
        area_total = "48"
        objetivo = "exposição"
        tipo_stand = "ilha"
        tipo_estrutura = "misto"
        piso_elevado = "sem_elevacao"

    # 6. Criar dicionário de substituições
    replacements = {
        # === IDENTIFICAÇÃO ===
        "[EMPRESA]": empresa,
        "[OBJETIVO_ESTANDE]": objetivo,
        "[NOME_FEIRA]": feira,

        # === DIMENSÕES (dados diretos) ===
        "[LARGURA]": largura,
        "[PROFUNDIDADE]": profundidade,
        "[AREA_TOTAL]": area_total,

        # === TIPO STAND (interpretado) ===
        "[TIPO_STAND]": interpretar_tipo_stand(tipo_stand),

        # === LAYOUT (formatado do JSON) ===
        "[LAYOUT_AREAS_DETALHADO]": formatar_layout_areas_detalhado(layout),
        "[LADOS_ABERTOS]": formatar_lados_abertos(layout),
        "[AREAS_INTERNAS_LISTA]": extrair_areas_por_categoria(layout, 'interna'),
        "[AREAS_EXTERNAS_LISTA]": extrair_areas_por_categoria(layout, 'externa'),

        # === DESIGN (formatado do JSON) ===
        "[ESTILO_VISUAL]": formatar_estilo(inspiracoes),
        "[CORES_APLICADAS]": formatar_cores_aplicadas(inspiracoes),
        "[MATERIAIS_DETALHADOS]": formatar_materiais_detalhados(inspiracoes),
        "[ELEMENTOS_DESTAQUE]": formatar_elementos_destaque(inspiracoes),
        "[ILUMINACAO_TIPO]": formatar_iluminacao(inspiracoes),

        # === ESTRUTURA (interpretado) ===
        "[TIPO_ESTRUTURA]": interpretar_estrutura(tipo_estrutura),
        "[PISO_ESPECIFICACAO]": interpretar_piso(piso_elevado),

        # === PERSPECTIVA ===
        "[LADO_PERSPECTIVA]": determinar_lado_perspectiva(layout),

        # === OUTROS CAMPOS DO TEMPLATE ===
        "[LARGURA_CIRCULACAO]": "1.5",
        "[CONCEITO_DESIGN]": formatar_estilo(inspiracoes),
        "[TESTEIRA_SPEC]": "acrílico iluminado com logo",
        "[MATERIAL_DIVISORIAS]": "MDF com pintura",
        "[ALTURA_MAXIMA]": "3",
        "[PONTOS_ELETRICOS]": "distribuídos conforme layout",
        "[CLIMATIZACAO]": "ar condicionado central",
        "[SISTEMA_SOM]": "",
        "[LISTA_MOBILIARIO]": formatar_mobiliario(briefing, layout),
        "[LISTA_EQUIPAMENTOS]": formatar_equipamentos(briefing),
        "[DISPLAYS_ESPECIFICOS]": "displays de produtos",
        "[LOGO_POSICAO]": "testeira frontal",
        "[SINALIZACAO_TIPO]": "placas direcionais",
        "[COMUNICACAO_VISUAL]": "banners informativos",
        "[LOCAL_EVENTO]": local_evento,
    }

    # 7. Aplicar substituições
    prompt_final = template
    for key, value in replacements.items():
        prompt_final = prompt_final.replace(key, str(value))

    # 8. Limpar placeholders não substituídos
    import re
    placeholders_restantes = re.findall(r'\[([A-Z_]+)\]', prompt_final)
    if placeholders_restantes:
        logger.warning(f"Placeholders não substituídos: {placeholders_restantes}")
        # Remover placeholders vazios
        for placeholder in set(placeholders_restantes):
            prompt_final = prompt_final.replace(f"[{placeholder}]", "")

    # 9. Limpar espaços extras e linhas vazias
    linhas = [linha.strip() for linha in prompt_final.split('\n') if linha.strip()]
    prompt_final = '\n'.join(linhas)

    # 10. Log final
    logger.info(f"Prompt gerado: {len(prompt_final)} caracteres")

    return prompt_final
