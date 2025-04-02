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
from openai import OpenAI  # Versão moderna da API
import os
from dotenv import load_dotenv

from django.db import models

# Carrega variáveis de ambiente
load_dotenv()

# Adicione logo após o load_dotenv()
api_key = os.getenv('OPENAI_API_KEY')
if api_key:
    print(f"API Key carregada (primeiros 10 caracteres): {api_key[:10]}...")
else:
    print("AVISO: API Key não encontrada!")

@login_required
@cliente_required
def iniciar_briefing(request, projeto_id):
    """
    Inicia um novo briefing para um projeto ou redireciona para o briefing existente.
    """
    projeto = get_object_or_404(Projeto, pk=projeto_id, empresa=request.user.empresa)
    
    # Verificar se já existe um briefing para este projeto
    try:
        briefing = Briefing.objects.get(projeto=projeto)
        # Se já existe, redirecionar para a etapa atual
        return redirect('cliente:briefing_etapa', projeto_id=projeto.id, etapa=briefing.etapa_atual)
    except Briefing.DoesNotExist:
        # Criar um novo briefing
        briefing = Briefing.objects.create(
            projeto=projeto,
            status='rascunho',
            etapa_atual=1
        )
        
        # Atualizar o status do projeto
        projeto.tem_briefing = True  # Atualiza o campo tem_briefing
        projeto.briefing_status = 'em_andamento'
        projeto.save()
        
        # Criar validações iniciais (todas como pendentes)
        BriefingValidacao.objects.create(briefing=briefing, secao='informacoes_basicas', status='pendente')
        BriefingValidacao.objects.create(briefing=briefing, secao='detalhes_tecnicos', status='pendente')
        BriefingValidacao.objects.create(briefing=briefing, secao='materiais_acabamentos', status='pendente')
        BriefingValidacao.objects.create(briefing=briefing, secao='requisitos_tecnicos', status='pendente')
        
        # Adicionar mensagem inicial da IA
        BriefingConversation.objects.create(
            briefing=briefing,
            mensagem="Olá! Sou o assistente do briefing. Estou aqui para ajudá-lo a preencher todas as informações do seu projeto. Vamos começar com as informações básicas!",
            origem='ia',
            etapa=1
        )
        
        return redirect('cliente:briefing_etapa', projeto_id=projeto.id, etapa=1)

@login_required
@cliente_required
def briefing_etapa(request, projeto_id, etapa):
    """
    Exibe e processa uma etapa específica do briefing.
    """
    projeto = get_object_or_404(Projeto, pk=projeto_id, empresa=request.user.empresa)
    
    try:
        briefing = Briefing.objects.get(projeto=projeto)
    except Briefing.DoesNotExist:
        return redirect('cliente:iniciar_briefing', projeto_id=projeto.id)
    
    # Converter etapa para inteiro
    etapa = int(etapa)
    
    # Verificar se a etapa é válida (entre 1 e 4)
    if etapa < 1 or etapa > 4:
        etapa = 1
    
    # Obter formulário para a etapa atual
    if etapa == 1:
        form_class = BriefingEtapa1Form
        secao = 'informacoes_basicas'
    elif etapa == 2:
        form_class = BriefingEtapa2Form
        secao = 'detalhes_tecnicos'
    elif etapa == 3:
        form_class = BriefingEtapa3Form
        secao = 'materiais_acabamentos'
    elif etapa == 4:
        form_class = BriefingEtapa4Form
        secao = 'requisitos_tecnicos'
    
    # Processar formulário enviado
    if request.method == 'POST':
        form = form_class(request.POST, instance=briefing)
        if form.is_valid():
            form.save()
            
            # Atualizar etapa atual do briefing
            briefing.etapa_atual = etapa
            briefing.save()
            
            # Validar automaticamente a seção atual com a IA
            validar_secao_briefing(briefing, secao)
            
            # Adicionar mensagem de sucesso
            messages.success(request, f'Etapa {etapa} salva com sucesso!')
            
            # Se houver próxima etapa, avançar
            if 'avancar' in request.POST and etapa < 4:
                return redirect('cliente:briefing_etapa', projeto_id=projeto.id, etapa=etapa+1)
            # Se for a última etapa e o usuário pediu para concluir
            elif 'concluir' in request.POST and etapa == 4:
                return redirect('cliente:concluir_briefing', projeto_id=projeto.id)
    else:
        form = form_class(instance=briefing)
    
    # Obter histórico de conversas
    conversas = BriefingConversation.objects.filter(briefing=briefing).order_by('timestamp')
    
    # Obter validações
    validacoes = BriefingValidacao.objects.filter(briefing=briefing)
    validacao_atual = validacoes.filter(secao=secao).first()
    
    # Formulário para enviar mensagem à IA
    mensagem_form = BriefingMensagemForm()
    
    # Formulário para upload de arquivos
    arquivo_form = BriefingArquivoReferenciaForm()
    
    # Obter arquivos de referência
    arquivos = BriefingArquivoReferencia.objects.filter(briefing=briefing)
    
    # Contexto para o template
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
def enviar_mensagem_ia(request, projeto_id):
    """
    Envia uma mensagem para a IA e retorna a resposta.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Método não permitido'}, status=405)
    
    projeto = get_object_or_404(Projeto, pk=projeto_id, empresa=request.user.empresa)
    briefing = get_object_or_404(Briefing, projeto=projeto)
    
    form = BriefingMensagemForm(request.POST)
    if not form.is_valid():
        return JsonResponse({'error': 'Mensagem inválida'}, status=400)
    
    mensagem = form.cleaned_data['mensagem']
    etapa_atual = briefing.etapa_atual
    
    # Salvar mensagem do cliente
    mensagem_cliente = BriefingConversation.objects.create(
        briefing=briefing,
        mensagem=mensagem,
        origem='cliente',
        etapa=etapa_atual
    )
    
    # Aqui você integraria com a IA para obter a resposta
    # Por enquanto, vamos simular uma resposta
    resposta_ia = "Obrigado por sua mensagem! Estou analisando as informações do seu projeto. Posso ajudar com mais alguma coisa?"
    
    # Salvar resposta da IA
    mensagem_ia = BriefingConversation.objects.create(
        briefing=briefing,
        mensagem=resposta_ia,
        origem='ia',
        etapa=etapa_atual
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
    """
    Faz upload de um arquivo de referência para o briefing.
    """
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
def validar_briefing(request, projeto_id):
    """
    Valida o briefing completo com a IA.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Método não permitido'}, status=405)
    
    projeto = get_object_or_404(Projeto, pk=projeto_id, empresa=request.user.empresa)
    briefing = get_object_or_404(Briefing, projeto=projeto)
    
    # Validar todas as seções
    validar_secao_briefing(briefing, 'informacoes_basicas')
    validar_secao_briefing(briefing, 'detalhes_tecnicos')
    validar_secao_briefing(briefing, 'materiais_acabamentos')
    validar_secao_briefing(briefing, 'requisitos_tecnicos')
    
    # Verificar se todas as seções estão aprovadas
    validacoes = BriefingValidacao.objects.filter(briefing=briefing)
    todas_aprovadas = all(v.status == 'aprovado' for v in validacoes)
    
    if todas_aprovadas:
        briefing.status = 'validado'
        briefing.validado_por_ia = True
        briefing.save()
        
        # Adicionar mensagem da IA
        BriefingConversation.objects.create(
            briefing=briefing,
            mensagem="Parabéns! Seu briefing foi aprovado com sucesso. Você pode enviá-lo para a equipe de cenografia avaliar.",
            origem='ia',
            etapa=briefing.etapa_atual
        )
    
    # Retornar resultados da validação
    return JsonResponse({
        'success': True,
        'todas_aprovadas': todas_aprovadas,
        'validacoes': {v.secao: v.status for v in validacoes}
    })


@login_required
@cliente_required
def concluir_briefing(request, projeto_id):
    """
    Conclui o briefing e envia para análise.
    """
    projeto = get_object_or_404(Projeto, pk=projeto_id, empresa=request.user.empresa)
    briefing = get_object_or_404(Briefing, projeto=projeto)
    
    # Verificar se todas as seções estão aprovadas
    validacoes = BriefingValidacao.objects.filter(briefing=briefing)
    todas_aprovadas = all(v.status == 'aprovado' for v in validacoes)
    
    if request.method == 'POST' and todas_aprovadas:
        # Atualizar status do briefing
        briefing.status = 'enviado'
        briefing.save()
        
        # Atualizar status do projeto
        projeto.briefing_status = 'enviado'
        projeto.save()
        
        messages.success(request, 'Briefing enviado com sucesso para análise!')
        return redirect('cliente:projeto_detail', pk=projeto.id)
    
    # Se não for POST ou nem todas as seções estiverem aprovadas, mostrar tela de conclusão
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
    """
    Salva o briefing como rascunho sem validar.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Método não permitido'}, status=405)
    
    projeto = get_object_or_404(Projeto, pk=projeto_id, empresa=request.user.empresa)
    briefing = get_object_or_404(Briefing, projeto=projeto)
    
    # Atualizar timestamp do briefing para indicar que foi salvo
    briefing.save(update_fields=['updated_at'])
    
    messages.success(request, 'Rascunho salvo com sucesso!')
    return JsonResponse({'success': True})


@login_required
@cliente_required
def excluir_arquivo_referencia(request, arquivo_id):
    """
    Exclui um arquivo de referência do briefing.
    """
    arquivo = get_object_or_404(BriefingArquivoReferencia, pk=arquivo_id)
    
    # Verificar se o usuário tem permissão para excluir o arquivo
    if arquivo.briefing.projeto.empresa != request.user.empresa:
        return JsonResponse({'error': 'Permissão negada'}, status=403)
    
    arquivo.delete()
    return JsonResponse({'success': True})


# Funções auxiliares

def obter_titulo_etapa(etapa):
    """
    Retorna o título para cada etapa do briefing.
    """
    titulos = {
        1: 'Informações Básicas',
        2: 'Detalhes Técnicos',
        3: 'Materiais e Acabamentos',
        4: 'Requisitos Técnicos'
    }
    return titulos.get(etapa, 'Etapa do Briefing')


def validar_secao_briefing(briefing, secao):
    """
    Valida uma seção específica do briefing com a IA.
    Por enquanto, implementamos uma lógica simples de validação.
    Futuramente, isso utilizará a IA para validação mais avançada.
    """
    # Obter a validação existente ou criar uma nova
    validacao, created = BriefingValidacao.objects.get_or_create(
        briefing=briefing,
        secao=secao,
        defaults={'status': 'pendente'}
    )
    
    # Verificar campos preenchidos de acordo com a seção
    if secao == 'informacoes_basicas':
        if briefing.categoria and briefing.descricao_detalhada and briefing.objetivos:
            validacao.status = 'aprovado'
            validacao.mensagem = 'Informações básicas completas.'
        else:
            validacao.status = 'atencao'
            validacao.mensagem = 'Alguns campos importantes estão incompletos.'
    
    elif secao == 'detalhes_tecnicos':
        if briefing.dimensoes and briefing.altura and briefing.paleta_cores:
            validacao.status = 'aprovado'
            validacao.mensagem = 'Detalhes técnicos completos.'
        else:
            validacao.status = 'atencao'
            validacao.mensagem = 'Informações sobre dimensões ou cores estão incompletas.'
    
    elif secao == 'materiais_acabamentos':
        if briefing.materiais_preferidos and briefing.acabamentos:
            validacao.status = 'aprovado'
            validacao.mensagem = 'Informações de materiais e acabamentos completas.'
        else:
            validacao.status = 'atencao'
            validacao.mensagem = 'Detalhe melhor seus materiais e acabamentos preferidos.'
    
    elif secao == 'requisitos_tecnicos':
        if briefing.iluminacao and briefing.eletrica and briefing.mobiliario:
            validacao.status = 'aprovado'
            validacao.mensagem = 'Requisitos técnicos completos.'
        else:
            validacao.status = 'atencao'
            validacao.mensagem = 'Especifique melhor os requisitos técnicos do projeto.'
    
    # Verificar regras específicas de negócio
    # (Aqui seria onde integraria com a IA para regras mais complexas)
    
    # Exemplo simples de regra de negócio:
    if secao == 'informacoes_basicas' and briefing.categoria == 'evento_corporativo':
        if not briefing.objetivos or len(briefing.objetivos) < 50:
            validacao.status = 'atencao'
            validacao.mensagem = 'Para eventos corporativos, detalhe melhor os objetivos do projeto.'
    
    # Salvar a validação
    validacao.save()
    
    # Adicionar uma mensagem da IA sobre a validação
    if validacao.status == 'aprovado':
        BriefingConversation.objects.create(
            briefing=briefing,
            mensagem=f"Analisei a seção '{secao.replace('_', ' ').title()}' e tudo parece estar completo!",
            origem='ia',
            etapa=briefing.etapa_atual
        )
    elif validacao.status == 'atencao':
        BriefingConversation.objects.create(
            briefing=briefing,
            mensagem=f"Analisei a seção '{secao.replace('_', ' ').title()}'. {validacao.mensagem} Você pode revisar e melhorar estas informações.",
            origem='ia',
            etapa=briefing.etapa_atual
        )
    
    return validacao

@require_POST
def enviar_mensagem_ia(request, projeto_id):
    """
    Processa mensagens enviadas para a IA e retorna uma resposta (usando OpenAI)
    """
    # Obter a mensagem do usuário
    mensagem = request.POST.get('mensagem', '')
    
    # Obter contexto do projeto
    projeto = Projeto.objects.get(id=projeto_id)
    
    # Obter histórico de conversa (opcional - para manter contexto)
    # Limitando a últimas 5 mensagens para não exceder o limite de tokens
    conversas_anteriores = Conversa.objects.filter(
        projeto_id=projeto_id
    ).order_by('-created_at')[:5]
    
    # Construir o contexto da conversa
    contexto = f"Você é um assistente especializado em projetos cenográficos da Afinal Cenografia. "
    contexto += f"Você está ajudando o cliente a preencher um briefing para o projeto '{projeto.nome}'. "
    contexto += f"O projeto tem orçamento de R$ {projeto.orcamento} e prazo de entrega {projeto.prazo_entrega}. "
    
    # Adiciona instruções sobre como ajudar
    contexto += "Sua função é auxiliar o cliente a fornecer informações claras e completas para o briefing. "
    contexto += "Responda perguntas sobre o processo, sugira ideias quando solicitado e ajude a esclarecer dúvidas. "
    contexto += "Seja amigável, profissional e focado em ajudar o cliente a ter sucesso em seu projeto cenográfico."
    
    # Configurar o cliente da API de IA
    try:
        # OpenAI
        API_KEY = os.getenv('OPENAI_API_KEY')
        if API_KEY:
            # Inicialize o cliente com a nova API
            client = OpenAI(api_key=API_KEY)
            
            # Montar a lista de mensagens com histórico
            messages = [{"role": "system", "content": contexto}]
            
            # Adicionar histórico de conversa (opcional)
            for conv in reversed(list(conversas_anteriores)):
                role = "user" if conv.origem == "cliente" else "assistant"
                messages.append({"role": role, "content": conv.mensagem})
            
            # Adicionar a mensagem atual
            messages.append({"role": "user", "content": mensagem})
            
            resposta = client.chat.completions.create(
                model="gpt-4o-mini",  # Versão mais leve do GPT-4 Omni
                messages=messages,
                max_tokens=1000,
                temperature=0.7
            )
        
            
            # Extrair o texto da resposta
            texto_resposta = resposta.choices[0].message.content
        else:
            # Fallback para caso a API key não esteja configurada
            texto_resposta = "Olá! Sou o assistente de briefing. Estou aqui para ajudar, mas parece que estou em modo de manutenção no momento. Por favor, continue preenchendo o formulário e, se tiver dúvidas específicas, você pode contatar a equipe da Afinal Cenografia diretamente."
    
    except Exception as e:
        # Em caso de erro, fornecer uma resposta genérica
        texto_resposta = f"Desculpe, não consegui processar sua pergunta no momento. Por favor, tente novamente mais tarde ou entre em contato com nossa equipe para assistência. (Erro: {str(e)})"
    
    # Salvar a conversa no banco de dados
    Conversa.objects.create(
        projeto_id=projeto_id,
        origem='cliente',
        mensagem=mensagem,
        timestamp=timezone.now()
    )
    
    Conversa.objects.create(
        projeto_id=projeto_id,
        origem='ai',
        mensagem=texto_resposta,
        timestamp=timezone.now()
    )
    
    # Retornar a resposta para o frontend
    return JsonResponse({
        'mensagem_ia': {
            'texto': texto_resposta,
            'timestamp': timezone.now().strftime('%H:%M')
        }
    })

class Conversa(models.Model):
    """
    Modelo para armazenar conversas entre cliente e IA no contexto de um projeto
    """
    projeto = models.ForeignKey('Projeto', on_delete=models.CASCADE, related_name='conversas')
    origem = models.CharField(max_length=10, choices=[
        ('cliente', 'Cliente'),
        ('ai', 'Assistente IA'),
    ])
    mensagem = models.TextField()
    timestamp = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Conversa'
        verbose_name_plural = 'Conversas'
    
    def __str__(self):
        return f"{self.origem} em {self.timestamp.strftime('%d/%m/%Y %H:%M')}"