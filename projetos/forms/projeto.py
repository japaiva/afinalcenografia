#forms/projeto.py

from django import forms
from django.forms.widgets import Input
from projetos.models import Projeto, ProjetoPlanta, ProjetoReferencia
from core.models import Feira


# Widget personalizado que permite múltiplos arquivos
class CustomMultipleFileInput(Input):
    input_type = 'file'

    def __init__(self, attrs=None):
        if attrs is None:
            attrs = {}
        attrs['multiple'] = True
        super().__init__(attrs)

    def value_from_datadict(self, data, files, name):
        if hasattr(files, 'getlist'):
            return files.getlist(name)
        return files.get(name)

    def value_omitted_from_data(self, data, files, name):
        return name not in files


class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs["widget"] = CustomMultipleFileInput(attrs={'class': 'form-control'})
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            result = [single_file_clean(d, initial) for d in data]
        else:
            result = single_file_clean(data, initial)
        return result

class ProjetoForm(forms.ModelForm):
    class Meta:
        model = Projeto
        fields = [
            'nome', 'descricao', 'orcamento', 'status',
            # O campo feira agora é mostrado diretamente no formulário
            'feira'
        ]
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'descricao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'orcamento': forms.TextInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'feira': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filtrar apenas feiras ativas para o campo feira
        self.fields['feira'].queryset = Feira.objects.filter(ativa=True).order_by('-data_inicio')
        self.fields['nome'].required = True
        self.fields['orcamento'].required = True


    def save(self, commit=True):
        projeto = super().save(commit=commit)

        if commit and self.cleaned_data.get('arquivos_referencia'):
            for arquivo in self.cleaned_data['arquivos_referencia']:
                ProjetoReferencia.objects.create(
                    projeto=projeto,
                    nome=arquivo.name,
                    arquivo=arquivo,
                    tamanho=arquivo.size
                )

        return projeto
    
# projetos/forms.py

from django import forms
from projetos.models import ProjetoPlanta

class ProjetoPlantaForm(forms.ModelForm):
    class Meta:
        model = ProjetoPlanta
        fields = ['nome', 'arquivo', 'tipo', 'observacoes']

from django import forms
from projetos.models import ProjetoReferencia

class ProjetoReferenciaForm(forms.ModelForm):
    class Meta:
        model = ProjetoReferencia
        fields = ['nome', 'arquivo', 'tipo', 'observacoes']
        widgets = {
            'observacoes': forms.Textarea(attrs={'rows': 3}),
        }