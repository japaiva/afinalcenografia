# views/briefing.py

import json
import os

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
    Briefing, AreaExposicao, SalaReuniao, Copa, Deposito, Palco, Workshop,
    BriefingArquivoReferencia, BriefingValidacao, BriefingConversation
)

from projetos.forms.briefing import (
    BriefingEtapa1Form, BriefingEtapa2Form,
    BriefingEtapa3Form, BriefingEtapa4Form,
    BriefingArquivoReferenciaForm, BriefingMensagemForm,
    CopaForm, DepositoForm, PalcoForm, WorkshopForm
)

# validar_secao_briefing agora está definida abaixo neste arquivo

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

@login_required
@cliente_required
def briefing_etapa(request, projeto_id, etapa):
    """Gerencia cada etapa do briefing - VERSÃO FINAL"""
    from projetos.services.briefing_service import proxima_etapa_logica, obter_titulo_etapa

    projeto = get_object_or_404(Projeto, pk=projeto_id, empresa=request.user.empresa)

    try:
        briefing = Briefing.objects.get(projeto=projeto)
        logger.debug(f"Briefing {briefing.id} carregado - Endereço: '{briefing.endereco_estande}'")
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
            # Usar o processador de áreas (código refatorado)
            from projetos.services.briefing_areas_processor import BriefingAreasProcessor

            form = form_class(request.POST)
            if form.is_valid():
                with transaction.atomic():
                    # Processar todas as áreas usando o novo processador
                    processor = BriefingAreasProcessor(request, briefing)
                    stats = processor.process_all_areas()

                    # Atualizar etapa atual
                    briefing.etapa_atual = etapa
                    briefing.save()

                    logger.debug(f"Etapa 3 salva - Endereço: '{briefing.endereco_estande}', Áreas: {stats}")
            else:
                logger.warning(f"Form etapa 3 inválido: {form.errors}")

        else:
            # Para outras etapas, usar o formulário normalmente
            # DEBUG: Ver o que está vindo no POST
            if etapa == 1:
                logger.debug(f"POST data - endereco_estande: '{request.POST.get('endereco_estande')}'")
                logger.debug(f"POST keys: {list(request.POST.keys())}")

            form = form_class(request.POST, request.FILES, instance=briefing)
            if form.is_valid():
                # DEBUG: Ver o que está no form.cleaned_data
                if etapa == 1:
                    logger.debug(f"Form cleaned_data - endereco_estande: '{form.cleaned_data.get('endereco_estande')}'")

                briefing_saved = form.save()
                briefing_saved.etapa_atual = etapa
                briefing_saved.save()

                # Log de salvamento
                if etapa == 1:
                    logger.debug(f"Etapa 1 salva - Endereço: '{briefing_saved.endereco_estande}'")
            else:
                logger.warning(f"Form etapa {etapa} inválido: {form.errors}")

        if 'avancar' in request.POST and etapa < 4:
            briefing.refresh_from_db()
            logger.debug(f"Avançando para próxima etapa - Endereço: '{briefing.endereco_estande}'")
            return redirect('cliente:briefing_etapa', projeto_id=projeto.id, etapa=proxima_etapa_logica(projeto.tipo_projeto, etapa))
        elif 'concluir' in request.POST:
            return redirect('cliente:concluir_briefing', projeto_id=projeto.id)

    else:
        # GET request - exibir formulário

        if etapa == 3:
            form = BriefingEtapa3Form(initial={
                'tem_area_exposicao': AreaExposicao.objects.filter(briefing=briefing).exists(),
                'tem_sala_reuniao': SalaReuniao.objects.filter(briefing=briefing).exists(),
                'tem_palco': Palco.objects.filter(briefing=briefing).exists(),
                'tem_workshop': Workshop.objects.filter(briefing=briefing).exists(),
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
        # Usar o processador para obter dados de contexto
        from projetos.services.briefing_areas_processor import BriefingAreasProcessor

        processor = BriefingAreasProcessor(request, briefing)
        areas_context = processor.get_context_data()

        # Adicionar forms específicos para Copa e Depósito
        copa = areas_context.get('copa')
        deposito = areas_context.get('deposito')

        areas_context.update({
            'copa_form': CopaForm(instance=copa) if copa else CopaForm(prefix='copa'),
            'deposito_form': DepositoForm(instance=deposito) if deposito else DepositoForm(prefix='deposito'),
            'palco_form': PalcoForm(prefix='palco'),
            'workshop_form': WorkshopForm(prefix='workshop'),
        })

        context.update(areas_context)

    # Renderiza template dinâmico por etapa
    template_name = f'cliente/briefing_etapa{etapa}.html'
    return render(request, template_name, context)
# ==================== FUNÇÕES MOVIDAS DE projetos/views/briefing_views.py ====================

# Imports adicionais necessários
import os
try:
    from core.utils.llm_utils import get_llm_client
except ImportError:
    get_llm_client = None

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

from core.services.extracao_service import eh_pergunta_relacionada_a_feira
from core.models import Feira, Agente
from core.services.rag_service import RAGService

@login_required
@cliente_required
def enviar_mensagem_ia(request, projeto_id):
    """
    View para processar mensagens enviadas para o assistente IA
    """
    if request.method == 'POST':
        mensagem = request.POST.get('mensagem', '')
    else:
        mensagem = request.GET.get('mensagem', '')  # Compatibilidade para GET
    
    etapa = int(request.POST.get('etapa', 1))
    projeto = get_object_or_404(Projeto, pk=projeto_id, empresa=request.user.empresa)
    briefing = get_object_or_404(Briefing, projeto=projeto)
    
    # Obtém conversas anteriores para contexto
    conversas_anteriores = BriefingConversation.objects.filter(
        briefing=briefing
    ).order_by('-timestamp')[:5]
    
    # Salvar a mensagem do cliente
    mensagem_cliente = BriefingConversation.objects.create(
        briefing=briefing,
        mensagem=mensagem,
        origem='cliente',
        etapa=etapa
    )
    
    # Busca um agente adequado no banco de dados
    try:
        # Obtém o cliente LLM, modelo e configurações do agente "Assistente de Briefing"
        client, model, temperature, system_prompt, task_instructions = get_llm_client("Assistente de Briefing")
        if client is None:
            raise ValueError("Não foi possível inicializar o cliente LLM para o agente 'Assistente de Briefing'")
    except Exception as e:
        # Fallback para cliente OpenAI padrão se não conseguir obter o cliente do agente
        logger.warning(f"Erro ao obter cliente LLM: {str(e)}. Usando cliente padrão.")
        if OPENAI_AVAILABLE:
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key:
                logger.error("API Key do OpenAI não encontrada!")
                raise ValueError("API Key do OpenAI não encontrada")
            client = OpenAI(api_key=api_key)
            model = "gpt-4o-mini"
            temperature = 0.7
            system_prompt = "Você é um assistente especializado em projetos cenográficos da Afinal Cenografia."
            task_instructions = None
        else:
            # Se OpenAI não estiver disponível, usar resposta básica
            texto_resposta = "Lamento, mas estou enfrentando dificuldades técnicas no momento. Nossa equipe já está trabalhando nisso. Por favor, tente novamente em alguns instantes ou continue preenchendo o formulário normalmente."
            mensagem_ia = BriefingConversation.objects.create(
                briefing=briefing,
                mensagem=texto_resposta,
                origem='ia',
                etapa=etapa
            )
            return JsonResponse({
                'success': True,
                'mensagem_cliente': {
                    'id': mensagem_cliente.id,
                    'texto': mensagem_cliente.mensagem,
                    'timestamp': mensagem_cliente.timestamp.strftime('%H:%M')
                },
                'mensagem_ia': {
                    'id': mensagem_ia.id,
                    'texto': mensagem_ia.mensagem,
                    'timestamp': mensagem_ia.timestamp.strftime('%H:%M')
                }
            })
    
    # Construir o contexto para o assistente
    contexto = system_prompt + "\n\n"
    contexto += f"Você está ajudando o cliente a preencher um briefing para o projeto '{projeto.nome}'. "
    
    # Adicionar informações do briefing para contexto
    if etapa == 1:
        contexto += "O cliente está na etapa de definição do LOCAL DO ESTANDE (onde fica o estande no pavilhão). "
    elif etapa == 2:
        contexto += "O cliente está na etapa de definição das CARACTERÍSTICAS do estande (dimensões, estilo, etc). "
    elif etapa == 3:
        contexto += "O cliente está na etapa de definição das DIVISÕES do estande (área de exposição, sala reunião, etc). "
    elif etapa == 4:
        contexto += "O cliente está na etapa de REFERÊNCIAS VISUAIS (referências, logotipo, campanha). "
    
    # Adicionar task_instructions se disponível
    if task_instructions:
        # Substituir variáveis no template de instruções
        instrucoes = task_instructions.replace("{nome_projeto}", projeto.nome)
        instrucoes = instrucoes.replace("{etapa_atual}", str(etapa))
        contexto += instrucoes
    else:
        # Instrução padrão se não houver task_instructions
        contexto += "Sua função é auxiliar o cliente a fornecer informações claras e completas para o briefing. "
        contexto += "Responda perguntas sobre o processo, sugira ideias quando solicitado e ajude a esclarecer dúvidas. "
        contexto += "Seja amigável, profissional e focado em ajudar o cliente a ter sucesso em seu projeto cenográfico."
    
    try:
        # Construir histórico de mensagens
        mensagens_formatadas = []
        
        # Adicionar mensagens anteriores ao histórico
        for conv in reversed(list(conversas_anteriores)):
            if conv.origem == "cliente":
                mensagens_formatadas.append({"role": "user", "content": conv.mensagem})
            else:
                mensagens_formatadas.append({"role": "assistant", "content": conv.mensagem})
        
        # Adicionar a mensagem atual
        mensagens_formatadas.append({"role": "user", "content": mensagem})
        
        # Enviar para a API apropriada com base no provider do cliente
        if hasattr(client, 'chat') and hasattr(client.chat, 'completions'):  # OpenAI
            logger.info(f"Enviando requisição para OpenAI (modelo: {model})")
            resposta = client.chat.completions.create(
                model=model,
                messages=[{"role": "system", "content": contexto}] + mensagens_formatadas,
                max_tokens=1000,
                temperature=temperature
            )
            texto_resposta = resposta.choices[0].message.content
            logger.info("Resposta recebida da OpenAI com sucesso")
            
        elif hasattr(client, 'messages') and hasattr(client.messages, 'create'):  # Anthropic
            logger.info(f"Enviando requisição para Anthropic (modelo: {model})")
            resposta = client.messages.create(
                model=model,
                system=contexto,
                messages=mensagens_formatadas,
                max_tokens=1000,
                temperature=temperature
            )
            texto_resposta = resposta.content[0].text
            logger.info("Resposta recebida da Anthropic com sucesso")
            
        else:
            # Provedor desconhecido ou não suportado
            logger.warning("Provedor de IA desconhecido ou não suportado")
            texto_resposta = "Olá! Sou o assistente de briefing. Infelizmente, estou encontrando um problema técnico no momento. Nossa equipe já está trabalhando nisso. Por favor, tente novamente mais tarde ou continue preenchendo o formulário normalmente."
            
    except Exception as e:
        logger.error(f"Erro ao processar mensagem com IA: {str(e)}")
        texto_resposta = f"Desculpe, não consegui processar sua pergunta no momento. Por favor, tente novamente mais tarde ou entre em contato com nossa equipe para assistência."
    
    # Salvar a resposta da IA
    mensagem_ia = BriefingConversation.objects.create(
        briefing=briefing,
        mensagem=texto_resposta,
        origem='ia',
        etapa=etapa
    )
    
    return JsonResponse({
        'success': True,
        'mensagem_cliente': {
            'id': mensagem_cliente.id,
            'texto': mensagem_cliente.mensagem,
            'timestamp': mensagem_cliente.timestamp.strftime('%H:%M')
        },
        'mensagem_ia': {
            'id': mensagem_ia.id,
            'texto': mensagem_ia.mensagem,
            'timestamp': mensagem_ia.timestamp.strftime('%H:%M')
        }
    })


@login_required
@cliente_required
def limpar_conversas_briefing(request, projeto_id):
    """Limpa o histórico de conversas do briefing"""
    projeto = get_object_or_404(Projeto, pk=projeto_id, empresa=request.user.empresa)
    briefing = get_object_or_404(Briefing, projeto=projeto)
    
    # Manter apenas a mensagem de boas-vindas 
    # (a primeira mensagem da IA)
    primeira_mensagem = BriefingConversation.objects.filter(
        briefing=briefing, 
        origem='ia'
    ).order_by('timestamp').first()
    
    if primeira_mensagem:
        # Excluir todas as outras mensagens
        BriefingConversation.objects.filter(
            briefing=briefing
        ).exclude(id=primeira_mensagem.id).delete()
    
    # Redirecionar de volta para a etapa atual
    return redirect('cliente:briefing_etapa', 
                   projeto_id=projeto.id, 
                   etapa=briefing.etapa_atual)


@login_required
@cliente_required
@require_POST
def perguntar_manual(request):
    """
    Recebe uma pergunta sobre o manual da feira e retorna uma resposta usando RAG.
    """
    try:
        data = json.loads(request.body)
        pergunta = data.get('pergunta')
        feira_id = data.get('feira_id')
        
        if not pergunta:
            return JsonResponse({'success': False, 'message': 'Forneça uma pergunta.'}, status=400)
        if not feira_id:
            return JsonResponse({'success': False, 'message': 'Especifique uma feira.'}, status=400)
        
        feira = get_object_or_404(Feira, pk=feira_id)
        if not feira.chunks_processados:
            return JsonResponse({
                'success': False,
                'message': 'O manual desta feira ainda não foi totalmente processado.'
            })
        
        # Usar o agente específico para RAG de feiras
        agente_nome = 'Assistente RAG de Feiras'
        try:
            agente = Agente.objects.get(nome=agente_nome, ativo=True)
        except Agente.DoesNotExist:
            # Fallback para outro agente
            agente_nome = 'Assistente de Briefing'
        
        # Inicializar o serviço RAG com o agente apropriado
        rag_service = RAGService(agent_name=agente_nome)
        rag_result = rag_service.gerar_resposta_rag(pergunta, feira_id)
        
        # Verificar resultados
        if rag_result.get('status') == 'error':
            return JsonResponse({'success': False, 'message': rag_result.get('error')})
        if rag_result.get('status') == 'no_results':
            return JsonResponse({
                'success': True,
                'resposta': 'Não encontrei informações específicas sobre isso no manual da feira.',
                'contextos': [],
                'agente_usado': agente_nome
            })
        
        # Buscar o projeto e o briefing associados à feira
        projeto = get_object_or_404(Projeto, feira_id=feira_id, empresa=request.user.empresa)
        briefing = get_object_or_404(Briefing, projeto=projeto)
        
        # Salvar a interação no histórico de conversa
        BriefingConversation.objects.create(
            briefing=briefing,
            mensagem=f"Sobre o manual: {pergunta}",
            origem='cliente',
            etapa=briefing.etapa_atual
        )
        
        # Salvar a resposta no histórico
        BriefingConversation.objects.create(
            briefing=briefing,
            mensagem=rag_result['resposta'],
            origem='ia',
            etapa=briefing.etapa_atual
        )
        
        return JsonResponse({
            'success': True,
            'resposta': rag_result['resposta'],
            'contextos': rag_result['contextos'],
            'status': rag_result['status'],
            'agente_usado': agente_nome
        })
        
    except Exception as e:
        logger.error(f"Erro ao responder pergunta sobre manual: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f"Erro ao processar consulta: {str(e)}"
        }, status=500)
def validar_secao_briefing(briefing, secao):
    """
    Função que valida uma seção do briefing usando APENAS campos que existem no modelo
    """
    import json
    import re
    
    # Obtém o objeto de validação existente ou cria um novo
    validacao, created = BriefingValidacao.objects.get_or_create(
        briefing=briefing,
        secao=secao,
        defaults={'status': 'pendente'}
    )
    
    # Tenta carregar o cliente LLM
    usar_ia = False
    try:
        if get_llm_client:
            client, model, temperature, system_prompt, task_instructions = get_llm_client("Validador de Briefing")
            usar_ia = client is not None
    except Exception as e:
        logger.error(f"Erro ao obter cliente LLM para validação: {str(e)}")
        usar_ia = False
    
    # Verificação básica (sem IA)
    if not usar_ia:
        logger.info(f"Usando validação básica para a seção '{secao}' do briefing {briefing.id}")
        
        if secao == 'evento':
            if briefing.projeto.tipo_projeto == 'outros' and not briefing.feira:
                # Para projetos sem feira, verificar campos manuais
                campos_preenchidos = sum([
                    bool(briefing.nome_evento),
                    bool(briefing.local_evento), 
                    bool(briefing.endereco_estande),
                    bool(briefing.data_horario_evento),
                    bool(briefing.organizador_evento),
                    bool(briefing.periodo_montagem_evento),
                    bool(briefing.periodo_desmontagem_evento)
                ])
                
                if campos_preenchidos >= 5:  # Pelo menos 5 dos 7 campos
                    validacao.status = 'aprovado'
                    validacao.mensagem = 'Informações do evento completas.'
                else:
                    validacao.status = 'atencao'
                    validacao.mensagem = f'Preencha mais campos do evento ({campos_preenchidos}/7 preenchidos).'
            else:
                # Para projetos com feira, só precisa do endereço do estande
                if briefing.endereco_estande:
                    validacao.status = 'aprovado'
                    validacao.mensagem = 'Localização do estande definida.'
                else:
                    validacao.status = 'atencao'
                    validacao.mensagem = 'Informe a localização do estande no pavilhão.'
        
        elif secao == 'estande':
            # Verificar se tem dimensões básicas E estilo
            tem_dimensoes = bool(briefing.medida_frente or briefing.area_estande)
            tem_estilo = bool(briefing.estilo_estande)
            
            if tem_dimensoes and tem_estilo:
                validacao.status = 'aprovado'
                validacao.mensagem = 'Características do estande definidas.'
            elif tem_dimensoes:
                validacao.status = 'atencao'
                validacao.mensagem = 'Defina o estilo/conceito do estande.'
            elif tem_estilo:
                validacao.status = 'atencao'
                validacao.mensagem = 'Informe as dimensões do estande.'
            else:
                validacao.status = 'atencao'
                validacao.mensagem = 'Defina dimensões e estilo do estande.'
        
        elif secao == 'areas_estande':
            # Verificar se tem alguma área configurada
            if hasattr(briefing, 'tem_qualquer_area_estande') and briefing.tem_qualquer_area_estande():
                validacao.status = 'aprovado'
                validacao.mensagem = 'Divisões do estande configuradas.'
            else:
                validacao.status = 'atencao'
                validacao.mensagem = 'Configure as áreas internas do estande.'
        
        elif secao == 'dados_complementares':
            # Verificar referências ou arquivos
            tem_referencias = bool(briefing.referencias_dados)
            tem_logotipo = bool(briefing.logotipo)
            tem_campanha = bool(briefing.campanha_dados)
            tem_arquivos = BriefingArquivoReferencia.objects.filter(briefing=briefing).exists()
            
            if tem_referencias or tem_arquivos or tem_logotipo or tem_campanha:
                validacao.status = 'aprovado'
                validacao.mensagem = 'Informações complementares fornecidas.'
            else:
                validacao.status = 'atencao'
                validacao.mensagem = 'Adicione referências visuais ou informações complementares.'
        
        feedback = validacao.mensagem
        
    else:
        # Validação usando IA
        logger.info(f"Usando validação com IA para a seção '{secao}' do briefing {briefing.id}")
        
        try:
            # Dados básicos sempre presentes
            briefing_data = {
                "secao": secao,
                "nome_projeto": briefing.projeto.nome,
                "tipo_projeto": briefing.projeto.tipo_projeto,
            }
            
            # Campos específicos por seção (APENAS os que existem)
            if secao == 'evento':
                briefing_data.update({
                    "endereco_estande": briefing.endereco_estande,
                    "tem_feira_associada": briefing.feira is not None,
                })
                
                if briefing.feira:
                    briefing_data.update({
                        "nome_feira": briefing.feira.nome,
                        "local_feira": briefing.feira.local,
                    })
                
                # Campos para eventos manuais (tipo 'outros')
                briefing_data.update({
                    "nome_evento": briefing.nome_evento,
                    "local_evento": briefing.local_evento,
                    "organizador_evento": briefing.organizador_evento,
                    "data_horario_evento": briefing.data_horario_evento,
                    "periodo_montagem_evento": briefing.periodo_montagem_evento,
                    "periodo_desmontagem_evento": briefing.periodo_desmontagem_evento,
                })
                
            elif secao == 'estande':
                briefing_data.update({
                    "medida_frente": str(briefing.medida_frente) if briefing.medida_frente else None,
                    "medida_fundo": str(briefing.medida_fundo) if briefing.medida_fundo else None,
                    "medida_lateral_esquerda": str(briefing.medida_lateral_esquerda) if briefing.medida_lateral_esquerda else None,
                    "medida_lateral_direita": str(briefing.medida_lateral_direita) if briefing.medida_lateral_direita else None,
                    "area_estande": str(briefing.area_estande) if briefing.area_estande else None,
                    "estilo_estande": briefing.estilo_estande,
                    "material": briefing.get_material_display() if briefing.material else None,
                    "piso_elevado": briefing.get_piso_elevado_display() if briefing.piso_elevado else None,
                    "tipo_testeira": briefing.get_tipo_testeira_display() if briefing.tipo_testeira else None,
                    "tipo_venda": briefing.get_tipo_venda_display() if briefing.tipo_venda else None,
                    "tipo_ativacao": briefing.tipo_ativacao,
                    "tipo_stand": briefing.get_tipo_stand_display() if briefing.tipo_stand else None,
                })
                
            elif secao == 'areas_estande':
                # Areas de exposição
                areas_exposicao = []
                for area in AreaExposicao.objects.filter(briefing=briefing):
                    areas_exposicao.append({
                        "tem_lounge": area.tem_lounge,
                        "tem_vitrine_exposicao": area.tem_vitrine_exposicao,
                        "tem_balcao_recepcao": area.tem_balcao_recepcao,
                        "tem_mesas_atendimento": area.tem_mesas_atendimento,
                        "tem_balcao_cafe": area.tem_balcao_cafe,
                        "tem_balcao_vitrine": area.tem_balcao_vitrine,
                        "tem_caixa_vendas": area.tem_caixa_vendas,
                        "equipamentos": area.equipamentos,
                        "observacoes": area.observacoes,
                        "metragem": str(area.metragem) if area.metragem else None,
                    })
                
                # Salas de reunião
                salas_reuniao = []
                for sala in SalaReuniao.objects.filter(briefing=briefing):
                    salas_reuniao.append({
                        "capacidade": sala.capacidade,
                        "equipamentos": sala.equipamentos,
                        "metragem": str(sala.metragem) if sala.metragem else None,
                    })
                
                # Copas
                copas = []
                for copa in Copa.objects.filter(briefing=briefing):
                    copas.append({
                        "equipamentos": copa.equipamentos,
                        "metragem": str(copa.metragem) if copa.metragem else None,
                    })
                
                # Depósitos
                depositos = []
                for deposito in Deposito.objects.filter(briefing=briefing):
                    depositos.append({
                        "equipamentos": deposito.equipamentos,
                        "metragem": str(deposito.metragem) if deposito.metragem else None,
                    })
                
                briefing_data.update({
                    "areas_exposicao": areas_exposicao,
                    "salas_reuniao": salas_reuniao,
                    "copas": copas,
                    "depositos": depositos,
                    "total_areas": len(areas_exposicao) + len(salas_reuniao) + len(copas) + len(depositos)
                })
                
            elif secao == 'dados_complementares':
                briefing_data.update({
                    "referencias_dados": briefing.referencias_dados,
                    "logotipo": briefing.logotipo,
                    "campanha_dados": briefing.campanha_dados,
                    "arquivos": [
                        {"nome": arq.nome, "tipo": arq.get_tipo_display()}
                        for arq in BriefingArquivoReferencia.objects.filter(briefing=briefing)
                    ]
                })
            
            # Prompt otimizado para Groq
            prompt_validacao = f"""Analise a seção '{secao}' do briefing e retorne apenas um JSON válido.

DADOS: {json.dumps(briefing_data, ensure_ascii=False)}

Responda APENAS com JSON no formato:
{{"status": "aprovado|atencao|reprovado", "mensagem": "resumo", "feedback": "detalhes"}}

Critérios:
- aprovado: informações completas e consistentes
- atencao: informações incompletas mas utilizáveis  
- reprovado: informações inconsistentes ou insuficientes"""

            # Detectar provider e fazer chamada apropriada
            provider_name = "unknown"
            if hasattr(client, '__class__'):
                class_name = str(client.__class__).lower()
                if 'groq' in class_name:
                    provider_name = "groq"
                elif 'openai' in class_name:
                    provider_name = "openai"
                elif 'anthropic' in class_name:
                    provider_name = "anthropic"
            
            logger.info(f"Usando provider: {provider_name}")
            
            if provider_name == "groq":
                # Groq - sem response_format
                response = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt or "Você é um validador de briefings cenográficos."},
                        {"role": "user", "content": prompt_validacao}
                    ],
                    temperature=temperature or 0.1,
                    max_tokens=300
                )
                content = response.choices[0].message.content
                
            elif provider_name == "openai":
                # OpenAI - com response_format
                response = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt or "Você é um validador de briefings cenográficos."},
                        {"role": "user", "content": prompt_validacao}
                    ],
                    temperature=temperature or 0.1,
                    max_tokens=300,
                    response_format={"type": "json_object"}
                )
                content = response.choices[0].message.content
                
            elif provider_name == "anthropic":
                # Anthropic
                response = client.messages.create(
                    model=model,
                    system=system_prompt or "Você é um validador de briefings cenográficos.",
                    messages=[
                        {"role": "user", "content": prompt_validacao}
                    ],
                    temperature=temperature or 0.1,
                    max_tokens=300
                )
                content = response.content[0].text
                
            else:
                # Fallback genérico
                response = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt or "Você é um validador de briefings cenográficos."},
                        {"role": "user", "content": prompt_validacao}
                    ],
                    temperature=temperature or 0.1,
                    max_tokens=300
                )
                content = response.choices[0].message.content
            
            # Limpar e extrair JSON
            content = content.strip()
            content = re.sub(r'^```json\s*', '', content)
            content = re.sub(r'\s*```$', '', content)
            
            # Encontrar JSON válido
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
            else:
                json_str = content
            
            # Parse do JSON
            try:
                result = json.loads(json_str)
            except json.JSONDecodeError as e:
                logger.error(f"Erro JSON: {e}, conteúdo: {content[:200]}")
                raise Exception("Resposta da IA inválida")
            
            # Validar campos obrigatórios
            if not all(field in result for field in ['status', 'mensagem', 'feedback']):
                raise Exception("Campos obrigatórios ausentes na resposta")
            
            # Validar status
            if result['status'] not in ['aprovado', 'atencao', 'reprovado']:
                result['status'] = 'atencao'
            
            # Atualizar validação
            validacao.status = result['status']
            validacao.mensagem = result['mensagem'][:255]
            feedback = result['feedback']
            
            logger.info(f"Validação IA: {validacao.status}")
                
        except Exception as e:
            logger.error(f"Erro na validação IA: {str(e)}")
            
            # Fallback para validação básica
            if secao == 'evento':
                if briefing.endereco_estande:
                    validacao.status = 'aprovado'
                    validacao.mensagem = 'Localização verificada'
                    feedback = 'Localização do estande foi informada.'
                else:
                    validacao.status = 'atencao'
                    validacao.mensagem = 'Localização em falta'
                    feedback = 'Informe onde ficará o estande no pavilhão.'
            elif secao == 'estande':
                if briefing.area_estande and briefing.estilo_estande:
                    validacao.status = 'aprovado'
                    validacao.mensagem = 'Características básicas definidas'
                    feedback = 'Dimensões e estilo foram informados.'
                else:
                    validacao.status = 'atencao'
                    validacao.mensagem = 'Complete as características'
                    feedback = 'Defina melhor as dimensões e estilo do estande.'
            elif secao == 'areas_estande':
                if hasattr(briefing, 'tem_qualquer_area_estande') and briefing.tem_qualquer_area_estande():
                    validacao.status = 'aprovado'
                    validacao.mensagem = 'Áreas configuradas'
                    feedback = 'Divisões internas foram definidas.'
                else:
                    validacao.status = 'atencao'
                    validacao.mensagem = 'Configure as áreas'
                    feedback = 'Defina como será dividido o espaço interno.'
            else:  # dados_complementares
                if briefing.referencias_dados:
                    validacao.status = 'aprovado'
                    validacao.mensagem = 'Referências fornecidas'
                    feedback = 'Referências visuais foram informadas.'
                else:
                    validacao.status = 'atencao'
                    validacao.mensagem = 'Adicione referências'
                    feedback = 'Forneça referências visuais para o projeto.'
    
    # Salvar validação
    validacao.save()
    
    # Adicionar feedback no chat
    if feedback:
        emoji = "✅" if validacao.status == 'aprovado' else "⚠️" if validacao.status == 'atencao' else "❌"
        mensagem_chat = f"{emoji} {secao.replace('_', ' ').title()}: {feedback}"
        
        BriefingConversation.objects.create(
            briefing=briefing,
            mensagem=mensagem_chat,
            origem='ia',
            etapa=briefing.etapa_atual
        )
    
    logger.info(f"Validação '{secao}' finalizada: {validacao.status}")

