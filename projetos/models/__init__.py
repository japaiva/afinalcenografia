from projetos.models.projeto import Projeto
from projetos.models.arquivo import ArquivoReferencia
from projetos.models.briefing import Briefing, BriefingConversation, BriefingArquivoReferencia, BriefingValidacao

# Garantir que todos os modelos estejam disponíveis através do pacote models
__all__ = [
    'Projeto',
    'ArquivoReferencia',
    'Briefing',
    'BriefingConversation',
    'BriefingArquivoReferencia',
    'BriefingValidacao',
]