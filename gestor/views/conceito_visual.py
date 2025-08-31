# gestor/views/conceito_visual.py
# -----------------------------------------------------------------------------
# CONCEITO VISUAL - Fluxo em 3 botões:
#  1) Etapa 1: Analisar Esboço (CV)  -> salva em projeto.layout_identificado
#  2) Etapa 2: Referências + Consolidação (+ Prompt Final)
#        - Analisa referências (CV)   -> projeto.inspiracoes_visuais
#        - Consolida com briefing+A1  -> projeto.dados_consolidados
#        - Monta prompt final         -> projeto.prompt_final
#  3) Etapa 3: Geração de imagem (DALL·E / fallback)
#        - Usa projeto.prompt_final   -> projeto.analise_visual_processada=True
#
# Observações:
# - Tudo que for "simulado" está isolado e fácil de trocar por integração real.
# - Respostas JSON incluem 'sucesso' e retornam o resultado para a UI.
# - Flags visuais na UI podem ler do front, mas aqui já persistimos os estados.
# -----------------------------------------------------------------------------

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional, Tuple

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from core.decorators import gestor_required
from core.models import Agente
from projetos.models import Projeto  # ajuste se o caminho do modelo for diferente

# ============================== Helpers de dados ==============================

def _briefing(projeto: Projeto):
    # Adeque conforme seu relacionamento real
    return getattr(projeto, "briefings", None).first()

def _arquivos(briefing_obj, tipo: str) -> List[Any]:
    """Retorna QuerySet de arquivos do briefing por tipo ('planta' | 'referencia')."""
    if not briefing_obj:
        return []
    return list(briefing_obj.arquivos.filter(tipo=tipo))

def _float_or(value, default):
    try:
        return float(value) if value is not None else default
    except Exception:
        return default

# ======================== Fallbacks/Simulações controladas ====================

def _stub_layout(brief) -> Dict[str, Any]:
    return {
        "tipo_estande": getattr(brief, "tipo_stand", None) or "ponta_de_ilha",
        "dimensoes_detectadas": {
            "largura": _float_or(getattr(brief, "medida_frente", None), 6),
            "profundidade": _float_or(getattr(brief, "medida_fundo", None), 8),
            "altura": _float_or(getattr(brief, "altura_maxima", None), 4),
        },
        "areas": {
            "area_principal": {"posicao": "centro", "tipo": "exposicao", "tamanho_estimado": 30},
            "area_reuniao": {"posicao": "superior_direita", "tipo": "fechada", "tamanho_estimado": 12},
        },
        "circulacao_principal": "centro_vertical",
        "acessos": ["frente"],
        "confidence": 0.8,
        "processado_em": timezone.now().isoformat(),
    }

def _stub_inspiracoes(brief, referencias_qs) -> Dict[str, Any]:
    return {
        "estilo_identificado": {"principal": "contemporaneo_clean", "secundario": "nature_inspired"},
        "cores_hex": [
            {"hex": "#F4F1EC", "uso": "painéis/ripados"},
            {"hex": "#6DB37F", "uso": "parede verde/acento"},
            {"hex": "#1A1A1A", "uso": "contraste/logotipia"},
        ],
        "materiais_sugeridos": [
            {"nome": "ripado_madeira_clara", "tag": "revestimento"},
            {"nome": "marmorite_bege_claro", "tag": "piso"},
            {"nome": "perfis_aluminio_branco", "tag": "estrutura"},
            {"nome": "led_linear_embutido_4000K", "tag": "iluminacao"},
        ],
        "elementos_destaque": ["parede verde iluminada", "logo volumétrico frontal", "nichos iluminados"],
        "iluminacao": {"temperatura": "4000K", "solucoes": ["rasgos no forro", "pendentes no lounge"]},
        "riscos_e_mitigacoes": [{"risco": "ofuscamento LED", "mitigacao": "usar difusor/controle de brilho"}],
        "confidence": 0.85 if referencias_qs else 0.3,
        "arquivos_analisados": [getattr(ref, "nome", getattr(ref, "arquivo", "")) for ref in referencias_qs],
        "processado_em": timezone.now().isoformat(),
    }

def _consolidar(brief, layout: Dict[str, Any], inspiracoes: Dict[str, Any]) -> Dict[str, Any]:
    largura = layout.get("dimensoes_detectadas", {}).get("largura")
    profundidade = layout.get("dimensoes_detectadas", {}).get("profundidade")
    altura = layout.get("dimensoes_detectadas", {}).get("altura")

    if largura is None: largura = _float_or(getattr(brief, "medida_frente", None), 6)
    if profundidade is None: profundidade = _float_or(getattr(brief, "medida_fundo", None), 8)
    if altura is None: altura = _float_or(getattr(brief, "altura_maxima", None), 4)

    paleta = [c.get("hex") for c in inspiracoes.get("cores_hex", []) if c.get("hex")]
    if not paleta:
        paleta = ["#FFFFFF", "#1A1A1A"]

    dataset = {
        "dimensoes": {
            "largura_m": float(largura),
            "profundidade_m": float(profundidade),
            "altura_m": float(altura),
            "assuncao_dimensional": any([
                getattr(brief, "medida_frente", None) is None,
                getattr(brief, "medida_fundo", None) is None
            ]),
        },
        "tipo_estande": layout.get("tipo_estande") or getattr(brief, "tipo_stand", None) or "desconhecido",
        "zonas": [],
        "circulacao": {"min_m": 1.2, "rotas": layout.get("circulacao", [])},
        "paleta_final_hex": paleta,
        "riscos": inspiracoes.get("riscos_e_mitigacoes", []),
        "pronto_para_geracao": True,
    }

    # Converte "areas" do layout em "zonas"
    for nome, a in (layout.get("areas") or {}).items():
        dataset["zonas"].append({
            "nome": nome,
            "bbox_norm": a.get("bbox_norm", {"x": 0, "y": 0, "w": 1, "h": 1}),
            "materiais": [m.get("nome") for m in inspiracoes.get("materiais_sugeridos", []) if m.get("nome")],
            "elementos": inspiracoes.get("elementos_destaque", []),
            "cores_hex": paleta[:2],
        })

    return dataset

def _montar_prompt(brief, dataset: Dict[str, Any], inspiracoes: Dict[str, Any]) -> str:
    W = dataset["dimensoes"]["largura_m"]
    D = dataset["dimensoes"]["profundidade_m"]
    H = dataset["dimensoes"]["altura_m"]
    tipo = dataset.get("tipo_estande", "desconhecido")
    setores = getattr(brief, "setor_atuacao", None) or "não informado"

    areas_txt = "\n".join(f"- {z.get('nome')}" for z in dataset.get("zonas", [])) or "- (não informado)"
    materiais = []
    for z in dataset.get("zonas", []):
        for m in z.get("materiais", []):
            if m not in materiais:
                materiais.append(m)
    cores = ", ".join(dataset.get("paleta_final_hex", []))
    estilo_extra = (inspiracoes.get("estilo_identificado", {}).get("principal") or "contemporaneo").replace("_", " ")

    prompt = f"""
Você é um especialista em cenografia para feiras de negócios. Crie uma imagem de estande seguindo este raciocínio passo a passo:

*ETAPA 1 - ANÁLISE DE OBJETIVOS E IDENTIDADE*
Objetivo do estande: {getattr(brief, 'objetivo_estande', None) or "não informado"}
Descrição da empresa: {getattr(brief, 'descricao_empresa', None) or "não informado"}
Setor de atuação: {setores}

*ETAPA 2 - ANÁLISE ESPACIAL*
Dimensões: {W}m x {D}m
Altura máxima: {H}m
Tipo de estande: {tipo}
Posição nos corredores: {getattr(brief, 'posicionamento', None) or "não informado"}

*ETAPA 3 - CÁLCULO DE ÁREAS INTERNAS*
Áreas internas:
{areas_txt}
Priorize: circulação principal >= 1,2m, funcionalidade e harmonia visual.

*ETAPA 4 - ESTRUTURA E MATERIAIS*
Estrutura: personalizada/modular (ajuste conforme necessidade)
Piso: (conforme inspiração)
Testeira: (conforme inspiração)
Altura das divisórias: {getattr(brief, 'altura_divisorias', None) or "padrão"}

*ETAPA 5 - FUNCIONALIDADES E ÁREAS EXTERNAS*
Áreas de ativação: recepção, exposição de produtos, possíveis áreas instagramáveis
Referências visuais consideradas: paleta e estilo consolidados

*PROMPT FINAL PARA IA:*
Crie uma imagem realística 3/4 em alta resolução de um estande de feira de negócios com as seguintes características:

Conceito: {(getattr(brief, 'objetivo_estande', None) or "atrair leads qualificados")} alinhado à identidade da marca
Dimensões: {W}m x {D}m x {H}m, tipo {tipo}
Layout: Áreas internas distribuídas conforme zonas, com circulação principal >= 1,2m
Estrutura: {", ".join(materiais) if materiais else "materiais a partir das inspirações"}, iluminação coerente (4000K)
Elementos visuais: paleta de cores {cores}
Estilo: Moderno, profissional, acolhedor, {estilo_extra}

Renderize em perspectiva 3/4 mostrando a fachada principal e uma lateral, com pessoas interagindo naturalmente no espaço, iluminação de feira comercial realística, acabamento fotorrealístico.
""".strip()
    return prompt

def _gerar_imagem_stub(prompt: str, projeto_id: int) -> Tuple[str, str]:
    """
    Fallback local: gera PNG simples com o prompt impresso (para validação do fluxo).
    """
    from PIL import Image, ImageDraw

    media_root = getattr(settings, "MEDIA_ROOT", os.path.join(settings.BASE_DIR, "media"))
    media_url = getattr(settings, "MEDIA_URL", "/media/")
    out_dir = os.path.join(media_root, "conceitos")
    os.makedirs(out_dir, exist_ok=True)

    ts = timezone.now().strftime("%Y%m%d_%H%M%S")
    fn = f"conceito_{projeto_id}_{ts}.png"
    out_path = os.path.join(out_dir, fn)

    W, H = 1280, 720
    img = Image.new("RGB", (W, H), (245, 245, 245))
    d = ImageDraw.Draw(img)

    d.text((20, 20), "Conceito Visual (stub)", fill=(20, 20, 20))
    y = 60
    wrap_w = 95
    words = (prompt or "")[:2000].split()
    line = []
    for w in words:
        if len(" ".join(line + [w])) > wrap_w:
            d.text((20, y), " ".join(line), fill=(40, 40, 40))
            y += 20
            line = [w]
        else:
            line.append(w)
    if line:
        d.text((20, y), " ".join(line), fill=(40, 40, 40))

    img.save(out_path, "PNG")
    url = f"{media_url}conceitos/{fn}"
    return url, url

# =================================== Views ===================================

@login_required
@gestor_required
@require_GET
def conceito_visual(request: HttpRequest, projeto_id: int) -> HttpResponse:
    """
    Tela principal do Conceito Visual
    """
    projeto = get_object_or_404(Projeto, pk=projeto_id)

    if not getattr(projeto, "has_briefing", False):
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
    Etapa 1: Análise do esboço (A1)
    """
    projeto = get_object_or_404(Projeto, pk=projeto_id)
    brief = _briefing(projeto)
    if not brief:
        return JsonResponse({"sucesso": False, "erro": "Briefing não encontrado."}, status=400)

    # Agente opcional (se quiser validar existência)
    try:
        Agente.objects.get(nome="Analisador de Esboços de Planta", tipo="individual", ativo=True)
    except Agente.DoesNotExist:
        # Não bloqueia; seguimos com stub
        pass

    esbocos = _arquivos(brief, "planta")
    if not esbocos:
        return JsonResponse({"sucesso": False, "erro": "Nenhum esboço de planta encontrado."}, status=400)

    # TODO: substituir por chamada real ao agente de visão
    layout = _stub_layout(brief)

    # Persistir no projeto
    projeto.layout_identificado = layout
    projeto.save(update_fields=["layout_identificado"])

    return JsonResponse({
        "sucesso": True,
        "layout": layout,
        "arquivo_analisado": getattr(esbocos[0], "nome", getattr(esbocos[0], "arquivo", "")),
        "calculado": True,
        "processado_em": timezone.now().isoformat(),
    })

@login_required
@gestor_required
@require_POST
def conceito_etapa2_referencias(request: HttpRequest, projeto_id: int) -> JsonResponse:
    """
    Etapa 2: Referências (A2) + Consolidação (A3) + Prompt Final
    """
    projeto = get_object_or_404(Projeto, pk=projeto_id)
    brief = _briefing(projeto)
    if not brief:
        return JsonResponse({"sucesso": False, "erro": "Briefing não encontrado."}, status=400)

    # Validar existência do agente (não bloqueante)
    try:
        Agente.objects.get(nome="Analisador de Referências Visuais", tipo="individual", ativo=True)
    except Agente.DoesNotExist:
        pass

    refs = _arquivos(brief, "referencia")

    # Inspirações (CV)
    inspiracoes = _stub_inspiracoes(brief, refs)

    # Layout: pegar o que veio da etapa 1 (se existir) ou usar stub
    try:
        body = json.loads(request.body or "{}")
    except Exception:
        body = {}

    layout = body.get("layout") or getattr(projeto, "layout_identificado", None) or _stub_layout(brief)

    # Consolidação (A3) local
    dataset = _consolidar(brief, layout, inspiracoes)
    dataset["projeto_id"] = projeto.id

    # Prompt Final
    prompt_final = _montar_prompt(brief, dataset, inspiracoes)

    # Persistir no projeto (flags de "calculado")
    projeto.inspiracoes_visuais = inspiracoes
    projeto.dados_consolidados = dataset
    projeto.prompt_final = prompt_final
    projeto.save(update_fields=["inspiracoes_visuais", "dados_consolidados", "prompt_final"])

    return JsonResponse({
        "sucesso": True,
        "inspiracoes": inspiracoes,
        "dataset_consolidado": dataset,
        "prompt_final": prompt_final,
        "calculado": True,
        "processado_em": timezone.now().isoformat(),
    })

@login_required
@gestor_required
@require_POST
def conceito_etapa3_geracao(request: HttpRequest, projeto_id: int) -> JsonResponse:
    """
    Etapa 3: Geração final (DALL·E/SDXL)
    - Usa projeto.prompt_final ou o 'prompt' enviado no body.
    - Aqui deixamos um fallback local com PIL para validar o fluxo.
    """
    projeto = get_object_or_404(Projeto, pk=projeto_id)

    try:
        body = json.loads(request.body or "{}")
    except Exception:
        body = {}

    prompt = body.get("prompt") or getattr(projeto, "prompt_final", None)
    if not prompt:
        return JsonResponse({"sucesso": False, "erro": "Prompt final não disponível."}, status=400)

    # TODO: integrar com DalleService ou provedor real
    # from gestor.services.dalle_service import DalleService
    # url_imagem = DalleService().gerar_imagem(prompt)
    # download_url = url_imagem

    # Fallback local:
    url_imagem, download_url = _gerar_imagem_stub(prompt, projeto_id)

    # Persistir flag/tempo
    projeto.analise_visual_processada = True
    projeto.data_analise_visual = timezone.now()
    projeto.save(update_fields=["analise_visual_processada", "data_analise_visual"])

    return JsonResponse({
        "sucesso": True,
        "image_url": url_imagem,
        "download_url": download_url,
        "prompt_usado": (prompt[:600] + "...") if len(prompt) > 600 else prompt,
        "processado_em": timezone.now().isoformat(),
    })