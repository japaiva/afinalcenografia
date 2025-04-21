# afinal_cenografia/middleware.py
from django.db.models import Q

class MensagensNotificacaoMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        
        # Injetar contagem de mensagens não lidas para usuários autenticados
        if request.user.is_authenticated:
            # Importar aqui dentro para evitar importações circulares
            from projetos.models import Mensagem
            
            # Contar mensagens não lidas para este usuário
            mensagens_nao_lidas = Mensagem.objects.filter(
                Q(destinatario=request.user) | 
                (Q(projeto__cliente=request.user) & ~Q(remetente=request.user)),
                lida=False
            ).count()
            
            # Adicionar ao objeto usuário
            request.user.mensagens_nao_lidas = mensagens_nao_lidas
        
        return response