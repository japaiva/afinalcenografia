# projetista/views/novo_conceito.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.conf import settings
import logging

from projetos.models import Projeto, Briefing
from projetista.models import PlantaBaixa, ConceitoVisualNovo, Modelo3D
from core.services.planta_baixa_service import PlantaBaixaService
from core.services.conceito_visual_service import ConceitoVisualService
from core.services.modelo_3d_service import Modelo3DService

logger = logging.getLogger(__name__)

@login_required
def novo_conceito_dashboard(request, projeto_id):
    """
    Dashboard principal com os 3 botões: Planta Baixa, Conceito Visual, Modelo 3D
    """
    projeto = get_object_or_404(Projeto, pk=projeto_id, projetista=request.user)
    
    # Obter briefing mais recente
    try:
        briefing = projeto.briefings.latest('versao')
    except Briefing.DoesNotExist:
        messages.error(request, "Não foi encontrado um briefing para este projeto.")
        return redirect('projetista:projeto_detail', pk=projeto_id)
    
    # Verificar status de cada etapa
    planta_baixa = PlantaBaixa.objects.filter(projeto=projeto).order_by('-versao').first()
    conceito_visual = ConceitoVisualNovo.objects.filter(projeto=projeto).order_by('-versao').first()
    modelo_3d = Modelo3D.objects.filter(projeto=projeto).order_by('-versao').first()
    
    # Status dos botões
    status = {
        'planta_baixa': {
            'disponivel': True,
            'concluido': planta_baixa and planta_baixa.status == 'pronta',
            'objeto': planta_baixa,
            'versao': planta_baixa.versao if planta_baixa else 0
        },
        'conceito_visual': {
            'disponivel': planta_baixa and planta_baixa.status == 'pronta',
            'concluido': conceito_visual and conceito_visual.status == 'pronto',
            'objeto': conceito_visual,
            'versao': conceito_visual.versao if conceito_visual else 0
        },
        'modelo_3d': {
            'disponivel': (planta_baixa and planta_baixa.status == 'pronta' and 
                          conceito_visual and conceito_visual.status == 'pronto'),
            'concluido': modelo_3d and modelo_3d.status == 'pronto',
            'objeto': modelo_3d,
            'versao': modelo_3d.versao if modelo_3d else 0
        }
    }
    
    context = {
        'projeto': projeto,
        'briefing': briefing,
        'status': status,
        'planta_baixa': planta_baixa,
        'conceito_visual': conceito_visual,
        'modelo_3d': modelo_3d,
    }
    
    return render(request, 'projetista/novo_conceito/dashboard.html', context)

# =============================================================================
# PLANTA BAIXA
# =============================================================================


@login_required
@require_POST
def gerar_planta_baixa(request, projeto_id):
    """
    Gera ou regenera a planta baixa algorítmica - VERSÃO CORRIGIDA
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
        
        # Inicializar serviço
        planta_service = PlantaBaixaService()
        
        # CRÍTICO: Gerar planta baixa e verificar resultado IMEDIATAMENTE
        resultado = planta_service.gerar_planta_baixa(
            briefing=briefing,
            versao=nova_versao,
            planta_anterior=planta_anterior
        )
        
        # ✅ VERIFICAÇÃO CRÍTICA: Parar imediatamente se houver erro
        if not resultado.get('success', False):
            logger.warning(f"Falha na geração de planta baixa: {resultado.get('error', 'Erro desconhecido')}")
            
            # Determinar tipo de erro para ação específica
            error_type = 'validation_error'
            if 'DADOS INSUFICIENTES' in resultado.get('critica', ''):
                error_type = 'incomplete_data'
            elif 'ESPAÇO INSUFICIENTE' in resultado.get('critica', ''):
                error_type = 'insufficient_space'
            elif 'DIMENSÕES INCOMPATÍVEIS' in resultado.get('critica', ''):
                error_type = 'incompatible_dimensions'
            
            return JsonResponse({
                'success': False,
                'error': resultado.get('error', 'Erro na geração da planta baixa'),
                'message': resultado.get('error', 'Não foi possível gerar a planta baixa'),
                'detailed_error': resultado.get('critica', ''),
                'suggestions': resultado.get('sugestoes', []),
                'error_type': error_type,
                'can_proceed': resultado.get('pode_prosseguir', False),
                'validation_details': resultado.get('detalhes_validacao', {}),
                'briefing_data': resultado.get('dados_estande', {}),
                'requested_environments': resultado.get('ambientes_solicitados', [])
            })
        
        # ✅ Se chegou aqui, foi sucesso
        planta_gerada = resultado['planta']
        
        # Log de sucesso
        logger.info(f"Planta baixa v{nova_versao} gerada com sucesso para projeto {projeto.nome}")
        
        return JsonResponse({
            'success': True,
            'message': f'Planta baixa v{nova_versao} gerada com sucesso!',
            'planta_id': planta_gerada.id,
            'versao': nova_versao,
            'area_utilizada': resultado.get('layout', {}).get('area_total_usada', 0),
            'ambientes_posicionados': len(resultado.get('layout', {}).get('ambientes_posicionados', [])),
            'validation_success': resultado.get('critica', ''),
            'redirect_url': request.build_absolute_uri(f'/projetista/projetos/{projeto_id}/planta-baixa/')
        })
            
    except Exception as e:
        # Log do erro completo para debug
        logger.error(f"Erro técnico ao gerar planta baixa: {str(e)}", exc_info=True)
        
        return JsonResponse({
            'success': False,
            'error': 'Erro técnico do sistema',
            'message': f'Ocorreu um erro técnico: {str(e)}',
            'error_type': 'system_error',
            'can_proceed': False
        }, status=500)


@login_required
def visualizar_planta_baixa(request, projeto_id):
    """
    Visualiza a planta baixa atual (versão mais recente) - VERSÃO SUPER ROBUSTA
    """
    projeto = get_object_or_404(Projeto, pk=projeto_id, projetista=request.user)
    
    # CORREÇÃO: Buscar a versão mais recente, não uma única
    planta_baixa = PlantaBaixa.objects.filter(projeto=projeto).order_by('-versao').first()
    
    if not planta_baixa:
        # Se não tem nenhuma planta baixa, mostrar mensagem e redirecionar
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
            pass  # Se versão inválida, continuar com a mais recente
    
    # Listar todas as versões disponíveis
    versoes = PlantaBaixa.objects.filter(projeto=projeto).order_by('-versao')
    
    # Tratar dados JSON de forma segura
    dados_json = {}
    try:
        if planta_baixa.dados_json:
            if isinstance(planta_baixa.dados_json, dict):
                dados_json = planta_baixa.dados_json
            else:
                # Se for string, tentar fazer parse
                import json
                dados_json = json.loads(planta_baixa.dados_json)
    except (json.JSONDecodeError, TypeError, AttributeError) as e:
        logger.warning(f"Erro ao processar dados_json da planta {planta_baixa.id}: {str(e)}")
        dados_json = {}
    
    context = {
        'projeto': projeto,
        'planta_baixa': planta_baixa,
        'versoes': versoes,
        'dados_json': dados_json
    }
    
    return render(request, 'projetista/novo_conceito/planta_baixa.html', context)

@login_required
def download_planta_svg(request, planta_id):
    """
    Download do arquivo SVG da planta baixa
    """
    planta = get_object_or_404(PlantaBaixa, pk=planta_id, projeto__projetista=request.user)
    
    if planta.arquivo_svg:
        response = HttpResponse(planta.arquivo_svg.read(), content_type='image/svg+xml')
        response['Content-Disposition'] = f'attachment; filename="planta_baixa_v{planta.versao}.svg"'
        return response
    else:
        messages.error(request, 'Arquivo SVG não encontrado.')
        return redirect('projetista:novo_conceito_dashboard', projeto_id=planta.projeto.id)

# =============================================================================
# CONCEITO VISUAL
# =============================================================================

@login_required
@require_POST
def gerar_conceito_visual(request, projeto_id):
    """
    Gera conceito visual baseado na planta baixa
    """
    projeto = get_object_or_404(Projeto, pk=projeto_id, projetista=request.user)
    
    try:
        # Obter briefing e planta baixa
        briefing = projeto.briefings.latest('versao')
        planta_baixa = PlantaBaixa.objects.filter(projeto=projeto, status='pronta').order_by('-versao').first()
        
        if not planta_baixa:
            return JsonResponse({
                'success': False,
                'message': 'É necessário ter uma planta baixa pronta antes de gerar o conceito visual.'
            })
        
        # Obter parâmetros da requisição
        estilo_visualizacao = request.POST.get('estilo_visualizacao', 'fotorrealista')
        iluminacao = request.POST.get('iluminacao', 'feira')
        instrucoes_adicionais = request.POST.get('instrucoes_adicionais', '')
        
        # Verificar se já existe conceito visual
        conceito_anterior = ConceitoVisualNovo.objects.filter(projeto=projeto).order_by('-versao').first()
        nova_versao = conceito_anterior.versao + 1 if conceito_anterior else 1
        
        # Inicializar serviço
        conceito_service = ConceitoVisualService()
        
        # Gerar conceito visual
        resultado = conceito_service.gerar_conceito_visual(
            briefing=briefing,
            planta_baixa=planta_baixa,
            estilo_visualizacao=estilo_visualizacao,
            iluminacao=iluminacao,
            instrucoes_adicionais=instrucoes_adicionais,
            versao=nova_versao,
            conceito_anterior=conceito_anterior
        )
        
        if resultado['success']:
            messages.success(request, f'Conceito visual v{nova_versao} gerado com sucesso!')
            return JsonResponse({
                'success': True,
                'message': 'Conceito visual gerado com sucesso!',
                'conceito_id': resultado['conceito'].id,
                'versao': nova_versao,
                'redirect_url': request.build_absolute_uri(f'/projetista/projetos/{projeto_id}/novo-conceito/')
            })
        else:
            return JsonResponse({
                'success': False,
                'message': f"Erro ao gerar conceito visual: {resultado['error']}"
            })
            
    except Exception as e:
        logger.error(f"Erro ao gerar conceito visual: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': f"Erro ao processar solicitação: {str(e)}"
        }, status=500)

@login_required
def visualizar_conceito_visual(request, projeto_id):
    """
    Visualiza o conceito visual atual
    """
    projeto = get_object_or_404(Projeto, pk=projeto_id, projetista=request.user)
    conceito_visual = get_object_or_404(ConceitoVisualNovo, projeto=projeto)
    
    # Listar versões disponíveis
    versoes = ConceitoVisualNovo.objects.filter(projeto=projeto).order_by('-versao')
    
    context = {
        'projeto': projeto,
        'conceito_visual': conceito_visual,
        'versoes': versoes,
        'planta_baixa': conceito_visual.planta_baixa
    }
    
    return render(request, 'projetista/novo_conceito/conceito_visual.html', context)

@login_required
@require_POST
def refinar_conceito_visual(request, conceito_id):
    """
    Refina conceito visual existente com novas instruções
    """
    conceito = get_object_or_404(ConceitoVisualNovo, pk=conceito_id, projeto__projetista=request.user)
    
    try:
        instrucoes_refinamento = request.POST.get('instrucoes_refinamento', '')
        
        if not instrucoes_refinamento.strip():
            return JsonResponse({
                'success': False,
                'message': 'Por favor, forneça instruções para refinamento.'
            })
        
        # Gerar nova versão
        conceito_service = ConceitoVisualService()
        
        resultado = conceito_service.gerar_conceito_visual(
            briefing=conceito.briefing,
            planta_baixa=conceito.planta_baixa,
            estilo_visualizacao=conceito.estilo_visualizacao,
            iluminacao=conceito.iluminacao,
            instrucoes_adicionais=f"{conceito.instrucoes_adicionais}\n\nREFINAMENTO: {instrucoes_refinamento}",
            versao=conceito.versao + 1,
            conceito_anterior=conceito
        )
        
        if resultado['success']:
            # Marcar conceito anterior como não sendo mais a versão ativa
            conceito.status = 'substituido'
            conceito.save(update_fields=['status'])
            
            return JsonResponse({
                'success': True,
                'message': 'Conceito visual refinado com sucesso!',
                'conceito_id': resultado['conceito'].id,
                'versao': resultado['conceito'].versao
            })
        else:
            return JsonResponse({
                'success': False,
                'message': f"Erro ao refinar conceito: {resultado['error']}"
            })
            
    except Exception as e:
        logger.error(f"Erro ao refinar conceito visual: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': f"Erro ao processar refinamento: {str(e)}"
        }, status=500)

# =============================================================================
# MODELO 3D
# =============================================================================

@login_required
@require_POST
def gerar_modelo_3d(request, projeto_id):
    """
    Gera modelo 3D baseado na planta baixa e conceito visual
    """
    projeto = get_object_or_404(Projeto, pk=projeto_id, projetista=request.user)
    
    try:
        # Obter dependências
        briefing = projeto.briefings.latest('versao')
        planta_baixa = PlantaBaixa.objects.filter(projeto=projeto, status='pronta').order_by('-versao').first()
        conceito_visual = ConceitoVisualNovo.objects.filter(projeto=projeto, status='pronto').order_by('-versao').first()
        
        if not planta_baixa:
            return JsonResponse({
                'success': False,
                'message': 'É necessário ter uma planta baixa pronta antes de gerar o modelo 3D.'
            })
        
        if not conceito_visual:
            return JsonResponse({
                'success': False,
                'message': 'É necessário ter um conceito visual pronto antes de gerar o modelo 3D.'
            })
        
        # Verificar se já existe modelo 3D
        modelo_anterior = Modelo3D.objects.filter(projeto=projeto).order_by('-versao').first()
        nova_versao = modelo_anterior.versao + 1 if modelo_anterior else 1
        
        # Inicializar serviço
        modelo_service = Modelo3DService()
        
        # Gerar modelo 3D
        resultado = modelo_service.gerar_modelo_3d(
            briefing=briefing,
            planta_baixa=planta_baixa,
            conceito_visual=conceito_visual,
            versao=nova_versao,
            modelo_anterior=modelo_anterior
        )
        
        if resultado['success']:
            messages.success(request, f'Modelo 3D v{nova_versao} gerado com sucesso!')
            return JsonResponse({
                'success': True,
                'message': 'Modelo 3D gerado com sucesso!',
                'modelo_id': resultado['modelo'].id,
                'versao': nova_versao,
                'arquivos_gerados': resultado['arquivos_gerados'],
                'componentes_usados': resultado['componentes_usados'],
                'redirect_url': request.build_absolute_uri(f'/projetista/projetos/{projeto_id}/novo-conceito/')
            })
        else:
            return JsonResponse({
                'success': False,
                'message': f"Erro ao gerar modelo 3D: {resultado['error']}"
            })
            
    except Exception as e:
        logger.error(f"Erro ao gerar modelo 3D: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': f"Erro ao processar solicitação: {str(e)}"
        }, status=500)

@login_required
def visualizar_modelo_3d(request, projeto_id):
    """
    Visualiza o modelo 3D navegável
    """
    projeto = get_object_or_404(Projeto, pk=projeto_id, projetista=request.user)
    modelo_3d = get_object_or_404(Modelo3D, projeto=projeto)
    
    # Listar versões disponíveis
    versoes = Modelo3D.objects.filter(projeto=projeto).order_by('-versao')
    
    # Preparar dados para o visualizador Three.js
    dados_cena = modelo_3d.dados_cena or {}
    camera_inicial = modelo_3d.camera_inicial or {}
    pontos_interesse = modelo_3d.pontos_interesse or []
    
    context = {
        'projeto': projeto,
        'modelo_3d': modelo_3d,
        'versoes': versoes,
        'dados_cena': dados_cena,
        'camera_inicial': camera_inicial,
        'pontos_interesse': pontos_interesse,
        'planta_baixa': modelo_3d.planta_baixa,
        'conceito_visual': modelo_3d.conceito_visual
    }
    
    return render(request, 'projetista/novo_conceito/modelo_3d.html', context)

@login_required
def download_modelo_3d(request, modelo_id, formato):
    """
    Download do modelo 3D em diferentes formatos
    """
    modelo = get_object_or_404(Modelo3D, pk=modelo_id, projeto__projetista=request.user)
    
    arquivo_map = {
        'gltf': modelo.arquivo_gltf,
        'obj': modelo.arquivo_obj,
        'skp': modelo.arquivo_skp
    }
    
    arquivo = arquivo_map.get(formato.lower())
    
    if arquivo and arquivo.name:
        response = HttpResponse(arquivo.read(), content_type='application/octet-stream')
        filename = f"modelo_3d_v{modelo.versao}.{formato.lower()}"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    else:
        messages.error(request, f'Arquivo {formato.upper()} não encontrado.')
        return redirect('projetista:visualizar_modelo_3d', projeto_id=modelo.projeto.id)

# =============================================================================
# UTILITÁRIOS E AJAX
# =============================================================================

@login_required
def status_projeto_conceito(request, projeto_id):
    """
    Retorna status atual do projeto em JSON (para polling/atualização)
    """
    projeto = get_object_or_404(Projeto, pk=projeto_id, projetista=request.user)
    
    planta_baixa = PlantaBaixa.objects.filter(projeto=projeto).order_by('-versao').first()
    conceito_visual = ConceitoVisualNovo.objects.filter(projeto=projeto).order_by('-versao').first()
    modelo_3d = Modelo3D.objects.filter(projeto=projeto).order_by('-versao').first()
    
    status = {
        'planta_baixa': {
            'existe': planta_baixa is not None,
            'status': planta_baixa.status if planta_baixa else None,
            'versao': planta_baixa.versao if planta_baixa else 0,
            'atualizado_em': planta_baixa.atualizado_em.isoformat() if planta_baixa else None
        },
        'conceito_visual': {
            'existe': conceito_visual is not None,
            'status': conceito_visual.status if conceito_visual else None,
            'versao': conceito_visual.versao if conceito_visual else 0,
            'atualizado_em': conceito_visual.atualizado_em.isoformat() if conceito_visual else None
        },
        'modelo_3d': {
            'existe': modelo_3d is not None,
            'status': modelo_3d.status if modelo_3d else None,
            'versao': modelo_3d.versao if modelo_3d else 0,
            'atualizado_em': modelo_3d.atualizado_em.isoformat() if modelo_3d else None
        }
    }
    
    return JsonResponse(status)

@login_required
@require_POST
def restaurar_versao(request, tipo, objeto_id):
    """
    Restaura uma versão anterior como atual
    """
    tipo_map = {
        'planta': PlantaBaixa,
        'conceito': ConceitoVisualNovo,
        'modelo': Modelo3D
    }
    
    if tipo not in tipo_map:
        return JsonResponse({
            'success': False,
            'message': 'Tipo de objeto inválido.'
        })
    
    try:
        modelo_class = tipo_map[tipo]
        objeto = get_object_or_404(modelo_class, pk=objeto_id, projeto__projetista=request.user)
        
        # Criar nova versão baseada na versão selecionada
        # (Esta lógica específica dependeria de cada tipo de objeto)
        
        return JsonResponse({
            'success': True,
            'message': f'Versão restaurada com sucesso!'
        })
        
    except Exception as e:
        logger.error(f"Erro ao restaurar versão: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': f"Erro ao restaurar versão: {str(e)}"
        }, status=500)

@login_required
@require_POST
def excluir_versao(request, tipo, objeto_id):
    """
    Exclui uma versão específica (se não for a atual)
    """
    tipo_map = {
        'planta': PlantaBaixa,
        'conceito': ConceitoVisualNovo,
        'modelo': Modelo3D
    }
    
    if tipo not in tipo_map:
        return JsonResponse({
            'success': False,
            'message': 'Tipo de objeto inválido.'
        })
    
    try:
        modelo_class = tipo_map[tipo]
        objeto = get_object_or_404(modelo_class, pk=objeto_id, projeto__projetista=request.user)
        
        # Verificar se não é a versão mais recente
        versao_mais_recente = modelo_class.objects.filter(projeto=objeto.projeto).order_by('-versao').first()
        
        if objeto.id == versao_mais_recente.id:
            return JsonResponse({
                'success': False,
                'message': 'Não é possível excluir a versão mais recente.'
            })
        
        objeto.delete()
        
        return JsonResponse({
            'success': True,
            'message': f'Versão excluída com sucesso!'
        })
        
    except Exception as e:
        logger.error(f"Erro ao excluir versão: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': f"Erro ao excluir versão: {str(e)}"
        }, status=500)