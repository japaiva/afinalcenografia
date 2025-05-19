# projetista/urls.py

from django.urls import path
from .views import (
    # Base views
    ProjetistaLoginView, home, dashboard,
    
    # Projeto views
    projeto_list, projeto_detail, ver_briefing,
    
    # Conceito views (legadas e novas)
    gerar_conceito, conceito_detalhes, upload_imagem, excluir_imagem,
    conceito_visual, conceito_etapa1, conceito_etapa2, conceito_etapa3, conceito_completo,
    gerar_conceito_ia, gerar_imagem_ia, gerar_vistas_ia, modificar_imagem_ia, exportar_conceito,
    
    # Mensagens views
    mensagens, nova_mensagem, mensagens_projeto
)

app_name = 'projetista'

urlpatterns = [
    # Nova URL para login
    path('login/', ProjetistaLoginView.as_view(), name='login'),
    
    # Páginas principais
    path('', home, name='home'),
    path('dashboard/', dashboard, name='dashboard'),
    
    # Gestão de Projetos
    path('projetos/', projeto_list, name='projeto_list'),
    path('projetos/<int:pk>/', projeto_detail, name='projeto_detail'),
    path('projetos/<int:projeto_id>/briefing/', ver_briefing, name='ver_briefing'),
    
    # URLs legadas do conceito visual (para compatibilidade)
    path('projetos/<int:projeto_id>/gerar-conceito/', gerar_conceito, name='gerar_conceito'),
    path('conceito/<int:conceito_id>/', conceito_detalhes, name='conceito_detalhes'),
    path('conceito/<int:conceito_id>/upload-imagem/', upload_imagem, name='upload_imagem'),
    path('imagem/<int:imagem_id>/excluir/', excluir_imagem, name='excluir_imagem'),
    
    # Novas URLs para o fluxo de 3 etapas
    path('projetos/<int:projeto_id>/conceito/', conceito_visual, name='conceito_visual'),
    path('projetos/<int:projeto_id>/conceito/etapa1/', conceito_etapa1, name='conceito_etapa1'),
    path('projetos/<int:projeto_id>/conceito/etapa2/', conceito_etapa2, name='conceito_etapa2'),
    path('projetos/<int:projeto_id>/conceito/etapa3/', conceito_etapa3, name='conceito_etapa3'),
    path('conceito/<int:conceito_id>/completo/', conceito_completo, name='conceito_completo'),
    
    # APIs para integração com IA
    path('conceito/<int:projeto_id>/gerar-conceito-ia/', gerar_conceito_ia, name='gerar_conceito_ia'),
    path('conceito/<int:conceito_id>/gerar-imagem-ia/', gerar_imagem_ia, name='gerar_imagem_ia'),
    path('conceito/<int:conceito_id>/gerar-vistas-ia/', gerar_vistas_ia, name='gerar_vistas_ia'),
    path('conceito/imagem/<int:imagem_id>/modificar-ia/', modificar_imagem_ia, name='modificar_imagem_ia'),
    
    # Exportação
    path('conceito/<int:conceito_id>/exportar/<str:formato>/', exportar_conceito, name='exportar_conceito'),
    
    # Sistema de Mensagens
    path('mensagens/', mensagens, name='mensagens'),
    path('mensagens/nova/', nova_mensagem, name='nova_mensagem'),
    path('mensagens/projeto/<int:projeto_id>/', mensagens_projeto, name='mensagens_projeto'),
]