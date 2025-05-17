# projetista/views/base.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy

from core.models import Usuario

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

# PÁGINAS PRINCIPAIS

def home(request):
    """
    Página inicial do Portal do Projetista
    """
    return render(request, 'projetista/home.html')

@login_required
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