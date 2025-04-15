from .base import (
    GestorLoginView, home, empresa_list, empresa_create, empresa_update,
    empresa_toggle_status, usuario_list, usuario_create, usuario_update,
    usuario_toggle_status, parametro_list, parametro_create, parametro_update,
    parametro_delete, dashboard, parametro_indexacao_list,
    parametro_indexacao_create, parametro_indexacao_update,
    parametro_indexacao_delete, agente_list, agente_create, agente_update, agente_delete
)

from .feira import (
    feira_list, feira_create, feira_update, feira_toggle_status, feira_detail,
    feira_search, feira_reprocess, feira_progress, feira_qa_list,
    feira_qa_regenerate, feira_qa_get, feira_qa_update, feira_qa_delete,
    feira_qa_regenerate_single, briefing_vincular_feira, briefing_responder_pergunta,
    feira_reset_data_confirm, feira_reset_data, feira_qa_progress, feira_qa_add, feira_blocos_list,
    feira_chunk_get, feira_chunk_update, feira_chunk_delete, feira_chunk_add, feira_chunk_regenerate_vector,
    feira_search_unified
)

from .projeto import (
    projeto_list, projeto_detail, projeto_atribuir, projeto_alterar_status,
    ver_briefing, aprovar_briefing, reprovar_briefing, upload_arquivo,
    excluir_arquivo, mensagens, nova_mensagem, mensagens_projeto
)

__all__ = [
    'GestorLoginView', 'home', 'empresa_list', 'empresa_create', 'empresa_update',
    'empresa_toggle_status', 'usuario_list', 'usuario_create', 'usuario_update',
    'usuario_toggle_status', 'parametro_list', 'parametro_create', 'parametro_update',
    'parametro_delete', 'dashboard',
    'feira_list', 'feira_create', 'feira_update', 'feira_toggle_status', 'feira_detail',
    'feira_search', 'feira_reprocess', 'feira_progress', 'feira_qa_list',
    'feira_qa_regenerate', 'feira_qa_get', 'feira_qa_update', 'feira_qa_delete',
    'feira_qa_regenerate_single', 'briefing_vincular_feira', 'briefing_responder_pergunta',
    'projeto_list', 'projeto_detail', 'projeto_atribuir', 'projeto_alterar_status',
    'ver_briefing', 'aprovar_briefing', 'reprovar_briefing', 'upload_arquivo',
    'excluir_arquivo', 'mensagens', 'nova_mensagem', 'mensagens_projeto',
    'parametro_indexacao_list', 'parametro_indexacao_create', 'parametro_indexacao_update',
    'parametro_indexacao_delete', 'agente_list', 'agente_create', 'agente_update', 'agente_delete',
    'feira_reset_data_confirm', 'feira_reset_data', 'feira_qa_progress', 'feira_qa_add','feira_blocos_list',
    'feira_chunk_get', 'feira_chunk_update', 'feira_chunk_delete', 'feira_chunk_add', 
    'feira_chunk_regenerate_vector','feira_search_unified'
]