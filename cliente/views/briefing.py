# views/briefing.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.template.loader import get_template
from django.utils import timezone
from django.core.files.base import ContentFile
from django.conf import settings
from django.db import transaction

from core.decorators import cliente_required

from projetos.models import Projeto
from projetos.models.briefing import (
    Briefing, AreaExposicao, SalaReuniao, Copa, Deposito,
    BriefingArquivoReferencia, BriefingValidacao, BriefingConversation
)

from projetos.forms.briefing import (
    BriefingEtapa1Form, BriefingEtapa2Form,
    BriefingEtapa3Form, BriefingEtapa4Form,
    BriefingArquivoReferenciaForm, BriefingMensagemForm,
    CopaForm, DepositoForm
)

from projetos.views import validar_secao_briefing

#logger
import logging
logger = logging.getLogger(__name__)

#REFATORADAS
# briefing_etapa
# salvar_rascunho_briefing
# concluir briefing

from django.views.decorators.http import require_POST

@login_required
@require_POST
def salvar_rascunho_briefing(request, projeto_id):
    """
    View para salvar um rascunho do briefing (via AJAX)
    """
    from projetos.services.briefing_service import salvar_rascunho_briefing

    etapa = int(request.POST.get('etapa', 1))

    form_map = {
        1: BriefingEtapa1Form,
        2: BriefingEtapa2Form,
        3: BriefingEtapa3Form,
        4: BriefingEtapa4Form,
    }
    form_class = form_map.get(etapa, BriefingEtapa1Form)

    success, form = salvar_rascunho_briefing(
        projeto_id,
        form_class,
        {'data': request.POST, 'files': request.FILES}
    )

    if success:
        return JsonResponse({'success': True, 'message': 'Rascunho salvo com sucesso!'})
    return JsonResponse({'success': False, 'errors': form.errors})

@login_required
@cliente_required
def concluir_briefing(request, projeto_id):
    """Tela de conclusão do briefing"""
    projeto = get_object_or_404(Projeto, pk=projeto_id, empresa=request.user.empresa)
    
    try:
        briefing = Briefing.objects.get(projeto=projeto)
    except Briefing.DoesNotExist:
        messages.error(request, 'Nenhum briefing encontrado para este projeto.')
        return redirect('cliente:briefing_etapa', projeto_id=projeto.id, etapa=1)
    
    validacoes = BriefingValidacao.objects.filter(briefing=briefing)
    todas_aprovadas = all(v.status == 'aprovado' for v in validacoes)
    
    if request.method == 'POST':
        if todas_aprovadas:
            briefing.status = 'enviado'
            briefing.save()

            projeto.status = 'briefing_enviado'
            projeto.data_envio_briefing = timezone.now()
            projeto.save()

            messages.success(request, 'Briefing enviado com sucesso para análise!')
            return redirect('cliente:projeto_detail', pk=projeto.id)
        else:
            messages.error(request, 'Existem seções do briefing que ainda não foram aprovadas.')

    context = {
        'projeto': projeto,
        'briefing': briefing,
        'validacoes': validacoes,
        'todas_aprovadas': todas_aprovadas,
    }

    return render(request, 'cliente/briefing_conclusao.html', context)

@login_required
@cliente_required
def briefing_etapa(request, projeto_id, etapa):
    """Gerencia cada etapa do briefing"""
    from projetos.services.briefing_service import proxima_etapa_logica, obter_titulo_etapa

    projeto = get_object_or_404(Projeto, pk=projeto_id, empresa=request.user.empresa)

    try:
        briefing = Briefing.objects.get(projeto=projeto)
    except Briefing.DoesNotExist:
        return redirect('cliente:iniciar_briefing', projeto_id=projeto.id)

    etapa = int(etapa)
    if etapa < 1 or etapa > 4:
        etapa = 1

    # Formulários por etapa
    if etapa == 1:
        form_class = BriefingEtapa1Form
        secao = 'evento'
    elif etapa == 2:
        form_class = BriefingEtapa2Form
        secao = 'estande'
    elif etapa == 3:
        form_class = BriefingEtapa3Form
        secao = 'areas_estande'
    else:
        form_class = BriefingEtapa4Form
        secao = 'dados_complementares'

    if request.method == 'POST':
        if etapa == 3:
            form = form_class(request.POST)
            if form.is_valid():
                with transaction.atomic():
                    # Checkboxes principais
                    tem_area_exposicao = form.cleaned_data.get('tem_area_exposicao', False)
                    tem_sala_reuniao = form.cleaned_data.get('tem_sala_reuniao', False)
                    tem_copa = form.cleaned_data.get('tem_copa', False)
                    tem_deposito = form.cleaned_data.get('tem_deposito', False)

                    if not tem_area_exposicao:
                        AreaExposicao.objects.filter(briefing=briefing).delete()

                    if not tem_sala_reuniao:
                        SalaReuniao.objects.filter(briefing=briefing).delete()

                    if not tem_copa:
                        Copa.objects.filter(briefing=briefing).delete()

                    if not tem_deposito:
                        Deposito.objects.filter(briefing=briefing).delete()

                    # Áreas de exposição
                    if tem_area_exposicao:
                        AreaExposicao.objects.filter(briefing=briefing).delete()
                        num_areas = int(request.POST.get('num_areas_exposicao', 1))
                        for i in range(num_areas):
                            if f'area_exposicao-{i}-metragem' in request.POST:
                                area = AreaExposicao(briefing=briefing)
                                area.tem_lounge = request.POST.get(f'area_exposicao-{i}-tem_lounge') == 'on'
                                area.tem_vitrine_exposicao = request.POST.get(f'area_exposicao-{i}-tem_vitrine_exposicao') == 'on'
                                area.tem_balcao_recepcao = request.POST.get(f'area_exposicao-{i}-tem_balcao_recepcao') == 'on'
                                area.tem_mesas_atendimento = request.POST.get(f'area_exposicao-{i}-tem_mesas_atendimento') == 'on'
                                area.tem_balcao_cafe = request.POST.get(f'area_exposicao-{i}-tem_balcao_cafe') == 'on'
                                area.tem_balcao_vitrine = request.POST.get(f'area_exposicao-{i}-tem_balcao_vitrine') == 'on'
                                area.tem_caixa_vendas = request.POST.get(f'area_exposicao-{i}-tem_caixa_vendas') == 'on'
                                area.equipamentos = request.POST.get(f'area_exposicao-{i}-equipamentos', '')
                                area.observacoes = request.POST.get(f'area_exposicao-{i}-observacoes', '')
                                try:
                                    area.metragem = float(request.POST.get(f'area_exposicao-{i}-metragem', 0))
                                except (ValueError, TypeError):
                                    area.metragem = 0
                                area.save()

                    # Salas de reunião
                    if tem_sala_reuniao:
                        SalaReuniao.objects.filter(briefing=briefing).delete()
                        num_salas = int(request.POST.get('num_salas_reuniao', 1))
                        for i in range(num_salas):
                            if f'sala_reuniao-{i}-capacidade' in request.POST:
                                sala = SalaReuniao(briefing=briefing)
                                try:
                                    sala.capacidade = int(request.POST.get(f'sala_reuniao-{i}-capacidade', 0))
                                except (ValueError, TypeError):
                                    sala.capacidade = 0
                                sala.equipamentos = request.POST.get(f'sala_reuniao-{i}-equipamentos', '')
                                try:
                                    sala.metragem = float(request.POST.get(f'sala_reuniao-{i}-metragem', 0))
                                except (ValueError, TypeError):
                                    sala.metragem = 0
                                sala.save()

                    # Copa
                    if tem_copa and 'copa-equipamentos' in request.POST:
                        copa, _ = Copa.objects.get_or_create(briefing=briefing)
                        copa.equipamentos = request.POST.get('copa-equipamentos', '')
                        try:
                            copa.metragem = float(request.POST.get('copa-metragem', 0))
                        except (ValueError, TypeError):
                            copa.metragem = 0
                        copa.save()

                    # Depósito
                    if tem_deposito and 'deposito-equipamentos' in request.POST:
                        deposito, _ = Deposito.objects.get_or_create(briefing=briefing)
                        deposito.equipamentos = request.POST.get('deposito-equipamentos', '')
                        try:
                            deposito.metragem = float(request.POST.get('deposito-metragem', 0))
                        except (ValueError, TypeError):
                            deposito.metragem = 0
                        deposito.save()

                briefing.etapa_atual = etapa
                briefing.save()
        else:
            form = form_class(request.POST, request.FILES, instance=briefing)
            if form.is_valid():
                form.save()
                briefing.etapa_atual = etapa
                briefing.save()

        if 'avancar' in request.POST and etapa < 4:
            return redirect('cliente:briefing_etapa', projeto_id=projeto.id, etapa=proxima_etapa_logica(projeto.tipo_projeto, etapa))
        elif 'concluir' in request.POST:
            return redirect('cliente:concluir_briefing', projeto_id=projeto.id)

    else:
        if etapa == 3:
            form = BriefingEtapa3Form(initial={
                'tem_area_exposicao': AreaExposicao.objects.filter(briefing=briefing).exists(),
                'tem_sala_reuniao': SalaReuniao.objects.filter(briefing=briefing).exists(),
                'tem_copa': Copa.objects.filter(briefing=briefing).exists(),
                'tem_deposito': Deposito.objects.filter(briefing=briefing).exists(),
            })
        else:
            form = form_class(instance=briefing)

    conversas = BriefingConversation.objects.filter(briefing=briefing, etapa=etapa).order_by('-timestamp')[:20]
    validacoes = BriefingValidacao.objects.filter(briefing=briefing)
    validacao_atual = validacoes.filter(secao=secao).first()
    arquivos = BriefingArquivoReferencia.objects.filter(briefing=briefing)

    context = {
        'projeto': projeto,
        'briefing': briefing,
        'etapa': etapa,
        'form': form,
        'conversas': conversas,
        'validacoes': validacoes,
        'validacao_atual': validacao_atual,
        'mensagem_form': BriefingMensagemForm(),
        'arquivo_form': BriefingArquivoReferenciaForm(),
        'arquivos': arquivos,
        'titulo_etapa': obter_titulo_etapa(etapa),
        'pode_avancar': etapa < 4,
        'pode_voltar': etapa > 1,
        'todas_aprovadas': all(v.status == 'aprovado' for v in validacoes),
    }

    if etapa == 3:
        areas_exposicao = list(AreaExposicao.objects.filter(briefing=briefing)) or [None]
        salas_reuniao = list(SalaReuniao.objects.filter(briefing=briefing)) or [None]
        copa = Copa.objects.filter(briefing=briefing).first()
        deposito = Deposito.objects.filter(briefing=briefing).first()

        context.update({
            'areas_exposicao': areas_exposicao,
            'salas_reuniao': salas_reuniao,
            'copa_form': CopaForm(instance=copa) if copa else CopaForm(prefix='copa'),
            'deposito_form': DepositoForm(instance=deposito) if deposito else DepositoForm(prefix='deposito'),
            'num_areas_exposicao': len(areas_exposicao),
            'num_salas_reuniao': len(salas_reuniao),
        })

    # Renderiza template dinâmico por etapa (ex: briefing_etapa3.html)
    template_name = f'cliente/briefing_etapa{etapa}.html'
    return render(request, template_name, context)

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
        # Obtemos o briefing mais recente para acessar sua etapa_atual
        briefing_atual = Briefing.objects.filter(projeto=projeto).order_by('-updated_at').first()
        return redirect('cliente:briefing_etapa', projeto_id=projeto.id, etapa=briefing_atual.etapa_atual)

    # Cria um novo briefing para o projeto
    briefing = Briefing.objects.create(projeto=projeto)

    # Preenche dados iniciais do briefing
    if projeto.feira:
        briefing.feira = projeto.feira

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
    projeto.status = 'briefing_pendente'
    projeto.save(update_fields=['status'])

    messages.success(request, 'Briefing iniciado com sucesso!')
    return redirect('cliente:briefing_etapa', projeto_id=projeto.id, etapa=1)

#A REFATORAR

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
        
        # Seção 1: Informações do Evento
        # Garantir que estamos utilizando as informações da feira corretamente
        feira = briefing.feira if briefing.feira else projeto.feira
        
        dados_evento = {
            'Nome do Evento': feira.nome if feira else 'Não informado',
            'Local': feira.local if feira else 'Não informado',
            'Cidade/Estado': f"{feira.cidade}/{feira.estado}" if feira and feira.cidade else 'Não informado',
            'Organizador': feira.promotora if feira and feira.promotora else 'Não informado',
            'Horário': feira.data_horario if feira and feira.data_horario else 'Não informado',
            'Data de Início': feira.data_inicio.strftime('%d/%m/%Y') if feira and feira.data_inicio else 'Não informada',
            'Data de Término': feira.data_fim.strftime('%d/%m/%Y') if feira and feira.data_fim else 'Não informada',
            'Período de Montagem': feira.periodo_montagem if feira and feira.periodo_montagem else 'Não informado',
            'Período de Desmontagem': feira.periodo_desmontagem if feira and feira.periodo_desmontagem else 'Não informado',
            'Endereço do Estande': briefing.endereco_estande or 'Não informado'
        }
        
        # Seção 2: Características do Estande
        dados_estande = {
            'Tipo de Estande': briefing.get_material_display() if hasattr(briefing, 'get_material_display') and briefing.material else 'Não informado',
            'Metragem Frente': f"{briefing.medida_frente} m" if briefing.medida_frente else 'Não informada',
            'Metragem Fundo': f"{briefing.medida_fundo} m" if briefing.medida_fundo else 'Não informada',
            'Metragem Lateral Esquerda': f"{briefing.medida_lateral_esquerda} m" if briefing.medida_lateral_esquerda else 'Não informada',
            'Metragem Lateral Direita': f"{briefing.medida_lateral_direita} m" if briefing.medida_lateral_direita else 'Não informada',
            'Área Total': f"{briefing.area_estande} m²" if briefing.area_estande else 'Não informada',
            'Orçamento': f"R$ {briefing.orcamento:,.2f}".replace(',', '.').replace('.', ',') if briefing.orcamento else 'Não informado',
            'Estilo': briefing.estilo_estande or 'Não informado',
            'Piso Elevado': briefing.get_piso_elevado_display() if hasattr(briefing, 'get_piso_elevado_display') and briefing.piso_elevado else 'Não informado',
            'Tipo de Testeira': briefing.get_tipo_testeira_display() if hasattr(briefing, 'get_tipo_testeira_display') and briefing.tipo_testeira else 'Não informado',
            'Tipo de Venda': briefing.get_tipo_venda_display() if hasattr(briefing, 'get_tipo_venda_display') and briefing.tipo_venda else 'Não informado',
            'Tipo de Ativação': briefing.tipo_ativacao or 'Não informado',
            'Objetivo': briefing.objetivo_estande or 'Não informado',
        }
        
        # Seção 3: Áreas do Estande
        dados_areas = {}
        
        # Áreas de Exposição
        areas_exposicao = []
        if hasattr(briefing, 'areas_exposicao'):
            for area in briefing.areas_exposicao.all():
                area_info = {
                    'Metragem': f"{area.metragem} m²" if area.metragem else 'Não informada',
                    'Equipamentos': area.equipamentos or 'Não informados',
                    'Observações': area.observacoes or 'Nenhuma observação',
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
        
        # Seção 4: Dados complementares 
        dados_complementares = {
            'Objetivo do Evento': briefing.objetivo_evento or projeto.descricao or 'Não informado',
            'Referências Visuais': briefing.referencias_dados or 'Não informado',
            'Logotipo': briefing.logotipo or 'Não informado',
            'Campanha': briefing.campanha_dados or 'Não informado',
        }
        
        # Arquivos de referência
        arquivos_referencias = []
        imagens_referencias = []

        if hasattr(briefing, 'arquivos'):
            for arquivo in briefing.arquivos.all():
                tipo_display = arquivo.get_tipo_display() if hasattr(arquivo, 'get_tipo_display') else arquivo.tipo
                arquivos_referencias.append({
                    'nome': arquivo.nome,
                    'tipo': tipo_display,
                    'observacoes': arquivo.observacoes or 'Sem observações'
                })

                # Verifica se é imagem para galeria
                tipos_imagem = ['imagem', 'referencia', 'campanha', 'logo']
                if any(t in arquivo.tipo.lower() for t in tipos_imagem):
                    try:
                        imagens_referencias.append({
                            'url': arquivo.arquivo.url,
                            'nome': arquivo.nome,
                            'tipo': tipo_display
                        })
                    except Exception as e:
                        logger.warning(f"Arquivo {arquivo.nome} não possui URL válida: {e}")
        
        # Contexto para o template
        context = {
            'empresa': empresa,
            'projeto': projeto,
            'briefing': briefing,
            'secoes': [
                {'titulo': 'Informações do Evento', 'dados': dados_evento},
                {'titulo': 'Características do Estande', 'dados': dados_estande},
                {'titulo': 'Áreas do Estande', 'dados': dados_areas},
                {'titulo': 'Informações Complementares', 'dados': dados_complementares},
            ],
            'arquivos': arquivos_referencias,
            'imagens_referencias': imagens_referencias,
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
                    CSS(string='''
                        @page {
                            size: A4;
                            margin: 1cm;
                            @top-center {
                                content: "Briefing - Projeto #''' + str(projeto.numero) + '''";
                                font-family: Arial;
                                font-size: 10pt;
                            }
                            @bottom-center {
                                content: "Página " counter(page) " de " counter(pages);
                                font-family: Arial;
                                font-size: 10pt;
                            }
                        }
                        /* Removido o page-break-inside: avoid para permitir que o conteúdo flua naturalmente */
                    ''')
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
    
    # Obtém o briefing mais recente/ativo
    try:
        briefing = Briefing.objects.filter(projeto=projeto).order_by('-updated_at').first()
        if not briefing:
            return JsonResponse({'success': False, 'message': 'Este projeto não possui um briefing iniciado.'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro ao obter briefing: {str(e)}'})
        
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
@require_POST
def upload_arquivo_referencia(request, projeto_id):
    """
    View para fazer upload de um arquivo de referência para o briefing
    Versão melhorada para suportar diferentes tipos de arquivo com tratamento unificado
    """
    # Obtém a empresa do usuário logado
    empresa = request.user.empresa
    
    # Obtém o projeto e verifica se pertence à mesma empresa
    projeto = get_object_or_404(Projeto, pk=projeto_id, empresa=empresa)
    
    # Verifica se o projeto tem um briefing associado e obtém o briefing mais recente
    try:
        # Tenta obter o briefing ativo/mais recente
        briefing = Briefing.objects.filter(projeto=projeto).order_by('-updated_at').first()
        if not briefing:
            return JsonResponse({'success': False, 'message': 'Este projeto não possui um briefing iniciado.'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro ao obter briefing: {str(e)}'})
    
    # Processa o upload
    if request.method == 'POST' and request.FILES.get('arquivo'):
        arquivo_file = request.FILES.get('arquivo')
        tipo = request.POST.get('tipo', 'outro')
        nome = request.POST.get('nome') or arquivo_file.name
        observacoes = request.POST.get('observacoes', '')
        
        # Validações
        tipos_validos = ['mapa', 'planta', 'referencia', 'campanha', 'logo', 'imagem', 'outro']
        if tipo not in tipos_validos:
            return JsonResponse({'success': False, 'message': f'Tipo de arquivo inválido. Tipos permitidos: {", ".join(tipos_validos)}'})
        
        # Verificar tamanho do arquivo (opcional, ajuste conforme necessário)
        max_size = getattr(settings, 'MAX_UPLOAD_SIZE', 10 * 1024 * 1024)  # 10MB por padrão
        if arquivo_file.size > max_size:
            return JsonResponse({'success': False, 'message': f'Arquivo muito grande. Tamanho máximo: {max_size/1024/1024}MB'})
        
        # Verificar se tipo deve ser único (mapa ou planta)
        # Se for, excluir os anteriores
        if tipo in ['mapa', 'planta']:
            # Remove arquivos existentes do mesmo tipo
            existentes = BriefingArquivoReferencia.objects.filter(
                briefing=briefing, 
                tipo=tipo
            )
            if existentes.exists():
                for existente in existentes:
                    existente.delete()
        
        # Criar o novo arquivo
        try:
            arquivo = BriefingArquivoReferencia(
                briefing=briefing,
                nome=nome,
                arquivo=arquivo_file,
                tipo=tipo,
                observacoes=observacoes
            )
            arquivo.save()


            return JsonResponse({
                'success': True,
                'arquivo': {
                    'id': arquivo.id,
                    'nome': arquivo.nome,
                    'url': arquivo.arquivo.url,
                    'tipo': arquivo.tipo
                }
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'message': f'Erro ao salvar arquivo: {str(e)}'})
    
    return JsonResponse({'success': False, 'message': 'Requisição inválida. Verifique os parâmetros enviados.'})

@login_required
@require_POST
def excluir_arquivo_referencia(request, arquivo_id):
    """
    View para excluir um arquivo de referência do briefing
    """
    # Obtém a empresa do usuário logado
    empresa = request.user.empresa
    
    try:
        # Obtém o arquivo, garantindo que pertence a um briefing de um projeto da mesma empresa
        arquivo = get_object_or_404(BriefingArquivoReferencia, 
                                id=arquivo_id, 
                                briefing__projeto__empresa=empresa)
        
        # Armazenar algumas informações para a resposta
        arquivo_info = {
            'id': arquivo.id,
            'nome': arquivo.nome,
            'tipo': arquivo.tipo
        }
        
        # Exclui o arquivo
        arquivo.delete()
        
        return JsonResponse({'success': True, 'message': 'Arquivo excluído com sucesso!', 'arquivo': arquivo_info})
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro ao excluir arquivo: {str(e)}'})

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