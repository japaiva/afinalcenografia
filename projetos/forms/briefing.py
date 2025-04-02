from django import forms
from projetos.models.briefing import Briefing, BriefingArquivoReferencia

class BriefingForm(forms.ModelForm):
    """
    Formulário para o briefing completo.
    """
    class Meta:
        model = Briefing
        exclude = ['projeto', 'status', 'etapa_atual', 'progresso', 'validado_por_ia', 'created_at', 'updated_at']
        widgets = {
            'categoria': forms.Select(attrs={'class': 'form-select'}),
            'descricao_detalhada': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'objetivos': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'dimensoes': forms.NumberInput(attrs={'class': 'form-control'}),
            'altura': forms.NumberInput(attrs={'class': 'form-control'}),
            'paleta_cores': forms.TextInput(attrs={'class': 'form-control'}),
            'materiais_preferidos': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'acabamentos': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'iluminacao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'eletrica': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'mobiliario': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class BriefingEtapa1Form(forms.ModelForm):
    """
    Formulário para a primeira etapa do briefing (Informações Básicas).
    """
    class Meta:
        model = Briefing
        fields = ['categoria', 'descricao_detalhada', 'objetivos']
        widgets = {
            'categoria': forms.Select(attrs={
                'class': 'form-select',
                'choices': (
                    ('', 'Selecione...'),
                    ('evento_corporativo', 'Evento Corporativo'),
                    ('evento_social', 'Evento Social'),
                    ('televisao', 'Televisão'),
                    ('varejo', 'Varejo'),
                    ('teatro', 'Teatro'),
                    ('outros', 'Outros'),
                )
            }),
            'descricao_detalhada': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'objetivos': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class BriefingEtapa2Form(forms.ModelForm):
    """
    Formulário para a segunda etapa do briefing (Detalhes Técnicos).
    """
    class Meta:
        model = Briefing
        fields = ['dimensoes', 'altura', 'paleta_cores']
        widgets = {
            'dimensoes': forms.NumberInput(attrs={'class': 'form-control'}),
            'altura': forms.NumberInput(attrs={'class': 'form-control'}),
            'paleta_cores': forms.TextInput(attrs={'class': 'form-control'}),
        }


class BriefingEtapa3Form(forms.ModelForm):
    """
    Formulário para a terceira etapa do briefing (Materiais e Acabamentos).
    """
    class Meta:
        model = Briefing
        fields = ['materiais_preferidos', 'acabamentos']
        widgets = {
            'materiais_preferidos': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'acabamentos': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class BriefingEtapa4Form(forms.ModelForm):
    """
    Formulário para a quarta etapa do briefing (Requisitos Técnicos).
    """
    class Meta:
        model = Briefing
        fields = ['iluminacao', 'eletrica', 'mobiliario']
        widgets = {
            'iluminacao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'eletrica': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'mobiliario': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class BriefingArquivoReferenciaForm(forms.ModelForm):
    """
    Formulário para upload de arquivos de referência.
    """
    class Meta:
        model = BriefingArquivoReferencia
        fields = ['arquivo', 'tipo', 'observacoes']
        widgets = {
            'arquivo': forms.FileInput(attrs={'class': 'form-control'}),
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class BriefingMensagemForm(forms.Form):
    """
    Formulário para envio de mensagens para a IA.
    """
    mensagem = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Faça uma pergunta ao assistente...'
        }),
        required=True
    )