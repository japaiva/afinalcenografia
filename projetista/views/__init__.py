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

# Importa as funções legadas e as novas do conceito.py
from .conceito import (
    # Funções legadas (mantidas para compatibilidade)
    gerar_conceito,
    conceito_detalhes,
    upload_imagem,
    excluir_imagem,
    
    # Novas funções do fluxo em 3 etapas
    conceito_visual,
    conceito_etapa1,
    conceito_etapa2,
    conceito_etapa3,
    conceito_completo,
    
    # APIs para integração com IA
    gerar_conceito_ia,
    gerar_imagem_ia,
    gerar_vistas_ia,
    modificar_imagem_ia,
    
    # Exportação
    exportar_conceito
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
    
    # Conceito views legadas
    'gerar_conceito',
    'conceito_detalhes',
    'upload_imagem',
    'excluir_imagem',
    
    # Novas conceito views
    'conceito_visual',
    'conceito_etapa1',
    'conceito_etapa2',
    'conceito_etapa3',
    'conceito_completo',
    
    # APIs para IA
    'gerar_conceito_ia',
    'gerar_imagem_ia',
    'gerar_vistas_ia',
    'modificar_imagem_ia',
    
    # Exportação
    'exportar_conceito',
    
    # Mensagens views
    'mensagens',
    'nova_mensagem',
    'mensagens_projeto'
]