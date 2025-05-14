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
            'tipo_projeto', 'nome', 'descricao', 'orcamento', 'status', 'feira'
        ]
        widgets = {
            'tipo_projeto': forms.Select(attrs={'class': 'form-select', 'id': 'id_tipo_projeto'}),
            'nome': forms.TextInput(attrs={'class': 'form-control'}),  # Agora é um TextInput comum
            'descricao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'orcamento': forms.TextInput(attrs={'class': 'form-control'}),
            'status': forms.HiddenInput(),  # Campo oculto, será preenchido automaticamente
            'feira': forms.Select(attrs={'class': 'form-select', 'id': 'id_feira'}),
        }
        labels = {
            'descricao': 'Objetivo',  # Altera o label de Descrição para Objetivo
            'tipo_projeto': 'Tipo de Projeto',
            'nome': 'Nome do Projeto',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filtrar apenas feiras ativas para o campo feira
        self.fields['feira'].queryset = Feira.objects.filter(ativa=True).order_by('-data_inicio')
        self.fields['feira'].required = False  # Feira não é mais obrigatória
        self.fields['orcamento'].required = True
        self.fields['descricao'].required = True  # Tornar objetivo obrigatório
        self.fields['nome'].required = True
        
        # Definir valor padrão para tipo_projeto
        if not self.instance.pk:
            self.fields['tipo_projeto'].initial = 'feira_negocios'

        # Se for uma instância existente (edição), deixar o campo status apenas leitura
        instance = kwargs.get('instance')
        if instance and instance.pk:
            self.fields['status'].widget.attrs['readonly'] = True

    def clean(self):
        cleaned_data = super().clean()
        tipo_projeto = cleaned_data.get('tipo_projeto')
        feira = cleaned_data.get('feira')
        
        # Se for feira de negócios, é obrigatório ter uma feira selecionada
        if tipo_projeto == 'feira_negocios' and not feira:
            self.add_error('feira', 'Este campo é obrigatório para projetos do tipo Feira de Negócios.')
            
        return cleaned_data
    
    def save(self, commit=True):
        projeto = super().save(commit=False)
        
        # Para novos projetos, define o status como briefing_pendente
        if not projeto.pk:
            projeto.status = 'briefing_pendente'
            
        # Se for do tipo feira_negocios e tiver feira selecionada, preenche o nome com o nome da feira
        if projeto.tipo_projeto == 'feira_negocios' and projeto.feira:
            projeto.nome = projeto.feira.nome
            
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