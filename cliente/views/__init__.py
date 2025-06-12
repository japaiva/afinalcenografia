# core/views/__init__.py
from core.decorators import cliente_required

# Importações do arquivo base.py (views principais e únicas)
from .base import (
    ClienteLoginView,
    home,
    dashboard,  # Esta é a view principal do dashboard
    usuario_list,
    usuario_detail,
    empresa_detail,
    determinar_tipo_arquivo,
    briefing  # Função de compatibilidade
)

# Importações do arquivo projeto.py (views especializadas de projeto)
from .projeto import (
    projeto_list,
    projeto_detail,
    projeto_create,
    projeto_update,
    projeto_delete,
    selecionar_feira,
    aprovar_projeto,
    verificar_manual_feira,
    processar_upload_manual,
    # Classes baseadas em view também
    ProjetoListView,
    ProjetoDetailView,
    ProjetoCreateView,
    ProjetoUpdateView,
    ProjetoDeleteView
)

# Importações do arquivo mensagens.py (views especializadas de mensagens)
from .mensagens import (
    mensagens, 
    nova_mensagem, 
    mensagens_projeto
)

# Importações do arquivo briefing.py (views especializadas de briefing)
from .briefing import (
    briefing_etapa,
    salvar_rascunho_briefing,
    concluir_briefing,
    iniciar_briefing,  # Esta é a view principal do briefing
    upload_arquivo_referencia,
    excluir_arquivo_referencia,
    ver_manual_feira,
    validar_briefing,
    gerar_relatorio_briefing,
    briefing_perguntar_feira
)

# Lista para facilitar importações em massa se necessário
__all__ = [
    # Views de base (principais e únicas)
    'ClienteLoginView',
    'home',
    'dashboard',
    'usuario_list', 
    'usuario_detail',
    'empresa_detail',
    'determinar_tipo_arquivo',
    'briefing',
    
    # Views de projeto (especializadas)
    'projeto_list',
    'projeto_detail', 
    'projeto_create',
    'projeto_update',
    'projeto_delete',
    'selecionar_feira',
    'aprovar_projeto',
    'verificar_manual_feira',
    'processar_upload_manual',
    'ProjetoListView',
    'ProjetoDetailView',
    'ProjetoCreateView', 
    'ProjetoUpdateView',
    'ProjetoDeleteView',
    
    # Views de mensagens
    'mensagens',
    'nova_mensagem',
    'mensagens_projeto',
    
    # Views de briefing
    'briefing_etapa',
    'salvar_rascunho_briefing',
    'concluir_briefing',
    'iniciar_briefing',
    'upload_arquivo_referencia',
    'excluir_arquivo_referencia',
    'ver_manual_feira',
    'validar_briefing',
    'gerar_relatorio_briefing',
    'briefing_perguntar_feira',
    
    # Decorators
    'cliente_required'
]