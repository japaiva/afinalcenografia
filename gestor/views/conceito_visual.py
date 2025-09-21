# gestor/views/conceito_visual.py - VERSÃO COMPLETA ATUALIZADA

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
from projetos.models import Projeto

# ========================== Tenta importar executor central ===================

_RUN_AGENT_EXECUTOR = None
try:
    from .agents_crews import run_agent as _RUN_AGENT_EXECUTOR
except Exception:
    _RUN_AGENT_EXECUTOR = None

# ============================== Helpers de dados ==============================

def _briefing(projeto: Projeto):
    """Retorna o primeiro briefing relacionado ao projeto."""
    return getattr(projeto, "briefings", None).first()

def _arquivos(briefing_obj, tipo: str) -> List[Any]:
    """Retorna uma lista de arquivos do briefing por tipo."""
    if not briefing_obj:
        return []
    return list(briefing_obj.arquivos.filter(tipo=tipo))

def _float_or(value, default):
    try:
        return float(value) if value is not None else default
    except Exception:
        return default

# ======================= Função para normalizar resposta do agente ======================

def _normalize_agent_response(resp: Dict[str, Any], expected_structure: str) -> Dict[str, Any]:
    """
    Normaliza a resposta do agente para o formato esperado
    """
    if expected_structure == "areas":
        # Se veio como 'layout', mapear para 'areas'
        if "layout" in resp and "areas" not in resp:
            layout_data = resp["layout"]
            
            # Se layout é um dict com áreas
            if isinstance(layout_data, dict):
                # Várias possibilidades de estrutura
                if "areas" in layout_data:
                    resp["areas"] = layout_data["areas"]
                elif "zones" in layout_data:
                    resp["areas"] = layout_data["zones"]
                elif "espacos" in layout_data:
                    resp["areas"] = layout_data["espacos"]
                else:
                    # Se layout tem estrutura direta de áreas
                    areas_encontradas = {}
                    for key, value in layout_data.items():
                        if isinstance(value, dict) and ("bbox" in value or "posicao" in value or "area" in str(key).lower()):
                            areas_encontradas[key] = value
                    
                    if areas_encontradas:
                        resp["areas"] = areas_encontradas
                    else:
                        # Fallback: criar uma área genérica
                        resp["areas"] = {
                            "area_principal": {
                                "nome": "Área Principal",
                                "tipo": resp.get("type", "stand"),
                                "bbox_norm": {"x": 0, "y": 0, "w": 1, "h": 1}
                            }
                        }
            
            # Se ainda não tem areas, criar estrutura mínima
            if "areas" not in resp:
                resp["areas"] = {
                    "area_central": {
                        "nome": "Área Central",
                        "tipo": resp.get("type", "desconhecido"),
                        "dimensoes": resp.get("dimensions", {}),
                        "bbox_norm": {"x": 0, "y": 0, "w": 1, "h": 1}
                    }
                }
        
        # Adicionar campos complementares se não existirem
        if "dimensoes_detectadas" not in resp and "dimensions" in resp:
            resp["dimensoes_detectadas"] = resp["dimensions"]
        
        if "tipo_estande" not in resp and "type" in resp:
            resp["tipo_estande"] = resp["type"]
    
    return resp

# ======================= Execução de agentes COM NORMALIZACAO ===================

def _run_agent(nome_agente: str, payload: Dict[str, Any], imagens: Optional[List[str]] = None) -> Dict[str, Any]:
    """Executa agente com normalização de resposta"""
    if not _RUN_AGENT_EXECUTOR:
        return {"erro": "Sistema de agentes não disponível", "sucesso": False}
    
    try:
        # Construir prompt limpo baseado no tipo de agente
        if "Esboço" in nome_agente or "Esboco" in nome_agente:
            briefing_data = payload.get("briefing", {})
            
            prompt = f"""Analise este esboço de planta baixa e extraia o layout estruturado:

DADOS DO PROJETO:
- ID: {payload.get('projeto_id')}
- Tipo de stand: {briefing_data.get('tipo_stand', 'não informado')}
- Dimensões: {briefing_data.get('medida_frente_m', 'não informado')}m x {briefing_data.get('medida_fundo_m', 'não informado')}m
- Altura máxima: {briefing_data.get('altura_m', 3.0)}m

IMPORTANTE: Retorne um JSON com a estrutura 'areas' contendo as diferentes zonas/espaços identificados no layout.
Exemplo esperado:
{{
  "areas": {{
    "recepcao": {{"nome": "Recepção", "bbox_norm": {{"x": 0, "y": 0, "w": 0.3, "h": 0.4}}}},
    "reuniao": {{"nome": "Sala de Reunião", "bbox_norm": {{"x": 0.3, "y": 0, "w": 0.4, "h": 0.6}}}}
  }},
  "dimensoes_detectadas": {{"largura": {briefing_data.get('medida_frente_m', 6)}, "profundidade": {briefing_data.get('medida_fundo_m', 8)}}},
  "tipo_estande": "{briefing_data.get('tipo_stand', 'corporativo')}"
}}

Por favor, analise a imagem fornecida e retorne o layout estruturado."""

        elif "Referência" in nome_agente or "Referencia" in nome_agente:
            prompt = f"""Analise as imagens de referência para o projeto ID {payload.get('projeto_id')}.
Marca/Cliente: {payload.get('marca', 'não informado')}

Extraia e retorne JSON com:
- estilo_identificado, cores_hex, materiais_sugeridos, elementos_destaque, iluminacao, riscos_e_mitigacoes"""
        else:
            prompt = json.dumps(payload, indent=2)
        
        print(f"DEBUG - Prompt enviado: {prompt[:300]}...")
        
        # Executar com prompt específico
        executor_payload = {"prompt": prompt, **payload}
        resultado = _RUN_AGENT_EXECUTOR(nome_agente, executor_payload, imagens)
        
        # Verificar se retornou erro
        if not resultado or "erro" in resultado:
            return {"erro": resultado.get("erro", "Agente não retornou resultado válido"), "sucesso": False}
        
        # Extrair dados se veio do executor genérico
        if "_metadata" in resultado:
            resultado = {k: v for k, v in resultado.items() if k != "_metadata"}
        
        # NORMALIZAR RESPOSTA baseado no tipo de agente
        if "Esboço" in nome_agente or "Esboco" in nome_agente:
            resultado = _normalize_agent_response(resultado, "areas")
        
        return resultado
        
    except Exception as e:
        print(f"ERRO no executor: {str(e)}")
        return {"erro": f"Erro na execução do agente: {str(e)}", "sucesso": False}

# ======================= Consolidação + Prompt (Etapa 2) ======================

def _consolidar(brief, layout: Dict[str, Any], inspiracoes: Dict[str, Any]) -> Dict[str, Any]:
    # Tentar extrair dimensões do layout primeiro, depois do briefing
    dimensoes_layout = layout.get("dimensoes_detectadas", {}) if isinstance(layout.get("dimensoes_detectadas"), dict) else {}
    
    largura = dimensoes_layout.get("largura") or _float_or(getattr(brief, "medida_frente", None), 6.0)
    profundidade = dimensoes_layout.get("profundidade") or _float_or(getattr(brief, "medida_fundo", None), 8.0)
    altura = dimensoes_layout.get("altura") or 3.0  # Altura padrão
    
    paleta = []
    if isinstance(inspiracoes.get("cores_predominantes"), list):
        # Mudança aqui: cores_predominantes ao invés de cores_hex
        paleta = [c.get("hex") for c in inspiracoes["cores_predominantes"] if isinstance(c, dict) and c.get("hex")]
    elif isinstance(inspiracoes.get("cores_hex"), list):
        # Fallback para cores_hex se existir
        paleta = [c.get("hex") for c in inspiracoes["cores_hex"] if isinstance(c, dict) and c.get("hex")]
    
    if not paleta:
        paleta = ["#FFFFFF", "#1A1A1A"]  # Padrão

    dataset = {
        "dimensoes": {
            "largura_m": float(largura),
            "profundidade_m": float(profundidade),
            "altura_m": float(altura),
        },
        "tipo_estande": layout.get("tipo_estande") or getattr(brief, "tipo_stand", None) or "desconhecido",
        "zonas": [],
        "circulacao": {"min_m": 1.2, "rotas": layout.get("circulacao", [])},
        "paleta_final_hex": paleta,
        "riscos": inspiracoes.get("riscos_e_mitigacoes", []),
        "pronto_para_geracao": True,
    }

    # Processar áreas
    areas = layout.get("areas", {})
    if isinstance(areas, dict):
        for nome, a in areas.items():
            if isinstance(a, dict):
                dataset["zonas"].append({
                    "nome": nome,
                    "bbox_norm": a.get("bbox_norm", {"x": 0, "y": 0, "w": 1, "h": 1}),
                    "materiais": [],  # Será preenchido se necessário
                    "elementos": inspiracoes.get("elementos_destaque", []) if isinstance(inspiracoes.get("elementos_destaque"), list) else [],
                    "cores_hex": paleta[:2],
                })

    return dataset

def _montar_prompt(brief, dataset: Dict[str, Any], inspiracoes: Dict[str, Any]) -> str:
    W = dataset["dimensoes"]["largura_m"]
    D = dataset["dimensoes"]["profundidade_m"]
    H = dataset["dimensoes"]["altura_m"]
    tipo = dataset.get("tipo_estande", "desconhecido")

    areas_txt = "\n".join(f"- {z.get('nome')}" for z in dataset.get("zonas", [])) or "- Área central"
    cores = ", ".join(dataset.get("paleta_final_hex", []))
    
    estilo_extra = "moderno"
    if isinstance(inspiracoes.get("estilo_identificado"), dict):
        estilo_extra = inspiracoes["estilo_identificado"].get("principal", "moderno").replace("_", " ")

    prompt = f"""Crie uma imagem realística 3/4 em alta resolução de um estande de feira de negócios:

Dimensões: {W}m x {D}m x {H}m, tipo {tipo}
Áreas internas:
{areas_txt}

Elementos visuais: paleta de cores {cores}
Estilo: Moderno, profissional, {estilo_extra}

Renderize em perspectiva 3/4 mostrando a fachada principal e uma lateral, com pessoas interagindo naturalmente no espaço, iluminação de feira comercial realística, acabamento fotorrealístico.""".strip()
    
    return prompt

def _gerar_imagem_stub(prompt: str, projeto_id: int) -> Tuple[str, str]:
    """Fallback local com PIL para validar o fluxo."""
    from PIL import Image, ImageDraw

    media_root = getattr(settings, "MEDIA_ROOT", os.path.join(getattr(settings, "BASE_DIR", ""), "media"))
    if not media_root:
        media_root = os.path.join(os.getcwd(), "media")
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
    """Tela principal do Conceito Visual - COM CONTEXTO DOS DADOS SALVOS"""
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
        # NÃO PRECISA ADICIONAR NADA AQUI
        # O template acessará projeto.layout_identificado e projeto.inspiracoes_visuais diretamente
    }
    
    return render(request, "gestor/conceito_visual.html", context)

@login_required
@gestor_required
@require_POST
def conceito_etapa1_esboco(request: HttpRequest, projeto_id: int) -> JsonResponse:
    """Etapa 1: Análise do esboço (A1) - VERSÃO CORRIGIDA"""
    projeto = get_object_or_404(Projeto, pk=projeto_id)
    brief = _briefing(projeto)
    if not brief:
        return JsonResponse({"sucesso": False, "erro": "Briefing não encontrado."}, status=400)

    # Verificar agente
    agente_nome = "Analisador de Esboços de Planta"
    agente_id = None
    try:
        agente_obj = Agente.objects.get(nome=agente_nome, tipo="individual", ativo=True)
        agente_id = agente_obj.id
    except Agente.DoesNotExist:
        agente_obj = None

    # Body para arquivo específico
    try:
        body = json.loads(request.body or "{}")
    except Exception:
        body = {}
    arquivo_id = body.get("arquivo_id")

    # Coletar esboços
    esbocos_qs = brief.arquivos.filter(tipo="planta")
    
    if not esbocos_qs.exists():
        return JsonResponse({"sucesso": False, "erro": "Nenhum esboço de planta encontrado."}, status=400)

    if arquivo_id:
        esboco = esbocos_qs.filter(id=arquivo_id).first()
        if not esboco:
            return JsonResponse({"sucesso": False, "erro": f"Esboço id={arquivo_id} não encontrado."}, status=404)
    else:
        esboco = esbocos_qs.first()

    # Path/URL do arquivo
    if not esboco.arquivo:
        return JsonResponse({"sucesso": False, "erro": "Esboço não possui arquivo anexado."}, status=400)
    
    arquivo_nome = esboco.nome or esboco.arquivo.name
    esboco_url = esboco.arquivo.url
    esboco_path = esboco.arquivo.url  # Para MinIO

    # Payload consistente
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

    executor_nome = "agents_crews.run_agent" if _RUN_AGENT_EXECUTOR else "sem_executor"
    imagens_usadas = [esboco_path] if esboco_path else []

    # Chamada do agente
    resp = _run_agent(agente_nome, payload, imagens=imagens_usadas)
    
    # Verificar erros
    if not resp.get("sucesso", True) or "erro" in resp:
        return JsonResponse({
            "sucesso": False, 
            "erro": resp.get("erro", "Agente não conseguiu processar o esboço")
        }, status=400)

    # Verificar estrutura válida (agora deve ter 'areas' após normalização)
    if "areas" not in resp:
        return JsonResponse({
            "sucesso": False, 
            "erro": f"Agente não retornou estrutura 'areas'. Estrutura retornada: {list(resp.keys())}"
        }, status=400)

    # Persistir resultado
    projeto.layout_identificado = resp
    projeto.save(update_fields=["layout_identificado"])

    return JsonResponse({
        "sucesso": True,
        "agente": {
            "nome": agente_nome,
            "id": agente_id,
            "ativo_no_banco": agente_obj is not None,
        },
        "executor": executor_nome,
        "modo_demo": False,
        "layout": resp,
        "arquivo": {
            "id": getattr(esboco, "id", None),
            "nome": arquivo_nome,
            "url": esboco_url,
            "tem_path": bool(esboco_path),
        },
        "imagens_usadas": imagens_usadas,
        "calculado": True,
        "processado_em": timezone.now().isoformat(),
    })

@login_required
@gestor_required
@require_POST
def conceito_etapa2_referencias(request: HttpRequest, projeto_id: int) -> JsonResponse:
    """Etapa 2: Referências (A2) + Consolidação (A3) + Prompt Final - CORRIGIDA"""
    projeto = get_object_or_404(Projeto, pk=projeto_id)
    brief = _briefing(projeto)
    if not brief:
        return JsonResponse({"sucesso": False, "erro": "Briefing não encontrado."}, status=400)

    # Coletar referências
    refs = _arquivos(brief, "referencia")
    imagens_ref = []
    for ref in refs:
        if ref.arquivo:
            imagens_ref.append(ref.arquivo.url)

    # Executar agente de referências
    payload = {"projeto_id": projeto.id, "marca": getattr(projeto.empresa, "nome", None)}
    inspiracoes = _run_agent("Analisador de Referências Visuais", payload, imagens=imagens_ref)
    
    if "erro" in inspiracoes:
        return JsonResponse({
            "sucesso": False,
            "erro": f"Erro na análise de referências: {inspiracoes.get('erro')}"
        }, status=400)

    # Layout do request ou do projeto
    try:
        body = json.loads(request.body or "{}")
    except Exception:
        body = {}
    
    layout = body.get("layout") or getattr(projeto, "layout_identificado", None)
    
    if not layout:
        return JsonResponse({
            "sucesso": False,
            "erro": "Layout não disponível. Execute a Etapa 1 primeiro."
        }, status=400)

    # Consolidar e gerar prompt
    dataset = _consolidar(brief, layout, inspiracoes)
    dataset["projeto_id"] = projeto.id  # Adicionar ID do projeto ao dataset
    prompt_final = _montar_prompt(brief, dataset, inspiracoes)

    # SALVAR APENAS O NECESSÁRIO - CORRIGIDO
    projeto.inspiracoes_visuais = inspiracoes
    projeto.save(update_fields=["inspiracoes_visuais"])  # Apenas inspiracoes_visuais existe no modelo

    # RETORNAR tudo para o frontend usar
    return JsonResponse({
        "sucesso": True,
        "inspiracoes": inspiracoes,
        "dataset_consolidado": dataset,  # Não salva, só retorna
        "prompt_final": prompt_final,     # Não salva, só retorna
        "calculado": True,
        "processado_em": timezone.now().isoformat(),
    })

@login_required
@gestor_required
@require_POST
def conceito_etapa3_geracao(request: HttpRequest, projeto_id: int) -> JsonResponse:
    """Etapa 3: Geração final (DALL·E/SDXL)"""
    projeto = get_object_or_404(Projeto, pk=projeto_id)

    try:
        body = json.loads(request.body or "{}")
    except Exception:
        body = {}

    prompt = body.get("prompt")
    
    if not prompt:
        # Se não veio prompt no body, tentar regenerar a partir dos dados salvos
        brief = _briefing(projeto)
        layout = getattr(projeto, "layout_identificado", None)
        inspiracoes = getattr(projeto, "inspiracoes_visuais", None)
        
        if brief and layout and inspiracoes:
            dataset = _consolidar(brief, layout, inspiracoes)
            prompt = _montar_prompt(brief, dataset, inspiracoes)
    
    if not prompt:
        return JsonResponse({
            "sucesso": False, 
            "erro": "Prompt não fornecido. Execute a Etapa 2 ou forneça um prompt customizado."
        }, status=400)

    # TODO: integrar com serviço real de geração de imagem
    # Por enquanto, usar fallback local
    url_imagem, download_url = _gerar_imagem_stub(prompt, projeto_id)

    # Marcar projeto como processado
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