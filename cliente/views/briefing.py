# views/briefing.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from core.decorators import cliente_required

from projetos.models import Projeto,Briefing, BriefingArquivoReferencia, BriefingValidacao, BriefingConversation

from projetos.forms import (
    BriefingEtapa1Form, BriefingEtapa2Form,
    BriefingEtapa3Form, BriefingEtapa4Form,
    BriefingArquivoReferenciaForm
)

from .ai_services import validar_briefing_com_ia, processar_mensagem_ia

# views/briefing.py (adaptado - apenas para a função briefing_etapa)

# views/briefing.py

@login_required
def briefing_etapa(request, projeto_id, etapa):
    """
    View para exibir e processar um formulário de briefing por etapa
    """
    # Obtém a empresa do usuário logado
    empresa = request.user.empresa
    
    # Obtém o projeto e verifica se pertence à mesma empresa
    projeto = get_object_or_404(Projeto, pk=projeto_id, empresa=empresa)
    
    # Verifica se o projeto tem um briefing associado
    if not projeto.has_briefing:
        messages.error(request, 'Este projeto não possui um briefing iniciado.')
        return redirect('projetos:projeto_detail', pk=projeto_id)
    
    # Obtém o briefing
    briefing = projeto.briefing
    
    # Verifica a etapa solicitada (1-4)
    if etapa < 1 or etapa > 4:
        messages.error(request, 'Etapa inválida.')
        return redirect('briefing:briefing_etapa', projeto_id=projeto_id, etapa=briefing.etapa_atual)
    
    # Define o título da etapa e o formulário correspondente
    if etapa == 1:
        titulo_etapa = "EVENTO - Datas e Localização"
        validacao_atual = briefing.validacoes.get(secao='evento')
        form_class = BriefingEtapa1Form
    elif etapa == 2:
        titulo_etapa = "ESTANDE - Características Físicas"
        validacao_atual = briefing.validacoes.get(secao='estande')
        form_class = BriefingEtapa2Form
    elif etapa == 3:
        titulo_etapa = "ÁREAS DO ESTANDE - Divisões Funcionais"
        validacao_atual = briefing.validacoes.get(secao='areas_estande')
        form_class = BriefingEtapa3Form
    else:  # etapa == 4
        titulo_etapa = "DADOS COMPLEMENTARES - Referências Visuais"
        validacao_atual = briefing.validacoes.get(secao='dados_complementares')
        form_class = BriefingEtapa4Form
    
    # Se estamos na etapa 4, pegamos os arquivos de referência (mudei de 2 para 4)
    arquivos = []
    if etapa == 4:
        arquivos = briefing.arquivos.all()
    
    # Processa o formulário se for um POST
    if request.method == 'POST':
        form = form_class(request.POST, request.FILES, instance=briefing)
        if form.is_valid():
            # Salva o formulário
            form.save()
            
            # Atualiza a etapa atual do briefing se necessário
            if 'avancar' in request.POST and etapa < 4:
                briefing.etapa_atual = etapa + 1
                briefing.save(update_fields=['etapa_atual'])
                messages.success(request, f'Etapa {etapa} concluída com sucesso!')
                return redirect('cliente:briefing_etapa', projeto_id=projeto_id, etapa=etapa+1)
            elif 'concluir' in request.POST:
                # Marca o briefing como validado
                briefing.status = 'em_validacao'
                briefing.save(update_fields=['status'])
                messages.success(request, 'Todas as etapas preenchidas! O briefing será validado.')
                return redirect('cliente:concluir_briefing', projeto_id=projeto_id)
            
            # Simples salvamento sem navegação
            messages.success(request, 'Informações salvas com sucesso!')
            return redirect('cliente:briefing_etapa', projeto_id=projeto_id, etapa=etapa)
    else:
        form = form_class(instance=briefing)
    
    # Verifica botões de navegação
    pode_voltar = etapa > 1
    pode_avancar = etapa < 4
    
    # Obtém todas as validações do briefing
    validacoes = briefing.validacoes.all()
    
    # Verifica se todas as seções estão aprovadas
    todas_aprovadas = all(v.status == 'aprovado' for v in validacoes)
    
    # Obtém as conversas desta etapa
    conversas = briefing.conversas.filter(etapa=etapa).order_by('-timestamp')[:20]
    
    context = {
        'empresa': empresa,
        'projeto': projeto,
        'briefing': briefing,
        'form': form,
        'etapa': etapa,
        'titulo_etapa': titulo_etapa,
        'validacao_atual': validacao_atual,
        'validacoes': validacoes,
        'todas_aprovadas': todas_aprovadas,
        'pode_voltar': pode_voltar,
        'pode_avancar': pode_avancar,
        'arquivos': arquivos,
        'conversas': conversas,
    }
    return render(request, 'briefing/briefing_etapa.html', context)

@login_required
@require_POST
def salvar_rascunho_briefing(request, projeto_id):
    """
    View para salvar um rascunho do briefing (usado em AJAX)
    """
    # Obtém a empresa do usuário logado
    empresa = request.user.empresa
    
    # Obtém o projeto e verifica se pertence à mesma empresa
    projeto = get_object_or_404(Projeto, pk=projeto_id, empresa=empresa)
    
    # Verifica se o projeto tem um briefing associado
    if not projeto.has_briefing:
        return JsonResponse({'success': False, 'message': 'Este projeto não possui um briefing iniciado.'})
    
    # Obtém o briefing
    briefing = projeto.briefing
    
    # Determina a etapa atual para selecionar o formulário correto
    etapa = int(request.POST.get('etapa', briefing.etapa_atual))
    
    # Seleciona o formulário correspondente
    if etapa == 1:
        form_class = BriefingEtapa1Form
    elif etapa == 2:
        form_class = BriefingEtapa2Form
    elif etapa == 3:
        form_class = BriefingEtapa3Form
    else:  # etapa == 4
        form_class = BriefingEtapa4Form
    
    # Processa o formulário
    form = form_class(request.POST, request.FILES, instance=briefing)
    if form.is_valid():
        form.save()
        return JsonResponse({'success': True, 'message': 'Rascunho salvo com sucesso!'})
    
    # Se o formulário não for válido, retorna os erros
    return JsonResponse({'success': False, 'errors': form.errors})

@login_required
@require_POST
def validar_briefing(request, projeto_id):
    """
    View para validar o briefing usando IA
    """
    # Obtém a empresa do usuário logado
    empresa = request.user.empresa
    
    # Obtém o projeto e verifica se pertence à mesma empresa
    projeto = get_object_or_404(Projeto, pk=projeto_id, empresa=empresa)
    
    # Verifica se o projeto tem um briefing associado
    if not projeto.has_briefing:
        return JsonResponse({'success': False, 'message': 'Este projeto não possui um briefing iniciado.'})
    
    # Obtém o briefing
    briefing = projeto.briefing
    
    # Valida o briefing usando IA
    resultado = validar_briefing_com_ia(briefing)
    
    if resultado['success']:
        # Atualiza o status
        briefing.status = 'validado' if resultado['is_valid'] else 'em_validacao'
        briefing.validado_por_ia = resultado['is_valid']
        briefing.save(update_fields=['status', 'validado_por_ia'])
        
        # Resposta de sucesso
        return JsonResponse({
            'success': True, 
            'is_valid': resultado['is_valid'],
            'message': 'Briefing validado com sucesso!' if resultado['is_valid'] else 'Briefing necessita de ajustes.'
        })
    
    # Caso ocorra algum erro na validação
    return JsonResponse({'success': False, 'message': 'Erro ao validar o briefing. Tente novamente.'})

@login_required
def concluir_briefing(request, projeto_id):
    """
    View para concluir o briefing e enviá-lo para aprovação
    """
    # Obtém a empresa do usuário logado
    empresa = request.user.empresa
    
    # Obtém o projeto e verifica se pertence à mesma empresa
    projeto = get_object_or_404(Projeto, pk=projeto_id, empresa=empresa)
    
    # Verifica se o projeto tem um briefing associado
    if not projeto.has_briefing:
        messages.error(request, 'Este projeto não possui um briefing iniciado.')
        return redirect('projetos:projeto_detail', pk=projeto_id)
    
    # Obtém o briefing
    briefing = projeto.briefing
    
    # Obtém todas as validações
    validacoes = briefing.validacoes.all()
    
    # Verifica se todas as seções estão aprovadas
    todas_aprovadas = all(v.status == 'aprovado' for v in validacoes)
    
    # Se for um POST, processa o envio do briefing
    if request.method == 'POST':
        if todas_aprovadas:
            # Atualiza o status do briefing e do projeto
            briefing.status = 'enviado'
            briefing.save(update_fields=['status'])
            
            projeto.briefing_status = 'enviado'
            projeto.save(update_fields=['briefing_status'])
            
            messages.success(request, 'Briefing enviado com sucesso para análise!')
            return redirect('projetos:projeto_detail', pk=projeto_id)
        else:
            messages.error(request, 'O briefing não pode ser enviado pois existem seções que precisam ser corrigidas.')
    
    context = {
        'empresa': empresa,
        'projeto': projeto,
        'briefing': briefing,
        'validacoes': validacoes,
        'todas_aprovadas': todas_aprovadas,
    }
    return render(request, 'briefing/concluir_briefing.html', context)

@login_required
@require_POST
def upload_arquivo_referencia(request, projeto_id):
    """
    View para fazer upload de um arquivo de referência para o briefing
    """
    # Obtém a empresa do usuário logado
    empresa = request.user.empresa
    
    # Obtém o projeto e verifica se pertence à mesma empresa
    projeto = get_object_or_404(Projeto, pk=projeto_id, empresa=empresa)
    
    # Verifica se o projeto tem um briefing associado
    if not projeto.has_briefing:
        return JsonResponse({'success': False, 'message': 'Este projeto não possui um briefing iniciado.'})
    
    # Obtém o briefing
    briefing = projeto.briefing
    
    # Processa o upload
    if request.method == 'POST' and request.FILES.get('arquivo'):
        form = BriefingArquivoReferenciaForm(request.POST, request.FILES)
        if form.is_valid():
            arquivo = form.save(commit=False)
            arquivo.briefing = briefing
            arquivo.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Arquivo enviado com sucesso!',
                'arquivo': {
                    'id': arquivo.id,
                    'nome': arquivo.nome,
                    'tipo': arquivo.get_tipo_display(),
                    'url': arquivo.arquivo.url,
                }
            })
        else:
            return JsonResponse({'success': False, 'errors': form.errors})
    
    return JsonResponse({'success': False, 'message': 'Nenhum arquivo encontrado.'})

@login_required
@require_POST
def excluir_arquivo_referencia(request, arquivo_id):
    """
    View para excluir um arquivo de referência do briefing
    """
    # Obtém a empresa do usuário logado
    empresa = request.user.empresa
    
    # Obtém o arquivo, garantindo que pertence a um briefing de um projeto da mesma empresa
    arquivo = get_object_or_404(BriefingArquivoReferencia, 
                               id=arquivo_id, 
                               briefing__projeto__empresa=empresa)
    
    # Exclui o arquivo
    arquivo.delete()
    
    return JsonResponse({'success': True, 'message': 'Arquivo excluído com sucesso!'})

@login_required
def ver_manual_feira(request, projeto_id):
    """
    View para visualizar o manual da feira com suporte de IA
    """
    # Obtém a empresa do usuário logado
    empresa = request.user.empresa
    
    # Obtém o projeto e verifica se pertence à mesma empresa
    projeto = get_object_or_404(Projeto, pk=projeto_id, empresa=empresa)
    
    # Verifica se o projeto tem uma feira com manual
    if not projeto.feira or not projeto.feira.manual:
        messages.error(request, 'Este projeto não possui uma feira com manual.')
        return redirect('projetos:projeto_detail', pk=projeto_id)
    
    context = {
        'empresa': empresa,
        'projeto': projeto,
        'feira': projeto.feira,
    }
    return render(request, 'briefing/ver_manual_feira.html', context)

@login_required
@require_POST
def enviar_mensagem_ia(request, projeto_id):
    """
    View para enviar mensagem ao assistente IA e obter resposta
    """
    # Obtém a empresa do usuário logado
    empresa = request.user.empresa
    
    # Obtém o projeto e verifica se pertence à mesma empresa
    projeto = get_object_or_404(Projeto, pk=projeto_id, empresa=empresa)
    
    # Verifica se o projeto tem um briefing associado
    if not projeto.has_briefing:
        return JsonResponse({'success': False, 'message': 'Este projeto não possui um briefing iniciado.'})
    
    # Obtém o briefing
    briefing = projeto.briefing
    
    # Obtém a mensagem e a etapa atual
    mensagem = request.POST.get('mensagem', '')
    etapa = int(request.POST.get('etapa', briefing.etapa_atual))
    
    if not mensagem:
        return JsonResponse({'success': False, 'message': 'Mensagem não fornecida.'})
    
    # Salva a mensagem do cliente
    conversa_cliente = BriefingConversation.objects.create(
        briefing=briefing,
        mensagem=mensagem,
        origem='cliente',
        etapa=etapa
    )
    
    # Processa a mensagem com a IA
    resposta = processar_mensagem_ia(briefing, mensagem, etapa)
    
    # Salva a resposta da IA
    conversa_ia = BriefingConversation.objects.create(
        briefing=briefing,
        mensagem=resposta['mensagem'],
        origem='ia',
        etapa=etapa
    )
    
    # Retorna a resposta para o cliente
    return JsonResponse({
        'success': True,
        'mensagem_cliente': {
            'id': conversa_cliente.id,
            'texto': conversa_cliente.mensagem,
            'timestamp': conversa_cliente.timestamp.strftime('%H:%M')
        },
        'mensagem_ia': {
            'id': conversa_ia.id,
            'texto': conversa_ia.mensagem,
            'timestamp': conversa_ia.timestamp.strftime('%H:%M')
        }
    })

# cliente/views/briefing.py

@login_required
@cliente_required
def briefing_perguntar_feira(request, briefing_id):
    """
    Permite ao cliente fazer perguntas específicas sobre a feira no contexto do briefing
    """
    briefing = get_object_or_404(Briefing, pk=briefing_id, projeto__empresa=request.user.empresa)
    
    # Verifica se o projeto tem uma feira associada
    if not briefing.projeto.feira:
        messages.error(request, 'Este projeto não possui uma feira associada.')
        return redirect('cliente:briefing_etapa', projeto_id=briefing.projeto.id, etapa=briefing.etapa_atual)
    
    feira = briefing.projeto.feira
    
    if request.method == 'POST':
        pergunta = request.POST.get('pergunta', '')
        if not pergunta:
            messages.error(request, 'Por favor, informe uma pergunta.')
            return redirect('cliente:briefing_perguntar_feira', briefing_id=briefing.id)
        
        # Aqui você implementaria a lógica para consultar a IA com RAG usando Pinecone
        # Por enquanto, vamos criar uma resposta simulada
        resposta = f"Esta é uma resposta simulada sobre a feira {feira.nome}. Em uma implementação real, a IA consultaria a base de conhecimento vetorial no Pinecone para fornecer informações específicas do manual da feira."
        
        # Registrar a interação
        BriefingConversation.objects.create(
            briefing=briefing,
            mensagem=f"Pergunta sobre a feira: {pergunta}",
            origem='cliente',
            etapa=briefing.etapa_atual
        )
        
        BriefingConversation.objects.create(
            briefing=briefing,
            mensagem=resposta,
            origem='ia',
            etapa=briefing.etapa_atual
        )
        
        messages.success(request, 'Pergunta enviada com sucesso!')
        
        # Retornar ao briefing
        return redirect('cliente:briefing_etapa', projeto_id=briefing.projeto.id, etapa=briefing.etapa_atual)
    
    context = {
        'briefing': briefing,
        'feira': feira,
    }
    return render(request, 'cliente/briefing_perguntar_feira.html', context)

# views/briefing.py ou onde você preferir colocar

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
        return redirect('cliente:briefing_etapa', projeto_id=projeto.id, etapa=projeto.briefing.etapa_atual)
    
    # Cria um novo briefing para o projeto
    briefing = Briefing.objects.create(projeto=projeto)
    
    # Preencher dados iniciais do projeto
    # Se o projeto tiver uma feira associada, podemos preencher esses dados automaticamente
    if projeto.feira:
        briefing.feira = projeto.feira
        briefing.local_evento = projeto.feira.local
        briefing.data_feira_inicio = projeto.feira.data_inicio
        briefing.data_feira_fim = projeto.feira.data_fim
    
    # Preenchemos também o nome do projeto e orçamento se disponíveis
    briefing.nome_projeto = projeto.nome
    briefing.orcamento = projeto.orcamento
    briefing.save()
    
    # Cria as validações iniciais para as novas seções
    for secao in ['evento', 'estande', 'areas_estande', 'dados_complementares']:
        BriefingValidacao.objects.create(
            briefing=briefing,
            secao=secao,
            status='pendente'
        )
    
    # Atualiza o status do projeto
    projeto.tem_briefing = True
    projeto.briefing_status = 'em_andamento'
    projeto.save(update_fields=['tem_briefing', 'briefing_status'])
    
    messages.success(request, 'Briefing iniciado com sucesso!')
    return redirect('cliente:briefing_etapa', projeto_id=projeto.id, etapa=1)