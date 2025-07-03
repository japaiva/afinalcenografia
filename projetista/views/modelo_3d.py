# projetista/views/modelo_3d.py - VIEWS ESPECÍFICAS PARA MODELO 3D

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
from django.utils import timezone
import logging

from projetos.models import Projeto, Briefing
from projetista.models import PlantaBaixa, ConceitoVisualNovo, Modelo3D
from core.services.modelo_3d_service import Modelo3DService

logger = logging.getLogger(__name__)

# =============================================================================
# GERAÇÃO E REFINAMENTO
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
        
        # Validar dependências
        if not planta_baixa:
            return JsonResponse({
                'success': False,
                'message': 'É necessário ter uma planta baixa pronta antes de gerar o modelo 3D.',
                'error_type': 'missing_planta_baixa'
            })
        
        if not conceito_visual:
            return JsonResponse({
                'success': False,
                'message': 'É necessário ter um conceito visual pronto antes de gerar o modelo 3D.',
                'error_type': 'missing_conceito_visual'
            })
        
        # Obter parâmetros opcionais
        qualidade = request.POST.get('qualidade', 'media')  # baixa, media, alta
        incluir_texturas = request.POST.get('incluir_texturas', 'true').lower() == 'true'
        incluir_iluminacao = request.POST.get('incluir_iluminacao', 'true').lower() == 'true'
        nivel_detalhe = request.POST.get('nivel_detalhe', 'medio')  # baixo, medio, alto
        
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
            modelo_anterior=modelo_anterior,
            parametros={
                'qualidade': qualidade,
                'incluir_texturas': incluir_texturas,
                'incluir_iluminacao': incluir_iluminacao,
                'nivel_detalhe': nivel_detalhe
            }
        )
        
        if resultado['success']:
            modelo_gerado = resultado['modelo']
            
            messages.success(request, f'Modelo 3D v{nova_versao} gerado com sucesso!')
            
            return JsonResponse({
                'success': True,
                'message': 'Modelo 3D gerado com sucesso!',
                'modelo_id': modelo_gerado.id,
                'versao': nova_versao,
                'arquivos_gerados': resultado.get('arquivos_gerados', []),
                'componentes_usados': resultado.get('componentes_usados', []),
                'parametros_usados': {
                    'qualidade': qualidade,
                    'incluir_texturas': incluir_texturas,
                    'incluir_iluminacao': incluir_iluminacao,
                    'nivel_detalhe': nivel_detalhe
                },
                'baseado_em': {
                    'planta_versao': planta_baixa.versao,
                    'conceito_versao': conceito_visual.versao
                },
                'redirect_url': request.build_absolute_uri(f'/projetista/projetos/{projeto_id}/modelo-3d/')
            })
        else:
            return JsonResponse({
                'success': False,
                'message': f"Erro ao gerar modelo 3D: {resultado['error']}",
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
        logger.error(f"Erro ao gerar modelo 3D: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': f"Erro ao processar solicitação: {str(e)}",
            'error_type': 'system_error'
        }, status=500)

@login_required
@require_POST
def refinar_modelo_3d(request, modelo_id):
    """
    Refina um modelo 3D existente
    """
    modelo = get_object_or_404(Modelo3D, pk=modelo_id, projeto__projetista=request.user)
    
    try:
        # Obter parâmetros de refinamento
        ajustes = {
            'iluminacao': request.POST.get('ajustar_iluminacao'),
            'materiais': request.POST.get('ajustar_materiais'),
            'geometria': request.POST.get('ajustar_geometria'),
            'cameras': request.POST.get('ajustar_cameras'),
            'texturas': request.POST.get('ajustar_texturas')
        }
        
        # Filtrar apenas ajustes que foram solicitados
        ajustes_solicitados = {k: v for k, v in ajustes.items() if v and v.strip()}
        
        if not ajustes_solicitados:
            return JsonResponse({
                'success': False,
                'message': 'Nenhum ajuste foi especificado.'
            })
        
        # Gerar versão refinada
        modelo_service = Modelo3DService()
        
        resultado = modelo_service.refinar_modelo_3d(
            modelo_atual=modelo,
            ajustes=ajustes_solicitados
        )
        
        if resultado['success']:
            # Marcar modelo anterior como substituído
            modelo.status = 'substituido'
            modelo.save(update_fields=['status'])
            
            modelo_refinado = resultado['modelo']
            
            return JsonResponse({
                'success': True,
                'message': f'Modelo 3D refinado com sucesso (v{modelo_refinado.versao})!',
                'modelo_id': modelo_refinado.id,
                'versao': modelo_refinado.versao,
                'ajustes_aplicados': list(ajustes_solicitados.keys()),
                'baseado_em_versao': modelo.versao,
                'redirect_url': request.build_absolute_uri(f'/projetista/projetos/{modelo.projeto.id}/modelo-3d/')
            })
        else:
            return JsonResponse({
                'success': False,
                'message': f"Erro ao refinar modelo: {resultado['error']}",
                'details': resultado.get('details', '')
            })
            
    except Exception as e:
        logger.error(f"Erro ao refinar modelo 3D: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': f"Erro ao processar refinamento: {str(e)}"
        }, status=500)

# =============================================================================
# VISUALIZAÇÃO
# =============================================================================

@login_required
def visualizar_modelo_3d(request, projeto_id):
    """
    Visualiza o modelo 3D navegável
    """
    projeto = get_object_or_404(Projeto, pk=projeto_id, projetista=request.user)
    
    # Buscar modelo 3D mais recente
    modelo_3d = Modelo3D.objects.filter(projeto=projeto).order_by('-versao').first()
    
    if not modelo_3d:
        messages.info(request, 'Nenhum modelo 3D encontrado para este projeto.')
        return redirect('projetista:projeto_detail', pk=projeto_id)
    
    # Permitir seleção de versão específica
    versao_solicitada = request.GET.get('versao')
    if versao_solicitada:
        try:
            versao_num = int(versao_solicitada)
            modelo_especifico = Modelo3D.objects.filter(
                projeto=projeto, 
                versao=versao_num
            ).first()
            if modelo_especifico:
                modelo_3d = modelo_especifico
        except (ValueError, TypeError):
            pass
    
    # Listar todas as versões disponíveis
    versoes = Modelo3D.objects.filter(projeto=projeto).order_by('-versao')
    
    # Preparar dados para o visualizador Three.js
    dados_cena = modelo_3d.dados_cena or {}
    camera_inicial = modelo_3d.camera_inicial or {
        'position': {'x': 10, 'y': 10, 'z': 10},
        'target': {'x': 0, 'y': 0, 'z': 0}
    }
    pontos_interesse = modelo_3d.pontos_interesse or []
    
    # Verificar arquivos disponíveis
    arquivos_disponiveis = []
    if modelo_3d.arquivo_gltf:
        arquivos_disponiveis.append({
            'formato': 'gltf',
            'url': modelo_3d.arquivo_gltf.url,
            'tamanho': modelo_3d.arquivo_gltf.size if hasattr(modelo_3d.arquivo_gltf, 'size') else None
        })
    if modelo_3d.arquivo_obj:
        arquivos_disponiveis.append({
            'formato': 'obj',
            'url': modelo_3d.arquivo_obj.url,
            'tamanho': modelo_3d.arquivo_obj.size if hasattr(modelo_3d.arquivo_obj, 'size') else None
        })
    if modelo_3d.arquivo_skp:
        arquivos_disponiveis.append({
            'formato': 'skp',
            'url': modelo_3d.arquivo_skp.url,
            'tamanho': modelo_3d.arquivo_skp.size if hasattr(modelo_3d.arquivo_skp, 'size') else None
        })
    
    # Verificar se pode refinar
    pode_refinar = (modelo_3d.status == 'pronto' and 
                   modelo_3d == versoes.first())
    
    # Obter informações das dependências
    dependencias_info = {
        'planta_baixa': None,
        'conceito_visual': None
    }
    
    if modelo_3d.planta_baixa:
        try:
            from core.services.crewai.specialized.planta_baixa import PlantaBaixaService
            planta_service = PlantaBaixaService()
            dependencias_info['planta_baixa'] = {
                'versao': modelo_3d.planta_baixa.versao,
                'metodo': planta_service.get_metodo_geracao(modelo_3d.planta_baixa),
                'area_total': planta_service.get_area_total(modelo_3d.planta_baixa)
            }
        except:
            dependencias_info['planta_baixa'] = {
                'versao': modelo_3d.planta_baixa.versao,
                'metodo': 'desconhecido',
                'area_total': 0
            }
    
    if modelo_3d.conceito_visual:
        dependencias_info['conceito_visual'] = {
            'versao': modelo_3d.conceito_visual.versao,
            'estilo': modelo_3d.conceito_visual.estilo_visualizacao,
            'iluminacao': modelo_3d.conceito_visual.iluminacao
        }
    
    context = {
        'projeto': projeto,
        'modelo_3d': modelo_3d,
        'versoes': versoes,
        'dados_cena': dados_cena,
        'camera_inicial': camera_inicial,
        'pontos_interesse': pontos_interesse,
        'arquivos_disponiveis': arquivos_disponiveis,
        'pode_refinar': pode_refinar,
        'dependencias_info': dependencias_info
    }
    
    return render(request, 'projetista/modelo_3d.html', context)

@login_required
def viewer_interativo(request, modelo_id):
    """
    Visualizador 3D interativo em tela cheia
    """
    modelo = get_object_or_404(Modelo3D, pk=modelo_id, projeto__projetista=request.user)
    
    # Verificar se tem arquivo GLTF (preferencial para visualização)
    if not modelo.arquivo_gltf:
        messages.error(request, 'Modelo 3D não possui arquivo GLTF para visualização.')
        return redirect('projetista:visualizar_modelo_3d', projeto_id=modelo.projeto.id)
    
    # Preparar configurações do viewer
    viewer_config = {
        'modelo_url': modelo.arquivo_gltf.url,
        'camera_inicial': modelo.camera_inicial or {},
        'pontos_interesse': modelo.pontos_interesse or [],
        'controles': {
            'zoom': True,
            'pan': True,
            'rotate': True,
            'reset_camera': True,
            'fullscreen': True,
            'wireframe': True,
            'materials': True
        },
        'ambiente': {
            'background_color': '#f0f0f0',
            'ambiente_light': True,
            'directional_light': True,
            'shadows': True
        }
    }
    
    context = {
        'modelo': modelo,
        'viewer_config': viewer_config,
        'projeto': modelo.projeto
    }
    
    return render(request, 'projetista/viewer_interativo.html', context)

# =============================================================================
# DOWNLOADS E EXPORTAÇÃO
# =============================================================================

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
        try:
            response = HttpResponse(arquivo.read(), content_type='application/octet-stream')
            filename = f"modelo_3d_v{modelo.versao}_{modelo.projeto.numero}.{formato.lower()}"
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            
            # Log do download
            logger.info(f"Download do modelo 3D: {filename} por {request.user.username}")
            
            return response
        except Exception as e:
            logger.error(f"Erro no download do modelo: {str(e)}")
            messages.error(request, f'Erro ao fazer download do arquivo {formato.upper()}: {str(e)}')
    else:
        messages.error(request, f'Arquivo {formato.upper()} não encontrado.')
    
    return redirect('projetista:visualizar_modelo_3d', projeto_id=modelo.projeto.id)

@login_required
def download_todos_formatos(request, modelo_id):
    """
    Download de todos os formatos disponíveis do modelo 3D em ZIP
    """
    modelo = get_object_or_404(Modelo3D, pk=modelo_id, projeto__projetista=request.user)
    
    try:
        import zipfile
        from io import BytesIO
        import os
        
        # Criar arquivo ZIP em memória
        zip_buffer = BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            arquivos_incluidos = 0
            
            # Adicionar cada formato disponível
            if modelo.arquivo_gltf and modelo.arquivo_gltf.name:
                try:
                    zip_file.writestr(f"modelo_v{modelo.versao}.gltf", modelo.arquivo_gltf.read())
                    arquivos_incluidos += 1
                except Exception as e:
                    logger.warning(f"Erro ao adicionar GLTF ao ZIP: {str(e)}")
            
            if modelo.arquivo_obj and modelo.arquivo_obj.name:
                try:
                    zip_file.writestr(f"modelo_v{modelo.versao}.obj", modelo.arquivo_obj.read())
                    arquivos_incluidos += 1
                except Exception as e:
                    logger.warning(f"Erro ao adicionar OBJ ao ZIP: {str(e)}")
            
            if modelo.arquivo_skp and modelo.arquivo_skp.name:
                try:
                    zip_file.writestr(f"modelo_v{modelo.versao}.skp", modelo.arquivo_skp.read())
                    arquivos_incluidos += 1
                except Exception as e:
                    logger.warning(f"Erro ao adicionar SKP ao ZIP: {str(e)}")
            
            # Adicionar arquivo de informações
            info_content = f"""Modelo 3D - Projeto {modelo.projeto.numero}
Versão: {modelo.versao}
Projeto: {modelo.projeto.nome}
Empresa: {modelo.projeto.empresa.nome}
Criado em: {modelo.criado_em.strftime('%d/%m/%Y %H:%M')}
Status: {modelo.get_status_display()}

Baseado em:
- Planta Baixa v{modelo.planta_baixa.versao if modelo.planta_baixa else 'N/A'}
- Conceito Visual v{modelo.conceito_visual.versao if modelo.conceito_visual else 'N/A'}

Arquivos incluídos: {arquivos_incluidos}
"""
            zip_file.writestr("README.txt", info_content)
        
        if arquivos_incluidos == 0:
            messages.error(request, 'Nenhum arquivo disponível para download.')
            return redirect('projetista:visualizar_modelo_3d', projeto_id=modelo.projeto.id)
        
        # Preparar resposta
        zip_buffer.seek(0)
        response = HttpResponse(zip_buffer.getvalue(), content_type='application/zip')
        filename = f"modelo_3d_completo_v{modelo.versao}_{modelo.projeto.numero}.zip"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        logger.info(f"Download completo do modelo 3D: {filename} por {request.user.username}")
        
        return response
        
    except Exception as e:
        logger.error(f"Erro ao criar ZIP do modelo: {str(e)}")
        messages.error(request, f'Erro ao criar arquivo ZIP: {str(e)}')
        return redirect('projetista:visualizar_modelo_3d', projeto_id=modelo.projeto.id)

@login_required
def exportar_dados_modelo(request, modelo_id):
    """
    Exporta dados completos do modelo 3D
    """
    modelo = get_object_or_404(Modelo3D, pk=modelo_id, projeto__projetista=request.user)
    
    try:
        dados_exportacao = {
            'modelo_3d': {
                'versao': modelo.versao,
                'status': modelo.status,
                'criado_em': modelo.criado_em.isoformat(),
                'atualizado_em': modelo.atualizado_em.isoformat(),
                'dados_cena': modelo.dados_cena,
                'camera_inicial': modelo.camera_inicial,
                'pontos_interesse': modelo.pontos_interesse
            },
            'projeto': {
                'numero': modelo.projeto.numero,
                'nome': modelo.projeto.nome,
                'empresa': modelo.projeto.empresa.nome
            },
            'dependencias': {
                'planta_baixa': {
                    'versao': modelo.planta_baixa.versao if modelo.planta_baixa else None,
                    'algoritmo': modelo.planta_baixa.algoritmo_usado if modelo.planta_baixa else None
                },
                'conceito_visual': {
                    'versao': modelo.conceito_visual.versao if modelo.conceito_visual else None,
                    'estilo': modelo.conceito_visual.estilo_visualizacao if modelo.conceito_visual else None
                }
            },
            'arquivos': {
                'gltf_disponivel': bool(modelo.arquivo_gltf),
                'obj_disponivel': bool(modelo.arquivo_obj),
                'skp_disponivel': bool(modelo.arquivo_skp)
            },
            'metadados': {
                'parametros_geracao': getattr(modelo, 'parametros_geracao', {}),
                'componentes_usados': getattr(modelo, 'componentes_usados', []),
                'tempo_geracao': getattr(modelo, 'tempo_geracao', None)
            }
        }
        
        response = JsonResponse(dados_exportacao, json_dumps_params={'indent': 2})
        filename = f"modelo_3d_v{modelo.versao}_{modelo.projeto.numero}_dados.json"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response
        
    except Exception as e:
        logger.error(f"Erro ao exportar dados do modelo: {str(e)}")
        messages.error(request, f"Erro ao exportar dados: {str(e)}")
        return redirect('projetista:visualizar_modelo_3d', projeto_id=modelo.projeto.id)

# =============================================================================
# UTILITÁRIOS E AJAX
# =============================================================================

@login_required
def status_modelo_3d(request, projeto_id):
    """
    Retorna status atual dos modelos 3D do projeto
    """
    projeto = get_object_or_404(Projeto, pk=projeto_id, projetista=request.user)
    
    modelos = Modelo3D.objects.filter(projeto=projeto).order_by('-versao')
    modelo_atual = modelos.first()
    
    status = {
        'existe': modelo_atual is not None,
        'versao_atual': modelo_atual.versao if modelo_atual else 0,
        'status_atual': modelo_atual.status if modelo_atual else None,
        'total_versoes': modelos.count(),
        'arquivos_disponiveis': {
            'gltf': bool(modelo_atual and modelo_atual.arquivo_gltf),
            'obj': bool(modelo_atual and modelo_atual.arquivo_obj),
            'skp': bool(modelo_atual and modelo_atual.arquivo_skp)
        } if modelo_atual else {},
        'atualizado_em': modelo_atual.atualizado_em.isoformat() if modelo_atual else None,
        'pode_refinar': modelo_atual and modelo_atual.status == 'pronto',
        'dependencias': {
            'tem_planta': bool(modelo_atual and modelo_atual.planta_baixa),
            'tem_conceito': bool(modelo_atual and modelo_atual.conceito_visual),
            'planta_versao': modelo_atual.planta_baixa.versao if modelo_atual and modelo_atual.planta_baixa else None,
            'conceito_versao': modelo_atual.conceito_visual.versao if modelo_atual and modelo_atual.conceito_visual else None
        } if modelo_atual else {},
        'historico': [
            {
                'versao': m.versao,
                'status': m.status,
                'criado_em': m.criado_em.isoformat(),
                'tem_arquivos': bool(m.arquivo_gltf or m.arquivo_obj or m.arquivo_skp)
            } for m in modelos[:5]  # Últimas 5 versões
        ]
    }
    
    return JsonResponse(status)

@login_required
@require_POST
def atualizar_camera_modelo(request, modelo_id):
    """
    Atualiza posição da câmera inicial do modelo
    """
    modelo = get_object_or_404(Modelo3D, pk=modelo_id, projeto__projetista=request.user)
    
    try:
        import json
        
        # Obter nova posição da câmera
        camera_data = json.loads(request.body)
        
        # Validar dados
        required_fields = ['position', 'target']
        for field in required_fields:
            if field not in camera_data:
                return JsonResponse({
                    'success': False,
                    'message': f'Campo {field} é obrigatório'
                })
        
        # Atualizar câmera inicial
        modelo.camera_inicial = camera_data
        modelo.save(update_fields=['camera_inicial'])
        
        return JsonResponse({
            'success': True,
            'message': 'Posição da câmera atualizada com sucesso!'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': 'Dados JSON inválidos'
        })
    except Exception as e:
        logger.error(f"Erro ao atualizar câmera: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'Erro ao atualizar câmera: {str(e)}'
        }, status=500)

@login_required
@require_POST
def adicionar_ponto_interesse(request, modelo_id):
    """
    Adiciona um ponto de interesse ao modelo
    """
    modelo = get_object_or_404(Modelo3D, pk=modelo_id, projeto__projetista=request.user)
    
    try:
        import json
        
        # Obter dados do ponto
        ponto_data = json.loads(request.body)
        
        # Validar dados obrigatórios
        required_fields = ['nome', 'posicao', 'descricao']
        for field in required_fields:
            if field not in ponto_data:
                return JsonResponse({
                    'success': False,
                    'message': f'Campo {field} é obrigatório'
                })
        
        # Obter pontos existentes
        pontos = modelo.pontos_interesse or []
        
        # Adicionar novo ponto
        novo_ponto = {
            'id': len(pontos) + 1,
            'nome': ponto_data['nome'],
            'posicao': ponto_data['posicao'],
            'descricao': ponto_data['descricao'],
            'criado_em': timezone.now().isoformat(),
            'criado_por': request.user.username
        }
        
        pontos.append(novo_ponto)
        
        # Salvar
        modelo.pontos_interesse = pontos
        modelo.save(update_fields=['pontos_interesse'])
        
        return JsonResponse({
            'success': True,
            'message': 'Ponto de interesse adicionado com sucesso!',
            'ponto': novo_ponto
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': 'Dados JSON inválidos'
        })
    except Exception as e:
        logger.error(f"Erro ao adicionar ponto de interesse: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'Erro ao adicionar ponto: {str(e)}'
        }, status=500)

@login_required
@require_POST
def excluir_modelo(request, modelo_id):
    """
    Exclui uma versão de modelo 3D (se não for a única)
    """
    modelo = get_object_or_404(Modelo3D, pk=modelo_id, projeto__projetista=request.user)
    
    try:
        # Verificar se é a única versão
        total_modelos = Modelo3D.objects.filter(projeto=modelo.projeto).count()
        
        if total_modelos <= 1:
            return JsonResponse({
                'success': False,
                'message': 'Não é possível excluir o único modelo 3D do projeto.'
            })
        
        # Verificar se é a versão mais recente
        modelo_mais_recente = Modelo3D.objects.filter(projeto=modelo.projeto).order_by('-versao').first()
        
        if modelo.id == modelo_mais_recente.id:
            return JsonResponse({
                'success': False,
                'message': 'Não é possível excluir a versão mais recente. Crie uma nova versão primeiro.'
            })
        
        versao_excluida = modelo.versao
        modelo.delete()
        
        return JsonResponse({
            'success': True,
            'message': f'Modelo 3D v{versao_excluida} excluído com sucesso!'
        })
        
    except Exception as e:
        logger.error(f"Erro ao excluir modelo: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': f"Erro ao excluir modelo: {str(e)}"
        }, status=500)

@login_required
def preview_modelo(request, modelo_id):
    """
    Gera preview/thumbnail do modelo 3D
    """
    modelo = get_object_or_404(Modelo3D, pk=modelo_id, projeto__projetista=request.user)
    
    try:
        # Aqui seria implementada a lógica para gerar preview
        # Por enquanto, retorna um placeholder
        
        return JsonResponse({
            'success': True,
            'preview_url': '/static/img/modelo_3d_placeholder.png',
            'message': 'Preview gerado com sucesso'
        })
        
    except Exception as e:
        logger.error(f"Erro ao gerar preview: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'Erro ao gerar preview: {str(e)}'
        }, status=500)