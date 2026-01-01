"""
Views para Modelo 3D (Módulo 3)

Interface para geração de modelo 3D (.obj) a partir da planta baixa
Compatível com 3ds Max, Blender, SketchUp, etc.
"""

import logging
import os
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse, FileResponse
from django.views.decorators.http import require_http_methods, require_POST
from django.core.files.base import ContentFile
from django.utils import timezone

from projetos.models import Projeto
from core.services.exportador_3d_service import Exportador3DService

logger = logging.getLogger(__name__)


@login_required
@require_http_methods(["GET"])
def modelo_3d_wizard(request, projeto_id):
    """
    Tela principal do wizard de Modelo 3D
    """
    projeto = get_object_or_404(Projeto, id=projeto_id)

    # Verificar se planta baixa foi gerada
    if not projeto.planta_baixa_json:
        return render(request, 'gestor/erro.html', {
            'titulo': 'Planta Baixa Pendente',
            'mensagem': 'Complete o módulo de Planta Baixa antes de gerar o modelo 3D.',
            'link_voltar': f'/gestor/projeto/{projeto.id}/planta-baixa/',
            'texto_voltar': 'Ir para Planta Baixa'
        })

    # Extrair informações para exibição
    dims = projeto.planta_baixa_json.get('dimensoes_totais', {})
    areas = projeto.planta_baixa_json.get('areas', [])

    context = {
        'projeto': projeto,
        'modelo_3d_gerado': projeto.modelo_3d_processado,
        'dimensoes': dims,
        'areas': areas,
        'total_areas': len(areas),
    }

    return render(request, 'gestor/modelo_3d_wizard.html', context)


@login_required
@require_POST
def modelo_3d_gerar(request, projeto_id):
    """
    Gera modelo 3D (.obj) a partir da planta baixa
    """
    projeto = get_object_or_404(Projeto, id=projeto_id)

    logger.info(f"[Modelo 3D] Gerando modelo - Projeto {projeto.id}")

    try:
        if not projeto.planta_baixa_json:
            return JsonResponse({
                'sucesso': False,
                'erro': 'Planta baixa não encontrada. Gere a planta baixa primeiro.'
            })

        # Criar exportador
        exportador = Exportador3DService(projeto.planta_baixa_json)

        # Gerar modelo
        obj_data, mtl_data, metadados = exportador.gerar_modelo_3d()

        # Salvar arquivo OBJ no projeto
        nome_arquivo = f"modelo_3d_{projeto.id}.obj"
        projeto.arquivo_3d.save(nome_arquivo, ContentFile(obj_data), save=False)

        # Atualizar flags do projeto
        projeto.modelo_3d_processado = True
        projeto.data_modelo_3d = timezone.now()
        projeto.save(update_fields=['arquivo_3d', 'modelo_3d_processado', 'data_modelo_3d'])

        logger.info(f"[Modelo 3D] Modelo gerado com sucesso - Projeto {projeto.id}")

        return JsonResponse({
            'sucesso': True,
            'mensagem': 'Modelo 3D gerado com sucesso!',
            'metadados': metadados,
            'download_url': projeto.arquivo_3d.url if projeto.arquivo_3d else None
        })

    except Exception as e:
        logger.error(f"[Modelo 3D] Erro ao gerar modelo - Projeto {projeto.id}: {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'sucesso': False,
            'erro': f'Erro ao gerar modelo 3D: {str(e)}'
        })


@login_required
@require_http_methods(["GET"])
def modelo_3d_download(request, projeto_id):
    """
    Download do modelo 3D gerado
    """
    projeto = get_object_or_404(Projeto, id=projeto_id)

    if not projeto.arquivo_3d:
        return JsonResponse({
            'sucesso': False,
            'erro': 'Modelo 3D não encontrado. Gere o modelo primeiro.'
        }, status=404)

    # Retornar arquivo para download
    response = FileResponse(
        projeto.arquivo_3d.open('rb'),
        as_attachment=True,
        filename=f"stand_{projeto.nome.replace(' ', '_')}.obj"
    )
    return response


@login_required
@require_http_methods(["GET"])
def modelo_3d_download_mtl(request, projeto_id):
    """
    Download do arquivo de materiais (.mtl)
    """
    projeto = get_object_or_404(Projeto, id=projeto_id)

    if not projeto.planta_baixa_json:
        return JsonResponse({
            'sucesso': False,
            'erro': 'Planta baixa não encontrada.'
        }, status=404)

    # Gerar MTL
    exportador = Exportador3DService(projeto.planta_baixa_json)
    _, mtl_data, _ = exportador.gerar_modelo_3d()

    response = HttpResponse(mtl_data, content_type='text/plain')
    response['Content-Disposition'] = f'attachment; filename="stand_{projeto.nome.replace(" ", "_")}.mtl"'
    return response
