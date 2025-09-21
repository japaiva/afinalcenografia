# gestor/views/conceito_visual.py
# VERSÃO COMPLETA COM FUNÇÕES DE FORMATAÇÃO

import json
import logging
import re
from typing import Dict, Any, List, Optional

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from core.decorators import gestor_required
from core.models import Agente
from projetos.models import Projeto

logger = logging.getLogger(__name__)

# ========================== Funções Helper Básicas ==========================

def _briefing(projeto: Projeto):
    """Retorna o primeiro briefing relacionado ao projeto."""
    return projeto.briefings.first() if hasattr(projeto, 'briefings') else None

def _arquivos(briefing_obj, tipo: str) -> List[Any]:
    """Retorna uma lista de arquivos do briefing por tipo."""
    if not briefing_obj:
        return []
    return list(briefing_obj.arquivos.filter(tipo=tipo))

def _run_agent(nome_agente: str, payload: Dict[str, Any], imagens: Optional[List[str]] = None) -> Dict[str, Any]:
    """Executa agente se disponível"""
    try:
        from .agents_crews import run_agent as RUN_AGENT_EXECUTOR
        resultado = RUN_AGENT_EXECUTOR(nome_agente, payload, imagens)
        if not resultado or "erro" in resultado:
            return {"erro": resultado.get("erro", "Agente não retornou resultado válido"), "sucesso": False}
        return resultado
    except Exception as e:
        logger.error(f"Erro ao executar agente: {str(e)}")
        return {"erro": f"Sistema de agentes não disponível", "sucesso": False}

# ========================== Funções de Formatação para Prompt ==========================

def formatar_layout_areas(layout_json: Dict) -> str:
    """
    Formata o JSON do layout em descrição textual das áreas
    Separa áreas visíveis de áreas internas
    """
    if not layout_json or 'areas' not in layout_json:
        return "Área de exposição principal com balcão de atendimento"
    
    texto = []
    areas = layout_json.get('areas', [])
    acessos = layout_json.get('acessos', {})
    
    # Informar lados abertos
    lados_abertos = [lado.capitalize() for lado, aberto in acessos.items() if aberto]
    if lados_abertos:
        texto.append(f"Estande aberto pelos lados: {', '.join(lados_abertos)}\n")
    
    # Separar áreas por categoria e posição
    areas_apoio = []
    areas_visiveis = []
    
    for area in areas:
        nome = area.get('subtipo', 'área').replace('_', ' ')
        m2 = area.get('m2_estimado', 0)
        categoria = area.get('categoria', 'externa')
        
        # Determinar posição baseado em bbox_norm
        bbox = area.get('bbox_norm', {})
        y_pos = bbox.get('y', 0.5)
        
        if categoria == 'interna':
            # Áreas internas (não aparecem na imagem)
            posicao = "fundo" if y_pos < 0.3 else "lateral"
            areas_apoio.append(f"• {nome} ({m2:.0f}m²) - {posicao} [área fechada]")
        else:
            # Áreas visíveis
            areas_visiveis.append(f"• {nome} ({m2:.0f}m²)")
    
    # Montar texto final
    if areas_visiveis:
        texto.append("Áreas principais (visíveis na renderização):")
        texto.extend(areas_visiveis)
    
    if areas_apoio:
        texto.append("\nÁreas de apoio (internas/não visíveis):")
        texto.extend(areas_apoio)
    
    # Adicionar insights de circulação se existirem
    insights_circ = layout_json.get('insights', {}).get('circulacao', [])
    if insights_circ and insights_circ[0]:
        texto.append(f"\n{insights_circ[0].get('descricao', '')}")
    
    return "\n".join(texto)

def formatar_cores_aplicadas(inspiracoes_json: Dict) -> str:
    """
    Formata cores com suas aplicações específicas
    """
    if not inspiracoes_json or 'cores_predominantes' not in inspiracoes_json:
        return "• #FFFFFF - acabamentos\n• #0066CC - destaques\n• #333333 - estrutura"
    
    cores_texto = []
    for cor in inspiracoes_json.get('cores_predominantes', [])[:5]:  # Máximo 5 cores
        hex_cor = cor.get('hex', '')
        uso = cor.get('uso', 'geral')
        if hex_cor:
            cores_texto.append(f"• {hex_cor} - {uso}")
    
    return "\n".join(cores_texto) if cores_texto else "• Paleta corporativa padrão"

def formatar_materiais_detalhados(inspiracoes_json: Dict) -> str:
    """
    Formata materiais com onde serão aplicados
    """
    if not inspiracoes_json or 'materiais_sugeridos' not in inspiracoes_json:
        return "• Madeira clara - estrutura e acabamentos\n• Vidro temperado - divisórias\n• Metal escovado - detalhes"
    
    materiais_texto = []
    for mat in inspiracoes_json.get('materiais_sugeridos', []):
        material = mat.get('material', '').replace('_', ' ')
        aplicacao = mat.get('aplicacao', 'acabamento')
        if material:
            materiais_texto.append(f"• {material} - {aplicacao}")
    
    return "\n".join(materiais_texto) if materiais_texto else "• Materiais corporativos padrão"

def formatar_elementos_destaque(inspiracoes_json: Dict) -> str:
    """
    Lista elementos visuais de destaque
    """
    if not inspiracoes_json or 'elementos_destaque' not in inspiracoes_json:
        return "• Logo corporativo iluminado\n• Displays de produtos\n• Balcão de atendimento"
    
    elementos = inspiracoes_json.get('elementos_destaque', [])
    if elementos:
        return "\n".join([f"• {elem}" for elem in elementos[:6]])  # Máximo 6 elementos
    
    return "• Logo iluminado\n• Vitrines\n• Displays"

def formatar_iluminacao(inspiracoes_json: Dict) -> str:
    """
    Especifica tipo e temperatura de iluminação
    """
    if not inspiracoes_json or 'iluminacao' not in inspiracoes_json:
        return "LED profissional 4000K"
    
    ilum = inspiracoes_json.get('iluminacao', {})
    tipos = ilum.get('tipos', ['LED geral'])
    temperatura = ilum.get('temperatura', '4000K')
    
    tipos_texto = ", ".join(tipos) if tipos else "LED profissional"
    return f"{tipos_texto} - {temperatura}"

def determinar_lado_perspectiva(layout_json: Dict) -> str:
    """
    Determina qual lado mostrar na perspectiva baseado nos acessos
    """
    if not layout_json or 'acessos' not in layout_json:
        return "direita"
    
    acessos = layout_json.get('acessos', {})
    
    # Prioridade: direita > esquerda > qualquer outro
    if acessos.get('direita'):
        return "direita"
    elif acessos.get('esquerda'):
        return "esquerda"
    elif acessos.get('fundo'):
        return "fundo"
    
    return "direita"

# ========================== Função Principal: Gerar Prompt ==========================

def gerar_prompt_completo(projeto: Projeto, template: Optional[str] = None) -> str:
    """
    Gera o prompt final combinando template do agente com dados do projeto
    Usa as funções de formatação para trabalhar com os JSONs
    """
    # 1. Obter template
    if not template:
        try:
            agente = Agente.objects.get(
                nome="Agente de Imagem Principal", 
                tipo="individual", 
                ativo=True
            )
            system = agente.llm_system_prompt or ""
            task = agente.task_instructions or ""
            template = f"{system}\n\n{task}" if system or task else None
            logger.info(f"Template carregado do banco: {len(template) if template else 0} chars")
        except Agente.DoesNotExist:
            logger.warning("Agente 'Agente de Imagem Principal' não encontrado no banco")
            template = None
    
    # Se não tem template, usar o template NOVO e SIMPLIFICADO
    if not template:
        template = """Crie uma renderização fotorrealística de estande para feira comercial seguindo estas especificações:

DADOS DO PROJETO:
Empresa: [EMPRESA]
Dimensões: [LARGURA]m (frente) × [PROFUNDIDADE]m (fundo) × 3m (altura)
Área total: [AREA_TOTAL]m²
Tipo de stand: [TIPO_STAND]
Objetivo: [OBJETIVO_ESTANDE]

LAYOUT ESPACIAL (conforme esboço analisado):
[LAYOUT_AREAS]

DESIGN VISUAL (conforme referências analisadas):
Paleta de cores:
[CORES_APLICADAS]

Estilo arquitetônico: [ESTILO_VISUAL]

Materiais e acabamentos:
[MATERIAIS_DETALHADOS]

Elementos de destaque:
[ELEMENTOS_DESTAQUE]

ESPECIFICAÇÕES TÉCNICAS:
- Estrutura: [TIPO_ESTRUTURA]
- Piso: [PISO_ESPECIFICACAO]
- Iluminação: [ILUMINACAO_TIPO]

REQUISITOS DA IMAGEM:
- Perspectiva 3/4 mostrando frente principal e lateral [LADO_PERSPECTIVA]
- Respeitar fielmente o layout mapeado no esboço
- Aplicar cores exatamente onde indicado na análise
- Incluir apenas áreas visíveis (não mostrar interior de depósitos/copas)
- Ambiente de feira comercial com visitantes interagindo
- Iluminação profissional de centro de convenções
- Qualidade fotorrealística em alta resolução
- Acabamento premium e contemporâneo

Gere uma imagem que represente fielmente este briefing técnico."""
    
    # 2. Carregar dados do projeto
    briefing = projeto.briefings.first()
    layout = projeto.layout_identificado or {}
    inspiracoes = projeto.inspiracoes_visuais or {}
    
    # 3. Preparar dados básicos
    empresa_nome = "Empresa"
    descricao_empresa = ""
    if hasattr(projeto, 'empresa'):
        empresa_nome = projeto.empresa.nome or "Empresa"
        if hasattr(projeto.empresa, 'descricao'):
            descricao_empresa = projeto.empresa.descricao or ""
    
    largura = "6"
    profundidade = "8"
    area_total = "48"
    objetivo = "exposição de produtos e networking"
    tipo_stand = "ilha"
    tipo_estrutura = "mista"
    piso_spec = "nivelado - carpete"
    
    if briefing:
        largura = str(briefing.medida_frente or 6)
        profundidade = str(briefing.medida_fundo or 8)
        area_total = str(briefing.area_estande or (float(largura) * float(profundidade)))
        objetivo = briefing.objetivo_estande or briefing.objetivo_evento or objetivo
        
        # Tipo de stand
        if hasattr(briefing, 'get_tipo_stand_display'):
            tipo_stand = briefing.get_tipo_stand_display()
        elif hasattr(briefing, 'tipo_stand'):
            tipo_stand = briefing.tipo_stand or "ilha"
        
        # Tipo de estrutura/material
        if hasattr(briefing, 'get_material_display'):
            tipo_estrutura = briefing.get_material_display()
        elif hasattr(briefing, 'material'):
            tipo_estrutura = briefing.material or "mista"
        
        # Especificação do piso
        piso_elevado = "nivelado"
        if hasattr(briefing, 'get_piso_elevado_display'):
            piso_elevado = briefing.get_piso_elevado_display()
        elif hasattr(briefing, 'piso_elevado'):
            piso_elevado = briefing.piso_elevado or "sem elevação"
        
        piso_spec = f"{piso_elevado}"
    
    # Estilo visual das inspirações
    estilo = "moderno e profissional"
    if inspiracoes.get('estilo_identificado'):
        estilo_data = inspiracoes['estilo_identificado']
        if isinstance(estilo_data, dict):
            principal = estilo_data.get('principal', '').replace('_', ' ')
            secundario = estilo_data.get('secundario', '').replace('_', ' ')
            if principal:
                estilo = principal
                if secundario:
                    estilo += f" com toques {secundario}"
    
    # 4. Dicionário de substituições COMPLETO (para compatibilidade com template antigo)
    replacements = {
        # Dados básicos do projeto
        "[EMPRESA]": empresa_nome,
        "[LARGURA]": largura,
        "[PROFUNDIDADE]": profundidade,
        "[AREA_TOTAL]": area_total,
        "[TIPO_STAND]": tipo_stand,
        "[OBJETIVO_ESTANDE]": objetivo,
        
        # Layout formatado do esboço
        "[LAYOUT_AREAS]": formatar_layout_areas(layout),
        
        # Design visual das referências
        "[CORES_APLICADAS]": formatar_cores_aplicadas(inspiracoes),
        "[ESTILO_VISUAL]": estilo,
        "[MATERIAIS_DETALHADOS]": formatar_materiais_detalhados(inspiracoes),
        "[ELEMENTOS_DESTAQUE]": formatar_elementos_destaque(inspiracoes),
        
        # Especificações técnicas
        "[TIPO_ESTRUTURA]": tipo_estrutura,
        "[PISO_ESPECIFICACAO]": piso_spec,
        "[ILUMINACAO_TIPO]": formatar_iluminacao(inspiracoes),
        
        # Perspectiva da imagem
        "[LADO_PERSPECTIVA]": determinar_lado_perspectiva(layout),
        
        # PLACEHOLDERS DO TEMPLATE ANTIGO (para compatibilidade)
        "[DESCRICAO_EMPRESA]": descricao_empresa[:200] if descricao_empresa else "",
        "[SETOR]": "cosméticos" if "cosmético" in empresa_nome.lower() else "corporativo",
        "[SETOR_EMPRESA]": "cosméticos" if "cosmético" in empresa_nome.lower() else "corporativo",
        "[ALTURA]": "3",
        "[TIPO]": tipo_stand,
        "[TIPO_ESTANDE]": tipo_stand,
        "[POSICIONAMENTO]": "posição estratégica com alta visibilidade",
        "[AREAS_INTERNAS]": "depósito, workshop",
        "[AREAS_EXTERNAS]": "área de exposição",
        "[AREAS_FUNCIONAIS]": "área de exposição principal",
        "[LISTA_AREAS_INTERNAS]": "depósito, workshop",
        "[PISO_ELEVADO]": piso_elevado,
        "[ALTURA_PISO]": "3" if "3cm" in piso_spec else "0",
        "[MATERIAL_PISO]": "carpete",
        "[TIPO_TESTEIRA]": "reta",
        "[MATERIAL_TESTEIRA]": "acrílico iluminado com logo",
        "[ALTURA_DIVISORIAS]": "2.5",
        "[REFERENCIAS]": f"Estilo {estilo}",
        "[CONCEITO_INTEGRADO]": f"Estande {estilo} para {empresa_nome}",
        "[LARGURA_CIRCULACAO]": "1.5",
        "[TIPO_PISO]": "elevado" if "elevado" in piso_elevado.lower() else "nivelado",
        "[ELEVACAO_PISO]": piso_elevado,
        "[TIPO_ILUMINACAO]": formatar_iluminacao(inspiracoes),
        "[CORES_PRINCIPAIS]": formatar_cores_aplicadas(inspiracoes).replace("\n", ", ").replace("• ", ""),
        "[MATERIAIS_PRINCIPAIS]": formatar_materiais_detalhados(inspiracoes).replace("\n", ", ").replace("• ", ""),
        "[LISTA_MOBILIARIO]": "balcão recepção, expositores, mesas",
        "[LISTA_EQUIPAMENTOS]": "TVs LED, tablets",
        "[ELEMENTOS_DECORATIVOS]": formatar_elementos_destaque(inspiracoes).replace("\n", ", ").replace("• ", ""),
        "[CARACTERISTICAS_ESPECIFICAS]": estilo,
    }
    
    # 5. Substituir todos os placeholders
    prompt_final = template
    for placeholder, valor in replacements.items():
        if placeholder in prompt_final:
            prompt_final = prompt_final.replace(placeholder, str(valor))
    
    # 6. Verificar placeholders não substituídos (debug)
    placeholders_restantes = re.findall(r'\[[A-Z_]+\]', prompt_final)
    if placeholders_restantes:
        logger.warning(f"Placeholders não substituídos: {set(placeholders_restantes)}")
    
    logger.info(f"Prompt final gerado: {len(prompt_final)} caracteres")
    
    return prompt_final

# ========================== Views HTTP ==========================

@login_required
@gestor_required
@require_GET
def conceito_visual(request: HttpRequest, projeto_id: int) -> HttpResponse:
    """
    Tela principal do Conceito Visual
    Renderiza o template HTML com os dados do projeto
    """
    projeto = get_object_or_404(Projeto, pk=projeto_id)
    
    # Verificar se tem briefing
    if not hasattr(projeto, 'briefings') or not projeto.briefings.exists():
        messages.error(request, "Este projeto não possui briefing.")
        return redirect("gestor:projeto_detail", pk=projeto_id)
    
    brief = _briefing(projeto)
    arquivos_planta = _arquivos(brief, "planta")
    arquivos_referencia = _arquivos(brief, "referencia")
    
    context = {
        "projeto": projeto,
        "briefing": brief,
        "arquivos_planta": arquivos_planta,
        "arquivos_referencia": arquivos_referencia,
        "tem_esbocos": bool(arquivos_planta),
        "tem_referencias": bool(arquivos_referencia),
    }
    
    return render(request, "gestor/conceito_visual.html", context)

@login_required
@gestor_required
@require_POST
def conceito_etapa1_esboco(request: HttpRequest, projeto_id: int) -> JsonResponse:
    """
    Etapa 1: Análise do esboço de planta
    Extrai layout, áreas e dimensões
    """
    projeto = get_object_or_404(Projeto, pk=projeto_id)
    brief = _briefing(projeto)
    
    if not brief:
        return JsonResponse({"sucesso": False, "erro": "Briefing não encontrado."}, status=400)
    
    # Verificar arquivos de planta
    esbocos = brief.arquivos.filter(tipo="planta")
    if not esbocos.exists():
        return JsonResponse({"sucesso": False, "erro": "Nenhum esboço de planta encontrado."}, status=400)
    
    esboco = esbocos.first()
    
    # Preparar payload para o agente
    payload = {
        "projeto_id": projeto.id,
        "briefing_id": brief.id,
        "briefing": {
            "tipo_stand": brief.tipo_stand,
            "medida_frente_m": float(brief.medida_frente) if brief.medida_frente else None,
            "medida_fundo_m": float(brief.medida_fundo) if brief.medida_fundo else None,
            "altura_m": 3.0,
        }
    }
    
    # Executar agente de análise
    resultado = _run_agent("Analisador de Esboços de Planta", payload, imagens=[esboco.arquivo.url])
    
    if "erro" in resultado:
        return JsonResponse({"sucesso": False, "erro": resultado["erro"]}, status=400)
    
    # Salvar resultado no projeto
    projeto.layout_identificado = resultado
    projeto.save(update_fields=["layout_identificado"])
    
    logger.info(f"Layout identificado para projeto {projeto_id}: {len(str(resultado))} chars")
    
    return JsonResponse({
        "sucesso": True,
        "layout": resultado,
        "arquivo": {
            "nome": esboco.nome or esboco.arquivo.name,
            "url": esboco.arquivo.url,
        },
        "processado_em": timezone.now().isoformat(),
    })

@login_required
@gestor_required
@require_POST
def conceito_etapa2_referencias(request: HttpRequest, projeto_id: int) -> JsonResponse:
    """
    Etapa 2: Análise das referências visuais
    Extrai cores, estilos, materiais e inspirações
    """
    projeto = get_object_or_404(Projeto, pk=projeto_id)
    brief = _briefing(projeto)
    
    if not brief:
        return JsonResponse({"sucesso": False, "erro": "Briefing não encontrado."}, status=400)
    
    # Verificar arquivos de referência
    refs = brief.arquivos.filter(tipo="referencia")
    if not refs.exists():
        return JsonResponse({"sucesso": False, "erro": "Nenhuma imagem de referência encontrada."}, status=400)
    
    # Coletar URLs das imagens
    imagens = [ref.arquivo.url for ref in refs if ref.arquivo]
    
    # Preparar payload para o agente
    payload = {
        "projeto_id": projeto.id,
        "marca": projeto.empresa.nome if hasattr(projeto, 'empresa') else None
    }
    
    # Executar agente de análise visual
    resultado = _run_agent("Analisador de Referências Visuais", payload, imagens=imagens)
    
    if "erro" in resultado:
        return JsonResponse({"sucesso": False, "erro": resultado["erro"]}, status=400)
    
    # Salvar resultado no projeto
    projeto.inspiracoes_visuais = resultado
    projeto.save(update_fields=["inspiracoes_visuais"])
    
    logger.info(f"Inspirações identificadas para projeto {projeto_id}: {len(str(resultado))} chars")
    
    return JsonResponse({
        "sucesso": True,
        "inspiracoes": resultado,
        "quantidade_imagens": len(imagens),
        "processado_em": timezone.now().isoformat(),
    })

@login_required
@gestor_required
@require_POST
def conceito_etapa3_geracao(request: HttpRequest, projeto_id: int) -> JsonResponse:
    """
    Etapa 3: Geração do conceito visual
    Gera o prompt e chama o serviço DALL-E
    """
    projeto = get_object_or_404(Projeto, pk=projeto_id)
    
    # Verificar pré-requisitos
    if not projeto.layout_identificado:
        return JsonResponse({
            "sucesso": False,
            "erro": "Layout não encontrado. Execute a Etapa 1 primeiro."
        }, status=400)
    
    if not projeto.inspiracoes_visuais:
        return JsonResponse({
            "sucesso": False,
            "erro": "Inspirações não encontradas. Execute a Etapa 2 primeiro."
        }, status=400)
    
    # Verificar se veio prompt customizado do usuário
    body = json.loads(request.body or "{}")
    prompt_customizado = body.get("prompt")
    
    # Gerar ou usar prompt
    if prompt_customizado:
        prompt_final = prompt_customizado
        logger.info(f"Usando prompt customizado do usuário: {len(prompt_customizado)} chars")
    else:
        prompt_final = gerar_prompt_completo(projeto)
        logger.info(f"Prompt gerado automaticamente: {len(prompt_final)} chars")
    
    # Validar prompt
    if not prompt_final or len(prompt_final) < 50:
        return JsonResponse({
            "sucesso": False,
            "erro": "Prompt inválido ou muito curto"
        }, status=400)
    
    # Chamar serviço DALL-E
    from gestor.services.conceito_visual_dalle import ConceitoVisualDalleService
    dalle_service = ConceitoVisualDalleService()
    
    briefing = projeto.briefings.first()
    resultado = dalle_service.gerar_conceito_visual(
        briefing,
        projeto.layout_identificado,
        projeto.inspiracoes_visuais,
        prompt_customizado=prompt_final
    )
    
    if resultado["sucesso"]:
        # Salvar dados no projeto
        if not projeto.layout_identificado:
            projeto.layout_identificado = {}
        
        # Salvar URL da imagem e prompt no layout_identificado
        projeto.layout_identificado['conceito_visual_url'] = resultado["image_url"]
        projeto.layout_identificado['conceito_visual_prompt'] = resultado["prompt_usado"]
        projeto.layout_identificado['conceito_visual_data'] = timezone.now().isoformat()
        
        # Se houver prompt revisado pelo DALL-E, salvar também
        if resultado.get("prompt_revisado"):
            projeto.layout_identificado['conceito_visual_prompt_revisado'] = resultado["prompt_revisado"]
        
        # Marcar como processado
        projeto.analise_visual_processada = True
        projeto.data_analise_visual = timezone.now()
        projeto.save()
        
        logger.info(f"Conceito visual gerado para projeto {projeto_id}")
        
        return JsonResponse({
            "sucesso": True,
            "image_url": resultado["image_url"],
            "prompt_usado": resultado["prompt_usado"],
            "modelo": resultado.get("modelo", "dall-e-3"),
            "processado_em": timezone.now().isoformat()
        })
    else:
        logger.error(f"Erro ao gerar conceito para projeto {projeto_id}: {resultado.get('erro')}")
        return JsonResponse({
            "sucesso": False,
            "erro": resultado.get("erro", "Erro ao gerar imagem"),
            "tipo_erro": resultado.get("tipo_erro", "unknown")
        }, status=400)