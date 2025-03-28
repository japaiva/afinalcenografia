from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required

@login_required
def redirect_by_user_level(request):
    """
    Redireciona o usuário para a página adequada com base em seu nível
    """
    try:
        nivel = request.user.perfil.nivel
    except:
        # Se o usuário não tem perfil, redireciona para o login
        return redirect('login')
    
    if nivel == 'admin':
        return redirect('admin_portal:index')
    elif nivel == 'gestor':
        return redirect('gestor:index')
    elif nivel == 'projetista':
        return redirect('projetista:index')
    else:  # cliente é o padrão
        return redirect('cliente:index')