# gestor/views/projeto.py

# - projeto_list
# - projeto_detail
# - projeto_alterar_status
# - projeto_atribuir
# - ver_briefing

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db.models import Q

from core.models import Usuario, Empresa, Feira, FeiraManualQA
from projetos.models import (
    Projeto, ProjetoReferencia, ProjetoMarco, 
    Mensagem, AnexoMensagem,
    Briefing, BriefingConversation, BriefingValidacao, BriefingArquivoReferencia
)

@login_required
def projeto_list(request):
    """
    Lista de todos os projetos para o gestor com filtros avançados
    """
    projetos_list = Projeto.objects.all().order_by('-created_at')
    
    # Filtros aprimorados
    status = request.GET.get('status')
    empresa_id = request.GET.get('empresa')
    feira_id = request.GET.get('feira')
    search = request.GET.get('search')
    
    if status:
        projetos_list = projetos_list.filter(status=status)
    if empresa_id:
        projetos_list = projetos_list.filter(empresa_id=empresa_id)
    if feira_id:
        projetos_list = projetos_list.filter(feira_id=feira_id)
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
    empresas = Empresa.objects.all().order_by('nome')
    feiras = Feira.objects.filter(ativa=True).order_by('-data_inicio')
    
    # Status disponíveis (alinhados com o novo modelo)
    status_choices = Projeto.STATUS_CHOICES
    
    context = {
        'projetos': projetos,
        'empresas': empresas,
        'feiras': feiras,
        'status_choices': status_choices,
        'status_escolhido': status,
        'empresa_escolhida': empresa_id,
        'feira_escolhida': feira_id,
        'search_query': search,
    }
    
    return render(request, 'gestor/projeto_list.html', context)

@login_required
def projeto_detail(request, pk):
    """
    Detalhes de um projeto específico
    """
    projeto = get_object_or_404(Projeto, pk=pk)
    
    projetistas = Usuario.objects.filter(nivel='projetista', is_active=True).order_by('username')
    
    # Obter informações mais detalhadas
    briefings = projeto.briefings.all().order_by('-versao')
    marcos = projeto.marcos.all().order_by('-data')
    mensagens = projeto.mensagens.all().order_by('-data_envio')[:5]  # Últimas 5 mensagens
    plantas = projeto.plantas.all()
    referencias = projeto.referencias.all()
    
    context = {
        'projeto': projeto,
        'projetistas': projetistas,
        'briefings': briefings,
        'marcos': marcos,
        'mensagens': mensagens,
        'plantas': plantas,
        'referencias': referencias,
    }
    
    return render(request, 'gestor/projeto_detail.html', context)

@login_required
def projeto_alterar_status(request, pk):
    """
    Alterar o status de um projeto e registrar o marco correspondente
    """
    projeto = get_object_or_404(Projeto, pk=pk)
    
    if request.method == 'POST':
        novo_status = request.POST.get('status')
        observacao = request.POST.get('observacao', '')
        
        if novo_status in [s[0] for s in Projeto.STATUS_CHOICES]:
            status_antigo = projeto.status
            projeto.status = novo_status
            projeto.save()
            
            # Mapeia status para tipos de marco
            status_marco_map = {
                'briefing_validado': 'validacao_briefing',
                'projeto_em_desenvolvimento': 'inicio_desenvolvimento',
                'projeto_enviado': 'envio_projeto',
                'projeto_em_analise': 'analise_projeto',
                'projeto_aprovado': 'aprovacao_projeto',
                'em_producao': 'inicio_producao',
                'concluido': 'entrega_estande',
                'cancelado': 'cancelamento',
            }
            
            # Se o status mapeia para um marco, cria o registro
            if novo_status in status_marco_map:
                ProjetoMarco.objects.create(
                    projeto=projeto,
                    tipo=status_marco_map[novo_status],
                    observacao=observacao or f'Status alterado de {status_antigo} para {novo_status}',
                    registrado_por=request.user
                )
            
            # Atualiza métricas do projeto
            projeto.atualizar_metricas()
            
            messages.success(request, f'Status do projeto alterado para {projeto.get_status_display()} com sucesso.')
        else:
            messages.error(request, 'Status inválido.')
        
    return redirect('gestor:projeto_detail', pk=projeto.pk)

@login_required
def projeto_atribuir(request, pk, usuario_id):
    """
    Atribuir ou desatribuir um projetista a um projeto
    """
    projeto = get_object_or_404(Projeto, pk=pk)
    
    if usuario_id == 0:
        # Desatribuir projetista
        projetista_antigo = projeto.projetista
        projeto.projetista = None
        projeto.save()
        
        messages.success(request, f'Projetista removido com sucesso.')
    else:
        # Atribuir projetista
        projetista = get_object_or_404(Usuario, pk=usuario_id, nivel='projetista')
        
        # Verificar se é uma alteração de projetista
        foi_alteracao = projeto.projetista is not None and projeto.projetista != projetista
        
        projeto.projetista = projetista
        projeto.save()
        
        if foi_alteracao:
            messages.success(request, f'Projetista alterado para {projetista.get_full_name() or projetista.username} com sucesso.')
        else:
            messages.success(request, f'Projetista {projetista.get_full_name() or projetista.username} atribuído com sucesso.')
    
    return redirect('gestor:projeto_detail', pk=projeto.pk)

    
@login_required
def ver_briefing(request, projeto_id, versao=None):

    projeto = get_object_or_404(Projeto, pk=projeto_id)
        
    # Buscar todas as versões do briefing
    briefings = projeto.briefings.all().order_by('-versao')
    
    if not briefings.exists():
        messages.error(request, 'Este projeto não possui um briefing.')
        return redirect('gestor:projeto_detail', pk=projeto_id)
    
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
    areas_exposicao = list(briefing.areas_exposicao.all()) if hasattr(briefing, 'areas_exposicao') else []
    salas_reuniao = list(briefing.salas_reuniao.all()) if hasattr(briefing, 'salas_reuniao') else []
    copas = list(briefing.copas.all()) if hasattr(briefing, 'copas') else []
    depositos = list(briefing.depositos.all()) if hasattr(briefing, 'depositos') else []
    
    # Dados específicos da feira (caso exista)
    feira = None
    if hasattr(briefing, 'feira') and briefing.feira:
        feira = briefing.feira
    elif hasattr(projeto, 'feira') and projeto.feira:
        feira = projeto.feira
    
    # Adicionar informações específicas para o gestor
    projetista_info = None
    if projeto.projetista:
        projetista_info = {
            'nome': projeto.projetista.get_full_name() or projeto.projetista.username,
            'email': projeto.projetista.email,
            'telefone': projeto.projetista.telefone if hasattr(projeto.projetista, 'telefone') else None,
        }
    
    # Informações adicionais relevantes para gestão
    info_gestao = {
        'data_criacao': projeto.created_at,
        'data_ultima_atualizacao': projeto.updated_at,
        'data_envio_briefing': projeto.data_envio_briefing,
        'orcamento': briefing.orcamento,
        'data_limite': projeto.data_limite_entrega if hasattr(projeto, 'data_limite_entrega') else None,
    }

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
        'projetista_info': projetista_info,  # Informação adicional para gestores
        'info_gestao': info_gestao,  # Informações de gestão adicionais
        'from_page': 'gestor',  # Indicador da origem para o template
    }
    
    return render(request, 'gestor/ver_briefing.html', context)