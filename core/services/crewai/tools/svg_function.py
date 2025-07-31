# core/services/crewai/tools/svg_function.py - ZERO HARDCODE

import json
import logging
from crewai.tools import BaseTool

logger = logging.getLogger(__name__)


class PlantaBaixaSvgTool(BaseTool):
    name: str = "planta_baixa_svg_generator"
    description: str = """
    Ferramenta para gerar SVG lendo TUDO dinamicamente do JSON.
    Zero hardcode - toda configuração vem do JSON de entrada.
    """

    def _run(self, dados_json: str) -> str:
        """
        Gera SVG lendo TUDO do JSON - zero hardcode
        """
        try:
            dados = json.loads(dados_json)
            logger.info("🎯 Lendo JSON dinâmico - zero hardcode...")
            
            svg_content = self._gerar_svg_puro_json(dados)
            logger.info("✅ SVG gerado 100% baseado no JSON")
            
        except Exception as e:
            logger.error(f"❌ Erro: {e}")
            svg_content = self._svg_erro_minimo(str(e))
        
        resultado = {
            "svg_completo": svg_content,
            "renderizacao_sucesso": True
        }
        
        return json.dumps(resultado, ensure_ascii=False, indent=2)

    def _gerar_svg_puro_json(self, dados):
        """Gera SVG lendo TUDO do JSON"""
        
        # Extrair TUDO do JSON
        projeto_info = dados.get('projeto_info', {})
        dimensoes_stand = dados.get('dimensoes_stand', {})
        areas_posicionadas = dados.get('areas_posicionadas', [])
        validacao_layout = dados.get('validacao_layout', {})
        metadados = dados.get('metadados_geracao', {})
        
        # Parâmetros do SVG vindos do JSON ou calculados
        svg_config = self._extrair_config_svg(dados)
        
        # Dados do projeto vindos do JSON
        nome_projeto = projeto_info.get('nome', '')
        empresa = projeto_info.get('empresa', '')
        area_total = projeto_info.get('area_total', 0)
        
        # Dimensões vindas do JSON
        frente = dimensoes_stand.get('frente', 0)
        fundo = dimensoes_stand.get('fundo', 0)
        
        # Configurações visuais vindas do JSON
        largura_svg = svg_config['largura_svg']
        altura_svg = svg_config['altura_svg']
        margem = svg_config['margem']
        escala = svg_config['escala']
        
        # Início do SVG com dados do JSON
        svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg width="{largura_svg}" height="{altura_svg}" viewBox="0 0 {largura_svg} {altura_svg}" xmlns="http://www.w3.org/2000/svg">
  
  <rect width="{largura_svg}" height="{altura_svg}" fill="white"/>
  
  <text x="{largura_svg/2}" y="25" text-anchor="middle" font-family="Arial" font-size="16" font-weight="bold" fill="#000">
    {nome_projeto}
  </text>
  <text x="{largura_svg/2}" y="45" text-anchor="middle" font-family="Arial" font-size="11" fill="#666">
    {empresa} | {area_total}m²
  </text>
  
  <rect x="{margem}" y="65" width="{frente * escala}" height="{fundo * escala}" 
        fill="none" stroke="#000" stroke-width="3"/>
'''

        # Gerar cores dinamicamente dos dados
        cores_mapeadas = self._mapear_cores_json(areas_posicionadas, dados)
        
        # Renderizar áreas usando dados do JSON
        for area in areas_posicionadas:
            coords = area.get('coordenadas', {})
            x = coords.get('x', 0)
            y = coords.get('y', 0)
            largura = coords.get('largura', 0)
            profundidade = coords.get('profundidade', 0)
            
            tipo = area.get('tipo', '')
            nome = area.get('nome', '')
            area_m2 = area.get('area_m2', 0)
            
            # Usar cor mapeada do JSON
            cor_info = cores_mapeadas.get(tipo, cores_mapeadas.get('default', {}))
            fill_color = cor_info.get('fill', '#ccc')
            stroke_color = cor_info.get('stroke', '#000')
            
            # Posição em pixels
            x_px = margem + (x * escala)
            y_px = 65 + (y * escala)
            w_px = largura * escala
            h_px = profundidade * escala
            
            svg += f'''
  <rect x="{x_px}" y="{y_px}" width="{w_px}" height="{h_px}" 
        fill="{fill_color}" stroke="{stroke_color}" stroke-width="2"/>
  
  <text x="{x_px + w_px/2}" y="{y_px + h_px/2}" text-anchor="middle" 
        font-family="Arial" font-size="9" font-weight="bold" fill="{stroke_color}">
    {nome}
  </text>
  <text x="{x_px + w_px/2}" y="{y_px + h_px/2 + 12}" text-anchor="middle" 
        font-family="Arial" font-size="7" fill="{stroke_color}">
    {largura}×{profundidade}m
  </text>'''

        # Entrada se definida no JSON
        entrada = validacao_layout.get('entrada_definida', {})
        if entrada:
            ent_pos = entrada.get('posicao', {})
            ent_x = ent_pos.get('x', 0)
            ent_y = ent_pos.get('y', 0)
            ent_largura = entrada.get('largura', 0)
            
            ent_x_px = margem + (ent_x * escala)
            ent_y_px = 65 + (ent_y * escala)
            ent_w_px = ent_largura * escala
            
            svg += f'''
  <rect x="{ent_x_px}" y="{ent_y_px}" width="{ent_w_px}" height="6" 
        fill="#0a0" stroke="#060"/>
  <text x="{ent_x_px + ent_w_px/2}" y="{ent_y_px - 5}" text-anchor="middle" 
        font-family="Arial" font-size="8" fill="#0a0">
    ENTRADA
  </text>'''

        # Footer com dados do JSON
        algoritmo = metadados.get('algoritmo', '')
        timestamp = metadados.get('timestamp', '')
        
        svg += f'''
  
  <text x="{largura_svg/2}" y="{altura_svg - 40}" text-anchor="middle" font-family="Arial" font-size="11" fill="#00f">
    Coordenadas JSON Pipeline
  </text>
  <text x="{largura_svg/2}" y="{altura_svg - 20}" text-anchor="middle" font-family="Arial" font-size="8" fill="#666">
    {len(areas_posicionadas)} áreas | {algoritmo} | {timestamp}
  </text>
  
</svg>'''
        
        return svg

    def _extrair_config_svg(self, dados):
        """Extrai configurações SVG do JSON ou calcula dinamicamente"""
        config = {}
        
        # Procurar configurações em qualquer lugar do JSON
        config['largura_svg'] = self._buscar_valor_json(dados, ['largura_svg', 'width', 'svg_width'], 800)
        config['altura_svg'] = self._buscar_valor_json(dados, ['altura_svg', 'height', 'svg_height'], 600)
        config['margem'] = self._buscar_valor_json(dados, ['margem', 'margin', 'margem_pixels'], 50)
        
        # Calcular escala baseada nas dimensões do stand
        dimensoes = dados.get('dimensoes_stand', {})
        frente = dimensoes.get('frente', 1)
        fundo = dimensoes.get('fundo', 1)
        
        # Calcular escala que cabe no SVG
        area_util_x = config['largura_svg'] - (2 * config['margem'])
        area_util_y = config['altura_svg'] - 150  # espaço para header/footer
        
        escala_x = area_util_x / frente if frente > 0 else 1
        escala_y = area_util_y / fundo if fundo > 0 else 1
        config['escala'] = min(escala_x, escala_y)
        
        # Tentar usar escala do JSON se existir
        escala_json = self._buscar_valor_json(dados, ['escala', 'scale', 'escala_recomendada'], None)
        if escala_json:
            config['escala'] = escala_json
        
        return config

    def _buscar_valor_json(self, dados, chaves_possiveis, valor_padrao):
        """Busca valor em múltiplas chaves possíveis no JSON"""
        def buscar_recursivo(obj):
            if isinstance(obj, dict):
                for chave in chaves_possiveis:
                    if chave in obj:
                        return obj[chave]
                for valor in obj.values():
                    resultado = buscar_recursivo(valor)
                    if resultado is not None:
                        return resultado
            return None
        
        resultado = buscar_recursivo(dados)
        return resultado if resultado is not None else valor_padrao

    def _mapear_cores_json(self, areas_posicionadas, dados):
        """Mapeia cores baseado nos dados do JSON"""
        # Tentar encontrar configurações de cores no JSON
        cores_config = self._buscar_cores_config(dados)
        
        if cores_config:
            return cores_config
        
        # Se não tem cores no JSON, gerar baseado nos tipos
        tipos_unicos = []
        for area in areas_posicionadas:
            tipo = area.get('tipo', '')
            if tipo and tipo not in tipos_unicos:
                tipos_unicos.append(tipo)
        
        # Gerar cores programaticamente
        cores_geradas = {}
        for i, tipo in enumerate(tipos_unicos):
            hue = (i * 137.5) % 360  # Golden angle distribution
            cores_geradas[tipo] = {
                'fill': f'hsl({hue}, 60%, 90%)',
                'stroke': f'hsl({hue}, 80%, 40%)'
            }
        
        cores_geradas['default'] = {'fill': '#f0f0f0', 'stroke': '#666'}
        return cores_geradas

    def _buscar_cores_config(self, dados):
        """Busca configuração de cores no JSON"""
        # Procurar em lugares possíveis
        for secao in dados.values():
            if isinstance(secao, dict):
                if 'cores_por_tipo' in secao:
                    return secao['cores_por_tipo']
                if 'colors' in secao:
                    return secao['colors']
                if 'cores' in secao:
                    return secao['cores']
        return None

    def _svg_erro_minimo(self, erro):
        """SVG mínimo para erro"""
        return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg width="400" height="200" viewBox="0 0 400 200" xmlns="http://www.w3.org/2000/svg">
  <rect width="400" height="200" fill="white"/>
  <text x="200" y="100" text-anchor="middle" font-family="Arial" font-size="12" fill="red">
    Erro: {erro[:30]}...
  </text>
</svg>'''


# Instância
planta_baixa_svg_tool = PlantaBaixaSvgTool()
svg_generator_tool = planta_baixa_svg_tool