# projetos/views/projeto_views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils import timezone

from core.decorators import cliente_required, gestor_required, projetista_required
from projetos.models.projeto import Projeto, ProjetoPlanta, ProjetoReferencia, ArquivoProjeto
from projetos.forms.projeto import ProjetoForm

import logging
import os

# Configurar logger
logger = logging.getLogger(__name__)

# Views relacionadas ao gerenciamento de projetos

@login_required
@cliente_required
def projeto_list(request):
    """Lista todos os projetos do cliente"""
    empresa = request.user.empresa
    projetos = Projeto.objects.filter(empresa=empresa).order_by('-created_at')
    
    context = {
        'projetos': projetos
    }
    return render(request, 'cliente/projeto_list.html', context)

@login_required
@cliente_required
def projeto_detail(request, pk):
    """Detalhe de um projeto específico"""
    projeto = get_object_or_404(Projeto, pk=pk, empresa=request.user.empresa)
    
    context = {
        'projeto': projeto,
        'referencias': ProjetoReferencia.objects.filter(projeto=projeto),
        'plantas': ProjetoPlanta.objects.filter(projeto=projeto),
        'arquivos': ArquivoProjeto.objects.filter(projeto=projeto)
    }
    return render(request, 'cliente/projeto_detail.html', context)



# cliente/views/projeto.py
# CORREÇÃO para a view projeto_create

@login_required
def projeto_create(request):
    """
    View para criar um novo projeto - VERSÃO CORRIGIDA
    """
    empresa = request.user.empresa

    if request.method == 'POST':
        # CORREÇÃO: Passa a empresa para o formulário
        form = ProjetoForm(request.POST, empresa=empresa)
        if form.is_valid():
            projeto = form.save(commit=False)
            
            # CORREÇÃO: Definir criado_por (empresa já foi definida no formulário)
            projeto.criado_por = request.user

            # Salvar o projeto (status já definido no método save do formulário)
            projeto.save()

            # Cria um marco para registrar a criação do projeto
            ProjetoMarco.objects.create(
                projeto=projeto,
                tipo='criacao_projeto',
                observacao='Projeto criado pelo cliente',
                registrado_por=request.user
            )

            messages.success(request, 'Projeto criado com sucesso!')

            # Mensagem específica baseada no status final
            if projeto.tipo_projeto == 'feira_negocios' and not projeto.feira:
                messages.warning(request, 'Você não selecionou uma feira. Por favor, envie o manual do expositor da feira pelo sistema de mensagens.')

            return redirect('cliente:projeto_detail', pk=projeto.id)

    else:
        # CORREÇÃO: Passa a empresa para o formulário também no GET
        form = ProjetoForm(
            initial={'tipo_projeto': 'feira_negocios'},
            empresa=empresa
        )

    return render(request, 'cliente/projeto_form.html', {
        'empresa': empresa,
        'form': form,
    })

@login_required
@cliente_required
def projeto_update(request, pk):
    """Atualização de projeto existente"""
    projeto = get_object_or_404(Projeto, pk=pk, empresa=request.user.empresa)
    
    if request.method == 'POST':
        form = ProjetoForm(request.POST, instance=projeto)
        if form.is_valid():
            form.save()
            messages.success(request, 'Projeto atualizado com sucesso!')
            return redirect('cliente:projeto_detail', pk=projeto.id)
    else:
        form = ProjetoForm(instance=projeto)
    
    context = {
        'form': form,
        'projeto': projeto
    }
    return render(request, 'cliente/projeto_form.html', context)

@login_required
@cliente_required
@require_POST
def projeto_upload_arquivo(request, pk):
    """Upload de arquivos para o projeto"""
    projeto = get_object_or_404(Projeto, pk=pk, empresa=request.user.empresa)
    
    if 'arquivo' in request.FILES:
        arquivo = request.FILES['arquivo']
        tipo = request.POST.get('tipo', 'referencia')
        
        # Decidir qual modelo usar com base no tipo
        if tipo == 'planta':
            obj = ProjetoPlanta(
                projeto=projeto,
                nome=arquivo.name,
                arquivo=arquivo,
                tipo=request.POST.get('subtipo', 'localizacao')
            )
        elif tipo == 'referencia':
            obj = ProjetoReferencia(
                projeto=projeto,
                nome=arquivo.name,
                arquivo=arquivo,
                tipo=request.POST.get('subtipo', 'estilo_visual')
            )
        else:
            obj = ArquivoProjeto(
                projeto=projeto,
                nome_original=arquivo.name,
                arquivo=arquivo
            )
        
        obj.save()
        
        return JsonResponse({
            'success': True,
            'arquivo_id': obj.id,
            'arquivo_nome': obj.nome if hasattr(obj, 'nome') else obj.nome_original,
            'arquivo_url': obj.arquivo.url,
            'arquivo_tipo': tipo
        })
    
    return JsonResponse({'error': 'Nenhum arquivo enviado'}, status=400)

@login_required
@cliente_required
@require_POST
def projeto_delete_arquivo(request, pk, arquivo_id, tipo):
    """Exclusão de arquivos do projeto"""
    projeto = get_object_or_404(Projeto, pk=pk, empresa=request.user.empresa)
    
    try:
        if tipo == 'planta':
            obj = get_object_or_404(ProjetoPlanta, id=arquivo_id, projeto=projeto)
        elif tipo == 'referencia':
            obj = get_object_or_404(ProjetoReferencia, id=arquivo_id, projeto=projeto)
        else:
            obj = get_object_or_404(ArquivoProjeto, id=arquivo_id, projeto=projeto)
        
        obj.delete()
        
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

# Visões para gestores e projetistas

@login_required
@gestor_required
def gestor_projeto_list(request):
    """Lista todos os projetos para o gestor"""
    empresa = request.user.empresa
    projetos = Projeto.objects.filter(empresa=empresa).order_by('-created_at')
    
    context = {
        'projetos': projetos
    }
    return render(request, 'gestor/projeto_list.html', context)

@login_required
@projetista_required
def projetista_projeto_list(request):
    """Lista de projetos para o projetista"""
    # Mostrar apenas projetos com briefing enviado
    projetos = Projeto.objects.filter(
        empresa=request.user.empresa,
        status__in=['briefing_enviado', 'projeto_em_desenvolvimento', 'projeto_enviado', 'projeto_em_analise']
    ).order_by('-updated_at')
    
    context = {
        'projetos': projetos
    }
    return render(request, 'projetista/projeto_list.html', context)