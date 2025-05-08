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

from projetos.views import validar_secao_briefing

from django.http import HttpResponse
from django.template.loader import get_template
from django.utils import timezone
from django.core.files.base import ContentFile

import logging

# Configure o logger
logger = logging.getLogger(__name__)

@login_required
def gerar_relatorio_briefing(request, projeto_id):
    """
    Gera um relatório PDF do briefing e o armazena no MinIO
    """
    # Obtém a empresa do usuário logado
    empresa = request.user.empresa
    
    # Obtém o projeto específico
    projeto = get_object_or_404(Projeto, pk=projeto_id, empresa=empresa)
    
    # Verifica se o projeto tem briefing
    if not projeto.has_briefing:
        messages.error(request, 'Este projeto não possui briefing para gerar relatório.')
        return redirect('cliente:projeto_detail', pk=projeto_id)
    
    # Obtém o briefing mais recente
    briefing = projeto.briefings.first()
    
    # Flag para verificar se precisamos gerar um novo PDF
    generate_new_pdf = True
    
    # Verifica se já existe um PDF armazenado e atualizado
    if briefing.pdf_file and briefing.pdf_generated_at and briefing.updated_at <= briefing.pdf_generated_at:
        try:
            # Tenta acessar o conteúdo do arquivo para garantir que ele existe
            pdf_content = briefing.pdf_file.read()
            briefing.pdf_file.seek(0)  # Retorna ao início do arquivo para uso posterior
            
            # Se chegou aqui, conseguimos ler o arquivo, então não precisamos gerar novo
            generate_new_pdf = False
            
            # Retorna o PDF existente
            response = HttpResponse(pdf_content, content_type='application/pdf')
            response['Content-Disposition'] = f'inline; filename="relatorio_briefing_{projeto.numero}.pdf"'
            return response
            
        except Exception as e:
            # Se ocorrer qualquer erro ao acessar o arquivo, registramos e continuamos para gerar um novo
            logger.error(f"Erro ao acessar arquivo PDF existente: {e}")
            messages.warning(request, "Regenerando o relatório PDF, aguarde um momento...")
            generate_new_pdf = True
    
    # Se chegamos aqui, precisamos gerar um novo PDF
    if generate_new_pdf:
        # Prepara os dados das seções do briefing para o PDF
        dados_evento = {
            'Nome do Evento': briefing.feira.nome if briefing.feira else 'Não informado',
            'Local': briefing.feira.local if briefing.feira else 'Não informado',
            'Data de Início': briefing.feira.data_inicio.strftime('%d/%m/%Y') if briefing.feira and briefing.feira.data_inicio else 'Não informada',
            'Data de Término': briefing.feira.data_fim.strftime('%d/%m/%Y') if briefing.feira and briefing.feira.data_fim else 'Não informada',
            'Endereço do Estande': briefing.endereco_estande or 'Não informado'
        }
        
        # Adapte os dados conforme o modelo real
        dados_estande = {
            'Tipo de Estande': briefing.get_material_display() if hasattr(briefing, 'get_material_display') else 'Não informado',
            'Metragem Frente': f"{briefing.medida_frente} m" if hasattr(briefing, 'medida_frente') and briefing.medida_frente else 'Não informada',
            'Metragem Fundo': f"{briefing.medida_fundo} m" if hasattr(briefing, 'medida_fundo') and briefing.medida_fundo else 'Não informada',
            'Área Total': f"{briefing.area_estande} m²" if hasattr(briefing, 'area_estande') and briefing.area_estande else 'Não informada',
            'Orçamento': f"R$ {briefing.orcamento:,.2f}".replace(',', '.').replace('.', ',') if briefing.orcamento else 'Não informado',
            'Estilo': briefing.estilo_estande or 'Não informado',
            'Objetivo': briefing.objetivo_estande or 'Não informado',
        }
        
        # Colete dados das áreas do estande
        dados_areas = {}
        
        # Áreas de Exposição
        areas_exposicao = []
        if hasattr(briefing, 'areas_exposicao'):
            for area in briefing.areas_exposicao.all():
                area_info = {
                    'Metragem': f"{area.metragem} m²" if area.metragem else 'Não informada',
                    'Equipamentos': area.equipamentos or 'Não informados',
                    'Itens': []
                }
                
                if area.tem_lounge:
                    area_info['Itens'].append('Lounge')
                if area.tem_vitrine_exposicao:
                    area_info['Itens'].append('Vitrine de Exposição')
                if area.tem_balcao_recepcao:
                    area_info['Itens'].append('Balcão de Recepção')
                if area.tem_mesas_atendimento:
                    area_info['Itens'].append('Mesas de Atendimento')
                if area.tem_balcao_cafe:
                    area_info['Itens'].append('Balcão para Café/Bar')
                if area.tem_balcao_vitrine:
                    area_info['Itens'].append('Balcão Vitrine')
                if area.tem_caixa_vendas:
                    area_info['Itens'].append('Caixa para Vendas')
                
                areas_exposicao.append(area_info)
        
        if areas_exposicao:
            dados_areas['Áreas de Exposição'] = areas_exposicao
        
        # Salas de Reunião
        salas_reuniao = []
        if hasattr(briefing, 'salas_reuniao'):
            for sala in briefing.salas_reuniao.all():
                salas_reuniao.append({
                    'Capacidade': f"{sala.capacidade} pessoas" if sala.capacidade else 'Não informada',
                    'Metragem': f"{sala.metragem} m²" if sala.metragem else 'Não informada',
                    'Equipamentos': sala.equipamentos or 'Não informados'
                })
        
        if salas_reuniao:
            dados_areas['Salas de Reunião'] = salas_reuniao
        
        # Copas
        copas = []
        if hasattr(briefing, 'copas'):
            for copa in briefing.copas.all():
                copas.append({
                    'Metragem': f"{copa.metragem} m²" if copa.metragem else 'Não informada',
                    'Equipamentos': copa.equipamentos or 'Não informados'
                })
        
        if copas:
            dados_areas['Copas'] = copas
        
        # Depósitos
        depositos = []
        if hasattr(briefing, 'depositos'):
            for deposito in briefing.depositos.all():
                depositos.append({
                    'Metragem': f"{deposito.metragem} m²" if deposito.metragem else 'Não informada',
                    'Equipamentos': deposito.equipamentos or 'Não informados'
                })
        
        if depositos:
            dados_areas['Depósitos'] = depositos
        
        # Dados complementares 
        dados_complementares = {
            'Objetivo do Estande': briefing.objetivo_evento if hasattr(briefing, 'objetivo_evento') and briefing.objetivo_evento else 'Não informado',
            'Referências Visuais': briefing.referencias_dados if hasattr(briefing, 'referencias_dados') and briefing.referencias_dados else 'Não informado',
            'Logotipo': briefing.logotipo if hasattr(briefing, 'logotipo') and briefing.logotipo else 'Não informado',
            'Campanha': briefing.campanha_dados if hasattr(briefing, 'campanha_dados') and briefing.campanha_dados else 'Não informado',
        }
        
        # Arquivos de referência
        arquivos_referencias = []
        if hasattr(briefing, 'arquivos'):
            for arquivo in briefing.arquivos.all():
                arquivos_referencias.append({
                    'Nome': arquivo.nome,
                    'Tipo': arquivo.get_tipo_display() if hasattr(arquivo, 'get_tipo_display') else arquivo.tipo,
                    'Observações': arquivo.observacoes or 'Sem observações'
                })
        
        # Contexto para o template
        context = {
            'empresa': empresa,
            'projeto': projeto,
            'briefing': briefing,
            'secoes': [
                {'titulo': 'Informações do Evento', 'dados': dados_evento},
                {'titulo': 'Características do Estande', 'dados': dados_estande},
                {'titulo': 'Áreas do Estande', 'dados': dados_areas or {'Informação': 'Nenhuma área definida'}},
                {'titulo': 'Informações Complementares', 'dados': dados_complementares},
            ],
            'arquivos': arquivos_referencias,
            'data_geracao': timezone.now().strftime('%d/%m/%Y %H:%M')
        }
        
        # Carrega o template HTML para o PDF
        template = get_template('cliente/briefing_relatorio.html')
        html_string = template.render(context)
        
        # Gera o PDF usando WeasyPrint
        try:
            from weasyprint import HTML, CSS
            pdf_file = HTML(string=html_string).write_pdf(
                stylesheets=[
                    CSS(string='@page { size: A4; margin: 1cm }')
                ]
            )
            
            # Cria um nome de arquivo único com timestamp
            timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
            filename = f"relatorio_briefing_{projeto.numero}_{timestamp}.pdf"
            
            # Limpe qualquer referência anterior ao arquivo PDF
            if briefing.pdf_file:
                try:
                    # Tenta excluir o arquivo anterior
                    old_filename = briefing.pdf_file.name
                    briefing.pdf_file.delete(save=False)
                    logger.info(f"Arquivo anterior excluído: {old_filename}")
                except Exception as e:
                    logger.warning(f"Erro ao excluir arquivo anterior: {e}")
            
            # Salva o arquivo no storage configurado
            briefing.pdf_file.save(filename, ContentFile(pdf_file), save=True)
            briefing.pdf_generated_at = timezone.now()
            briefing.save(update_fields=['pdf_generated_at'])
            
            # Registra no log
            logger.info(f"Relatório do briefing gerado para o projeto #{projeto.numero}")
            
            # Retorna o PDF ao usuário
            response = HttpResponse(pdf_file, content_type='application/pdf')
            response['Content-Disposition'] = f'inline; filename="{filename}"'
            return response
            
        except ImportError:
            # Se WeasyPrint não estiver disponível, envia mensagem de erro
            messages.error(request, 'Não foi possível gerar o relatório PDF. Biblioteca WeasyPrint não disponível.')
            return redirect('cliente:projeto_detail', pk=projeto_id)
        except Exception as e:
            # Registra qualquer outro erro na geração do PDF
            logger.error(f"Erro ao gerar relatório PDF: {e}")
            messages.error(request, f'Erro ao gerar o relatório: {str(e)}')
            return redirect('cliente:projeto_detail', pk=projeto_id)

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
    View para validar o briefing verificando todas as seções
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
    
    # Valida cada seção individualmente para garantir que todas estão atualizadas
    for secao in ['evento', 'estande', 'areas_estande', 'dados_complementares']:
        validar_secao_briefing(briefing, secao)
    
    # Verifica se todas as seções estão aprovadas
    validacoes = briefing.validacoes.all()
    todas_aprovadas = all(v.status == 'aprovado' for v in validacoes)
    
    # Atualiza o status do briefing com base nas validações
    if todas_aprovadas:
        briefing.status = 'validado'
        briefing.validado_por_ia = True
        briefing.save(update_fields=['status', 'validado_por_ia'])
        
        # Adiciona mensagem de parabéns no chat
        BriefingConversation.objects.create(
            briefing=briefing,
            mensagem="Parabéns! Seu briefing foi completamente validado. Você pode enviá-lo para a equipe de cenografia avaliar.",
            origem='ia',
            etapa=briefing.etapa_atual
        )
    else:
        briefing.status = 'em_validacao'
        briefing.validado_por_ia = False
        briefing.save(update_fields=['status', 'validado_por_ia'])
        
        # Adiciona mensagem indicando ajustes necessários
        BriefingConversation.objects.create(
            briefing=briefing,
            mensagem="Algumas seções do briefing ainda precisam de ajustes. Por favor, verifique os itens marcados em vermelho ou amarelo.",
            origem='ia',
            etapa=briefing.etapa_atual
        )
    
    # Retorna o resultado da validação
    return JsonResponse({
        'success': True, 
        'is_valid': todas_aprovadas,
        'message': 'Briefing validado com sucesso!' if todas_aprovadas else 'Briefing necessita de ajustes.',
        'validacoes': {v.secao: v.status for v in validacoes}
    })


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