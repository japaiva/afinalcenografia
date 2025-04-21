# projetos/models/__init__.py

from projetos.models.projeto import (
    Projeto,
    ProjetoPlanta,
    ProjetoReferencia,
    ArquivoProjeto
)

from projetos.models.briefing import (
    Briefing,
    BriefingArquivoReferencia,
    BriefingValidacao,
    BriefingConversation
)

from projetos.models.mensagem import (
    Mensagem,
    AnexoMensagem
)

from projetos.models.marco import (
    ProjetoMarco
)

__all__ = [
    'Projeto',
    'ProjetoPlanta',
    'ProjetoReferencia',
    'Briefing',
    'BriefingArquivoReferencia',
    'BriefingValidacao',
    'BriefingConversation',
    'Mensagem',
    'AnexoMensagem',
    'ArquivoProjeto',
    'ProjetoMarco',
]