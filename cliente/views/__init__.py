# core/views/__init__.py

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

# Importações do arquivo qa_briefing.py
from .qa_briefing import (
    briefing_vincular_feira,
    briefing_responder_pergunta,
    briefing_perguntar_feira
)