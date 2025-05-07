# views/base.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

from core.models import Usuario, Empresa
from core.forms import EmpresaForm  # Importe o formulário da empresa
from projetos.models import Projeto, ProjetoReferencia
from projetos.forms import ProjetoForm

from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy

class ClienteLoginView(LoginView):
    template_name = 'cliente/login.html'
    
    def form_valid(self, form):
        print("Login bem-sucedido para:", form.get_user())
        return super().form_valid(form)
    
    def get_success_url(self):
        print("Redirecionando para:", reverse_lazy('cliente:dashboard'))
        return reverse_lazy('cliente:dashboard')
 
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['app_name'] = 'Portal do Cliente'
        return context

# Middleware para verificar se o usuário é cliente
def cliente_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not hasattr(request.user, 'nivel') or request.user.nivel != 'cliente':
            messages.error(request, 'Acesso negado. Você não tem permissão de cliente.')
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return wrapper

# Middleware para verificar se o usuário é gestor
def gestor_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not hasattr(request.user, 'nivel') or request.user.nivel != 'gestor':
            messages.error(request, 'Acesso negado. Você não tem permissão de gestor.')
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return wrapper

# Middleware para verificar se o usuário é projetista
def projetista_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not hasattr(request.user, 'nivel') or request.user.nivel != 'projetista':
            messages.error(request, 'Acesso negado. Você não tem permissão de projetista.')
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return wrapper

# PÁGINAS PRINCIPAIS

def home(request):
    """
    Página inicial do Portal do Cliente
    """
    return render(request, 'cliente/home.html')

@login_required
@cliente_required
def dashboard(request):
    """
    Dashboard do Portal do Cliente
    """
    # Obtém a empresa do usuário logado
    empresa = request.user.empresa
    
    # Obtém as estatísticas de projetos do cliente
    total_projetos = Projeto.objects.filter(empresa=empresa).count()
    projetos_ativos = Projeto.objects.filter(empresa=empresa, status='ativo').count()
    
    context = {
        'empresa': empresa,
        'total_projetos': total_projetos,
        'projetos_ativos': projetos_ativos,
    }
    return render(request, 'cliente/dashboard.html', context)

# VISUALIZAÇÃO DE USUÁRIOS DA EMPRESA

@login_required
@cliente_required
def usuario_list(request):
    """
    Lista de usuários da mesma empresa do cliente
    """
    # Obtém a empresa do usuário logado
    empresa = request.user.empresa
    
    # Obtém usuários da mesma empresa
    usuarios_list = Usuario.objects.filter(empresa=empresa).order_by('username')
    
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
    
    context = {
        'empresa': empresa,
        'usuarios': usuarios,
    }
    return render(request, 'cliente/usuario_list.html', context)

@login_required
@cliente_required
def usuario_detail(request, pk):
    """
    Detalhes de um usuário específico da mesma empresa
    """
    # Obtém a empresa do usuário logado
    empresa = request.user.empresa
    
    # Obtém o usuário específico (verificando se pertence à mesma empresa)
    usuario = get_object_or_404(Usuario, pk=pk, empresa=empresa)
    
    context = {
        'empresa': empresa,
        'usuario': usuario,
    }
    return render(request, 'cliente/usuario_detail.html', context)

@login_required
@cliente_required
def empresa_detail(request):
    """
    Detalhes da empresa do cliente com possibilidade de edição
    """
    # Obtém a empresa do usuário logado
    empresa = request.user.empresa
    
    if request.method == 'POST':
        form = EmpresaForm(request.POST, request.FILES, instance=empresa)
        # Se o cliente está editando, não permitimos alterar o status ativo/inativo
        if form.is_valid():
            # Preservar o status original (ativa/inativa)
            status_original = empresa.ativa
            empresa_atualizada = form.save(commit=False)
            empresa_atualizada.ativa = status_original  # Garantir que o status não mude
            empresa_atualizada.save()
            messages.success(request, 'Empresa atualizada com sucesso.')
            return redirect('cliente:empresa_detail')
    else:
        form = EmpresaForm(instance=empresa)
    
    context = {
        'empresa': empresa,
        'form': form,
    }
    return render(request, 'cliente/empresa_detail.html', context)

# CRUD PROJETOS

@login_required
@cliente_required
def projeto_list(request):
    """
    Lista de projetos da empresa do cliente
    """
    # Obtém a empresa do usuário logado
    empresa = request.user.empresa
    
    # Obtém projetos da empresa
    projetos_list = Projeto.objects.filter(empresa=empresa).order_by('-created_at')
    
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
    
    context = {
        'empresa': empresa,
        'projetos': projetos,
    }
    return render(request, 'cliente/projeto_list.html', context)


@login_required
@cliente_required
def projeto_detail(request, pk):
    """
    Detalhes de um projeto específico
    """
    # Obtém a empresa do usuário logado
    empresa = request.user.empresa
    
    # Obtém o projeto específico (verificando se pertence à mesma empresa)
    projeto = get_object_or_404(Projeto, pk=pk, empresa=empresa)
    
    context = {
        'empresa': empresa,
        'projeto': projeto,
    }
    return render(request, 'cliente/projeto_detail.html', context)

@login_required
@cliente_required
def projeto_create(request):
    """
    View para criar um novo projeto e redirecionar diretamente para o briefing
    """
    # Obtém a empresa do usuário logado
    empresa = request.user.empresa
    
    if request.method == 'POST':
        form = ProjetoForm(request.POST, request.FILES)
        if form.is_valid():
            projeto = form.save(commit=False)
            projeto.empresa = empresa
            projeto.cliente = request.user
            projeto.save()
            
            # Processar os arquivos de referência, se houver
            if 'arquivos_referencia' in request.FILES:
                for arquivo in request.FILES.getlist('arquivos_referencia'):
                    ProjetoReferencia.objects.create(
                        projeto=projeto,
                        nome=arquivo.name,
                        arquivo=arquivo,
                        tipo=determinar_tipo_arquivo(arquivo.name)
                    )
            
            messages.success(request, 'Projeto criado com sucesso!')
            
            # Redirecionar diretamente para iniciar o briefing
            return redirect('cliente:iniciar_briefing', projeto_id=projeto.id)
    else:
        form = ProjetoForm()
    
    context = {
        'empresa': empresa,
        'form': form,
    }
    return render(request, 'cliente/projeto_form.html', context)

def determinar_tipo_arquivo(nome_arquivo):
    """
    Determina o tipo de arquivo com base na extensão
    """
    nome_arquivo = nome_arquivo.lower()
    if nome_arquivo.endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp')):
        return 'imagem'
    elif nome_arquivo.endswith(('.pdf', '.doc', '.docx', '.txt')):
        return 'documento'
    elif nome_arquivo.endswith(('.dwg', '.dxf', '.skp')):
        return 'planta'
    else:
        return 'outro'

@login_required
@cliente_required
def projeto_update(request, pk):
    # Obtém a empresa do usuário logado
    empresa = request.user.empresa
    
    # Obtém o projeto específico (verificando se pertence à mesma empresa)
    projeto = get_object_or_404(Projeto, pk=pk, empresa=empresa)
    
    if request.method == 'POST':
        form = ProjetoForm(request.POST, request.FILES, instance=projeto)  # Importante: inclua request.FILES
        if form.is_valid():
            form.save()
            messages.success(request, 'Projeto atualizado com sucesso.')
            # Limpa todas as mensagens após adicionar para evitar duplicação
            storage = messages.get_messages(request)
            storage.used = True
            return redirect('cliente:projeto_detail', pk=projeto.pk)
    else:
        form = ProjetoForm(instance=projeto)
    
    context = {
        'empresa': empresa,
        'projeto': projeto,
        'form': form,
    }
    return render(request, 'cliente/projeto_form.html', context)

@login_required
@cliente_required
def projeto_delete(request, pk):
    """
    Exclusão de um projeto existente
    """
    # Obtém a empresa do usuário logado
    empresa = request.user.empresa
    
    # Obtém o projeto específico (verificando se pertence à mesma empresa)
    projeto = get_object_or_404(Projeto, pk=pk, empresa=empresa)
    
    if request.method == 'POST':
        projeto.delete()
        messages.success(request, 'Projeto excluído com sucesso.')
        # Limpa todas as mensagens após adicionar para evitar duplicação
        storage = messages.get_messages(request)
        storage.used = True
        return redirect('cliente:projeto_list')
    
    context = {
        'empresa': empresa,
        'projeto': projeto,
    }
    return render(request, 'cliente/projeto_confirm_delete.html', context)

# Adicione estas funções ao views.py do app cliente

@login_required
@cliente_required
def briefing(request):
    """
    Briefing assistido por IA para criação de novo projeto
    """
    # Obtém a empresa do usuário logado
    empresa = request.user.empresa
    
    if request.method == 'POST':
        # Aqui você processaria os dados do formulário
        # Para simplificar, vamos apenas criar um projeto básico
        projeto = Projeto(
            nome=request.POST.get('nomeProjeto', 'Novo Projeto'),
            empresa=empresa,
            cliente=request.user,
            descricao=request.POST.get('descricaoProjeto', ''),
            requisitos=request.POST.get('objetivoProjeto', ''),
            data_inicio=request.POST.get('dataInicio'),
            prazo_entrega=request.POST.get('dataFim'),
            orcamento=request.POST.get('orcamento', 0),
            status='pendente'
        )
        projeto.save()
        
        # Processa uploads de arquivos
        if 'referencias' in request.FILES:
            for arquivo in request.FILES.getlist('referencias'):
                ProjetoReferencia.objects.create(
                    projeto=projeto,
                    nome=arquivo.name,
                    arquivo=arquivo,
                    tamanho=arquivo.size
                )
        
        messages.success(request, 'Projeto criado com sucesso! Aguarde análise da equipe.')
        return redirect('cliente:projeto_detail', pk=projeto.pk)
    
    context = {
        'empresa': empresa,
    }
    return render(request, 'cliente/briefing.html', context)

@login_required
@cliente_required
def mensagens(request):
    """
    Central de mensagens do cliente
    """
    # Obtém a empresa do usuário logado
    empresa = request.user.empresa
    
    # Obtém projetos do cliente para listar nas conversas
    projetos = Projeto.objects.filter(empresa=empresa)
    
    # Para demonstração, podemos criar uma lista de conversas fictícias
    conversas = [
        {
            'projeto': projeto,
            'ultima_mensagem': f"Últimas atualizações sobre {projeto.nome}",
            'data': projeto.updated_at,
            'nao_lidas': 0
        } for projeto in projetos
    ]
    
    context = {
        'empresa': empresa,
        'conversas': conversas,
        'projetos': projetos,
    }
    return render(request, 'cliente/central_mensagens.html', context)

@login_required
@cliente_required
def nova_mensagem(request):
    """
    Criação de nova mensagem
    """
    # Obtém a empresa do usuário logado
    empresa = request.user.empresa
    
    # Obtém projetos do cliente para selecionar
    projetos = Projeto.objects.filter(empresa=empresa)
    
    if request.method == 'POST':
        # Aqui você processaria a mensagem
        # Para demonstração, vamos apenas redirecionar
        messages.success(request, 'Mensagem enviada com sucesso!')
        return redirect('cliente:mensagens')
    
    context = {
        'empresa': empresa,
        'projetos': projetos,
    }
    return render(request, 'cliente/nova_mensagem.html', context)

@login_required
@cliente_required
def mensagens_projeto(request, projeto_id):
    """
    Mensagens de um projeto específico
    """
    # Obtém a empresa do usuário logado
    empresa = request.user.empresa
    
    # Obtém o projeto específico
    projeto = get_object_or_404(Projeto, pk=projeto_id, empresa=empresa)
    
    # Para demonstração, podemos criar uma lista de mensagens fictícias
    mensagens_lista = [
        {
            'remetente': 'Você',
            'conteudo': 'Precisamos de ajustes no projeto.',
            'data': projeto.updated_at,
            'is_cliente': True
        },
        {
            'remetente': 'Afinal Cenografia',
            'conteudo': 'Claro, vamos analisar e retornar em breve.',
            'data': projeto.updated_at,
            'is_cliente': False
        }
    ]
    
    context = {
        'empresa': empresa,
        'projeto': projeto,
        'mensagens': mensagens_lista,
    }
    return render(request, 'cliente/mensagens_projeto.html', context)