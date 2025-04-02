# core/decorators.py

from django.shortcuts import redirect
from django.contrib import messages

def cliente_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not hasattr(request.user, 'nivel') or request.user.nivel != 'cliente':
            messages.error(request, 'Acesso negado. Você não tem permissão de cliente.')
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return wrapper
