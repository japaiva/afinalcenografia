from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
import json

# Importe os modelos do core
from core.models import Empresa, EmpresaUsuario, Projeto, Briefing, ArquivoProjeto

@login_required
def home(request):
    """Vista principal do portal do cliente"""
    context = {
        'use_content_box': True,
    }
    return render(request, 'cliente/home.html', context)

@login_required
def meus_projetos(request):
    """Lista os projetos do cliente logado"""
    projetos = Projeto.objects.filter(cliente=request.user).order_by('-data_criacao')
    
    context = {
        'projetos': projetos
    }
    return render(request, 'cliente/meus_projetos.html', context)

@login_required
def novo_projeto(request):
    """Criação de novo projeto"""
    if request.method == 'POST':
        titulo = request.POST.get('titulo')
        descricao = request.POST.get('descricao')
        empresa_id = request.POST.get('empresa_id')
        
        if not titulo:
            messages.error(request, 'O título do projeto é obrigatório.')
            return redirect('cliente:novo_projeto')
        
        # Verificar empresa
        if empresa_id:
            empresa = get_object_or_404(Empresa, id=empresa_id)
            # Verificar se o usuário tem vínculo com esta empresa
            if not EmpresaUsuario.objects.filter(usuario=request.user, empresa=empresa).exists():
                messages.error(request, 'Você não tem permissão para esta empresa.')
                return redirect('cliente:novo_projeto')
        else:
            # Obter a empresa principal do usuário
            empresa_usuario = EmpresaUsuario.objects.filter(usuario=request.user, principal=True).first()
            
            if not empresa_usuario:
                # Se não tem principal, pegar a primeira
                empresa_usuario = EmpresaUsuario.objects.filter(usuario=request.user).first()
                
            if not empresa_usuario:
                messages.error(request, 'Você não tem uma empresa associada.')
                return redirect('cliente:novo_projeto')
                
            empresa = empresa_usuario.empresa
        
        # Criar o projeto
        projeto = Projeto.objects.create(
            cliente=request.user,
            empresa=empresa,
            titulo=titulo,
            descricao=descricao,
            status='novo'
        )
        
        # Criar briefing vazio
        Briefing.objects.create(projeto=projeto)
        
        messages.success(request, 'Projeto criado com sucesso!')
        return redirect('cliente:briefing', projeto_id=projeto.id)
    
    # Obter empresas do usuário
    vinculos = EmpresaUsuario.objects.filter(usuario=request.user)
    empresas = [v.empresa for v in vinculos]
    
    context = {
        'empresas': empresas
    }
    return render(request, 'cliente/novo_projeto.html', context)

@login_required
def briefing(request, projeto_id):
    """Gerenciamento do briefing de um projeto"""
    projeto = get_object_or_404(Projeto, id=projeto_id, cliente=request.user)
    briefing, created = Briefing.objects.get_or_create(projeto=projeto)
    arquivos = ArquivoProjeto.objects.filter(projeto=projeto).order_by('-data_upload')
    
    # Verificação básica de campos
    validacao = {
        'feira': None if not briefing.feira else True,
        'posicao': None if not briefing.posicao else True,
        'orcamento': None if not briefing.orcamento else True
    }
    
    if request.method == 'POST':
        # Atualizar briefing
        briefing.feira = request.POST.get('feira')
        briefing.posicao = request.POST.get('posicao')
        briefing.orcamento = request.POST.get('orcamento') if request.POST.get('orcamento') else None
        briefing.observacoes = request.POST.get('observacoes')
        briefing.save()
        
        messages.success(request, 'Briefing atualizado com sucesso!')
        return redirect('cliente:briefing', projeto_id=projeto.id)
    
    context = {
        'projeto': projeto,
        'briefing': briefing,
        'arquivos': arquivos,
        'validacao': validacao,
    }
    return render(request, 'cliente/briefing.html', context)

@login_required
@require_POST
def validar_briefing(request, projeto_id):
    """Endpoint para validação do briefing pela IA"""
    projeto = get_object_or_404(Projeto, id=projeto_id, cliente=request.user)
    briefing = get_object_or_404(Briefing, projeto=projeto)
    
    # Atualizar dados do briefing
    briefing.feira = request.POST.get('feira')
    briefing.posicao = request.POST.get('posicao')
    briefing.orcamento = request.POST.get('orcamento') if request.POST.get('orcamento') else None
    briefing.observacoes = request.POST.get('observacoes')
    briefing.save()
    
    # Validação simulada (substituir por chamada à IA)
    validacao = {
        'feira': bool(briefing.feira),
        'posicao': bool(briefing.posicao),
        'orcamento': bool(briefing.orcamento) and float(briefing.orcamento) > 0 if briefing.orcamento else False
    }
    
    todos_validos = all(validacao.values())
    
    # Feedback de validação
    if todos_validos:
        feedback = "Seu briefing está completo e foi validado com sucesso! Os dados fornecidos são suficientes para iniciarmos o projeto. Se precisar de ajuda adicional, estou à disposição."
        briefing.validado_ia = True
    else:
        feedback = "Identifiquei alguns pontos que precisam ser completados:\n\n"
        if not validacao['feira']:
            feedback += "• A feira ou evento onde será montado o estande não foi informada. Esta informação é crucial para entendermos o contexto e público-alvo.\n\n"
        if not validacao['posicao']:
            feedback += "• A posição/localização no evento não foi especificada. Isso influencia diretamente no design e visibilidade do estande.\n\n"
        if not validacao['orcamento']:
            feedback += "• O orçamento disponível não foi definido ou tem valor inválido. Precisamos desta informação para dimensionar adequadamente o projeto.\n\n"
        
        feedback += "Por favor, complete as informações destacadas para prosseguirmos com a validação."
        briefing.validado_ia = False
    
    briefing.feedback_ia = feedback
    briefing.save()
    
    # Atualizar status do projeto se validado
    if briefing.validado_ia and projeto.status == 'novo':
        projeto.status = 'validado'
        projeto.save()
    
    return JsonResponse({
        'validado': briefing.validado_ia,
        'feedback': feedback,
        'validacao': validacao
    })

@login_required
@csrf_exempt
def chat_ia(request, projeto_id):
    """Endpoint para interação com a IA via chat"""
    if request.method != 'POST':
        return JsonResponse({'erro': 'Método não permitido'}, status=405)
    
    projeto = get_object_or_404(Projeto, id=projeto_id, cliente=request.user)
    
    try:
        data = json.loads(request.body)
        mensagem = data.get('mensagem', '')
        
        # Aqui você implementaria a chamada real à API de IA
        # Esta é apenas uma simulação básica de respostas
        
        resposta = "Desculpe, ainda não entendi completamente sua pergunta. Pode reformular?"
        
        # Respostas simuladas baseadas em palavras-chave
        palavras_chave = mensagem.lower()
        
        if 'orçamento' in palavras_chave or 'orcamento' in palavras_chave or 'custo' in palavras_chave:
            resposta = "O orçamento para projetos cenográficos varia de acordo com vários fatores como tamanho, complexidade e materiais. Para estandes em feiras, os valores geralmente começam em R$ 30.000,00 para estruturas pequenas e podem chegar a R$ 200.000,00 ou mais para projetos elaborados. Posso ajudar a adequar seu projeto às suas possibilidades de investimento."
        
        elif 'prazo' in palavras_chave or 'tempo' in palavras_chave:
            resposta = "O tempo de produção de um projeto cenográfico geralmente leva de 30 a 60 dias, dependendo da complexidade. Para feiras, recomendamos iniciar o processo com pelo menos 3 meses de antecedência, considerando o tempo de planejamento, aprovações, produção e montagem. Prazos mais curtos são possíveis, mas podem implicar em custos adicionais."
        
        elif 'material' in palavras_chave or 'materiais' in palavras_chave:
            resposta = "Trabalhamos com diversos materiais para cenografia, incluindo: MDF, madeira, acrílico, vidro, metal, tecidos, impressões em lona e vinil, iluminação LED, painéis interativos, entre outros. A escolha dos materiais depende do conceito visual, durabilidade necessária e orçamento disponível."
        
        elif 'feira' in palavras_chave or 'evento' in palavras_chave:
            resposta = "Temos experiência em diversas feiras e eventos como Expoagas, ExpoFood, Feicon, Hospitalar, entre outras. Cada feira tem características específicas que influenciam o projeto cenográfico. Qual feira específica você está planejando participar?"
        
        return JsonResponse({'resposta': resposta})
        
    except Exception as e:
        return JsonResponse({'erro': str(e)}, status=400)