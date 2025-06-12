# core/decorators.py

from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps
from django.urls import reverse

def admin_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        print(f"DEBUG @admin_required - Usuário: {request.user.username if request.user.is_authenticated else 'Anônimo'}")
        
        if not request.user.is_authenticated:
            messages.error(request, 'Você precisa estar autenticado.')
            return redirect('login')
            
        if not hasattr(request.user, 'nivel') or request.user.nivel != 'admin':
            print(f"DEBUG @admin_required - Nível: {getattr(request.user, 'nivel', 'Não definido')}")
            messages.error(request, 'Acesso negado. Você não tem permissão de administrador.')
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return wrapper

def gestor_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        print(f"DEBUG @gestor_required - Usuário: {request.user.username if request.user.is_authenticated else 'Anônimo'}")
        
        if not request.user.is_authenticated:
            messages.error(request, 'Você precisa estar autenticado.')
            return redirect('gestor:login')
        
        # CORRIGIDO: Verificar se é gestor OU admin
        if not hasattr(request.user, 'nivel') or request.user.nivel not in ['admin', 'gestor']:
            print(f"DEBUG @gestor_required - Nível: {getattr(request.user, 'nivel', 'Não definido')}")
            messages.error(request, 'Acesso negado. Você não tem permissão de gestor.')
            
            # NOVO: Tentar verificar também no PerfilUsuario
            try:
                from .models import PerfilUsuario
                perfil = request.user.perfil
                if perfil.nivel in ['admin', 'gestor']:
                    print(f"DEBUG @gestor_required - Acesso liberado via perfil: {perfil.nivel}")
                    return view_func(request, *args, **kwargs)
                else:
                    print(f"DEBUG @gestor_required - Perfil nivel: {perfil.nivel} (não autorizado)")
            except:
                print("DEBUG @gestor_required - Sem perfil ou erro ao acessar")
            
            return redirect('home')
            
        print(f"DEBUG @gestor_required - Acesso liberado via nivel: {request.user.nivel}")
        return view_func(request, *args, **kwargs)
    return wrapper

def projetista_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        print(f"DEBUG @projetista_required - Usuário: {request.user.username if request.user.is_authenticated else 'Anônimo'}")
        
        if not request.user.is_authenticated:
            messages.error(request, 'Você precisa estar autenticado.')
            return redirect('projetista:login')
            
        # Projetista, gestor ou admin podem acessar
        if not hasattr(request.user, 'nivel') or request.user.nivel not in ['admin', 'gestor', 'projetista']:
            print(f"DEBUG @projetista_required - Nível: {getattr(request.user, 'nivel', 'Não definido')}")
            
            # Verificar também no PerfilUsuario
            try:
                from .models import PerfilUsuario
                perfil = request.user.perfil
                if perfil.nivel in ['admin', 'gestor', 'projetista']:
                    print(f"DEBUG @projetista_required - Acesso liberado via perfil: {perfil.nivel}")
                    return view_func(request, *args, **kwargs)
            except:
                print("DEBUG @projetista_required - Sem perfil ou erro ao acessar")
            
            messages.error(request, 'Acesso negado. Você não tem permissão de projetista.')
            return redirect('home')
            
        return view_func(request, *args, **kwargs)
    return wrapper

def cliente_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        print(f"DEBUG @cliente_required - Usuário: {request.user.username if request.user.is_authenticated else 'Anônimo'}")
        
        if not request.user.is_authenticated:
            messages.error(request, 'Você precisa estar autenticado.')
            return redirect('cliente:login')
            
        if not hasattr(request.user, 'nivel') or request.user.nivel != 'cliente':
            print(f"DEBUG @cliente_required - Nível: {getattr(request.user, 'nivel', 'Não definido')}")
            
            # Verificar também no PerfilUsuario
            try:
                from .models import PerfilUsuario
                perfil = request.user.perfil
                if perfil.nivel == 'cliente':
                    print(f"DEBUG @cliente_required - Acesso liberado via perfil: {perfil.nivel}")
                    return view_func(request, *args, **kwargs)
            except:
                print("DEBUG @cliente_required - Sem perfil ou erro ao acessar")
            
            messages.error(request, 'Acesso negado. Você não tem permissão de cliente.')
            return redirect('home')
            
        return view_func(request, *args, **kwargs)
    return wrapper

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
        if not hasattr(request.user, 'nivel') or request.user.nivel not in ['admin', 'gestor']:
            # Verificar também no PerfilUsuario
            try:
                from .models import PerfilUsuario
                perfil = request.user.perfil
                if perfil.nivel not in ['admin', 'gestor']:
                    raise Exception("Sem permissão")
            except:
                messages.error(request, 'Você não tem permissão para realizar esta operação.')
                return redirect(reverse('gestor:dashboard'))
        
        # Registrar a ação para auditoria
        import logging
        logger = logging.getLogger('core.security')
        logger.info(
            f"Acesso privilegiado: usuário={request.user.username}, "
            f"nivel={getattr(request.user, 'nivel', 'N/A')}, view={view_func.__name__}, "
            f"path={request.path}"
        )
        
        # Continuar com a view original se todas as verificações passarem
        return view_func(request, *args, **kwargs)
    
    return _wrapped_view

