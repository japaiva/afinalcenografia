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
            'nome', 'descricao', 'orcamento', 'status', 'feira'
        ]
        widgets = {
            'nome': forms.HiddenInput(),  # Campo oculto, será preenchido via JavaScript
            'descricao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'orcamento': forms.TextInput(attrs={'class': 'form-control'}),
            'status': forms.HiddenInput(),  # Campo oculto, será preenchido automaticamente
            'feira': forms.Select(attrs={'class': 'form-select'}),
        }
        labels = {
            'descricao': 'Objetivo',  # Altera o label de Descrição para Objetivo
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filtrar apenas feiras ativas para o campo feira
        self.fields['feira'].queryset = Feira.objects.filter(ativa=True).order_by('-data_inicio')
        self.fields['feira'].required = True
        self.fields['orcamento'].required = True
        self.fields['descricao'].required = True  # Tornar objetivo obrigatório

        # Se for uma instância existente (edição), deixar o campo status apenas leitura
        instance = kwargs.get('instance')
        if instance and instance.pk:
            self.fields['status'].widget.attrs['readonly'] = True

    def save(self, commit=True):
        projeto = super().save(commit=False)
        
        # Para novos projetos, define o status como briefing_pendente
        if not projeto.pk:
            projeto.status = 'briefing_pendente'
            
        if commit:
            projeto.save()
            
            # Salva os arquivos de referência, se houver
            if hasattr(self, 'cleaned_data') and self.cleaned_data.get('arquivos_referencia'):
                for arquivo in self.cleaned_data['arquivos_referencia']:
                    ProjetoReferencia.objects.create(
                        projeto=projeto,
                        nome=arquivo.name,
                        arquivo=arquivo,
                        tamanho=arquivo.size
                    )

        return projeto