# cliente/views/base.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy

from core.models import Usuario, Empresa
from core.forms import EmpresaForm
from core.decorators import cliente_required

# PAGINAS PRINCIPAIS

@login_required
@cliente_required
def dashboard(request):
    """
    Dashboard principal do Portal do Cliente
    """
    # Obtém a empresa do usuário logado
    empresa = request.user.empresa
    
    # Obtém as estatísticas de projetos do cliente
    from projetos.models import Projeto
    total_projetos = Projeto.objects.filter(empresa=empresa).count()
    projetos_ativos = Projeto.objects.filter(empresa=empresa, status='ativo').count()
    
    # Projetos recentes
    projetos_recentes = Projeto.objects.filter(empresa=empresa).order_by('-created_at')[:5]
    
    context = {
        'empresa': empresa,
        'total_projetos': total_projetos,
        'projetos_ativos': projetos_ativos,
        'projetos_recentes': projetos_recentes,
    }
    return render(request, 'cliente/dashboard.html', context)

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

def home(request):
    return render(request, 'cliente/home.html')

# CRUD USUARIOS

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

# FUNCOES UTILITARIAS

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

# ADICIONE ESTAS FUNCOES PARA COMPATIBILIDADE (caso sejam usadas em templates ou URLs)

@login_required
@cliente_required
def briefing(request):
    """
    Briefing assistido por IA para criação de novo projeto
    """
    # Obtém a empresa do usuário logado
    empresa = request.user.empresa
    
    from projetos.models import Projeto, ProjetoReferencia
    
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