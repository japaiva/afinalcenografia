# projetista/forms.py

from django import forms
from projetista.models import ConceitoVisual, ImagemConceitoVisual, PackageVistasPreset

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
        fields = ['imagem', 'descricao', 'angulo_vista', 'categoria']
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
            'categoria': forms.Select(attrs={
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
        initial='perspectiva_externa'
    )

class GeracaoMultiplasVistasForm(forms.Form):
    """Formulário para geração de múltiplas vistas via IA"""
    
    # Pacotes pré-definidos
    PACOTE_CHOICES = [
        ('cliente', 'Apresentação para Cliente (6-8 vistas)'),
        ('tecnico_basico', 'Técnico Básico (12-15 vistas)'),
        ('fotogrametria', 'Fotogrametria Completa (20+ vistas)'),
        ('personalizado', 'Personalizado (escolher vistas)')
    ]
    
    pacote_vistas = forms.ChoiceField(
        choices=PACOTE_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        initial='cliente',
        label="Tipo de Pacote"
    )
    
    # Vistas para cliente (sempre visíveis)
    vistas_cliente = forms.MultipleChoiceField(
        choices=[
            ('perspectiva_externa', 'Perspectiva Externa Principal'),
            ('entrada_recepcao', 'Vista da Entrada/Recepção'),
            ('interior_principal', 'Vista Interna Principal'),
            ('area_produtos', 'Área de Produtos/Destaque'),
        ],
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        initial=['perspectiva_externa', 'entrada_recepcao', 'interior_principal'],
        required=False,
        label="Vistas para Cliente"
    )
    
    # Vistas técnicas externas
    vistas_externas = forms.MultipleChoiceField(
        choices=[
            ('elevacao_frontal', 'Elevação Frontal'),
            ('elevacao_lateral_esquerda', 'Elevação Lateral Esquerda'),
            ('elevacao_lateral_direita', 'Elevação Lateral Direita'),
            ('elevacao_fundos', 'Elevação Fundos'),
            ('quina_frontal_esquerda', 'Quina Frontal-Esquerda'),
            ('quina_frontal_direita', 'Quina Frontal-Direita'),
        ],
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        required=False,
        label="Vistas Técnicas Externas"
    )
    
    # Plantas e elevações
    plantas_elevacoes = forms.MultipleChoiceField(
        choices=[
            ('planta_baixa', 'Planta Baixa'),
            ('vista_superior', 'Vista Superior'),
        ],
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        required=False,
        label="Plantas e Elevações"
    )
    
    # Vistas internas
    vistas_internas = forms.MultipleChoiceField(
        choices=[
            ('interior_parede_norte', 'Interior - Parede Norte'),
            ('interior_parede_sul', 'Interior - Parede Sul'),
            ('interior_parede_leste', 'Interior - Parede Leste'),
            ('interior_parede_oeste', 'Interior - Parede Oeste'),
            ('interior_perspectiva_1', 'Interior - Perspectiva 1'),
            ('interior_perspectiva_2', 'Interior - Perspectiva 2'),
            ('interior_perspectiva_3', 'Interior - Perspectiva 3'),
        ],
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        required=False,
        label="Vistas Internas"
    )
    
    # Detalhes
    detalhes = forms.MultipleChoiceField(
        choices=[
            ('detalhe_balcao', 'Detalhe do Balcão'),
            ('detalhe_display', 'Detalhe dos Displays'),
            ('detalhe_iluminacao', 'Detalhe da Iluminação'),
            ('detalhe_entrada', 'Detalhe da Entrada'),
        ],
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        required=False,
        label="Detalhes Específicos"
    )
    
    # Estilo de geração
    estilo_visualizacao = forms.ChoiceField(
        choices=[
            ('fotorrealista', 'Fotorrealista'),
            ('renderizado', 'Renderização 3D'),
            ('tecnico', 'Técnico/Arquitetônico'),
            ('estilizado', 'Estilizado'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'}),
        initial='fotorrealista',
        label="Estilo de Visualização"
    )
    
    # Configurações de iluminação
    iluminacao = forms.ChoiceField(
        choices=[
            ('diurna', 'Iluminação Diurna'),
            ('noturna', 'Iluminação Noturna'),
            ('evento', 'Iluminação de Evento'),
            ('mista', 'Mista (dia/noite conforme vista)'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'}),
        initial='diurna',
        label="Iluminação"
    )
    
    # Instruções adicionais
    instrucoes_adicionais = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Instruções específicas para todas as vistas...'
        }),
        required=False,
        label="Instruções Adicionais"
    )
    
    # Prioridade de geração
    prioridade_cliente = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label="Gerar vistas para cliente primeiro"
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
        ('photogrammetry', 'ZIP - Pacote Fotogrametria'),
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
    
    # Filtro por categoria para exportação
    categorias_exportar = forms.MultipleChoiceField(
        choices=ImagemConceitoVisual.CATEGORIA_CHOICES,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        required=False,
        initial=['cliente'],
        label="Categorias a Exportar"
    )

class FiltroVistasForm(forms.Form):
    """Formulário para filtrar vistas na visualização"""
    categoria = forms.ChoiceField(
        choices=[('todas', 'Todas as Categorias')] + ImagemConceitoVisual.CATEGORIA_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        initial='todas',
        required=False
    )
    
    essencial_fotogrametria = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label="Apenas essenciais para fotogrametria"
    )
    
    ia_gerada = forms.ChoiceField(
        choices=[
            ('todas', 'Todas'),
            ('ia', 'Apenas geradas por IA'),
            ('manual', 'Apenas upload manual')
        ],
        widget=forms.Select(attrs={'class': 'form-select'}),
        initial='todas',
        required=False,
        label="Origem"
    )