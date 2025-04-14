# core/services/rag/__init__.py
"""
Pacote de serviços para o sistema RAG (Retrieval-Augmented Generation).

Este pacote contém os serviços especializados para gerenciamento de
embeddings, pares Q&A, busca semântica e integração com banco de dados vetorial.
"""

from core.services.rag.embedding_service import EmbeddingService
from core.services.rag.qa_service import QAService
from core.services.rag.retrieval_service import RetrievalService
from core.services.rag.vector_db_service import VectorDBService

__all__ = [
    'EmbeddingService',
    'QAService',
    'RetrievalService', 
    'VectorDBService'
]