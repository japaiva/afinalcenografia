from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from projetos.models import Projeto, Briefing
from projetista.models import ConceitoVisual, ImagemConceitoVisual
from projetista.forms import ConceitoVisualForm, ImagemConceitoForm

import logging
logger = logging.getLogger(__name__)

@login_required
def gerar_conceito(request, projeto_id):
    """
    Página inicial para geração de conceito visual
    """
    projeto = get_object_or_404(Projeto, pk=projeto_id, projetista=request.user)
    
    # Obter o briefing mais recente
    try:
        briefing = projeto.briefings.latest('versao')
    except Briefing.DoesNotExist:
        messages.error(request, "Não foi encontrado um briefing para este projeto.")
        return redirect('projetista:projeto_detail', pk=projeto_id)
    
    # Verificar se já existe um conceito
    conceito = ConceitoVisual.objects.filter(
        projeto=projeto
    ).order_by('-criado_em').first()
    
    # Formulário para criação manual
    form = ConceitoVisualForm(instance=conceito) if conceito else ConceitoVisualForm()
    
    if request.method == 'POST':
        # Processar criação manual
        form = ConceitoVisualForm(request.POST, instance=conceito)
        if form.is_valid():
            conceito = form.save(commit=False)
            conceito.projeto = projeto
            conceito.briefing = briefing
            conceito.projetista = request.user
            conceito.save()
            
            messages.success(request, 'Conceito visual salvo com sucesso!')
            return redirect('projetista:conceito_detalhes', conceito_id=conceito.id)
    
    context = {
        'projeto': projeto,
        'briefing': briefing,
        'conceito': conceito,
        'form': form,
    }
    
    return render(request, 'projetista/gerar_conceito.html', context)

@login_required
def conceito_detalhes(request, conceito_id):
    """
    Página de detalhes do conceito visual
    """
    conceito = get_object_or_404(ConceitoVisual, pk=conceito_id)
    projeto = conceito.projeto
    
    # Verificar permissão
    if projeto.projetista != request.user:
        messages.error(request, 'Você não tem permissão para acessar este conceito.')
        return redirect('projetista:projeto_list')
    
    # Formulário para upload de imagens
    form_imagem = ImagemConceitoForm()
    
    # Agrupar imagens por categoria
    imagens_por_categoria = {}
    for angulo, nome in ImagemConceitoVisual.ANGULOS_CHOICES:
        imagens_por_categoria[angulo] = conceito.imagens.filter(angulo_vista=angulo)
    
    # Calcular o total de imagens
    total_imagens = conceito.imagens.count()
    
    context = {
        'conceito': conceito,
        'projeto': projeto,
        'form_imagem': form_imagem,
        'imagens_por_categoria': imagens_por_categoria,
        'total_imagens': total_imagens,
    }
    
    return render(request, 'projetista/conceito_detalhes.html', context)

@login_required
@require_POST
def upload_imagem(request, conceito_id):
    """
    Upload de imagem para o conceito
    """
    conceito = get_object_or_404(ConceitoVisual, pk=conceito_id)
    
    # Verificar permissão
    if conceito.projeto.projetista != request.user:
        return JsonResponse({
            'status': 'error',
            'message': 'Permissão negada'
        }, status=403)
    
    form = ImagemConceitoForm(request.POST, request.FILES)
    if form.is_valid():
        imagem = form.save(commit=False)
        imagem.conceito = conceito
        imagem.ordem = conceito.imagens.count() + 1
        imagem.save()
        
        return JsonResponse({
            'status': 'success',
            'message': 'Imagem adicionada com sucesso',
            'id': imagem.id,
            'url': imagem.imagem.url
        })
    
    return JsonResponse({
        'status': 'error',
        'message': 'Formulário inválido',
        'errors': form.errors
    }, status=400)

@login_required
def excluir_imagem(request, imagem_id):
    """
    Excluir imagem do conceito
    """
    imagem = get_object_or_404(ImagemConceitoVisual, pk=imagem_id)
    conceito = imagem.conceito
    
    # Verificar permissão
    if conceito.projeto.projetista != request.user:
        messages.error(request, 'Permissão negada.')
        return redirect('projetista:projeto_list')
    
    if request.method == 'POST':
        imagem.delete()
        messages.success(request, 'Imagem excluída com sucesso.')
    
    return redirect('projetista:conceito_detalhes', conceito_id=conceito.id)
