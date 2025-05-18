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
    com suporte para visualizar versões específicas e informações detalhadas
    """
    # Verificar se o projeto pertence ao projetista logado
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
    arquivos = list(BriefingArquivoReferencia.objects.filter(briefing=briefing))
    conversas = BriefingConversation.objects.filter(briefing=briefing).order_by('timestamp')
    
    # Extrair arquivos específicos para uso direto no template
    mapa_arquivo = next((a for a in arquivos if a.tipo == 'mapa'), None)
    planta_arquivos = [a for a in arquivos if a.tipo == 'planta']
    referencia_arquivos = [a for a in arquivos if a.tipo == 'referencia']
    campanha_arquivos = [a for a in arquivos if a.tipo == 'campanha']
    outros_arquivos = [a for a in arquivos if a.tipo not in ('mapa', 'planta', 'referencia', 'campanha')]
    
    # Obter dados para as áreas específicas do estande
    # Estamos usando hasattr para verificar se o modelo possui esses relacionamentos
    areas_exposicao = list(briefing.areas_exposicao.all()) if hasattr(briefing, 'areas_exposicao') else []
    salas_reuniao = list(briefing.salas_reuniao.all()) if hasattr(briefing, 'salas_reuniao') else []
    copas = list(briefing.copas.all()) if hasattr(briefing, 'copas') else []
    depositos = list(briefing.depositos.all()) if hasattr(briefing, 'depositos') else []
    
    # Dados específicos da feira (caso exista)
    # Priorizamos a feira do briefing, depois a feira do projeto
    feira = None
    if hasattr(briefing, 'feira') and briefing.feira:
        feira = briefing.feira
    elif hasattr(projeto, 'feira') and projeto.feira:
        feira = projeto.feira

    context = {
        'projeto': projeto,
        'briefing': briefing,
        'briefings': briefings,  # Todas as versões
        'validacoes': validacoes,
        'arquivos': arquivos,  # Lista completa de arquivos
        'mapa_arquivo': mapa_arquivo,  # Arquivo de mapa específico
        'planta_arquivos': planta_arquivos,  # Arquivos de planta
        'referencia_arquivos': referencia_arquivos,  # Arquivos de referência
        'campanha_arquivos': campanha_arquivos,  # Arquivos de campanha
        'outros_arquivos': outros_arquivos,  # Outros tipos de arquivo
        'conversas': conversas,
        'areas_exposicao': areas_exposicao,
        'salas_reuniao': salas_reuniao,
        'copas': copas,
        'depositos': depositos,
        'feira': feira,
        'todas_aprovadas': all(v.status == 'aprovado' for v in validacoes),
        'from_page': 'projetista',  # Indicador da origem para o template
    }
    
    return render(request, 'projetista/ver_briefing.html', context)
