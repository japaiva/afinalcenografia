# projetista/forms.py

from django import forms
from projetista.models import ConceitoVisual, ImagemConceitoVisual

class ConceitoVisualForm(forms.ModelForm):
    """Formulário para manipulação do conceito visual (Etapa 1)"""
    class Meta:
        model = ConceitoVisual
        fields = [
            'titulo', 'descricao', 'paleta_cores', 
            'materiais_principais', 'elementos_interativos'
        ]
        widgets = {
            'titulo': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Título do conceito visual'
            }),
            'descricao': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Descrição detalhada do conceito'
            }),
            'paleta_cores': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Paleta de cores principais'
            }),
            'materiais_principais': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Materiais e acabamentos principais'
            }),
            'elementos_interativos': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Descrição de como os visitantes interagirão com o espaço'
            }),
        }

class ImagemConceitoForm(forms.ModelForm):
    """Formulário para upload de imagens do conceito"""
    class Meta:
        model = ImagemConceitoVisual
        fields = ['imagem', 'descricao', 'angulo_vista']
        widgets = {
            'imagem': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/jpeg,image/png,image/webp'
            }),
            'descricao': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Descrição breve da imagem'
            }),
            'angulo_vista': forms.Select(attrs={
                'class': 'form-select'
            }),
        }

class GeracaoImagemForm(forms.Form):
    """Formulário para geração de imagem via IA"""
    instrucoes_adicionais = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Instruções adicionais para a geração da imagem (opcional)'
        }),
        required=False
    )
    
    angulo = forms.ChoiceField(
        choices=ImagemConceitoVisual.ANGULOS_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        initial='perspectiva'
    )

class ModificacaoImagemForm(forms.Form):
    """Formulário para modificar uma imagem existente"""
    instrucoes_modificacao = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'Descreva as modificações desejadas'
        }),
        required=True
    )

class ExportacaoConceitoForm(forms.Form):
    """Formulário para exportação do conceito visual"""
    FORMATO_CHOICES = [
        ('pdf', 'PDF - Relatório Completo'),
        ('images', 'ZIP - Pacote de Imagens'),
        ('pptx', 'PPTX - Apresentação para Cliente'),
    ]
    
    formato = forms.ChoiceField(
        choices=FORMATO_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        initial='pdf'
    )
    
    incluir_briefing = forms.BooleanField(
        required=False, 
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    alta_resolucao = forms.BooleanField(
        required=False, 
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )