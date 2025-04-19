# projetos/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
import json

from core.decorators import cliente_required
from projetos.models import Projeto
from projetos.models.briefing import Briefing, BriefingConversation, BriefingValidacao, BriefingArquivoReferencia
from projetos.forms.briefing import (
    BriefingForm, BriefingEtapa1Form, BriefingEtapa2Form, 
    BriefingEtapa3Form, BriefingEtapa4Form, 
    BriefingArquivoReferenciaForm, BriefingMensagemForm
)

from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils import timezone
from openai import OpenAI
import os
import logging
from dotenv import load_dotenv

from django.db import models

# Configurar logger
logger = logging.getLogger(__name__)

# Carrega variáveis de ambiente
load_dotenv()

# Adicione logo após o load_dotenv()
api_key = os.getenv('OPENAI_API_KEY')
if api_key:
    logger.info(f"API Key carregada (primeiros 10 caracteres): {api_key[:10]}...")
else:
    logger.warning("AVISO: API Key não encontrada!")

@login_required
@cliente_required
def iniciar_briefing(request, projeto_id):
    projeto = get_object_or_404(Projeto, pk=projeto_id, empresa=request.user.empresa)
    
    try:
        briefing = Briefing.objects.get(projeto=projeto)
        return redirect('cliente:briefing_etapa', projeto_id=projeto.id, etapa=briefing.etapa_atual)
    except Briefing.DoesNotExist:
        briefing = Briefing.objects.create(
            projeto=projeto,
            status='rascunho',
            etapa_atual=1
        )
        
        projeto.tem_briefing = True
        projeto.briefing_status = 'em_andamento'
        projeto.save()
        
        BriefingValidacao.objects.create(briefing=briefing, secao='evento', status='pendente')
        BriefingValidacao.objects.create(briefing=briefing, secao='estande', status='pendente')
        BriefingValidacao.objects.create(briefing=briefing, secao='areas_estande', status='pendente')
        BriefingValidacao.objects.create(briefing=briefing, secao='dados_complementares', status='pendente')
        
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
    projeto = get_object_or_404(Projeto, pk=projeto_id, empresa=request.user.empresa)
    
    try:
        briefing = Briefing.objects.get(projeto=projeto)
    except Briefing.DoesNotExist:
        return redirect('cliente:iniciar_briefing', projeto_id=projeto.id)
    
    etapa = int(etapa)
    
    if etapa < 1 or etapa > 4:
        etapa = 1
        
    if etapa == 1:
        form_class = BriefingEtapa1Form
        secao = 'evento'
    elif etapa == 2:
        form_class = BriefingEtapa2Form
        secao = 'estande'
    elif etapa == 3:
        form_class = BriefingEtapa3Form
        secao = 'areas_estande'
    else:  # etapa == 4
        form_class = BriefingEtapa4Form
        secao = 'dados_complementares'
    
    if request.method == 'POST':
        form = form_class(request.POST, instance=briefing)
        if form.is_valid():
            form.save()
            
            briefing.etapa_atual = etapa
            briefing.save()
            
            validar_secao_briefing(briefing, secao)
            
            messages.success(request, f'Etapa {etapa} salva com sucesso!')
            
            if 'avancar' in request.POST and etapa < 4:
                return redirect('cliente:briefing_etapa', projeto_id=projeto.id, etapa=etapa+1)
            elif 'concluir' in request.POST and etapa == 4:
                return redirect('cliente:concluir_briefing', projeto_id=projeto.id)
    else:
        form = form_class(instance=briefing)
    
    conversas = BriefingConversation.objects.filter(briefing=briefing).order_by('timestamp')
    
    validacoes = BriefingValidacao.objects.filter(briefing=briefing)
    validacao_atual = validacoes.filter(secao=secao).first()
    
    mensagem_form = BriefingMensagemForm()
    
    arquivo_form = BriefingArquivoReferenciaForm()
    
    arquivos = BriefingArquivoReferencia.objects.filter(briefing=briefing)
    
    context = {
        'projeto': projeto,
        'briefing': briefing,
        'etapa': etapa,
        'form': form,
        'conversas': conversas,
        'validacoes': validacoes,
        'validacao_atual': validacao_atual,
        'mensagem_form': mensagem_form,
        'arquivo_form': arquivo_form,
        'arquivos': arquivos,
        'titulo_etapa': obter_titulo_etapa(etapa),
        'pode_avancar': etapa < 4,
        'pode_voltar': etapa > 1,
        'pode_concluir': etapa == 4,
    }
    
    return render(request, 'cliente/briefing_etapa.html', context)

@login_required
@cliente_required
@require_POST
def enviar_mensagem_ia(request, projeto_id):
    mensagem = request.POST.get('mensagem', '')
    
    projeto = get_object_or_404(Projeto, pk=projeto_id, empresa=request.user.empresa)
    briefing = get_object_or_404(Briefing, projeto=projeto)
    
    # Obtém conversas anteriores para contexto
    conversas_anteriores = BriefingConversation.objects.filter(
        briefing=briefing
    ).order_by('-timestamp')[:5]
    
    # Busca um agente adequado no banco de dados
    try:
        from core.utils.llm_utils import get_llm_client
        
        # Obtém o cliente LLM, modelo e configurações do agente "Assistente de Briefing"
        client, model, temperature, system_prompt, task_instructions = get_llm_client("Assistente de Briefing")
        
        if client is None:
            raise ValueError("Não foi possível inicializar o cliente LLM para o agente 'Assistente de Briefing'")
    except Exception as e:
        # Fallback para cliente OpenAI padrão se não conseguir obter o cliente do agente
        logger.warning(f"Erro ao obter cliente LLM: {str(e)}. Usando cliente padrão.")
        
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            logger.error("API Key do OpenAI não encontrada!")
            raise ValueError("API Key do OpenAI não encontrada")
            
        client = OpenAI(api_key=api_key)
        model = "gpt-4o-mini"
        temperature = 0.7
        system_prompt = "Você é um assistente especializado em projetos cenográficos da Afinal Cenografia."
        task_instructions = None
    
    # Construir o contexto para o assistente
    contexto = system_prompt + "\n\n"
    contexto += f"Você está ajudando o cliente a preencher um briefing para o projeto '{projeto.nome}'. "
    
    # Usar atributos que realmente existem no modelo Projeto
    # Verificar atributos disponíveis e adicionar se existirem
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
def concluir_briefing(request, projeto_id):
    projeto = get_object_or_404(Projeto, pk=projeto_id, empresa=request.user.empresa)
    briefing = get_object_or_404(Briefing, projeto=projeto)
    
    validacoes = BriefingValidacao.objects.filter(briefing=briefing)
    todas_aprovadas = all(v.status == 'aprovado' for v in validacoes)
    
    if request.method == 'POST' and todas_aprovadas:
        briefing.status = 'enviado'
        briefing.save()
        
        projeto.briefing_status = 'enviado'
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
def salvar_rascunho_briefing(request, projeto_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Método não permitido'}, status=405)
    
    projeto = get_object_or_404(Projeto, pk=projeto_id, empresa=request.user.empresa)
    briefing = get_object_or_404(Briefing, projeto=projeto)
    
    briefing.save(update_fields=['updated_at'])
    
    messages.success(request, 'Rascunho salvo com sucesso!')
    return JsonResponse({'success': True})

@login_required
@cliente_required
def excluir_arquivo_referencia(request, arquivo_id):
    arquivo = get_object_or_404(BriefingArquivoReferencia, pk=arquivo_id)
    
    if arquivo.briefing.projeto.empresa != request.user.empresa:
        return JsonResponse({'error': 'Permissão negada'}, status=403)
    
    arquivo.delete()
    return JsonResponse({'success': True})

def obter_titulo_etapa(etapa):
    titulos = {
        1: 'EVENTO - Datas e Localização',
        2: 'ESTANDE - Características Físicas',
        3: 'ÁREAS DO ESTANDE - Divisões Funcionais',
        4: 'DADOS COMPLEMENTARES - Referências Visuais'
    }
    return titulos.get(etapa, 'Etapa do Briefing')

def validar_secao_briefing(briefing, secao):
    """
    Função que utiliza o agente 'Validador de Briefing'
    para validar as seções do briefing de maneira inteligente
    """
    import json
    
    # Obtém o objeto de validação existente ou cria um novo
    validacao, created = BriefingValidacao.objects.get_or_create(
        briefing=briefing,
        secao=secao,
        defaults={'status': 'pendente'}
    )
    
    # Tenta carregar o cliente LLM para o agente "Validador de Briefing"
    try:
        from core.utils.llm_utils import get_llm_client
        
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
            if briefing.local_evento and briefing.data_feira_inicio and briefing.data_feira_fim:
                validacao.status = 'aprovado'
                validacao.mensagem = 'Informações do evento completas.'
            else:
                validacao.status = 'atencao'
                validacao.mensagem = 'Alguns campos importantes do evento estão incompletos.'
        
        elif secao == 'estande':
            if briefing.area_estande and briefing.estilo_estande:
                validacao.status = 'aprovado'
                validacao.mensagem = 'Características do estande completas.'
            else:
                validacao.status = 'atencao'
                validacao.mensagem = 'Informações sobre área ou estilo do estande estão incompletas.'
        
        elif secao == 'areas_estande':
            if briefing.tem_sala_reuniao is not None and briefing.tem_copa is not None and briefing.tem_deposito is not None:
                validacao.status = 'aprovado'
                validacao.mensagem = 'Informações das áreas do estande completas.'
            else:
                validacao.status = 'atencao'
                validacao.mensagem = 'Algumas informações sobre as áreas do estande estão faltando.'
        
        elif secao == 'dados_complementares':
            if briefing.referencias_dados:
                validacao.status = 'aprovado'
                validacao.mensagem = 'Dados complementares completos.'
            else:
                validacao.status = 'atencao'
                validacao.mensagem = 'Adicione mais informações complementares ou referências.'
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
                briefing_data.update({
                    "nome_feira": briefing.nome_feira,
                    "local_evento": briefing.local_evento,
                    "data_inicio": str(briefing.data_feira_inicio) if briefing.data_feira_inicio else None,
                    "data_fim": str(briefing.data_feira_fim) if briefing.data_feira_fim else None,
                    "montagem_inicio": str(briefing.data_montagem_inicio) if briefing.data_montagem_inicio else None,
                    "montagem_fim": str(briefing.data_montagem_fim) if briefing.data_montagem_fim else None,
                    "desmontagem_inicio": str(briefing.data_desmontagem_inicio) if briefing.data_desmontagem_inicio else None,
                    "desmontagem_fim": str(briefing.data_desmontagem_fim) if briefing.data_desmontagem_fim else None,
                })
            elif secao == 'estande':
                briefing_data.update({
                    "area_estande": briefing.area_estande,
                    "tipo_montagem": briefing.tipo_montagem,
                    "estilo_estande": briefing.estilo_estande,
                    "formato_estande": briefing.formato_estande,
                    "altura_maxima": briefing.altura_maxima,
                    "numero_andares": briefing.numero_andares,
                })
            elif secao == 'areas_estande':
                briefing_data.update({
                    "tem_recepcao": briefing.tem_recepcao,
                    "tem_sala_reuniao": briefing.tem_sala_reuniao,
                    "qtd_salas_reuniao": briefing.qtd_salas_reuniao,
                    "tem_copa": briefing.tem_copa,
                    "tem_deposito": briefing.tem_deposito,
                    "tamanho_deposito": briefing.tamanho_deposito,
                })
            elif secao == 'dados_complementares':
                briefing_data.update({
                    "referencias_dados": briefing.referencias_dados,
                    "observacoes": briefing.observacoes,
                })
            
            # Instrução para o validador
            if task_instructions:
                # Usar as instruções personalizadas do agente
                user_prompt = task_instructions
            else:
                # Instrução padrão
                user_prompt = f"""
                Por favor, valide a seção '{secao}' do briefing com base nos seguintes dados:
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
        mensagem = f"Analisei a seção '{secao.replace('_', ' ').title()}' e tudo parece estar completo!"
        if 'feedback' in locals() and feedback:
            mensagem += f" {feedback}"
            
        BriefingConversation.objects.create(
            briefing=briefing,
            mensagem=mensagem,
            origem='ia',
            etapa=briefing.etapa_atual
        )
    elif validacao.status == 'atencao':
        mensagem = f"Analisei a seção '{secao.replace('_', ' ').title()}'. {validacao.mensagem}"
        if 'feedback' in locals() and feedback:
            mensagem += f" {feedback}"
        
        BriefingConversation.objects.create(
            briefing=briefing,
            mensagem=mensagem,
            origem='ia',
            etapa=briefing.etapa_atual
        )
    elif validacao.status == 'reprovado':
        mensagem = f"Encontrei problemas na seção '{secao.replace('_', ' ').title()}'. {validacao.mensagem}"
        if 'feedback' in locals() and feedback:
            mensagem += f" {feedback}"
        
        BriefingConversation.objects.create(
            briefing=briefing,
            mensagem=mensagem,
            origem='ia',
            etapa=briefing.etapa_atual
        )

