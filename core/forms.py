from django import forms
from core.models import Usuario, Parametro, Empresa, Feira, ParametroIndexacao, Agente
from django.contrib.auth.hashers import make_password

class UsuarioForm(forms.ModelForm):
    confirm_password = forms.CharField(widget=forms.PasswordInput(), required=False)
    password = forms.CharField(widget=forms.PasswordInput(), required=False)
    
    class Meta:
        model = Usuario
        fields = ['username', 'first_name', 'last_name', 'email', 'nivel', 'empresa', 'telefone', 'is_active']
        widgets = {
            'telefone': forms.TextInput(attrs={'class': 'form-control'}),
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'nivel': forms.Select(attrs={'class': 'form-select'}),
            'empresa': forms.Select(attrs={'class': 'form-select'}),
        }
    
    def __init__(self, *args, **kwargs):
        super(UsuarioForm, self).__init__(*args, **kwargs)
        
        # Se estiver editando um usuário existente, não exigir senha
        if self.instance.pk:
            self.fields['password'].required = False
            self.fields['confirm_password'].required = False
        else:
            self.fields['password'].required = True
            self.fields['confirm_password'].required = True
        
        # Adicionar atributos de classe para os widgets que não foram especificados
        for field_name, field in self.fields.items():
            if not hasattr(field.widget, 'attrs') or 'class' not in field.widget.attrs:
                if isinstance(field.widget, forms.CheckboxInput):
                    field.widget.attrs['class'] = 'form-check-input'
                else:
                    field.widget.attrs['class'] = 'form-control'
    
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")
        
        if password and confirm_password and password != confirm_password:
            self.add_error('confirm_password', "As senhas não coincidem.")
        
        return cleaned_data
    
    def save(self, commit=True):
        user = super().save(commit=False)
        
        # Se uma senha foi fornecida, codificá-la
        password = self.cleaned_data.get('password')
        if password:
            user.password = make_password(password)
        
        if commit:
            user.save()
        
        return user

class ParametroForm(forms.ModelForm):
    class Meta:
        model = Parametro
        fields = ['parametro', 'valor']
        widgets = {
            'parametro': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome do parâmetro'}),
            'valor': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Valor do parâmetro'})
        }

class EmpresaForm(forms.ModelForm):
    class Meta:
        model = Empresa
        fields = ['nome', 'cnpj', 'endereco', 'telefone', 'email', 'logo', 'ativa']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome da empresa'}),
            'cnpj': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'CNPJ'}),
            'endereco': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Endereço'}),
            'telefone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Telefone'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email'}),
            'ativa': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class FeiraForm(forms.ModelForm):
    class Meta:
        model = Feira
        fields = [
            'nome', 'local', 'cidade', 'estado', 'data_inicio', 'data_fim',
            'website', 'contato_organizacao', 'email_organizacao', 
            'telefone_organizacao', 'manual', 'ativa'
        ]
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'local': forms.TextInput(attrs={'class': 'form-control'}),
            'cidade': forms.TextInput(attrs={'class': 'form-control'}),
            'estado': forms.TextInput(attrs={'class': 'form-control'}),
            'data_inicio': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'data_fim': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'website': forms.URLInput(attrs={'class': 'form-control'}),
            'contato_organizacao': forms.TextInput(attrs={'class': 'form-control'}),
            'email_organizacao': forms.EmailInput(attrs={'class': 'form-control'}),
            'telefone_organizacao': forms.TextInput(attrs={'class': 'form-control'}),
            'ativa': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class ParametroIndexacaoForm(forms.ModelForm):
    class Meta:
        model = ParametroIndexacao
        fields = ['nome', 'descricao', 'valor', 'tipo', 'categoria']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'descricao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'valor': forms.TextInput(attrs={'class': 'form-control'}),
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'categoria': forms.Select(attrs={'class': 'form-select'}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        tipo = cleaned_data.get('tipo')
        valor = cleaned_data.get('valor')
        
        # Validar valor de acordo com o tipo
        if tipo and valor:
            try:
                if tipo == 'int':
                    int(valor)
                elif tipo == 'float':
                    float(valor)
                elif tipo == 'bool':
                    if valor.lower() not in ('true', 'false', 'sim', 'não', 's', 'n', 'yes', 'no', 'y', 'n', '1', '0'):
                        self.add_error('valor', 'Valor booleano inválido')
            except ValueError:
                self.add_error('valor', f'Valor não é do tipo {tipo}')
        
        return cleaned_data
    
class AgenteForm(forms.ModelForm):
    class Meta:
        model = Agente
        fields = ['nome', 'descricao', 'llm_provider', 'llm_model', 'llm_temperature', 'llm_system_prompt', 'task_instructions', 'ativo']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'descricao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'llm_provider': forms.TextInput(attrs={'class': 'form-control'}),
            'llm_model': forms.TextInput(attrs={'class': 'form-control'}),
            'llm_temperature': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'min': '0', 'max': '1'}),
            'llm_system_prompt': forms.Textarea(attrs={'class': 'form-control', 'rows': 8}),
            'task_instructions': forms.Textarea(attrs={'class': 'form-control', 'rows': 8}),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        
    def clean(self):
        cleaned_data = super().clean()
        llm_temperature = cleaned_data.get('llm_temperature')
        
        # Validar temperatura entre 0 e 1
        if llm_temperature is not None:
            if llm_temperature < 0 or llm_temperature > 1:
                self.add_error('llm_temperature', 'A temperatura deve estar entre 0 e 1')
        
        # Validar se o prompt do sistema foi fornecido
        llm_system_prompt = cleaned_data.get('llm_system_prompt')
        if not llm_system_prompt or llm_system_prompt.strip() == '':
            self.add_error('llm_system_prompt', 'O prompt do sistema é obrigatório')
        
        # Validar provider e modelo
        llm_provider = cleaned_data.get('llm_provider')
        llm_model = cleaned_data.get('llm_model')
        
        if not llm_provider or llm_provider.strip() == '':
            self.add_error('llm_provider', 'O provedor é obrigatório')
        
        if not llm_model or llm_model.strip() == '':
            self.add_error('llm_model', 'O modelo é obrigatório')
        
        return cleaned_data