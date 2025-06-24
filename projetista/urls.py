# projetista/urls.py

from django.urls import path
from .views import (
    # Base views
    ProjetistaLoginView, home, dashboard,
    
    # Projeto views
    projeto_list, projeto_detail, ver_briefing,
    
    # NOVO SISTEMA - Views do novo_conceito.py
    novo_conceito_dashboard, 
    gerar_planta_baixa, visualizar_planta_baixa, download_planta_svg,
    gerar_conceito_visual, visualizar_conceito_visual, refinar_conceito_visual,
    gerar_modelo_3d, visualizar_modelo_3d, download_modelo_3d,
    status_projeto_conceito, restaurar_versao, excluir_versao,
    
    # Mensagens views
    mensagens, nova_mensagem, mensagens_projeto
)

app_name = 'projetista'

urlpatterns = [
    # =========================================================================
    # AUTENTICAÇÃO E HOME
    # =========================================================================
    path('', home, name='home'),
    path('login/', ProjetistaLoginView.as_view(), name='login'),
    path('dashboard/', dashboard, name='dashboard'),
    
    # =========================================================================
    # GESTÃO DE PROJETOS
    # =========================================================================
    path('projetos/', projeto_list, name='projeto_list'),
    path('projetos/<int:pk>/', projeto_detail, name='projeto_detail'),
    path('projetos/<int:projeto_id>/briefing/', ver_briefing, name='ver_briefing'),
    
    # =========================================================================
    # NOVO SISTEMA - 3 BOTÕES (Planta, Conceito, Modelo 3D)
    # =========================================================================
    
    # Dashboard principal do novo sistema
    path('projetos/<int:projeto_id>/novo-conceito/', novo_conceito_dashboard, name='novo_conceito_dashboard'),
    
    # PLANTA BAIXA
    path('projetos/<int:projeto_id>/planta-baixa/gerar/', gerar_planta_baixa, name='gerar_planta_baixa'),
    path('projetos/<int:projeto_id>/planta-baixa/', visualizar_planta_baixa, name='visualizar_planta_baixa'),
    path('planta-baixa/<int:planta_id>/download-svg/', download_planta_svg, name='download_planta_svg'),
    
    # CONCEITO VISUAL NOVO
    path('projetos/<int:projeto_id>/conceito-visual/gerar/', gerar_conceito_visual, name='gerar_conceito_visual'),
    path('projetos/<int:projeto_id>/conceito-visual/', visualizar_conceito_visual, name='visualizar_conceito_visual'),
    path('conceito-visual/<int:conceito_id>/refinar/', refinar_conceito_visual, name='refinar_conceito_visual'),
    
    # MODELO 3D
    path('projetos/<int:projeto_id>/modelo-3d/gerar/', gerar_modelo_3d, name='gerar_modelo_3d'),
    path('projetos/<int:projeto_id>/modelo-3d/', visualizar_modelo_3d, name='visualizar_modelo_3d'),
    path('modelo-3d/<int:modelo_id>/download/<str:formato>/', download_modelo_3d, name='download_modelo_3d'),
    
    # UTILITÁRIOS E AJAX
    path('projetos/<int:projeto_id>/status/', status_projeto_conceito, name='status_projeto_conceito'),
    path('restaurar-versao/<str:tipo>/<int:objeto_id>/', restaurar_versao, name='restaurar_versao'),
    path('excluir-versao/<str:tipo>/<int:objeto_id>/', excluir_versao, name='excluir_versao'),
    
    # =========================================================================
    # SISTEMA DE MENSAGENS
    # =========================================================================
    path('mensagens/', mensagens, name='mensagens'),
    path('mensagens/nova/', nova_mensagem, name='nova_mensagem'),
    path('mensagens/projeto/<int:projeto_id>/', mensagens_projeto, name='mensagens_projeto'),
]