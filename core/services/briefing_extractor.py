# core/services/briefing_extractor.py

class BriefingExtractor:
    """Extrai dados relevantes do briefing para uso na geração de conceitos visuais"""
    
    def __init__(self, briefing):
        self.briefing = briefing
        self.projeto = briefing.projeto
    
    def extract_data(self):
        """Extrai todos os dados relevantes em um formato estruturado"""
        return {
            'informacoes_basicas': self._extract_basic_info(),
            'caracteristicas_fisicas': self._extract_physical_characteristics(),
            'areas_funcionais': self._extract_functional_areas(),
            'elementos_visuais': self._extract_visual_elements(),
            'objetivos_projeto': self._extract_project_goals(),
        }
    
    def _extract_basic_info(self):
        """Extrai informações básicas do projeto e briefing"""
        return {
            'nome_projeto': self.projeto.nome,
            'tipo_projeto': self.projeto.tipo_projeto,
            'tipo_stand': self.briefing.tipo_stand,
            'feira': self.briefing.feira.nome if self.briefing.feira else self.briefing.nome_evento,
            'orcamento': float(self.briefing.orcamento) if self.briefing.orcamento else None,
        }
    
    def _extract_physical_characteristics(self):
        """Extrai características físicas do estande"""
        area = None
        if self.briefing.area_estande:
            area = float(self.briefing.area_estande)
        elif self.briefing.medida_frente and self.briefing.medida_fundo:
            area = float(self.briefing.medida_frente) * float(self.briefing.medida_fundo)
        
        return {
            'area_total': area,
            'dimensoes': {
                'frente': float(self.briefing.medida_frente) if self.briefing.medida_frente else None,
                'fundo': float(self.briefing.medida_fundo) if self.briefing.medida_fundo else None,
                'lateral_esquerda': float(self.briefing.medida_lateral_esquerda) if self.briefing.medida_lateral_esquerda else None,
                'lateral_direita': float(self.briefing.medida_lateral_direita) if self.briefing.medida_lateral_direita else None,
            },
            'piso_elevado': self.briefing.piso_elevado,
            'tipo_testeira': self.briefing.tipo_testeira,
            'estilo_estande': self.briefing.estilo_estande,
            'material_predominante': self.briefing.material,
        }
    
    def _extract_functional_areas(self):
        """Extrai dados sobre áreas funcionais do estande"""
        # Áreas de exposição
        areas_exposicao = []
        for area in self.briefing.areas_exposicao.all():
            areas_exposicao.append({
                'tem_lounge': area.tem_lounge,
                'tem_vitrine': area.tem_vitrine_exposicao,
                'tem_balcao_recepcao': area.tem_balcao_recepcao,
                'tem_mesas_atendimento': area.tem_mesas_atendimento,
                'tem_balcao_cafe': area.tem_balcao_cafe,
                'tem_balcao_vitrine': area.tem_balcao_vitrine,
                'tem_caixa_vendas': area.tem_caixa_vendas,
                'equipamentos': area.equipamentos,
                'metragem': float(area.metragem) if area.metragem else None,
            })
        
        # Salas de reunião
        salas_reuniao = []
        for sala in self.briefing.salas_reuniao.all():
            salas_reuniao.append({
                'capacidade': sala.capacidade,
                'equipamentos': sala.equipamentos,
                'metragem': float(sala.metragem) if sala.metragem else None,
            })
        
        # Copa e depósito
        copas = [{
            'equipamentos': copa.equipamentos,
            'metragem': float(copa.metragem) if copa.metragem else None,
        } for copa in self.briefing.copas.all()]
        
        depositos = [{
            'equipamentos': dep.equipamentos,
            'metragem': float(dep.metragem) if dep.metragem else None,
        } for dep in self.briefing.depositos.all()]
        
        return {
            'tipo_venda': self.briefing.tipo_venda,
            'tipo_ativacao': self.briefing.tipo_ativacao,
            'areas_exposicao': areas_exposicao,
            'salas_reuniao': salas_reuniao,
            'copas': copas,
            'depositos': depositos,
        }
    
    def _extract_visual_elements(self):
        """Extrai elementos visuais e referências"""
        # Arquivos de referência
        referencias = []
        arquivos_ref = self.briefing.arquivos.filter(tipo='referencia')
        for ref in arquivos_ref:
            referencias.append({
                'nome': ref.nome,
                'observacoes': ref.observacoes,
                'url': ref.arquivo.url if ref.arquivo else None,
            })
        
        return {
            'referencias_dados': self.briefing.referencias_dados,
            'logotipo': self.briefing.logotipo,
            'campanha_dados': self.briefing.campanha_dados,
            'arquivos_referencias': referencias,
        }
    
    def _extract_project_goals(self):
        """Extrai objetivos do projeto"""
        return {
            'objetivo_evento': self.briefing.objetivo_evento,
            'objetivo_estande': self.briefing.objetivo_estande,
        }