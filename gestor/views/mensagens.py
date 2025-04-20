# gestor/views/mensagens.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib import messages as django_messages
from django.db.models import Q, Count, Max, F
from django.utils import timezone

from projetos.models.projeto import Projeto
from core.models import Mensagem, AnexoMensagem, Usuario

@login_required
def mensagens(request):
    """Exibe a central de mensagens para o gestor."""
    # Obtém todos os projetos com mensagens para o gestor
    conversas = Projeto.objects.annotate(
        ultima_mensagem=Max('mensagens__data_envio'),
        mensagens_nao_lidas=Count('mensagens', filter=Q(mensagens__lida=False) & 
                                 Q(mensagens__destinatario=request.user))
    ).filter(
        # Inclui projetos onde o gestor é destinatário de pelo menos uma mensagem
        Q(mensagens__destinatario=request.user) | 
        # Ou projetos onde o gestor enviou mensagens
        Q(mensagens__remetente=request.user)
    ).filter(
        # Garante que o projeto tenha mensagens
        ultima_mensagem__isnull=False
    ).distinct().order_by('-ultima_mensagem')
    
    # Se um projeto estiver selecionado, mostra suas mensagens
    projeto_id = request.GET.get('projeto_id')
    mensagens_lista = None
    projeto_atual = None
    
    if projeto_id:
        projeto_atual = get_object_or_404(Projeto, id=projeto_id)
        mensagens_lista = Mensagem.objects.filter(
            projeto=projeto_atual
        ).filter(
            # Mensagens onde o gestor é destinatário ou remetente
            Q(destinatario=request.user) | Q(remetente=request.user)
        ).order_by('data_envio')
        
        # Marca mensagens como lidas
        mensagens_lista.filter(
            destinatario=request.user, 
            lida=False
        ).update(lida=True)
    
    # Contexto para o template
    context = {
        'conversas': conversas,
        'mensagens': mensagens_lista,
        'projeto_atual': projeto_atual,
        'today_date': timezone.now().strftime('%Y-%m-%d'),
        'yesterday_date': (timezone.now() - timezone.timedelta(days=1)).strftime('%Y-%m-%d'),
    }
    
    return render(request, 'gestor/central_mensagens.html', context)

@login_required
def nova_mensagem(request):
    """Formulário para envio de nova mensagem pelo gestor."""
    if request.method == 'POST':
        projeto_id = request.POST.get('projeto')
        conteudo = request.POST.get('mensagem')
        
        if projeto_id and conteudo:
            projeto = get_object_or_404(Projeto, id=projeto_id)
            
            # Criar a mensagem
            mensagem = Mensagem(
                projeto=projeto,
                remetente=request.user,
                conteudo=conteudo
            )
            
            # Determinar o destinatário correto
            # Por padrão é o cliente do projeto
            mensagem.destinatario = projeto.cliente
            mensagem.save()
            
            # Processar anexos
            for arquivo in request.FILES.getlist('anexos'):
                anexo = AnexoMensagem(
                    mensagem=mensagem,
                    arquivo=arquivo,
                    nome_original=arquivo.name,
                    tipo_arquivo=arquivo.content_type,
                    tamanho=arquivo.size
                )
                anexo.save()
            
            django_messages.success(request, 'Mensagem enviada com sucesso!')
            return redirect('gestor:mensagens')
    
    # Buscar projetos para o formulário
    projetos = Projeto.objects.all().order_by('-created_at')
    
    return render(request, 'gestor/nova_mensagem.html', {
        'projetos': projetos,
    })

@login_required
def mensagens_projeto(request, projeto_id):
    """Exibe e gerencia mensagens específicas de um projeto para o gestor."""
    projeto = get_object_or_404(Projeto, id=projeto_id)
    
    # Processar nova mensagem
    if request.method == 'POST':
        mensagem_texto = request.POST.get('mensagem')
        if mensagem_texto:
            mensagem = Mensagem(
                projeto=projeto,
                remetente=request.user,
                conteudo=mensagem_texto
            )
            
            # Definir o destinatário como o cliente do projeto
            mensagem.destinatario = projeto.cliente
            mensagem.save()
            
            # Processar anexos (se houver)
            for arquivo in request.FILES.getlist('anexos'):
                anexo = AnexoMensagem(
                    mensagem=mensagem,
                    arquivo=arquivo,
                    nome_original=arquivo.name,
                    tipo_arquivo=arquivo.content_type,
                    tamanho=arquivo.size
                )
                anexo.save()
    
    # Buscar todas as mensagens do projeto relacionadas ao gestor
    mensagens_lista = Mensagem.objects.filter(
        projeto=projeto
    ).filter(
        # Mensagens onde o gestor é destinatário ou remetente
        Q(destinatario=request.user) | Q(remetente=request.user)
    ).order_by('data_envio')
    
    # Marcar mensagens como lidas
    mensagens_lista.filter(
        destinatario=request.user, 
        lida=False
    ).update(lida=True)
    
    context = {
        'projeto': projeto,
        'mensagens': mensagens_lista,
        'today_date': timezone.now().strftime('%Y-%m-%d'),
        'yesterday_date': (timezone.now() - timezone.timedelta(days=1)).strftime('%Y-%m-%d'),
    }
    
    return render(request, 'gestor/mensagens_projeto.html', context)