# projetos/views/briefing_views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.forms import modelformset_factory
from django.db import transaction

import json
import os
import logging

from core.decorators import cliente_required
from projetos.models.projeto import Projeto
from projetos.models.briefing import (
    Briefing, BriefingConversation, BriefingValidacao, BriefingArquivoReferencia,
    AreaExposicao, SalaReuniao, Copa, Deposito
)
from projetos.forms.briefing import (
    BriefingEtapa1Form, BriefingEtapa2Form, BriefingEtapa3Form, BriefingEtapa4Form,
    AreaExposicaoForm, SalaReuniaoForm, CopaForm, DepositoForm,
    BriefingArquivoReferenciaForm, BriefingMensagemForm
)

# Configurar logger
logger = logging.getLogger(__name__)

# Carrega cliente de IA de acordo com o ambiente
try:
    from core.utils.llm_utils import get_llm_client
except ImportError:
    logger.warning("LLM utilities not available. Using fallback.")
    get_llm_client = None
    
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("OpenAI SDK not available")

@login_required
@cliente_required
def iniciar_briefing(request, projeto_id):
    """Inicia um novo briefing ou redireciona para o briefing existente"""
    projeto = get_object_or_404(Projeto, pk=projeto_id, empresa=request.user.empresa)
    
    try:
        briefing = Briefing.objects.get(projeto=projeto)
        return redirect('cliente:briefing_etapa', projeto_id=projeto.id, etapa=briefing.etapa_atual)
    except Briefing.DoesNotExist:
        # Criar novo briefing
        briefing = Briefing.objects.create(
            projeto=projeto,
            status='rascunho',
            etapa_atual=1
        )
        
        # Atualizar status do projeto
        projeto.status = 'briefing_pendente'
        projeto.save()
        
        # Criar validações iniciais (uma para cada seção)
        BriefingValidacao.objects.create(briefing=briefing, secao='evento', status='pendente')
        BriefingValidacao.objects.create(briefing=briefing, secao='estande', status='pendente')
        BriefingValidacao.objects.create(briefing=briefing, secao='areas_estande', status='pendente')
        BriefingValidacao.objects.create(briefing=briefing, secao='dados_complementares', status='pendente')
        
        # Mensagem de boas-vindas da IA
        BriefingConversation.objects.create(
            briefing=briefing,
            mensagem="Olá! Sou o assistente do briefing. Estou aqui para ajudá-lo a preencher todas as informações do seu projeto. Vamos começar com as informações do evento!",
            origem='ia',
            etapa=1
        )
        
        return redirect('cliente:briefing_etapa', projeto_id=projeto.id, etapa=1)

@login_required
@cliente_required
def briefing_etapa(request, projeto_id, etapa):
    """Gerencia cada etapa do briefing"""
    projeto = get_object_or_404(Projeto, pk=projeto_id, empresa=request.user.empresa)
    
    try:
        briefing = Briefing.objects.get(projeto=projeto)
    except Briefing.DoesNotExist:
        return redirect('cliente:iniciar_briefing', projeto_id=projeto.id)
    
    etapa = int(etapa)
    
    if etapa < 1 or etapa > 4:
        etapa = 1
    
    # Definir a seção baseada na etapa
    if etapa == 1:
        form_class = BriefingEtapa1Form
        secao = 'evento'
    elif etapa == 2:
        form_class = BriefingEtapa2Form
        secao = 'estande'
    elif etapa == 3:
        form_class = BriefingEtapa3Form  # Form especial que lida com múltiplas áreas
        secao = 'areas_estande'
    else:  # etapa == 4
        form_class = BriefingEtapa4Form
        secao = 'dados_complementares'
    
    if request.method == 'POST':
        # Processamento diferente para a etapa 3 que lida com múltiplas áreas
        if etapa == 3:
            form = form_class(request.POST)
            if form.is_valid():
                with transaction.atomic():
                    # Processar checkboxes principais
                    tem_area_exposicao = form.cleaned_data.get('tem_area_exposicao', False)
                    tem_sala_reuniao = form.cleaned_data.get('tem_sala_reuniao', False)
                    tem_copa = form.cleaned_data.get('tem_copa', False)
                    tem_deposito = form.cleaned_data.get('tem_deposito', False)
                    
                    # Limpar áreas existentes se desmarcadas
                    if not tem_area_exposicao:
                        AreaExposicao.objects.filter(briefing=briefing).delete()
                    
                    if not tem_sala_reuniao:
                        SalaReuniao.objects.filter(briefing=briefing).delete()
                    
                    if not tem_copa:
                        Copa.objects.filter(briefing=briefing).delete()
                    
                    if not tem_deposito:
                        Deposito.objects.filter(briefing=briefing).delete()

                    # Processar múltiplas áreas de exposição
                    if tem_area_exposicao:
                        # Obter o número de áreas de exposição enviadas
                        num_areas = int(request.POST.get('num_areas_exposicao', 1))
                        
                        # Limpar áreas existentes para recriar
                        AreaExposicao.objects.filter(briefing=briefing).delete()
                        
                        # Criar cada área de exposição
                        for i in range(num_areas):
                            # Verificar se os campos para esta área foram enviados
                            if f'area_exposicao-{i}-metragem' in request.POST:
                                area = AreaExposicao(briefing=briefing)
                                
                                # Processar checkboxes
                                area.tem_lounge = request.POST.get(f'area_exposicao-{i}-tem_lounge') == 'on'
                                area.tem_vitrine_exposicao = request.POST.get(f'area_exposicao-{i}-tem_vitrine_exposicao') == 'on'
                                area.tem_balcao_recepcao = request.POST.get(f'area_exposicao-{i}-tem_balcao_recepcao') == 'on'
                                area.tem_mesas_atendimento = request.POST.get(f'area_exposicao-{i}-tem_mesas_atendimento') == 'on'
                                area.tem_balcao_cafe = request.POST.get(f'area_exposicao-{i}-tem_balcao_cafe') == 'on'
                                area.tem_balcao_vitrine = request.POST.get(f'area_exposicao-{i}-tem_balcao_vitrine') == 'on'
                                area.tem_caixa_vendas = request.POST.get(f'area_exposicao-{i}-tem_caixa_vendas') == 'on'
                                
                                # Campos de texto
                                area.equipamentos = request.POST.get(f'area_exposicao-{i}-equipamentos', '')
                                area.observacoes = request.POST.get(f'area_exposicao-{i}-observacoes', '')
                                
                                # Conversão segura de decimal
                                try:
                                    area.metragem = float(request.POST.get(f'area_exposicao-{i}-metragem', 0))
                                except (ValueError, TypeError):
                                    area.metragem = 0
                                
                                area.save()

                    # Processar múltiplas salas de reunião
                    if tem_sala_reuniao:
                        # Obter o número de salas de reunião enviadas
                        num_salas = int(request.POST.get('num_salas_reuniao', 1))
                        
                        # Limpar salas existentes para recriar
                        SalaReuniao.objects.filter(briefing=briefing).delete()
                        
                        # Criar cada sala de reunião
                        for i in range(num_salas):
                            # Verificar se os campos para esta sala foram enviados
                            if f'sala_reuniao-{i}-capacidade' in request.POST:
                                sala = SalaReuniao(briefing=briefing)
                                
                                # Processar campos
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
                    
                    # Lógica para copa
                    if tem_copa and 'copa-equipamentos' in request.POST:
                        # Se não existir uma copa, criar uma
                        if not Copa.objects.filter(briefing=briefing).exists():
                            copa = Copa(briefing=briefing)
                        else:
                            copa = Copa.objects.get(briefing=briefing)
                        
                        # Atualizar campos manualmente
                        copa.equipamentos = request.POST.get('copa-equipamentos', '')
                        
                        try:
                            copa.metragem = float(request.POST.get('copa-metragem', 0))
                        except (ValueError, TypeError):
                            copa.metragem = 0
                        
                        copa.save()
                    
                    # Lógica para depósito
                    if tem_deposito and 'deposito-equipamentos' in request.POST:
                        # Se não existir um depósito, criar um
                        if not Deposito.objects.filter(briefing=briefing).exists():
                            deposito = Deposito(briefing=briefing)
                        else:
                            deposito = Deposito.objects.get(briefing=briefing)
                        
                        # Atualizar campos manualmente
                        deposito.equipamentos = request.POST.get('deposito-equipamentos', '')
                        
                        try:
                            deposito.metragem = float(request.POST.get('deposito-metragem', 0))
                        except (ValueError, TypeError):
                            deposito.metragem = 0
                        
                        deposito.save()
                
                # Atualizar etapa atual
                briefing.etapa_atual = etapa
                briefing.save()
                
                # Validar a seção
                validar_secao_briefing(briefing, secao)
                
                #messages.success(request, f'Etapa {etapa} salva com sucesso!')
                
                if 'avancar' in request.POST and etapa < 4:
                    return redirect('cliente:briefing_etapa', projeto_id=projeto.id, etapa=etapa+1)
                elif 'concluir' in request.POST and etapa == 4:
                    return redirect('cliente:concluir_briefing', projeto_id=projeto.id)
        else:
            # Processamento normal para outras etapas
            form = form_class(request.POST, request.FILES, instance=briefing)
            if form.is_valid():
                form.save()
                
                # Atualizar etapa atual
                briefing.etapa_atual = etapa
                briefing.save()
                
                # Validar a seção
                validar_secao_briefing(briefing, secao)
                
                #messages.success(request, f'Etapa {etapa} salva com sucesso!')
                
                if 'avancar' in request.POST and etapa < 4:
                    return redirect('cliente:briefing_etapa', projeto_id=projeto.id, etapa=etapa+1)
                elif 'concluir' in request.POST and etapa == 4:
                    return redirect('cliente:concluir_briefing', projeto_id=projeto.id)
    else:
        # Lógica para exibir o formulário
        if etapa == 3:
            # Para a etapa 3, precisamos verificar se já existem áreas cadastradas
            form = BriefingEtapa3Form(initial={
                'tem_area_exposicao': AreaExposicao.objects.filter(briefing=briefing).exists(),
                'tem_sala_reuniao': SalaReuniao.objects.filter(briefing=briefing).exists(),
                'tem_copa': Copa.objects.filter(briefing=briefing).exists(),
                'tem_deposito': Deposito.objects.filter(briefing=briefing).exists(),
            })
            
            # Buscar todas as áreas existentes
            areas_exposicao = list(AreaExposicao.objects.filter(briefing=briefing))
            salas_reuniao = list(SalaReuniao.objects.filter(briefing=briefing))
            
            # Se não existirem áreas ou salas, criar placeholders para o template
            if not areas_exposicao:
                areas_exposicao = [None]  # Placeholder para o template
                
            if not salas_reuniao:
                salas_reuniao = [None]  # Placeholder para o template

            # Adicione estas linhas aqui para eliminar a advertência
            area_exposicao_form = None  # Inicializa com None para evitar advertência
            sala_reuniao_form = None    # Inicializa com None para evitar advertência
            
            try:
                copa = Copa.objects.get(briefing=briefing)
                copa_form = CopaForm(instance=copa, prefix='copa')
            except Copa.DoesNotExist:
                copa_form = CopaForm(prefix='copa')
            
            try:
                deposito = Deposito.objects.get(briefing=briefing)
                deposito_form = DepositoForm(instance=deposito, prefix='deposito')
            except Deposito.DoesNotExist:
                deposito_form = DepositoForm(prefix='deposito')
        else:
            # Para outras etapas, usar o form normal
            form = form_class(instance=briefing)
    
    # Carregar conversas e validações
    conversas = BriefingConversation.objects.filter(briefing=briefing).order_by('-timestamp')
    validacoes = BriefingValidacao.objects.filter(briefing=briefing)
    validacao_atual = validacoes.filter(secao=secao).first()
    
    # Carregar arquivos de referência
    arquivos = BriefingArquivoReferencia.objects.filter(briefing=briefing)
    
    # Preparar contexto da view
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
    
    # Adicionar formulários específicos da etapa 3
    if etapa == 3:
        context.update({
            'area_exposicao_form': area_exposicao_form if 'area_exposicao_form' in locals() else None,
            'sala_reuniao_form': sala_reuniao_form if 'sala_reuniao_form' in locals() else None,
            'copa_form': copa_form,
            'deposito_form': deposito_form,
            'areas_exposicao': areas_exposicao,
            'salas_reuniao': salas_reuniao,
            'num_areas_exposicao': len(areas_exposicao),
            'num_salas_reuniao': len(salas_reuniao),
        })
    
    #return render(request, 'cliente/briefing_etapa.html', context)

    template_name = f'cliente/briefing_etapa{etapa}.html'
    return render(request, template_name, context)

@login_required
@cliente_required
@require_POST
def enviar_mensagem_ia(request, projeto_id):
    """Processa mensagem enviada para o assistente IA"""
    mensagem = request.POST.get('mensagem', '')
    
    projeto = get_object_or_404(Projeto, pk=projeto_id, empresa=request.user.empresa)
    briefing = get_object_or_404(Briefing, projeto=projeto)
    
    # Obtém conversas anteriores para contexto
    conversas_anteriores = BriefingConversation.objects.filter(
        briefing=briefing
    ).order_by('-timestamp')[:5]
    
    # Tenta obter um cliente de IA configurado
    try:
        if get_llm_client:
            # Obtém o cliente LLM, modelo e configurações do agente "Assistente de Briefing"
            client, model, temperature, system_prompt, task_instructions = get_llm_client("Assistente de Briefing")
        else:
            # Fallback para OpenAI se get_llm_client não estiver disponível
            raise ValueError("get_llm_client não está disponível")
    except Exception as e:
        logger.warning(f"Erro ao obter cliente LLM: {str(e)}. Usando cliente padrão.")
        
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            logger.error("API Key não encontrada")
            return JsonResponse({
                'success': False,
                'error': 'Configuração de IA não disponível'
            }, status=500)
            
        if OPENAI_AVAILABLE:
            client = OpenAI(api_key=api_key)
            model = "gpt-4-turbo" if client else None
            temperature = 0.7
            system_prompt = "Você é um assistente especializado em projetos cenográficos da Afinal Cenografia."
            task_instructions = None
        else:
            logger.error("OpenAI SDK não disponível")
            return JsonResponse({
                'success': False,
                'error': 'Configuração de IA não disponível'
            }, status=500)
    
    # Construir o contexto para o assistente
    contexto = system_prompt + "\n\n"
    contexto += f"Você está ajudando o cliente a preencher um briefing para o projeto '{projeto.nome}'. "
    
    # Usar atributos que realmente existem no modelo Projeto
    if hasattr(projeto, 'orcamento') and projeto.orcamento:
        contexto += f"O projeto tem orçamento de R$ {projeto.orcamento}. "
    
    # Adicionar informações do briefing para contexto
    if briefing.etapa_atual == 1:
        contexto += "O cliente está na etapa de definição do EVENTO (datas e localização). "
    elif briefing.etapa_atual == 2:
        contexto += "O cliente está na etapa de definição do ESTANDE (características físicas). "
    elif briefing.etapa_atual == 3:
        contexto += "O cliente está na etapa de definição das ÁREAS DO ESTANDE (divisões funcionais). "
    elif briefing.etapa_atual == 4:
        contexto += "O cliente está na etapa de DADOS COMPLEMENTARES (referências visuais). "
    
    # Adicionar task_instructions se disponível
    if task_instructions:
        # Substituir variáveis no template de instruções
        instrucoes = task_instructions.replace("{nome_projeto}", projeto.nome)
        instrucoes = instrucoes.replace("{etapa_atual}", str(briefing.etapa_atual))
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
        
        # Enviar para a API apropriada
        if hasattr(client, 'chat') and hasattr(client.chat, 'completions'):  # OpenAI
            logger.info(f"Enviando requisição para OpenAI (modelo: {model})")
            resposta = client.chat.completions.create(
                model=model,
                messages=[{"role": "system", "content": contexto}] + mensagens_formatadas,
                max_tokens=1000,
                temperature=temperature
            )
            texto_resposta = resposta.choices[0].message.content
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
        else:
            # Provedor desconhecido ou não suportado
            logger.warning("Provedor de IA desconhecido ou não suportado")
            texto_resposta = "Olá! Infelizmente, estou encontrando um problema técnico. Nossa equipe já está trabalhando nisso. Por favor, tente novamente mais tarde."
    
    except Exception as e:
        logger.error(f"Erro ao processar mensagem com IA: {str(e)}")
        texto_resposta = f"Desculpe, não consegui processar sua pergunta no momento. Por favor, tente novamente mais tarde."
    
    # Salvar a mensagem do cliente
    mensagem_cliente = BriefingConversation.objects.create(
        briefing=briefing,
        mensagem=mensagem,
        origem='cliente',
        etapa=briefing.etapa_atual
    )
    
    # Salvar a resposta da IA
    mensagem_ia = BriefingConversation.objects.create(
        briefing=briefing,
        mensagem=texto_resposta,
        origem='ia',
        etapa=briefing.etapa_atual
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
def upload_arquivo_referencia(request, projeto_id):
    """Upload de arquivos de referência para o briefing"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Método não permitido'}, status=405)
    
    projeto = get_object_or_404(Projeto, pk=projeto_id, empresa=request.user.empresa)
    briefing = get_object_or_404(Briefing, projeto=projeto)
    
    form = BriefingArquivoReferenciaForm(request.POST, request.FILES)
    if not form.is_valid():
        return JsonResponse({'error': 'Formulário inválido'}, status=400)
    
    arquivo = form.save(commit=False)
    arquivo.briefing = briefing
    arquivo.nome = request.FILES['arquivo'].name
    arquivo.save()
    
    return JsonResponse({
        'success': True,
        'arquivo': {
            'id': arquivo.id,
            'nome': arquivo.nome,
            'url': arquivo.arquivo.url,
            'tipo': arquivo.get_tipo_display()
        }
    })

@login_required
@cliente_required
def excluir_arquivo_referencia(request, arquivo_id):
    """Exclui um arquivo de referência"""
    arquivo = get_object_or_404(BriefingArquivoReferencia, pk=arquivo_id)
    
    # Verificar permissão
    if arquivo.briefing.projeto.empresa != request.user.empresa:
        return JsonResponse({'error': 'Permissão negada'}, status=403)
    
    arquivo.delete()
    return JsonResponse({'success': True})

@login_required
@cliente_required
@require_POST
def validar_briefing(request, projeto_id):
    """Valida todas as seções do briefing"""
    projeto = get_object_or_404(Projeto, pk=projeto_id, empresa=request.user.empresa)
    briefing = get_object_or_404(Briefing, projeto=projeto)
    
    # Validar cada seção
    validar_secao_briefing(briefing, 'evento')
    validar_secao_briefing(briefing, 'estande')
    validar_secao_briefing(briefing, 'areas_estande')
    validar_secao_briefing(briefing, 'dados_complementares')
    
    # Verificar se todas as seções estão aprovadas
    validacoes = BriefingValidacao.objects.filter(briefing=briefing)
    todas_aprovadas = all(v.status == 'aprovado' for v in validacoes)
    
    # Atualizar status do briefing se todas forem aprovadas
    if todas_aprovadas:
        briefing.status = 'validado'
        briefing.save()
    
    return JsonResponse({
        'success': True,
        'todas_aprovadas': todas_aprovadas
    })

@login_required
@cliente_required
def concluir_briefing(request, projeto_id):
    """Tela de conclusão do briefing"""
    projeto = get_object_or_404(Projeto, pk=projeto_id, empresa=request.user.empresa)
    briefing = get_object_or_404(Briefing, projeto=projeto)
    
    validacoes = BriefingValidacao.objects.filter(briefing=briefing)
    todas_aprovadas = all(v.status == 'aprovado' for v in validacoes)
    
    if request.method == 'POST' and todas_aprovadas:
        briefing.status = 'enviado'
        briefing.save()
        
        # Atualizar status do projeto
        projeto.status = 'briefing_enviado'
        projeto.data_envio_briefing = timezone.now()
        projeto.save()
        
        messages.success(request, 'Briefing enviado com sucesso para análise!')
        return redirect('cliente:projeto_detail', pk=projeto.id)
    
    context = {
        'projeto': projeto,
        'briefing': briefing,
        'validacoes': validacoes,
        'todas_aprovadas': todas_aprovadas
    }
    
    return render(request, 'cliente/briefing_conclusao.html', context)

@login_required
@cliente_required
@require_POST
def salvar_rascunho_briefing(request, projeto_id):
    """Salva automaticamente o rascunho do briefing"""
    projeto = get_object_or_404(Projeto, pk=projeto_id, empresa=request.user.empresa)
    briefing = get_object_or_404(Briefing, projeto=projeto)
    
    # Atualizar timestamp
    briefing.save(update_fields=['updated_at'])
    
    return JsonResponse({'success': True})

def obter_titulo_etapa(etapa):
    """Retorna o título de cada etapa"""
    titulos = {
        1: 'Local Estande',
        2: 'Características',
        3: 'Divisões',
        4: 'Referências Visuais'
    }
    return titulos.get(etapa, 'Etapa do Briefing')

def validar_secao_briefing(briefing, secao):
    """
    Função que valida uma seção do briefing utilizando análise básica ou IA
    """
    import json
    
    # Obtém o objeto de validação existente ou cria um novo
    validacao, created = BriefingValidacao.objects.get_or_create(
        briefing=briefing,
        secao=secao,
        defaults={'status': 'pendente'}
    )
    
    # Tenta carregar o cliente LLM para o agente "Validador de Briefing"
    usar_ia = False
    try:
        if get_llm_client:
            # Obtém o cliente LLM, modelo e configurações
            client, model, temperature, system_prompt, task_instructions = get_llm_client("Validador de Briefing")
            
            # Se conseguiu obter o cliente, usar validação por IA
            usar_ia = client is not None
    except Exception as e:
        logger.error(f"Erro ao obter cliente LLM para validação: {str(e)}")
        usar_ia = False
    
    # Verificação básica (sem IA) como fallback
    if not usar_ia:
        logger.info(f"Usando validação básica para a seção '{secao}' do briefing {briefing.id}")
        
        if secao == 'evento':
            if briefing.endereco_estande:
                validacao.status = 'aprovado'
                validacao.mensagem = 'Informações do evento completas.'
            else:
                validacao.status = 'atencao'
                validacao.mensagem = 'Alguns campos importantes do evento estão incompletos.'
        
        elif secao == 'estande':
            if (briefing.medida_frente or briefing.area_estande) and briefing.estilo_estande:
                validacao.status = 'aprovado'
                validacao.mensagem = 'Características do estande completas.'
            else:
                validacao.status = 'atencao'
                validacao.mensagem = 'Informações sobre dimensões ou estilo do estande estão incompletas.'
        
        elif secao == 'areas_estande':
            # Verificar se existe alguma área configurada
            if briefing.tem_qualquer_area_estande():
                validacao.status = 'aprovado'
                validacao.mensagem = 'Áreas do estande definidas.'
            else:
                validacao.status = 'atencao'
                validacao.mensagem = 'Nenhuma área do estande foi configurada.'
        
        elif secao == 'dados_complementares':
            if briefing.referencias_dados:
                validacao.status = 'aprovado'
                validacao.mensagem = 'Dados complementares completos.'
            else:
                validacao.status = 'atencao'
                validacao.mensagem = 'Adicione mais informações sobre referências visuais.'
    else:
        # Validação usando o agente de IA
        logger.info(f"Usando validação com IA para a seção '{secao}' do briefing {briefing.id}")
        
        try:
            # Preparar os dados do briefing para análise
            briefing_data = {
                "secao": secao,
                "nome_projeto": briefing.projeto.nome,
                "etapa_atual": briefing.etapa_atual,
            }
            
            # Adicionar campos específicos de cada seção
            if secao == 'evento':
                # Se a feira estiver associada ao projeto
                if briefing.projeto.feira:
                    briefing_data.update({
                        "endereco_estande": briefing.endereco_estande,
                        "nome_feira": briefing.projeto.feira.nome,
                        "local_feira": briefing.projeto.feira.local,
                        "data_feira_inicio": str(briefing.projeto.feira.data_inicio) if briefing.projeto.feira.data_inicio else None,
                        "data_feira_fim": str(briefing.projeto.feira.data_fim) if briefing.projeto.feira.data_fim else None,
                        "horario_feira": briefing.projeto.feira.data_horario,
                        "promotora_feira": briefing.projeto.feira.promotora,  # Adicionando o organizador
                        "periodo_montagem": briefing.projeto.feira.periodo_montagem,
                        "periodo_desmontagem": briefing.projeto.feira.periodo_desmontagem,
                    })
                else:
                    # Se não houver feira associada
                    briefing_data.update({
                        "endereco_estande": briefing.endereco_estande,
                        "nome_feira": None,
                        "local_feira": None,
                        "data_feira_inicio": None,
                        "data_feira_fim": None,
                        "horario_feira": None,
                        "promotora_feira": None,  # Adicionando o organizador
                        "periodo_montagem": None,
                        "periodo_desmontagem": None,
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
                    "objetivo_estande": briefing.objetivo_estande,
                })
            elif secao == 'areas_estande':
                # Dados das áreas de exposição
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
                
                # Dados das salas de reunião
                salas_reuniao = []
                for sala in SalaReuniao.objects.filter(briefing=briefing):
                    salas_reuniao.append({
                        "capacidade": sala.capacidade,
                        "equipamentos": sala.equipamentos,
                        "metragem": str(sala.metragem) if sala.metragem else None,
                    })
                
                # Dados das copas
                copas = []
                for copa in Copa.objects.filter(briefing=briefing):
                    copas.append({
                        "equipamentos": copa.equipamentos,
                        "metragem": str(copa.metragem) if copa.metragem else None,
                    })
                
                # Dados dos depósitos
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
            
            # Instrução para o validador
            if task_instructions:
                # Usar as instruções personalizadas do agente
                user_prompt = task_instructions
            else:
                # Instrução padrão
                user_prompt = f"""
                Por favor, valide a seção '{secao}' do briefing com base nos dados fornecidos:
                {json.dumps(briefing_data, indent=2, ensure_ascii=False)}
                
                Analise se as informações estão completas, consistentes e realistas.
                Retorne um JSON com o seguinte formato:
                {{
                    "status": "[aprovado/atencao/reprovado]",
                    "mensagem": "Mensagem explicando o resultado da validação",
                    "feedback": "Feedback mais detalhado para apresentar ao cliente"
                }}
                """
            
            # Detectar tipo de cliente e enviar solicitação apropriada
            if hasattr(client, 'chat') and hasattr(client.chat, 'completions'):  # OpenAI
                logger.info(f"Enviando requisição de validação para OpenAI (modelo: {model})")
                response = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=temperature,
                    response_format={"type": "json_object"}
                )
                
                result = json.loads(response.choices[0].message.content)
                logger.info(f"Resposta de validação recebida da OpenAI: {result.get('status', 'desconhecido')}")
                
            elif hasattr(client, 'messages') and hasattr(client.messages, 'create'):  # Anthropic
                logger.info(f"Enviando requisição de validação para Anthropic (modelo: {model})")
                response = client.messages.create(
                    model=model,
                    system=system_prompt,
                    messages=[
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=temperature,
                    max_tokens=1000
                )
                
                # Extrair o JSON da resposta (Claude pode adicionar texto antes/depois do JSON)
                content = response.content[0].text
                
                # Tentar encontrar e extrair somente o JSON
                start_idx = content.find('{')
                end_idx = content.rfind('}') + 1
                if start_idx >= 0 and end_idx > start_idx:
                    json_str = content[start_idx:end_idx]
                    result = json.loads(json_str)
                else:
                    # Fallback
                    result = {
                        "status": "atencao",
                        "mensagem": "Não foi possível analisar completamente esta seção.",
                        "feedback": "O sistema encontrou um problema ao validar os dados. Por favor, revise manualmente."
                    }
                logger.info(f"Resposta de validação recebida da Anthropic: {result.get('status', 'desconhecido')}")
            else:
                # Provedor não suportado
                logger.warning("Provedor de IA não suportado para validação")
                result = {
                    "status": "atencao",
                    "mensagem": "Validação avançada indisponível",
                    "feedback": "O sistema está configurado com um provedor não suportado. Usando validação básica."
                }
                
            # Atualizar o objeto de validação com o resultado da IA
            validacao.status = result.get("status", "atencao")
            validacao.mensagem = result.get("mensagem", "Validação realizada")
            
            # Feedback detalhado para o cliente
            feedback = result.get("feedback", "")
            
        except Exception as e:
            # Em caso de erro, usar validação básica
            import traceback
            logger.error(f"Erro na validação com IA: {str(e)}")
            logger.error(traceback.format_exc())
            
            validacao.status = 'atencao'
            validacao.mensagem = 'Verificação automática indisponível. Por favor, revise manualmente.'
            feedback = "O sistema encontrou um problema ao analisar esta seção. Recomendamos revisar cuidadosamente as informações fornecidas."
    
    # Salvar o resultado da validação
    validacao.save()
    
    # Adicionar mensagem de feedback no chat
    if validacao.status == 'aprovado':
        mensagem = f"Analisei a seção '{secao.replace('_', ' ').title()}' e tudo parece estar completo e consistente!"
        if 'feedback' in locals() and feedback:
            mensagem += f" {feedback}"
            
        BriefingConversation.objects.create(
            briefing=briefing,
            mensagem=mensagem,
            origem='ia',
            etapa=briefing.etapa_atual
        )
    elif validacao.status == 'atencao':
        mensagem = f"Analisei a seção '{secao.replace('_', ' ').title()}' e tenho algumas observações: {validacao.mensagem}"
        if 'feedback' in locals() and feedback:
            mensagem += f" {feedback}"
        
        BriefingConversation.objects.create(
            briefing=briefing,
            mensagem=mensagem,
            origem='ia',
            etapa=briefing.etapa_atual
        )
    elif validacao.status == 'reprovado':
        mensagem = f"Encontrei problemas importantes na seção '{secao.replace('_', ' ').title()}': {validacao.mensagem}"
        if 'feedback' in locals() and feedback:
            mensagem += f" {feedback}"
        
        BriefingConversation.objects.create(
            briefing=briefing,
            mensagem=mensagem,
            origem='ia',
            etapa=briefing.etapa_atual
        )