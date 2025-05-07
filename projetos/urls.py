# projetos/urls.py

from django.urls import path

# Importações específicas das views refatoradas
from .views.projeto_views import (
    projeto_list, projeto_detail, projeto_create, 
    projeto_update, projeto_delete
)
from .views.projeto_views import (
    selecionar_feira, aprovar_projeto, verificar_manual_feira
)
from .views.projeto_views import (
    projeto_upload_arquivo, projeto_delete_arquivo
)
from .views.briefing_views import (
    iniciar_briefing, concluir_briefing
)
from .views.briefing_views import (
    briefing_etapa, salvar_rascunho_briefing
)
from .views.briefing_views import (
    validar_briefing
)
from .views.briefing_views import (
    enviar_mensagem_ia
)
from .views.briefing_views import (
    upload_arquivo_referencia, excluir_arquivo_referencia
)
from .views.briefing_views import (
    ver_manual_feira, briefing_perguntar_feira
)

app_name = 'projetos'

# Estas URLs são usadas internamente no app projetos
urlpatterns = [
    # URLs de projeto
    path('', projeto_list, name='projeto_list'),
    path('novo/', projeto_create, name='projeto_create'),
    path('<int:pk>/', projeto_detail, name='projeto_detail'),
    path('<int:pk>/editar/', projeto_update, name='projeto_update'),
    path('<int:pk>/excluir/', projeto_delete, name='projeto_delete'),
    path('<int:projeto_id>/selecionar-feira/', selecionar_feira, name='selecionar_feira'),
    path('<int:pk>/aprovar/', aprovar_projeto, name='aprovar_projeto'),
    path('<int:projeto_id>/verificar-manual/', verificar_manual_feira, name='verificar_manual_feira'),
    path('<int:pk>/upload-arquivo/', projeto_upload_arquivo, name='projeto_upload_arquivo'),
    path('<int:pk>/arquivo/<int:arquivo_id>/<str:tipo>/excluir/', projeto_delete_arquivo, name='projeto_delete_arquivo'),
    

    
    # URLs de briefing
    path('<int:projeto_id>/briefing/iniciar/', iniciar_briefing, name='iniciar_briefing'),
    path('<int:projeto_id>/briefing/etapa/<int:etapa>/', briefing_etapa, name='briefing_etapa'),
    path('<int:projeto_id>/briefing/mensagem/', enviar_mensagem_ia, name='enviar_mensagem_ia'),
    path('<int:projeto_id>/briefing/upload/', upload_arquivo_referencia, name='upload_arquivo_referencia'),
    path('<int:projeto_id>/briefing/concluir/', concluir_briefing, name='concluir_briefing'),
    path('<int:projeto_id>/briefing/salvar-rascunho/', salvar_rascunho_briefing, name='salvar_rascunho_briefing'),
    path('<int:projeto_id>/briefing/validar/', validar_briefing, name='validar_briefing'),
    path('arquivo/<int:arquivo_id>/excluir/', excluir_arquivo_referencia, name='excluir_arquivo_referencia'),
    path('<int:projeto_id>/briefing/manual-feira/', ver_manual_feira, name='ver_manual_feira'),
    path('briefing/<int:briefing_id>/perguntar-feira/', briefing_perguntar_feira, name='briefing_perguntar_feira'),
]

# URLs para inclusão em outros apps (cliente, gestor, projetista)
projeto_patterns = [
    path('projetos/', projeto_list, name='projeto_list'),
    path('projetos/novo/', projeto_create, name='projeto_create'),
    path('projetos/<int:pk>/', projeto_detail, name='projeto_detail'),
    path('projetos/<int:pk>/editar/', projeto_update, name='projeto_update'),
    path('projetos/<int:pk>/excluir/', projeto_delete, name='projeto_delete'),
    path('projetos/<int:projeto_id>/selecionar-feira/', selecionar_feira, name='selecionar_feira'),
    path('projetos/<int:pk>/aprovar/', aprovar_projeto, name='aprovar_projeto'),
    path('projetos/<int:projeto_id>/verificar-manual/', verificar_manual_feira, name='verificar_manual_feira'),
    path('projetos/<int:pk>/upload-arquivo/', projeto_upload_arquivo, name='projeto_upload_arquivo'),
    path('projetos/<int:pk>/arquivo/<int:arquivo_id>/<str:tipo>/excluir/', projeto_delete_arquivo, name='projeto_delete_arquivo'),
]

briefing_patterns = [
    path('projeto/<int:projeto_id>/briefing/iniciar/', iniciar_briefing, name='iniciar_briefing'),
    path('projeto/<int:projeto_id>/briefing/etapa/<int:etapa>/', briefing_etapa, name='briefing_etapa'),
    path('projeto/<int:projeto_id>/briefing/mensagem/', enviar_mensagem_ia, name='enviar_mensagem_ia'),
    path('projeto/<int:projeto_id>/briefing/upload/', upload_arquivo_referencia, name='upload_arquivo_referencia'),
    path('projeto/<int:projeto_id>/briefing/concluir/', concluir_briefing, name='concluir_briefing'),
    path('projeto/<int:projeto_id>/briefing/salvar-rascunho/', salvar_rascunho_briefing, name='salvar_rascunho_briefing'),
    path('projeto/<int:projeto_id>/briefing/validar/', validar_briefing, name='validar_briefing'),
    path('arquivo/<int:arquivo_id>/excluir/', excluir_arquivo_referencia, name='excluir_arquivo_referencia'),
    path('projeto/<int:projeto_id>/briefing/manual-feira/', ver_manual_feira, name='ver_manual_feira'),
    path('briefing/<int:briefing_id>/perguntar-feira/', briefing_perguntar_feira, name='briefing_perguntar_feira'),
]