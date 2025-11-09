# projetos/forms/briefing.py

from django import forms
from projetos.models.briefing import (
    Briefing, BriefingArquivoReferencia, 
    AreaExposicao, SalaReuniao, Copa, Deposito, Palco, Workshop
)
class BriefingEtapa1Form(forms.ModelForm):
    """Formulário para a primeira etapa do briefing: Evento - Datas e Localização"""
    
    class Meta:
        model = Briefing
        fields = [
            'endereco_estande',  
            # Campos adicionais para projetos tipo "outros"
            'nome_evento', 
            'local_evento', 
            'organizador_evento', 
            'data_horario_evento', 
            'periodo_montagem_evento', 
            'periodo_desmontagem_evento'
        ]
        widgets = {
            'endereco_estande': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Rua B, Estande 42'}),
            'nome_evento': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome do evento ou feira'}),
            'local_evento': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Local completo, incluindo cidade/estado'}),
            'organizador_evento': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Empresa organizadora'}),
            'data_horario_evento': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: 25/06 a 27/06/2024 - 10h às 19h'}),
            'periodo_montagem_evento': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: 22/06 a 24/06 - 8h às 22h'}),
            'periodo_desmontagem_evento': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: 27/06 - 22h às 06h (28/06)'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Tornar endereco_estande obrigatório
        self.fields['endereco_estande'].required = True

        # Verificar se o projeto é do tipo "outros" para mostrar campos adicionais
        if hasattr(self.instance, 'projeto') and self.instance.projeto and self.instance.projeto.tipo_projeto == 'outros' and not self.instance.feira:
            # Campos serão mostrados
            pass
        else:
            # Ocultar campos adicionais para projetos com feira
            for field_name in ['nome_evento', 'local_evento', 'organizador_evento',
                               'data_horario_evento', 'periodo_montagem_evento', 'periodo_desmontagem_evento']:
                self.fields[field_name].widget = forms.HiddenInput()
                self.fields[field_name].required = False
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Tornar o campo tipo_stand não obrigatório
        self.fields['tipo_stand'].required = False
        
        # Se a instância estiver associada a um projeto do tipo "outros", usar widget escondido
        if hasattr(self.instance, 'projeto') and self.instance.projeto and self.instance.projeto.tipo_projeto == 'outros':
            # Em vez de remover o campo, vamos torná-lo um campo escondido com valor padrão
            self.fields['tipo_stand'].widget = forms.HiddenInput()
            # Definir valor inicial para o campo
            self.fields['tipo_stand'].initial = 'esquina'
            
    def clean(self):
        cleaned_data = super().clean()
        
        # Se o campo tipo_stand não foi preenchido, usar o valor padrão
        if 'tipo_stand' not in cleaned_data or not cleaned_data.get('tipo_stand'):
            cleaned_data['tipo_stand'] = 'esquina'  # Valor padrão do modelo
            
        return cleaned_data

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


# projetos/forms/briefing.py - Modificar o SalaReuniaoForm

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
            # NOVO WIDGET
            'tipo_sala': forms.Select(attrs={
                'class': 'form-select'
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


# projetos/forms/briefing.py - ATUALIZAR BriefingEtapa3Form

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
    
    # NOVOS CAMPOS
    tem_palco = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    tem_workshop = forms.BooleanField(
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

# projetos/forms/briefing.py - ADICIONAR após DepositoForm

class PalcoForm(forms.ModelForm):
    """Formulário para palcos do estande"""
    class Meta:
        model = Palco
        exclude = ['briefing']
        widgets = {
            # Checkboxes para itens do palco
            'tem_elevacao_podium': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'tem_sistema_som': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'tem_microfone': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'tem_telao_tv': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'tem_iluminacao_cenica': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'tem_backdrop_cenario': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'tem_bancada_demonstracao': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'tem_espaco_plateia': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            
            # Campos tradicionais
            'equipamentos': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Detalhes adicionais sobre equipamentos específicos'
            }),
            'observacoes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Coloque aqui como você imagina o palco'
            }),
            'metragem': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '',
                'step': '0.01'
            }),
        }


class WorkshopForm(forms.ModelForm):
    """Formulário para workshops do estande"""
    class Meta:
        model = Workshop
        exclude = ['briefing']
        widgets = {
            # Checkboxes para itens do workshop
            'tem_bancada_trabalho': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'tem_mesas_participantes': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'tem_cadeiras_bancos': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'tem_quadro_flipchart': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'tem_projetor_tv': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'tem_pia_bancada_molhada': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'tem_armario_materiais': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'tem_pontos_eletricos_extras': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            
            # Campos tradicionais
            'equipamentos': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Detalhes adicionais sobre equipamentos específicos'
            }),
            'observacoes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Coloque aqui como você imagina o workshop'
            }),
            'metragem': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '',
                'step': '0.01'
            }),
        }