# projetista/views/__init__.py

from .base import (
    ProjetistaLoginView,
    home,
    dashboard
)

from .projeto import (
    projeto_list,
    projeto_detail,
    ver_briefing,
    gerar_conceito,
    salvar_conceito
)

from .mensagens import (
    mensagens,
    nova_mensagem,
    mensagens_projeto
)

# Exporta todas as views para serem acessíveis diretamente do módulo views
__all__ = [
    # Base views
    'ProjetistaLoginView',
    'home',
    'dashboard',
    
    # Projeto views
    'projeto_list',
    'projeto_detail',
    'ver_briefing',
    'gerar_conceito',
    'salvar_conceito',
    
    # Mensagens views
    'mensagens',
    'nova_mensagem',
    'mensagens_projeto'
]