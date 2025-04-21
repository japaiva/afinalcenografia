# projetos/forms/__init__.py
from projetos.forms.projeto import ProjetoForm,  ProjetoPlantaForm, ProjetoReferenciaForm
from projetos.forms.briefing import (
    BriefingForm, BriefingEtapa1Form, BriefingEtapa2Form, 
    BriefingEtapa3Form, BriefingEtapa4Form, 
    BriefingArquivoReferenciaForm, BriefingMensagemForm, 
   
)

__all__ = [
    'ProjetoForm',  
    'BriefingForm', 
    'BriefingEtapa1Form', 
    'BriefingEtapa2Form', 
    'BriefingEtapa3Form', 
    'BriefingEtapa4Form', 
    'BriefingArquivoReferenciaForm', 
    'BriefingMensagemForm',
    'ProjetoPlantaForm',
    'ProjetoReferenciaForm'
]
