from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

from core.models import Usuario, Parametro, Empresa
from core.forms import UsuarioForm, ParametroForm, EmpresaForm

from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy

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

# PÁGINAS PRINCIPAIS

def home(request):
    """
    Página inicial do Portal do Gestor
    """
    return render(request, 'gestor/home.html')


# CRUD EMPRESA

@login_required
def empresa_list(request):
    # Ordena por nome para garantir consistência na paginação
    empresas_list = Empresa.objects.all().order_by('nome')
    
    # Configurar paginação (10 itens por página)
    paginator = Paginator(empresas_list, 10)
    page = request.GET.get('page', 1)
    
    try:
        empresas = paginator.page(page)
    except PageNotAnInteger:
        # Se a página não for um inteiro, exibe a primeira página
        empresas = paginator.page(1)
    except EmptyPage:
        # Se a página estiver fora do intervalo, exibe a última página
        empresas = paginator.page(paginator.num_pages)
    
    return render(request, 'gestor/empresa_list.html', {'empresas': empresas})

@login_required
def empresa_create(request):
    if request.method == 'POST':
        form = EmpresaForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Empresa criada com sucesso.')
            # Limpa todas as mensagens após adicionar para evitar duplicação
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
            # Limpa todas as mensagens após adicionar para evitar duplicação
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

# CRUD USUÁRIO

@login_required
def usuario_list(request):
    # Ordena por username para garantir consistência na paginação
    usuarios_list = Usuario.objects.all().order_by('username')
    
    # Configurar paginação (10 itens por página)
    paginator = Paginator(usuarios_list, 10)
    page = request.GET.get('page', 1)
    
    try:
        usuarios = paginator.page(page)
    except PageNotAnInteger:
        # Se a página não for um inteiro, exibe a primeira página
        usuarios = paginator.page(1)
    except EmptyPage:
        # Se a página estiver fora do intervalo, exibe a última página
        usuarios = paginator.page(paginator.num_pages)
    
    return render(request, 'gestor/usuario_list.html', {'usuarios': usuarios})

@login_required
def usuario_create(request):
    if request.method == 'POST':
        form = UsuarioForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Usuário criado com sucesso.')
            # Limpa todas as mensagens após adicionar para evitar duplicação
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
            # Limpa todas as mensagens após adicionar para evitar duplicação
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

# CRUD PARÂMETROS

@login_required
def parametro_list(request):
    # Buscar todos os parâmetros, ordenados por nome do parâmetro
    parametros_list = Parametro.objects.all().order_by('parametro')
    
    # Configurar paginação (10 itens por página)
    paginator = Paginator(parametros_list, 10)
    page = request.GET.get('page', 1)
    
    try:
        parametros = paginator.page(page)
    except PageNotAnInteger:
        # Se a página não for um inteiro, exibe a primeira página
        parametros = paginator.page(1)
    except EmptyPage:
        # Se a página estiver fora do intervalo, exibe a última página
        parametros = paginator.page(paginator.num_pages)
    
    return render(request, 'gestor/parametro_list.html', {'parametros': parametros})

@login_required
def parametro_create(request):
    if request.method == 'POST':
        form = ParametroForm(request.POST)
        if form.is_valid():
            parametro = form.save()
            messages.success(request, 'Parâmetro criado com sucesso.')
            # Redireciona diretamente para a lista, não para o detalhe
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
            # Redireciona diretamente para a lista, não para o detalhe
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
        # Limpa todas as mensagens após adicionar para evitar duplicação
        storage = messages.get_messages(request)
        storage.used = True
        return redirect('gestor:parametro_list')
    return render(request, 'gestor/parametro_confirm_delete.html', {'parametro': parametro})

@login_required
def dashboard(request):
    print("Usuário acessando o dashboard:", request.user)
    context = {
        'total_empresas': Empresa.objects.filter(ativa=True).count(),
        'total_usuarios': Usuario.objects.filter(is_active=True).count(),
    }
    return render(request, 'gestor/dashboard.html', context)