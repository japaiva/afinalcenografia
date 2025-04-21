# clientes/views/projeto.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from core.models import Usuario, Empresa, Feira
from projetos.models import Projeto, ProjetoPlanta, ProjetoReferencia
from projetos.forms import ProjetoForm, ProjetoPlantaForm, ProjetoReferenciaForm

from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy

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
    Detalhes de um projeto específico
    """
    # Obtém a empresa do usuário logado
    empresa = request.user.empresa
    
    # Obtém o projeto específico (verificando se pertence à mesma empresa)
    projeto = get_object_or_404(Projeto, pk=pk, empresa=empresa)
    
    # Obtém plantas e referências
    plantas = projeto.plantas.all()
    referencias = projeto.referencias.all()
    
    context = {
        'empresa': empresa,
        'projeto': projeto,
        'plantas': plantas,
        'referencias': referencias,
    }
    return render(request, 'projetos/projeto_detail.html', context)

# projetos/views/projeto.py (para cliente)

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
            projeto.cliente = request.user
            
            # Se a feira for selecionada, os campos serão preenchidos automaticamente
            # pelo método save() no modelo Projeto
            projeto.save()
            
            messages.success(request, 'Projeto criado com sucesso!')
            
            # Verificar se a feira foi selecionada
            if not projeto.feira:
                # Se não houver feira, redirecionar para selecionar
                return redirect('cliente:selecionar_feira', projeto_id=projeto.id)
            else:
                # Se já tiver feira, ir para detalhes do projeto
                return redirect('cliente:projeto_detail', pk=projeto.id)
    else:
        form = ProjetoForm()
    
    context = {
        'empresa': empresa,
        'form': form,
    }
    return render(request, 'cliente/projeto_form.html', context)

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
            form.save()
            messages.success(request, 'Projeto atualizado com sucesso.')
            return redirect('projetos:projeto_detail', pk=projeto.pk)
    else:
        form = ProjetoForm(instance=projeto)
    
    context = {
        'empresa': empresa,
        'projeto': projeto,
        'form': form,
    }
    return render(request, 'projetos/projeto_form.html', context)

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

@login_required
def upload_planta(request, projeto_id):
    """
    View para fazer upload de uma planta
    """
    # Obtém a empresa do usuário logado
    empresa = request.user.empresa
    
    # Obtém o projeto
    projeto = get_object_or_404(Projeto, pk=projeto_id, empresa=empresa)
    
    if request.method == 'POST':
        form = ProjetoPlantaForm(request.POST, request.FILES)
        if form.is_valid():
            planta = form.save(commit=False)
            planta.projeto = projeto
            planta.save()
            
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                # Resposta para requisições AJAX
                return JsonResponse({
                    'success': True,
                    'planta': {
                        'id': planta.id,
                        'nome': planta.nome,
                        'tipo': planta.get_tipo_display(),
                        'url': planta.arquivo.url,
                    }
                })
            
            messages.success(request, 'Planta adicionada com sucesso.')
            return redirect('projetos:projeto_detail', pk=projeto.id)
    else:
        form = ProjetoPlantaForm()
    
    context = {
        'empresa': empresa,
        'projeto': projeto,
        'form': form,
    }
    return render(request, 'projetos/upload_planta.html', context)

@login_required
def upload_referencia(request, projeto_id):
    """
    View para fazer upload de uma referência
    """
    # Obtém a empresa do usuário logado
    empresa = request.user.empresa
    
    # Obtém o projeto
    projeto = get_object_or_404(Projeto, pk=projeto_id, empresa=empresa)
    
    if request.method == 'POST':
        form = ProjetoReferenciaForm(request.POST, request.FILES)
        if form.is_valid():
            referencia = form.save(commit=False)
            referencia.projeto = projeto
            referencia.save()
            
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                # Resposta para requisições AJAX
                return JsonResponse({
                    'success': True,
                    'referencia': {
                        'id': referencia.id,
                        'nome': referencia.nome,
                        'tipo': referencia.get_tipo_display(),
                        'url': referencia.arquivo.url,
                    }
                })
            
            messages.success(request, 'Referência adicionada com sucesso.')
            return redirect('projetos:projeto_detail', pk=projeto.id)
    else:
        form = ProjetoReferenciaForm()
    
    context = {
        'empresa': empresa,
        'projeto': projeto,
        'form': form,
    }
    return render(request, 'projetos/upload_referencia.html', context)

@login_required
@require_POST
def delete_planta(request, planta_id):
    """
    View para excluir uma planta
    """
    # Obtém a empresa do usuário logado
    empresa = request.user.empresa
    
    # Obtém a planta, garantindo que pertence a um projeto da mesma empresa
    planta = get_object_or_404(ProjetoPlanta, pk=planta_id, projeto__empresa=empresa)
    projeto_id = planta.projeto.id
    
    planta.delete()
    
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        # Resposta para requisições AJAX
        return JsonResponse({'success': True})
    
    messages.success(request, 'Planta excluída com sucesso.')
    return redirect('projetos:projeto_detail', pk=projeto_id)

@login_required
@require_POST
def delete_referencia(request, referencia_id):
    """
    View para excluir uma referência
    """
    # Obtém a empresa do usuário logado
    empresa = request.user.empresa
    
    # Obtém a referência, garantindo que pertence a um projeto da mesma empresa
    referencia = get_object_or_404(ProjetoReferencia, pk=referencia_id, projeto__empresa=empresa)
    projeto_id = referencia.projeto.id
    
    referencia.delete()
    
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        # Resposta para requisições AJAX
        return JsonResponse({'success': True})
    
    messages.success(request, 'Referência excluída com sucesso.')
    return redirect('projetos:projeto_detail', pk=projeto_id)


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
    if projeto.has_briefing:
        # Pega o briefing mais recente
        briefing = projeto.briefings.first()
        return redirect('cliente:briefing_etapa', projeto_id=projeto.id, etapa=briefing.etapa_atual)
    
    # Cria um novo briefing para o projeto
    from projetos.models import Briefing, BriefingValidacao
    
    briefing = Briefing.objects.create(
        projeto=projeto,
        nome_projeto=projeto.nome,
        orcamento=projeto.orcamento,
        feira=projeto.feira
    )
    
    # Cria as validações iniciais para o briefing
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

class ProjetoUpdateView(LoginRequiredMixin, UpdateView):
    model = Projeto
    form_class = ProjetoForm
    template_name = 'projetos/projeto_form.html'
    
    def get_queryset(self):
        # Filtra projetos da empresa do usuário logado
        return Projeto.objects.filter(empresa=self.request.user.empresa)
    
    def form_valid(self, form):
        self.object = form.save()
        messages.success(self.request, 'Projeto atualizado com sucesso!')
        return redirect('projetos:projeto_detail', pk=self.object.id)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['empresa'] = self.request.user.empresa
        context['projeto'] = self.object
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