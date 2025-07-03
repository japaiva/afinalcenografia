# core/services/crewai/tools/svg_generator.py

import json
import logging
import math
from typing import Dict, Any, Optional
from .base_tool import AfinalBaseTool, ToolResult

logger = logging.getLogger(__name__)

class SVGGeneratorTool(AfinalBaseTool):
    """
    Tool genérica para gerar arquivos SVG
    
    Configurável via parâmetros para diferentes tipos de uso:
    - Plantas baixas
    - Diagramas
    - Layouts
    - Esquemas técnicos
    """
    
    def __init__(self, verbose_manager=None, **config):
        super().__init__(
            name="svg_generator",
            description="""
            Gera arquivos SVG baseado em dados estruturados.
            
            ENTRADA OBRIGATÓRIA:
            - dados: Dados estruturados para geração do SVG
            
            ENTRADA OPCIONAL:
            - tipo: Tipo de SVG (planta_baixa, diagrama, layout, tecnico)
            - config: Configurações específicas do SVG
            
            RETORNA: Código SVG completo
            """,
            verbose_manager=verbose_manager
        )
        
        # 🔧 CORREÇÃO: Garantir que logger seja atributo público
        self.logger = logging.getLogger(f"svg_generator_tool")
        
        # Configurações padrão
        self.config = {
            'width': 800,
            'height': 600,
            'margin': 50,
            'background_color': '#f8f9fa',
            'style': 'technical',  # technical, artistic, minimal
            **config  # Sobrescrever com configurações fornecidas
        }
        
        self.logger.info(f"🛠️ SVGGeneratorTool configurada: {self.config}")
    
    def _execute(self, **kwargs) -> ToolResult:
        """
        Executa a geração do SVG
        """
        try:
            # Validar entrada obrigatória
            input_data = self._validate_input(kwargs, ['dados'])
            
            # Extrair dados
            dados = input_data.get('dados')
            tipo_svg = input_data.get('tipo', 'generico')
            config_adicional = input_data.get('config', {})
            
            # Log do progresso
            if self.verbose_manager:
                self.verbose_manager.log_step(f"🎨 Gerando SVG tipo '{tipo_svg}'", "tool")
            
            # Aplicar configurações adicionais
            config_final = {**self.config, **config_adicional}
            
            # Gerar SVG baseado no tipo
            svg_content = self._gerar_svg_por_tipo(dados, tipo_svg, config_final)
            
            # Validar SVG gerado
            if not svg_content or len(svg_content) < 100:
                raise ValueError("SVG gerado inválido ou muito pequeno")
            
            # Log de sucesso
            if self.verbose_manager:
                self.verbose_manager.log_step(f"✅ SVG gerado: {len(svg_content)} caracteres", "tool")
            
            return self._create_success_result(
                data=svg_content,
                metadata={
                    'svg_size': len(svg_content),
                    'tipo': tipo_svg,
                    'config_used': config_final
                }
            )
            
        except Exception as e:
            return self._create_error_result(e, "Geração de SVG")
    
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
        Gera SVG específico para plantas baixas
        """
        # Extrair dados do estande/projeto
        estande = dados.get('estande', {})
        projeto = dados.get('projeto', {})
        
        frente = float(estande.get('medida_frente', 10))
        fundo = float(estande.get('medida_fundo', 10))
        area_total = float(estande.get('area_total', frente * fundo))
        
        # Calcular dimensões em pixels
        dimensoes = self._calcular_dimensoes_pixel(frente, fundo, config)
        
        return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg width="{config['width']}" height="{config['height']}" viewBox="0 0 {config['width']} {config['height']}" xmlns="http://www.w3.org/2000/svg">
  <!-- Fundo -->
  <rect x="0" y="0" width="{config['width']}" height="{config['height']}" fill="{config['background_color']}"/>
  
  <!-- Título -->
  <text x="{config['width']/2}" y="30" text-anchor="middle" font-family="Arial" font-size="16" font-weight="bold" fill="#333">
    🏗️ PLANTA BAIXA - {projeto.get('nome', 'Projeto')}
  </text>
  
  <!-- Contorno do estande -->
  <rect x="{dimensoes['start_x']}" y="{dimensoes['start_y']}" 
        width="{dimensoes['width_pixel']}" height="{dimensoes['height_pixel']}" 
        fill="white" stroke="#333" stroke-width="3"/>
  
  <!-- Área central -->
  <circle cx="{dimensoes['center_x']}" cy="{dimensoes['center_y']}" 
          r="30" fill="#007bff" fill-opacity="0.1" stroke="#007bff" stroke-width="2"/>
  <text x="{dimensoes['center_x']}" y="{dimensoes['center_y']}" 
        text-anchor="middle" font-family="Arial" font-size="14" font-weight="bold" fill="#007bff">
    {area_total:.1f} m²
  </text>
  
  <!-- Cotas -->
  <text x="{dimensoes['center_x']}" y="{dimensoes['start_y'] - 10}" 
        text-anchor="middle" font-family="Arial" font-size="12" fill="#666">
    {frente:.1f}m × {fundo:.1f}m
  </text>
  
  <!-- Rodapé -->
  <text x="20" y="{config['height'] - 20}" font-family="Arial" font-size="10" fill="#666">
    🛠️ Gerado por SVGGeneratorTool | {projeto.get('empresa', 'Cliente')}
  </text>
</svg>'''
    
    def _gerar_svg_diagrama(self, dados: Dict, config: Dict) -> str:
        """
        Gera SVG para diagramas
        """
        titulo = dados.get('titulo', 'Diagrama')
        elementos = dados.get('elementos', [])
        
        svg_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg width="{config['width']}" height="{config['height']}" viewBox="0 0 {config['width']} {config['height']}" xmlns="http://www.w3.org/2000/svg">
  <rect x="0" y="0" width="{config['width']}" height="{config['height']}" fill="{config['background_color']}"/>
  
  <text x="{config['width']/2}" y="30" text-anchor="middle" font-family="Arial" font-size="16" font-weight="bold" fill="#333">
    📊 {titulo}
  </text>'''
        
        # Adicionar elementos do diagrama
        y_pos = 80
        for i, elemento in enumerate(elementos):
            svg_content += f'''
  <rect x="50" y="{y_pos}" width="200" height="40" fill="#e3f2fd" stroke="#1976d2" stroke-width="1"/>
  <text x="150" y="{y_pos + 25}" text-anchor="middle" font-family="Arial" font-size="12" fill="#333">
    {elemento.get('nome', f'Elemento {i+1}')}
  </text>'''
            y_pos += 60
        
        svg_content += '</svg>'
        return svg_content
    
    def _gerar_svg_layout(self, dados: Dict, config: Dict) -> str:
        """
        Gera SVG para layouts genéricos
        """
        titulo = dados.get('titulo', 'Layout')
        areas = dados.get('areas', [])
        
        return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg width="{config['width']}" height="{config['height']}" viewBox="0 0 {config['width']} {config['height']}" xmlns="http://www.w3.org/2000/svg">
  <rect x="0" y="0" width="{config['width']}" height="{config['height']}" fill="{config['background_color']}"/>
  
  <text x="{config['width']/2}" y="30" text-anchor="middle" font-family="Arial" font-size="16" font-weight="bold" fill="#333">
    🎨 {titulo}
  </text>
  
  <rect x="100" y="60" width="600" height="400" fill="white" stroke="#333" stroke-width="2"/>
  
  <text x="{config['width']/2}" y="{config['height']/2}" text-anchor="middle" font-family="Arial" font-size="14" fill="#666">
    Layout com {len(areas)} áreas
  </text>
</svg>'''
    
    def _gerar_svg_tecnico(self, dados: Dict, config: Dict) -> str:
        """
        Gera SVG para desenhos técnicos
        """
        titulo = dados.get('titulo', 'Desenho Técnico')
        especificacoes = dados.get('especificacoes', [])
        
        return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg width="{config['width']}" height="{config['height']}" viewBox="0 0 {config['width']} {config['height']}" xmlns="http://www.w3.org/2000/svg">
  <rect x="0" y="0" width="{config['width']}" height="{config['height']}" fill="white"/>
  
  <text x="{config['width']/2}" y="30" text-anchor="middle" font-family="Arial" font-size="16" font-weight="bold" fill="#333">
    ⚙️ {titulo}
  </text>
  
  <rect x="50" y="50" width="700" height="450" fill="none" stroke="#333" stroke-width="1"/>
  
  <text x="60" y="480" font-family="Arial" font-size="10" fill="#666">
    Especificações técnicas: {len(especificacoes)} itens
  </text>
</svg>'''
    
    def _gerar_svg_generico(self, dados: Dict, config: Dict) -> str:
        """
        Gera SVG genérico para dados não estruturados
        """
        titulo = dados.get('titulo', 'SVG Gerado')
        conteudo = dados.get('conteudo', 'Conteúdo não especificado')
        
        return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg width="{config['width']}" height="{config['height']}" viewBox="0 0 {config['width']} {config['height']}" xmlns="http://www.w3.org/2000/svg">
  <rect x="0" y="0" width="{config['width']}" height="{config['height']}" fill="{config['background_color']}"/>
  
  <text x="{config['width']/2}" y="30" text-anchor="middle" font-family="Arial" font-size="16" font-weight="bold" fill="#333">
    📄 {titulo}
  </text>
  
  <rect x="50" y="60" width="{config['width'] - 100}" height="{config['height'] - 120}" 
        fill="white" stroke="#333" stroke-width="2"/>
  
  <text x="{config['width']/2}" y="{config['height']/2}" text-anchor="middle" font-family="Arial" font-size="14" fill="#666">
    {str(conteudo)[:50]}...
  </text>
  
  <text x="20" y="{config['height'] - 20}" font-family="Arial" font-size="10" fill="#666">
    🛠️ Gerado por SVGGeneratorTool
  </text>
</svg>'''
    
    def _calcular_dimensoes_pixel(self, frente: float, fundo: float, config: Dict) -> Dict:
        """
        Calcula dimensões em pixels mantendo proporção
        """
        # Área disponível
        area_width = config['width'] - (2 * config['margin'])
        area_height = config['height'] - (2 * config['margin']) - 120  # espaço para textos
        
        # Escala
        escala_x = area_width / frente if frente > 0 else 20
        escala_y = area_height / fundo if fundo > 0 else 20
        escala = min(escala_x, escala_y, 20)  # máximo 20px por metro
        
        # Dimensões em pixels
        width_pixel = frente * escala
        height_pixel = fundo * escala
        
        # Centralizar
        start_x = (config['width'] - width_pixel) / 2
        start_y = (config['height'] - height_pixel) / 2 + 60
        
        return {
            'width_pixel': width_pixel,
            'height_pixel': height_pixel,
            'start_x': start_x,
            'start_y': start_y,
            'center_x': start_x + width_pixel / 2,
            'center_y': start_y + height_pixel / 2,
            'escala': escala
        }