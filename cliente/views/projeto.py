# clientes/views/projeto.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from core.models import Usuario, Empresa, Feira
from projetos.models import Projeto, ProjetoMarco
from projetos.forms import ProjetoForm

from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.utils import timezone

@login_required
def dashboard(request):
    """
    Dashboard principal do sistema
    """
    # Obtém a empresa do usuário logado
    empresa = request.user.empresa
    
    # Obtém as estatísticas de projetos do cliente
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
    return render(request, 'dashboard.html', context)

@login_required
def projeto_list(request):
    """
    Lista de projetos da empresa
    """
    # Obtém a empresa do usuário logado
    empresa = request.user.empresa
    
    # Filtros
    status = request.GET.get('status')
    search = request.GET.get('search')
    
    # Base query
    projetos_list = Projeto.objects.filter(empresa=empresa).order_by('-created_at')
    
    # Aplica filtros se fornecidos
    if status and status != 'todos':
        projetos_list = projetos_list.filter(status=status)
    
    if search:
        projetos_list = projetos_list.filter(nome__icontains=search)
    
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
        'status_filter': status,
        'search_query': search,
    }
    return render(request, 'projetos/projeto_list.html', context)

@login_required
def projeto_detail(request, pk):
    """
    Detalhes de um projeto específico no portal do cliente
    """
    # Obtém a empresa do usuário logado
    empresa = request.user.empresa
    
    # Obtém o projeto específico (verificando se pertence à mesma empresa)
    projeto = get_object_or_404(Projeto, pk=pk, empresa=empresa)
    
    # Obtém plantas e referências
    plantas = projeto.plantas.all()
    referencias = projeto.referencias.all()
    
    # Obtém marcos do projeto ordenados por data
    marcos = projeto.marcos.all().order_by('data')
    
    # Obtém mensagens não lidas
    mensagens_nao_lidas = 0
    if hasattr(projeto, 'mensagens'):
        mensagens_nao_lidas = projeto.mensagens.filter(
            destinatario=request.user, 
            lida=False
        ).count()
    
    context = {
        'empresa': empresa,
        'projeto': projeto,
        'plantas': plantas,
        'referencias': referencias,
        'marcos': marcos,
        'mensagens_nao_lidas': mensagens_nao_lidas,
    }
    return render(request, 'cliente/projeto_detail.html', context)

@login_required
def aprovar_projeto(request, pk):
    """
    View para aprovar um projeto
    """
    # Obtém a empresa do usuário logado
    empresa = request.user.empresa
    
    # Obtém o projeto específico
    projeto = get_object_or_404(Projeto, pk=pk, empresa=empresa)
    
    if request.method == 'POST':
        # Atualiza o status do projeto
        projeto.status = 'projeto_aprovado'
        projeto.data_aprovacao_projeto = timezone.now()
        projeto.save(update_fields=['status', 'data_aprovacao_projeto'])
        
        # Registra o marco de aprovação do projeto
        ProjetoMarco.objects.create(
            projeto=projeto,
            tipo='aprovacao_projeto',
            observacao='Projeto aprovado pelo cliente',
            registrado_por=request.user
        )
        
        # Atualiza as métricas do projeto
        projeto.atualizar_metricas()
        
        messages.success(request, 'Projeto aprovado com sucesso!')
        return redirect('cliente:projeto_detail', pk=projeto.id)
    
    return render(request, 'cliente/aprovar_projeto.html', {'projeto': projeto})

@login_required
def selecionar_feira(request, projeto_id):
    """
    View para selecionar a feira associada ao projeto
    """
    # Obtém a empresa do usuário logado
    empresa = request.user.empresa
    
    # Obtém o projeto
    projeto = get_object_or_404(Projeto, pk=projeto_id, empresa=empresa)
    
    # Lista de feiras ativas
    feiras = Feira.objects.filter(ativa=True).order_by('-data_inicio')
    
    if request.method == 'POST':
        feira_id = request.POST.get('feira_id')
        if feira_id:
            feira = get_object_or_404(Feira, pk=feira_id)
            projeto.feira = feira
            projeto.save()
            
            messages.success(request, f'Feira "{feira.nome}" selecionada com sucesso!')
            return redirect('projetos:projeto_detail', pk=projeto.id)
        else:
            messages.error(request, 'Por favor, selecione uma feira.')
    
    context = {
        'empresa': empresa,
        'projeto': projeto,
        'feiras': feiras,
    }
    return render(request, 'projetos/selecionar_feira.html', context)

# clientes/views/projeto.py

# Atualize a função projeto_create para lidar com o novo campo tipo_projeto
@login_required
def projeto_create(request):
    """
    View para criar um novo projeto
    """
    # Obtém a empresa do usuário logado
    empresa = request.user.empresa
    
    if request.method == 'POST':
        form = ProjetoForm(request.POST)
        if form.is_valid():
            projeto = form.save(commit=False)
            projeto.empresa = empresa
            projeto.criado_por = request.user
            
            # Define o status como briefing_pendente
            projeto.status = 'briefing_pendente'
            
            # Se o tipo for feira_negocios e tiver feira selecionada, preenche o nome com a feira
            if projeto.tipo_projeto == 'feira_negocios' and projeto.feira:
                projeto.nome = projeto.feira.nome
            
            # Salva o projeto
            projeto.save()
            
            # Cria um marco para registrar a criação do projeto
            ProjetoMarco.objects.create(
                projeto=projeto,
                tipo='criacao_projeto',
                observacao='Projeto criado pelo cliente',
                registrado_por=request.user
            )
            
            messages.success(request, 'Projeto criado com sucesso!')
            return redirect('cliente:projeto_detail', pk=projeto.id)
    else:
        form = ProjetoForm()
        # Inicializar campos ocultos com valores padrão
        form.initial['status'] = 'briefing_pendente'
        form.initial['tipo_projeto'] = 'feira_negocios'
    
    context = {
        'empresa': empresa,
        'form': form,
    }
    return render(request, 'cliente/projeto_form.html', context)

# Atualize a função projeto_update para lidar com o novo campo tipo_projeto
@login_required
def projeto_update(request, pk):
    """
    View para atualizar um projeto existente
    """
    # Obtém a empresa do usuário logado
    empresa = request.user.empresa
    
    # Obtém o projeto específico (verificando se pertence à mesma empresa)
    projeto = get_object_or_404(Projeto, pk=pk, empresa=empresa)
    
    if request.method == 'POST':
        form = ProjetoForm(request.POST, instance=projeto)
        if form.is_valid():
            projeto_atualizado = form.save(commit=False)
            
            # Atualiza o nome baseado no tipo de projeto e feira
            if projeto_atualizado.tipo_projeto == 'feira_negocios' and projeto_atualizado.feira:
                projeto_atualizado.nome = projeto_atualizado.feira.nome
            
            projeto_atualizado.save()
            messages.success(request, 'Projeto atualizado com sucesso.')
            return redirect('cliente:projeto_detail', pk=projeto.pk)
    else:
        form = ProjetoForm(instance=projeto)
    
    context = {
        'empresa': empresa,
        'projeto': projeto,
        'form': form,
    }
    return render(request, 'cliente/projeto_form.html', context)


# Atualize também a classe ProjetoUpdateView
class ProjetoUpdateView(LoginRequiredMixin, UpdateView):
    model = Projeto
    form_class = ProjetoForm
    template_name = 'projetos/projeto_form.html'
    
    def get_queryset(self):
        # Filtra projetos da empresa do usuário logado
        return Projeto.objects.filter(empresa=self.request.user.empresa)
    
    def form_valid(self, form):
        projeto = form.save(commit=False)
        
        # Atualiza o nome baseado no tipo de projeto e feira
        if projeto.tipo_projeto == 'feira_negocios' and projeto.feira:
            projeto.nome = projeto.feira.nome
            
        projeto.save()
        messages.success(self.request, 'Projeto atualizado com sucesso!')
        return redirect('projetos:projeto_detail', pk=self.object.id)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['empresa'] = self.request.user.empresa
        context['projeto'] = self.object
        return context

@login_required
def projeto_delete(request, pk):
    """
    View para excluir um projeto existente
    """
    # Obtém a empresa do usuário logado
    empresa = request.user.empresa
    
    # Obtém o projeto específico (verificando se pertence à mesma empresa)
    projeto = get_object_or_404(Projeto, pk=pk, empresa=empresa)
    
    if request.method == 'POST':
        projeto.delete()
        messages.success(request, 'Projeto excluído com sucesso.')
        return redirect('projetos:projeto_list')
    
    context = {
        'empresa': empresa,
        'projeto': projeto,
    }
    return render(request, 'projetos/projeto_confirm_delete.html', context)

# Atualização da função iniciar_briefing

@login_required
def iniciar_briefing(request, projeto_id):
    """
    View para iniciar o briefing de um projeto
    """
    # Obtém a empresa do usuário logado
    empresa = request.user.empresa
    
    # Obtém o projeto
    projeto = get_object_or_404(Projeto, pk=projeto_id, empresa=empresa)
    
    # Verifica se o projeto já tem um briefing
    # Adiciona verificação extra de segurança
    if projeto.pk and projeto.has_briefing:
        # Pega o briefing mais recente
        briefing = projeto.briefings.first()
        return redirect('cliente:briefing_etapa', projeto_id=projeto.id, etapa=briefing.etapa_atual)
    
    try:
        # Cria um novo briefing para o projeto usando create para minimizar chamadas ao banco
        from projetos.models import Briefing, BriefingValidacao
        
        # Cria o briefing primeiro sem chamar métodos que dependem de relacionamentos
        briefing = Briefing(
            projeto=projeto,
            status='rascunho',
            etapa_atual=1
        )
        
        # Salva o objeto para garantir que tenha um ID
        briefing.save()
        
        # Agora podemos criar as validações com segurança
        for secao in ['evento', 'estande', 'areas_estande', 'dados_complementares']:
            BriefingValidacao.objects.create(
                briefing=briefing,
                secao=secao,
                status='pendente'
            )
        
        # Atualiza o status do projeto
        projeto.status = 'briefing_em_andamento'
        projeto.save(update_fields=['status'])
        
        messages.success(request, 'Briefing iniciado com sucesso!')
        return redirect('cliente:briefing_etapa', projeto_id=projeto.id, etapa=1)
    
    except Exception as e:
        # Registra o erro e apresenta uma mensagem mais amigável
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Erro ao criar briefing: {str(e)}")
        
        messages.error(request, "Ocorreu um erro ao iniciar o briefing. Por favor, tente novamente ou contate o suporte.")
        return redirect('cliente:projeto_detail', pk=projeto.id)


@login_required
def verificar_manual_feira(request, projeto_id):
    """
    View para verificar o manual da feira usando o assistente IA
    """
    # Obtém a empresa do usuário logado
    empresa = request.user.empresa
    
    # Obtém o projeto
    projeto = get_object_or_404(Projeto, pk=projeto_id, empresa=empresa)
    
    # Verifica se o projeto tem uma feira selecionada com manual
    if not projeto.feira or not projeto.feira.manual:
        messages.error(request, 'Este projeto não possui feira selecionada ou a feira não tem manual disponível.')
        return redirect('projetos:projeto_detail', pk=projeto.id)
    
    context = {
        'empresa': empresa,
        'projeto': projeto,
        'feira': projeto.feira,
    }
    return render(request, 'projetos/verificar_manual.html', context)

# Classes baseadas em view como alternativa

class ProjetoListView(LoginRequiredMixin, ListView):
    model = Projeto
    template_name = 'projetos/projeto_list.html'
    context_object_name = 'projetos'
    paginate_by = 10
    
    def get_queryset(self):
        # Filtra projetos da empresa do usuário logado
        queryset = Projeto.objects.filter(empresa=self.request.user.empresa).order_by('-created_at')
        
        # Aplica filtros adicionais
        status = self.request.GET.get('status')
        search = self.request.GET.get('search')
        
        if status and status != 'todos':
            queryset = queryset.filter(status=status)
        
        if search:
            queryset = queryset.filter(nome__icontains=search)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['empresa'] = self.request.user.empresa
        context['status_filter'] = self.request.GET.get('status')
        context['search_query'] = self.request.GET.get('search')
        return context

class ProjetoDetailView(LoginRequiredMixin, DetailView):
    model = Projeto
    template_name = 'projetos/projeto_detail.html'
    context_object_name = 'projeto'
    
    def get_queryset(self):
        # Filtra projetos da empresa do usuário logado
        return Projeto.objects.filter(empresa=self.request.user.empresa)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['empresa'] = self.request.user.empresa
        context['plantas'] = self.object.plantas.all()
        context['referencias'] = self.object.referencias.all()
        return context

class ProjetoCreateView(LoginRequiredMixin, CreateView):
    model = Projeto
    form_class = ProjetoForm
    template_name = 'projetos/projeto_form.html'
    
    def form_valid(self, form):
        form.instance.empresa = self.request.user.empresa
        form.instance.cliente = self.request.user
        self.object = form.save()
        messages.success(self.request, 'Projeto criado com sucesso!')
        return redirect('projetos:selecionar_feira', projeto_id=self.object.id)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['empresa'] = self.request.user.empresa
        return context
class ProjetoDeleteView(LoginRequiredMixin, DeleteView):
    model = Projeto
    template_name = 'projetos/projeto_confirm_delete.html'
    success_url = reverse_lazy('projetos:projeto_list')
    
    def get_queryset(self):
        # Filtra projetos da empresa do usuário logado
        return Projeto.objects.filter(empresa=self.request.user.empresa)
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Projeto excluído com sucesso!')
        return super().delete(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['empresa'] = self.request.user.empresa
        return context
    

# projetos/views/projeto.py

@login_required
def aprovar_projeto(request, pk):
    """
    View para aprovar um projeto
    """
    # Obtém a empresa do usuário logado
    empresa = request.user.empresa
    
    # Obtém o projeto específico
    projeto = get_object_or_404(Projeto, pk=pk, empresa=empresa)
    
    if request.method == 'POST':
        # Atualiza o status do projeto
        projeto.status = 'projeto_aprovado'
        projeto.data_aprovacao_projeto = timezone.now()
        projeto.save()
        
        # Registra o marco de aprovação do projeto
        ProjetoMarco.objects.create(
            projeto=projeto,
            tipo='aprovacao_projeto',
            observacao='Projeto aprovado pelo cliente',
            registrado_por=request.user
        )
        
        # Atualiza as métricas do projeto
        projeto.atualizar_metricas()
        
        messages.success(request, 'Projeto aprovado com sucesso!')
        return redirect('cliente:projeto_detail', pk=projeto.id)
    
    return render(request, 'projetos/aprovar_projeto.html', {'projeto': projeto})