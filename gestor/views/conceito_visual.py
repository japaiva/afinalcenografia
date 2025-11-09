# gestor/views/conceito_visual.py

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

# ========================== Import da Função de Service ==========================

# gerar_prompt_completo movida para gestor/services/conceito_visual_service.py
from gestor.services.conceito_visual_service import gerar_prompt_completo

# Mantida aqui por compatibilidade (apenas import):
# def gerar_prompt_completo(projeto: Projeto, prompt_customizado: Optional[str] = None) -> str:
# ========================== Views HTTP ==========================

@login_required
@gestor_required
@require_GET
def conceito_visual(request: HttpRequest, projeto_id: int) -> HttpResponse:
    """
    Tela principal do Conceito Visual
    Renderiza o template HTML com os dados do projeto
    """
    projeto = get_object_or_404(
        Projeto.objects.select_related('empresa', 'feira'),
        pk=projeto_id
    )

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
    projeto = get_object_or_404(
        Projeto.objects.select_related('empresa', 'feira'),
        pk=projeto_id
    )
    brief = _briefing(projeto)
    
    if not brief:
        return JsonResponse({"sucesso": False, "erro": "Briefing não encontrado."}, status=400)
    
    # Verificar arquivos de planta
    esbocos = brief.arquivos.filter(tipo="planta")
    if not esbocos.exists():
        return JsonResponse({"sucesso": False, "erro": "Nenhum esboço de planta encontrado."}, status=400)
    
    esboco = esbocos.first()
    
    # Preparar payload para o agente
    # Usar lateral (priorizar esquerda, depois direita)
    lateral = brief.medida_lateral_esquerda or brief.medida_lateral_direita

    payload = {
        "projeto_id": projeto.id,
        "briefing_id": brief.id,
        "briefing": {
            "tipo_stand": brief.tipo_stand,
            "medida_frente_m": float(brief.medida_frente) if brief.medida_frente else None,
            "medida_lateral_m": float(lateral) if lateral else None,
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
    projeto = get_object_or_404(Projeto.objects.select_related("empresa", "feira"), pk=projeto_id)
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
    projeto = get_object_or_404(Projeto.objects.select_related("empresa", "feira"), pk=projeto_id)
    
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