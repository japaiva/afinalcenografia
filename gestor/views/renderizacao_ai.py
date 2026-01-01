"""
Views para Renderização AI (Módulo 2)

Interface wizard para:
1. Enriquecer JSON (planta + briefing + inspirações)
2. Gerar prompt e imagem DALL-E
3. Visualizar resultado
4. [Futuro] Ajuste conversacional
"""

import json
import logging
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods, require_POST
from django.utils import timezone

from projetos.models import Projeto
from gestor.services.renderizacao_ai_service import RenderizacaoAIService

logger = logging.getLogger(__name__)


@login_required
@require_http_methods(["GET"])
def renderizacao_ai_wizard(request, projeto_id):
    """
    Tela principal do wizard de Renderização AI
    """
    projeto = get_object_or_404(Projeto, id=projeto_id)

    # Verificar se planta baixa foi processada
    if not projeto.planta_baixa_processada:
        return render(request, 'gestor/erro.html', {
            'titulo': 'Planta Baixa Pendente',
            'mensagem': 'Complete o módulo de Planta Baixa antes de gerar o conceito visual.',
            'link_voltar': f'/gestor/projetos/{projeto.id}/',
            'texto_voltar': 'Voltar ao Projeto'
        })

    # Verificar se briefing existe
    if not projeto.has_briefing:
        return render(request, 'gestor/erro.html', {
            'titulo': 'Briefing Pendente',
            'mensagem': 'Complete o briefing antes de gerar o conceito visual.',
            'link_voltar': f'/gestor/projetos/{projeto.id}/',
            'texto_voltar': 'Voltar ao Projeto'
        })

    context = {
        'projeto': projeto,
        'etapa1_concluida': bool(projeto.renderizacao_ai_json),
        'etapa2_concluida': projeto.renderizacao_ai_processada,
        'imagem_url': projeto.imagem_conceito_url,
        'prompt_atual': projeto.prompt_dalle_atual,
    }

    return render(request, 'gestor/renderizacao_ai_wizard.html', context)


@login_required
@require_POST
def renderizacao_etapa1_enriquecer(request, projeto_id):
    """
    Etapa 1: Enriquecer JSON com dados do briefing e inspirações

    Returns:
        JsonResponse com resultado do processamento
    """
    projeto = get_object_or_404(Projeto, id=projeto_id)

    logger.info(f"[Renderização AI] Iniciando Etapa 1 - Projeto {projeto.id}")

    try:
        service = RenderizacaoAIService(projeto)
        resultado = service.etapa1_enriquecer_json()

        if resultado['sucesso']:
            logger.info(f"[Renderização AI] Etapa 1 concluída - Projeto {projeto.id}")
        else:
            logger.warning(f"[Renderização AI] Etapa 1 falhou - Projeto {projeto.id}: {resultado.get('erro')}")

        return JsonResponse(resultado)

    except Exception as e:
        logger.error(f"[Renderização AI] Erro na Etapa 1 - Projeto {projeto.id}: {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'sucesso': False,
            'erro': f'Erro ao enriquecer JSON: {str(e)}'
        })


@login_required
@require_POST
def renderizacao_etapa2_gerar(request, projeto_id):
    """
    Etapa 2: Gerar prompt e imagem DALL-E usando o Agente de Imagem Principal

    Returns:
        JsonResponse com prompt e URL da imagem
    """
    projeto = get_object_or_404(Projeto, id=projeto_id)

    logger.info(f"[Renderização AI] Iniciando Etapa 2 - Projeto {projeto.id}")

    try:
        service = RenderizacaoAIService(projeto)
        resultado = service.etapa2_gerar_prompt_e_imagem()

        if resultado['sucesso']:
            logger.info(f"[Renderização AI] Etapa 2 concluída - Projeto {projeto.id}")
            logger.info(f"[Renderização AI] Imagem URL: {resultado.get('imagem_url', '')[:100]}...")
        else:
            logger.warning(f"[Renderização AI] Etapa 2 falhou - Projeto {projeto.id}: {resultado.get('erro')}")

        return JsonResponse(resultado)

    except Exception as e:
        logger.error(f"[Renderização AI] Erro na Etapa 2 - Projeto {projeto.id}: {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'sucesso': False,
            'erro': f'Erro ao gerar imagem: {str(e)}'
        })


@login_required
@require_POST
def renderizacao_executar_tudo(request, projeto_id):
    """
    Executa todas as etapas em sequência:
    1. Enriquecimento
    2. Geração de prompt e imagem

    Returns:
        JsonResponse com resultado final
    """
    projeto = get_object_or_404(Projeto, id=projeto_id)

    logger.info(f"[Renderização AI] Executando tudo - Projeto {projeto.id}")

    try:
        service = RenderizacaoAIService(projeto)

        # Etapa 1: Enriquecimento
        resultado_etapa1 = service.etapa1_enriquecer_json()
        if not resultado_etapa1['sucesso']:
            return JsonResponse(resultado_etapa1)

        # Etapa 2: Geração de prompt e imagem
        resultado_etapa2 = service.etapa2_gerar_prompt_e_imagem()
        if not resultado_etapa2['sucesso']:
            return JsonResponse(resultado_etapa2)

        logger.info(f"[Renderização AI] Todas as etapas concluídas - Projeto {projeto.id}")

        return JsonResponse({
            'sucesso': True,
            'etapa1': resultado_etapa1,
            'etapa2': resultado_etapa2,
            'mensagem': 'Conceito visual gerado com sucesso!'
        })

    except Exception as e:
        logger.error(f"[Renderização AI] Erro ao executar tudo - Projeto {projeto.id}: {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'sucesso': False,
            'erro': f'Erro ao processar: {str(e)}'
        })
