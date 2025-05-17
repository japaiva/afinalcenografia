# projetista/views/mensagens.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib import messages as django_messages
from django.db.models import Q, Count, Max
from django.utils import timezone

from projetos.models import Mensagem, AnexoMensagem, Projeto
from core.models import Usuario, Empresa

@login_required
def mensagens(request):
    """Exibe a central de mensagens para o projetista."""
    # Buscar todos os projetos atribuídos ao projetista
    conversas = Projeto.objects.filter(projetista=request.user).annotate(
        ultima_mensagem=Max('mensagens__data_envio'),
        mensagens_nao_lidas=Count('mensagens', filter=Q(mensagens__lida=False) & ~Q(mensagens__remetente=request.user))
    ).filter(ultima_mensagem__isnull=False).order_by('-ultima_mensagem')
    
    # Filtro por cliente (empresa)
    empresa_id = request.GET.get('empresa_id')
    if empresa_id:
        conversas = conversas.filter(empresa_id=empresa_id)
    
    # Lista de empresas para o filtro
    empresas = Empresa.objects.filter(
        projetos__in=conversas
    ).distinct().order_by('nome')
    
    # Se um projeto estiver selecionado, mostra suas mensagens
    projeto_id = request.GET.get('projeto_id')
    mensagens_lista = None
    projeto_atual = None
    
    if projeto_id:
        projeto_atual = get_object_or_404(Projeto, id=projeto_id, projetista=request.user)
        mensagens_lista = Mensagem.objects.filter(projeto=projeto_atual).order_by('data_envio')
        
        # Marca mensagens como lidas
        mensagens_lista.filter(~Q(remetente=request.user), lida=False).update(lida=True)
    
    # Contexto para o template
    context = {
        'conversas': conversas,
        'mensagens': mensagens_lista,
        'projeto_atual': projeto_atual,
        'empresas': empresas,
        'empresa_filtro_id': empresa_id,
        'today_date': timezone.now().strftime('%Y-%m-%d'),
        'yesterday_date': (timezone.now() - timezone.timedelta(days=1)).strftime('%Y-%m-%d'),
    }
    
    return render(request, 'projetista/central_mensagens.html', context)

@login_required
def nova_mensagem(request):
    """Permite ao projetista criar uma nova mensagem."""
    if request.method == 'POST':
        projeto_id = request.POST.get('projeto')
        conteudo = request.POST.get('mensagem')
        
        if projeto_id and conteudo:
            projeto = get_object_or_404(Projeto, id=projeto_id, projetista=request.user)
            
            # Criar a mensagem
            mensagem = Mensagem(
                projeto=projeto,
                remetente=request.user,
                conteudo=conteudo
            )
            
            # Determinar o destinatário (algum cliente da empresa)
            destinatario = None
            
            # Verificar se o projeto tem um cliente que o criou
            if projeto.criado_por and projeto.criado_por.nivel == 'cliente':
                destinatario = projeto.criado_por
            else:
                # Buscar algum usuário cliente da empresa
                destinatario = Usuario.objects.filter(
                    empresa=projeto.empresa, 
                    nivel='cliente',
                    is_active=True
                ).first()
            
            # Atribui o destinatário encontrado
            mensagem.destinatario = destinatario
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
            return redirect('projetista:mensagens_projeto', projeto_id=projeto.id)
    
    # Buscar projetos atribuídos ao projetista
    projetos_query = Projeto.objects.filter(projetista=request.user).order_by('-created_at')
    
    return render(request, 'projetista/nova_mensagem.html', {
        'projetos': projetos_query,
    })

@login_required
def mensagens_projeto(request, projeto_id):
    """Exibe e gerencia mensagens específicas de um projeto para o projetista."""
    projeto = get_object_or_404(Projeto, id=projeto_id, projetista=request.user)
    
    # Processar nova mensagem
    if request.method == 'POST':
        mensagem_texto = request.POST.get('mensagem')
        if mensagem_texto:
            # Buscar um usuário cliente para ser o destinatário
            destinatario = None
            
            # Tentar encontrar o cliente que criou o projeto
            if projeto.criado_por and hasattr(projeto.criado_por, 'nivel') and projeto.criado_por.nivel == 'cliente':
                destinatario = projeto.criado_por
            else:
                # Buscar algum usuário cliente da empresa associada ao projeto
                destinatario = Usuario.objects.filter(
                    empresa=projeto.empresa, 
                    nivel='cliente',
                    is_active=True
                ).first()
            
            mensagem = Mensagem(
                projeto=projeto,
                remetente=request.user,
                conteudo=mensagem_texto,
                destinatario=destinatario
            )
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
    
    # Buscar todas as mensagens do projeto
    mensagens_lista = Mensagem.objects.filter(projeto=projeto).order_by('-data_envio')
    
    # Marcar mensagens como lidas
    mensagens_lista.filter(~Q(remetente=request.user), lida=False).update(lida=True)
    
    context = {
        'projeto': projeto,
        'mensagens': mensagens_lista,
        'today_date': timezone.now().strftime('%Y-%m-%d'),
        'yesterday_date': (timezone.now() - timezone.timedelta(days=1)).strftime('%Y-%m-%d'),
    }
    
    return render(request, 'projetista/mensagens_projeto.html', context)