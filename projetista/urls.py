# projetista/urls.py

from django.urls import path
from . import views

app_name = 'projetista'

urlpatterns = [
    # Nova URL para login
    path('login/', views.ProjetistaLoginView.as_view(), name='login'),
    
    # Páginas principais
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # Gestão de Projetos
    path('projetos/', views.projeto_list, name='projeto_list'),
    path('projetos/<int:pk>/', views.projeto_detail, name='projeto_detail'),
    path('projetos/<int:projeto_id>/briefing/', views.ver_briefing, name='ver_briefing'),
    
    # Conceito Visual
    path('projetos/<int:projeto_id>/gerar-conceito/', views.gerar_conceito, name='gerar_conceito'),
    path('conceito/<int:conceito_id>/', views.conceito_detalhes, name='conceito_detalhes'),
    path('conceito/<int:conceito_id>/upload-imagem/', views.upload_imagem, name='upload_imagem'),
    path('imagem/<int:imagem_id>/excluir/', views.excluir_imagem, name='excluir_imagem'),
    
    # Sistema de Mensagens
    path('mensagens/', views.mensagens, name='mensagens'),
    path('mensagens/nova/', views.nova_mensagem, name='nova_mensagem'),
    path('mensagens/projeto/<int:projeto_id>/', views.mensagens_projeto, name='mensagens_projeto'),
]