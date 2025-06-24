# projetista/forms.py

from django import forms
from projetista.models import ConceitoVisualLegado, ConceitoVisualNovo, PlantaBaixa, Modelo3D

# =============================================================================
# FORMULÁRIOS PARA O SISTEMA LEGADO (compatibilidade)
# =============================================================================

class ConceitoVisualLegadoForm(forms.ModelForm):
    """Formulário para manipulação do conceito visual legado (Etapa 1)"""
    class Meta:
        model = ConceitoVisualLegado
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

# =============================================================================
# FORMULÁRIOS PARA O NOVO SISTEMA
# =============================================================================

class ConceitoVisualNovoForm(forms.ModelForm):
    """Formulário para o novo sistema de conceito visual"""
    class Meta:
        model = ConceitoVisualNovo
        fields = [
            'descricao', 'estilo_visualizacao', 'iluminacao', 'instrucoes_adicionais'
        ]
        widgets = {
            'descricao': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Descrição do conceito visual'
            }),
            'estilo_visualizacao': forms.Select(attrs={
                'class': 'form-select'
            }),
            'iluminacao': forms.Select(attrs={
                'class': 'form-select'
            }),
            'instrucoes_adicionais': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Instruções específicas para geração'
            }),
        }

class GeracaoImagemForm(forms.Form):
    """Formulário para geração de imagem via IA"""
    estilo_visualizacao = forms.ChoiceField(
        choices=[
            ('fotorrealista', 'Fotorrealista'),
            ('artistico', 'Artístico'),
            ('tecnico', 'Técnico'),
            ('conceitual', 'Conceitual')
        ],
        widget=forms.Select(attrs={'class': 'form-select'}),
        initial='fotorrealista'
    )
    
    iluminacao = forms.ChoiceField(
        choices=[
            ('diurna', 'Iluminação Diurna'),
            ('noturna', 'Iluminação Noturna'),
            ('feira', 'Iluminação de Feira'),
            ('dramatica', 'Iluminação Dramática')
        ],
        widget=forms.Select(attrs={'class': 'form-select'}),
        initial='feira'
    )
    
    instrucoes_adicionais = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Instruções adicionais para a geração da imagem (opcional)'
        }),
        required=False
    )

class GeracaoMultiplasVistasForm(forms.Form):
    """Formulário para geração de múltiplas vistas via IA"""
    
    # Vistas para cliente
    vistas_cliente = forms.MultipleChoiceField(
        choices=[
            ('perspectiva_externa', 'Perspectiva Externa Principal'),
            ('entrada_recepcao', 'Vista da Entrada/Recepção'),
            ('interior_principal', 'Vista Interna Principal'),
            ('area_produtos', 'Área de Produtos/Destaque'),
        ],
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
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
    
    def clean(self):
        """
        Validação para garantir que pelo menos uma vista seja selecionada
        """
        cleaned_data = super().clean()
        
        # Coletar todas as vistas selecionadas
        vistas_selecionadas = []
        vistas_selecionadas.extend(cleaned_data.get('vistas_cliente', []))
        vistas_selecionadas.extend(cleaned_data.get('vistas_externas', []))
        vistas_selecionadas.extend(cleaned_data.get('plantas_elevacoes', []))
        vistas_selecionadas.extend(cleaned_data.get('vistas_internas', []))
        vistas_selecionadas.extend(cleaned_data.get('detalhes', []))
        
        if not vistas_selecionadas:
            raise forms.ValidationError(
                "Selecione pelo menos uma vista para gerar."
            )
        
        return cleaned_data

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

class UploadImagemForm(forms.Form):
    """Formulário para upload manual de imagem"""
    imagem = forms.ImageField(
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': 'image/jpeg,image/png,image/webp'
        })
    )
    descricao = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Descrição da imagem'
        })
    )
    angulo_vista = forms.ChoiceField(
        choices=[
            ('perspectiva', 'Perspectiva Externa'),
            ('frontal', 'Vista Frontal'),
            ('lateral', 'Vista Lateral'),
            ('interior', 'Vista Interior'),
            ('detalhe', 'Detalhe'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    categoria = forms.ChoiceField(
        choices=[
            ('cliente', 'Para Cliente'),
            ('tecnica', 'Técnica'),
            ('referencia', 'Referência'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'})
    )