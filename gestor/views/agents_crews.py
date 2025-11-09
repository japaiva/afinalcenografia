from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import JsonResponse
from django.db.models import Q, Count, Max
from django.db import transaction
from django.views.decorators.http import require_POST
import json

from core.models import Agente, Crew, CrewMembro, CrewTask
from core.forms import AgenteForm, CrewForm, CrewMembroForm, CrewTaskForm
from projetos.models import Projeto # Assuming Projeto might be needed for agent-related stats later.
from core.decorators import gestor_required # Keep if agents/crews can only be managed by gestor
from core.models import CrewExecucao # Import the missing model

import os
from typing import Dict, Any, List, Optional
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

##############################
# CRUD AGENTE
##############################

@login_required
@gestor_required
def agente_list(request):
    """Lista de agentes com filtros e estatísticas"""
    # Filtros
    tipo_filtro = request.GET.get('tipo', '')
    status_filtro = request.GET.get('status', '')
    busca = request.GET.get('busca', '')
    
    agentes_list = Agente.objects.all().order_by('nome')
    
    # Aplicar filtros
    if tipo_filtro:
        agentes_list = agentes_list.filter(tipo=tipo_filtro)
    
    if status_filtro == 'ativo':
        agentes_list = agentes_list.filter(ativo=True)
    elif status_filtro == 'inativo':
        agentes_list = agentes_list.filter(ativo=False)
    
    if busca:
        agentes_list = agentes_list.filter(
            Q(nome__icontains=busca) | Q(descricao__icontains=busca)
        )
    
    # Paginação
    paginator = Paginator(agentes_list, 10)
    page = request.GET.get('page', 1)
    
    try:
        agentes = paginator.page(page)
    except PageNotAnInteger:
        agentes = paginator.page(1)
    except EmptyPage:
        agentes = paginator.page(paginator.num_pages)
    
    # Estatísticas
    stats = {
        'total': Agente.objects.count(),
        'ativos': Agente.objects.filter(ativo=True).count(),
        'individuais': Agente.objects.filter(tipo='individual').count(),
        'crew_members': Agente.objects.filter(tipo='crew_member').count(),
    }
    
    context = {
        'agentes': agentes,
        'stats': stats,
        'filtros': {
            'tipo': tipo_filtro,
            'status': status_filtro,
            'busca': busca,
        }
    }
    
    return render(request, 'gestor/agente_list.html', context)

@login_required
@gestor_required
def agente_create(request):
    """Criação de novo agente"""
    if request.method == 'POST':
        form = AgenteForm(request.POST)
        if form.is_valid():
            agente = form.save()
            messages.success(request, f'Agente "{agente.nome}" criado com sucesso.')
            return redirect('gestor:agente_list')
    else:
        form = AgenteForm()
    
    return render(request, 'gestor/agente_form.html', {'form': form})

@login_required
@gestor_required
def agente_update(request, pk):
    """Atualização de agente"""
    agente = get_object_or_404(Agente, pk=pk)
    
    if request.method == 'POST':
        form = AgenteForm(request.POST, instance=agente)
        if form.is_valid():
            agente = form.save()
            messages.success(request, f'Agente "{agente.nome}" atualizado com sucesso.')
            return redirect('gestor:agente_list')
    else:
        form = AgenteForm(instance=agente)
    
    context = {
        'form': form,
        'agente': agente
    }
    
    return render(request, 'gestor/agente_form.html', context)

@login_required
@gestor_required
def agente_delete(request, pk):
    """Exclusão de agente com verificações"""
    agente = get_object_or_404(Agente, pk=pk)
    
    # Verificar se agente está sendo usado em crews
    crews_vinculados = CrewMembro.objects.filter(agente=agente).count()
    
    if request.method == 'POST':
        confirm = request.POST.get('confirm_delete')
        if confirm == 'sim':
            try:
                nome_agente = agente.nome
                agente.delete()
                messages.success(request, f'Agente "{nome_agente}" excluído com sucesso.')
                return redirect('gestor:agente_list')
            except Exception as e:
                messages.error(request, f'Erro ao excluir agente: {str(e)}')
        else:
            messages.info(request, 'Exclusão cancelada.')
            return redirect('gestor:agente_list')
    
    context = {
        'agente': agente,
        'crews_vinculados': crews_vinculados,
        'pode_excluir': crews_vinculados == 0
    }
    
    return render(request, 'gestor/agente_confirm_delete.html', context)

##############################
# CRUD CREW
##############################

@login_required
@gestor_required
def crew_list(request):
    """Lista de crews com estatísticas"""
    crews_list = Crew.objects.annotate(
        num_agentes=Count('membros', distinct=True),
        num_tarefas=Count('tasks', distinct=True)  # ✅ Adicionei distinct=True
    ).order_by('nome')
    
    # Filtros
    status_filtro = request.GET.get('status', '')
    processo_filtro = request.GET.get('processo', '')
    
    if status_filtro == 'ativo':
        crews_list = crews_list.filter(ativo=True)
    elif status_filtro == 'inativo':
        crews_list = crews_list.filter(ativo=False)
        
    if processo_filtro:
        crews_list = crews_list.filter(processo=processo_filtro)
    
    # Paginação
    paginator = Paginator(crews_list, 10)
    page = request.GET.get('page', 1)
    
    try:
        crews = paginator.page(page)
    except PageNotAnInteger:
        crews = paginator.page(1)
    except EmptyPage:
        crews = paginator.page(paginator.num_pages)
    
    context = {
        'crews': crews,
        'total_crews': Crew.objects.count(),
        'crews_ativos': Crew.objects.filter(ativo=True).count(),
        'filtros': {
            'status': status_filtro,
            'processo': processo_filtro,
        }
    }
    
    return render(request, 'gestor/crew_list.html', context)

@login_required
@gestor_required
def crew_create(request):
    """Criação de novo crew - VERSÃO SIMPLIFICADA"""
    if request.method == 'POST':
        form = CrewForm(request.POST)
        
        if form.is_valid():
            try:
                with transaction.atomic():
                    # O próprio form.save() já cuida de criar os membros
                    crew = form.save()
                    
                    messages.success(request, f'Crew "{crew.nome}" criado com sucesso!')
                    return redirect('gestor:crew_detail', pk=crew.id)
                    
            except Exception as e:
                messages.error(request, f'Erro ao criar crew: {str(e)}')
        else:
            # Mostrar erros específicos
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = CrewForm()
    
    context = {
        'form': form,
        'agentes_disponiveis': Agente.objects.filter(tipo='crew_member', ativo=True)
    }
    
    return render(request, 'gestor/crew_form.html', context)

@login_required
@gestor_required
def crew_detail(request, pk):
    """Detalhes do crew com gestão de membros e tarefas"""
    crew = get_object_or_404(Crew, pk=pk)
    
    # Membros do crew ordenados por execução
    membros = CrewMembro.objects.filter(crew=crew).order_by('ordem_execucao')
    
    # Tarefas do crew ordenadas por execução
    tarefas = CrewTask.objects.filter(crew=crew).order_by('ordem_execucao')
    
    # Últimas execuções
    execucoes_recentes = crew.execucoes.all()[:5]
    
    context = {
        'crew': crew,
        'membros': membros,
        'tarefas': tarefas,
        'execucoes_recentes': execucoes_recentes,
        'total_membros': membros.count(),
        'total_tarefas': tarefas.count(),
    }
    
    return render(request, 'gestor/crew_detail.html', context)

@login_required
@gestor_required
def crew_update(request, pk):
    """Atualização de crew"""
    crew = get_object_or_404(Crew, pk=pk)
    
    if request.method == 'POST':
        form = CrewForm(request.POST, instance=crew)
        if form.is_valid():
            crew = form.save()
            messages.success(request, f'Crew "{crew.nome}" atualizado com sucesso.')
            return redirect('gestor:crew_detail', pk=crew.id)
    else:
        form = CrewForm(instance=crew)
    
    context = {
        'form': form,
        'crew': crew
    }
    
    return render(request, 'gestor/crew_form.html', context)

@login_required
@gestor_required
def crew_delete(request, pk):
    """Exclusão de crew"""
    crew = get_object_or_404(Crew, pk=pk)
    
    # Verificar se há execuções vinculadas
    execucoes_vinculadas = crew.execucoes.count()
    
    if request.method == 'POST':
        confirm = request.POST.get('confirm_delete')
        if confirm == 'sim':
            try:
                nome_crew = crew.nome
                crew.delete()
                messages.success(request, f'Crew "{nome_crew}" excluído com sucesso.')
                return redirect('gestor:crew_list')
            except Exception as e:
                messages.error(request, f'Erro ao excluir crew: {str(e)}')
        else:
            messages.info(request, 'Exclusão cancelada.')
            return redirect('gestor:crew_detail', pk=crew.id)
    
    context = {
        'crew': crew,
        'execucoes_vinculadas': execucoes_vinculadas,
        'pode_excluir': execucoes_vinculadas == 0
    }
    
    return render(request, 'gestor/crew_confirm_delete.html', context)

##############################
# GESTÃO DE MEMBROS DO CREW
##############################

@login_required
@gestor_required
def crew_add_member(request, crew_id):
    """Adicionar membro ao crew"""
    crew = get_object_or_404(Crew, pk=crew_id)
    
    if request.method == 'POST':
        form = CrewMembroForm(request.POST, crew=crew)
        if form.is_valid():
            membro = form.save(commit=False)
            membro.crew = crew
            membro.save()
            
            messages.success(request, f'Agente "{membro.agente.nome}" adicionado ao crew.')
            return redirect('gestor:crew_detail', pk=crew.id)
    else:
        form = CrewMembroForm(crew=crew)
    
    context = {
        'form': form,
        'crew': crew
    }
    
    return render(request, 'gestor/crew_member_form.html', context)

@login_required
@gestor_required
def crew_member_update(request, crew_id, membro_id):
    """Edita configurações de um membro específico do crew"""
    crew = get_object_or_404(Crew, pk=crew_id)
    membro = get_object_or_404(CrewMembro, pk=membro_id, crew=crew)
    
    if request.method == 'POST':
        print(f"POST data: {request.POST}")  # Debug
        form = CrewMembroForm(request.POST, instance=membro, crew=crew)
        
        if form.is_valid():
            print("Form is valid, saving...")  # Debug
            try:
                membro_salvo = form.save()
                return redirect('gestor:crew_detail', pk=crew_id)
            except Exception as e:
                print(f"Erro ao salvar: {e}")  # Debug
                messages.error(request, f'Erro ao salvar: {str(e)}')
        else:
            print(f"Form errors: {form.errors}")  # Debug
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = CrewMembroForm(instance=membro, crew=crew)
    
    context = {
        'crew': crew,
        'membro': membro,
        'form': form,
        'title': f'Editar Membro: {membro.agente.nome}'
    }
    
    return render(request, 'gestor/crew_member_update.html', context)

@login_required
@gestor_required
@require_POST
def crew_member_delete(request, crew_id, membro_id):
    """Remove um membro do crew"""
    crew = get_object_or_404(Crew, pk=crew_id)
    membro = get_object_or_404(CrewMembro, pk=membro_id, crew=crew)
    
    agente_nome = membro.agente.nome
    membro.delete()
    
    messages.success(request, f'Agente {agente_nome} removido do crew com sucesso!')
    return redirect('gestor:crew_detail', pk=crew_id)


@login_required
@gestor_required
@require_POST
def crew_member_reorder(request, crew_id):
    """Reordena membros do crew via AJAX"""
    crew = get_object_or_404(Crew, pk=crew_id)
    
    try:
        nova_ordem = json.loads(request.body)
        
        for item in nova_ordem:
            membro_id = item['id']
            nova_posicao = item['position']
            
            CrewMembro.objects.filter(
                id=membro_id, 
                crew=crew
            ).update(ordem_execucao=nova_posicao)
        
        return JsonResponse({'success': True})
        
    except Exception as e:
        return JsonResponse({
            'success': False, 
            'error': str(e)
        }, status=400)

##############################
# GESTÃO DE TASKS DO CREW
##############################

@login_required
@gestor_required
def crew_task_list(request, crew_id):
    """Lista detalhada das tasks do crew"""
    crew = get_object_or_404(Crew, pk=crew_id)
    tasks = crew.tasks.all().order_by('ordem_execucao')
    
    context = {
        'crew': crew,
        'tasks': tasks,
        'total_tasks': tasks.count(),
        'tasks_ativas': tasks.filter(ativo=True).count()
    }
    
    return render(request, 'gestor/crew_task_list.html', context)


@login_required
@gestor_required
def crew_task_create(request, crew_id):
    """Cria nova task para o crew - VERSÃO CORRIGIDA"""
    crew = get_object_or_404(Crew, pk=crew_id)
    
    if request.method == 'POST':
        form = CrewTaskForm(request.POST, crew=crew)
        if form.is_valid():
            task = form.save(commit=False)
            task.crew = crew
            task.save()
            
            # IMPORTANTE: Salvar dependências ManyToMany APÓS save()
            form.save_m2m()
            
            messages.success(request, f'Tarefa "{task.nome}" criada com sucesso!')
            return redirect('gestor:crew_detail', pk=crew_id)
        else:
            # Debug para ver erros
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = CrewTaskForm(crew=crew)
        
        # Auto-sugerir próxima ordem
        max_ordem = crew.tasks.aggregate(Max('ordem_execucao'))['ordem_execucao__max'] or 0
        form.initial['ordem_execucao'] = max_ordem + 1
        form.initial['ativo'] = True
    
    context = {
        'crew': crew,
        'form': form,
        'title': f'Criar Tarefa para {crew.nome}',
        'is_create': True
    }
    
    return render(request, 'gestor/crew_task_form.html', context)

@login_required
@gestor_required
def crew_task_update(request, crew_id, task_id):
    """Edita uma task existente - VERSÃO CORRIGIDA"""
    crew = get_object_or_404(Crew, pk=crew_id)
    task = get_object_or_404(CrewTask, pk=task_id, crew=crew)
    
    if request.method == 'POST':
        form = CrewTaskForm(request.POST, instance=task, crew=crew)
        if form.is_valid():
            task = form.save()
            # ManyToMany já é salvo automaticamente quando tem instance
            messages.success(request, f'Tarefa "{task.nome}" atualizada com sucesso!')
            return redirect('gestor:crew_detail', pk=crew_id)
        else:
            # Debug para ver erros
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = CrewTaskForm(instance=task, crew=crew)
    
    context = {
        'crew': crew,
        'task': task,
        'form': form,
        'title': f'Editar Tarefa: {task.nome}',
        'is_create': False
    }
    
    return render(request, 'gestor/crew_task_form.html', context)

@login_required
@gestor_required
@require_POST
def crew_task_delete(request, crew_id, task_id):
    """Exclui uma task"""
    crew = get_object_or_404(Crew, pk=crew_id)
    task = get_object_or_404(CrewTask, pk=task_id, crew=crew)
    
    task_nome = task.nome
    task.delete()
    
    return redirect('gestor:crew_detail', pk=crew_id)

@login_required
@gestor_required
@require_POST
def crew_task_duplicate(request, crew_id, task_id):
    """Duplica uma task existente"""
    crew = get_object_or_404(Crew, pk=crew_id)
    task_original = get_object_or_404(CrewTask, pk=task_id, crew=crew)
    
    try:
        # Determinar próxima ordem
        max_ordem = crew.tasks.aggregate(Max('ordem_execucao'))['ordem_execucao__max'] or 0
        
        # Criar cópia
        nova_task = CrewTask.objects.create(
            crew=crew,
            nome=f"{task_original.nome} (Cópia)",
            descricao=task_original.descricao,
            expected_output=task_original.expected_output,
            agente_responsavel=task_original.agente_responsavel,
            ordem_execucao=max_ordem + 1,
            async_execution=task_original.async_execution,
            ativo=False  # Criar inativa por padrão
        )
        
        return redirect('gestor:crew_task_update', crew_id=crew_id, task_id=nova_task.id)
        
    except Exception as e:
        messages.error(request, f'Erro ao duplicar tarefa: {str(e)}')
        return redirect('gestor:crew_detail', pk=crew_id)

@login_required
@gestor_required
@require_POST
def crew_task_reorder(request, crew_id):
    """Reordena tasks do crew via AJAX"""
    crew = get_object_or_404(Crew, pk=crew_id)
    
    try:
        nova_ordem = json.loads(request.body)
        
        for item in nova_ordem:
            task_id = item['id']
            nova_posicao = item['position']
            
            CrewTask.objects.filter(
                id=task_id, 
                crew=crew
            ).update(ordem_execucao=nova_posicao)
        
        return JsonResponse({'success': True})
        
    except Exception as e:
        return JsonResponse({
            'success': False, 
            'error': str(e)
        }, status=400)

##############################
# FUNÇÕES DE VALIDAÇÃO E TESTE DO CREW
##############################


# agents_crews.py - Função crew_validate CORRIGIDA

@login_required
@gestor_required
def crew_validate(request, pk):
    """Valida configuração do crew"""
    crew = get_object_or_404(Crew, pk=pk)
    
    problemas = []
    avisos = []
    
    # Validar membros ATIVOS
    membros = crew.membros.filter(ativo=True)
    if not membros.exists():
        problemas.append("Crew não possui membros ativos")
    
    # Validar tasks ATIVAS
    tasks = crew.tasks.filter(ativo=True)
    if not tasks.exists():
        problemas.append("Crew não possui tarefas ativas")
    
    # Validar ordem de execução dos MEMBROS
    ordens_membros = list(membros.values_list('ordem_execucao', flat=True))
    if len(set(ordens_membros)) != len(ordens_membros):
        problemas.append("Membros têm ordens de execução duplicadas")
    
    # Validar ordem de execução das TASKS
    ordens_tasks = list(tasks.values_list('ordem_execucao', flat=True))
    if len(set(ordens_tasks)) != len(ordens_tasks):
        problemas.append("Tasks têm ordens de execução duplicadas")
    
    # Validar agentes dos membros ativos
    for membro in membros:
        if not membro.agente.ativo:
            avisos.append(f"Agente {membro.agente.nome} está inativo")
        
        if not membro.agente.llm_model:
            problemas.append(f"Agente {membro.agente.nome} não tem modelo LLM configurado")
        
        if not membro.agente.llm_system_prompt:
            problemas.append(f"Agente {membro.agente.nome} não tem prompt do sistema configurado")
    
    # Validar responsáveis das tasks ativas
    for task in tasks:
        if task.agente_responsavel:
            # Verificar se o agente responsável está nos membros ativos do crew
            agentes_no_crew = [m.agente for m in membros]
            if task.agente_responsavel not in agentes_no_crew:
                problemas.append(f"Task '{task.nome}' atribuída a agente que não está no crew")
        else:
            problemas.append(f"Task '{task.nome}' não tem agente responsável")
    
    # Validar configuração hierárquica
    if crew.processo == 'hierarchical':
        if not crew.manager_llm_model:
            problemas.append("Processo hierárquico requer configuração do modelo LLM do manager")
        if not crew.manager_llm_provider:
            problemas.append("Processo hierárquico requer configuração do provedor LLM do manager")
    
    # Validar se há pelo menos uma sequência válida de execução
    if membros.exists() and tasks.exists():
        primeira_ordem_membro = min(ordens_membros) if ordens_membros else 1
        primeira_ordem_task = min(ordens_tasks) if ordens_tasks else 1
        
        if primeira_ordem_membro != 1:
            avisos.append("Ordem de execução dos membros não começa em 1")
        
        if primeira_ordem_task != 1:
            avisos.append("Ordem de execução das tasks não começa em 1")
    
    # Resposta JSON para AJAX
    if request.headers.get('Accept') == 'application/json':
        return JsonResponse({
            'valido': len(problemas) == 0,
            'problemas': problemas,
            'avisos': avisos,
            'total_membros': membros.count(),
            'total_tasks': tasks.count()
        })
    
    # Contexto para template
    context = {
        'crew': crew,
        'problemas': problemas,
        'avisos': avisos,
        'valido': len(problemas) == 0,
        'total_membros': membros.count(),  # ✅ Passa valor calculado
        'total_tasks': tasks.count(),      # ✅ Passa valor calculado
        
        # Dados extras para debug se necessário
        'total_membros_todos': crew.membros.count(),  # Incluindo inativos
        'total_tasks_todas': crew.tasks.count(),      # Incluindo inativas
    }
    
    return render(request, 'gestor/crew_validate.html', context)

@login_required
@gestor_required
def crew_toggle(request, pk):
    """Ativa/desativa um crew"""
    crew = get_object_or_404(Crew, pk=pk)
    crew.ativo = not crew.ativo
    crew.save()
    
    status_text = "ativado" if crew.ativo else "desativado"
    messages.success(request, f'Crew {crew.nome} {status_text} com sucesso.')
    
    return redirect('gestor:crew_list')

##############################
# API ENDPOINTS PARA AJAX (CrewAI related)
##############################

@login_required
def api_agentes_crew_members(request):
    """API: Lista agentes disponíveis para crews"""
    agentes = Agente.objects.filter(
        tipo='crew_member', 
        ativo=True
    ).values('id', 'nome', 'crew_role', 'llm_model')
    
    return JsonResponse({
        'success': True,
        'agentes': list(agentes)
    })

@login_required
def api_crew_stats(request):
    """API: Estatísticas dos crews"""
    stats = {
        'total_crews': Crew.objects.count(),
        'crews_ativos': Crew.objects.filter(ativo=True).count(),
        'total_agentes_crew': Agente.objects.filter(tipo='crew_member', ativo=True).count(),
        'crews_por_processo': {
            'sequential': Crew.objects.filter(processo='sequential').count(),
            'hierarchical': Crew.objects.filter(processo='hierarchical').count(),
        }
    }
    
    return JsonResponse({
        'success': True,
        'stats': stats
    })

##############################
# GESTÃO DE MEMBROS DO CREW
##############################

@login_required
@gestor_required
def crew_add_member(request, crew_id):
    """Adicionar membro ao crew"""
    crew = get_object_or_404(Crew, pk=crew_id)
    
    if request.method == 'POST':
        form = CrewMembroForm(request.POST, crew=crew)
        if form.is_valid():
            membro = form.save(commit=False)
            membro.crew = crew
            membro.save()
            
            messages.success(request, f'Agente "{membro.agente.nome}" adicionado ao crew.')
            return redirect('gestor:crew_detail', pk=crew.id)
    else:
        form = CrewMembroForm(crew=crew)
    
    context = {
        'form': form,
        'crew': crew
    }
    
    return render(request, 'gestor/crew_member_form.html', context)

@login_required
@gestor_required
def crew_member_update(request, crew_id, membro_id):
    """Edita configurações de um membro específico do crew"""
    crew = get_object_or_404(Crew, pk=crew_id)
    membro = get_object_or_404(CrewMembro, pk=membro_id, crew=crew)
    
    if request.method == 'POST':
        form = CrewMembroForm(request.POST, instance=membro, crew=crew)
        if form.is_valid():
            form.save()
            return redirect('gestor:crew_detail', pk=crew_id)
    else:
        form = CrewMembroForm(instance=membro, crew=crew)
    
    context = {
        'crew': crew,
        'membro': membro,
        'form': form,
        'title': f'Editar Membro: {membro.agente.nome}'
    }
    
    return render(request, 'gestor/crew_member_update.html', context)

@login_required
@gestor_required
@require_POST
def crew_member_delete(request, crew_id, membro_id):
    """Remove um membro do crew"""
    crew = get_object_or_404(Crew, pk=crew_id)
    membro = get_object_or_404(CrewMembro, pk=membro_id, crew=crew)
    
    agente_nome = membro.agente.nome
    membro.delete()
    
    messages.success(request, f'Agente {agente_nome} removido do crew com sucesso!')
    return redirect('gestor:crew_detail', pk=crew_id)

import tempfile
import requests
import os
from typing import Dict, Any, List, Optional

# Função run_agent COMPLETA e SIMPLIFICADA para agents_crews.py
# O AgenteService já faz todo o trabalho pesado!

def run_agent(nome_agente: str, payload: Dict[str, Any], imagens: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Executor central de agentes - versão simplificada
    O AgenteService já lida com downloads de URLs, conversão para base64, etc.
    """
    logger.info(f"[EXECUTOR] Iniciando execução do agente: {nome_agente}")
    logger.info(f"[EXECUTOR] Payload keys: {list(payload.keys())}")
    logger.info(f"[EXECUTOR] Imagens: {len(imagens) if imagens else 0} arquivos")
    
    try:
        # Buscar agente no banco (aceita tanto 'individual' quanto 'crew_member')
        agente = Agente.objects.get(nome=nome_agente, ativo=True)
        logger.info(f"[EXECUTOR] Agente encontrado: {agente.nome} (ID: {agente.id}, Tipo: {agente.tipo}, Modelo: {agente.llm_model})")
        
        # Importar o serviço de agentes
        from ..services.agente_executor import AgenteService
        
        # O prompt deve vir no payload ou ser construído usando task_instructions do agente
        if 'prompt' in payload and payload['prompt']:
            prompt_usuario = payload['prompt']
        else:
            # Usar task_instructions do agente como template
            prompt_usuario = _build_prompt_from_template(agente, payload)

        if not prompt_usuario:
            raise ValueError("Não foi possível gerar prompt para o agente")
        
        logger.info(f"[EXECUTOR] Prompt (primeiros 200 chars): {prompt_usuario[:200]}...")
        
        # Executar agente - SIMPLES ASSIM!
        service = AgenteService()
        
        # O AgenteService.executar_agente já aceita imagens como terceiro parâmetro
        # e faz todo o processamento (download de URLs, conversão base64, etc.)
        if imagens and len(imagens) > 0:
            logger.info(f"[EXECUTOR] Executando com {len(imagens)} imagens")
            # Log das URLs/paths para debug
            for i, img in enumerate(imagens, 1):
                logger.info(f"[EXECUTOR] Imagem {i}: {img[:100]}...")
            
            # Passar direto pro service - ele cuida de tudo!
            resposta = service.executar_agente(agente, prompt_usuario, imagens)
        else:
            logger.info("[EXECUTOR] Executando sem imagens")
            resposta = service.executar_agente(agente, prompt_usuario)
        
        logger.info(f"[EXECUTOR] Resposta recebida ({len(resposta) if resposta else 0} chars)")
        
        # Processar resposta
        resultado = _process_generic_response(resposta, payload, nome_agente)
        
        logger.info("[EXECUTOR] Execução concluída com sucesso")
        return resultado
        
    except Agente.DoesNotExist:
        logger.error(f"[EXECUTOR] Agente '{nome_agente}' não encontrado")
        raise ValueError(f"Agente '{nome_agente}' não encontrado no sistema")
        
    except Exception as e:
        logger.error(f"[EXECUTOR] Erro na execução: {str(e)}", exc_info=True)
        raise RuntimeError(f"Falha na execução do agente: {str(e)}")

def _build_prompt_from_template(agente: Agente, payload: Dict[str, Any]) -> str:
    """
    Constrói prompt usando as task_instructions do agente como template.
    Substitui placeholders {campo} pelos valores do payload.

    Args:
        agente: Instância do agente
        payload: Dados para substituir no template

    Returns:
        Prompt formatado com os dados do payload
    """
    logger.info("[EXECUTOR] Construindo prompt a partir do template do agente")

    # Usar task_instructions como base
    template = agente.task_instructions or ""

    if not template:
        logger.warning("[EXECUTOR] Agente sem task_instructions, usando prompt básico")
        return _build_fallback_prompt(payload)

    # Construir dados de entrada formatados
    prompt_final = template + "\n\n**DADOS DE ENTRADA:**\n\n"

    # Adicionar dados do payload de forma estruturada
    for key, value in payload.items():
        if key == 'prompt':
            continue  # Pular se já tem prompt

        if isinstance(value, dict):
            prompt_final += f"**{key.upper()}:**\n{json.dumps(value, indent=2, ensure_ascii=False)}\n\n"
        elif isinstance(value, (list, tuple)):
            prompt_final += f"**{key.upper()}:**\n{json.dumps(value, indent=2, ensure_ascii=False)}\n\n"
        else:
            prompt_final += f"**{key.upper()}:** {value}\n\n"

    logger.info(f"[EXECUTOR] Prompt construído: {len(prompt_final)} chars")
    return prompt_final


def _build_fallback_prompt(payload: Dict[str, Any]) -> str:
    """
    Fallback: constrói um prompt básico se não foi fornecido explicitamente.
    """
    logger.warning("[EXECUTOR] Usando prompt de fallback")

    # Prompt genérico baseado no payload
    prompt_parts = []

    if payload.get('projeto_id'):
        prompt_parts.append(f"Projeto ID: {payload['projeto_id']}")

    if payload.get('instrucoes'):
        prompt_parts.append(f"Instruções: {payload['instrucoes']}")

    if payload.get('dados'):
        prompt_parts.append(f"Dados para análise: {json.dumps(payload['dados'], indent=2)}")

    if not prompt_parts:
        # Último recurso
        prompt_parts.append(f"Processar dados: {json.dumps(payload, indent=2)}")

    return "\n\n".join(prompt_parts)


def _process_generic_response(resposta: str, payload: Dict[str, Any], nome_agente: str) -> Dict[str, Any]:
    """
    Processa a resposta do agente de forma genérica.
    Tenta extrair JSON, mas mantém resposta original se não conseguir.
    """
    
    try:
        # Tentar extrair JSON da resposta
        json_resposta = _extract_json_from_response(resposta)
        
        if json_resposta:
            # Adicionar metadados ao JSON extraído
            resultado = {
                **json_resposta,
                "_metadata": {
                    "processado_em": timezone.now().isoformat(),
                    "projeto_id": payload.get("projeto_id"),
                    "agente_executado": nome_agente,
                    "parsing_success": True,
                    "response_type": "json"
                }
            }
        else:
            # Se não conseguir extrair JSON, retornar estrutura com resposta crua
            resultado = {
                "resposta_texto": resposta,
                "_metadata": {
                    "processado_em": timezone.now().isoformat(),
                    "projeto_id": payload.get("projeto_id"),
                    "agente_executado": nome_agente,
                    "parsing_success": False,
                    "response_type": "text"
                }
            }
        
        return resultado
            
    except Exception as e:
        logger.error(f"[EXECUTOR] Erro ao processar resposta: {str(e)}")
        return {
            "erro_processamento": str(e),
            "resposta_original": resposta,
            "_metadata": {
                "processado_em": timezone.now().isoformat(),
                "projeto_id": payload.get("projeto_id"),
                "agente_executado": nome_agente,
                "parsing_success": False,
                "response_type": "error"
            }
        }


def _extract_json_from_response(resposta: str) -> Optional[Dict[str, Any]]:
    """Extrai JSON válido da resposta do agente usando várias estratégias"""
    
    if not resposta or not resposta.strip():
        return None
    
    # Estratégia 1: Parse direto
    try:
        return json.loads(resposta.strip())
    except:
        pass
    
    # Estratégia 2: JSON entre ```json e ```
    try:
        import re
        json_match = re.search(r'```json\s*\n?(.*?)\n?\s*```', resposta, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(1).strip())
    except:
        pass
    
    # Estratégia 3: JSON entre ``` e ``` (sem especificar linguagem)
    try:
        import re
        json_match = re.search(r'```\s*\n?(.*?)\n?\s*```', resposta, re.DOTALL)
        if json_match:
            content = json_match.group(1).strip()
            if content.startswith('{') or content.startswith('['):
                return json.loads(content)
    except:
        pass
    
    # Estratégia 4: Primeiro { até último }
    try:
        import re
        json_match = re.search(r'\{.*\}', resposta, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(0))
    except:
        pass
    
    # Estratégia 5: Primeiro [ até último ]
    try:
        import re
        json_match = re.search(r'\[.*\]', resposta, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(0))
    except:
        pass
    
    return None