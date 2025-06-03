# projetos/forms/projeto.py - Atualização completa

from django import forms
from django.forms.widgets import Input
from projetos.models import Projeto, ProjetoReferencia
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
    # NOVO CAMPO para editar descrição da empresa no contexto do projeto
    descricao_empresa = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        required=False,
        label="Descrição da Empresa",
        help_text="Esta descrição pode ser ajustada para o contexto específico deste projeto"
    )
    
    class Meta:
        model = Projeto
        fields = [
            'tipo_projeto', 'nome', 'descricao', 'orcamento', 'feira'
        ]
        widgets = {
            'tipo_projeto': forms.Select(attrs={'class': 'form-select', 'id': 'id_tipo_projeto'}),
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'descricao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'orcamento': forms.TextInput(attrs={'class': 'form-control'}),
            'feira': forms.Select(attrs={'class': 'form-select', 'id': 'id_feira'}),
        }
        labels = {
            'descricao': 'Objetivo do Projeto',
            'tipo_projeto': 'Tipo de Projeto',
            'nome': 'Nome do Projeto',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['feira'].queryset = Feira.objects.filter(ativa=True).order_by('-data_inicio')
        self.fields['feira'].required = False
        self.fields['orcamento'].required = True
        self.fields['descricao'].required = True

        # Pré-preencher com a descrição padrão da empresa
        if self.instance and self.instance.empresa and self.instance.empresa.descricao:
            self.fields['descricao_empresa'].initial = self.instance.empresa.descricao

        # Lógica condicional para campo nome
        tipo_projeto = self.initial.get('tipo_projeto') or self.data.get('tipo_projeto')
        feira = self.initial.get('feira') or self.data.get('feira')

        if tipo_projeto == 'feira_negocios':
            self.fields['nome'].required = False
            self.fields['nome'].help_text = 'Digite o nome da Feira (ainda sem manual).'
        else:
            self.fields['nome'].required = True
            self.fields['nome'].help_text = ''

    def clean(self):
        cleaned_data = super().clean()
        tipo_projeto = cleaned_data.get('tipo_projeto')
        feira = cleaned_data.get('feira')
        nome = cleaned_data.get('nome')

        if tipo_projeto == 'feira_negocios':
            if not feira and not nome:
                self.add_error('nome', 'Como não foi selecionada uma feira, você precisa fornecer um nome para o projeto.')
        elif not nome:
            self.add_error('nome', 'Este campo é obrigatório para projetos que não são do tipo Feira de Negócios.')

        return cleaned_data

    def save(self, commit=True):
        projeto = super().save(commit=False)

        if not projeto.pk:
            projeto.definir_status_inicial()

        if projeto.tipo_projeto == 'feira_negocios' and projeto.feira:
            projeto.nome = projeto.feira.nome

        # NOVA LÓGICA: Atualizar a descrição da empresa se foi modificada
        descricao_empresa = self.cleaned_data.get('descricao_empresa')
        if descricao_empresa and projeto.empresa:
            projeto.empresa.descricao = descricao_empresa
            projeto.empresa.save()

        if commit:
            projeto.save()
            if hasattr(self, 'cleaned_data') and self.cleaned_data.get('arquivos_referencia'):
                for arquivo in self.cleaned_data['arquivos_referencia']:
                    ProjetoReferencia.objects.create(
                        projeto=projeto,
                        nome=arquivo.name,
                        arquivo=arquivo,
                        tamanho=arquivo.size
                    )

        return projeto