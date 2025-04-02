from django import forms
from django.contrib.auth.hashers import make_password
from core.models import Usuario, Empresa, Parametro


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

class UsuarioForm(forms.ModelForm):
    password = forms.CharField(
        label="Senha", 
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        required=False,  # Não obrigatório na edição
        help_text="Deixe em branco para manter a senha atual (ao editar)."
    )
    
    class Meta:
        model = Usuario
        fields = ['username', 'email', 'first_name', 'last_name', 'password', 'nivel', 'empresa', 'telefone', 'foto_perfil', 'is_active']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'nivel': forms.Select(attrs={'class': 'form-control'}),
            'empresa': forms.Select(attrs={'class': 'form-control'}),
            'telefone': forms.TextInput(attrs={'class': 'form-control', 'data-mask': '(00) 00000-0000'}),
            'foto_perfil': forms.FileInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Se for uma edição, a senha não é obrigatória
        if self.instance.pk:
            self.fields['password'].required = False
        else:
            self.fields['password'].required = True
            
        # Filtrar apenas empresas ativas para o select
        self.fields['empresa'].queryset = Empresa.objects.filter(ativa=True)
    
    def clean_password(self):
        """
        Processa o campo de senha:
        - Se for um novo usuário, a senha é obrigatória
        - Se for edição e senha estiver vazia, mantém a senha atual
        - Se for edição e senha for fornecida, criptografa a nova senha
        """
        password = self.cleaned_data.get('password')
        if self.instance.pk and not password:
            # Se é edição e senha vazia, retorna a senha existente
            return self.instance.password
        elif password:
            # Se senha fornecida, criptografa
            return make_password(password)
        return password
    
    def save(self, commit=True):
        usuario = super().save(commit=False)
        
        # Apenas define a senha se foi fornecida no formulário
        password = self.cleaned_data.get('password')
        if password:
            usuario.password = password
            
        if commit:
            usuario.save()
        return usuario

class ParametroForm(forms.ModelForm):
    class Meta:
        model = Parametro
        fields = ['parametro', 'valor']
        widgets = {
            'parametro': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'valor': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
        }