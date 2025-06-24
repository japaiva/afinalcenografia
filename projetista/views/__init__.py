# projetista/views/__init__.py

from .base import (
    ProjetistaLoginView,
    home,
    dashboard
)

from .projeto import (
    projeto_list,
    projeto_detail,
    ver_briefing
)

from .novo_conceito import (
    # Dashboard principal
    novo_conceito_dashboard,
    
    # Planta Baixa
    gerar_planta_baixa,
    visualizar_planta_baixa,
    download_planta_svg,
    
    # Conceito Visual
    gerar_conceito_visual,
    visualizar_conceito_visual,
    refinar_conceito_visual,
    
    # Modelo 3D
    gerar_modelo_3d,
    visualizar_modelo_3d,
    download_modelo_3d,
    
    # Utilitários e AJAX
    status_projeto_conceito,
    restaurar_versao,
    excluir_versao
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
    
    # Novo Conceito - Dashboard
    'novo_conceito_dashboard',
    
    # Novo Conceito - Planta Baixa
    'gerar_planta_baixa',
    'visualizar_planta_baixa',
    'download_planta_svg',
    
    # Novo Conceito - Conceito Visual
    'gerar_conceito_visual',
    'visualizar_conceito_visual',
    'refinar_conceito_visual',
    
    # Novo Conceito - Modelo 3D
    'gerar_modelo_3d',
    'visualizar_modelo_3d',
    'download_modelo_3d',
    
    # Novo Conceito - Utilitários
    'status_projeto_conceito',
    'restaurar_versao',
    'excluir_versao',
    
    # Mensagens views
    'mensagens',
    'nova_mensagem',
    'mensagens_projeto'
]