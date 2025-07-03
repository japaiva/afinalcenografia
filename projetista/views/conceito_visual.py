# projetista/views/conceito_visual.py - VIEWS ESPECÍFICAS PARA CONCEITO VISUAL

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
from django.utils import timezone
import logging

from projetos.models import Projeto, Briefing
from projetista.models import PlantaBaixa, ConceitoVisualNovo
from core.services.conceito_visual_service import ConceitoVisualService

logger = logging.getLogger(__name__)

# =============================================================================
# GERAÇÃO E REFINAMENTO
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
                'message': 'É necessário ter uma planta baixa pronta antes de gerar o conceito visual.',
                'error_type': 'missing_dependency'
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
            conceito_gerado = resultado['conceito']
            
            messages.success(request, f'Conceito visual v{nova_versao} gerado com sucesso!')
            
            return JsonResponse({
                'success': True,
                'message': 'Conceito visual gerado com sucesso!',
                'conceito_id': conceito_gerado.id,
                'versao': nova_versao,
                'estilo_usado': estilo_visualizacao,
                'iluminacao_usada': iluminacao,
                'tem_instrucoes_adicionais': bool(instrucoes_adicionais.strip()),
                'baseado_em_planta': f"v{planta_baixa.versao}",
                'redirect_url': request.build_absolute_uri(f'/projetista/projetos/{projeto_id}/conceito-visual/')
            })
        else:
            return JsonResponse({
                'success': False,
                'message': f"Erro ao gerar conceito visual: {resultado['error']}",
                'error_type': 'generation_error',
                'details': resultado.get('details', '')
            })
            
    except Briefing.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Briefing não encontrado para este projeto.',
            'error_type': 'missing_briefing'
        })
    except Exception as e:
        logger.error(f"Erro ao gerar conceito visual: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': f"Erro ao processar solicitação: {str(e)}",
            'error_type': 'system_error'
        }, status=500)

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
        
        # Gerar nova versão refinada
        conceito_service = ConceitoVisualService()
        
        # Combinar instruções originais com refinamento
        instrucoes_combinadas = conceito.instrucoes_adicionais or ''
        if instrucoes_combinadas:
            instrucoes_combinadas += '\n\n'
        instrucoes_combinadas += f"REFINAMENTO: {instrucoes_refinamento}"
        
        resultado = conceito_service.gerar_conceito_visual(
            briefing=conceito.briefing,
            planta_baixa=conceito.planta_baixa,
            estilo_visualizacao=conceito.estilo_visualizacao,
            iluminacao=conceito.iluminacao,
            instrucoes_adicionais=instrucoes_combinadas,
            versao=conceito.versao + 1,
            conceito_anterior=conceito
        )
        
        if resultado['success']:
            # Marcar conceito anterior como substituído
            conceito.status = 'substituido'
            conceito.save(update_fields=['status'])
            
            conceito_refinado = resultado['conceito']
            
            return JsonResponse({
                'success': True,
                'message': 'Conceito visual refinado com sucesso!',
                'conceito_id': conceito_refinado.id,
                'versao': conceito_refinado.versao,
                'instrucoes_aplicadas': instrucoes_refinamento,
                'baseado_em_versao': conceito.versao,
                'redirect_url': request.build_absolute_uri(f'/projetista/projetos/{conceito.projeto.id}/conceito-visual/')
            })
        else:
            return JsonResponse({
                'success': False,
                'message': f"Erro ao refinar conceito: {resultado['error']}",
                'details': resultado.get('details', '')
            })
            
    except Exception as e:
        logger.error(f"Erro ao refinar conceito visual: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': f"Erro ao processar refinamento: {str(e)}"
        }, status=500)

# =============================================================================
# VISUALIZAÇÃO
# =============================================================================

@login_required
def visualizar_conceito_visual(request, projeto_id):
    """
    Visualiza o conceito visual atual
    """
    projeto = get_object_or_404(Projeto, pk=projeto_id, projetista=request.user)
    
    # Buscar conceito visual mais recente
    conceito_visual = ConceitoVisualNovo.objects.filter(projeto=projeto).order_by('-versao').first()
    
    if not conceito_visual:
        messages.info(request, 'Nenhum conceito visual encontrado para este projeto.')
        return redirect('projetista:projeto_detail', pk=projeto_id)
    
    # Permitir seleção de versão específica via GET parameter
    versao_solicitada = request.GET.get('versao')
    if versao_solicitada:
        try:
            versao_num = int(versao_solicitada)
            conceito_especifico = ConceitoVisualNovo.objects.filter(
                projeto=projeto, 
                versao=versao_num
            ).first()
            if conceito_especifico:
                conceito_visual = conceito_especifico
        except (ValueError, TypeError):
            pass
    
    # Listar todas as versões disponíveis
    versoes = ConceitoVisualNovo.objects.filter(projeto=projeto).order_by('-versao')
    
    # Verificar se pode refinar (se é a versão mais recente e está pronta)
    pode_refinar = (conceito_visual.status == 'pronto' and 
                   conceito_visual == versoes.first())
    
    # Obter informações da planta baixa usada como base
    planta_info = None
    if conceito_visual.planta_baixa:
        try:
            from core.services.crewai.specialized.planta_baixa import PlantaBaixaService
            planta_service = PlantaBaixaService()
            planta_info = {
                'versao': conceito_visual.planta_baixa.versao,
                'metodo': planta_service.get_metodo_geracao(conceito_visual.planta_baixa),
                'tipo_estande': planta_service.get_tipo_estande(conceito_visual.planta_baixa),
                'area_total': planta_service.get_area_total(conceito_visual.planta_baixa)
            }
        except Exception as e:
            logger.warning(f"Erro ao obter informações da planta: {str(e)}")
            planta_info = {
                'versao': conceito_visual.planta_baixa.versao,
                'metodo': 'desconhecido',
                'tipo_estande': 'não especificado',
                'area_total': 0
            }
    
    context = {
        'projeto': projeto,
        'conceito_visual': conceito_visual,
        'versoes': versoes,
        'pode_refinar': pode_refinar,
        'planta_info': planta_info,
        'tem_instrucoes_adicionais': bool(conceito_visual.instrucoes_adicionais and conceito_visual.instrucoes_adicionais.strip())
    }
    
    return render(request, 'projetista/conceito_visual.html', context)

@login_required
def galeria_conceitos(request, projeto_id):
    """
    Mostra galeria com todos os conceitos visuais do projeto
    """
    projeto = get_object_or_404(Projeto, pk=projeto_id, projetista=request.user)
    
    # Obter todos os conceitos com suas imagens
    conceitos = ConceitoVisualNovo.objects.filter(projeto=projeto).order_by('-versao')
    
    # Agrupar por versão (caso tenham múltiplas imagens por versão)
    conceitos_agrupados = {}
    for conceito in conceitos:
        versao = conceito.versao
        if versao not in conceitos_agrupados:
            conceitos_agrupados[versao] = {
                'conceito': conceito,
                'imagens': []
            }
        
        if conceito.imagem:
            conceitos_agrupados[versao]['imagens'].append({
                'url': conceito.imagem.url,
                'descricao': conceito.descricao or f"Conceito v{versao}",
                'estilo': conceito.estilo_visualizacao,
                'iluminacao': conceito.iluminacao
            })
    
    context = {
        'projeto': projeto,
        'conceitos_agrupados': conceitos_agrupados,
        'total_versoes': len(conceitos_agrupados)
    }
    
    return render(request, 'projetista/galeria_conceitos.html', context)

# =============================================================================
# DOWNLOADS E EXPORTAÇÃO
# =============================================================================

@login_required
def download_conceito_imagem(request, conceito_id):
    """
    Download da imagem do conceito visual
    """
    conceito = get_object_or_404(ConceitoVisualNovo, pk=conceito_id, projeto__projetista=request.user)
    
    if conceito.imagem:
        # Obter extensão do arquivo
        import os
        nome_original = conceito.imagem.name
        extensao = os.path.splitext(nome_original)[1] or '.png'
        
        response = HttpResponse(conceito.imagem.read(), content_type='image/png')
        filename = f"conceito_v{conceito.versao}_{conceito.projeto.numero}_{conceito.estilo_visualizacao}{extensao}"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response
    else:
        messages.error(request, 'Imagem do conceito não encontrada.')
        return redirect('projetista:visualizar_conceito_visual', projeto_id=conceito.projeto.id)

@login_required
def exportar_dados_conceito(request, conceito_id):
    """
    Exporta dados completos do conceito visual
    """
    conceito = get_object_or_404(ConceitoVisualNovo, pk=conceito_id, projeto__projetista=request.user)
    
    try:
        dados_exportacao = {
            'conceito_visual': {
                'versao': conceito.versao,
                'titulo': conceito.titulo,
                'descricao': conceito.descricao,
                'estilo_visualizacao': conceito.estilo_visualizacao,
                'iluminacao': conceito.iluminacao,
                'instrucoes_adicionais': conceito.instrucoes_adicionais,
                'status': conceito.status,
                'criado_em': conceito.criado_em.isoformat(),
                'atualizado_em': conceito.atualizado_em.isoformat()
            },
            'projeto': {
                'numero': conceito.projeto.numero,
                'nome': conceito.projeto.nome,
                'empresa': conceito.projeto.empresa.nome
            },
            'planta_base': {
                'versao': conceito.planta_baixa.versao if conceito.planta_baixa else None,
                'algoritmo': conceito.planta_baixa.algoritmo_usado if conceito.planta_baixa else None
            },
            'metadados': {
                'prompt_usado': getattr(conceito, 'prompt_geracao', ''),
                'modelo_ia': getattr(conceito, 'modelo_ia_usado', ''),
                'tem_imagem': bool(conceito.imagem)
            }
        }
        
        response = JsonResponse(dados_exportacao, json_dumps_params={'indent': 2})
        filename = f"conceito_v{conceito.versao}_{conceito.projeto.numero}_dados.json"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response
        
    except Exception as e:
        logger.error(f"Erro ao exportar dados do conceito: {str(e)}")
        messages.error(request, f"Erro ao exportar dados: {str(e)}")
        return redirect('projetista:visualizar_conceito_visual', projeto_id=conceito.projeto.id)

# =============================================================================
# UTILITÁRIOS E AJAX
# =============================================================================

@login_required
def status_conceito_visual(request, projeto_id):
    """
    Retorna status atual dos conceitos visuais do projeto
    """
    projeto = get_object_or_404(Projeto, pk=projeto_id, projetista=request.user)
    
    conceitos = ConceitoVisualNovo.objects.filter(projeto=projeto).order_by('-versao')
    conceito_atual = conceitos.first()
    
    status = {
        'existe': conceito_atual is not None,
        'versao_atual': conceito_atual.versao if conceito_atual else 0,
        'status_atual': conceito_atual.status if conceito_atual else None,
        'total_versoes': conceitos.count(),
        'estilo_atual': conceito_atual.estilo_visualizacao if conceito_atual else None,
        'iluminacao_atual': conceito_atual.iluminacao if conceito_atual else None,
        'tem_imagem': bool(conceito_atual and conceito_atual.imagem),
        'atualizado_em': conceito_atual.atualizado_em.isoformat() if conceito_atual else None,
        'pode_refinar': conceito_atual and conceito_atual.status == 'pronto',
        'historico': [
            {
                'versao': c.versao,
                'status': c.status,
                'criado_em': c.criado_em.isoformat(),
                'estilo': c.estilo_visualizacao,
                'tem_imagem': bool(c.imagem)
            } for c in conceitos[:5]  # Últimas 5 versões
        ]
    }
    
    return JsonResponse(status)

@login_required
@require_POST
def duplicar_conceito(request, conceito_id):
    """
    Duplica um conceito existente para nova versão com modificações
    """
    conceito_original = get_object_or_404(ConceitoVisualNovo, pk=conceito_id, projeto__projetista=request.user)
    
    try:
        # Obter novos parâmetros
        novo_estilo = request.POST.get('estilo_visualizacao', conceito_original.estilo_visualizacao)
        nova_iluminacao = request.POST.get('iluminacao', conceito_original.iluminacao)
        novas_instrucoes = request.POST.get('instrucoes_adicionais', conceito_original.instrucoes_adicionais)
        
        # Verificar se algo mudou
        mudou_algo = (novo_estilo != conceito_original.estilo_visualizacao or
                     nova_iluminacao != conceito_original.iluminacao or
                     novas_instrucoes != conceito_original.instrucoes_adicionais)
        
        if not mudou_algo:
            return JsonResponse({
                'success': False,
                'message': 'Nenhuma modificação foi feita. Altere pelo menos um parâmetro.'
            })
        
        # Gerar nova versão
        conceito_service = ConceitoVisualService()
        nova_versao = ConceitoVisualNovo.objects.filter(projeto=conceito_original.projeto).order_by('-versao').first().versao + 1
        
        resultado = conceito_service.gerar_conceito_visual(
            briefing=conceito_original.briefing,
            planta_baixa=conceito_original.planta_baixa,
            estilo_visualizacao=novo_estilo,
            iluminacao=nova_iluminacao,
            instrucoes_adicionais=novas_instrucoes,
            versao=nova_versao,
            conceito_anterior=conceito_original
        )
        
        if resultado['success']:
            conceito_duplicado = resultado['conceito']
            
            return JsonResponse({
                'success': True,
                'message': f'Conceito duplicado com sucesso (v{nova_versao})!',
                'conceito_id': conceito_duplicado.id,
                'versao': nova_versao,
                'mudancas': {
                    'estilo': novo_estilo if novo_estilo != conceito_original.estilo_visualizacao else None,
                    'iluminacao': nova_iluminacao if nova_iluminacao != conceito_original.iluminacao else None,
                    'instrucoes': 'modificadas' if novas_instrucoes != conceito_original.instrucoes_adicionais else None
                }
            })
        else:
            return JsonResponse({
                'success': False,
                'message': f"Erro ao duplicar conceito: {resultado['error']}"
            })
            
    except Exception as e:
        logger.error(f"Erro ao duplicar conceito: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': f"Erro ao processar duplicação: {str(e)}"
        }, status=500)

@login_required
@require_POST
def excluir_conceito(request, conceito_id):
    """
    Exclui uma versão de conceito visual (se não for a única)
    """
    conceito = get_object_or_404(ConceitoVisualNovo, pk=conceito_id, projeto__projetista=request.user)
    
    try:
        # Verificar se é a única versão
        total_conceitos = ConceitoVisualNovo.objects.filter(projeto=conceito.projeto).count()
        
        if total_conceitos <= 1:
            return JsonResponse({
                'success': False,
                'message': 'Não é possível excluir o único conceito visual do projeto.'
            })
        
        # Verificar se há modelos 3D dependentes
        from projetista.models import Modelo3D
        modelos_dependentes = Modelo3D.objects.filter(conceito_visual=conceito)
        
        if modelos_dependentes.exists():
            return JsonResponse({
                'success': False,
                'message': 'Este conceito não pode ser excluído pois há modelos 3D baseados nele.'
            })
        
        versao_excluida = conceito.versao
        conceito.delete()
        
        return JsonResponse({
            'success': True,
            'message': f'Conceito v{versao_excluida} excluído com sucesso!'
        })
        
    except Exception as e:
        logger.error(f"Erro ao excluir conceito: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': f"Erro ao excluir conceito: {str(e)}"
        }, status=500)