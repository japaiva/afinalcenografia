# Imports da base
from .base import (
    GestorLoginView, home, empresa_list, empresa_create, empresa_update,
    empresa_toggle_status, usuario_list, usuario_create, usuario_update,
    usuario_toggle_status, parametro_list, parametro_create, parametro_update,
    parametro_delete, dashboard, parametro_indexacao_list,
    parametro_indexacao_create, parametro_indexacao_update,
    parametro_indexacao_delete, agente_list, agente_create, agente_update, agente_delete
)

# Imports dos arquivos de feira
from .feira import (
    feira_list, feira_create, feira_update, feira_toggle_status, feira_detail,
    feira_search, feira_reprocess, feira_progress
)

from .feira_qa import (
    feira_qa_list, feira_qa_regenerate, feira_qa_get, feira_qa_update, 
    feira_qa_delete, feira_qa_regenerate_single, feira_qa_progress, feira_qa_add,
    feira_qa_stats  # Este estava faltando no seu __all__
)

from .feira_rag import (
    briefing_vincular_feira, briefing_responder_pergunta, feira_reset_data_confirm, 
    feira_reset_data, feira_search_unified
)

from .feira_chunk import (
    feira_blocos_list, feira_chunk_get, feira_chunk_update, feira_chunk_delete, 
    feira_chunk_add, feira_chunk_regenerate_vector
)

# Imports do projeto
from .projeto import (
    projeto_list, projeto_detail, projeto_atribuir, projeto_alterar_status,
    ver_briefing
)

# Importe as views de mensagens
from .mensagens import mensagens, nova_mensagem, mensagens_projeto,limpar_mensagens

from .feira_extracao import feira_extrair_dados, feira_aplicar_dados

__all__ = [
    # Base
    'GestorLoginView', 'home', 'empresa_list', 'empresa_create', 'empresa_update',
    'empresa_toggle_status', 'usuario_list', 'usuario_create', 'usuario_update',
    'usuario_toggle_status', 'parametro_list', 'parametro_create', 'parametro_update',
    'parametro_delete', 'dashboard', 'parametro_indexacao_list', 
    'parametro_indexacao_create', 'parametro_indexacao_update',
    'parametro_indexacao_delete', 'agente_list', 'agente_create', 'agente_update', 'agente_delete',
    
    # Feira principal
    'feira_list', 'feira_create', 'feira_update', 'feira_toggle_status', 'feira_detail',
    'feira_search', 'feira_reprocess', 'feira_progress',
    
    # Feira QA
    'feira_qa_list', 'feira_qa_regenerate', 'feira_qa_get', 'feira_qa_update', 
    'feira_qa_delete', 'feira_qa_regenerate_single', 'feira_qa_progress', 'feira_qa_add',
    'feira_qa_stats',
    
    # Feira RAG
    'briefing_vincular_feira', 'briefing_responder_pergunta', 'feira_reset_data_confirm', 
    'feira_reset_data', 'feira_search_unified',

    # Mensagens
    'mensagem', 'nova_mensagem', 'mensagens_projeto','limpar_mensagens',

    # Feira Extração
    'feira_extrair_dados', 'feira_aplicar_dados',

    # Feira Chunks
    'feira_blocos_list', 'feira_chunk_get', 'feira_chunk_update', 'feira_chunk_delete', 
    'feira_chunk_add', 'feira_chunk_regenerate_vector',
    
    # Projeto
    'projeto_list', 'projeto_detail', 'projeto_atribuir', 'projeto_alterar_status',
    'ver_briefing', 'mensagens', 'nova_mensagem', 'mensagens_projeto'
]