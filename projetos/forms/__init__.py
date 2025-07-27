# projetos/forms/__init__.py
from projetos.forms.projeto import ProjetoForm
from projetos.forms.briefing import (
    BriefingEtapa1Form, BriefingEtapa2Form, 
    BriefingEtapa3Form, BriefingEtapa4Form, 
    BriefingArquivoReferenciaForm, BriefingMensagemForm, 
)

__all__ = [
    'ProjetoForm',  
    'BriefingEtapa1Form', 
    'BriefingEtapa2Form', 
    'BriefingEtapa3Form', 
    'BriefingEtapa4Form', 
    'BriefingArquivoReferenciaForm', 
    'BriefingMensagemForm',
]
