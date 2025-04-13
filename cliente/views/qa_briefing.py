import json
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST, require_GET

from projetos.models import Projeto
from projetos.models.briefing import Briefing, BriefingConversation
from core.models import Feira
from core.services.qa_integration import integrar_feira_com_briefing, RAGService

@login_required
@require_POST
def briefing_vincular_feira(request, briefing_id, feira_id):
    """
    Vincula uma feira a um briefing para usar seu manual como referência.
    """
    # Verificar permissões
    briefing = get_object_or_404(Briefing, pk=briefing_id)
    projeto = briefing.projeto
    
    # Garantir que o usuário tenha acesso ao projeto
    if not (
        request.user.nivel in ['admin', 'gestor'] or 
        request.user == projeto.projetista or 
        request.user == projeto.cliente
    ):
        return JsonResponse({
            'success': False,
            'message': 'Você não tem permissão para realizar esta operação.'
        }, status=403)
    
    # Integrar a feira ao briefing
    result = integrar_feira_com_briefing(briefing_id, feira_id)
    
    return JsonResponse({
        'success': result.get('status') == 'success',
        'message': result.get('message', '')
    })

@login_required
@require_POST
def briefing_responder_pergunta(request):
    """
    Responde a uma pergunta do usuário usando o RAG baseado no manual da feira.
    """
    try:
        data = json.loads(request.body)
        briefing_id = data.get('briefing_id')
        pergunta = data.get('pergunta')
        
        if not briefing_id or not pergunta:
            return JsonResponse({
                'success': False,
                'message': 'Briefing ID e pergunta são obrigatórios.'
            }, status=400)
        
        # Obter o briefing
        briefing = get_object_or_404(Briefing, pk=briefing_id)
        
        # Verificar se há uma feira vinculada
        if not hasattr(briefing, 'feira') or not briefing.feira:
            return JsonResponse({
                'success': False,
                'message': 'Este briefing não possui uma feira vinculada.'
            })
        
        # Inicializar o serviço RAG
        rag_service = RAGService()
        
        # Gerar resposta
        rag_result = rag_service.gerar_resposta_rag(pergunta, briefing.feira.id)
        
        # Registrar a pergunta e resposta no histórico de conversas
        BriefingConversation.objects.create(
            briefing=briefing,
            mensagem=f"Pergunta: {pergunta}",
            origem='cliente' if request.user == briefing.projeto.cliente else 'projetista',
            etapa=briefing.etapa_atual
        )
        
        BriefingConversation.objects.create(
            briefing=briefing,
            mensagem=f"Resposta (Manual da Feira): {rag_result['resposta']}",
            origem='sistema',
            etapa=briefing.etapa_atual
        )
        
        return JsonResponse({
            'success': True,
            'resposta': rag_result['resposta'],
            'contextos': rag_result['contextos'],
            'status': rag_result['status']
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)

# Para o portal do cliente
@login_required
def briefing_perguntar_feira(request, briefing_id):
    """
    Renderiza a interface para fazer perguntas sobre a feira.
    """
    from django.shortcuts import render
    
    # Obter o briefing
    briefing = get_object_or_404(Briefing, pk=briefing_id)
    projeto = briefing.projeto
    
    # Verificar permissões
    if request.user != projeto.cliente and request.user.nivel not in ['admin', 'gestor']:
        return JsonResponse({
            'success': False, 
            'message': 'Você não tem permissão para acessar este briefing.'
        }, status=403)
    
    # Verificar se há uma feira vinculada
    feira = None
    if hasattr(briefing, 'feira') and briefing.feira:
        feira = briefing.feira
    
    # Obter histórico de perguntas e respostas
    conversas = BriefingConversation.objects.filter(
        briefing=briefing,
        origem__in=['cliente', 'sistema']
    ).order_by('timestamp')
    
    # Filtrar apenas as perguntas e respostas relacionadas à feira
    feira_qa = []
    for i, conversa in enumerate(conversas):
        if 'Pergunta: ' in conversa.mensagem and i < len(conversas) - 1:
            if 'Resposta (Manual da Feira): ' in conversas[i+1].mensagem:
                pergunta = conversa.mensagem.replace('Pergunta: ', '')
                resposta = conversas[i+1].mensagem.replace('Resposta (Manual da Feira): ', '')
                feira_qa.append({
                    'pergunta': pergunta,
                    'resposta': resposta,
                    'timestamp': conversa.timestamp
                })
    
    context = {
        'briefing': briefing,
        'projeto': projeto,
        'feira': feira,
        'feira_qa': feira_qa,
        'feiras_disponiveis': Feira.objects.filter(ativa=True).order_by('-data_inicio')
    }
    
    return render(request, 'cliente/briefing_perguntar_feira.html', context)