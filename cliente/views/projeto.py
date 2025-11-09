# clientes/views/projeto.py
#
# Views neste arquivo:
# - projeto_list
# - projeto_detail
# - projeto_create
# - projeto_update
# - projeto_delete
# - aprovar_projeto
# - selecionar_feira
# - verificar_manual_feira
# - processar_upload_manual
# - ProjetoListView
# - ProjetoDetailView
# - ProjetoCreateView
# - ProjetoUpdateView
# - ProjetoDeleteView

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
    projetos_list = Projeto.objects.filter(empresa=empresa).select_related('feira').order_by('-created_at')
    
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
    return render(request, 'cliente/projeto_list.html', context)

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
def projeto_create(request):
    """
    View para criar um novo projeto
    """
    empresa = request.user.empresa

    if request.method == 'POST':
        # CORREÇÃO: Passar a empresa para o formulário
        form = ProjetoForm(request.POST, empresa=empresa)
        if form.is_valid():
            projeto = form.save(commit=False)
            projeto.empresa = empresa
            projeto.criado_por = request.user

            # Define status inicial centralizado
            projeto.definir_status_inicial()

            projeto.save()

            # Cria um marco para registrar a criação do projeto
            ProjetoMarco.objects.create(
                projeto=projeto,
                tipo='criacao_projeto',
                observacao='Projeto criado pelo cliente',
                registrado_por=request.user
            )

            messages.success(request, 'Projeto criado com sucesso!')

            if projeto.tipo_projeto == 'feira_negocios' and not projeto.feira:
                messages.warning(request, 'Você não selecionou uma feira. Por favor, envie o manual do expositor da feira pelo sistema de mensagens.')

            return redirect('cliente:projeto_detail', pk=projeto.id)

    else:
        # CORREÇÃO: Passar a empresa para o formulário também no GET
        form = ProjetoForm(
            initial={'tipo_projeto': 'feira_negocios'},
            empresa=empresa
        )

    return render(request, 'cliente/projeto_form.html', {
        'empresa': empresa,
        'form': form,
    })

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
        # CORREÇÃO: Passar a empresa para o formulário
        form = ProjetoForm(request.POST, instance=projeto, empresa=empresa)
        if form.is_valid():
            projeto_atualizado = form.save(commit=False)
            
            # Atualiza o nome baseado no tipo de projeto e feira
            if projeto_atualizado.tipo_projeto == 'feira_negocios' and projeto_atualizado.feira:
                projeto_atualizado.nome = projeto_atualizado.feira.nome
                
            # Atualiza o status se mudar a feira em um projeto aguardando manual
            if projeto.status == 'aguardando_manual' and projeto_atualizado.feira:
                projeto_atualizado.status = 'briefing_pendente'
            # Se remover a feira de um projeto de feira, muda para aguardando manual
            elif projeto_atualizado.tipo_projeto == 'feira_negocios' and not projeto_atualizado.feira and projeto.feira:
                projeto_atualizado.status = 'aguardando_manual'
            
            projeto_atualizado.save()
            
            # Mensagem específica para projeto de feira sem feira
            if projeto_atualizado.tipo_projeto == 'feira_negocios' and not projeto_atualizado.feira:
                messages.warning(request, 'Você não selecionou uma feira. Por favor, envie o manual do expositor da feira pelo sistema de mensagens.')
            else:
                messages.success(request, 'Projeto atualizado com sucesso.')
                
            return redirect('cliente:projeto_detail', pk=projeto.pk)
    else:
        # CORREÇÃO: Passar a empresa para o formulário também no GET
        form = ProjetoForm(instance=projeto, empresa=empresa)
    
    context = {
        'empresa': empresa,
        'projeto': projeto,
        'form': form,
    }
    return render(request, 'cliente/projeto_form.html', context)

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
        return redirect('cliente:projeto_list')
    
    context = {
        'empresa': empresa,
        'projeto': projeto,
    }
    return render(request, 'cliente/projeto_confirm_delete.html', context)

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
            # Se o status for 'aguardando_manual', atualiza para 'briefing_pendente'
            if projeto.status == 'aguardando_manual':
                projeto.status = 'briefing_pendente'
            projeto.save()
            
            messages.success(request, f'Feira "{feira.nome}" selecionada com sucesso!')
            return redirect('cliente:projeto_detail', pk=projeto.id)
        else:
            messages.error(request, 'Por favor, selecione uma feira.')
    
    context = {
        'empresa': empresa,
        'projeto': projeto,
        'feiras': feiras,
    }
    return render(request, 'cliente/selecionar_feira.html', context)

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
    return render(request, 'cliente/verificar_manual.html', context)

@login_required
def processar_upload_manual(request, projeto_id):
    """
    View para processar o upload do manual do expositor
    e atualizar o status do projeto
    """
    # Obtém a empresa do usuário logado
    empresa = request.user.empresa
    
    # Obtém o projeto
    projeto = get_object_or_404(Projeto, pk=projeto_id, empresa=empresa)
    
    if request.method == 'POST' and 'manual' in request.FILES:
        arquivo = request.FILES['manual']
        
        # Criar uma mensagem com o arquivo anexado
        from projetos.models import ProjetoMensagem
        
        mensagem = ProjetoMensagem.objects.create(
            projeto=projeto,
            remetente=request.user,
            destinatario=None,  # Destinado à equipe interna
            assunto="Manual do Expositor",
            mensagem="Segue o manual do expositor para análise e cadastro da feira.",
            arquivo=arquivo,
            arquivo_nome=arquivo.name
        )
        
        # Atualizar o status do projeto se estava aguardando manual
        if projeto.status == 'aguardando_manual':
            # Definir para briefing_pendente e salvar
            projeto.status = 'briefing_pendente'
            projeto.save(update_fields=['status'])
            
            messages.success(request, 'Manual enviado com sucesso! O status do projeto foi atualizado para Briefing Pendente.')
        else:
            messages.success(request, 'Manual enviado com sucesso!')
            
        return redirect('cliente:projeto_detail', pk=projeto.id)
        
    messages.error(request, 'Nenhum arquivo foi enviado.')
    return redirect('cliente:mensagens_projeto', projeto_id=projeto.id)


class ProjetoListView(LoginRequiredMixin, ListView):
    model = Projeto
    template_name = 'cliente/projeto_list.html'  # CORRIGIDO
    context_object_name = 'projetos'
    paginate_by = 10
    
    def get_queryset(self):
        # Filtra projetos da empresa do usuário logado
        queryset = Projeto.objects.filter(empresa=self.request.user.empresa).select_related('feira').order_by('-created_at')
        
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
    template_name = 'cliente/projeto_detail.html'  # CORRIGIDO
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
    template_name = 'cliente/projeto_form.html'  # CORRIGIDO

    def get_form_kwargs(self):
        # CORREÇÃO: Adicionar empresa aos kwargs do formulário
        kwargs = super().get_form_kwargs()
        kwargs['empresa'] = self.request.user.empresa
        return kwargs

    def form_valid(self, form):
        form.instance.empresa = self.request.user.empresa
        form.instance.criado_por = self.request.user

        # Aplica lógica centralizada de status
        form.instance.definir_status_inicial()

        self.object = form.save()

        if self.object.tipo_projeto == 'feira_negocios' and not self.object.feira:
            messages.warning(self.request, 'Você não selecionou uma feira. Por favor, envie o manual do expositor da feira pelo sistema de mensagens.')
        else:
            messages.success(self.request, 'Projeto criado com sucesso!')

        return redirect('cliente:projeto_detail', pk=self.object.id)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['empresa'] = self.request.user.empresa
        return context

class ProjetoUpdateView(LoginRequiredMixin, UpdateView):
    model = Projeto
    form_class = ProjetoForm
    template_name = 'cliente/projeto_form.html'  # CORRIGIDO
    
    def get_queryset(self):
        # Filtra projetos da empresa do usuário logado
        return Projeto.objects.filter(empresa=self.request.user.empresa)
    
    def get_form_kwargs(self):
        # CORREÇÃO: Adicionar empresa aos kwargs do formulário
        kwargs = super().get_form_kwargs()
        kwargs['empresa'] = self.request.user.empresa
        return kwargs
    
    def form_valid(self, form):
        projeto = form.save(commit=False)
        
        # Atualiza o nome baseado no tipo de projeto e feira
        if projeto.tipo_projeto == 'feira_negocios' and projeto.feira:
            projeto.nome = projeto.feira.nome
            
        # Atualiza o status se mudar a feira em um projeto aguardando manual
        if projeto.status == 'aguardando_manual' and projeto.feira:
            projeto.status = 'briefing_pendente'
        # Se remover a feira de um projeto de feira, muda para aguardando manual
        elif projeto.tipo_projeto == 'feira_negocios' and not projeto.feira and self.object.feira:
            projeto.status = 'aguardando_manual'
            
        projeto.save()
        
        # Mensagem específica para projeto de feira sem feira
        if projeto.tipo_projeto == 'feira_negocios' and not projeto.feira:
            messages.warning(self.request, 'Você não selecionou uma feira. Por favor, envie o manual do expositor da feira pelo sistema de mensagens.')
        else:
            messages.success(self.request, 'Projeto atualizado com sucesso!')
            
        return redirect('cliente:projeto_detail', pk=self.object.id)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['empresa'] = self.request.user.empresa
        context['projeto'] = self.object
        return context

class ProjetoDeleteView(LoginRequiredMixin, DeleteView):
    model = Projeto
    template_name = 'cliente/projeto_confirm_delete.html'  # CORRIGIDO
    success_url = reverse_lazy('cliente:projeto_list')  # CORRIGIDO
    
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