# projetista/urls.py - VERSÃO CORRIGIDA

from django.urls import path
from .views import (
    # Base views
    ProjetistaLoginView, home, dashboard,
    
    # Projeto views
    projeto_list, projeto_detail, ver_briefing,
    
    # Planta Baixa views (atualizadas para CrewAI)
    gerar_planta_baixa, refinar_planta_baixa, visualizar_planta_baixa, 
    download_planta_svg, comparar_plantas, validar_agente_status, 
    exportar_dados_planta,
    
    # Conceito Visual views (baseado em planta baixa)
    gerar_conceito_visual, refinar_conceito_visual, visualizar_conceito_visual,
    galeria_conceitos, download_conceito_imagem, exportar_dados_conceito,
    status_conceito_visual, duplicar_conceito, excluir_conceito,
    
    # Modelo 3D views (baseado em planta + conceito)
    gerar_modelo_3d, refinar_modelo_3d, visualizar_modelo_3d, viewer_interativo,
    download_modelo_3d, download_todos_formatos, exportar_dados_modelo,
    status_modelo_3d, atualizar_camera_modelo, adicionar_ponto_interesse,
    excluir_modelo, preview_modelo,
    
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
    # PIPELINE NOVO: PLANTA BAIXA → CONCEITO VISUAL → MODELO 3D
    # =========================================================================
    
    # -------------------------------------------------------------------------
    # BOTÃO 1 - PLANTA BAIXA (via CrewAI "Gerador de Plantas Baixas Pipeline")
    # -------------------------------------------------------------------------
    
    # Geração e refinamento
    path('projetos/<int:projeto_id>/planta-baixa/gerar/', 
         gerar_planta_baixa, name='gerar_planta_baixa'),
    path('projetos/<int:projeto_id>/planta-baixa/refinar/', 
         refinar_planta_baixa, name='refinar_planta_baixa'),
    
    # Visualização e downloads
    path('projetos/<int:projeto_id>/planta-baixa/', 
         visualizar_planta_baixa, name='visualizar_planta_baixa'),
    path('planta-baixa/<int:planta_id>/download-svg/', 
         download_planta_svg, name='download_planta_svg'),
    path('planta-baixa/<int:planta_id>/exportar/', 
         exportar_dados_planta, name='exportar_dados_planta'),
    
    # Comparação e análise
    path('projetos/<int:projeto_id>/planta-baixa/comparar/', 
         comparar_plantas, name='comparar_plantas'),
    
    # -------------------------------------------------------------------------
    # BOTÃO 2 - CONCEITO VISUAL (via CrewAI baseado na planta baixa)
    # -------------------------------------------------------------------------
    
    # Geração (requer planta baixa)
    path('projetos/<int:projeto_id>/conceito-visual/gerar/', 
         gerar_conceito_visual, name='gerar_conceito_visual'),
    path('projetos/<int:projeto_id>/conceito-visual/gerar/<int:planta_id>/', 
         gerar_conceito_visual, name='gerar_conceito_visual_from_planta'),
    
    # Refinamento e duplicação
    path('conceito-visual/<int:conceito_id>/refinar/', 
         refinar_conceito_visual, name='refinar_conceito_visual'),
    path('conceito-visual/<int:conceito_id>/duplicar/', 
         duplicar_conceito, name='duplicar_conceito'),
    
    # Visualização
    path('projetos/<int:projeto_id>/conceito-visual/', 
         visualizar_conceito_visual, name='visualizar_conceito_visual'),
    path('projetos/<int:projeto_id>/conceito-visual/galeria/', 
         galeria_conceitos, name='galeria_conceitos'),
    
    # Downloads e exportação
    path('conceito-visual/<int:conceito_id>/download/', 
         download_conceito_imagem, name='download_conceito_imagem'),
    path('conceito-visual/<int:conceito_id>/exportar/', 
         exportar_dados_conceito, name='exportar_dados_conceito'),
    
    # Status e utilitários
    path('projetos/<int:projeto_id>/conceito-visual/status/', 
         status_conceito_visual, name='status_conceito_visual'),
    path('conceito-visual/<int:conceito_id>/excluir/', 
         excluir_conceito, name='excluir_conceito'),
    
    # -------------------------------------------------------------------------
    # BOTÃO 3 - MODELO 3D (via CrewAI baseado em planta + conceito)
    # -------------------------------------------------------------------------
    
    # Geração (requer planta baixa e conceito visual)
    path('projetos/<int:projeto_id>/modelo-3d/gerar/', 
         gerar_modelo_3d, name='gerar_modelo_3d'),
    path('projetos/<int:projeto_id>/modelo-3d/gerar/<int:planta_id>/', 
         gerar_modelo_3d, name='gerar_modelo_3d_from_planta'),
    path('projetos/<int:projeto_id>/modelo-3d/gerar/<int:planta_id>/<int:conceito_id>/', 
         gerar_modelo_3d, name='gerar_modelo_3d_from_planta_conceito'),
    
    # Refinamento
    path('modelo-3d/<int:modelo_id>/refinar/', 
         refinar_modelo_3d, name='refinar_modelo_3d'),
    
    # Visualização e interação
    path('projetos/<int:projeto_id>/modelo-3d/', 
         visualizar_modelo_3d, name='visualizar_modelo_3d'),
    path('modelo-3d/<int:modelo_id>/viewer/', 
         viewer_interativo, name='viewer_interativo'),
    path('modelo-3d/<int:modelo_id>/preview/', 
         preview_modelo, name='preview_modelo'),
    
    # Downloads e exportação
    path('modelo-3d/<int:modelo_id>/download/<str:formato>/', 
         download_modelo_3d, name='download_modelo_3d'),
    path('modelo-3d/<int:modelo_id>/download-todos/', 
         download_todos_formatos, name='download_todos_formatos'),
    path('modelo-3d/<int:modelo_id>/exportar/', 
         exportar_dados_modelo, name='exportar_dados_modelo'),
    
    # Configurações 3D
    path('modelo-3d/<int:modelo_id>/camera/atualizar/', 
         atualizar_camera_modelo, name='atualizar_camera_modelo'),
    path('modelo-3d/<int:modelo_id>/ponto-interesse/adicionar/', 
         adicionar_ponto_interesse, name='adicionar_ponto_interesse'),
    path('modelo-3d/<int:modelo_id>/excluir/', 
         excluir_modelo, name='excluir_modelo'),
    
    # =========================================================================
    # UTILITÁRIOS E STATUS
    # =========================================================================
    
    # Status dos crews e agentes
    path('agente/validar/', validar_agente_status, name='validar_agente_status'),
    path('projetos/<int:projeto_id>/modelo-3d/status/', 
         status_modelo_3d, name='status_modelo_3d'),
    
    # =========================================================================
    # SISTEMA DE MENSAGENS
    # =========================================================================
    path('mensagens/', mensagens, name='mensagens'),
    path('mensagens/nova/', nova_mensagem, name='nova_mensagem'),
    path('mensagens/projeto/<int:projeto_id>/', mensagens_projeto, name='mensagens_projeto'),
]

# =============================================================================
# COMENTÁRIO EXPLICATIVO: VIEWS QUE PRECISAM SER IMPLEMENTADAS
# =============================================================================

"""
VIEWS QUE PRECISAM EXISTIR NO projetista/views/:

📋 BÁSICAS (já devem existir):
- ProjetistaLoginView, home, dashboard
- projeto_list, projeto_detail, ver_briefing
- mensagens, nova_mensagem, mensagens_projeto

🏗️ PLANTA BAIXA (devem existir ou ser adaptadas):
- gerar_planta_baixa ✅ (já existe)
- refinar_planta_baixa ✅ (já existe)  
- visualizar_planta_baixa ✅ (já existe)
- download_planta_svg ✅ (já existe)
- comparar_plantas ✅ (já existe)
- validar_agente_status ✅ (já existe)
- exportar_dados_planta ✅ (já existe)

🎨 CONCEITO VISUAL (precisam ser criadas):
- gerar_conceito_visual ❌ (criar)
- refinar_conceito_visual ❌ (criar)
- visualizar_conceito_visual ❌ (criar)
- galeria_conceitos ❌ (criar)
- download_conceito_imagem ❌ (criar)
- exportar_dados_conceito ❌ (criar)
- status_conceito_visual ❌ (criar)
- duplicar_conceito ❌ (criar)
- excluir_conceito ❌ (criar)

🏢 MODELO 3D (precisam ser criadas):
- gerar_modelo_3d ❌ (criar)
- refinar_modelo_3d ❌ (criar)
- visualizar_modelo_3d ❌ (criar)
- viewer_interativo ❌ (criar)
- download_modelo_3d ❌ (criar)
- download_todos_formatos ❌ (criar)
- exportar_dados_modelo ❌ (criar)
- status_modelo_3d ❌ (criar)
- atualizar_camera_modelo ❌ (criar)
- adicionar_ponto_interesse ❌ (criar)
- excluir_modelo ❌ (criar)
- preview_modelo ❌ (criar)

PRÓXIMOS PASSOS:
1. Verificar quais views já existem
2. Criar as views que faltam
3. Implementar os templates correspondentes
4. Configurar os crews no admin
"""