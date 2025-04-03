from django import forms
from django.contrib.auth.hashers import make_password
from core.models import Usuario, Empresa, Parametro, PerfilUsuario
from core.storage import MinioStorage


class EmpresaForm(forms.ModelForm):
    class Meta:
        model = Empresa
        fields = ['nome', 'cnpj', 'endereco', 'telefone', 'email', 'logo', 'ativa']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'cnpj': forms.TextInput(attrs={'class': 'form-control', 'data-mask': '00.000.000/0000-00'}),
            'endereco': forms.TextInput(attrs={'class': 'form-control'}),
            'telefone': forms.TextInput(attrs={'class': 'form-control', 'data-mask': '(00) 00000-0000'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'logo': forms.FileInput(attrs={'class': 'form-control'}),
            'ativa': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class ParametroForm(forms.ModelForm):
    class Meta:
        model = Parametro
        fields = ['parametro', 'valor']
        widgets = {
            'parametro': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'valor': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
        }

class UsuarioForm(forms.ModelForm):
    password = forms.CharField(
        label="Senha", 
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        required=False,
        help_text="Deixe em branco para manter a senha atual (ao editar)."
    )
    
    class Meta:
        model = Usuario
        fields = [
            'username', 'email', 'first_name', 'last_name', 'password',
            'nivel', 'empresa', 'telefone', 'is_active'
        ]
        # Removido 'foto_perfil' dos campos
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'nivel': forms.Select(attrs={'class': 'form-control'}),
            'empresa': forms.Select(attrs={'class': 'form-control'}),
            'telefone': forms.TextInput(attrs={'class': 'form-control', 'data-mask': '(00) 00000-0000'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields['password'].required = False
        else:
            self.fields['password'].required = True

        self.fields['empresa'].queryset = Empresa.objects.filter(ativa=True)
    
    def clean_password(self):
        password = self.cleaned_data.get('password')
        if self.instance.pk and not password:
            return self.instance.password
        elif password:
            return make_password(password)
        return password
    
    def save(self, commit=True):
        usuario = super().save(commit=False)
        password = self.cleaned_data.get('password')
        if password:
            usuario.password = password
        if commit:
            usuario.save()
        return usuario


# Adicionando o formulário para PerfilUsuario
class PerfilUsuarioForm(forms.ModelForm):
    class Meta:
        model = PerfilUsuario
        fields = ['telefone', 'foto']
        widgets = {
            'telefone': forms.TextInput(attrs={'class': 'form-control', 'data-mask': '(00) 00000-0000'}),
            'foto': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }
