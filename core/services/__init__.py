#core/services/__init__.py
from .qa_generator import QAGenerator, process_all_chunks_for_feira
from .rag_service import RAGService, integrar_feira_com_briefing
from .extracao_service import ExtracaoService  # Adicionar esta linha

__all__ = [
    'QAGenerator',
    'process_all_chunks_for_feira',
    'RAGService',
    'integrar_feira_com_briefing',
    'ExtracaoService'  # Adicionar esta linha
]