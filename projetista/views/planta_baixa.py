# projetista/views/planta_baixa.py - VERSÃO LIMPA COM CREWAI V2

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
import logging

from projetos.models import Projeto, Briefing
from projetista.models import PlantaBaixa
from core.services.crewai import PlantaBaixaServiceV2
from core.models import CrewExecucao

logger = logging.getLogger(__name__)

# =============================================================================
# GERAÇÃO DE PLANTA BAIXA - VERSÃO SIMPLIFICADA
# =============================================================================

@login_required
@require_POST
def gerar_planta_baixa(request, projeto_id):
    """
    Gera planta baixa usando CrewAI V2 - Pipeline completo de 4 agentes
    """
    projeto = get_object_or_404(Projeto, pk=projeto_id, projetista=request.user)
    
    try:
        # Obter briefing
        try:
            briefing = projeto.briefings.latest('versao')
        except Briefing.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Briefing não encontrado',
                'message': 'Este projeto não possui um briefing válido.'
            })
        
        # Determinar nova versão
        planta_anterior = PlantaBaixa.objects.filter(projeto=projeto).order_by('-versao').first()
        nova_versao = planta_anterior.versao + 1 if planta_anterior else 1
        
        # Usar CrewAI V2
        service = PlantaBaixaServiceV2()
        
        # Validar crew
        validacao = service.validar_crew()
        if not validacao['valido']:
            return JsonResponse({
                'success': False,
                'error': f"Crew inválida: {validacao.get('erro', 'Erro desconhecido')}"
            })
        
        # Executar pipeline de 4 agentes
        logger.info(f"🚀 Iniciando pipeline CrewAI V2 para projeto {projeto.nome}")
        resultado = service.gerar_planta(briefing, nova_versao)
        
        # Processar resultado
        if resultado['success']:
            return JsonResponse({
                'success': True,
                'message': f'Pipeline completo! Planta v{nova_versao} gerada em {resultado.get("tempo_execucao", 0):.1f}s',
                'planta_id': resultado['planta'].id,
                'versao': nova_versao,
                'execucao_id': resultado.get('execucao_id'),
                'tempo_execucao': resultado.get('tempo_execucao', 0),
                'agentes_executados': 4,
                'metodo': 'crewai_v2_pipeline',
                'redirect_url': f'/projetista/projetos/{projeto_id}/planta-baixa/'
            })
        else:
            return JsonResponse({
                'success': False,
                'error': resultado.get('error', 'Erro desconhecido na geração')
            })
            
    except Exception as e:
        logger.error(f"Erro técnico ao gerar planta baixa: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': f'Erro técnico: {str(e)}'
        }, status=500)

# =============================================================================
# VIEWS DE VISUALIZAÇÃO (mantidas)
# =============================================================================

@login_required
def visualizar_planta_baixa(request, projeto_id):
    """Visualização da planta baixa"""
    projeto = get_object_or_404(Projeto, pk=projeto_id, projetista=request.user)
    planta_baixa = PlantaBaixa.objects.filter(projeto=projeto).order_by('-versao').first()
    
    if not planta_baixa:
        messages.info(request, 'Nenhuma planta baixa encontrada para este projeto.')
        return redirect('projetista:projeto_detail', pk=projeto_id)
    
    # Permitir visualizar versão específica
    versao_solicitada = request.GET.get('versao')
    if versao_solicitada:
        try:
            versao_num = int(versao_solicitada)
            planta_especifica = PlantaBaixa.objects.filter(
                projeto=projeto, 
                versao=versao_num
            ).first()
            if planta_especifica:
                planta_baixa = planta_especifica
        except (ValueError, TypeError):
            pass
    
    # Listar todas as versões
    versoes = PlantaBaixa.objects.filter(projeto=projeto).order_by('-versao')
    
    context = {
        'projeto': projeto,
        'planta_baixa': planta_baixa,
        'versoes': versoes,
        'dados_json': planta_baixa.dados_json
    }
    
    return render(request, 'projetista/planta_baixa.html', context)

@login_required
def download_planta_svg(request, planta_id):
    """Download do arquivo SVG"""
    planta = get_object_or_404(PlantaBaixa, pk=planta_id, projeto__projetista=request.user)
    
    if planta.arquivo_svg:
        response = HttpResponse(planta.arquivo_svg.read(), content_type='image/svg+xml')
        filename = f"planta_v{planta.versao}_{planta.projeto.numero}.svg"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    else:
        messages.error(request, 'Arquivo SVG não encontrado.')
        return redirect('projetista:projeto_detail', projeto_id=planta.projeto.id)

# =============================================================================
# VIEWS DE VERBOSE E LOGS (simplificadas)
# =============================================================================

@login_required
def obter_logs_execucao(request, execucao_id):
    """
    Retorna logs da execução em tempo real via AJAX
    """
    try:
        execucao = get_object_or_404(CrewExecucao, id=execucao_id)
        
        # Buscar logs no cache (VerboseManager cuida disso)
        from django.core.cache import cache
        cache_key = f"crewai_logs_{execucao_id}"
        logs = cache.get(cache_key, [])
        
        # Pegar logs novos se solicitado
        desde = int(request.GET.get('desde', 0))
        logs_novos = logs[desde:] if desde < len(logs) else []
        
        return JsonResponse({
            'success': True,
            'logs': logs_novos,
            'total_logs': len(logs),
            'execucao_id': execucao_id
        })
        
    except Exception as e:
        logger.error(f"Erro ao buscar logs: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)})

@login_required 
def status_execucao(request, execucao_id):
    """
    Retorna status atual da execução
    """
    try:
        execucao = get_object_or_404(CrewExecucao, id=execucao_id)
        
        return JsonResponse({
            'success': True,
            'execucao_id': execucao_id,
            'status': execucao.status,
            'iniciado_em': execucao.iniciado_em.isoformat(),
            'finalizado_em': execucao.finalizado_em.isoformat() if execucao.finalizado_em else None,
            'tempo_execucao': execucao.tempo_execucao,
            'crew_nome': execucao.crew.nome if execucao.crew else 'Desconhecido'
        })
        
    except Exception as e:
        logger.error(f"Erro ao buscar status: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)})

# =============================================================================
# VIEWS DE REFINAMENTO (opcional - futura implementação)
# =============================================================================

@login_required
@require_POST
def refinar_planta_baixa(request, projeto_id):
    """
    Refina planta baixa com feedback do usuário (futura implementação)
    """
    projeto = get_object_or_404(Projeto, pk=projeto_id, projetista=request.user)
    
    try:
        planta_atual = PlantaBaixa.objects.filter(projeto=projeto).order_by('-versao').first()
        if not planta_atual:
            return JsonResponse({
                'success': False,
                'error': 'Nenhuma planta baixa encontrada para refinar'
            })
        
        feedback_usuario = request.POST.get('feedback', '').strip()
        if not feedback_usuario:
            return JsonResponse({
                'success': False,
                'error': 'Por favor, forneça feedback para o refinamento'
            })
        
        # TODO: Implementar refinamento com CrewAI V2
        # service = PlantaBaixaServiceV2()
        # resultado = service.refinar_planta(planta_atual, feedback_usuario)
        
        return JsonResponse({
            'success': False,
            'error': 'Refinamento ainda não implementado no CrewAI V2'
        })
            
    except Exception as e:
        logger.error(f"Erro ao refinar planta baixa: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'Erro técnico: {str(e)}'
        })

# =============================================================================
# VIEWS DE DEBUG (opcionais)
# =============================================================================

@login_required
def validar_crew_status(request):
    """
    Valida o status do CrewAI V2
    """
    try:
        service = PlantaBaixaServiceV2()
        validacao = service.validar_crew()
        
        return JsonResponse({
            'success': True,
            'crew_valido': validacao['valido'],
            'detalhes': validacao
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'crew_valido': False,
            'error': str(e)
        })