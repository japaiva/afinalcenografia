# core/services/__init__.py

from .qa_generators import QAGenerator, process_all_chunks_for_feira
from .rag_service import RAGService, integrar_feira_com_briefing

__all__ = [
    'QAGenerator',
    'process_all_chunks_for_feira',
    'RAGService',
    'integrar_feira_com_briefing'
]