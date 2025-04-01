# cliente/urls.py

from django.urls import path
from . import views

app_name = 'cliente'

urlpatterns = [
    # Nova URL para login
    path('login/', views.ClienteLoginView.as_view(), name='login'),

    # Páginas principais
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # CRUD Usuário (apenas da própria empresa)
    path('usuarios/', views.usuario_list, name='usuario_list'),
    path('usuarios/<int:pk>/', views.usuario_detail, name='usuario_detail'),
    
    # Detalhes da Empresa (apenas para consulta)
    path('empresa/', views.empresa_detail, name='empresa_detail'),
    
    # CRUD Projetos
    path('projetos/', views.projeto_list, name='projeto_list'),
    path('projetos/novo/', views.projeto_create, name='projeto_create'),
    path('projetos/briefing/', views.briefing, name='briefing'),  # Nova URL para o briefing com IA
    path('projetos/<int:pk>/', views.projeto_detail, name='projeto_detail'),
    path('projetos/<int:pk>/editar/', views.projeto_update, name='projeto_update'),
    path('projetos/<int:pk>/excluir/', views.projeto_delete, name='projeto_delete'),
    
    # Sistema de Mensagens
    path('mensagens/', views.mensagens, name='mensagens'),  # Central de mensagens
    path('mensagens/nova/', views.nova_mensagem, name='nova_mensagem'),  # Nova mensagem
    path('mensagens/projeto/<int:projeto_id>/', views.mensagens_projeto, name='mensagens_projeto'),  # Mensagens de um projeto específico
]