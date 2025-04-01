# gestor/urls.py

from django.urls import path
from . import views

app_name = 'gestor'

urlpatterns = [
    # Nova URL para login
    path('login/', views.GestorLoginView.as_view(), name='login'),

    # Páginas principais
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # CRUD Empresa
    path('empresas/', views.empresa_list, name='empresa_list'),
    path('empresas/novo/', views.empresa_create, name='empresa_create'),
    path('empresas/<int:pk>/editar/', views.empresa_update, name='empresa_update'),
    path('empresas/<int:pk>/alternar-status/', views.empresa_toggle_status, name='empresa_toggle_status'),
    
    # CRUD Usuário
    path('usuarios/', views.usuario_list, name='usuario_list'),
    path('usuarios/novo/', views.usuario_create, name='usuario_create'),
    path('usuarios/<int:pk>/editar/', views.usuario_update, name='usuario_update'),
    path('usuarios/<int:pk>/alternar-status/', views.usuario_toggle_status, name='usuario_toggle_status'),
    
    # CRUD Parâmetros
    path('parametros/', views.parametro_list, name='parametro_list'),
    path('parametros/novo/', views.parametro_create, name='parametro_create'),
    path('parametros/<int:pk>/editar/', views.parametro_update, name='parametro_update'),
    path('parametros/<int:pk>/excluir/', views.parametro_delete, name='parametro_delete'),
    
    # Gestão de Projetos
    path('projetos/', views.projeto_list, name='projeto_list'),
    path('projetos/<int:pk>/', views.projeto_detail, name='projeto_detail'),
    path('projetos/<int:pk>/atribuir/<int:usuario_id>/', views.projeto_atribuir, name='projeto_atribuir'),
    path('projetos/<int:pk>/alterar-status/', views.projeto_alterar_status, name='projeto_alterar_status'),
    
    # Sistema de Mensagens
    path('mensagens/', views.mensagens, name='mensagens'),  # Central de mensagens
    path('mensagens/nova/', views.nova_mensagem, name='nova_mensagem'),  # Nova mensagem
    path('mensagens/projeto/<int:projeto_id>/', views.mensagens_projeto, name='mensagens_projeto'),  # Mensagens de um projeto específico
]