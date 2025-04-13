# core/decorators.py

from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps
from django.urls import reverse

def cliente_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not hasattr(request.user, 'nivel') or request.user.nivel != 'cliente':
            messages.error(request, 'Acesso negado. Você não tem permissão de cliente.')
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return wrapper

# Adicione este decorator ao arquivo core/decorators.py ou onde for mais adequado



def require_admin_or_gestor(view_func):
    """
    Decorator que verifica se o usuário é administrador ou gestor.
    Usado para funções críticas como exclusão de dados.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # Verificar se o usuário está autenticado
        if not request.user.is_authenticated:
            messages.error(request, 'Você precisa estar autenticado para acessar esta página.')
            return redirect(reverse('login'))
        
        # Verificar se o usuário tem permissão adequada
        # Assumindo que 'nivel' é um atributo do modelo User
        if not hasattr(request.user, 'nivel') or request.user.nivel not in ['admin', 'gestor']:
            messages.error(request, 'Você não tem permissão para realizar esta operação.')
            return redirect(reverse('gestor:dashboard'))
        
        # Registrar a ação para auditoria
        # Este é opcional, mas recomendado para ações críticas
        import logging
        logger = logging.getLogger('core.security')
        logger.info(
            f"Acesso privilegiado: usuário={request.user.username}, "
            f"nivel={request.user.nivel}, view={view_func.__name__}, "
            f"path={request.path}"
        )
        
        # Continuar com a view original se todas as verificações passarem
        return view_func(request, *args, **kwargs)
    
    return _wrapped_view

