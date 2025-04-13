# cliente/urls.py

from django.urls import path
from projetos import views as projeto_views
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

    # Briefing
    #path('projeto/<int:projeto_id>/briefing/iniciar/', views.iniciar_briefing, name='iniciar_briefing'),
    #path('projeto/<int:projeto_id>/briefing/etapa/<int:etapa>/', views.briefing_etapa, name='briefing_etapa'),
    #path('projeto/<int:projeto_id>/briefing/mensagem/', views.enviar_mensagem_ia, name='enviar_mensagem_ia'),
    #path('projeto/<int:projeto_id>/briefing/upload/', views.upload_arquivo_referencia, name='upload_arquivo_referencia'),
    #path('projeto/<int:projeto_id>/briefing/validar/', views.validar_briefing, name='validar_briefing'),
    #path('projeto/<int:projeto_id>/briefing/concluir/', views.concluir_briefing, name='concluir_briefing'),
    #path('projeto/<int:projeto_id>/briefing/salvar-rascunho/', views.salvar_rascunho_briefing, name='salvar_rascunho_briefing'),
    #path('arquivo/<int:arquivo_id>/excluir/', views.excluir_arquivo_referencia, name='excluir_arquivo_referencia'),
    
    # Adicionar às URLs do cliente/urls.py
    path('briefing/<int:briefing_id>/perguntar-feira/', views.briefing_perguntar_feira, name='briefing_perguntar_feira'),

    path('projeto/<int:projeto_id>/briefing/iniciar/', projeto_views.iniciar_briefing, name='iniciar_briefing'),
    path('projeto/<int:projeto_id>/briefing/etapa/<int:etapa>/', projeto_views.briefing_etapa, name='briefing_etapa'),
    path('projeto/<int:projeto_id>/briefing/mensagem/', projeto_views.enviar_mensagem_ia, name='enviar_mensagem_ia'),
    path('projeto/<int:projeto_id>/briefing/upload/', projeto_views.upload_arquivo_referencia, name='upload_arquivo_referencia'),
    path('projeto/<int:projeto_id>/briefing/validar/', projeto_views.validar_briefing, name='validar_briefing'),
    path('projeto/<int:projeto_id>/briefing/concluir/', projeto_views.concluir_briefing, name='concluir_briefing'),
    path('projeto/<int:projeto_id>/briefing/salvar-rascunho/', projeto_views.salvar_rascunho_briefing, name='salvar_rascunho_briefing'),
    path('arquivo/<int:arquivo_id>/excluir/', projeto_views.excluir_arquivo_referencia, name='excluir_arquivo_referencia'),


    # Sistema de Mensagens
    path('mensagens/', views.mensagens, name='mensagens'),  # Central de mensagens
    path('mensagens/nova/', views.nova_mensagem, name='nova_mensagem'),  # Nova mensagem
    path('mensagens/projeto/<int:projeto_id>/', views.mensagens_projeto, name='mensagens_projeto'),  # Mensagens de um projeto específico
]