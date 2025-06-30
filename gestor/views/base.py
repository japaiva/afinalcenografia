# gestor/views/base.py - VIEWS ATUALIZADAS PARA CREWAI

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import JsonResponse
from django.urls import reverse_lazy
from django.db.models import Q, Count
from django.db import transaction

from core.models import Usuario, Parametro, Empresa, ParametroIndexacao, Agente, Crew, CrewMembro, CrewTask
from core.forms import (UsuarioForm, ParametroForm, EmpresaForm, ParametroIndexacaoForm, 
                       AgenteForm, CrewForm, CrewMembroForm, CrewTaskForm)
from core.decorators import gestor_required
from projetos.models import Projeto

##############################
# MAIN
##############################

@login_required
@gestor_required
def dashboard(request):
    print("Usuário acessando o dashboard:", request.user)
    
    context = {
        'total_empresas': Empresa.objects.filter(ativa=True).count(),
        'total_usuarios': Usuario.objects.filter(is_active=True).count(),
        'total_projetos': Projeto.objects.all().count(),
        'total_agentes': Agente.objects.filter(ativo=True).count(),
        'total_crews': Crew.objects.filter(ativo=True).count(),
        'agentes_individuais': Agente.objects.filter(tipo='individual', ativo=True).count(),
        'agentes_crew': Agente.objects.filter(tipo='crew_member', ativo=True).count(),
    }
    return render(request, 'gestor/dashboard.html', context)

class GestorLoginView(LoginView):
    template_name = 'gestor/login.html'
    
    def form_valid(self, form):
        print("Login bem-sucedido para:", form.get_user())
        return super().form_valid(form)
    
    def get_success_url(self):
        print("Redirecionando para:", reverse_lazy('gestor:dashboard'))
        return reverse_lazy('gestor:dashboard')
 
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['app_name'] = 'Portal do Gestor'
        return context

def home(request):
    return render(request, 'gestor/home.html')

##############################
# CRUD EMPRESA (mantido igual)
##############################

@login_required
def empresa_list(request):
    empresas_list = Empresa.objects.all().order_by('nome')
    paginator = Paginator(empresas_list, 10)
    page = request.GET.get('page', 1)
    
    try:
        empresas = paginator.page(page)
    except PageNotAnInteger:
        empresas = paginator.page(1)
    except EmptyPage:
        empresas = paginator.page(paginator.num_pages)
    
    return render(request, 'gestor/empresa_list.html', {'empresas': empresas})

@login_required
def empresa_create(request):
    if request.method == 'POST':
        form = EmpresaForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Empresa criada com sucesso.')
            storage = messages.get_messages(request)
            storage.used = True
            return redirect('gestor:empresa_list')
    else:
        form = EmpresaForm()
    return render(request, 'gestor/empresa_form.html', {'form': form})

@login_required
def empresa_update(request, pk):
    empresa = get_object_or_404(Empresa, pk=pk)
    if request.method == 'POST':
        form = EmpresaForm(request.POST, request.FILES, instance=empresa)
        if form.is_valid():
            form.save()
            messages.success(request, 'Empresa atualizada com sucesso.')
            storage = messages.get_messages(request)
            storage.used = True
            return redirect('gestor:empresa_list')
    else:
        form = EmpresaForm(instance=empresa)
    return render(request, 'gestor/empresa_form.html', {'form': form})

@login_required
def empresa_toggle_status(request, pk):
    empresa = get_object_or_404(Empresa, pk=pk)
    empresa.ativa = not empresa.ativa
    empresa.save()
    
    status_text = "ativada" if empresa.ativa else "desativada"
    messages.success(request, f'Empresa {empresa.nome} {status_text} com sucesso.')
    
    return redirect('gestor:empresa_list')

@login_required
def empresa_delete(request, pk):
    empresa = get_object_or_404(Empresa, pk=pk)
    usuarios_vinculados = Usuario.objects.filter(empresa=empresa).count()
    
    if request.method == 'POST':
        confirm = request.POST.get('confirm_delete')
        if confirm == 'sim':
            try:
                nome_empresa = empresa.nome
                empresa.delete()
                messages.success(request, f'Empresa "{nome_empresa}" excluída com sucesso.')
                storage = messages.get_messages(request)
                storage.used = True
                return redirect('gestor:empresa_list')
            except Exception as e:
                messages.error(request, f'Erro ao excluir empresa: {str(e)}')
        else:
            messages.info(request, 'Exclusão cancelada.')
            return redirect('gestor:empresa_list')
    
    context = {
        'empresa': empresa,
        'usuarios_vinculados': usuarios_vinculados,
        'pode_excluir': usuarios_vinculados == 0
    }
    return render(request, 'gestor/empresa_confirm_delete.html', context)

##############################
# CRUD USUARIO (mantido igual)
##############################

@login_required
def usuario_list(request):
    usuarios_list = Usuario.objects.all().order_by('username')
    paginator = Paginator(usuarios_list, 10)
    page = request.GET.get('page', 1)
    
    try:
        usuarios = paginator.page(page)
    except PageNotAnInteger:
        usuarios = paginator.page(1)
    except EmptyPage:
        usuarios = paginator.page(paginator.num_pages)
    
    return render(request, 'gestor/usuario_list.html', {'usuarios': usuarios})

@login_required
def usuario_create(request):
    if request.method == 'POST':
        form = UsuarioForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Usuário criado com sucesso.')
            storage = messages.get_messages(request)
            storage.used = True
            return redirect('gestor:usuario_list')
    else:
        form = UsuarioForm()
    return render(request, 'gestor/usuario_form.html', {'form': form})

@login_required
def usuario_update(request, pk):
    usuario = get_object_or_404(Usuario, pk=pk)
    if request.method == 'POST':
        form = UsuarioForm(request.POST, request.FILES, instance=usuario)
        if form.is_valid():
            form.save()
            messages.success(request, 'Usuário atualizado com sucesso.')
            storage = messages.get_messages(request)
            storage.used = True
            return redirect('gestor:usuario_list')
    else:
        form = UsuarioForm(instance=usuario)
    return render(request, 'gestor/usuario_form.html', {'form': form})

@login_required
def usuario_toggle_status(request, pk):
    usuario = get_object_or_404(Usuario, pk=pk)
    usuario.is_active = not usuario.is_active
    usuario.save()
    
    status_text = "ativado" if usuario.is_active else "desativado"
    messages.success(request, f'Usuário {usuario.username} {status_text} com sucesso.')
    
    return redirect('gestor:usuario_list')

@login_required
def usuario_delete(request, pk):
    usuario = get_object_or_404(Usuario, pk=pk)
    
    if usuario == request.user:
        messages.error(request, 'Você não pode excluir sua própria conta.')
        return redirect('gestor:usuario_list')
    
    try:
        from projetos.models import Projeto
        projetos_vinculados = Projeto.objects.filter(
            Q(criado_por=usuario) | Q(projetista=usuario)
        ).count()
    except ImportError:
        projetos_vinculados = 0
    
    if request.method == 'POST':
        confirm = request.POST.get('confirm_delete')
        if confirm == 'sim':
            try:
                username = usuario.username
                usuario.delete()
                messages.success(request, f'Usuário "{username}" excluído com sucesso.')
                storage = messages.get_messages(request)
                storage.used = True
                return redirect('gestor:usuario_list')
            except Exception as e:
                messages.error(request, f'Erro ao excluir usuário: {str(e)}')
        else:
            messages.info(request, 'Exclusão cancelada.')
            return redirect('gestor:usuario_list')
    
    context = {
        'usuario': usuario,
        'projetos_vinculados': projetos_vinculados,
        'pode_excluir': projetos_vinculados == 0,
        'is_own_account': usuario == request.user
    }
    return render(request, 'gestor/usuario_confirm_delete.html', context)

##############################
# CRUD PARAMETRO (mantido igual)
##############################

@login_required
def parametro_list(request):
    parametros_list = Parametro.objects.all().order_by('parametro')
    paginator = Paginator(parametros_list, 10)
    page = request.GET.get('page', 1)
    
    try:
        parametros = paginator.page(page)
    except PageNotAnInteger:
        parametros = paginator.page(1)
    except EmptyPage:
        parametros = paginator.page(paginator.num_pages)
    
    return render(request, 'gestor/parametro_list.html', {'parametros': parametros})

@login_required
def parametro_create(request):
    if request.method == 'POST':
        form = ParametroForm(request.POST)
        if form.is_valid():
            parametro = form.save()
            messages.success(request, 'Parâmetro criado com sucesso.')
            storage = messages.get_messages(request)
            storage.used = True
            return redirect('gestor:parametro_list')
    else:
        form = ParametroForm()
    return render(request, 'gestor/parametro_form.html', {'form': form})

@login_required
def parametro_update(request, pk):
    parametro = get_object_or_404(Parametro, pk=pk)
    if request.method == 'POST':
        form = ParametroForm(request.POST, instance=parametro)
        if form.is_valid():
            parametro = form.save()
            messages.success(request, 'Parâmetro atualizado com sucesso.')
            storage = messages.get_messages(request)
            storage.used = True
            return redirect('gestor:parametro_list')
    else:
        form = ParametroForm(instance=parametro)
    return render(request, 'gestor/parametro_form.html', {'form': form})

@login_required
def parametro_delete(request, pk):
    parametro = get_object_or_404(Parametro, pk=pk)
    if request.method == 'POST':
        parametro.delete()
        messages.success(request, 'Parâmetro excluído com sucesso.')
        storage = messages.get_messages(request)
        storage.used = True
        return redirect('gestor:parametro_list')
    return render(request, 'gestor/parametro_confirm_delete.html', {'parametro': parametro})

##############################
# CRUD AGENTE ATUALIZADO
##############################

@login_required
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
def agente_create(request):
    """Criação de novo agente"""
    if request.method == 'POST':
        form = AgenteForm(request.POST)
        if form.is_valid():
            agente = form.save()
            messages.success(request, f'Agente "{agente.nome}" criado com sucesso.')
            storage = messages.get_messages(request)
            storage.used = True
            return redirect('gestor:agente_list')
    else:
        form = AgenteForm()
    
    return render(request, 'gestor/agente_form.html', {'form': form})

@login_required
def agente_update(request, pk):
    """Atualização de agente"""
    agente = get_object_or_404(Agente, pk=pk)
    
    if request.method == 'POST':
        form = AgenteForm(request.POST, instance=agente)
        if form.is_valid():
            agente = form.save()
            messages.success(request, f'Agente "{agente.nome}" atualizado com sucesso.')
            storage = messages.get_messages(request)
            storage.used = True
            return redirect('gestor:agente_list')
    else:
        form = AgenteForm(instance=agente)
    
    context = {
        'form': form,
        'agente': agente
    }
    
    return render(request, 'gestor/agente_form.html', context)

@login_required
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
                storage = messages.get_messages(request)
                storage.used = True
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
def crew_list(request):
    """Lista de crews com estatísticas"""
    crews_list = Crew.objects.annotate(
        num_agentes=Count('membros'),
        num_tarefas=Count('tasks')
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
def crew_create(request):
    """Criação de novo crew - VERSÃO SIMPLIFICADA"""
    if request.method == 'POST':
        form = CrewForm(request.POST)
        
        print(f"POST Data: {request.POST}")
        print(f"Form válido: {form.is_valid()}")
        
        if form.errors:
            print(f"Erros do form: {form.errors}")
        
        if form.is_valid():
            try:
                with transaction.atomic():
                    # O próprio form.save() já cuida de criar os membros
                    crew = form.save()
                    
                    messages.success(request, f'Crew "{crew.nome}" criado com sucesso!')
                    return redirect('gestor:crew_detail', pk=crew.id)
                    
            except Exception as e:
                print(f"Erro na criação: {str(e)}")
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
def crew_update(request, pk):
    """Atualização de crew"""
    crew = get_object_or_404(Crew, pk=pk)
    
    if request.method == 'POST':
        form = CrewForm(request.POST, instance=crew)
        if form.is_valid():
            crew = form.save()
            messages.success(request, f'Crew "{crew.nome}" atualizado com sucesso.')
            storage = messages.get_messages(request)
            storage.used = True
            return redirect('gestor:crew_detail', pk=crew.id)
    else:
        form = CrewForm(instance=crew)
    
    context = {
        'form': form,
        'crew': crew
    }
    
    return render(request, 'gestor/crew_form.html', context)

@login_required
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
                storage = messages.get_messages(request)
                storage.used = True
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
            storage = messages.get_messages(request)
            storage.used = True
            return redirect('gestor:crew_detail', pk=crew.id)
    else:
        form = CrewMembroForm(crew=crew)
    
    context = {
        'form': form,
        'crew': crew
    }
    
    return render(request, 'gestor/crew_member_form.html', context)

@login_required
def crew_remove_member(request, crew_id, member_id):
    """Remover membro do crew"""
    crew = get_object_or_404(Crew, pk=crew_id)
    membro = get_object_or_404(CrewMembro, pk=member_id, crew=crew)
    
    if request.method == 'POST':
        agente_nome = membro.agente.nome
        membro.delete()
        messages.success(request, f'Agente "{agente_nome}" removido do crew.')
        storage = messages.get_messages(request)
        storage.used = True
    
    return redirect('gestor:crew_detail', pk=crew.id)

##############################
# API ENDPOINTS PARA AJAX
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
# PARAMETRO INDEXACAO (mantido igual)
##############################

@login_required
def parametro_indexacao_list(request):
    parametros_list = ParametroIndexacao.objects.all().order_by('categoria', 'nome')
    
    categoria = request.GET.get('categoria')
    if categoria:
        parametros_list = parametros_list.filter(categoria=categoria)
    
    paginator = Paginator(parametros_list, 10)
    page = request.GET.get('page', 1)
    
    try:
        parametros = paginator.page(page)
    except PageNotAnInteger:
        parametros = paginator.page(1)
    except EmptyPage:
        parametros = paginator.page(paginator.num_pages)
    
    context = {
        'parametros': parametros,
        'categorias': dict(ParametroIndexacao._meta.get_field('categoria').choices),
        'categoria_filtro': categoria,
    }
    
    return render(request, 'gestor/parametro_indexacao_list.html', context)

@login_required
def parametro_indexacao_create(request):
    if request.method == 'POST':
        form = ParametroIndexacaoForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Parâmetro de indexação criado com sucesso.')
            storage = messages.get_messages(request)
            storage.used = True
            return redirect('gestor:parametro_indexacao_list')
    else:
        form = ParametroIndexacaoForm()
    
    return render(request, 'gestor/parametro_indexacao_form.html', {'form': form})

@login_required
def parametro_indexacao_update(request, pk):
    parametro = get_object_or_404(ParametroIndexacao, pk=pk)
    
    if request.method == 'POST':
        form = ParametroIndexacaoForm(request.POST, instance=parametro)
        if form.is_valid():
            form.save()
            messages.success(request, 'Parâmetro de indexação atualizado com sucesso.')
            storage = messages.get_messages(request)
            storage.used = True
            return redirect('gestor:parametro_indexacao_list')
    else:
        form = ParametroIndexacaoForm(instance=parametro)
    
    return render(request, 'gestor/parametro_indexacao_form.html', {'form': form})

@login_required
def parametro_indexacao_delete(request, pk):
    parametro = get_object_or_404(ParametroIndexacao, pk=pk)
    
    if request.method == 'POST':
        parametro.delete()
        messages.success(request, 'Parâmetro de indexação excluído com sucesso.')
        storage = messages.get_messages(request)
        storage.used = True
        return redirect('gestor:parametro_indexacao_list')
    
    return render(request, 'gestor/parametro_indexacao_confirm_delete.html', {'parametro': parametro})