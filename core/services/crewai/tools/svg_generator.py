# core/services/crewai/tools/svg_generator.py - CORRIGIDA FINAL

import json
import logging
import math
from typing import Dict, Any, Optional, Type
from langchain.tools import BaseTool
from pydantic import BaseModel, Field

# Logger global para evitar conflito com LangChain
svg_logger = logging.getLogger(__name__)

class SVGGeneratorInput(BaseModel):
    """Schema de entrada para SVGGeneratorTool"""
    dados: Dict[str, Any] = Field(description="Dados estruturados para geração do SVG")
    tipo: str = Field(default="planta_baixa", description="Tipo de SVG: planta_baixa, diagrama, layout, tecnico")
    config: Optional[Dict[str, Any]] = Field(default=None, description="Configurações específicas do SVG")

class SVGGeneratorTool(BaseTool):
    """
    Tool LangChain compatível para gerar arquivos SVG
    
    Esta tool é específica para plantas baixas de estandes de feira,
    mas pode ser configurada para outros tipos de SVG.
    """
    
    name: str = "svg_generator"
    description: str = """
    Gera arquivos SVG baseado em dados estruturados de plantas baixas.
    
    ENTRADA OBRIGATÓRIA:
    - dados: Dados estruturados do briefing/projeto para geração do SVG
    
    ENTRADA OPCIONAL:
    - tipo: Tipo de SVG (planta_baixa, diagrama, layout, tecnico)
    - config: Configurações específicas do SVG
    
    RETORNA: Código SVG completo válido
    
    EXEMPLO DE USO:
    Use esta tool quando precisar gerar um arquivo SVG de planta baixa 
    baseado nos dados do briefing processado pelos agentes anteriores.
    """
    args_schema: Type[BaseModel] = SVGGeneratorInput
    
    def __init__(self, verbose_manager=None, **kwargs):
        # 🔧 CORREÇÃO: Não definir logger como atributo da instância
        super().__init__(**kwargs)
        
        # Usar variável interna sem conflito
        self._verbose_manager = verbose_manager
        self._execution_count = 0
        
        # Configurações padrão
        self._config_padrao = {
            'width': 800,
            'height': 600,
            'margin': 50,
            'background_color': '#f8f9fa',
            'style': 'technical'
        }
        
        if self._verbose_manager:
            self._verbose_manager.log_step("🔧 SVGGeneratorTool inicializada", "tool")
        
        svg_logger.info("🛠️ SVGGeneratorTool configurada")
    
    def _run(self, dados: Dict[str, Any], tipo: str = "planta_baixa", config: Optional[Dict[str, Any]] = None) -> str:
        """
        Executa a geração do SVG
        
        Args:
            dados: Dados estruturados do briefing
            tipo: Tipo de SVG a gerar
            config: Configurações adicionais
            
        Returns:
            String contendo o código SVG completo
        """
        try:
            self._execution_count += 1
            
            if self._verbose_manager:
                self._verbose_manager.log_step(f"🎨 Iniciando geração SVG tipo '{tipo}'", "tool")
            
            # Validar entrada
            if not dados:
                raise ValueError("Dados obrigatórios não fornecidos")
            
            # Aplicar configurações
            config_final = {**self._config_padrao, **(config or {})}
            
            # Log dos dados recebidos
            svg_logger.info(f"📊 Dados recebidos: {len(str(dados))} caracteres")
            if self._verbose_manager:
                self._verbose_manager.log_step("📊 Dados do briefing processados", "tool")
            
            # Gerar SVG baseado no tipo
            svg_content = self._gerar_svg_por_tipo(dados, tipo, config_final)
            
            # Validar SVG gerado
            if not svg_content or len(svg_content) < 100:
                raise ValueError("SVG gerado inválido ou muito pequeno")
            
            # Log de sucesso
            if self._verbose_manager:
                self._verbose_manager.log_step(f"✅ SVG gerado: {len(svg_content)} caracteres", "tool")
            
            svg_logger.info(f"✅ SVG gerado com sucesso: {len(svg_content)} caracteres")
            
            return svg_content
            
        except Exception as e:
            error_msg = f"Erro na geração SVG: {str(e)}"
            svg_logger.error(f"❌ {error_msg}")
            
            if self._verbose_manager:
                self._verbose_manager.log_error(error_msg)
            
            # Retornar SVG de erro em vez de falhar
            return self._gerar_svg_erro(str(e))
    
    def _gerar_svg_por_tipo(self, dados: Dict, tipo: str, config: Dict) -> str:
        """
        Gera SVG baseado no tipo especificado
        """
        if tipo == 'planta_baixa':
            return self._gerar_svg_planta_baixa(dados, config)
        elif tipo == 'diagrama':
            return self._gerar_svg_diagrama(dados, config)
        elif tipo == 'layout':
            return self._gerar_svg_layout(dados, config)
        elif tipo == 'tecnico':
            return self._gerar_svg_tecnico(dados, config)
        else:
            return self._gerar_svg_generico(dados, config)
    
    def _gerar_svg_planta_baixa(self, dados: Dict, config: Dict) -> str:
        """
        Gera SVG específico para plantas baixas de estandes
        """
        try:
            # Extrair dados do briefing
            briefing = dados.get('briefing_completo', dados)
            estande = briefing.get('estande', {})
            projeto = briefing.get('projeto', {})
            divisoes = briefing.get('divisoes_funcionais', {})
            
            # Dimensões do estande
            frente = float(estande.get('medida_frente', 10))
            fundo = float(estande.get('medida_fundo', 10))
            area_total = float(estande.get('area_total', frente * fundo))
            tipo_stand = estande.get('tipo_stand', 'ilha')
            
            # Calcular dimensões em pixels
            dimensoes = self._calcular_dimensoes_pixel(frente, fundo, config)
            
            # Cores por tipo de stand
            cor_contorno = {
                'ilha': '#007bff',
                'esquina': '#28a745',
                'corredor': '#ffc107',
                'ponta_de_ilha': '#17a2b8'
            }.get(tipo_stand, '#6c757d')
            
            # Começar SVG
            svg_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg width="{config['width']}" height="{config['height']}" viewBox="0 0 {config['width']} {config['height']}" xmlns="http://www.w3.org/2000/svg">
  <!-- Fundo -->
  <rect x="0" y="0" width="{config['width']}" height="{config['height']}" fill="{config['background_color']}"/>
  
  <!-- Título do Projeto -->
  <text x="{config['width']/2}" y="30" text-anchor="middle" font-family="Arial" font-size="18" font-weight="bold" fill="#333">
    🏗️ {projeto.get('nome', 'Projeto Estande')}
  </text>
  
  <!-- Subtítulo -->
  <text x="{config['width']/2}" y="50" text-anchor="middle" font-family="Arial" font-size="14" fill="#666">
    {projeto.get('empresa', 'Cliente')} | {tipo_stand.replace('_', ' ').title()}
  </text>
  
  <!-- Contorno principal do estande -->
  <rect x="{dimensoes['start_x']}" y="{dimensoes['start_y']}" 
        width="{dimensoes['width_pixel']}" height="{dimensoes['height_pixel']}" 
        fill="white" stroke="{cor_contorno}" stroke-width="4"/>
  
  <!-- Cotas principais -->
  <text x="{dimensoes['center_x']}" y="{dimensoes['start_y'] - 15}" 
        text-anchor="middle" font-family="Arial" font-size="12" font-weight="bold" fill="#333">
    {frente:.1f}m × {fundo:.1f}m = {area_total:.1f}m²
  </text>'''
            
            # Adicionar divisões funcionais
            svg_content += self._adicionar_divisoes_funcionais(divisoes, dimensoes)
            
            # Adicionar legenda
            svg_content += self._adicionar_legenda(divisoes, config)
            
            # Rodapé
            svg_content += f'''
  
  <!-- Rodapé -->
  <text x="20" y="{config['height'] - 40}" font-family="Arial" font-size="10" fill="#666">
    🛠️ Gerado por CrewAI | SVGGeneratorTool v2.0
  </text>
  <text x="20" y="{config['height'] - 25}" font-family="Arial" font-size="10" fill="#666">
    📋 Briefing processado automaticamente
  </text>
  <text x="20" y="{config['height'] - 10}" font-family="Arial" font-size="10" fill="#666">
    📐 Escala: {dimensoes['escala']:.1f} pixels/metro
  </text>
</svg>'''
            
            return svg_content
            
        except Exception as e:
            svg_logger.error(f"❌ Erro ao gerar planta baixa: {e}")
            return self._gerar_svg_erro(f"Erro na planta baixa: {e}")
    
    def _adicionar_divisoes_funcionais(self, divisoes: Dict, dimensoes: Dict) -> str:
        """Adiciona divisões funcionais ao SVG"""
        svg_divisoes = ""
        
        try:
            # Coletar todas as áreas
            todas_areas = []
            
            # Áreas de exposição
            for area in divisoes.get('areas_exposicao', []):
                todas_areas.append({
                    'tipo': 'exposicao',
                    'metragem': area.get('metragem', 0),
                    'cor': '#e3f2fd',
                    'stroke': '#1976d2'
                })
            
            # Salas de reunião
            for sala in divisoes.get('salas_reuniao', []):
                todas_areas.append({
                    'tipo': 'reuniao',
                    'metragem': sala.get('metragem', 0),
                    'cor': '#fff3e0',
                    'stroke': '#f57c00'
                })
            
            # Copas
            for copa in divisoes.get('copas', []):
                todas_areas.append({
                    'tipo': 'copa',
                    'metragem': copa.get('metragem', 0),
                    'cor': '#e8f5e8',
                    'stroke': '#388e3c'
                })
            
            # Depósitos
            for deposito in divisoes.get('depositos', []):
                todas_areas.append({
                    'tipo': 'deposito',
                    'metragem': deposito.get('metragem', 0),
                    'cor': '#f3e5f5',
                    'stroke': '#7b1fa2'
                })
            
            # Distribuir áreas no espaço
            if todas_areas:
                svg_divisoes += self._distribuir_areas_no_espaco(todas_areas, dimensoes)
                
        except Exception as e:
            svg_logger.warning(f"⚠️ Erro ao adicionar divisões: {e}")
        
        return svg_divisoes
    
    def _distribuir_areas_no_espaco(self, areas: list, dimensoes: Dict) -> str:
        """Distribui áreas funcionais no espaço do estande"""
        svg_areas = ""
        
        try:
            if not areas:
                return svg_areas
            
            # Área disponível para divisões (deixar margem)
            margin = 20
            area_width = dimensoes['width_pixel'] - (2 * margin)
            area_height = dimensoes['height_pixel'] - (2 * margin)
            
            # Calcular layout em grid
            num_areas = len(areas)
            cols = math.ceil(math.sqrt(num_areas))
            rows = math.ceil(num_areas / cols)
            
            cell_width = area_width / cols
            cell_height = area_height / rows
            
            for i, area in enumerate(areas):
                row = i // cols
                col = i % cols
                
                x = dimensoes['start_x'] + margin + (col * cell_width)
                y = dimensoes['start_y'] + margin + (row * cell_height)
                
                # Ajustar tamanho baseado na metragem
                metragem = float(area.get('metragem', 1))
                size_factor = min(1.0, max(0.3, metragem / 50))  # Normalizar entre 30% e 100%
                
                rect_width = cell_width * 0.8 * size_factor
                rect_height = cell_height * 0.8 * size_factor
                
                # Centralizar na célula
                rect_x = x + (cell_width - rect_width) / 2
                rect_y = y + (cell_height - rect_height) / 2
                
                svg_areas += f'''
  <!-- Área {area['tipo']} -->
  <rect x="{rect_x:.1f}" y="{rect_y:.1f}" 
        width="{rect_width:.1f}" height="{rect_height:.1f}"
        fill="{area['cor']}" stroke="{area['stroke']}" stroke-width="2" rx="4"/>
  <text x="{rect_x + rect_width/2:.1f}" y="{rect_y + rect_height/2 - 5:.1f}" 
        text-anchor="middle" font-family="Arial" font-size="10" font-weight="bold" fill="#333">
    {area['tipo'].title()}
  </text>
  <text x="{rect_x + rect_width/2:.1f}" y="{rect_y + rect_height/2 + 8:.1f}" 
        text-anchor="middle" font-family="Arial" font-size="9" fill="#666">
    {metragem:.1f}m²
  </text>'''
                
        except Exception as e:
            svg_logger.warning(f"⚠️ Erro ao distribuir áreas: {e}")
        
        return svg_areas
    
    def _adicionar_legenda(self, divisoes: Dict, config: Dict) -> str:
        """Adiciona legenda ao SVG"""
        legenda = ""
        
        try:
            # Contar divisões
            total_areas = (
                len(divisoes.get('areas_exposicao', [])) +
                len(divisoes.get('salas_reuniao', [])) +
                len(divisoes.get('copas', [])) +
                len(divisoes.get('depositos', []))
            )
            
            if total_areas > 0:
                legenda_y = config['height'] - 120
                
                legenda = f'''
  <!-- Legenda -->
  <rect x="{config['width'] - 200}" y="{legenda_y}" width="180" height="80" 
        fill="white" stroke="#ddd" stroke-width="1" rx="4"/>
  <text x="{config['width'] - 190}" y="{legenda_y + 15}" 
        font-family="Arial" font-size="12" font-weight="bold" fill="#333">
    📊 Divisões Funcionais
  </text>'''
                
                y_pos = legenda_y + 30
                if divisoes.get('areas_exposicao'):
                    legenda += f'''
  <rect x="{config['width'] - 185}" y="{y_pos}" width="12" height="8" fill="#e3f2fd" stroke="#1976d2"/>
  <text x="{config['width'] - 168}" y="{y_pos + 6}" font-family="Arial" font-size="9" fill="#333">
    Exposição ({len(divisoes['areas_exposicao'])})
  </text>'''
                    y_pos += 12
                
                if divisoes.get('salas_reuniao'):
                    legenda += f'''
  <rect x="{config['width'] - 185}" y="{y_pos}" width="12" height="8" fill="#fff3e0" stroke="#f57c00"/>
  <text x="{config['width'] - 168}" y="{y_pos + 6}" font-family="Arial" font-size="9" fill="#333">
    Reunião ({len(divisoes['salas_reuniao'])})
  </text>'''
                    y_pos += 12
                
                if divisoes.get('copas'):
                    legenda += f'''
  <rect x="{config['width'] - 185}" y="{y_pos}" width="12" height="8" fill="#e8f5e8" stroke="#388e3c"/>
  <text x="{config['width'] - 168}" y="{y_pos + 6}" font-family="Arial" font-size="9" fill="#333">
    Copa ({len(divisoes['copas'])})
  </text>'''
                    y_pos += 12
                
                if divisoes.get('depositos'):
                    legenda += f'''
  <rect x="{config['width'] - 185}" y="{y_pos}" width="12" height="8" fill="#f3e5f5" stroke="#7b1fa2"/>
  <text x="{config['width'] - 168}" y="{y_pos + 6}" font-family="Arial" font-size="9" fill="#333">
    Depósito ({len(divisoes['depositos'])})
  </text>'''
                
        except Exception as e:
            svg_logger.warning(f"⚠️ Erro ao criar legenda: {e}")
        
        return legenda
    
    def _calcular_dimensoes_pixel(self, frente: float, fundo: float, config: Dict) -> Dict:
        """
        Calcula dimensões em pixels mantendo proporção
        """
        # Área disponível
        area_width = config['width'] - (2 * config['margin'])
        area_height = config['height'] - (2 * config['margin']) - 140  # espaço para textos e legenda
        
        # Escala
        escala_x = area_width / frente if frente > 0 else 20
        escala_y = area_height / fundo if fundo > 0 else 20
        escala = min(escala_x, escala_y, 25)  # máximo 25px por metro
        
        # Dimensões em pixels
        width_pixel = frente * escala
        height_pixel = fundo * escala
        
        # Centralizar
        start_x = (config['width'] - width_pixel) / 2
        start_y = (config['height'] - height_pixel) / 2 + 20  # offset para título
        
        return {
            'width_pixel': width_pixel,
            'height_pixel': height_pixel,
            'start_x': start_x,
            'start_y': start_y,
            'center_x': start_x + width_pixel / 2,
            'center_y': start_y + height_pixel / 2,
            'escala': escala
        }
    
    def _gerar_svg_erro(self, erro: str) -> str:
        """Gera SVG de erro quando algo falha"""
        return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg width="600" height="400" viewBox="0 0 600 400" xmlns="http://www.w3.org/2000/svg">
  <rect x="0" y="0" width="600" height="400" fill="#fff5f5"/>
  
  <text x="300" y="50" text-anchor="middle" font-family="Arial" font-size="18" font-weight="bold" fill="#dc3545">
    ❌ Erro na Geração SVG
  </text>
  
  <rect x="50" y="80" width="500" height="200" fill="white" stroke="#dc3545" stroke-width="2" rx="8"/>
  
  <text x="300" y="150" text-anchor="middle" font-family="Arial" font-size="14" fill="#333">
    Erro: {erro[:50]}...
  </text>
  
  <text x="300" y="170" text-anchor="middle" font-family="Arial" font-size="12" fill="#666">
    Verifique os dados do briefing e tente novamente
  </text>
  
  <text x="300" y="350" text-anchor="middle" font-family="Arial" font-size="10" fill="#999">
    🛠️ SVGGeneratorTool | CrewAI Pipeline
  </text>
</svg>'''
    
    # Métodos para outros tipos de SVG (mantidos simples)
    def _gerar_svg_diagrama(self, dados: Dict, config: Dict) -> str:
        """Gera SVG para diagramas"""
        return self._gerar_svg_generico(dados, config, "📊 Diagrama")
    
    def _gerar_svg_layout(self, dados: Dict, config: Dict) -> str:
        """Gera SVG para layouts"""
        return self._gerar_svg_generico(dados, config, "🎨 Layout")
    
    def _gerar_svg_tecnico(self, dados: Dict, config: Dict) -> str:
        """Gera SVG técnico"""
        return self._gerar_svg_generico(dados, config, "⚙️ Desenho Técnico")
    
    def _gerar_svg_generico(self, dados: Dict, config: Dict, titulo: str = "📄 SVG Gerado") -> str:
        """Gera SVG genérico"""
        return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg width="{config['width']}" height="{config['height']}" viewBox="0 0 {config['width']} {config['height']}" xmlns="http://www.w3.org/2000/svg">
  <rect x="0" y="0" width="{config['width']}" height="{config['height']}" fill="{config['background_color']}"/>
  
  <text x="{config['width']/2}" y="30" text-anchor="middle" font-family="Arial" font-size="16" font-weight="bold" fill="#333">
    {titulo}
  </text>
  
  <rect x="50" y="60" width="{config['width'] - 100}" height="{config['height'] - 120}" 
        fill="white" stroke="#333" stroke-width="2" rx="8"/>
  
  <text x="{config['width']/2}" y="{config['height']/2}" text-anchor="middle" font-family="Arial" font-size="14" fill="#666">
    Dados processados com sucesso
  </text>
  
  <text x="20" y="{config['height'] - 20}" font-family="Arial" font-size="10" fill="#666">
    🛠️ Gerado por SVGGeneratorTool | CrewAI
  </text>
</svg>'''