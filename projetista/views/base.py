# projetista/views/base.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy
from django.contrib import messages

from core.models import Usuario
from core.decorators import projetista_required

# PAGINAS PRINCIPAIS

@login_required
@projetista_required
def dashboard(request):
    """
    Dashboard do Projetista
    """
    print("Usuário acessando o dashboard:", request.user)
    
    # Filtrar apenas projetos atribuídos ao projetista
    from projetos.models import Projeto
    total_projetos = Projeto.objects.filter(projetista=request.user).count()
    
    context = {
        'total_projetos': total_projetos,  # Passe o total para o template
    }
    return render(request, 'projetista/dashboard.html', context)

class ProjetistaLoginView(LoginView):
    template_name = 'projetista/login.html'
    
    def form_valid(self, form):
        print("Login bem-sucedido para:", form.get_user())
        return super().form_valid(form)
    
    def get_success_url(self):
        print("Redirecionando para:", reverse_lazy('projetista:dashboard'))
        return reverse_lazy('projetista:dashboard')
 
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['app_name'] = 'Portal do Projetista'
        return context

def home(request):
    """
    Página inicial do Portal do Projetista
    """
    if request.user.is_authenticated:
        nivel = getattr(request.user, 'nivel', None)
        
        # Se o usuário é projetista, permitir o acesso
        if nivel == 'projetista':
            return render(request, 'projetista/home.html')
        
        # Se não for projetista, mostrar mensagem e redirecionar
        messages.error(request, 'Acesso negado. Você não tem permissão para acessar o Portal do Projetista.')
        
        # Redirecionar com base no nível do usuário
        portal_mapping = {
            'admin': 'gestor:home',
            'gestor': 'gestor:home',
            'cliente': 'cliente:home',
        }
        
        if nivel in portal_mapping:
            return redirect(portal_mapping[nivel])
        
        # Se não tiver um nível reconhecido, volta para a página principal
        return redirect('/')
    
    # Se não estiver autenticado, redirecionar para a página de login
    return redirect('projetista:login')  # Ou simplesmente para 'login'