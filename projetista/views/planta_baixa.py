# projetista/views/planta_baixa.py 

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.core.files.base import ContentFile
from django.core.cache import cache
from django.conf import settings
import logging
import math
import time
import json

from projetos.models import Projeto, Briefing
from projetista.models import PlantaBaixa
from core.services.crewai_planta_service import CrewAIPlantaService
from core.models import CrewExecucao

logger = logging.getLogger(__name__)

from decimal import Decimal

def decimal_to_float(obj):
    """Converte objetos Decimal para float para serialização JSON"""
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, dict):
        return {k: decimal_to_float(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [decimal_to_float(v) for v in obj]
    return obj

# =============================================================================
# COMPARAÇÃO E ANÁLISE
# =============================================================================

@login_required
def comparar_plantas(request, projeto_id):
    """
    Compara diferentes versões de plantas baixas (adaptado para CrewAI)
    """
    projeto = get_object_or_404(Projeto, pk=projeto_id, projetista=request.user)
    
    # Obter versões para comparação
    versao1 = request.GET.get('v1')
    versao2 = request.GET.get('v2')
    
    if not (versao1 and versao2):
        # Mostrar interface para seleção de versões
        plantas = PlantaBaixa.objects.filter(projeto=projeto).order_by('-versao')
        return render(request, 'projetista/comparar_plantas.html', {
            'projeto': projeto,
            'plantas': plantas
        })
    
    try:
        planta1 = PlantaBaixa.objects.get(projeto=projeto, versao=int(versao1))
        planta2 = PlantaBaixa.objects.get(projeto=projeto, versao=int(versao2))
        
        # Fazer comparação usando CrewAI (FASE 1: simulação)
        comparacao = {
            'simulacao': True,
            'resumo': f'Comparação FASE 1: v{versao1} vs v{versao2}',
            'diferencas': [
                'Layout reorganizado',
                'Áreas redistribuídas',
                'Melhor aproveitamento do espaço'
            ],
            'metricas': {
                'area_v1': planta1.dados_json.get('area_total_usada', 0),
                'area_v2': planta2.dados_json.get('area_total_usada', 0),
                'ambientes_v1': len(planta1.dados_json.get('ambientes_criados', [])),
                'ambientes_v2': len(planta2.dados_json.get('ambientes_criados', []))
            }
        }
        
        context = {
            'projeto': projeto,
            'planta1': planta1,
            'planta2': planta2,
            'comparacao': comparacao,
            'dados_planta1': _processar_dados_planta_crewai(planta1, None),
            'dados_planta2': _processar_dados_planta_crewai(planta2, None)
        }
        
        return render(request, 'projetista/comparacao_resultado.html', context)
        
    except (PlantaBaixa.DoesNotExist, ValueError):
        messages.error(request, 'Versões de planta inválidas')
        return redirect('projetista:projeto_detail', pk=projeto_id)

# =============================================================================
# UTILITÁRIOS
# =============================================================================

def _processar_dados_planta_crewai(planta_baixa, crew_service=None):
    """
    Processa dados da planta baixa especificamente para CrewAI (FASE 1)
    """
    dados_json = planta_baixa.dados_json or {}
    
    # Extrair dados específicos do CrewAI (compatível com FASE 1)
    areas_criadas = dados_json.get('ambientes_criados', [])
    tipo_estande = dados_json.get('tipo_estande', 'não especificado')
    area_total = dados_json.get('area_total_usada', 0)
    resumo_execucao = dados_json.get('resumo_decisoes', '')
    crew_usado = dados_json.get('crew_info', {}).get('nome', 'Desconhecido')
    lados_abertos = dados_json.get('lados_abertos', [])
    
    # Processar ambientes (adaptar para FASE 1)
    ambientes = []
    for i, area_desc in enumerate(areas_criadas):
        ambientes.append({
            'nome': f'Ambiente {i+1}',
            'tipo': 'exposicao' if 'exposição' in area_desc.lower() else 'circulacao',
            'descricao': area_desc,
            'area': 0  # FASE 1: não calcula área específica ainda
        })
    
    # Informações específicas da FASE 1
    eh_simulacao = dados_json.get('simulacao', False)
    fase = dados_json.get('fase', 0)
    
    return {
        'dados_json': dados_json,
        'metodo_geracao': 'crewai_fase1' if eh_simulacao else 'crewai',
        'resumo_execucao': resumo_execucao,
        'areas_criadas': areas_criadas,
        'tipo_estande': tipo_estande,
        'area_total': area_total,
        'lados_abertos': lados_abertos,
        'ambientes': ambientes,
        'crew_usado': crew_usado,
        'eh_planta_crewai': True,
        'eh_simulacao_fase1': eh_simulacao,
        'fase_atual': fase,
        # Informações para interface
        'pode_refinar': True,
        'proximas_evolucoes': [
            'Implementar execução real do CrewAI',
            'Adicionar geração de SVG detalhada',
            'Integrar refinamento avançado'
        ] if eh_simulacao else []
    }

@login_required
def validar_crew_status(request):
    """
    Valida o status do CrewAI (substitui validar_agente_status)
    """
    try:
        crew_service = CrewAIPlantaService()
        validacao = crew_service.validar_crew()
        
        return JsonResponse({
            'success': True,
            'crew_valido': validacao['valido'],
            'detalhes': validacao,
            'crews_disponiveis': crew_service.listar_crews_disponiveis(),
            'debug_info': crew_service.debug_crew_info()
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'crew_valido': False,
            'error': str(e)
        })

@login_required
def exportar_dados_planta(request, planta_id):
    """
    Exporta dados da planta (adaptado para CrewAI)
    """
    planta = get_object_or_404(PlantaBaixa, pk=planta_id, projeto__projetista=request.user)
    
    try:
        # Dados para exportação (incluindo informações do CrewAI)
        dados_exportacao = {
            'planta_info': {
                'id': planta.id,
                'versao': planta.versao,
                'status': planta.status,
                'algoritmo_usado': planta.algoritmo_usado,
                'criado_em': planta.criado_em.isoformat(),
                'atualizado_em': planta.atualizado_em.isoformat()
            },
            'projeto_info': {
                'numero': planta.projeto.numero,
                'nome': planta.projeto.nome,
                'empresa': planta.projeto.empresa.nome
            },
            'dados_crew': planta.dados_json or {},
            'metodo_geracao': 'crewai',
            'eh_simulacao_fase1': planta.dados_json.get('simulacao', False),
            'exportado_em': timezone.now().isoformat()
        }
        
        response = JsonResponse(dados_exportacao, json_dumps_params={'indent': 2})
        filename = f"planta_crewai_v{planta.versao}_{planta.projeto.numero}_dados.json"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
        
    except Exception as e:
        logger.error(f"Erro ao exportar dados da planta: {str(e)}")
        messages.error(request, f"Erro ao exportar dados: {str(e)}")
        return redirect('projetista:visualizar_planta_baixa', projeto_id=planta.projeto.id)

# =============================================================================
# VIEWS DE TESTE E DEBUG PARA CREWAI (OPCIONAIS)
# =============================================================================

@login_required
def testar_crewai_config(request):
    """
    View para testar configuração do CrewAI (OPCIONAL - para debug)
    """
    try:
        crew_service = CrewAIPlantaService()
        
        # Informações básicas
        config_info = {
            'crew_carregado': crew_service.crew is not None,
            'crew_disponivel': crew_service.crew_disponivel(),
            'validacao': crew_service.validar_crew(),
            'debug': crew_service.debug_crew_info(),
            'crews_disponiveis': crew_service.listar_crews_disponiveis()
        }
        
        return JsonResponse({
            'success': True,
            'crewai_status': 'Configurado' if config_info['crew_disponivel'] else 'Pendente configuração',
            'config': config_info
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Erro ao testar CrewAI: {str(e)}',
            'crewai_status': 'Erro'
        })

@login_required
def debug_crew_info(request):
    """
    View para debug detalhado do crew (OPCIONAL - para debug)
    """
    try:
        crew_service = CrewAIPlantaService()
        debug_info = crew_service.debug_crew_info()
        
        context = {
            'debug_info': debug_info,
            'crews_disponiveis': crew_service.listar_crews_disponiveis(),
            'crew_atual': crew_service.crew.nome if crew_service.crew else None
        }
        
        return render(request, 'projetista/debug_crewai.html', context)
        
    except Exception as e:
        messages.error(request, f'Erro no debug: {str(e)}')
        return redirect('projetista:dashboard')




# ============================================================================
# VIEWS DE LOGS VERBOSE CORRIGIDAS
# ============================================================================

@login_required
def obter_logs_execucao(request, execucao_id):
    """
    Retorna logs da execução em tempo real via AJAX - CORRIGIDO
    """
    try:
        # Verificar se a execução existe
        try:
            execucao = CrewExecucao.objects.get(id=execucao_id)
        except CrewExecucao.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Execução não encontrada'
            })
        
        # Buscar logs no cache
        cache_key = f"crewai_logs_{execucao_id}"
        logs = cache.get(cache_key, [])
        
        # Pegar apenas logs novos se solicitado
        desde = request.GET.get('desde', 0)
        try:
            desde = int(desde)
            if desde < len(logs):
                logs_novos = logs[desde:]
            else:
                logs_novos = []
        except (ValueError, TypeError):
            logs_novos = logs
        
        # Debug logs
        logger.info(f"📋 Buscando logs para execução {execucao_id}: {len(logs)} total, {len(logs_novos)} novos desde {desde}")
        
        return JsonResponse({
            'success': True,
            'logs': logs_novos,
            'total_logs': len(logs),
            'timestamp': time.time(),
            'execucao_id': execucao_id,
            'cache_key': cache_key  # Para debug
        })
        
    except Exception as e:
        logger.error(f"Erro ao buscar logs da execução {execucao_id}: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

@login_required 
def status_execucao(request, execucao_id):
    """
    Retorna status atual da execução - CORRIGIDO
    """
    try:
        execucao = CrewExecucao.objects.get(id=execucao_id)
        
        return JsonResponse({
            'success': True,
            'execucao_id': execucao_id,
            'status': execucao.status,
            'iniciado_em': execucao.iniciado_em.isoformat(),
            'finalizado_em': execucao.finalizado_em.isoformat() if execucao.finalizado_em else None,
            'tempo_execucao': execucao.tempo_execucao,
            'crew_nome': execucao.crew.nome if execucao.crew else 'Desconhecido'
        })
        
    except CrewExecucao.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Execução não encontrada'
        })
    except Exception as e:
        logger.error(f"Erro ao buscar status da execução {execucao_id}: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

# ============================================================================
# GERAÇÃO CORRIGIDA COM VERBOSE
# ============================================================================


# projetista/views/planta_baixa.py - SUBSTITUIR A FUNÇÃO gerar_planta_baixa

@login_required
@require_POST
def gerar_planta_baixa(request, projeto_id):
    """
    Gera planta baixa usando CrewAI - CORRIGIDA PARA PIPELINE COMPLETO
    """
    projeto = get_object_or_404(Projeto, pk=projeto_id, projetista=request.user)
    
    try:
        logger.info(f"🚀 Iniciando geração CrewAI para projeto {projeto.nome}")
        
        # Obter briefing
        try:
            briefing = projeto.briefings.latest('versao')
        except Briefing.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Briefing não encontrado',
                'message': 'Este projeto não possui um briefing válido.',
                'action_required': 'complete_briefing'
            })
        
        # Determinar versão
        planta_anterior = PlantaBaixa.objects.filter(projeto=projeto).order_by('-versao').first()
        nova_versao = planta_anterior.versao + 1 if planta_anterior else 1
        
        # Inicializar serviço CrewAI
        try:
            crew_service = CrewAIPlantaService()
        except Exception as config_error:
            logger.error(f"Erro na configuração do CrewAI: {str(config_error)}")
            return JsonResponse({
                'success': False,
                'error': 'CrewAI não configurado',
                'message': 'O sistema CrewAI não está disponível. Contate o administrador.',
                'error_type': 'crew_config_error',
                'can_proceed': False,
                'details': str(config_error)
            })
        
        # Validar configuração do crew
        validacao_crew = crew_service.validar_crew()
        if not validacao_crew['valido']:
            return JsonResponse({
                'success': False,
                'error': 'Configuração do crew inválida',
                'message': f'Problema na configuração: {validacao_crew["erro"]}',
                'error_type': 'crew_config_error',
                'can_proceed': False,
                'details': validacao_crew
            })
        
        # ✅ EXECUÇÃO CORRIGIDA - USAR O MÉTODO CORRETO
        # Verificar se deve usar pipeline completo ou método anterior
        usar_pipeline = getattr(settings, 'CREWAI_USAR_PIPELINE_COMPLETO', False)
        
        if usar_pipeline:
            # MÉTODO CORRETO para pipeline completo
            resultado = crew_service.usar_fase3_pipeline_completo(briefing, nova_versao, planta_anterior)
        else:
            # Fallback para método anterior (1 agente)
            resultado = crew_service.usar_fase2_se_configurado(briefing, nova_versao, planta_anterior)
        
        # Verificar resultado
        if not resultado.get('success', False):
            logger.warning(f"Falha na geração com CrewAI: {resultado.get('error', 'Erro desconhecido')}")
            
            return JsonResponse({
                'success': False,
                'error': resultado.get('error', 'Erro na geração da planta baixa'),
                'message': resultado.get('error', 'Não foi possível gerar a planta baixa com CrewAI'),
                'detailed_error': resultado.get('detalhes_crew', ''),
                'error_type': 'crew_execution_error',
                'can_proceed': False,
                'crew_info': validacao_crew.get('crew', {}),
                'debug_info': crew_service.debug_crew_info()
            })
        
        # ✅ RESPOSTA CORRIGIDA PARA DIFERENTES FASES
        planta_gerada = resultado.get('planta')
        execucao_id = resultado.get('execucao_id')
        fase = resultado.get('fase', 1)
        
        if not execucao_id:
            logger.warning("⚠️ execucao_id não retornado pelo serviço")
        
        # PROCESSAR RESPOSTA BASEADA NA FASE
        if fase == 1:
            # FASE 1: Simulação
            dados_crew = resultado.get('resultado_simulado', {})
            areas_criadas = dados_crew.get('ambientes_criados', [])
            tipo_estande = dados_crew.get('tipo_estande', 'não especificado')
            area_total_usada = dados_crew.get('area_total_usada', 0)
            crew_usado = resultado.get('crew_usado', {}).get('nome', 'Simulação')
            
            logger.info(f"✅ FASE 1: Planta v{nova_versao} simulada")
            
            return JsonResponse({
                'success': True,
                'message': f'FASE 1: Planta baixa v{nova_versao} simulada com sucesso!',
                'planta_id': planta_gerada.id if planta_gerada else None,
                'versao': nova_versao,
                'tipo_estande': tipo_estande,
                'areas_criadas': len(areas_criadas),
                'areas_lista': areas_criadas,
                'metodo_geracao': 'crewai_fase1',
                'crew_usado': crew_usado,
                'simulacao': True,
                'execucao_id': execucao_id,
                'area_total_usada': area_total_usada,
                'redirect_url': request.build_absolute_uri(f'/projetista/projetos/{projeto_id}/planta-baixa/')
            })
            
        elif fase == 2:
            # FASE 2: Um agente
            tempo_execucao = resultado.get('tempo_execucao', 0)
            
            logger.info(f"✅ FASE 2: Planta v{nova_versao} gerada pelo primeiro agente em {tempo_execucao:.1f}s")
            
            return JsonResponse({
                'success': True,
                'message': resultado.get('message', f'Primeiro agente executado! Planta v{nova_versao} gerada'),
                'planta_id': planta_gerada.id if planta_gerada else None,
                'versao': nova_versao,
                'metodo_geracao': 'crewai_primeiro_agente',
                'crew_usado': 'Primeiro Agente - Analista de Briefing',
                'simulacao': False,
                'execucao_id': execucao_id,
                'tempo_execucao': tempo_execucao,
                'fase': 2,
                'agente_executado': 'primeiro',
                'redirect_url': request.build_absolute_uri(f'/projetista/projetos/{projeto_id}/planta-baixa/')
            })
            
        elif fase == 3:
            # FASE 3: Pipeline completo
            tempo_execucao = resultado.get('tempo_execucao', 0)
            agentes_executados = resultado.get('agentes_executados', 4)
            
            logger.info(f"✅ FASE 3: Pipeline completo! Planta v{nova_versao} gerada em {tempo_execucao:.1f}s")
            
            return JsonResponse({
                'success': True,
                'message': resultado.get('message', f'Pipeline completo! {agentes_executados} agentes executados em {tempo_execucao:.1f}s'),
                'planta_id': planta_gerada.id if planta_gerada else None,
                'versao': nova_versao,
                'metodo_geracao': 'crewai_pipeline_completo',
                'crew_usado': f'Pipeline Completo - {agentes_executados} Agentes',
                'simulacao': False,
                'execucao_id': execucao_id,
                'tempo_execucao': tempo_execucao,
                'fase': 3,
                'agentes_executados': agentes_executados,
                'pipeline_completo': True,
                'redirect_url': request.build_absolute_uri(f'/projetista/projetos/{projeto_id}/planta-baixa/')
            })
            
        else:
            # Fallback genérico
            return JsonResponse({
                'success': True,
                'message': f'Planta baixa v{nova_versao} gerada com sucesso!',
                'planta_id': planta_gerada.id if planta_gerada else None,
                'versao': nova_versao,
                'execucao_id': execucao_id,
                'fase': fase,
                'redirect_url': request.build_absolute_uri(f'/projetista/projetos/{projeto_id}/planta-baixa/')
            })
            
    except Exception as e:
        logger.error(f"Erro técnico ao gerar planta baixa: {str(e)}", exc_info=True)
        
        return JsonResponse({
            'success': False,
            'error': 'Erro técnico do sistema',
            'message': f'Ocorreu um erro técnico: {str(e)}',
            'error_type': 'system_error',
            'can_proceed': False
        }, status=500)

# ============================================================================
# TESTE DE LOGS (para debug)
# ============================================================================

@login_required
def testar_logs_verbose(request):
    """
    View para testar o sistema de logs verbose
    """
    try:
        # Criar execução de teste
        execucao = CrewExecucao.objects.create(
            crew_id=1,  # Assumindo que existe
            projeto_id=1,  # Assumindo que existe
            input_data={'teste': True},
            status='running'
        )
        
        # Simular logs
        cache_key = f"crewai_logs_{execucao.id}"
        logs_teste = [
            {
                'timestamp': time.strftime("%H:%M:%S"),
                'message': '🚀 Teste de logs iniciado',
                'tipo': 'inicio',
                'execucao_id': execucao.id,
                'crew_nome': 'Teste'
            },
            {
                'timestamp': time.strftime("%H:%M:%S"),
                'message': '🤖 Agente de teste carregado',
                'tipo': 'agente',
                'execucao_id': execucao.id,
                'crew_nome': 'Teste'
            },
            {
                'timestamp': time.strftime("%H:%M:%S"),
                'message': '✅ Teste concluído',
                'tipo': 'sucesso',
                'execucao_id': execucao.id,
                'crew_nome': 'Teste'
            }
        ]
        
        cache.set(cache_key, logs_teste, timeout=3600)
        
        return JsonResponse({
            'success': True,
            'message': 'Logs de teste criados',
            'execucao_id': execucao.id,
            'cache_key': cache_key,
            'logs_count': len(logs_teste)
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

# ============================================================================
# RESTO DAS VIEWS (mantidas como estavam)
# ============================================================================

@login_required
@require_POST
def refinar_planta_baixa(request, projeto_id):
    """
    Refina planta baixa usando CrewAI
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
        
        crew_service = CrewAIPlantaService()
        
        nova_versao = planta_atual.versao + 1
        
        try:
            briefing = projeto.briefings.latest('versao')
            resultado_simulado = {
                'success': True,
                'simulacao_refinamento': True,
                'feedback_aplicado': feedback_usuario,
                'versao_anterior': planta_atual.versao,
                'nova_versao': nova_versao,
                'mudancas_simuladas': [
                    f"Feedback aplicado: {feedback_usuario[:50]}...",
                    "Layout ajustado conforme solicitação",
                    "Áreas redistribuídas"
                ],
                'resultado_simulado': {
                    'tipo_estande': planta_atual.dados_json.get('tipo_estande', 'ilha'),
                    'area_total_usada': planta_atual.dados_json.get('area_total_usada', 0),
                    'ambientes_criados': planta_atual.dados_json.get('ambientes_criados', []),
                    'resumo_decisoes': f"REFINAMENTO: {feedback_usuario}"
                }
            }
            
            planta_refinada = _criar_planta_mock_refinamento(projeto, briefing, nova_versao, resultado_simulado)
            
            return JsonResponse({
                'success': True,
                'message': f'Planta baixa refinada (v{nova_versao})!',
                'planta_id': planta_refinada.id,
                'versao': nova_versao,
                'mudancas': '; '.join(resultado_simulado['mudancas_simuladas']),
                'feedback_aplicado': feedback_usuario,
                'simulacao': True,
                'crew_usado': crew_service.crew_nome_exato if crew_service else 'Simulado',
                'redirect_url': request.build_absolute_uri(f'/projetista/projetos/{projeto_id}/planta-baixa/')
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'Erro no refinamento: {str(e)}'
            })
            
    except Exception as e:
        logger.error(f"Erro ao refinar planta baixa: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': f'Erro técnico no refinamento: {str(e)}'
        }, status=500)

def _criar_planta_mock_refinamento(projeto, briefing, versao, resultado_simulado):
    """Cria planta mock para refinamento"""
    try:
        dados_json_raw = {
            'refinamento': True,
            'versao_anterior': resultado_simulado['versao_anterior'],
            'feedback_aplicado': resultado_simulado['feedback_aplicado'],
            'mudancas': resultado_simulado['mudancas_simuladas'],
            **resultado_simulado['resultado_simulado']
        }
        
        dados_json = decimal_to_float(dados_json_raw)
        
        planta = PlantaBaixa.objects.create(
            projeto=projeto,
            briefing=briefing,
            projetista=projeto.projetista,
            dados_json=dados_json,
            versao=versao,
            algoritmo_usado='crewai_refinamento_simulado',
            status='pronta'
        )
        
        svg_content = _gerar_svg_refinamento(resultado_simulado)
        svg_filename = f"planta_refinada_v{versao}_{projeto.numero}.svg"
        planta.arquivo_svg.save(
            svg_filename,
            ContentFile(svg_content.encode('utf-8')),
            save=False
        )
        
        planta.save()
        return planta
        
    except Exception as e:
        logger.error(f"Erro ao criar planta de refinamento: {str(e)}")
        raise

def _gerar_svg_refinamento(resultado_simulado):
    """Gera SVG para refinamento"""
    feedback = resultado_simulado.get('feedback_aplicado', 'Sem feedback')
    
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<svg width="700" height="500" viewBox="0 0 700 500" xmlns="http://www.w3.org/2000/svg">
  <rect x="0" y="0" width="700" height="500" fill="#f8f9fa"/>
  
  <text x="350" y="30" text-anchor="middle" font-family="Arial" font-size="18" font-weight="bold" fill="#333">
    PLANTA REFINADA
  </text>
  
  <text x="350" y="50" text-anchor="middle" font-family="Arial" font-size="12" fill="#666">
    Feedback aplicado: {feedback[:50]}...
  </text>
  
  <rect x="50" y="80" width="600" height="350" 
        fill="#fff3cd" stroke="#ffc107" stroke-width="3"/>
  
  <text x="350" y="260" text-anchor="middle" font-family="Arial" font-size="16" fill="#856404">
    🔄 Layout Refinado com Sucesso!
  </text>
  
</svg>"""

# Manter as outras views existentes...
@login_required
def visualizar_planta_baixa(request, projeto_id):
    """Visualização da planta baixa"""
    projeto = get_object_or_404(Projeto, pk=projeto_id, projetista=request.user)
    planta_baixa = PlantaBaixa.objects.filter(projeto=projeto).order_by('-versao').first()
    
    if not planta_baixa:
        messages.info(request, 'Nenhuma planta baixa encontrada para este projeto.')
        return redirect('projetista:projeto_detail', pk=projeto_id)
    
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
 