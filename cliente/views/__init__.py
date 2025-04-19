# core/views/__init__.py
from core.decorators import cliente_required

# Importações do arquivo base.py
from .base import (
    ClienteLoginView,
    cliente_required,
    home,
    dashboard,
    usuario_list,
    usuario_detail,
    empresa_detail,
    projeto_list,
    projeto_detail,
    projeto_create,
    projeto_update,
    projeto_delete,
    briefing,
    mensagens,
    nova_mensagem,
    mensagens_projeto
)

# Importações do arquivo projeto.py
from .projeto import (
    dashboard as projeto_dashboard,
    projeto_list as projeto_list_view,
    projeto_detail as projeto_detail_view,
    projeto_create as projeto_create_view,
    projeto_update as projeto_update_view,
    projeto_delete as projeto_delete_view,
    selecionar_feira,
    upload_planta,
    upload_referencia,
    delete_planta,
    delete_referencia,
    iniciar_briefing,
    verificar_manual_feira
)

# Importações do arquivo briefing.py
from .briefing import (
    briefing_etapa,
    salvar_rascunho_briefing,
    concluir_briefing,
    upload_arquivo_referencia,
    excluir_arquivo_referencia,
    ver_manual_feira,
    validar_briefing
)
