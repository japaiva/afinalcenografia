# projetos/views/briefing_views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.forms import modelformset_factory
from django.db import transaction
from core.services.extracao_service import eh_pergunta_relacionada_a_feira
from core.models import Feira, Agente
from core.services.rag_service import RAGService
from projetos.models.projeto import Projeto  # Importação necessária

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
            # Verificar se é um projeto do tipo "outros" sem feira
            if briefing.projeto.tipo_projeto == 'outros' and not briefing.feira:
                # Validar os campos específicos para projetos sem feira
                if (briefing.nome_evento and briefing.local_evento and briefing.endereco_estande and 
                    briefing.data_horario_evento and briefing.organizador_evento and 
                    briefing.periodo_montagem_evento and briefing.periodo_desmontagem_evento):
                    validacao.status = 'aprovado'
                    validacao.mensagem = 'Informações do evento completas.'
                else:
                    validacao.status = 'atencao'
                    validacao.mensagem = 'Alguns campos importantes do evento estão incompletos. Por favor, preencha todos os campos obrigatórios.'
            else:
                # Validação para projetos com feira (padrão)
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