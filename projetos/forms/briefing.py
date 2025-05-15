# projetos/forms/briefing.py

from django import forms
from projetos.models.briefing import (
    Briefing, BriefingArquivoReferencia, 
    AreaExposicao, SalaReuniao, Copa, Deposito
)

class BriefingEtapa1Form(forms.ModelForm):
    """Formulário para a primeira etapa do briefing: Evento - Datas e Localização"""
    
    class Meta:
        model = Briefing
        fields = [
            'endereco_estande', 'mapa_estande',
        ]
        widgets = {
            'endereco_estande': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Rua B, Estande 42'}),
            'mapa_estande': forms.FileInput(attrs={'class': 'form-control'}),
        }
class BriefingEtapa2Form(forms.ModelForm):
    """
    Formulário para a segunda etapa do briefing (ESTANDE - Características Físicas).
    """
    class Meta:
        model = Briefing
        fields = [
            'medida_frente', 'medida_fundo', 'medida_lateral_esquerda', 'medida_lateral_direita',
            'area_estande', 'tipo_stand', 'estilo_estande', 'material',
            'piso_elevado', 'tipo_testeira',
            'tipo_venda', 'tipo_ativacao', 'objetivo_estande'
        ]
        widgets = {
            'medida_frente': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01'
            }),
            'medida_fundo': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01'
            }),
            'medida_lateral_esquerda': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01'
            }),
            'medida_lateral_direita': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01'
            }),
            'area_estande': forms.NumberInput(attrs={
                'class': 'form-control',
                'readonly': True
            }),
            'estilo_estande': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Moderno, Clean, Futurista, Rústico'
            }),
            'tipo_stand': forms.RadioSelect(attrs={'class': 'form-check-input tipo-stand-radio'}),
            'material': forms.Select(attrs={'class': 'form-select'}),
            'piso_elevado': forms.Select(attrs={'class': 'form-select'}),
            'tipo_testeira': forms.Select(attrs={'class': 'form-select'}),
            'tipo_venda': forms.Select(attrs={'class': 'form-select'}),
            'tipo_ativacao': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Área instagramável, Glorify, Games, etc.'
            }),
            'objetivo_estande': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Lançamento da coleção'
            }),
        }


class AreaExposicaoForm(forms.ModelForm):
    """Formulário para áreas de exposição do estande"""
    class Meta:
        model = AreaExposicao
        exclude = ['briefing']
        widgets = {
            'tem_lounge': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'tem_vitrine_exposicao': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'tem_balcao_recepcao': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'tem_mesas_atendimento': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'tem_balcao_cafe': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'tem_balcao_vitrine': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'tem_caixa_vendas': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'equipamentos': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'LED, TVs, etc.'
            }),
            'observacoes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': ''
            }),
            'metragem': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '',
                'step': '0.01'
            }),
        }


class SalaReuniaoForm(forms.ModelForm):
    """Formulário para salas de reunião do estande"""
    class Meta:
        model = SalaReuniao
        exclude = ['briefing']
        widgets = {
            'capacidade': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': ''
            }),
            'equipamentos': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Prateleira, TV, armário, estilo mesa, etc.'
            }),
            'metragem': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '',
                'step': '0.01'
            }),
        }


class CopaForm(forms.ModelForm):
    """Formulário para copas do estande"""
    class Meta:
        model = Copa
        exclude = ['briefing']
        widgets = {
            'equipamentos': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Pia, geladeira, bancada, prateleiras, etc.'
            }),
            'metragem': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '',
                'step': '0.01'
            }),
        }


class DepositoForm(forms.ModelForm):
    """Formulário para depósitos do estande"""
    class Meta:
        model = Deposito
        exclude = ['briefing']
        widgets = {
            'equipamentos': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Prateleiras, etc.'
            }),
            'metragem': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '',
                'step': '0.01'
            }),
        }


class BriefingEtapa3Form(forms.Form):
    """
    Formulário para a terceira etapa do briefing (ÁREAS DO ESTANDE - Divisões Funcionais).
    Este formulário gerencia várias sub-áreas do estande através de JavaScript e formsets.
    """
    # Checkboxes para indicar a presença de cada área
    tem_area_exposicao = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    tem_sala_reuniao = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    tem_copa = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    tem_deposito = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )


class BriefingEtapa4Form(forms.ModelForm):
    """
    Formulário para a quarta etapa do briefing (DADOS COMPLEMENTARES - Referências Visuais).
    """
    class Meta:
        model = Briefing
        fields = ['referencias_dados', 'logotipo', 'campanha_dados']
        widgets = {
            'referencias_dados': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': ''
            }),
            'logotipo': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': ''
            }),
            'campanha_dados': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': ''
            }),
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
            'observacoes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Observações sobre este arquivo'
            }),
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