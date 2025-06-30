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

# Imports dos novos arquivos separados
from .planta_baixa import (
    # Geração e Regeneração
    gerar_planta_baixa,
    refinar_planta_baixa,
    
    # Visualização e Downloads
    visualizar_planta_baixa,
    download_planta_svg,
    
    # Comparação e Análise
    comparar_plantas,
    
    # Utilitários
    validar_agente_status,
    exportar_dados_planta
)

from .conceito_visual import (
    # Geração e Refinamento
    gerar_conceito_visual,
    refinar_conceito_visual,
    
    # Visualização
    visualizar_conceito_visual,
    galeria_conceitos,
    
    # Downloads e Exportação
    download_conceito_imagem,
    exportar_dados_conceito,
    
    # Utilitários e AJAX
    status_conceito_visual,
    duplicar_conceito,
    excluir_conceito
)

from .modelo_3d import (
    # Geração e Refinamento
    gerar_modelo_3d,
    refinar_modelo_3d,
    
    # Visualização
    visualizar_modelo_3d,
    viewer_interativo,
    
    # Downloads e Exportação
    download_modelo_3d,
    download_todos_formatos,
    exportar_dados_modelo,
    
    # Utilitários e AJAX
    status_modelo_3d,
    atualizar_camera_modelo,
    adicionar_ponto_interesse,
    excluir_modelo,
    preview_modelo
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
    
    # Planta Baixa - Geração
    'gerar_planta_baixa',
    'refinar_planta_baixa',
    
    # Planta Baixa - Visualização
    'visualizar_planta_baixa',
    'download_planta_svg',
    'comparar_plantas',
    
    # Planta Baixa - Utilitários
    'validar_agente_status',
    'exportar_dados_planta',
    
    # Conceito Visual - Geração
    'gerar_conceito_visual',
    'refinar_conceito_visual',
    
    # Conceito Visual - Visualização
    'visualizar_conceito_visual',
    'galeria_conceitos',
    
    # Conceito Visual - Downloads
    'download_conceito_imagem',
    'exportar_dados_conceito',
    
    # Conceito Visual - Utilitários
    'status_conceito_visual',
    'duplicar_conceito',
    'excluir_conceito',
    
    # Modelo 3D - Geração
    'gerar_modelo_3d',
    'refinar_modelo_3d',
    
    # Modelo 3D - Visualização
    'visualizar_modelo_3d',
    'viewer_interativo',
    
    # Modelo 3D - Downloads
    'download_modelo_3d',
    'download_todos_formatos',
    'exportar_dados_modelo',
    
    # Modelo 3D - Utilitários
    'status_modelo_3d',
    'atualizar_camera_modelo',
    'adicionar_ponto_interesse',
    'excluir_modelo',
    'preview_modelo',
    
    # Mensagens views
    'mensagens',
    'nova_mensagem',
    'mensagens_projeto'
]