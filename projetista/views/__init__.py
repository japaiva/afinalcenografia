# projetista/views/__init__.py - VERSÃO CORRIGIDA PARA CREWAI

# Importações básicas
from .base import ProjetistaLoginView, home, dashboard

# Importações de projetos (corrigir nome do arquivo)
from .projeto import projeto_list, projeto_detail, ver_briefing

# Importações de planta baixa (ATUALIZADAS PARA CREWAI)
from .planta_baixa import (
    gerar_planta_baixa,
    refinar_planta_baixa,
    visualizar_planta_baixa,
    download_planta_svg,
    comparar_plantas,
    validar_crew_status,  # ← MUDANÇA: era validar_agente_status
    exportar_dados_planta,
    testar_crewai_config,  # ← NOVO
    debug_crew_info,       # ← NOVO
    obter_logs_execucao,  # ← ADICIONADO
    status_execucao, 
)

# Importações de conceito visual (tentar importar, criar stubs se não existir)
try:
    from .conceito_visual import (
        gerar_conceito_visual,
        refinar_conceito_visual,
        visualizar_conceito_visual,
        galeria_conceitos,
        download_conceito_imagem,
        exportar_dados_conceito,
        status_conceito_visual,
        duplicar_conceito,
        excluir_conceito,
    )
except ImportError:
    # Views não implementadas ainda - criar stubs que retornam erro 501
    from django.http import JsonResponse
    from django.shortcuts import render
    
    def gerar_conceito_visual(*args, **kwargs):
        return JsonResponse({'error': 'Funcionalidade em desenvolvimento', 'status': 501})
    
    def refinar_conceito_visual(*args, **kwargs):
        return JsonResponse({'error': 'Funcionalidade em desenvolvimento', 'status': 501})
    
    def visualizar_conceito_visual(*args, **kwargs):
        return JsonResponse({'error': 'Funcionalidade em desenvolvimento', 'status': 501})
    
    def galeria_conceitos(*args, **kwargs):
        return JsonResponse({'error': 'Funcionalidade em desenvolvimento', 'status': 501})
    
    def download_conceito_imagem(*args, **kwargs):
        return JsonResponse({'error': 'Funcionalidade em desenvolvimento', 'status': 501})
    
    def exportar_dados_conceito(*args, **kwargs):
        return JsonResponse({'error': 'Funcionalidade em desenvolvimento', 'status': 501})
    
    def status_conceito_visual(*args, **kwargs):
        return JsonResponse({'error': 'Funcionalidade em desenvolvimento', 'status': 501})
    
    def duplicar_conceito(*args, **kwargs):
        return JsonResponse({'error': 'Funcionalidade em desenvolvimento', 'status': 501})
    
    def excluir_conceito(*args, **kwargs):
        return JsonResponse({'error': 'Funcionalidade em desenvolvimento', 'status': 501})

# Importações de modelo 3D (tentar importar, criar stubs se não existir)
try:
    from .modelo_3d import (
        gerar_modelo_3d,
        refinar_modelo_3d,
        visualizar_modelo_3d,
        viewer_interativo,
        download_modelo_3d,
        download_todos_formatos,
        exportar_dados_modelo,
        status_modelo_3d,
        atualizar_camera_modelo,
        adicionar_ponto_interesse,
        excluir_modelo,
        preview_modelo,
    )
except ImportError:
    # Views não implementadas ainda - criar stubs
    from django.http import JsonResponse
    
    def gerar_modelo_3d(*args, **kwargs):
        return JsonResponse({'error': 'Funcionalidade em desenvolvimento', 'status': 501})
    
    def refinar_modelo_3d(*args, **kwargs):
        return JsonResponse({'error': 'Funcionalidade em desenvolvimento', 'status': 501})
    
    def visualizar_modelo_3d(*args, **kwargs):
        return JsonResponse({'error': 'Funcionalidade em desenvolvimento', 'status': 501})
    
    def viewer_interativo(*args, **kwargs):
        return JsonResponse({'error': 'Funcionalidade em desenvolvimento', 'status': 501})
    
    def download_modelo_3d(*args, **kwargs):
        return JsonResponse({'error': 'Funcionalidade em desenvolvimento', 'status': 501})
    
    def download_todos_formatos(*args, **kwargs):
        return JsonResponse({'error': 'Funcionalidade em desenvolvimento', 'status': 501})
    
    def exportar_dados_modelo(*args, **kwargs):
        return JsonResponse({'error': 'Funcionalidade em desenvolvimento', 'status': 501})
    
    def status_modelo_3d(*args, **kwargs):
        return JsonResponse({'error': 'Funcionalidade em desenvolvimento', 'status': 501})
    
    def atualizar_camera_modelo(*args, **kwargs):
        return JsonResponse({'error': 'Funcionalidade em desenvolvimento', 'status': 501})
    
    def adicionar_ponto_interesse(*args, **kwargs):
        return JsonResponse({'error': 'Funcionalidade em desenvolvimento', 'status': 501})
    
    def excluir_modelo(*args, **kwargs):
        return JsonResponse({'error': 'Funcionalidade em desenvolvimento', 'status': 501})
    
    def preview_modelo(*args, **kwargs):
        return JsonResponse({'error': 'Funcionalidade em desenvolvimento', 'status': 501})

# Importações de mensagens (tentar importar, criar stubs se não existir)
try:
    from .mensagens import mensagens, nova_mensagem, mensagens_projeto
except ImportError:
    # Views não implementadas ainda - criar stubs
    from django.http import JsonResponse
    
    def mensagens(*args, **kwargs):
        return JsonResponse({'error': 'Funcionalidade em desenvolvimento', 'status': 501})
    
    def nova_mensagem(*args, **kwargs):
        return JsonResponse({'error': 'Funcionalidade em desenvolvimento', 'status': 501})
    
    def mensagens_projeto(*args, **kwargs):
        return JsonResponse({'error': 'Funcionalidade em desenvolvimento', 'status': 501})

# Lista de todas as views exportadas (ATUALIZADA)
__all__ = [
    # Base
    'ProjetistaLoginView', 'home', 'dashboard',
    
    # Projetos
    'projeto_list', 'projeto_detail', 'ver_briefing',
    
    # Planta Baixa (CrewAI) - PRINCIPAIS MUDANÇAS
    'gerar_planta_baixa', 'refinar_planta_baixa', 'visualizar_planta_baixa',
    'download_planta_svg', 'comparar_plantas', 'validar_crew_status',  # ← MUDANÇA
    'exportar_dados_planta', 'testar_crewai_config', 'debug_crew_info',  # ← NOVOS
    'obter_logs_execucao','status_execucao', 
    
    # Conceito Visual
    'gerar_conceito_visual', 'refinar_conceito_visual', 'visualizar_conceito_visual',
    'galeria_conceitos', 'download_conceito_imagem', 'exportar_dados_conceito',
    'status_conceito_visual', 'duplicar_conceito', 'excluir_conceito',
    
    # Modelo 3D
    'gerar_modelo_3d', 'refinar_modelo_3d', 'visualizar_modelo_3d',
    'viewer_interativo', 'download_modelo_3d', 'download_todos_formatos',
    'exportar_dados_modelo', 'status_modelo_3d', 'atualizar_camera_modelo',
    'adicionar_ponto_interesse', 'excluir_modelo', 'preview_modelo',
    
    # Mensagens
    'mensagens', 'nova_mensagem', 'mensagens_projeto',
]