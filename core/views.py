from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.contrib import messages

def home_view(request):
    """
    View para a página inicial do site.
    Redireciona para o dashboard apropriado se o usuário estiver autenticado,
    caso contrário, mostra a página inicial genérica.
    """
    if request.user.is_authenticated:
        # Redireciona para o portal adequado com base no nível do usuário
        if request.user.nivel in ['admin', 'gestor']:
            return redirect('gestor:dashboard')
        elif request.user.nivel == 'cliente':
            return redirect('cliente:dashboard')
        elif request.user.nivel == 'projetista':
            return redirect('projetista:dashboard')
        else:
            # Nível de usuário não reconhecido, redireciona para a página inicial padrão
            return render(request, 'home.html')
    else:
        # Usuário não autenticado, mostra a página inicial padrão
        return render(request, 'home.html')

@login_required
def perfil(request):
    """
    View para exibir e editar o perfil do usuário.
    """
    if request.method == 'POST':
        # Campos limitados para o usuário editar seu próprio perfil
        request.user.first_name = request.POST.get('first_name')
        request.user.last_name = request.POST.get('last_name')
        request.user.email = request.POST.get('email')
        request.user.telefone = request.POST.get('telefone')
        
        # Atualização de senha
        nova_senha = request.POST.get('nova_senha')
        if nova_senha:
            request.user.set_password(nova_senha)
        
        # Atualização da foto de perfil
        if 'foto_perfil' in request.FILES:
            request.user.foto_perfil = request.FILES['foto_perfil']
            
        request.user.save()
        
        from django.contrib import messages
        messages.success(request, 'Perfil atualizado com sucesso.')
        
        # Se houve alteração de senha, o usuário precisa fazer login novamente
        if nova_senha:
            messages.info(request, 'Sua senha foi alterada. Por favor, faça login novamente.')
            from django.contrib.auth import logout
            logout(request)
            return redirect('login')
            
        return redirect('perfil')
    
    return render(request, 'perfil.html', {'usuario': request.user})

def logout_view(request):
    """
    View para realizar o logout do usuário.
    """
    logout(request)
    messages.success(request, 'Você foi desconectado com sucesso.')
    return redirect('home')