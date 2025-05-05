# gestor/views/feira_extracao.py

import json
import logging
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from core.models import Feira, FeiraManualQA
from core.services.extracao_service import ExtracaoService

logger = logging.getLogger(__name__)

@login_required
@require_POST
def feira_extrair_dados(request, pk):
    """
    Extrai dados do Q&A da feira para preencher campos do cadastro.
    """
    feira = get_object_or_404(Feira, pk=pk)
    logger.info(f"Debug: Usuário {request.user.username}, nivel: {request.user.nivel}")
    logger.info(f"Debug: Feira {pk}, qa_processado: {Feira.objects.get(pk=pk).qa_processado}")

    # Verificar quantos QAs têm campo_relacionado
    qa_count = FeiraManualQA.objects.filter(
        feira_id=pk,
        campo_relacionado__isnull=False
    ).exclude(campo_relacionado='').count()
    logger.info(f"Debug: QAs com campo_relacionado: {qa_count}")
    
    # Verificar permissões
    if False:
    #request.user.nivel not in ['admin', 'gestor']:
        return JsonResponse({
            'status': 'error',
            'message': 'Você não tem permissão para esta operação.'
        }, status=403)
    
    # Verificar se existem Q&As
    if not feira.qa_processado:
        return JsonResponse({
            'status': 'error',
            'message': 'O Q&A desta feira ainda não foi processado. Por favor, processe-o primeiro.'
        })
        
    try:
        # Inicializar o serviço de extração
        servico = ExtracaoService()
        
        # Realizar a extração
        resultado = servico.extrair_dados_feira(feira.id)
        
        return JsonResponse(resultado)
        
    except Exception as e:
        logger.error(f"Erro ao extrair dados: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': f'Erro ao processar extração: {str(e)}'
        }, status=500)

@login_required
@require_POST
def feira_aplicar_dados(request, pk):
    """
    Aplica os dados extraídos ao cadastro da feira.
    """
    feira = get_object_or_404(Feira, pk=pk)
    
    # Verificar permissões
    if False:
        #request.user.nivel not in ['admin', 'gestor']:
        return JsonResponse({
            'status': 'error',
            'message': 'Você não tem permissão para esta operação.'
        }, status=403)
        
    try:
        # Obter dados do corpo da requisição
        data = json.loads(request.body)
        dados_selecionados = data.get('campos', {})
        
        if not dados_selecionados:
            return JsonResponse({
                'status': 'error',
                'message': 'Nenhum dado foi fornecido para aplicação.'
            })
        
        # Inicializar o serviço de extração
        servico = ExtracaoService()
        
        # Aplicar os dados selecionados
        resultado = servico.aplicar_dados(feira.id, dados_selecionados)
        
        return JsonResponse(resultado)
        
    except json.JSONDecodeError:
        return JsonResponse({
            'status': 'error',
            'message': 'Dados inválidos fornecidos.'
        }, status=400)
    except Exception as e:
        logger.error(f"Erro ao aplicar dados: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': f'Erro ao aplicar dados: {str(e)}'
        }, status=500)