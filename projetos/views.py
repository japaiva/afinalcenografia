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
def enviar_mensagem_ia(request, projeto_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Método não permitido'}, status=405)
    
    projeto = get_object_or_404(Projeto, pk=projeto_id, empresa=request.user.empresa)
    briefing = get_object_or_404(Briefing, projeto=projeto)
    
    form = BriefingMensagemForm(request.POST)
    if not form.is_valid():
        return JsonResponse({'error': 'Mensagem inválida'}, status=400)
    
    mensagem = form.cleaned_data['mensagem']
    etapa_atual = briefing.etapa_atual
    
    mensagem_cliente = BriefingConversation.objects.create(
        briefing=briefing,
        mensagem=mensagem,
        origem='cliente',
        etapa=etapa_atual
    )
    
    resposta_ia = "Obrigado por sua mensagem! Estou analisando as informações do seu projeto. Posso ajudar com mais alguma coisa?"
    
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
    if request.method != 'POST':
        return JsonResponse({'error': 'Método não permitido'}, status=405)
    
    projeto = get_object_or_404(Projeto, pk=projeto_id, empresa=request.user.empresa)
    briefing = get_object_or_404(Briefing, projeto=projeto)
    
    validar_secao_briefing(briefing, 'evento')
    validar_secao_briefing(briefing, 'estande')
    validar_secao_briefing(briefing, 'areas_estande')
    validar_secao_briefing(briefing, 'dados_complementares')
    
    validacoes = BriefingValidacao.objects.filter(briefing=briefing)
    todas_aprovadas = all(v.status == 'aprovado' for v in validacoes)
    
    if todas_aprovadas:
        briefing.status = 'validado'
        briefing.validado_por_ia = True
        briefing.save()
        
        BriefingConversation.objects.create(
            briefing=briefing,
            mensagem="Parabéns! Seu briefing foi aprovado com sucesso. Você pode enviá-lo para a equipe de cenografia avaliar.",
            origem='ia',
            etapa=briefing.etapa_atual
        )
    
    return JsonResponse({
        'success': True,
        'todas_aprovadas': todas_aprovadas,
        'validacoes': {v.secao: v.status for v in validacoes}
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
    validacao, created = BriefingValidacao.objects.get_or_create(
        briefing=briefing,
        secao=secao,
        defaults={'status': 'pendente'}
    )
    
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
    
    validacao.save()
    
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
    mensagem = request.POST.get('mensagem', '')
    
    projeto = Projeto.objects.get(id=projeto_id)
    
    conversas_anteriores = Conversa.objects.filter(
        projeto_id=projeto_id
    ).order_by('-created_at')[:5]
    
    contexto = f"Você é um assistente especializado em projetos cenográficos da Afinal Cenografia. "
    contexto += f"Você está ajudando o cliente a preencher um briefing para o projeto '{projeto.nome}'. "
    contexto += f"O projeto tem orçamento de R$ {projeto.orcamento} e prazo de entrega {projeto.prazo_entrega}. "
    
    contexto += "Sua função é auxiliar o cliente a fornecer informações claras e completas para o briefing. "
    contexto += "Responda perguntas sobre o processo, sugira ideias quando solicitado e ajude a esclarecer dúvidas. "
    contexto += "Seja amigável, profissional e focado em ajudar o cliente a ter sucesso em seu projeto cenográfico."
    
    try:
        API_KEY = os.getenv('OPENAI_API_KEY')
        if API_KEY:
            client = OpenAI(api_key=API_KEY)
            
            messages = [{"role": "system", "content": contexto}]
            
            for conv in reversed(list(conversas_anteriores)):
                role = "user" if conv.origem == "cliente" else "assistant"
                messages.append({"role": role, "content": conv.mensagem})
            
            messages.append({"role": "user", "content": mensagem})
            
            resposta = client.chat.completions.create(
                model="gpt-4o-mini",  
                messages=messages,
                max_tokens=1000,
                temperature=0.7
            )
        
            texto_resposta = resposta.choices[0].message.content
        else:
            texto_resposta = "Olá! Sou o assistente de briefing. Estou aqui para ajudar, mas parece que estou em modo de manutenção no momento. Por favor, continue preenchendo o formulário e, se tiver dúvidas específicas, você pode contatar a equipe da Afinal Cenografia diretamente."
    
    except Exception as e:
        texto_resposta = f"Desculpe, não consegui processar sua pergunta no momento. Por favor, tente novamente mais tarde ou entre em contato com nossa equipe para assistência. (Erro: {str(e)})"
    
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
    
    return JsonResponse({
        'mensagem_ia': {
            'texto': texto_resposta,
            'timestamp': timezone.now().strftime('%H:%M')
        }
    })

class Conversa(models.Model):
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