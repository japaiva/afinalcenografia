# projetista/views/planta_baixa.py - VIEWS ESPECÍFICAS PARA PLANTA BAIXA

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
from django.utils import timezone
import logging

from projetos.models import Projeto, Briefing
from projetista.models import PlantaBaixa
from core.services.planta_baixa_service import PlantaBaixaService

logger = logging.getLogger(__name__)

# =============================================================================
# GERAÇÃO E REGENERAÇÃO
# =============================================================================

@login_required
@require_POST
def gerar_planta_baixa(request, projeto_id):
    """
    Gera ou regenera a planta baixa usando AGENTE ARQUITETO
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
                'message': 'Este projeto não possui um briefing válido.',
                'action_required': 'complete_briefing'
            })
        
        # Verificar se já existe planta baixa
        planta_anterior = PlantaBaixa.objects.filter(projeto=projeto).order_by('-versao').first()
        nova_versao = planta_anterior.versao + 1 if planta_anterior else 1
        
        # Inicializar serviço com agente
        try:
            planta_service = PlantaBaixaService()
        except Exception as config_error:
            logger.error(f"Erro na configuração do agente: {str(config_error)}")
            return JsonResponse({
                'success': False,
                'error': 'Agente Arquiteto não configurado',
                'message': 'O agente Arquiteto de Estandes não está disponível. Contate o administrador.',
                'error_type': 'agent_config_error',
                'can_proceed': False,
                'details': str(config_error)
            })
        
        # Validar configuração do agente
        validacao_agente = planta_service.validar_configuracao_agente()
        if not validacao_agente['valido']:
            return JsonResponse({
                'success': False,
                'error': 'Configuração do agente inválida',
                'message': f'Problema na configuração: {validacao_agente["erro"]}',
                'error_type': 'agent_config_error',
                'can_proceed': False,
                'details': validacao_agente
            })
        
        # Gerar planta baixa com agente
        resultado = planta_service.gerar_planta_baixa(
            briefing=briefing,
            versao=nova_versao,
            planta_anterior=planta_anterior
        )
        
        # Verificar resultado
        if not resultado.get('success', False):
            logger.warning(f"Falha na geração com agente: {resultado.get('error', 'Erro desconhecido')}")
            
            # Determinar tipo de erro
            error_type = 'validation_error'
            critica = resultado.get('critica', '')
            
            if 'DADOS INSUFICIENTES' in critica:
                error_type = 'incomplete_data'
            elif 'AGENTE' in critica:
                error_type = 'agent_error'
            elif 'TÉCNICO' in critica:
                error_type = 'technical_error'
            elif 'SVG' in critica:
                error_type = 'svg_generation_error'
            elif 'API' in critica or 'Timeout' in resultado.get('error', ''):
                error_type = 'api_error'
            
            return JsonResponse({
                'success': False,
                'error': resultado.get('error', 'Erro na geração da planta baixa'),
                'message': resultado.get('error', 'Não foi possível gerar a planta baixa'),
                'detailed_error': critica,
                'suggestions': resultado.get('sugestoes', []),
                'error_type': error_type,
                'can_proceed': resultado.get('pode_prosseguir', False),
                'validation_details': resultado.get('detalhes_validacao', {}),
                'agent_info': validacao_agente.get('agente', {})
            })
        
        # Sucesso: Planta gerada pelo agente
        planta_gerada = resultado['planta']
        layout_data = resultado.get('layout', {})
        
        # Extrair informações detalhadas
        dados_basicos = layout_data.get('dados_basicos', {})
        areas_atendidas = dados_basicos.get('areas_atendidas', [])
        tipo_estande = dados_basicos.get('tipo_estande', 'não especificado')
        area_total_usada = dados_basicos.get('area_total_usada', 0)
        lados_abertos = dados_basicos.get('lados_abertos', [])
        
        logger.info(f"✅ Planta v{nova_versao} gerada pelo agente: {len(areas_atendidas)} áreas, tipo {tipo_estande}, {area_total_usada:.1f}m²")
        
        return JsonResponse({
            'success': True,
            'message': f'Planta baixa v{nova_versao} gerada com sucesso pelo agente Arquiteto!',
            'planta_id': planta_gerada.id,
            'versao': nova_versao,
            'tipo_estande': tipo_estande,
            'areas_atendidas': len(areas_atendidas),
            'areas_lista': areas_atendidas,
            'lados_abertos': lados_abertos,
            'metodo_geracao': 'agente_arquiteto',
            'resumo_decisoes': resultado.get('critica', ''),
            'area_total_usada': area_total_usada,
            'validation_success': True,
            'agente_usado': validacao_agente.get('agente', {}).get('nome', 'Arquiteto de Estandes'),
            'redirect_url': request.build_absolute_uri(f'/projetista/projetos/{projeto_id}/planta-baixa/')
        })
            
    except Exception as e:
        logger.error(f"Erro técnico ao gerar planta baixa com agente: {str(e)}", exc_info=True)
        
        return JsonResponse({
            'success': False,
            'error': 'Erro técnico do sistema',
            'message': f'Ocorreu um erro técnico: {str(e)}',
            'error_type': 'system_error',
            'can_proceed': False
        }, status=500)

@login_required
@require_POST
def refinar_planta_baixa(request, projeto_id):
    """
    Refina uma planta baixa existente com feedback do usuário
    """
    projeto = get_object_or_404(Projeto, pk=projeto_id, projetista=request.user)
    
    try:
        # Obter planta atual
        planta_atual = PlantaBaixa.objects.filter(projeto=projeto).order_by('-versao').first()
        
        if not planta_atual:
            return JsonResponse({
                'success': False,
                'error': 'Nenhuma planta baixa encontrada para refinar'
            })
        
        # Obter feedback do usuário
        feedback_usuario = request.POST.get('feedback', '').strip()
        
        if not feedback_usuario:
            return JsonResponse({
                'success': False,
                'error': 'Por favor, forneça feedback para o refinamento'
            })
        
        # Inicializar serviço
        planta_service = PlantaBaixaService()
        
        # Refinar planta
        resultado = planta_service.refinar_planta_com_feedback(planta_atual, feedback_usuario)
        
        if resultado['success']:
            planta_refinada = resultado['planta']
            
            return JsonResponse({
                'success': True,
                'message': f'Planta baixa refinada com sucesso (v{planta_refinada.versao})!',
                'planta_id': planta_refinada.id,
                'versao': planta_refinada.versao,
                'mudancas': resultado.get('mudancas', ''),
                'feedback_aplicado': feedback_usuario,
                'redirect_url': request.build_absolute_uri(f'/projetista/projetos/{projeto_id}/planta-baixa/')
            })
        else:
            return JsonResponse({
                'success': False,
                'error': resultado.get('error', 'Erro no refinamento'),
                'details': resultado.get('critica', '')
            })
            
    except Exception as e:
        logger.error(f"Erro ao refinar planta baixa: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': f'Erro técnico no refinamento: {str(e)}'
        }, status=500)

# =============================================================================
# VISUALIZAÇÃO E DOWNLOADS
# =============================================================================

@login_required
def visualizar_planta_baixa(request, projeto_id):
    """
    Visualiza a planta baixa atual (compatível com versão do agente)
    """
    projeto = get_object_or_404(Projeto, pk=projeto_id, projetista=request.user)
    
    # Buscar a versão mais recente
    planta_baixa = PlantaBaixa.objects.filter(projeto=projeto).order_by('-versao').first()
    
    if not planta_baixa:
        messages.info(request, 'Nenhuma planta baixa encontrada para este projeto.')
        return redirect('projetista:projeto_detail', pk=projeto_id)
    
    # Permitir seleção de versão específica via GET parameter
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
    
    # Listar todas as versões disponíveis
    versoes = PlantaBaixa.objects.filter(projeto=projeto).order_by('-versao')
    
    # Inicializar serviço para análise (com fallback)
    planta_service = None
    try:
        planta_service = PlantaBaixaService()
    except Exception as e:
        logger.warning(f"Serviço de planta não disponível: {str(e)}")
    
    # Processar dados de forma robusta (compatível com agente e algoritmo)
    context_data = _processar_dados_planta(planta_baixa, planta_service)
    
    # Análise da planta
    analise_planta = None
    if planta_service:
        try:
            resultado_analise = planta_service.analisar_planta_baixa(planta_baixa)
            if resultado_analise['success']:
                analise_planta = resultado_analise['analise']
        except Exception as e:
            logger.warning(f"Erro na análise da planta: {str(e)}")
    
    context = {
        'projeto': projeto,
        'planta_baixa': planta_baixa,
        'versoes': versoes,
        'analise_planta': analise_planta,
        'pode_refinar': context_data['metodo_geracao'] == 'agente' and planta_service is not None,
        **context_data  # Adicionar todos os dados processados
    }
    
    return render(request, 'projetista/planta_baixa.html', context)

@login_required
def download_planta_svg(request, planta_id):
    """
    Download do arquivo SVG da planta baixa
    """
    planta = get_object_or_404(PlantaBaixa, pk=planta_id, projeto__projetista=request.user)
    
    if planta.arquivo_svg:
        response = HttpResponse(planta.arquivo_svg.read(), content_type='image/svg+xml')
        
        # Nome do arquivo baseado no método de geração
        try:
            planta_service = PlantaBaixaService()
            metodo = planta_service.get_metodo_geracao(planta)
        except:
            metodo = 'planta'
        
        filename = f"planta_{metodo}_v{planta.versao}_{planta.projeto.numero}.svg"
        
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    else:
        messages.error(request, 'Arquivo SVG não encontrado.')
        return redirect('projetista:projeto_detail', projeto_id=planta.projeto.id)

# =============================================================================
# COMPARAÇÃO E ANÁLISE
# =============================================================================

@login_required
def comparar_plantas(request, projeto_id):
    """
    Compara diferentes versões de plantas baixas
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
        
        # Fazer comparação usando serviço
        comparacao = None
        try:
            planta_service = PlantaBaixaService()
            resultado = planta_service.comparar_plantas(planta1, planta2)
            
            if resultado['success']:
                comparacao = resultado['comparacao']
            else:
                messages.warning(request, f"Erro na comparação: {resultado['error']}")
        except Exception as e:
            logger.error(f"Erro no serviço de comparação: {str(e)}")
            messages.warning(request, "Serviço de comparação não disponível")
        
        context = {
            'projeto': projeto,
            'planta1': planta1,
            'planta2': planta2,
            'comparacao': comparacao,
            'dados_planta1': _processar_dados_planta(planta1, None),
            'dados_planta2': _processar_dados_planta(planta2, None)
        }
        
        return render(request, 'projetista/comparacao_resultado.html', context)
        
    except (PlantaBaixa.DoesNotExist, ValueError):
        messages.error(request, 'Versões de planta inválidas')
        return redirect('projetista:projeto_detail', pk=projeto_id)

# =============================================================================
# UTILITÁRIOS
# =============================================================================

def _processar_dados_planta(planta_baixa, planta_service=None):
    """
    Processa dados da planta baixa de forma robusta
    """
    dados_json = {}
    resumo_decisoes = ''
    areas_atendidas = []
    tipo_estande = ''
    metodo_geracao = 'desconhecido'
    area_total = 0
    ambientes = []
    lados_abertos = []
    nucleo_central = {}
    
    if planta_service:
        try:
            # Usar serviço para extrair informações
            metodo_geracao = planta_service.get_metodo_geracao(planta_baixa)
            resumo_decisoes = planta_service.get_resumo_decisoes(planta_baixa)
            tipo_estande = planta_service.get_tipo_estande(planta_baixa)
            area_total = planta_service.get_area_total(planta_baixa)
            ambientes = planta_service.get_ambientes(planta_baixa)
            lados_abertos = planta_service.get_lados_abertos(planta_baixa)
            nucleo_central = planta_service.get_nucleo_central(planta_baixa)
            
            # Extrair áreas atendidas se disponível
            if planta_baixa.dados_json:
                dados_json = planta_baixa.dados_json
                areas_atendidas = dados_json.get('areas_atendidas', [])
                
        except Exception as e:
            logger.warning(f"Erro ao processar dados com serviço: {str(e)}")
    
    # Fallback: processar dados JSON diretamente
    if not dados_json:
        try:
            if planta_baixa.dados_json:
                if isinstance(planta_baixa.dados_json, dict):
                    dados_json = planta_baixa.dados_json
                else:
                    import json
                    dados_json = json.loads(planta_baixa.dados_json)
        except Exception as e:
            logger.warning(f"Erro ao processar dados_json: {str(e)}")
            dados_json = {}
    
    return {
        'dados_json': dados_json,
        'metodo_geracao': metodo_geracao,
        'resumo_decisoes': resumo_decisoes,
        'areas_atendidas': areas_atendidas,
        'tipo_estande': tipo_estande,
        'area_total': area_total,
        'ambientes': ambientes,
        'lados_abertos': lados_abertos,
        'nucleo_central': nucleo_central,
        'eh_planta_agente': metodo_geracao == 'agente'
    }

@login_required
def validar_agente_status(request):
    """
    Valida o status do agente Arquiteto de Estandes
    """
    try:
        planta_service = PlantaBaixaService()
        validacao = planta_service.validar_configuracao_agente()
        
        return JsonResponse({
            'success': True,
            'agente_valido': validacao['valido'],
            'detalhes': validacao
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'agente_valido': False,
            'error': str(e)
        })

@login_required
def exportar_dados_planta(request, planta_id):
    """
    Exporta dados de uma planta específica
    """
    planta = get_object_or_404(PlantaBaixa, pk=planta_id, projeto__projetista=request.user)
    
    try:
        planta_service = PlantaBaixaService()
        resultado = planta_service.exportar_dados_planta(planta)
        
        if resultado['success']:
            response = JsonResponse(resultado['dados'], json_dumps_params={'indent': 2})
            filename = f"planta_v{planta.versao}_{planta.projeto.numero}_dados.json"
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response
        else:
            messages.error(request, f"Erro ao exportar: {resultado['error']}")
            return redirect('projetista:visualizar_planta_baixa', projeto_id=planta.projeto.id)
            
    except Exception as e:
        logger.error(f"Erro ao exportar dados da planta: {str(e)}")
        messages.error(request, f"Erro ao exportar dados: {str(e)}")
        return redirect('projetista:visualizar_planta_baixa', projeto_id=planta.projeto.id)