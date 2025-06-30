from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.urls import reverse_lazy
from django.db.models import Q

from core.models import Usuario, Parametro, Empresa, ParametroIndexacao, Agente, Crew
from core.forms import (UsuarioForm, ParametroForm, EmpresaForm, ParametroIndexacaoForm)
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
# CRUD EMPRESA
##############################

@login_required
@gestor_required
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
@gestor_required
def empresa_create(request):
    if request.method == 'POST':
        form = EmpresaForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Empresa criada com sucesso.')
            return redirect('gestor:empresa_list')
    else:
        form = EmpresaForm()
    return render(request, 'gestor/empresa_form.html', {'form': form})

@login_required
@gestor_required
def empresa_update(request, pk):
    empresa = get_object_or_404(Empresa, pk=pk)
    if request.method == 'POST':
        form = EmpresaForm(request.POST, request.FILES, instance=empresa)
        if form.is_valid():
            form.save()
            messages.success(request, 'Empresa atualizada com sucesso.')
            return redirect('gestor:empresa_list')
    else:
        form = EmpresaForm(instance=empresa)
    return render(request, 'gestor/empresa_form.html', {'form': form})

@login_required
@gestor_required
def empresa_toggle_status(request, pk):
    empresa = get_object_or_404(Empresa, pk=pk)
    empresa.ativa = not empresa.ativa
    empresa.save()
    
    status_text = "ativada" if empresa.ativa else "desativada"
    messages.success(request, f'Empresa {empresa.nome} {status_text} com sucesso.')
    
    return redirect('gestor:empresa_list')

@login_required
@gestor_required
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
# CRUD USUARIO
##############################

@login_required
@gestor_required
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
@gestor_required
def usuario_create(request):
    if request.method == 'POST':
        form = UsuarioForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Usuário criado com sucesso.')
            return redirect('gestor:usuario_list')
    else:
        form = UsuarioForm()
    return render(request, 'gestor/usuario_form.html', {'form': form})

@login_required
@gestor_required
def usuario_update(request, pk):
    usuario = get_object_or_404(Usuario, pk=pk)
    if request.method == 'POST':
        form = UsuarioForm(request.POST, request.FILES, instance=usuario)
        if form.is_valid():
            form.save()
            messages.success(request, 'Usuário atualizado com sucesso.')
            return redirect('gestor:usuario_list')
    else:
        form = UsuarioForm(instance=usuario)
    return render(request, 'gestor/usuario_form.html', {'form': form})

@login_required
@gestor_required
def usuario_toggle_status(request, pk):
    usuario = get_object_or_404(Usuario, pk=pk)
    usuario.is_active = not usuario.is_active
    usuario.save()
    
    status_text = "ativado" if usuario.is_active else "desativado"
    messages.success(request, f'Usuário {usuario.username} {status_text} com sucesso.')
    
    return redirect('gestor:usuario_list')

@login_required
@gestor_required
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
# CRUD PARAMETRO
##############################

@login_required
@gestor_required
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
@gestor_required
def parametro_create(request):
    if request.method == 'POST':
        form = ParametroForm(request.POST)
        if form.is_valid():
            parametro = form.save()
            messages.success(request, 'Parâmetro criado com sucesso.')
            return redirect('gestor:parametro_list')
    else:
        form = ParametroForm()
    return render(request, 'gestor/parametro_form.html', {'form': form})

@login_required
@gestor_required
def parametro_update(request, pk):
    parametro = get_object_or_404(Parametro, pk=pk)
    if request.method == 'POST':
        form = ParametroForm(request.POST, instance=parametro)
        if form.is_valid():
            parametro = form.save()
            messages.success(request, 'Parâmetro atualizado com sucesso.')
            return redirect('gestor:parametro_list')
    else:
        form = ParametroForm(instance=parametro)
    return render(request, 'gestor/parametro_form.html', {'form': form})

@login_required
@gestor_required
def parametro_delete(request, pk):
    parametro = get_object_or_404(Parametro, pk=pk)
    if request.method == 'POST':
        parametro.delete()
        messages.success(request, 'Parâmetro excluído com sucesso.')
        return redirect('gestor:parametro_list')
    return render(request, 'gestor/parametro_confirm_delete.html', {'parametro': parametro})

##############################
# PARAMETRO INDEXACAO
##############################

@login_required
@gestor_required
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
@gestor_required
def parametro_indexacao_create(request):
    if request.method == 'POST':
        form = ParametroIndexacaoForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Parâmetro de indexação criado com sucesso.')
            return redirect('gestor:parametro_indexacao_list')
    else:
        form = ParametroIndexacaoForm()
    
    return render(request, 'gestor/parametro_indexacao_form.html', {'form': form})

@login_required
@gestor_required
def parametro_indexacao_update(request, pk):
    parametro = get_object_or_404(ParametroIndexacao, pk=pk)
    
    if request.method == 'POST':
        form = ParametroIndexacaoForm(request.POST, instance=parametro)
        if form.is_valid():
            form.save()
            messages.success(request, 'Parâmetro de indexação atualizado com sucesso.')
            return redirect('gestor:parametro_indexacao_list')
    else:
        form = ParametroIndexacaoForm(instance=parametro)
    
    return render(request, 'gestor/parametro_indexacao_form.html', {'form': form})

@login_required
@gestor_required
def parametro_indexacao_delete(request, pk):
    parametro = get_object_or_404(ParametroIndexacao, pk=pk)
    
    if request.method == 'POST':
        parametro.delete()
        messages.success(request, 'Parâmetro de indexação excluído com sucesso.')
        return redirect('gestor:parametro_indexacao_list')
    
    return render(request, 'gestor/parametro_indexacao_confirm_delete.html', {'parametro': parametro})