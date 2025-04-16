# gestor/views/projeto.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from core.models import Usuario, Empresa
from projetos.models import Projeto, ProjetoReferencia
from projetos.models.briefing import Briefing, BriefingConversation, BriefingValidacao, BriefingArquivoReferencia

@login_required
def projeto_list(request):
    """
    Lista de todos os projetos para o gestor
    """
    projetos_list = Projeto.objects.all().order_by('-created_at')
    
    status = request.GET.get('status')
    empresa_id = request.GET.get('empresa')
    
    if status:
        projetos_list = projetos_list.filter(status=status)
    if empresa_id:
        projetos_list = projetos_list.filter(empresa_id=empresa_id)
    
    paginator = Paginator(projetos_list, 10)
    page = request.GET.get('page', 1)
    
    try:
        projetos = paginator.page(page)
    except PageNotAnInteger:
        projetos = paginator.page(1)
    except EmptyPage:
        projetos = paginator.page(paginator.num_pages)
    
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
    projetistas = Usuario.objects.filter(nivel='projetista', is_active=True).order_by('username')
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

@login_required
def ver_briefing(request, projeto_id):
    """
    Permite ao gestor visualizar o briefing de um projeto
    """
    projeto = get_object_or_404(Projeto, pk=projeto_id)
    
    try:
        briefing = Briefing.objects.get(projeto=projeto)
    except Briefing.DoesNotExist:
        messages.error(request, 'Este projeto não possui um briefing.')
        return redirect('gestor:projeto_detail', pk=projeto_id)
    
    validacoes = BriefingValidacao.objects.filter(briefing=briefing)
    arquivos = BriefingArquivoReferencia.objects.filter(briefing=briefing)
    conversas = BriefingConversation.objects.filter(briefing=briefing).order_by('timestamp')
    
    context = {
        'projeto': projeto,
        'briefing': briefing,
        'validacoes': validacoes,
        'arquivos': arquivos,
        'conversas': conversas,
        'todas_aprovadas': all(v.status == 'aprovado' for v in validacoes),
    }
    
    return render(request, 'gestor/ver_briefing.html', context)

@login_required
@require_POST
def aprovar_briefing(request, projeto_id):
    """
    Aprova o briefing de um projeto
    """
    projeto = get_object_or_404(Projeto, pk=projeto_id)
    
    try:
        briefing = Briefing.objects.get(projeto=projeto)
    except Briefing.DoesNotExist:
        messages.error(request, 'Este projeto não possui um briefing.')
        return redirect('gestor:projeto_detail', pk=projeto_id)
    
    briefing.status = 'aprovado'
    briefing.save()
    
    projeto.briefing_status = 'aprovado'
    projeto.status = 'ativo'
    projeto.save()
    
    comentario = request.POST.get('comentario', '')
    if comentario:
        BriefingConversation.objects.create(
            briefing=briefing,
            mensagem=f"Briefing aprovado: {comentario}",
            origem='gestor',
            etapa=briefing.etapa_atual
        )
    
    messages.success(request, f'Briefing do projeto "{projeto.nome}" aprovado com sucesso!')
    return redirect('gestor:projeto_detail', pk=projeto_id)

@login_required
@require_POST
def reprovar_briefing(request, projeto_id):
    """
    Reprova o briefing de um projeto e solicita ajustes
    """
    projeto = get_object_or_404(Projeto, pk=projeto_id)
    
    try:
        briefing = Briefing.objects.get(projeto=projeto)
    except Briefing.DoesNotExist:
        messages.error(request, 'Este projeto não possui um briefing.')
        return redirect('gestor:projeto_detail', pk=projeto_id)
    
    comentario = request.POST.get('comentario', '')
    if not comentario:
        messages.error(request, 'É necessário informar os motivos da reprovação.')
        return redirect('gestor:ver_briefing', projeto_id=projeto_id)
    
    briefing.status = 'revisao'
    briefing.save()
    
    projeto.briefing_status = 'reprovado'
    projeto.save()
    
    BriefingConversation.objects.create(
        briefing=briefing,
        mensagem=f"Solicitação de ajustes: {comentario}",
        origem='gestor',
        etapa=briefing.etapa_atual
    )
    
    messages.warning(request, f'Foram solicitados ajustes no briefing do projeto "{projeto.nome}".')
    return redirect('gestor:projeto_detail', pk=projeto_id)

@login_required
@require_POST
def upload_arquivo(request, projeto_id):
    """
    Faz upload de um arquivo para um projeto
    """
    projeto = get_object_or_404(Projeto, pk=projeto_id)
    
    if 'arquivo' not in request.FILES:
        messages.error(request, 'Nenhum arquivo foi enviado.')
        return redirect('gestor:projeto_detail', pk=projeto_id)
    
    arquivo = request.FILES['arquivo']
    tipo = request.POST.get('tipo', 'outro')
    descricao = request.POST.get('descricao', '')
    
    novo_arquivo = ArquivoReferencia.objects.create(
        projeto=projeto,
        nome=arquivo.name,
        arquivo=arquivo,
        tipo=tipo,
        descricao=descricao,
        uploaded_by=request.user
    )
    
    messages.success(request, f'Arquivo "{arquivo.name}" enviado com sucesso.')
    return redirect('gestor:projeto_detail', pk=projeto_id)

@login_required
@require_POST
def excluir_arquivo(request, arquivo_id):
    """
    Exclui um arquivo de referência
    """
    arquivo = get_object_or_404(ArquivoReferencia, pk=arquivo_id)
    
    if request.user.nivel not in ['admin', 'gestor']:
        return JsonResponse({'success': False, 'error': 'Permissão negada'}, status=403)
    
    projeto_id = arquivo.projeto.id
    arquivo.delete()
    
    return JsonResponse({'success': True})

@login_required
def mensagens(request):
    """
    Central de mensagens do gestor
    """
    projetos = Projeto.objects.all().order_by('-updated_at')
    
    conversas = [
        {
            'projeto': projeto,
            'cliente': projeto.cliente,
            'empresa': projeto.empresa,
            'ultima_mensagem': f"Últimas atualizações sobre {projeto.nome}",
            'data': projeto.updated_at,
            'nao_lidas': 0
        } for projeto in projetos[:5]
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
    projetos = Projeto.objects.all().order_by('-updated_at')
    
    if request.method == 'POST':
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
    projeto = get_object_or_404(Projeto, pk=projeto_id)
    
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

@login_required
def feira_qa_progress(request, pk):
    try:
        feira = Feira.objects.get(pk=pk)
        return JsonResponse({
            'success': True,
            'progress': feira.qa_progresso_processamento if hasattr(feira, 'qa_progresso_processamento') else 0,
            'status': feira.qa_processamento_status if hasattr(feira, 'qa_processamento_status') else 'pendente',
            'message': feira.qa_mensagem_erro if hasattr(feira, 'qa_mensagem_erro') else None,
            'processed': feira.qa_processado if hasattr(feira, 'qa_processado') else False,
            'total_qa': FeiraManualQA.objects.filter(feira=feira).count()
        })
    except Feira.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Feira não encontrada'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False, 
            'error': str(e)
        }, status=500)