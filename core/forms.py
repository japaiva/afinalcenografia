# core/forms.py
from django import forms
from core.models import Usuario, Parametro, Empresa, Feira, ParametroIndexacao, Agente, Crew, CrewMembro, CrewTask
from django.contrib.auth.hashers import make_password
from core.utils.view_utils import CustomDateInput 

class AgenteForm(forms.ModelForm):
    class Meta:
        model = Agente
        fields = [
            'nome', 'tipo', 'descricao', 
            'llm_provider', 'llm_model', 'llm_temperature', 
            'llm_system_prompt', 'task_instructions',
            'crew_role', 'crew_goal', 'crew_backstory',
            'ativo'
        ]
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'descricao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'llm_provider': forms.TextInput(attrs={
                'class': 'form-control'
            }),
            'llm_model': forms.TextInput(attrs={
                'class': 'form-control'
            }),
            'llm_temperature': forms.NumberInput(attrs={
                'class': 'form-control', 
                'step': '0.1', 
                'min': '0', 
                'max': '1'
            }),
            'llm_system_prompt': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 8,
                'placeholder': 'Prompt base que define o comportamento do agente...'
            }),
            'task_instructions': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 6,
                'placeholder': 'Instruções específicas para execução de tarefas...'
            }),
            'crew_role': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: Analista de Dados, Arquiteto Espacial, Gerador de SVG'
            }),
            'crew_goal': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 3,
                'placeholder': 'Objetivo específico deste agente dentro do fluxo de trabalho...'
            }),
            'crew_backstory': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 4,
                'placeholder': 'Contexto e experiência do agente para melhor performance...'
            }),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Adicionar classes JavaScript para comportamento dinâmico
        self.fields['tipo'].widget.attrs.update({
            'onchange': 'toggleCrewFields(this.value)'
        })
        
        # Se for edição, ajustar required fields baseado no tipo
        if self.instance.pk and self.instance.tipo == 'individual':
            self.fields['crew_role'].required = False
            self.fields['crew_goal'].required = False
            self.fields['crew_backstory'].required = False
    
    def clean(self):
        cleaned_data = super().clean()
        tipo = cleaned_data.get('tipo')
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
        
        # Validações específicas para crew members
        if tipo == 'crew_member':
            crew_role = cleaned_data.get('crew_role')
            if not crew_role or crew_role.strip() == '':
                self.add_error('crew_role', 'Papel no crew é obrigatório para membros de crew')
        
        return cleaned_data


class CrewForm(forms.ModelForm):
    """Formulário principal para criar/editar crews"""
    
    # ADICIONAR CAMPO PARA SELECIONAR AGENTES DIRETAMENTE NO FORMULÁRIO PRINCIPAL
    agentes_selecionados = forms.ModelMultipleChoiceField(
        queryset=Agente.objects.filter(tipo='crew_member', ativo=True),
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        required=True,
        help_text="Selecione os agentes que farão parte deste crew",
        label="Agentes do Crew"
    )
    
    class Meta:
        model = Crew
        fields = [
            'nome', 'descricao', 'processo', 'verbose', 'memory',
            'manager_llm_provider', 'manager_llm_model', 'manager_llm_temperature',
            'ativo'
        ]
        widgets = {
            'nome': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: Arquiteto de Plantas, Validador de Briefings'
            }),
            'descricao': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 4,
                'placeholder': 'Descreva o que este crew faz e qual problema resolve...'
            }),
            'processo': forms.Select(attrs={'class': 'form-select'}),
            'verbose': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'memory': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'manager_llm_provider': forms.Select(attrs={'class': 'form-select'}, choices=[
                ('', 'Selecione o provedor...'),
                ('openai', 'OpenAI'),
                ('anthropic', 'Anthropic'),
                ('google', 'Google'),
            ]),
            'manager_llm_model': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: gpt-4, claude-3-opus'
            }),
            'manager_llm_temperature': forms.NumberInput(attrs={
                'class': 'form-control', 
                'step': '0.1', 
                'min': '0', 
                'max': '1'
            }),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Campos obrigatórios
        self.fields['nome'].required = True
        self.fields['descricao'].required = True
        
        # Se for edição, pré-selecionar agentes já no crew
        if self.instance.pk:
            agentes_no_crew = CrewMembro.objects.filter(
                crew=self.instance
            ).values_list('agente_id', flat=True)
            self.fields['agentes_selecionados'].initial = agentes_no_crew
        
        # Valores padrão para novo crew
        if not self.instance.pk:
            self.fields['verbose'].initial = True
            self.fields['memory'].initial = True
            self.fields['ativo'].initial = True
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Validações básicas
        nome = cleaned_data.get('nome')
        if not nome or nome.strip() == '':
            self.add_error('nome', 'O nome do crew é obrigatório')
        
        descricao = cleaned_data.get('descricao')
        if not descricao or descricao.strip() == '':
            self.add_error('descricao', 'A descrição do crew é obrigatória')
        
        # Validar se pelo menos um agente foi selecionado
        agentes = cleaned_data.get('agentes_selecionados')
        if not agentes or len(agentes) == 0:
            self.add_error('agentes_selecionados', 'Selecione pelo menos um agente para o crew')
        
        # Validações para processo hierárquico
        processo = cleaned_data.get('processo')
        if processo == 'hierarchical':
            manager_provider = cleaned_data.get('manager_llm_provider')
            manager_model = cleaned_data.get('manager_llm_model')
            
            if not manager_provider:
                self.add_error('manager_llm_provider', 
                             'Provedor do manager é obrigatório para processo hierárquico')
            
            if not manager_model or manager_model.strip() == '':
                self.add_error('manager_llm_model', 
                             'Modelo do manager é obrigatório para processo hierárquico')
        
        return cleaned_data
    
    def save(self, commit=True):
        # Salvar o crew primeiro
        crew = super().save(commit=commit)
        
        if commit and self.cleaned_data.get('agentes_selecionados'):
            # Remover membros existentes se for edição
            if self.instance.pk:
                CrewMembro.objects.filter(crew=crew).delete()
            
            # Adicionar novos membros
            agentes_selecionados = self.cleaned_data['agentes_selecionados']
            for i, agente in enumerate(agentes_selecionados, 1):
                CrewMembro.objects.create(
                    crew=crew,
                    agente=agente,
                    ordem_execucao=i
                )
        
        return crew
    
class CrewMembroForm(forms.ModelForm):
    """
    Formulário para adicionar UM agente específico a um crew existente
    (usado na página de detalhes do crew)
    """
    class Meta:
        model = CrewMembro
        fields = ['agente', 'ordem_execucao', 'pode_delegar', 'max_iter', 'max_execution_time', 'ativo']
        widgets = {
            'agente': forms.Select(attrs={'class': 'form-select'}),
            'ordem_execucao': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'pode_delegar': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'max_iter': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'max': '50'}),
            'max_execution_time': forms.NumberInput(attrs={'class': 'form-control', 'min': '30', 'max': '3600'}),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        crew = kwargs.pop('crew', None)
        is_edit = kwargs.get('instance') is not None
        super().__init__(*args, **kwargs)
        
        if crew:
            if is_edit:
                # Na edição, não filtrar o agente atual
                agentes_ja_no_crew = CrewMembro.objects.filter(crew=crew).exclude(
                    id=self.instance.id if self.instance.id else None
                ).values_list('agente_id', flat=True)
                
                # Mostrar todos os agentes crew_member ativos, exceto os já no crew (menos o atual)
                self.fields['agente'].queryset = Agente.objects.filter(
                    tipo='crew_member', 
                    ativo=True
                ).exclude(id__in=agentes_ja_no_crew)
                
                # Para edição, tornar o campo agente readonly se necessário
                # self.fields['agente'].disabled = True
                
            else:
                # Na criação, excluir todos que já estão no crew
                agentes_ja_no_crew = CrewMembro.objects.filter(crew=crew).values_list('agente_id', flat=True)
                self.fields['agente'].queryset = Agente.objects.filter(
                    tipo='crew_member', 
                    ativo=True
                ).exclude(id__in=agentes_ja_no_crew)
                
                # Ordem padrão: próximo número
                proxima_ordem = CrewMembro.objects.filter(crew=crew).count() + 1
                self.fields['ordem_execucao'].initial = proxima_ordem
                self.fields['ativo'].initial = True
    
    def clean_ordem_execucao(self):
        ordem = self.cleaned_data.get('ordem_execucao')
        if ordem and ordem < 1:
            raise forms.ValidationError("A ordem de execução deve ser maior que 0")
        return ordem
    
    def clean_max_iter(self):
        max_iter = self.cleaned_data.get('max_iter')
        if max_iter and (max_iter < 1 or max_iter > 50):
            raise forms.ValidationError("Máximo de iterações deve estar entre 1 e 50")
        return max_iter
    
    def clean_max_execution_time(self):
        max_time = self.cleaned_data.get('max_execution_time')
        if max_time and (max_time < 30 or max_time > 3600):
            raise forms.ValidationError("Tempo máximo deve estar entre 30 e 3600 segundos")
        return max_time

# core/forms.py - Seção CrewTaskForm corrigida


class CrewTaskForm(forms.ModelForm):
    class Meta:
        model = CrewTask
        fields = [
            # CAMPOS PRINCIPAIS (sempre visíveis)
            'nome', 'descricao', 'expected_output', 'agente_responsavel',
            'ordem_execucao', 
            
            # CAMPOS ÚTEIS (visíveis)
            'tools_config', 'output_file',
            
            # CAMPOS OPCIONAIS AVANÇADOS (visíveis mas menos destaque)
            'async_execution', 'dependencias',
            
            # STATUS
            'ativo'
            
            # OCULTOS NO FORM (mas mantidos no model):
            # - context_template (usar descricao com interpolação)
        ]
        widgets = {
            'nome': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: Analisar Briefing, Gerar Layout, Criar SVG'
            }),
            'descricao': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 6,  # ← MAIOR porque aqui vai a interpolação
                'placeholder': '''DADOS RECEBIDOS:
{briefing_completo}

Descreva o que esta task deve fazer com os dados...'''
            }),
            'expected_output': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 3,
                'placeholder': 'JSON estruturado com análise completa, SVG com coordenadas, etc.'
            }),
            'agente_responsavel': forms.Select(attrs={'class': 'form-select'}),
            'ordem_execucao': forms.NumberInput(attrs={
                'class': 'form-control', 
                'min': '1'
            }),
            
            # TOOLS CONFIG - DESTACADO
            'tools_config': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 4,
                'placeholder': '''{"svg_generator": {"width": 800, "height": 600}, "file_upload": {"allowed_types": ["png", "svg"]}}'''
            }),
            
            # OUTPUT FILE - ÚTIL
            'output_file': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'outputs/planta_baixa.svg, outputs/analise.json'
            }),
            
            # CAMPOS AVANÇADOS (menos destaque visual)
            'async_execution': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'dependencias': forms.CheckboxSelectMultiple(attrs={
                'class': 'form-check-input'
            }),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        crew = kwargs.pop('crew', None)
        super().__init__(*args, **kwargs)
        
        if crew:
            # Filtrar agentes do crew
            agentes_do_crew = CrewMembro.objects.filter(
                crew=crew, ativo=True
            ).values_list('agente_id', flat=True)
            
            self.fields['agente_responsavel'].queryset = Agente.objects.filter(
                id__in=agentes_do_crew
            )
            
            # Filtrar dependências (tasks do mesmo crew, exceto self)
            dependencias_queryset = CrewTask.objects.filter(crew=crew)
            if self.instance.pk:
                dependencias_queryset = dependencias_queryset.exclude(id=self.instance.id)
            self.fields['dependencias'].queryset = dependencias_queryset
        
        # LABELS e HELP_TEXT otimizados
        self.fields['descricao'].label = "Descrição da Task (com interpolação)"
        self.fields['descricao'].help_text = "Use {briefing_completo} para receber dados reais do projeto"
        
        self.fields['tools_config'].label = "Configuração de Ferramentas (JSON)"
        self.fields['tools_config'].help_text = "Configure ferramentas específicas para esta task"
        
        self.fields['output_file'].label = "Arquivo de Saída (opcional)"
        self.fields['output_file'].help_text = "Caminho para salvar resultado automaticamente"
        
        self.fields['dependencias'].label = "Dependências (opcional)"
        self.fields['dependencias'].help_text = "Tasks que devem executar antes desta"
    
    def clean_tools_config(self):
        tools_config = self.cleaned_data.get('tools_config')
        if tools_config:
            try:
                if isinstance(tools_config, str) and tools_config.strip():
                    import json
                    parsed = json.loads(tools_config)
                    # Validar estrutura básica
                    if not isinstance(parsed, dict):
                        raise forms.ValidationError("Configuração deve ser um objeto JSON")
                    return tools_config
            except (json.JSONDecodeError, TypeError):
                raise forms.ValidationError("Configuração deve ser um JSON válido")
        return tools_config
    
    def clean_output_file(self):
        output_file = self.cleaned_data.get('output_file')
        if output_file:
            import os
            ext = os.path.splitext(output_file)[1].lower()
            allowed_extensions = ['.json', '.txt', '.md', '.csv', '.yaml', '.yml', '.png', '.svg', '.pdf']
            if ext and ext not in allowed_extensions:
                raise forms.ValidationError(f"Extensão {ext} não permitida. Use: {', '.join(allowed_extensions)}")
        return output_file





class CrewTaskForm(forms.ModelForm):
    class Meta:
        model = CrewTask
        fields = [
            'nome', 'descricao', 'expected_output', 'agente_responsavel',
            'ordem_execucao', 'async_execution', 'dependencias',
            'context_template', 'tools_config', 'output_file', 'ativo'
        ]
        widgets = {
            'nome': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: Analisar Briefing, Gerar Layout, Criar SVG'
            }),
            'descricao': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 4,
                'placeholder': 'Descrição detalhada do que esta tarefa deve fazer...'
            }),
            'expected_output': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 3,
                'placeholder': 'Descreva o formato e conteúdo esperado do resultado...'
            }),
            'agente_responsavel': forms.Select(attrs={'class': 'form-select'}),
            'ordem_execucao': forms.NumberInput(attrs={
                'class': 'form-control', 
                'min': '1'
            }),
            'async_execution': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            # CORRIGIDO: Widget adequado para ManyToMany
            'dependencias': forms.CheckboxSelectMultiple(attrs={
                'class': 'form-check-input'
            }),
            'context_template': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 8,
                'placeholder': 'Template para contexto da tarefa com variáveis como {empresa_nome}, {projeto_nome}...'
            }),
            'tools_config': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 4,
                'placeholder': '{"search_limit": 10, "file_types": ["pdf", "docx"], "api_timeout": 30}'
            }),
            'output_file': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: outputs/task_result.json, reports/analysis.md'
            }),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        crew = kwargs.pop('crew', None)
        super().__init__(*args, **kwargs)
        
        # Se for para um crew específico
        if crew:
            # Filtrar agentes apenas os do crew
            agentes_do_crew = CrewMembro.objects.filter(
                crew=crew, 
                ativo=True
            ).values_list('agente_id', flat=True)
            
            self.fields['agente_responsavel'].queryset = Agente.objects.filter(
                id__in=agentes_do_crew
            )
            
            # CORRIGIDO: Filtrar dependências apenas as tarefas do mesmo crew
            # e excluir a própria task se for edição
            dependencias_queryset = CrewTask.objects.filter(crew=crew)
            if self.instance.pk:
                dependencias_queryset = dependencias_queryset.exclude(id=self.instance.id)
            
            self.fields['dependencias'].queryset = dependencias_queryset
            
        # IMPORTANTE: Labels mais descritivos
        self.fields['dependencias'].label = "Dependências (Tasks que devem executar antes)"
        self.fields['dependencias'].help_text = "Selecione as tarefas que devem ser concluídas antes desta"
    
    def clean_tools_config(self):
        tools_config = self.cleaned_data.get('tools_config')
        if tools_config:
            try:
                # Validar se é JSON válido
                if isinstance(tools_config, str) and tools_config.strip():
                    import json
                    json.loads(tools_config)
            except (json.JSONDecodeError, TypeError):
                raise forms.ValidationError("Configuração de ferramentas deve ser um JSON válido")
        return tools_config
    
    def clean_output_file(self):
        output_file = self.cleaned_data.get('output_file')
        if output_file:
            # Validar extensões permitidas
            import os
            ext = os.path.splitext(output_file)[1].lower()
            allowed_extensions = ['.json', '.txt', '.md', '.csv', '.yaml', '.yml', '.png', '.svg']
            if ext and ext not in allowed_extensions:
                raise forms.ValidationError(f"Extensão {ext} não permitida. Use: {', '.join(allowed_extensions)}")
        return output_file
class FeiraForm(forms.ModelForm):
    class Meta:
        model = Feira
        fields = [
            # Bloco Evento (renomeado)
            'nome', 'descricao', 'website', 'local', 'data_horario', 'publico_alvo', 
            'eventos_simultaneos', 'promotora',
            # Campos controle mantidos no bloco Evento
            'cidade', 'estado', 'data_inicio', 'data_fim', 'ativa',
            # Bloco Montagem e Desmontagem (renomeado)
            'periodo_montagem', 'portao_acesso', 'periodo_desmontagem',
            # Bloco Normas Técnicas (renomeado)
            'altura_estande', 'palcos', 'piso_elevado', 'mezanino', 'iluminacao', 
            'materiais_permitidos_proibidos', 'visibilidade_obrigatoria', 
            'paredes_vidro', 'estrutura_aerea',
            # Bloco Credenciamento
            'documentos', 'credenciamento',
            # Manual
            'manual'
        ]
        widgets = {
            # Bloco Evento
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'descricao': forms.TextInput(attrs={'class': 'form-control'}),
            'website': forms.URLInput(attrs={'class': 'form-control'}),
            'local': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'data_horario': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'publico_alvo': forms.TextInput(attrs={'class': 'form-control'}),
            'eventos_simultaneos': forms.TextInput(attrs={'class': 'form-control'}),
            'promotora': forms.TextInput(attrs={'class': 'form-control'}),
            
            # Campos de controle mantidos
            'cidade': forms.TextInput(attrs={'class': 'form-control'}),
            'estado': forms.TextInput(attrs={'class': 'form-control'}),
            'data_inicio': CustomDateInput(attrs={'class': 'form-control'}),
            'data_fim': CustomDateInput(attrs={'class': 'form-control'}),
            'ativa': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            
            # Bloco Montagem e Desmontagem
            'periodo_montagem': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'portao_acesso': forms.TextInput(attrs={'class': 'form-control'}),
            'periodo_desmontagem': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            
            # Bloco Normas Técnicas
            'altura_estande': forms.TextInput(attrs={'class': 'form-control'}),
            'palcos': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'piso_elevado': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'mezanino': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'iluminacao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'materiais_permitidos_proibidos': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'visibilidade_obrigatoria': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'paredes_vidro': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'estrutura_aerea': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            
            # Bloco Credenciamento
            'documentos': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'credenciamento': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
        }
class UsuarioForm(forms.ModelForm):
    confirm_password = forms.CharField(widget=forms.PasswordInput(), required=False)
    password = forms.CharField(widget=forms.PasswordInput(), required=False)
    
    class Meta:
        model = Usuario
        fields = ['username', 'first_name', 'last_name', 'email', 'nivel', 'empresa', 'telefone', 'sexo', 'is_active']
        widgets = {
            'telefone': forms.TextInput(attrs={'class': 'form-control'}),
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'nivel': forms.Select(attrs={'class': 'form-select'}),
            'empresa': forms.Select(attrs={'class': 'form-select'}),
            'sexo': forms.Select(attrs={'class': 'form-select'}),
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
        
        # Só verificar se as senhas coincidem se uma nova senha for fornecida
        if password:
            if not confirm_password:
                self.add_error('confirm_password', "Por favor, confirme a senha.")
            elif password != confirm_password:
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
        fields = ['nome', 'cnpj', 'endereco', 'telefone', 'email', 'logo', 'descricao', 'razao_social', 'ativa']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome da empresa'}),
            'cnpj': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'CNPJ'}),
            'endereco': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Endereço'}),
            'telefone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Telefone'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email'}),
            'descricao': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 4, 
                'placeholder': 'Descrição da empresa (pode ser editada nos projetos)'
            }),
            'razao_social': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Razão Social'}),
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