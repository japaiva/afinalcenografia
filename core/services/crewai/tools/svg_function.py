# core/services/crewai/tools/svg_function.py - DADOS FIXOS SEM FALLBACK

import json
import logging
from crewai.tools import BaseTool

logger = logging.getLogger(__name__)


class PlantaBaixaSvgTool(BaseTool):
    name: str = "planta_baixa_svg_generator"
    description: str = """
    Ferramenta GARANTIDA para gerar plantas baixas com dados FIXOS.
    IMPOSSÍVEL usar fallback - sempre retorna dados fixos.
    """

    def _run(self, dados_json: str) -> str:
        """
        🔥 GARANTIA ABSOLUTA: Sempre usa dados fixos, NUNCA fallback
        """
        logger.info("🧪 MODO TESTE GARANTIDO - Dados fixos obrigatórios")
        
        # 🔥 FORÇAR uso dos dados fixos - SEM try-catch que pode gerar fallback
        svg_content = self._svg_fixo_garantido()
        
        resultado = {
            "svg_completo": svg_content,
            "svg_metadata": {
                "largura": 800,
                "altura": 600,
                "modo": "dados_fixos_garantido",
                "ambientes_renderizados": 8,
                "nucleo_operacional": True,
                "elementos_especiais": 2,
                "fallback_impossivel": True
            },
            "renderizacao_sucesso": True,
            "observacoes_tecnicas": [
                "🔥 DADOS FIXOS GARANTIDOS - Sem possibilidade de fallback",
                "8 ambientes específicos renderizados",
                "Núcleo operacional (Copa + Depósito) posicionado",
                "2 elementos especiais incluídos",
                "Grid técnico profissional ativo"
            ]
        }
        
        logger.info("✅ SVG com dados fixos garantido gerado")
        return json.dumps(resultado, ensure_ascii=False, indent=2)

    def _svg_fixo_garantido(self):
        """🔥 SVG HARDCODED - impossível falhar"""
        
        # SVG completo hardcoded baseado no exemplo profissional
        svg_hardcoded = '''<?xml version="1.0" encoding="UTF-8"?>
<svg width="800" height="600" viewBox="0 0 800 600" xmlns="http://www.w3.org/2000/svg">
  
  <!-- Background branco -->
  <rect width="800" height="600" fill="white"/>
  
  <!-- Grid técnico de fundo -->
  <defs>
    <pattern id="grid" width="10" height="10" patternUnits="userSpaceOnUse">
      <path d="M 10 0 L 0 0 0 10" fill="none" stroke="#e0e0e0" stroke-width="0.5"/>
    </pattern>
  </defs>
  <rect width="800" height="600" fill="url(#grid)"/>
  
  <!-- Título -->
  <text x="400" y="40" text-anchor="middle" font-family="Arial" font-size="18" font-weight="bold" fill="#2c3e50">
    🧪 PLANTA BAIXA PROFISSIONAL - DADOS FIXOS GARANTIDOS
  </text>
  <text x="400" y="65" text-anchor="middle" font-family="Arial" font-size="12" fill="#7f8c8d">
    Beauty Fair Test | 480m² | MODO TESTE GARANTIDO
  </text>
  
  <!-- Contorno principal do stand -->
  <rect x="115" y="145" width="425" height="280" fill="none" stroke="#2c3e50" stroke-width="4" rx="2"/>
  
  <!-- 🟢 SALAS DE REUNIÃO (Verde claro) -->
  <rect x="200" y="150" width="80" height="50" fill="#d4f6d4" stroke="#4caf50" stroke-width="2" rx="2"/>
  <text x="240" y="175" text-anchor="middle" font-family="Arial" font-size="11" font-weight="bold" fill="#4caf50">REUNIÃO 1</text>
  
  <rect x="285" y="150" width="80" height="50" fill="#d4f6d4" stroke="#4caf50" stroke-width="2" rx="2"/>
  <text x="325" y="175" text-anchor="middle" font-family="Arial" font-size="11" font-weight="bold" fill="#4caf50">REUNIÃO 2</text>
  
  <rect x="370" y="150" width="80" height="50" fill="#d4f6d4" stroke="#4caf50" stroke-width="2" rx="2"/>
  <text x="410" y="175" text-anchor="middle" font-family="Arial" font-size="11" font-weight="bold" fill="#4caf50">REUNIÃO 3</text>
  
  <rect x="455" y="150" width="80" height="50" fill="#d4f6d4" stroke="#4caf50" stroke-width="2" rx="2"/>
  <text x="495" y="175" text-anchor="middle" font-family="Arial" font-size="11" font-weight="bold" fill="#4caf50">REUNIÃO 4</text>
  
  <!-- 🔴 LOUNGE (Rosa) -->
  <rect x="455" y="205" width="80" height="95" fill="#f8d7da" stroke="#dc3545" stroke-width="2" rx="2"/>
  <text x="495" y="252" text-anchor="middle" font-family="Arial" font-size="11" font-weight="bold" fill="#dc3545">LOUNGE</text>
  
  <!-- 🔵 ÁREAS DE EXPOSIÇÃO (Azul claro) -->
  <rect x="120" y="205" width="75" height="145" fill="#cce7ff" stroke="#007bff" stroke-width="2" rx="2"/>
  <text x="157" y="277" text-anchor="middle" font-family="Arial" font-size="11" font-weight="bold" fill="#007bff">ALTA MODA</text>
  
  <rect x="455" y="355" width="80" height="65" fill="#cce7ff" stroke="#007bff" stroke-width="2" rx="2"/>
  <text x="495" y="387" text-anchor="middle" font-family="Arial" font-size="11" font-weight="bold" fill="#007bff">YELLOW</text>
  
  <!-- 🟡 BAR (Amarelo) -->
  <rect x="120" y="305" width="75" height="45" fill="#fff3cd" stroke="#ffc107" stroke-width="2" rx="2"/>
  <text x="157" y="327" text-anchor="middle" font-family="Arial" font-size="11" font-weight="bold" fill="#ffc107">BAR</text>
  
  <!-- 🟣 NÚCLEO OPERACIONAL (Roxo - Copa + Depósito) -->
  <rect x="285" y="355" width="80" height="65" fill="#e1bee7" stroke="#9c27b0" stroke-width="3" rx="2"/>
  <text x="325" y="387" text-anchor="middle" font-family="Arial" font-size="12" font-weight="bold" fill="#9c27b0">COPA</text>
  
  <rect x="370" y="355" width="80" height="65" fill="#e1bee7" stroke="#9c27b0" stroke-width="3" rx="2"/>
  <text x="410" y="387" text-anchor="middle" font-family="Arial" font-size="12" font-weight="bold" fill="#9c27b0">DEPÓSITO</text>
  
  <!-- 🟠 ELEMENTOS ESPECIAIS (Laranja tracejado) -->
  <rect x="200" y="355" width="80" height="65" fill="#ffecb3" stroke="#ff9800" stroke-width="2" stroke-dasharray="3,3" rx="2"/>
  <text x="240" y="387" text-anchor="middle" font-family="Arial" font-size="10" font-weight="bold" fill="#ff9800">LED</text>
  
  <rect x="455" y="305" width="80" height="45" fill="#ffecb3" stroke="#ff9800" stroke-width="2" stroke-dasharray="3,3" rx="2"/>
  <text x="495" y="327" text-anchor="middle" font-family="Arial" font-size="10" font-weight="bold" fill="#ff9800">CARTELA DE CORES</text>
  
  <!-- 🚪 ENTRADA PRINCIPAL (Verde) -->
  <rect x="297" y="137" width="60" height="8" fill="#28a745" stroke="#1e7e34" stroke-width="2"/>
  <text x="327" y="133" text-anchor="middle" font-family="Arial" font-size="9" font-weight="bold" fill="#28a745">ENTRADA</text>
  
  <!-- Seta de entrada -->
  <polygon points="327,128 322,123 332,123" fill="#28a745"/>
  
  <!-- Informações técnicas -->
  <text x="400" y="500" text-anchor="middle" font-family="Arial" font-size="11" fill="#7f8c8d">
    🔥 MODO TESTE GARANTIDO - CAPACIDADE MÁXIMA DO AGENTE 4
  </text>
  <text x="400" y="520" text-anchor="middle" font-family="Arial" font-size="10" fill="#95a5a6">
    8 Ambientes Específicos | Núcleo Operacional | 2 Elementos Especiais
  </text>
  <text x="400" y="540" text-anchor="middle" font-family="Arial" font-size="9" fill="#bdc3c7">
    DADOS HARDCODED - Impossível usar fallback
  </text>
  <text x="400" y="560" text-anchor="middle" font-family="Arial" font-size="8" fill="#dee2e6">
    Grid Técnico | Cores por Categoria | Layout Profissional Garantido
  </text>
  
</svg>'''
        
        logger.info("🔥 SVG hardcoded retornado - 0% chance de fallback")
        return svg_hardcoded


# Instância
planta_baixa_svg_tool = PlantaBaixaSvgTool()
svg_generator_tool = planta_baixa_svg_tool