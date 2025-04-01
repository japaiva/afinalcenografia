from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

from core.models import Usuario, Parametro, Empresa
from core.forms import UsuarioForm, ParametroForm, EmpresaForm
from projetos.models import Projeto

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
    
    # Adicione esta linha para contar o total de projetos
    total_projetos = Projeto.objects.all().count()
    
    context = {
        'total_empresas': Empresa.objects.filter(ativa=True).count(),
        'total_usuarios': Usuario.objects.filter(is_active=True).count(),
        'total_projetos': total_projetos,  # Passe o total para o template
    }
    return render(request, 'gestor/dashboard.html', context)

# Adicione estas funções ao views.py do app gestor

@login_required
def projeto_list(request):
    """
    Lista de todos os projetos para o gestor
    """
    # Lista de todos os projetos, ordenados por data de criação (mais recentes primeiro)
    projetos_list = Projeto.objects.all().order_by('-created_at')
    
    # Filtragem por parâmetros na URL
    status = request.GET.get('status')
    empresa_id = request.GET.get('empresa')
    
    if status:
        projetos_list = projetos_list.filter(status=status)
    if empresa_id:
        projetos_list = projetos_list.filter(empresa_id=empresa_id)
    
    # Configurar paginação (10 itens por página)
    paginator = Paginator(projetos_list, 10)
    page = request.GET.get('page', 1)
    
    try:
        projetos = paginator.page(page)
    except PageNotAnInteger:
        # Se a página não for um inteiro, exibe a primeira página
        projetos = paginator.page(1)
    except EmptyPage:
        # Se a página estiver fora do intervalo, exibe a última página
        projetos = paginator.page(paginator.num_pages)
    
    # Lista de empresas para o filtro
    empresas = Empresa.objects.all().order_by('nome')
    
    context = {
        'projetos': projetos,
        'empresas': empresas,
        'status_escolhido': status,
        'empresa_escolhida': empresa_id,
    }
    
    return render(request, 'gestor/projeto_list.html', context)

@login_required
def projeto_detail(request, pk):
    """
    Detalhes de um projeto específico
    """
    projeto = get_object_or_404(Projeto, pk=pk)
    
    # Lista de projetistas disponíveis para atribuição
    projetistas = Usuario.objects.filter(nivel='projetista', is_active=True).order_by('username')
    
    # Arquivos do projeto
    arquivos = projeto.arquivos.all()
    
    context = {
        'projeto': projeto,
        'projetistas': projetistas,
        'arquivos': arquivos,
    }
    
    return render(request, 'gestor/projeto_detail.html', context)

@login_required
def projeto_atribuir(request, pk, usuario_id):
    """
    Atribuir um projetista a um projeto
    """
    projeto = get_object_or_404(Projeto, pk=pk)
    projetista = get_object_or_404(Usuario, pk=usuario_id, nivel='projetista')
    
    projeto.projetista = projetista
    projeto.save()
    
    messages.success(request, f'Projeto atribuído a {projetista.get_full_name() or projetista.username} com sucesso.')
    return redirect('gestor:projeto_detail', pk=projeto.pk)

@login_required
def projeto_alterar_status(request, pk):
    """
    Alterar o status de um projeto
    """
    projeto = get_object_or_404(Projeto, pk=pk)
    
    if request.method == 'POST':
        novo_status = request.POST.get('status')
        if novo_status in [s[0] for s in Projeto.STATUS_CHOICES]:
            projeto.status = novo_status
            projeto.save()
            messages.success(request, f'Status do projeto alterado para {projeto.get_status_display()} com sucesso.')
        else:
            messages.error(request, 'Status inválido.')
        
        return redirect('gestor:projeto_detail', pk=projeto.pk)
    
    # Se não for POST, redireciona para os detalhes do projeto
    return redirect('gestor:projeto_detail', pk=projeto.pk)

@login_required
def mensagens(request):
    """
    Central de mensagens do gestor
    """
    # Obtém todos os projetos para listar nas conversas
    projetos = Projeto.objects.all().order_by('-updated_at')
    
    # Para demonstração, podemos criar uma lista de conversas fictícias
    conversas = [
        {
            'projeto': projeto,
            'cliente': projeto.cliente,
            'empresa': projeto.empresa,
            'ultima_mensagem': f"Últimas atualizações sobre {projeto.nome}",
            'data': projeto.updated_at,
            'nao_lidas': 0
        } for projeto in projetos[:5]  # Limita a 5 projetos para demonstração
    ]
    
    context = {
        'conversas': conversas,
        'projetos': projetos,
    }
    return render(request, 'gestor/central_mensagens.html', context)

@login_required
def nova_mensagem(request):
    """
    Criação de nova mensagem
    """
    # Obtém todos os projetos para selecionar
    projetos = Projeto.objects.all().order_by('-updated_at')
    
    if request.method == 'POST':
        # Aqui você processaria a mensagem
        # Para demonstração, vamos apenas redirecionar
        messages.success(request, 'Mensagem enviada com sucesso!')
        return redirect('gestor:mensagens')
    
    context = {
        'projetos': projetos,
    }
    return render(request, 'gestor/nova_mensagem.html', context)

@login_required
def mensagens_projeto(request, projeto_id):
    """
    Mensagens de um projeto específico
    """
    # Obtém o projeto específico
    projeto = get_object_or_404(Projeto, pk=projeto_id)
    
    # Para demonstração, podemos criar uma lista de mensagens fictícias
    mensagens_lista = [
        {
            'remetente': projeto.cliente.get_full_name() or projeto.cliente.username,
            'conteudo': 'Precisamos de ajustes no projeto.',
            'data': projeto.updated_at,
            'is_cliente': True
        },
        {
            'remetente': 'Você',
            'conteudo': 'Claro, vamos analisar e retornar em breve.',
            'data': projeto.updated_at,
            'is_cliente': False
        }
    ]
    
    context = {
        'projeto': projeto,
        'mensagens': mensagens_lista,
    }
    return render(request, 'gestor/mensagens_projeto.html', context)