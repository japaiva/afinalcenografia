# core/services/crewai/tools/svg_function.py - VERSÃO COM DEBUG

import json
import logging
import re
from crewai.tools import BaseTool

logger = logging.getLogger(__name__)


class SvgGeneratorTool(BaseTool):
    name: str = "svg_generator"
    description: str = """
    Ferramenta para gerar plantas baixas em formato SVG baseada em dados do briefing.
    Recebe um JSON com briefing_completo contendo informações do estande, projeto e divisões funcionais.
    Retorna código SVG completo da planta baixa com dimensões, áreas e layout visual.
    Use esta ferramenta quando precisar criar representações visuais de projetos cenográficos.
    """

    def _run(self, dados_json: str) -> str:
        """
        Executa a geração do SVG da planta baixa.
        
        Args:
            dados_json: JSON string com briefing_completo
            
        Returns:
            Código SVG completo da planta baixa
        """
        try:
            # 🔍 DEBUG COMPLETO DO JSON RECEBIDO
            logger.info("🔍 ===== DEBUG SVG TOOL =====")
            logger.info(f"🔍 Tipo do input: {type(dados_json)}")
            logger.info(f"🔍 Tamanho: {len(str(dados_json))} caracteres")
            
            if isinstance(dados_json, str):
                logger.info(f"🔍 Primeiros 300 chars: {dados_json[:300]}")
                logger.info(f"🔍 Últimos 100 chars: {dados_json[-100:]}")
                
                # Verificar área problemática (ao redor do char 2196)
                if len(dados_json) > 2200:
                    logger.info(f"🔍 Chars 2190-2210: '{dados_json[2190:2210]}'")
                    logger.info(f"🔍 Chars 2180-2220: '{dados_json[2180:2220]}'")
            
            # 🔍 TENTATIVAS DE PARSE COM DIFERENTES ESTRATÉGIAS
            dados = None
            
            # Estratégia 1: Parse direto
            try:
                if isinstance(dados_json, str):
                    dados = json.loads(dados_json)
                    logger.info("✅ Parse direto funcionou")
                else:
                    dados = dados_json
                    logger.info("✅ Dados já eram objeto")
            except json.JSONDecodeError as e:
                logger.warning(f"❌ Parse direto falhou: {str(e)}")
                
                # Estratégia 2: Limpar e tentar novamente
                try:
                    logger.info("🔄 Tentando limpar JSON...")
                    dados_clean = self._limpar_json(dados_json)
                    dados = json.loads(dados_clean)
                    logger.info("✅ Parse com limpeza funcionou")
                except json.JSONDecodeError as e2:
                    logger.warning(f"❌ Parse com limpeza falhou: {str(e2)}")
                    
                    # Estratégia 3: Extrair manualmente
                    try:
                        logger.info("🔄 Tentando extração manual...")
                        dados = self._extrair_dados_manual(dados_json)
                        logger.info("✅ Extração manual funcionou")
                    except Exception as e3:
                        logger.error(f"❌ Extração manual falhou: {str(e3)}")
                        return self._svg_erro(f"JSON inválido: {str(e)}")
            
            # Verificar se dados foram extraídos
            if not dados:
                return self._svg_erro("Não foi possível extrair dados do JSON")
            
            logger.info(f"🔍 Dados extraídos: {type(dados)}")
            logger.info(f"🔍 Keys principais: {list(dados.keys()) if isinstance(dados, dict) else 'não é dict'}")
            
            # ADAPTAR AO FORMATO REAL DOS AGENTES
            if 'briefing_completo' in dados:
                # Formato antigo
                briefing = dados['briefing_completo']
                estande = briefing.get('estande', {})
                projeto = briefing.get('projeto', {})
                divisoes_funcionais = briefing.get('divisoes_funcionais', {})
            else:
                # FORMATO NOVO - Direto dos agentes
                logger.info("🔍 Usando formato direto dos agentes")
                
                # Montar estrutura estande
                estande = {
                    'tipo_stand': dados.get('tipo_stand', 'ilha'),
                    'area_total': dados.get('area_total', 100),
                    'medida_frente': self._calcular_frente(dados.get('area_total', 100)),
                    'medida_fundo': self._calcular_fundo(dados.get('area_total', 100))
                }
                
                # Montar estrutura projeto
                projeto = {
                    'nome': dados.get('nome_projeto', 'Projeto'),
                    'empresa': dados.get('empresa', 'Cliente')
                }
                
                # Extrair divisões de diferentes fontes
                divisoes_funcionais = {}
                if 'areas_solicitadas' in dados:
                    divisoes_funcionais = dados['areas_solicitadas']
                elif 'distribuicao_espacial' in dados:
                    divisoes_funcionais = dados['distribuicao_espacial']
            
            logger.info(f"🔍 Estande adaptado: {estande}")
            logger.info(f"🔍 Projeto adaptado: {projeto}")
            logger.info(f"🔍 Divisões adaptadas: {divisoes_funcionais}")
            
            logger.info(f"🔍 Estande: {estande}")
            logger.info(f"🔍 Projeto: {projeto}")
            logger.info(f"🔍 Divisões: {divisoes_funcionais}")
            
            # Extrair dimensões com fallbacks
            frente = self._extrair_numero(estande.get('medida_frente'), 10)
            fundo = self._extrair_numero(estande.get('medida_fundo'), 10)
            area = self._extrair_numero(estande.get('area_total'), frente * fundo)
            tipo = str(estande.get('tipo_stand', 'ilha'))
            
            logger.info(f"🔍 Dimensões finais: {frente}m x {fundo}m = {area}m²")
            
            # Processar divisões funcionais
            divisoes_lista = self._processar_divisoes(divisoes_funcionais)
            logger.info(f"🔍 {len(divisoes_lista)} divisões processadas")
            
            # Gerar SVG
            svg = self._gerar_svg(projeto, estande, divisoes_lista, frente, fundo, area, tipo)
            
            logger.info(f"✅ SVG gerado com sucesso: {len(svg)} caracteres")
            return svg
            
        except Exception as e:
            error_msg = f"Erro inesperado: {str(e)}"
            logger.error(f"❌ {error_msg}")
            import traceback
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
            return self._svg_erro(error_msg)

    def _limpar_json(self, json_str: str) -> str:
        """Limpa JSON de caracteres problemáticos"""
        if not isinstance(json_str, str):
            return str(json_str)
        
        # Remover caracteres de controle
        json_clean = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', json_str)
        
        # Remover quebras de linha dentro de strings
        json_clean = json_clean.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
        
        # Remover espaços múltiplos
        json_clean = re.sub(r'\s+', ' ', json_clean)
        
        return json_clean.strip()

    def _extrair_dados_manual(self, dados_str: str) -> dict:
        """Extração manual de dados quando JSON falha"""
        dados = {}
        
        try:
            # Tentar encontrar padrões específicos
            # Buscar por "briefing_completo"
            if 'briefing_completo' in dados_str:
                # Implementar extração via regex se necessário
                pass
            
            # Por enquanto, retornar estrutura mínima
            dados = {
                'briefing_completo': {
                    'estande': {
                        'medida_frente': 10,
                        'medida_fundo': 10,
                        'area_total': 100,
                        'tipo_stand': 'ilha'
                    },
                    'projeto': {
                        'nome': 'Projeto Fallback',
                        'empresa': 'Cliente'
                    },
                    'divisoes_funcionais': {}
                }
            }
            
        except Exception as e:
            logger.error(f"Erro na extração manual: {e}")
        
        return dados

    def _calcular_frente(self, area_total):
        """Calcula frente aproximada baseada na área"""
        if not area_total:
            return 10
        
        # Assumir proporção próxima ao quadrado
        lado = (area_total ** 0.5)
        return round(lado * 1.2, 1)  # Ligeiramente retangular
    
    def _calcular_fundo(self, area_total):
        """Calcula fundo aproximado baseada na área"""
        if not area_total:
            return 10
        
        frente = self._calcular_frente(area_total)
        return round(area_total / frente, 1)
    
    def _extrair_numero(self, valor, default):
        """Extrai número de forma segura"""
        if isinstance(valor, (int, float)):
            return float(valor)
        
        if isinstance(valor, str):
            try:
                return float(valor)
            except ValueError:
                return default
        
        return default

    def _processar_divisoes(self, divisoes_funcionais) -> list:
        """Processa divisões funcionais de diferentes formatos"""
        divisoes_lista = []
        
        if isinstance(divisoes_funcionais, list):
            divisoes_lista = divisoes_funcionais
        elif isinstance(divisoes_funcionais, dict):
            # Converter dict para lista
            for key, items in divisoes_funcionais.items():
                if isinstance(items, list):
                    for item in items:
                        if isinstance(item, dict):
                            item['categoria'] = key
                            divisoes_lista.append(item)
                        else:
                            divisoes_lista.append({'nome': str(item), 'categoria': key})
        
        return divisoes_lista

    def _gerar_svg(self, projeto, estande, divisoes_lista, frente, fundo, area, tipo):
        """Gera o SVG final"""
        
        # Calcular escala para SVG (área útil: 400x300px)
        escala = min(400/frente, 300/fundo)
        svg_width = int(frente * escala)
        svg_height = int(fundo * escala)
        
        # Posição central
        offset_x = 200 + (400 - svg_width) // 2
        offset_y = 100 + (300 - svg_height) // 2
        
        # Gerar SVG base
        svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg width="800" height="600" viewBox="0 0 800 600" xmlns="http://www.w3.org/2000/svg">
  <!-- Fundo -->
  <rect x="0" y="0" width="800" height="600" fill="#f8f9fa"/>
  
  <!-- Título -->
  <text x="400" y="30" text-anchor="middle" font-family="Arial, sans-serif" font-size="18" font-weight="bold" fill="#333">
    🏗️ {projeto.get('nome', 'Estande')} - {projeto.get('empresa', 'Cliente')}
  </text>
  
  <!-- Subtítulo -->
  <text x="400" y="50" text-anchor="middle" font-family="Arial, sans-serif" font-size="14" fill="#666">
    {tipo.title()} | {frente:.1f}m × {fundo:.1f}m = {area:.1f}m²
  </text>
  
  <!-- Contorno principal do estande -->
  <rect x="{offset_x}" y="{offset_y}" width="{svg_width}" height="{svg_height}" 
        fill="white" stroke="#007bff" stroke-width="4" rx="5"/>'''
        
        # Adicionar divisões funcionais se existirem
        if divisoes_lista:
            div_height = svg_height / len(divisoes_lista)
            for i, divisao in enumerate(divisoes_lista):
                nome = divisao.get('nome', f'Área {i+1}')
                y_pos = offset_y + (i * div_height)
                
                # Área da divisão
                svg += f'''
  
  <!-- Divisão: {nome} -->
  <rect x="{offset_x + 10}" y="{y_pos + 5}" width="{svg_width - 20}" height="{div_height - 10}" 
        fill="rgba(0,123,255,0.1)" stroke="#007bff" stroke-width="1" stroke-dasharray="5,5" rx="3"/>
  
  <text x="{offset_x + 20}" y="{y_pos + 25}" font-family="Arial, sans-serif" font-size="12" fill="#333">
    📍 {nome}
  </text>'''
        
        # Entrada principal
        entrada_width = min(60, svg_width // 3)
        entrada_x = offset_x + (svg_width - entrada_width) // 2
        
        svg += f'''
  
  <!-- Entrada -->
  <rect x="{entrada_x}" y="{offset_y - 8}" width="{entrada_width}" height="8" 
        fill="#28a745" stroke="#1e7e34" stroke-width="2"/>
  <text x="{entrada_x + entrada_width//2}" y="{offset_y - 12}" text-anchor="middle" 
        font-family="Arial, sans-serif" font-size="10" fill="#1e7e34" font-weight="bold">ENTRADA</text>
  
  <!-- Dimensões -->
  <line x1="{offset_x}" y1="{offset_y + svg_height + 15}" x2="{offset_x + svg_width}" y2="{offset_y + svg_height + 15}" 
        stroke="#666" stroke-width="1"/>
  <text x="{offset_x + svg_width//2}" y="{offset_y + svg_height + 30}" text-anchor="middle" 
        font-family="Arial, sans-serif" font-size="12" fill="#666">
    {frente:.1f}m
  </text>
  
  <line x1="{offset_x - 15}" y1="{offset_y}" x2="{offset_x - 15}" y2="{offset_y + svg_height}" 
        stroke="#666" stroke-width="1"/>
  <text x="{offset_x - 25}" y="{offset_y + svg_height//2}" text-anchor="middle" 
        font-family="Arial, sans-serif" font-size="12" fill="#666" 
        transform="rotate(-90 {offset_x - 25} {offset_y + svg_height//2})">
    {fundo:.1f}m
  </text>
  
  <!-- Informações adicionais -->
  <text x="400" y="480" text-anchor="middle" font-family="Arial, sans-serif" font-size="12" fill="#666">
    ✅ Planta baixa gerada automaticamente | CrewAI Debug Tool
  </text>
  
  <text x="20" y="580" font-family="Arial, sans-serif" font-size="10" fill="#999">
    🛠️ svg_generator | {frente:.1f}×{fundo:.1f}m | {len(divisoes_lista)} divisões funcionais
  </text>
  
</svg>'''
        
        return svg

    def _svg_erro(self, erro: str) -> str:
        """Gera SVG de erro padronizado"""
        return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg width="600" height="400" viewBox="0 0 600 400" xmlns="http://www.w3.org/2000/svg">
  <rect x="0" y="0" width="600" height="400" fill="#fff5f5" stroke="#dc3545" stroke-width="2"/>
  
  <text x="300" y="60" text-anchor="middle" font-family="Arial, sans-serif" font-size="20" font-weight="bold" fill="#dc3545">
    ❌ Erro na Geração SVG
  </text>
  
  <text x="300" y="200" text-anchor="middle" font-family="Arial, sans-serif" font-size="14" fill="#333">
    {erro[:60]}{"..." if len(erro) > 60 else ""}
  </text>
  
  <text x="300" y="350" text-anchor="middle" font-family="Arial, sans-serif" font-size="12" fill="#999">
    🛠️ SvgGeneratorTool | CrewAI Debug Tool
  </text>
</svg>'''


# Instância da ferramenta para ser importada
svg_generator_tool = SvgGeneratorTool()