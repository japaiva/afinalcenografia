# gestor/views/__init__.py - ATUALIZADO PARA CREWAI

# Imports da base (atualizados com novas views de crew)
from .base import (
    GestorLoginView, home, dashboard,
    empresa_list, empresa_create, empresa_update, empresa_delete, empresa_toggle_status, 
    usuario_list, usuario_create, usuario_update, usuario_delete, usuario_toggle_status, 
    parametro_list, parametro_create, parametro_update, parametro_delete,
    parametro_indexacao_list, parametro_indexacao_create, parametro_indexacao_update, parametro_indexacao_delete,
    
    # Views de Agente atualizadas
    agente_list, agente_create, agente_update, agente_delete,
    
    # Views de Crew (NOVAS)
    crew_list, crew_create, crew_detail, crew_update, crew_delete,
    crew_add_member, crew_remove_member,
    
    # APIs para AJAX (NOVAS)
    api_agentes_crew_members, api_crew_stats
)

# Imports dos arquivos de feira
from .feira import (
    feira_list, feira_create, feira_update, feira_toggle_status, feira_detail,
    feira_search, feira_reprocess, feira_progress, feira_delete
)

from .feira_qa import (
    feira_qa_list, feira_qa_regenerate, feira_qa_get, feira_qa_update, 
    feira_qa_delete, feira_qa_regenerate_single, feira_qa_progress, feira_qa_add,
    feira_qa_stats
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

# Imports das mensagens
from .mensagens import mensagens, nova_mensagem, mensagens_projeto, limpar_mensagens

# Imports da extração de feiras
from .feira_extracao import feira_extrair_dados, feira_aplicar_dados

__all__ = [
    # Base
    'GestorLoginView', 'home', 'dashboard',
    'empresa_list', 'empresa_create', 'empresa_update', 'empresa_delete', 'empresa_toggle_status',
    'usuario_list', 'usuario_create', 'usuario_update', 'usuario_delete', 'usuario_toggle_status',
    'parametro_list', 'parametro_create', 'parametro_update', 'parametro_delete',
    'parametro_indexacao_list', 'parametro_indexacao_create', 'parametro_indexacao_update', 'parametro_indexacao_delete',
    
    # Agentes (atualizados)
    'agente_list', 'agente_create', 'agente_update', 'agente_delete',
    
    # Crews (NOVOS)
    'crew_list', 'crew_create', 'crew_detail', 'crew_update', 'crew_delete',
    'crew_add_member', 'crew_remove_member',
    
    # APIs AJAX (NOVAS)
    'api_agentes_crew_members', 'api_crew_stats',

    # Feira principal
    'feira_list', 'feira_create', 'feira_update', 'feira_toggle_status',
    'feira_detail', 'feira_search', 'feira_reprocess', 'feira_progress', 'feira_delete',

    # Feira QA
    'feira_qa_list', 'feira_qa_regenerate', 'feira_qa_get', 'feira_qa_update',
    'feira_qa_delete', 'feira_qa_regenerate_single', 'feira_qa_progress',
    'feira_qa_add', 'feira_qa_stats',

    # Feira RAG
    'briefing_vincular_feira', 'briefing_responder_pergunta',
    'feira_reset_data_confirm', 'feira_reset_data', 'feira_search_unified',

    # Feira Chunks
    'feira_blocos_list', 'feira_chunk_get', 'feira_chunk_update', 'feira_chunk_delete',
    'feira_chunk_add', 'feira_chunk_regenerate_vector',

    # Feira Extração
    'feira_extrair_dados', 'feira_aplicar_dados',

    # Projeto
    'projeto_list', 'projeto_detail', 'projeto_atribuir',
    'projeto_alterar_status', 'ver_briefing',

    # Mensagens
    'mensagens', 'nova_mensagem', 'mensagens_projeto', 'limpar_mensagens'
]