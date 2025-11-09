# gestor/views/planta_baixa.py
"""
Views para o wizard de geração de Planta Baixa.

Fluxo em 4 etapas:
1. Visualizar esboço e iniciar análise
2. Revisar estruturação da planta
3. Validar conformidade
4. Visualizar planta final (SVG)
"""

import json
import logging
from typing import Dict, Any

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from core.decorators import gestor_required
from projetos.models import Projeto
from gestor.services.planta_baixa_service import PlantaBaixaService

logger = logging.getLogger(__name__)


@login_required
@gestor_required
@require_GET
def planta_baixa_wizard(request: HttpRequest, projeto_id: int) -> HttpResponse:
    """
    Tela principal do wizard de Planta Baixa.
    Renderiza o template HTML com os dados do projeto.
    """
    projeto = get_object_or_404(
        Projeto.objects.select_related('empresa', 'feira'),
        pk=projeto_id
    )

    # Verificar se tem briefing
    if not hasattr(projeto, 'briefings') or not projeto.briefings.exists():
        messages.error(request, "Este projeto não possui briefing.")
        return redirect("gestor:projeto_detail", pk=projeto_id)

    briefing = projeto.briefings.first()

    # Verificar se tem esboço
    esbocos = briefing.arquivos.filter(tipo="planta")
    if not esbocos.exists():
        messages.error(request, "Este projeto não possui esboço de planta no briefing.")
        return redirect("gestor:projeto_detail", pk=projeto_id)

    # Determinar estado atual
    estado_atual = _determinar_estado(projeto)

    context = {
        "projeto": projeto,
        "briefing": briefing,
        "esbocos": list(esbocos),
        "estado_atual": estado_atual,
        "tem_layout": bool(projeto.layout_identificado),
        "tem_planta_json": bool(projeto.planta_baixa_json),
        "tem_svg": bool(projeto.planta_baixa_svg),
        "planta_processada": projeto.planta_baixa_processada,
    }

    return render(request, "gestor/planta_baixa_wizard.html", context)


def _determinar_estado(projeto: Projeto) -> str:
    """
    Determina em qual etapa do wizard o projeto está.

    Returns:
        'inicial' | 'etapa1' | 'etapa2' | 'etapa3' | 'completo'
    """
    if projeto.planta_baixa_processada and projeto.planta_baixa_svg:
        return 'completo'
    elif projeto.planta_baixa_json:
        return 'etapa2'
    elif projeto.layout_identificado:
        return 'etapa1'
    else:
        return 'inicial'


@login_required
@gestor_required
@require_POST
def planta_etapa1_analisar(request: HttpRequest, projeto_id: int) -> JsonResponse:
    """
    Etapa 1: Análise do esboço de planta.
    Extrai layout, áreas e dimensões.
    """
    projeto = get_object_or_404(
        Projeto.objects.select_related('empresa', 'feira'),
        pk=projeto_id
    )

    try:
        service = PlantaBaixaService(projeto)
        resultado = service.etapa1_analisar_esboco()

        if resultado["sucesso"]:
            return JsonResponse({
                "sucesso": True,
                "layout": resultado["layout"],
                "arquivo": resultado["arquivo"],
                "processado_em": resultado["processado_em"],
            })
        else:
            return JsonResponse({
                "sucesso": False,
                "erro": resultado["erro"]
            }, status=400)

    except Exception as e:
        logger.error(f"Erro na etapa 1 - Projeto {projeto_id}: {str(e)}")
        return JsonResponse({
            "sucesso": False,
            "erro": f"Erro ao processar: {str(e)}"
        }, status=500)


@login_required
@gestor_required
@require_POST
def planta_etapa2_estruturar(request: HttpRequest, projeto_id: int) -> JsonResponse:
    """
    Etapa 2: Estruturação da planta com coordenadas precisas.
    """
    projeto = get_object_or_404(
        Projeto.objects.select_related('empresa', 'feira'),
        pk=projeto_id
    )

    try:
        service = PlantaBaixaService(projeto)
        resultado = service.etapa2_estruturar_planta()

        if resultado["sucesso"]:
            return JsonResponse({
                "sucesso": True,
                "planta_estruturada": resultado["planta_estruturada"],
                "processado_em": resultado["processado_em"],
            })
        else:
            return JsonResponse({
                "sucesso": False,
                "erro": resultado["erro"]
            }, status=400)

    except Exception as e:
        logger.error(f"Erro na etapa 2 - Projeto {projeto_id}: {str(e)}")
        return JsonResponse({
            "sucesso": False,
            "erro": f"Erro ao processar: {str(e)}"
        }, status=500)


@login_required
@gestor_required
@require_POST
def planta_etapa3_validar(request: HttpRequest, projeto_id: int) -> JsonResponse:
    """
    Etapa 3: Validação da planta contra regras e normas.
    """
    projeto = get_object_or_404(
        Projeto.objects.select_related('empresa', 'feira'),
        pk=projeto_id
    )

    try:
        service = PlantaBaixaService(projeto)
        resultado = service.etapa3_validar_conformidade()

        if resultado["sucesso"]:
            return JsonResponse({
                "sucesso": True,
                "validacao": resultado["validacao"],
                "processado_em": resultado["processado_em"],
            })
        else:
            return JsonResponse({
                "sucesso": False,
                "erro": resultado["erro"]
            }, status=400)

    except Exception as e:
        logger.error(f"Erro na etapa 3 - Projeto {projeto_id}: {str(e)}")
        return JsonResponse({
            "sucesso": False,
            "erro": f"Erro ao processar: {str(e)}"
        }, status=500)


@login_required
@gestor_required
@require_POST
def planta_etapa4_gerar_svg(request: HttpRequest, projeto_id: int) -> JsonResponse:
    """
    Etapa 4: Geração da representação SVG da planta.
    """
    projeto = get_object_or_404(
        Projeto.objects.select_related('empresa', 'feira'),
        pk=projeto_id
    )

    try:
        # Verificar se tem validação anterior
        body = json.loads(request.body or "{}")
        validacao = body.get("validacao")

        service = PlantaBaixaService(projeto)
        resultado = service.etapa4_gerar_svg(validacao=validacao)

        if resultado["sucesso"]:
            return JsonResponse({
                "sucesso": True,
                "svg": resultado["svg"],
                "processado_em": resultado["processado_em"],
            })
        else:
            return JsonResponse({
                "sucesso": False,
                "erro": resultado["erro"]
            }, status=400)

    except Exception as e:
        logger.error(f"Erro na etapa 4 - Projeto {projeto_id}: {str(e)}")
        return JsonResponse({
            "sucesso": False,
            "erro": f"Erro ao processar: {str(e)}"
        }, status=500)


@login_required
@gestor_required
@require_POST
def planta_executar_todas(request: HttpRequest, projeto_id: int) -> JsonResponse:
    """
    Executa todas as 4 etapas sequencialmente.
    Útil para processamento rápido sem interação.
    """
    projeto = get_object_or_404(
        Projeto.objects.select_related('empresa', 'feira'),
        pk=projeto_id
    )

    try:
        service = PlantaBaixaService(projeto)
        resultado = service.executar_todas_etapas()

        if resultado["sucesso"]:
            return JsonResponse({
                "sucesso": True,
                "resultados": resultado,
                "svg_final": projeto.planta_baixa_svg,
            })
        else:
            return JsonResponse({
                "sucesso": False,
                "erro": f"Erro na etapa {resultado.get('erro_etapa')}",
                "detalhes": resultado
            }, status=400)

    except Exception as e:
        logger.error(f"Erro ao executar todas etapas - Projeto {projeto_id}: {str(e)}")
        return JsonResponse({
            "sucesso": False,
            "erro": f"Erro ao processar: {str(e)}"
        }, status=500)
