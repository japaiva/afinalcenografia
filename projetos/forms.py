from django import forms
from django.forms.widgets import Input
from projetos.models import Projeto, ArquivoReferencia

# Widget personalizado que herda diretamente de Input em vez de FileInput
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
    arquivos_referencia = MultipleFileField(
        required=False,
        help_text="Selecione um ou mais arquivos de referência (opcional)."
    )
    
    class Meta:
        model = Projeto
        fields = [
            'nome', 'descricao', 'status', 'data_inicio', 'prazo_entrega',
            'orcamento', 'progresso', 'requisitos'
        ]
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'descricao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'data_inicio': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'prazo_entrega': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'orcamento': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'progresso': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 100}),
            'requisitos': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['nome'].required = True
        self.fields['status'].required = True
    
    def save(self, commit=True):
        projeto = super().save(commit=commit)
        
        if commit and self.cleaned_data.get('arquivos_referencia'):
            # Processar arquivos de referência
            for arquivo in self.cleaned_data['arquivos_referencia']:
                ArquivoReferencia.objects.create(
                    projeto=projeto,
                    nome=arquivo.name,
                    arquivo=arquivo,
                    tamanho=arquivo.size
                )
        
        return projeto