# projetos/forms/__init__.py
from projetos.forms.projeto import ProjetoForm  # 👈 novo import
from projetos.forms.briefing import (
    BriefingForm, BriefingEtapa1Form, BriefingEtapa2Form, 
    BriefingEtapa3Form, BriefingEtapa4Form, 
    BriefingArquivoReferenciaForm, BriefingMensagemForm
)

__all__ = [
    'ProjetoForm',  # 👈 adicionar aqui também
    'BriefingForm', 
    'BriefingEtapa1Form', 
    'BriefingEtapa2Form', 
    'BriefingEtapa3Form', 
    'BriefingEtapa4Form', 
    'BriefingArquivoReferenciaForm', 
    'BriefingMensagemForm'
]
