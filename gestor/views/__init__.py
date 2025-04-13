# gestor/views/__init__.py

# Importações do arquivo base.py
from .base import (
    GestorLoginView,
    home,
    dashboard,
    usuario_list,
    usuario_create,
    usuario_update,
    usuario_toggle_status,
)

# Importações do arquivo feira.py
from .feira import (
    feira_list,
    feira_create,
    feira_update,
    feira_toggle_status,
    feira_detail,
    feira_search,
    feira_reprocess,
    feira_progress,
    feira_qa_list,
    feira_qa_regenerate,
    feira_qa_get,
    feira_qa_update,
    feira_qa_delete,
    feira_qa_regenerate_single,
    parametro_list,
    parametro_create,
    parametro_update,
    parametro_delete,
)

# Importações do arquivo projeto.py
from .projeto import (
    projeto_list,
    projeto_detail,
    projeto_atribuir,
    projeto_alterar_status,
    ver_briefing,
    aprovar_briefing,
    reprovar_briefing,
    upload_arquivo,
    excluir_arquivo,
    mensagens,
    nova_mensagem,
    mensagens_projeto,
)

