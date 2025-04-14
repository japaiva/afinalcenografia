# core/services/rag_service.py
import logging
from typing import List, Dict, Any, Optional

from core.models import Feira, FeiraManualQA, ParametroIndexacao
from django.conf import settings

logger = logging.getLogger(__name__)

class RAGService:
    """
    Serviço principal para integrar os pares QA com o sistema RAG existente.
    Coordena os diversos serviços especializados.
    """
    
    def __init__(self, agent_name='Assistente RAG de Feiras'):
        """
        Inicializa o serviço RAG.
        
        Args:
            agent_name: Nome do agente configurado a ser utilizado.
        """
        logger.info(f"Inicializando RAGService com agente '{agent_name}'")
        self.agent_name = agent_name
        
        # Inicializar serviços especializados
        self._initialize_services()
    
    def _initialize_services(self):
        """Inicializa os serviços especializados utilizados pelo RAGService."""
        try:
            # Importar dinamicamente para evitar dependências circulares
            from core.services.rag.embedding_service import EmbeddingService
            from core.services.rag.qa_service import QAService
            from core.services.rag.retrieval_service import RetrievalService
            from core.services.rag.vector_db_service import VectorDBService
            
            # Inicializar serviços na ordem correta
            self.embedding_service = EmbeddingService(self.agent_name)
            logger.info(f"✓ EmbeddingService inicializado")
            
            self.vector_db_service = VectorDBService()
            logger.info(f"✓ VectorDBService inicializado")
            
            self.qa_service = QAService(self.embedding_service)
            logger.info(f"✓ QAService inicializado")
            
            self.retrieval_service = RetrievalService(self.embedding_service, self.agent_name)
            logger.info(f"✓ RetrievalService inicializado")
            
        except Exception as e:
            logger.error(f"Erro ao inicializar serviços: {str(e)}")
            raise
    
    def atualizar_embeddings_feira(self, feira_id: int) -> Dict[str, Any]:
        """
        Atualiza os embeddings dos QA de uma feira.
        
        Args:
            feira_id: ID da feira.
            
        Returns:
            Dicionário com os resultados da atualização.
        """
        logger.info(f"Delegando atualização de embeddings para QAService (feira ID {feira_id})")
        return self.qa_service.atualizar_embeddings_feira(feira_id)
    
    def pesquisar_qa(self, query: str, feira_id: Optional[int] = None, top_k: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Pesquisa QA relevantes para uma consulta.
        
        Args:
            query: A consulta do usuário.
            feira_id: ID opcional da feira para restringir a busca.
            top_k: Número máximo de resultados.
            
        Returns:
            Lista de pares QA relevantes com scores.
        """
        logger.info(f"Delegando pesquisa QA para RetrievalService (query: '{query}', feira ID: {feira_id})")
        return self.retrieval_service.pesquisar_qa(query, feira_id, top_k)
    
    def gerar_resposta_rag(self, query: str, feira_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Gera uma resposta usando RAG com base na consulta e nos QA disponíveis.
        
        Args:
            query: A consulta do usuário.
            feira_id: ID opcional da feira para restringir a busca.
            
        Returns:
            Dicionário com a resposta gerada e os contextos utilizados.
        """
        logger.info(f"Delegando geração de resposta RAG para RetrievalService (query: '{query}', feira ID: {feira_id})")
        return self.retrieval_service.gerar_resposta_rag(query, feira_id)


def integrar_feira_com_briefing(briefing_id, feira_id):
    """
    Integra os QA de uma feira com um briefing específico.
    
    Args:
        briefing_id: ID do briefing.
        feira_id: ID da feira.
        
    Returns:
        Dicionário com os resultados da integração.
    """
    import logging
    from projetos.models.briefing import Briefing, BriefingConversation
    from core.models import Feira
    
    logger = logging.getLogger(__name__)
    
    try:
        logger.info(f"Iniciando integração da feira {feira_id} com o briefing {briefing_id}")
        
        # Buscar briefing e feira
        try:
            briefing = Briefing.objects.get(pk=briefing_id)
            logger.info(f"✓ Briefing encontrado: ID {briefing_id}")
        except Briefing.DoesNotExist:
            logger.error(f"Briefing com ID {briefing_id} não encontrado.")
            return {
                'status': 'error',
                'message': f'Briefing com ID {briefing_id} não encontrado.'
            }
            
        try:
            feira = Feira.objects.get(pk=feira_id)
            logger.info(f"✓ Feira encontrada: '{feira.nome}' (ID: {feira_id})")
        except Feira.DoesNotExist:
            logger.error(f"Feira com ID {feira_id} não encontrada.")
            return {
                'status': 'error',
                'message': f'Feira com ID {feira_id} não encontrada.'
            }
        
        # Vincular feira ao briefing
        briefing.feira = feira
        briefing.save()
        logger.info(f"✓ Feira '{feira.nome}' vinculada ao briefing {briefing_id}")
        
        # Nota: não estamos chamando o método de atualizar embeddings para evitar loops
        # A atualização de embeddings pode ser feita manualmente depois
        
        # Criar mensagem no histórico de conversas do briefing
        BriefingConversation.objects.create(
            briefing=briefing,
            mensagem=f"Manual da feira '{feira.nome}' integrado ao briefing. Agora você pode fazer perguntas específicas sobre esta feira.",
            origem='sistema',
            etapa=briefing.etapa_atual
        )
        logger.info(f"✓ Mensagem de integração adicionada ao histórico de conversas do briefing")
        
        return {
            'status': 'success',
            'message': f"Feira '{feira.nome}' integrada ao briefing com sucesso."
        }
        
    except Exception as e:
        logger.error(f"Erro ao integrar feira com briefing: {str(e)}")
        return {
            'status': 'error',
            'message': str(e)
        }