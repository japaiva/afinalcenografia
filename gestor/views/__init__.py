# gestor/views/__init__.py - ATUALIZADO PARA CREWAI

# Imports da base
from .base import (
    GestorLoginView, home, dashboard,
    empresa_list, empresa_create, empresa_update, empresa_delete, empresa_toggle_status, 
    usuario_list, usuario_create, usuario_update, usuario_delete, usuario_toggle_status, 
    parametro_list, parametro_create, parametro_update, parametro_delete,
    parametro_indexacao_list, parametro_indexacao_create, parametro_indexacao_update, parametro_indexacao_delete,
) # Removed agent and crew views from here

# Imports de agents_crews (NOVOS)
from .agents_crews import (
    agente_list, agente_create, agente_update, agente_delete, # These are in agents_crews.py
    crew_list, crew_create, crew_detail, crew_update, crew_delete, # These are in agents_crews.py
    crew_add_member, crew_member_update, crew_member_delete, crew_member_reorder, # These are in agents_crews.py
    crew_task_list, crew_task_create, crew_task_update, crew_task_delete, crew_task_duplicate, crew_task_reorder, # These are in agents_crews.py
    crew_validate, crew_toggle, 
    api_agentes_crew_members, api_crew_stats # These are in agents_crews.py
)

# Imports do Conceito Visual (NOVO)
from .conceito_visual import (
    conceito_visual,
    conceito_etapa1_esboco,
    conceito_etapa2_referencias,
    conceito_etapa3_geracao
) # These are in conceito_visual.py

# Imports da Planta Baixa
from .planta_baixa import (
    planta_baixa_wizard,
    planta_etapa1_analisar,
    planta_etapa2_estruturar,
    planta_etapa3_validar,
    planta_etapa4_gerar_svg,
    planta_executar_todas
) # These are in planta_baixa.py

# Imports do Ajuste Conversacional da Planta Baixa
from .planta_baixa_ajuste_view import (
    AjusteConversacionalView,
    AplicarAjustesView
) # These are in planta_baixa_ajuste_view.py

# Imports da Renderização AI
from .renderizacao_ai import (
    renderizacao_ai_wizard,
    renderizacao_etapa1_enriquecer,
    renderizacao_etapa2_gerar,
    renderizacao_executar_tudo
) # These are in renderizacao_ai.py

# Imports do Modelo 3D
from .modelo_3d import (
    modelo_3d_wizard,
    modelo_3d_gerar,
    modelo_3d_download,
    modelo_3d_download_mtl
) # These are in modelo_3d.py

# Imports dos arquivos de feira
from .feira import (
    feira_list, feira_create, feira_update, feira_toggle_status, feira_detail,
    feira_search, feira_reprocess, feira_progress, feira_delete
) # These are in feira.py

from .feira_qa import (
    feira_qa_list, feira_qa_regenerate, feira_qa_get, feira_qa_update, 
    feira_qa_delete, feira_qa_regenerate_single, feira_qa_progress, feira_qa_add,
    feira_qa_stats
) # These are in feira_qa.py

from .feira_rag import (
    briefing_vincular_feira, briefing_responder_pergunta, feira_reset_data_confirm, 
    feira_reset_data, feira_search_unified
) # These are in feira_rag.py

from .feira_chunk import (
    feira_blocos_list, feira_chunk_get, feira_chunk_update, feira_chunk_delete, 
    feira_chunk_add, feira_chunk_regenerate_vector
) # These are in feira_chunk.py

# Imports do projeto
from .projeto import (
    projeto_list, projeto_detail, projeto_atribuir, projeto_alterar_status,
    ver_briefing
) # These are in projeto.py

# Imports das mensagens
from .mensagens import mensagens, nova_mensagem, mensagens_projeto, limpar_mensagens # These are in mensagens.py

# Imports da extração de feiras
from .feira_extracao import feira_extrair_dados, feira_aplicar_dados # These are in feira_extracao.py

__all__ = [
    # Base
    'GestorLoginView', 'home', 'dashboard',
    'empresa_list', 'empresa_create', 'empresa_update', 'empresa_delete', 'empresa_toggle_status',
    'usuario_list', 'usuario_create', 'usuario_update', 'usuario_delete', 'usuario_toggle_status',
    'parametro_list', 'parametro_create', 'parametro_update', 'parametro_delete',
    'parametro_indexacao_list', 'parametro_indexacao_create', 'parametro_indexacao_update', 'parametro_indexacao_delete',
    
    # Agentes (atualizados)
    'agente_list', 'agente_create', 'agente_update', 'agente_delete', # From agents_crews.py
    
    # Crews (NOVOS)
    'crew_list', 'crew_create', 'crew_detail', 'crew_update', 'crew_delete', # From agents_crews.py
    'crew_add_member', 'crew_member_update', 'crew_member_delete', 'crew_member_reorder', # From agents_crews.py
    'crew_task_list', 'crew_task_create', 'crew_task_update', 'crew_task_delete', 'crew_task_duplicate', 'crew_task_reorder', # From agents_crews.py
    'crew_validate', 'crew_toggle', 
    
    # APIs AJAX (NOVAS)
    'api_agentes_crew_members', 'api_crew_stats', # From agents_crews.py

    # Feira principal
    'feira_list', 'feira_create', 'feira_update', 'feira_toggle_status',
    'feira_detail', 'feira_search', 'feira_reprocess', 'feira_progress', 'feira_delete', # From feira.py

    # Feira QA
    'feira_qa_list', 'feira_qa_regenerate', 'feira_qa_get', 'feira_qa_update',
    'feira_qa_delete', 'feira_qa_regenerate_single', 'feira_qa_progress',
    'feira_qa_add', 'feira_qa_stats', # From feira_qa.py

    # Feira RAG
    'briefing_vincular_feira', 'briefing_responder_pergunta',
    'feira_reset_data_confirm', 'feira_reset_data', 'feira_search_unified', # From feira_rag.py

    # Feira Chunks
    'feira_blocos_list', 'feira_chunk_get', 'feira_chunk_update', 'feira_chunk_delete',
    'feira_chunk_add', 'feira_chunk_regenerate_vector', # From feira_chunk.py

    # Feira Extração
    'feira_extrair_dados', 'feira_aplicar_dados', # From feira_extracao.py

    # Projeto
    'projeto_list', 'projeto_detail', 'projeto_atribuir',
    'projeto_alterar_status', 'ver_briefing', # From projeto.py

    # Conceito Visual
    'conceito_visual',
    'conceito_etapa1_esboco',
    'conceito_etapa2_referencias',
    'conceito_etapa3_geracao',

    # Planta Baixa
    'planta_baixa_wizard',
    'planta_etapa1_analisar',
    'planta_etapa2_estruturar',
    'planta_etapa3_validar',
    'planta_etapa4_gerar_svg',
    'planta_executar_todas',

    # Planta Baixa - Ajuste Conversacional
    'AjusteConversacionalView',
    'AplicarAjustesView',

    # Renderização AI
    'renderizacao_ai_wizard',
    'renderizacao_etapa1_enriquecer',
    'renderizacao_etapa2_gerar',
    'renderizacao_executar_tudo',

    # Modelo 3D
    'modelo_3d_wizard',
    'modelo_3d_gerar',
    'modelo_3d_download',
    'modelo_3d_download_mtl',

    # Mensagens
    'mensagens', 'nova_mensagem', 'mensagens_projeto', 'limpar_mensagens' # From mensagens.py
]