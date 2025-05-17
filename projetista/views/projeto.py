# projetista/views/projeto.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import JsonResponse
from django.db.models import Q
from django.utils import timezone

from core.models import Usuario, Empresa
from projetos.models import (
    Projeto, Briefing, BriefingConversation, BriefingValidacao, BriefingArquivoReferencia
)

# Vamos importar o modelo ConceitoVisual do app projetista, se ele existir
try:
    from projetista.models import ConceitoVisual
except ImportError:
    # Se o modelo não existir, vamos criar uma classe temporária para fins de desenvolvimento
    # Esta classe não será usada para persistência, apenas para evitar erros durante o desenvolvimento
    class ConceitoVisual:
        objects = type('MockManager', (), {
            'get': lambda *args, **kwargs: None,
            'filter': lambda *args, **kwargs: [],
            'create': lambda *args, **kwargs: None
        })()
        
        class DoesNotExist(Exception):
            pass

@login_required
def projeto_list(request):
    """
    Lista de projetos atribuídos ao projetista logado
    """
    # Filtrar apenas projetos atribuídos ao projetista atual
    projetos_list = Projeto.objects.filter(projetista=request.user).order_by('-created_at')
    
    # Filtros
    status = request.GET.get('status')
    empresa_id = request.GET.get('empresa')
    search = request.GET.get('search')
    
    if status:
        projetos_list = projetos_list.filter(status=status)
    if empresa_id:
        projetos_list = projetos_list.filter(empresa_id=empresa_id)
    if search:
        projetos_list = projetos_list.filter(
            Q(nome__icontains=search) | 
            Q(numero__icontains=search) |
            Q(empresa__nome__icontains=search)
        )
    
    # Paginação
    paginator = Paginator(projetos_list, 10)
    page = request.GET.get('page', 1)
    
    try:
        projetos = paginator.page(page)
    except PageNotAnInteger:
        projetos = paginator.page(1)
    except EmptyPage:
        projetos = paginator.page(paginator.num_pages)
    
    # Opções de filtro
    empresas = Empresa.objects.filter(projetos__projetista=request.user).distinct().order_by('nome')
    
    # Status disponíveis (alinhados com o novo modelo)
    status_choices = Projeto.STATUS_CHOICES
    
    context = {
        'projetos': projetos,
        'empresas': empresas,
        'status_choices': status_choices,
        'status_escolhido': status,
        'empresa_escolhida': empresa_id,
        'search_query': search,
    }
    
    return render(request, 'projetista/projeto_list.html', context)

@login_required
def projeto_detail(request, pk):
    """
    Detalhes de um projeto específico atribuído ao projetista
    """
    projeto = get_object_or_404(Projeto, pk=pk, projetista=request.user)
    
    # Obter informações mais detalhadas
    briefings = projeto.briefings.all().order_by('-versao')
    marcos = projeto.marcos.all().order_by('-data')
    mensagens = projeto.mensagens.all().order_by('-data_envio')[:5]  # Últimas 5 mensagens
    plantas = projeto.plantas.all()
    referencias = projeto.referencias.all()
    
    # Verificar se existe conceito visual
    tem_conceito = False
    if hasattr(projeto, 'conceitos_visuais'):
        tem_conceito = projeto.conceitos_visuais.exists()
    
    context = {
        'projeto': projeto,
        'briefings': briefings,
        'marcos': marcos,
        'mensagens': mensagens,
        'plantas': plantas,
        'referencias': referencias,
        'tem_conceito': tem_conceito,
    }
    
    return render(request, 'projetista/projeto_detail.html', context)

@login_required
def ver_briefing(request, projeto_id, versao=None):
    """
    Permite ao projetista visualizar o briefing de um projeto,
    com suporte para visualizar versões específicas
    """
    projeto = get_object_or_404(Projeto, pk=projeto_id, projetista=request.user)
    
    # Buscar todas as versões do briefing
    briefings = projeto.briefings.all().order_by('-versao')
    
    if not briefings.exists():
        messages.error(request, 'Este projeto não possui um briefing.')
        return redirect('projetista:projeto_detail', pk=projeto_id)
    
    # Processar seleção de versão específica se informada
    if versao is None and request.GET.get('versao'):
        try:
            versao = int(request.GET.get('versao'))
        except ValueError:
            versao = None
    
    # Se não especificou versão ou versão é inválida, pega a mais recente
    if versao is None:
        briefing = briefings.first()
    else:
        briefing = get_object_or_404(Briefing, projeto=projeto, versao=versao)
    
    # Obtenha as validações, arquivos e conversas
    validacoes = BriefingValidacao.objects.filter(briefing=briefing)
    arquivos = BriefingArquivoReferencia.objects.filter(briefing=briefing)
    conversas = BriefingConversation.objects.filter(briefing=briefing).order_by('timestamp')
    
    # Para os dados de áreas do estande
    areas_exposicao = briefing.areas_exposicao.all() if hasattr(briefing, 'areas_exposicao') else []
    salas_reuniao = briefing.salas_reuniao.all() if hasattr(briefing, 'salas_reuniao') else []
    copas = briefing.copas.all() if hasattr(briefing, 'copas') else []
    depositos = briefing.depositos.all() if hasattr(briefing, 'depositos') else []

    context = {
        'projeto': projeto,
        'briefing': briefing,
        'briefings': briefings,  # Todas as versões
        'validacoes': validacoes,
        'arquivos': arquivos,
        'conversas': conversas,
        'areas_exposicao': areas_exposicao,
        'salas_reuniao': salas_reuniao,
        'copas': copas,
        'depositos': depositos,
        'todas_aprovadas': all(v.status == 'aprovado' for v in validacoes),
    }
    
    return render(request, 'projetista/ver_briefing.html', context)

@login_required
def gerar_conceito(request, projeto_id):
    """
    Permite ao projetista gerar um conceito visual baseado no briefing
    """
    projeto = get_object_or_404(Projeto, pk=projeto_id, projetista=request.user)
    briefing = projeto.briefings.latest('versao')
    
    # Verificar se já existe um conceito (adaptado para funcionar sem o modelo concreto)
    conceito = None
    form_data = {}
    
    # Esta parte seria executada apenas se o modelo ConceitoVisual existir
    if hasattr(ConceitoVisual, 'objects') and not isinstance(ConceitoVisual.objects, type):
        try:
            conceito = ConceitoVisual.objects.filter(briefing=briefing).first()
            if conceito:
                form_data = {
                    'descricao': conceito.descricao,
                    'referencias_utilizadas': conceito.referencias_utilizadas
                }
        except:
            # Se ocorrer qualquer erro, simplesmente continuamos com conceito=None
            pass
    
    context = {
        'projeto': projeto,
        'briefing': briefing,
        'conceito': conceito,
        'form_data': form_data,
        'arquivos': BriefingArquivoReferencia.objects.filter(briefing=briefing),
    }
    
    return render(request, 'projetista/gerar_conceito.html', context)

@login_required
def salvar_conceito(request, projeto_id):
    """
    Salva o conceito visual gerado pelo projetista
    """
    projeto = get_object_or_404(Projeto, pk=projeto_id, projetista=request.user)
    briefing = projeto.briefings.latest('versao')
    
    if request.method == 'POST':
        # Obter dados do formulário
        descricao = request.POST.get('descricao', '')
        referencias_utilizadas = request.POST.get('referencias_utilizadas', '')
        
        # Aqui seria o código para salvar o conceito, mas isso requer o modelo
        # No momento, apenas simulamos o comportamento
        
        # Comentando o código que depende do modelo ConceitoVisual
        """
        try:
            conceito = ConceitoVisual.objects.get(briefing=briefing)
            conceito.descricao = descricao
            conceito.referencias_utilizadas = referencias_utilizadas
            conceito.atualizado_em = timezone.now()
        except ConceitoVisual.DoesNotExist:
            conceito = ConceitoVisual(
                briefing=briefing,
                projeto=projeto,
                projetista=request.user,
                descricao=descricao,
                referencias_utilizadas=referencias_utilizadas
            )
        
        # Salvar o conceito
        conceito.save()
        
        # Processar arquivos de imagem de conceito
        for arquivo in request.FILES.getlist('imagens_conceito'):
            # Adicionar lógica para salvar os arquivos de conceito
            pass
        """
        
        messages.success(request, 'Conceito visual salvo com sucesso! (Simulado)')
        return redirect('projetista:projeto_detail', pk=projeto.pk)
    
    return redirect('projetista:gerar_conceito', projeto_id=projeto.pk)