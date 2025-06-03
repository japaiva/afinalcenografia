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