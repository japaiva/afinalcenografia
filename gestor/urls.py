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
    path('projetos/<int:projeto_id>/briefing/', views.ver_briefing, name='ver_briefing'),
    path('projetos/<int:projeto_id>/briefing/aprovar/', views.aprovar_briefing, name='aprovar_briefing'),
    path('projetos/<int:projeto_id>/briefing/reprovar/', views.reprovar_briefing, name='reprovar_briefing'),    
    path('projetos/<int:projeto_id>/upload/', views.upload_arquivo, name='upload_arquivo'),


    # Para excluir arquivos
    path('arquivos/<int:arquivo_id>/excluir/', views.excluir_arquivo, name='excluir_arquivo'),
    
    # Sistema de Mensagens
    path('mensagens/', views.mensagens, name='mensagens'),  # Central de mensagens
    path('mensagens/nova/', views.nova_mensagem, name='nova_mensagem'),  # Nova mensagem
    path('mensagens/projeto/<int:projeto_id>/', views.mensagens_projeto, name='mensagens_projeto'),  # Mensagens de um projeto específico

    # Para os parâmetros do banco vetorial (antigos parâmetros de indexação)
    path('parametros-banco-vetorial/', views.parametro_indexacao_list, name='parametro_indexacao_list'),
    path('parametros-banco-vetorial/novo/', views.parametro_indexacao_create, name='parametro_indexacao_create'),
    path('parametros-banco-vetorial/<int:pk>/editar/', views.parametro_indexacao_update, name='parametro_indexacao_update'),
    path('parametros-banco-vetorial/<int:pk>/excluir/', views.parametro_indexacao_delete, name='parametro_indexacao_delete'),

    # CRUD de Agentes de IA
    path('agentes/', views.agente_list, name='agente_list'),
    path('agentes/novo/', views.agente_create, name='agente_create'),
    path('agentes/<int:pk>/editar/', views.agente_update, name='agente_update'),
    path('agentes/<int:pk>/excluir/', views.agente_delete, name='agente_delete'),

    # FEIRAS
    path('feiras/<int:feira_id>/qa/', views.feira_qa_list, name='feira_qa_list'),
    path('feiras/<int:feira_id>/qa/regenerate/', views.feira_qa_regenerate, name='feira_qa_regenerate'),
    path('feiras/qa/get/', views.feira_qa_get, name='feira_qa_get'),
    path('feiras/qa/update/', views.feira_qa_update, name='feira_qa_update'),
    path('feiras/qa/delete/', views.feira_qa_delete, name='feira_qa_delete'),
    path('feiras/qa/regenerate-single/', views.feira_qa_regenerate_single, name='feira_qa_regenerate_single'),
    path('feira/<int:feira_id>/qa/add/', views.feira_qa_add, name='feira_qa_add'),

    path('feiras/<int:pk>/qa/progress/', views.feira_qa_progress, name='feira_qa_progress'),
    path('feiras/', views.feira_list, name='feira_list'),
    path('feiras/nova/', views.feira_create, name='feira_create'),
    path('feiras/<int:pk>/', views.feira_detail, name='feira_detail'),
    path('feiras/<int:pk>/editar/', views.feira_update, name='feira_update'),
    path('feiras/<int:pk>/status/', views.feira_toggle_status, name='feira_toggle_status'),
    path('feiras/<int:pk>/search/', views.feira_search, name='feira_search'),
    path('feiras/<int:pk>/reprocess/', views.feira_reprocess, name='feira_reprocess'),
    path('feira/<int:pk>/progresso/', views.feira_progress, name='feira_progress'),
    path('feira/<int:pk>/reset-data/', views.feira_reset_data, name='feira_reset_data'),
    path('feira/<int:pk>/reset-data/confirm/', views.feira_reset_data_confirm, name='feira_reset_data_confirm'),
    path('feira/<int:pk>/progress/', views.feira_progress, name='feira_progress'),
    

    path('feiras/<int:feira_id>/blocos/', views.feira_blocos_list, name='feira_blocos_list'),
    path('feiras/chunk/get/', views.feira_chunk_get, name='feira_chunk_get'),
    path('feiras/chunk/update/', views.feira_chunk_update, name='feira_chunk_update'),
    path('feiras/chunk/delete/', views.feira_chunk_delete, name='feira_chunk_delete'),
    path('feiras/<int:feira_id>/chunk/add/', views.feira_chunk_add, name='feira_chunk_add'),
    path('feiras/chunk/regenerate-vector/', views.feira_chunk_regenerate_vector, name='feira_chunk_regenerate_vector'),

    # Consulta unificada ao banco vetorial
    path('feiras/<int:feira_id>/search-unified/', views.feira_search_unified, name='feira_search_unified'),


    # Integração de QA com Briefing
    path('briefing/<int:briefing_id>/vincular-feira/<int:feira_id>/', views.briefing_vincular_feira, name='briefing_vincular_feira'),
    path('briefing/responder-pergunta/', views.briefing_responder_pergunta, name='briefing_responder_pergunta'),
]  