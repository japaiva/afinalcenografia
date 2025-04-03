from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.contrib import messages
from django.contrib.auth.hashers import make_password
from .models import PerfilUsuario

@login_required
def perfil(request):
    usuario = request.user
    
    # Obter ou criar perfil ao carregar a página
    perfil, created = PerfilUsuario.objects.get_or_create(usuario=usuario)
    
    if request.method == 'POST':
        # Atualizar informações básicas
        usuario.first_name = request.POST.get('first_name', '')
        usuario.last_name = request.POST.get('last_name', '')
        usuario.email = request.POST.get('email', '')
        
        # Atualizar telefone no usuário e no perfil
        telefone = request.POST.get('telefone', '')
        usuario.telefone = telefone
        perfil.telefone = telefone
        
        # Processar foto
        if 'foto' in request.FILES:
            # Código de debug para verificar o upload
            arquivo = request.FILES['foto']
            print(f"Iniciando upload do arquivo: {arquivo.name}")
            
            # Salvar a foto no perfil (que usará o MinioStorage)
            perfil.foto = arquivo
            
            # Debug: verificar a URL gerada após salvar
            print(f"URL do arquivo após salvar: {perfil.foto.url if perfil.foto else 'Nenhuma URL'}")
        
        # Processar senha
        nova_senha = request.POST.get('nova_senha')
        if nova_senha:
            usuario.set_password(nova_senha)
        
        # Salvar alterações
        usuario.save()
        perfil.save()
        
        messages.success(request, 'Perfil atualizado com sucesso!')
        return redirect('perfil')
    
    return render(request, 'perfil.html', {'usuario': usuario})

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
    
def logout_view(request):
    """
    View para realizar o logout do usuário.
    """
    logout(request)
    messages.success(request, 'Você foi desconectado com sucesso.')
    return redirect('home')

def logout_view(request):
    """
    View para realizar o logout do usuário.
    """
    logout(request)
    messages.success(request, 'Você foi desconectado com sucesso.')
    return redirect('home')