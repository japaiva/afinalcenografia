#cliente/views/mensagens.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib import messages as django_messages
from django.db.models import Q, Count, Max
from django.utils import timezone

from projetos.models import Mensagem, AnexoMensagem,Projeto
from core.models import Usuario

@login_required
def mensagens(request):
    """Exibe a central de mensagens para o cliente."""
    # Alterado para usar empresa do usuário em vez de criado_por
    conversas = Projeto.objects.filter(empresa=request.user.empresa).annotate(
        ultima_mensagem=Max('mensagens__data_envio'),
        mensagens_nao_lidas=Count('mensagens', filter=Q(mensagens__lida=False) & ~Q(mensagens__remetente=request.user))
    ).filter(ultima_mensagem__isnull=False).order_by('-ultima_mensagem')
    
    # Se um projeto estiver selecionado, mostra suas mensagens
    projeto_id = request.GET.get('projeto_id')
    mensagens_lista = None
    projeto_atual = None
    
    if projeto_id:
        # Alterado para usar empresa do usuário em vez de cliente
        projeto_atual = get_object_or_404(Projeto, id=projeto_id, empresa=request.user.empresa)
        mensagens_lista = Mensagem.objects.filter(projeto=projeto_atual).order_by('data_envio')
        
        # Marca mensagens como lidas
        mensagens_lista.filter(~Q(remetente=request.user), lida=False).update(lida=True)
    
    # Contexto para o template
    context = {
        'conversas': conversas,
        'mensagens': mensagens_lista,
        'projeto_atual': projeto_atual,
        'today_date': timezone.now().strftime('%Y-%m-%d'),
        'yesterday_date': (timezone.now() - timezone.timedelta(days=1)).strftime('%Y-%m-%d'),
    }
    
    return render(request, 'cliente/central_mensagens.html', context)

@login_required
def nova_mensagem(request):
    """Formulário para envio de nova mensagem pelo cliente."""
    if request.method == 'POST':
        projeto_id = request.POST.get('projeto')
        conteudo = request.POST.get('mensagem')
        
        if projeto_id and conteudo:
            projeto = get_object_or_404(Projeto, id=projeto_id, empresa=request.user.empresa)
            
            # Criar a mensagem
            mensagem = Mensagem(
                projeto=projeto,
                remetente=request.user,
                conteudo=conteudo
            )
            
            # Determinar o destinatário correto
            # Verificar se o projeto tem um gestor designado
            gestor = None
            
            # Tenta obter o gestor do projeto (se este atributo existir)
            try:
                if hasattr(projeto, 'gestor') and projeto.gestor:
                    gestor = projeto.gestor
            except:
                pass
            
            # Se não encontrou gestor no projeto, busca um gestor ativo
            if not gestor:
                gestor = Usuario.objects.filter(nivel='gestor', is_active=True).first()
            
            # Atribui o destinatário encontrado
            mensagem.destinatario = gestor
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
            return redirect('cliente:mensagens')
    
    # Buscar projetos da empresa do usuário para o formulário
    projetos = Projeto.objects.filter(empresa=request.user.empresa).order_by('-created_at')
    
    return render(request, 'cliente/nova_mensagem.html', {
        'projetos': projetos,
    })

@login_required
def mensagens_projeto(request, projeto_id):
    """Exibe e gerencia mensagens específicas de um projeto para o cliente."""
    # Alterado para usar empresa do usuário em vez de criado_por
    projeto = get_object_or_404(Projeto, id=projeto_id, empresa=request.user.empresa)
    
    # Processar nova mensagem
    if request.method == 'POST':
        mensagem_texto = request.POST.get('mensagem')
        if mensagem_texto:
            mensagem = Mensagem(
                projeto=projeto,
                remetente=request.user,
                conteudo=mensagem_texto
            )
            
            # Determinar o destinatário correto
            # Verificar se o projeto tem um gestor designado
            gestor = None
            
            # Tenta obter o gestor do projeto (se este atributo existir)
            try:
                if hasattr(projeto, 'gestor') and projeto.gestor:
                    gestor = projeto.gestor
            except:
                pass
            
            # Se não encontrou gestor no projeto, busca um gestor ativo
            if not gestor:
                gestor = Usuario.objects.filter(nivel='gestor', is_active=True).first()
            
            # Atribui o destinatário encontrado
            mensagem.destinatario = gestor
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
    mensagens_lista = Mensagem.objects.filter(projeto=projeto).order_by('data_envio')
    
    # Marcar mensagens como lidas
    mensagens_lista.filter(~Q(remetente=request.user), lida=False).update(lida=True)
    
    context = {
        'projeto': projeto,
        'mensagens': mensagens_lista,
        'today_date': timezone.now().strftime('%Y-%m-%d'),
        'yesterday_date': (timezone.now() - timezone.timedelta(days=1)).strftime('%Y-%m-%d'),
    }
    
    return render(request, 'cliente/mensagens_projeto.html', context)