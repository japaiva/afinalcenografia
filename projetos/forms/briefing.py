# forms/briefing.py

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
    Formulário para a primeira etapa do briefing (EVENTO).
    """
    class Meta:
        model = Briefing
        fields = [
            'local_evento', 'data_feira_inicio', 'data_feira_fim', 'horario_feira',
            'data_montagem_inicio', 'data_montagem_fim', 
            'data_desmontagem_inicio', 'data_desmontagem_fim',
            'endereco_estande'
        ]
        widgets = {
            'local_evento': forms.TextInput(attrs={'class': 'form-control'}),
            'data_feira_inicio': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'data_feira_fim': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'horario_feira': forms.TextInput(attrs={'class': 'form-control'}),
            'data_montagem_inicio': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'data_montagem_fim': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'data_desmontagem_inicio': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'data_desmontagem_fim': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'endereco_estande': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class BriefingEtapa2Form(forms.ModelForm):
    """
    Formulário para a segunda etapa do briefing (ESTANDE).
    """
    class Meta:
        model = Briefing
        fields = [
            'area_estande', 'estilo_estande', 'cores', 'material',
            'piso_elevado', 'tipo_testeira', 'havera_venda', 
            'havera_ativacao', 'observacoes_estande'
        ]
        widgets = {
            'area_estande': forms.NumberInput(attrs={'class': 'form-control'}),
            'estilo_estande': forms.TextInput(attrs={'class': 'form-control'}),
            'cores': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'material': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'piso_elevado': forms.Select(attrs={'class': 'form-select'}),
            'tipo_testeira': forms.Select(attrs={'class': 'form-select'}),
            'havera_venda': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'havera_ativacao': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'observacoes_estande': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class BriefingEtapa3Form(forms.ModelForm):
    """
    Formulário para a terceira etapa do briefing (ÁREAS DO ESTANDE).
    """
    class Meta:
        model = Briefing
        fields = [
            # Área Aberta
            'area_aberta_tamanho', 'tem_mesas_atendimento', 'qtd_mesas_atendimento',
            'tem_lounge', 'tem_balcao_cafe', 'tem_vitrine', 'tem_balcao_vitrine',
            'tem_balcao_recepcao', 'tem_caixa', 'equipamentos',
            # Sala de Reunião
            'tem_sala_reuniao', 'sala_reuniao_capacidade', 'sala_reuniao_equipamentos',
            'sala_reuniao_tamanho',
            # Copa
            'tem_copa', 'copa_equipamentos', 'copa_tamanho',
            # Depósito
            'tem_deposito', 'deposito_equipamentos', 'deposito_tamanho',
        ]
        widgets = {
            # Área Aberta
            'area_aberta_tamanho': forms.NumberInput(attrs={'class': 'form-control'}),
            'tem_mesas_atendimento': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'qtd_mesas_atendimento': forms.NumberInput(attrs={'class': 'form-control'}),
            'tem_lounge': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'tem_balcao_cafe': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'tem_vitrine': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'tem_balcao_vitrine': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'tem_balcao_recepcao': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'tem_caixa': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'equipamentos': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            
            # Sala de Reunião
            'tem_sala_reuniao': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'sala_reuniao_capacidade': forms.NumberInput(attrs={'class': 'form-control'}),
            'sala_reuniao_equipamentos': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'sala_reuniao_tamanho': forms.NumberInput(attrs={'class': 'form-control'}),
            
            # Copa
            'tem_copa': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'copa_equipamentos': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'copa_tamanho': forms.NumberInput(attrs={'class': 'form-control'}),
            
            # Depósito
            'tem_deposito': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'deposito_equipamentos': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'deposito_tamanho': forms.NumberInput(attrs={'class': 'form-control'}),
        }


class BriefingEtapa4Form(forms.ModelForm):
    """
    Formulário para a quarta etapa do briefing (DADOS COMPLEMENTARES).
    """
    class Meta:
        model = Briefing
        fields = ['referencias_dados', 'logotipo', 'campanha_dados']
        widgets = {
            'referencias_dados': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'logotipo': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'campanha_dados': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
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