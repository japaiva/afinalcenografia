# core/services/crewai/tools/svg_function.py - VERSÃO COMPLETA CORRIGIDA

import json
import logging
import re
import html
from crewai.tools import BaseTool

logger = logging.getLogger(__name__)


class PlantaBaixaSvgTool(BaseTool):
    name: str = "planta_baixa_svg_generator"
    description: str = """
    Ferramenta ESPECIALIZADA para gerar PLANTAS BAIXAS ARQUITETÔNICAS em formato SVG.
    
    FUNÇÃO ESPECÍFICA: Converte dados de briefing cenográfico em representação visual 2D (planta baixa).
    
    INPUT: JSON com briefing_completo contendo:
    - Dados do estande (área, dimensões, tipo)
    - Divisões funcionais (salas, áreas de exposição, copas, depósitos)
    - Informações do projeto e empresa
    
    OUTPUT: Código SVG técnico representando:
    - Layout espacial do estande em vista superior
    - Divisões internas com labels
    - Dimensões e área total
    - Entrada principal
    - Informações do projeto
    
    Esta é uma ferramenta de ARQUITETURA/CENOGRAFIA, não um gerador genérico de SVG.
    Use APENAS quando precisar criar plantas baixas técnicas de estandes ou espaços cenográficos.
    """

    def _run(self, dados_json: str) -> str:
        """
        Executa a geração da PLANTA BAIXA em SVG.
        
        PROCESSO:
        1. Analisa dados do briefing (área, dimensões, divisões)
        2. Calcula layout espacial otimizado
        3. Gera representação 2D técnica em SVG
        4. Inclui labels, dimensões e informações técnicas
        
        Args:
            dados_json: JSON string com briefing_completo do projeto cenográfico
            
        Returns:
            Código SVG da planta baixa técnica (vista superior do estande)
        """
        try:
            logger.info("🏗️ ===== GERADOR DE PLANTAS BAIXAS - INÍCIO =====")
            
            # Processar dados de entrada
            dados = self._processar_dados_entrada(dados_json)
            
            # Extrair informações estruturadas para arquitetura
            projeto_info = self._extrair_projeto_info(dados)
            estande_info = self._extrair_estande_info(dados)
            divisoes_info = self._extrair_divisoes_info(dados)
            
            logger.info(f"🏢 Processando estande: {projeto_info['nome']} | {estande_info['area']}m² | {len(divisoes_info)} divisões")
            
            # Gerar planta baixa SVG técnica
            svg_planta = self._gerar_planta_baixa_svg(projeto_info, estande_info, divisoes_info)
            
            # Validação final arquitetônica
            svg_final = self._validacao_final_svg(svg_planta)
            
            logger.info(f"✅ Planta baixa gerada: {len(svg_final)} chars")
            return svg_final
            
        except Exception as e:
            logger.error(f"❌ Erro na geração da planta baixa: {str(e)}")
            return self._planta_baixa_emergencia()

    def _processar_dados_entrada(self, dados_json):
        """Parse ultra robusto dos dados de entrada"""
        
        # Estratégia 1: Se já é dict, usar direto
        if isinstance(dados_json, dict):
            logger.info("✅ Dados já são dict")
            return dados_json
            
        # Estratégia 2: JSON string
        if isinstance(dados_json, str):
            try:
                return json.loads(dados_json)
            except json.JSONDecodeError as e:
                logger.warning(f"⚠️ JSON parse falhou: {e}")
        
        # Estratégia 3: Extração via regex
        logger.info("🔧 Tentando extração via regex...")
        dados_extraidos = self._extrair_dados_por_padrao(str(dados_json))
        
        if dados_extraidos:
            logger.info("✅ Dados extraídos via regex")
            return dados_extraidos
        
        # Estratégia 4: Dados padrão
        logger.warning("⚠️ Usando dados padrão")
        return self._dados_padrao_seguros()

    def _extrair_dados_por_padrao(self, texto):
        """Extrai dados usando regex quando JSON falha"""
        dados = {}
        
        # Buscar área total
        area_match = re.search(r'area[_\s]*total["\s]*:?["\s]*(\d+\.?\d*)', texto, re.I)
        if area_match:
            dados['area_total'] = float(area_match.group(1))
        
        # Buscar nome do projeto
        nome_match = re.search(r'nome["\s]*:?["\s]*([^",\n]+)', texto, re.I)
        if nome_match:
            dados['nome_projeto'] = nome_match.group(1).strip('"\'')
        
        # Buscar empresa
        empresa_match = re.search(r'empresa["\s]*:?["\s]*([^",\n]+)', texto, re.I)
        if empresa_match:
            dados['empresa'] = empresa_match.group(1).strip('"\'')
            
        return dados if dados else self._dados_padrao_seguros()

    def _dados_padrao_seguros(self):
        """Retorna dados padrão seguros"""
        return {
            'area_total': 100,
            'nome_projeto': 'Estande Feira',
            'empresa': 'Cliente',
            'tipo_stand': 'ilha'
        }

    def _extrair_projeto_info(self, dados):
        """Extração segura de informações do projeto"""
        
        # Navegar estrutura aninhada
        if 'briefing_completo' in dados:
            projeto_data = dados['briefing_completo'].get('projeto', {})
        else:
            projeto_data = dados
        
        return {
            'nome': self._sanitizar_texto_extra_seguro(projeto_data.get('nome', dados.get('nome_projeto', 'Estande Feira'))),
            'empresa': self._sanitizar_texto_extra_seguro(projeto_data.get('empresa', dados.get('empresa', 'Cliente')))
        }

    def _extrair_estande_info(self, dados):
        """Extração segura de informações do estande"""
        
        # Navegar estrutura aninhada
        if 'briefing_completo' in dados:
            estande_data = dados['briefing_completo'].get('estande', {})
        else:
            estande_data = dados
        
        # Área total
        area = self._extrair_numero_seguro(
            estande_data.get('area_total', dados.get('area_total', 100))
        )
        
        # Calcular dimensões baseadas na área
        frente = self._calcular_dimensao_frente(area)
        fundo = self._calcular_dimensao_fundo(area)
        
        return {
            'area': area,
            'frente': frente,
            'fundo': fundo,
            'tipo': self._sanitizar_texto_extra_seguro(estande_data.get('tipo_stand', dados.get('tipo_stand', 'ilha')))
        }

    def _extrair_divisoes_info(self, dados):
        """Extração segura de divisões funcionais"""
        
        divisoes = []
        
        # Navegar estrutura aninhada
        if 'briefing_completo' in dados:
            divisoes_data = dados['briefing_completo'].get('divisoes_funcionais', {})
        else:
            divisoes_data = dados.get('divisoes_funcionais', {})
        
        # Processar diferentes tipos de divisões
        tipos_divisao = ['areas_exposicao', 'salas_reuniao', 'copas', 'depositos']
        
        for tipo in tipos_divisao:
            items = divisoes_data.get(tipo, [])
            if isinstance(items, list):
                for i, item in enumerate(items):
                    if isinstance(item, dict):
                        nome = self._sanitizar_texto_extra_seguro(item.get('nome', f'{tipo.title()} {i+1}'))
                    else:
                        nome = f'{tipo.title()} {i+1}'
                    
                    divisoes.append({
                        'nome': nome,
                        'tipo': tipo
                    })
        
        # Se não há divisões, criar algumas padrão
        if not divisoes:
            divisoes = [
                {'nome': 'Área Principal', 'tipo': 'exposicao'},
                {'nome': 'Recepção', 'tipo': 'atendimento'}
            ]
        
        return divisoes

    def _sanitizar_texto_extra_seguro(self, texto):
        """Sanitização extra segura de texto para SVG"""
        if not texto:
            return "Sem Info"
        
        # Converter para string
        texto_str = str(texto)
        
        # Remover caracteres problemáticos
        texto_limpo = re.sub(r'[^\w\s\-_.,!?()\[\]]', '', texto_str)
        
        # Remover espaços extras
        texto_limpo = ' '.join(texto_limpo.split())
        
        # Limitar tamanho
        texto_limitado = texto_limpo[:30]
        
        # Escapar para XML de forma super segura
        texto_escapado = html.escape(texto_limitado, quote=True)
        
        # Se vazio, usar padrão
        return texto_escapado if texto_escapado.strip() else "Texto"

    def _extrair_numero_seguro(self, valor):
        """Extrai número de forma completamente segura"""
        if isinstance(valor, (int, float)):
            return max(10, min(1000, float(valor)))  # Entre 10 e 1000
        
        if isinstance(valor, str):
            # Extrair apenas dígitos e ponto
            numeros = re.findall(r'\d+\.?\d*', valor)
            if numeros:
                try:
                    return max(10, min(1000, float(numeros[0])))
                except:
                    pass
        
        return 100  # Valor padrão seguro

    def _calcular_dimensao_frente(self, area):
        """Calcula frente baseada na área"""
        lado = (area ** 0.5)
        return round(lado * 1.3, 1)  # Ligeiramente retangular

    def _calcular_dimensao_fundo(self, area):
        """Calcula fundo baseada na área e frente"""
        frente = self._calcular_dimensao_frente(area)
        return round(area / frente, 1)

    def _gerar_planta_baixa_svg(self, projeto_info, estande_info, divisoes_info):
        """Gera PLANTA BAIXA ARQUITETÔNICA usando template técnico especializado"""
        
        # Extrair valores seguros
        nome_projeto = projeto_info['nome']
        nome_empresa = projeto_info['empresa']
        area = estande_info['area']
        frente = estande_info['frente']
        fundo = estande_info['fundo']
        tipo = estande_info['tipo']
        
        # CÁLCULOS ARQUITETÔNICOS
        # Canvas técnico para plantas baixas
        largura_canvas = 800
        altura_canvas = 600
        margem_tecnica = 80  # Margem para informações técnicas
        
        # Área útil para desenho da planta
        largura_util = largura_canvas - (2 * margem_tecnica)
        altura_util = altura_canvas - 250  # Espaço para título e legenda
        
        # Escala arquitetônica (manter proporções reais)
        escala_x = largura_util / frente
        escala_y = altura_util / fundo
        escala = min(escala_x, escala_y) * 0.75  # 75% da escala máxima para margens
        
        # Dimensões do estande no desenho
        largura_estande = int(frente * escala)
        altura_estande = int(fundo * escala)
        
        # Posicionamento centralizado
        x_estande = int((largura_canvas - largura_estande) / 2)
        y_estande = int(130 + (altura_util - altura_estande) / 2)
        
        # MONTAGEM DA PLANTA BAIXA TÉCNICA
        svg_parts = []
        
        # Header XML perfeito
        svg_parts.append('<?xml version="1.0" encoding="UTF-8"?>')
        svg_parts.append(f'<svg width="{largura_canvas}" height="{altura_canvas}" viewBox="0 0 {largura_canvas} {altura_canvas}" xmlns="http://www.w3.org/2000/svg">')
        
        # Background técnico
        svg_parts.append(f'  <rect x="0" y="0" width="{largura_canvas}" height="{altura_canvas}" fill="#ffffff" stroke="#e0e0e0" stroke-width="1"/>')
        
        # CABEÇALHO TÉCNICO
        svg_parts.append(f'  <text x="400" y="30" text-anchor="middle" font-family="Arial" font-size="18" font-weight="bold" fill="#2c3e50">')
        svg_parts.append(f'    PLANTA BAIXA - {nome_projeto}')
        svg_parts.append('  </text>')
        
        svg_parts.append(f'  <text x="400" y="50" text-anchor="middle" font-family="Arial" font-size="12" fill="#7f8c8d">')
        svg_parts.append(f'    Cliente: {nome_empresa}')
        svg_parts.append('  </text>')
        
        # INFORMAÇÕES TÉCNICAS
        svg_parts.append(f'  <text x="400" y="75" text-anchor="middle" font-family="Arial" font-size="14" font-weight="bold" fill="#34495e">')
        svg_parts.append(f'    {tipo.upper()} | {frente}m × {fundo}m | ÁREA: {area}m²')
        svg_parts.append('  </text>')
        
        # CONTORNO PRINCIPAL DO ESTANDE (paredes externas)
        svg_parts.append(f'  <rect x="{x_estande}" y="{y_estande}" width="{largura_estande}" height="{altura_estande}"')
        svg_parts.append('        fill="#f8f9fa" stroke="#2c3e50" stroke-width="4" rx="2"/>')
        
        # DIVISÕES INTERNAS (layout funcional)
        if divisoes_info and len(divisoes_info) > 0:
            self._adicionar_divisoes_funcionais(svg_parts, divisoes_info, x_estande, y_estande, largura_estande, altura_estande)
        
        # ENTRADA PRINCIPAL (elemento arquitetônico obrigatório)
        self._adicionar_entrada_principal(svg_parts, x_estande, y_estande, largura_estande)
        
        # COTAS E DIMENSÕES
        self._adicionar_cotas_dimensoes(svg_parts, x_estande, y_estande, largura_estande, altura_estande, frente, fundo)
        
        # LEGENDA TÉCNICA
        svg_parts.append('  <text x="400" y="530" text-anchor="middle" font-family="Arial" font-size="11" fill="#7f8c8d">')
        svg_parts.append('    PLANTA BAIXA TÉCNICA - VISTA SUPERIOR')
        svg_parts.append('  </text>')
        
        svg_parts.append(f'  <text x="400" y="550" text-anchor="middle" font-family="Arial" font-size="10" fill="#95a5a6">')
        svg_parts.append(f'    Escala: 1:{int(100/escala)} | {len(divisoes_info)} ambientes funcionais')
        svg_parts.append('  </text>')
        
        # Assinatura técnica
        svg_parts.append(f'  <text x="20" y="580" font-family="Arial" font-size="9" fill="#bdc3c7">')
        svg_parts.append(f'    CrewAI V2 | Gerador de Plantas Baixas | Sistema Arquitetônico')
        svg_parts.append('  </text>')
        
        # Fechar SVG
        svg_parts.append('</svg>')
        
        return '\n'.join(svg_parts)

    def _adicionar_divisoes_funcionais(self, svg_parts, divisoes_info, x_base, y_base, largura_base, altura_base):
        """Adiciona divisões funcionais com layout arquitetônico otimizado"""
        
        if len(divisoes_info) == 1:
            # Ambiente único
            div = divisoes_info[0]
            svg_parts.append(f'  <text x="{x_base + largura_base//2}" y="{y_base + altura_base//2}" text-anchor="middle"')
            svg_parts.append(f'        font-family="Arial" font-size="14" font-weight="bold" fill="#2c3e50">')
            svg_parts.append(f'    {div["nome"]}')
            svg_parts.append('  </text>')
            
        elif len(divisoes_info) == 2:
            # Layout horizontal (lado a lado)
            largura_divisao = largura_base // 2
            
            for i, div in enumerate(divisoes_info):
                x_div = x_base + (i * largura_divisao)
                y_div = y_base
                
                # Divisória interna
                if i > 0:
                    svg_parts.append(f'  <line x1="{x_div}" y1="{y_div + 10}" x2="{x_div}" y2="{y_div + altura_base - 10}"')
                    svg_parts.append('        stroke="#7f8c8d" stroke-width="2" stroke-dasharray="5,5"/>')
                
                # Label do ambiente
                svg_parts.append(f'  <text x="{x_div + largura_divisao//2}" y="{y_div + 30}" text-anchor="middle"')
                svg_parts.append(f'        font-family="Arial" font-size="12" font-weight="bold" fill="#34495e">')
                svg_parts.append(f'    {div["nome"]}')
                svg_parts.append('  </text>')
                
        else:
            # Layout em grid (múltiplas divisões)
            cols = 2 if len(divisoes_info) <= 4 else 3
            rows = (len(divisoes_info) + cols - 1) // cols
            
            largura_divisao = largura_base // cols
            altura_divisao = altura_base // rows
            
            for i, div in enumerate(divisoes_info[:6]):  # Máximo 6 divisões
                col = i % cols
                row = i // cols
                
                x_div = x_base + (col * largura_divisao)
                y_div = y_base + (row * altura_divisao)
                
                # Contorno da divisão
                svg_parts.append(f'  <rect x="{x_div + 5}" y="{y_div + 5}" width="{largura_divisao - 10}" height="{altura_divisao - 10}"')
                svg_parts.append('        fill="rgba(52,152,219,0.1)" stroke="#3498db" stroke-width="1" stroke-dasharray="3,3" rx="2"/>')
                
                # Label do ambiente
                svg_parts.append(f'  <text x="{x_div + largura_divisao//2}" y="{y_div + 25}" text-anchor="middle"')
                svg_parts.append(f'        font-family="Arial" font-size="10" font-weight="bold" fill="#2c3e50">')
                svg_parts.append(f'    {div["nome"]}')
                svg_parts.append('  </text>')

    def _adicionar_entrada_principal(self, svg_parts, x_base, y_base, largura_base):
        """Adiciona representação arquitetônica da entrada principal"""
        
        largura_entrada = min(80, largura_base // 3)
        x_entrada = x_base + (largura_base - largura_entrada) // 2
        
        # Abertura na parede (representação arquitetônica)
        svg_parts.append(f'  <rect x="{x_entrada}" y="{y_base - 8}" width="{largura_entrada}" height="8"')
        svg_parts.append('        fill="#27ae60" stroke="#229954" stroke-width="2"/>')
        
        # Símbolo de entrada
        svg_parts.append(f'  <text x="{x_entrada + largura_entrada//2}" y="{y_base - 12}" text-anchor="middle"')
        svg_parts.append('        font-family="Arial" font-size="10" font-weight="bold" fill="#27ae60">ENTRADA</text>')
        
        # Seta indicativa
        meio_entrada = x_entrada + largura_entrada // 2
        svg_parts.append(f'  <polygon points="{meio_entrada-8},{y_base-20} {meio_entrada},{y_base-25} {meio_entrada+8},{y_base-20}"')
        svg_parts.append('           fill="#27ae60"/>')

    def _adicionar_cotas_dimensoes(self, svg_parts, x_base, y_base, largura_base, altura_base, frente, fundo):
        """Adiciona cotas e dimensões técnicas"""
        
        # Cota horizontal (frente)
        y_cota_h = y_base + altura_base + 25
        svg_parts.append(f'  <line x1="{x_base}" y1="{y_cota_h}" x2="{x_base + largura_base}" y2="{y_cota_h}"')
        svg_parts.append('        stroke="#7f8c8d" stroke-width="1"/>')
        svg_parts.append(f'  <text x="{x_base + largura_base//2}" y="{y_cota_h + 15}" text-anchor="middle"')
        svg_parts.append(f'        font-family="Arial" font-size="10" fill="#7f8c8d">{frente}m</text>')
        
        # Cota vertical (fundo)
        x_cota_v = x_base + largura_base + 25
        svg_parts.append(f'  <line x1="{x_cota_v}" y1="{y_base}" x2="{x_cota_v}" y2="{y_base + altura_base}"')
        svg_parts.append('        stroke="#7f8c8d" stroke-width="1"/>')
        svg_parts.append(f'  <text x="{x_cota_v + 15}" y="{y_base + altura_base//2}" text-anchor="middle"')
        svg_parts.append(f'        font-family="Arial" font-size="10" fill="#7f8c8d" transform="rotate(90 {x_cota_v + 15} {y_base + altura_base//2})">{fundo}m</text>')

    def _validacao_final_svg(self, svg_content):
        """Validação final rigorosa do SVG"""
        
        # Normalizar declaração XML
        if not svg_content.startswith('<?xml'):
            logger.warning("Adicionando declaração XML ausente")
            svg_content = '<?xml version="1.0" encoding="UTF-8"?>\n' + svg_content
        
        # Limpar declaração XML malformada
        if svg_content.startswith('<?xml'):
            # Extrair e reconstruir declaração XML
            xml_end = svg_content.find('?>') + 2
            if xml_end > 1:
                resto_svg = svg_content[xml_end:].strip()
                svg_content = '<?xml version="1.0" encoding="UTF-8"?>\n' + resto_svg
        
        # Verificar estrutura básica
        if '<svg' not in svg_content or '</svg>' not in svg_content:
            logger.error("Tags SVG malformadas")
            return self._planta_baixa_emergencia()
        
        # Verificar aspas balanceadas
        aspas_duplas = svg_content.count('"')
        if aspas_duplas % 2 != 0:
            logger.error(f"Aspas duplas desbalanceadas: {aspas_duplas}")
            return self._planta_baixa_emergencia()
        
        # Limpar SVG para XML
        svg_limpo = self._limpar_svg_para_xml(svg_content)
        
        # Tentar parsear como XML básico
        try:
            import xml.etree.ElementTree as ET
            ET.fromstring(svg_limpo)
            logger.info("✅ SVG passou na validação XML")
            return svg_limpo
        except Exception as e:
            logger.error(f"SVG inválido como XML: {e}")
            logger.error(f"Primeiros 100 chars: {svg_limpo[:100]}")
            return self._planta_baixa_emergencia()
    
    def _limpar_svg_para_xml(self, svg_content):
        """Limpa SVG para ser válido como XML"""
        
        # Remover caracteres de controle
        svg_limpo = ''.join(char for char in svg_content if ord(char) >= 32 or char in '\n\r\t')
        
        # Corrigir quebras de linha em atributos
        svg_limpo = re.sub(r'=\s*\n\s*"', '="', svg_limpo)
        
        # Corrigir espaços em excesso
        svg_limpo = re.sub(r'\s+', ' ', svg_limpo)
        
        # Garantir quebras de linha adequadas
        svg_limpo = re.sub(r'>\s*<', '>\n<', svg_limpo)
        
        # Remover espaços no início/fim
        svg_limpo = svg_limpo.strip()
        
        return svg_limpo

    def _planta_baixa_emergencia(self):
        """Planta baixa de emergência com layout técnico básico"""
        return '''<?xml version="1.0" encoding="UTF-8"?>
<svg width="800" height="600" viewBox="0 0 800 600" xmlns="http://www.w3.org/2000/svg">
  <rect x="0" y="0" width="800" height="600" fill="#ffffff"/>
  <text x="400" y="40" text-anchor="middle" font-family="Arial" font-size="18" font-weight="bold" fill="#2c3e50">PLANTA BAIXA - SISTEMA DE EMERGENCIA</text>
  <text x="400" y="65" text-anchor="middle" font-family="Arial" font-size="12" fill="#7f8c8d">Layout Padrao | Estande Generico</text>
  <rect x="200" y="150" width="400" height="250" fill="#f8f9fa" stroke="#2c3e50" stroke-width="4" rx="2"/>
  <rect x="220" y="170" width="180" height="100" fill="rgba(52,152,219,0.1)" stroke="#3498db" stroke-width="1" stroke-dasharray="3,3"/>
  <text x="310" y="190" text-anchor="middle" font-family="Arial" font-size="12" fill="#2c3e50">Area Principal</text>
  <rect x="420" y="170" width="160" height="100" fill="rgba(52,152,219,0.1)" stroke="#3498db" stroke-width="1" stroke-dasharray="3,3"/>
  <text x="500" y="190" text-anchor="middle" font-family="Arial" font-size="12" fill="#2c3e50">Recepcao</text>
  <rect x="220" y="280" width="360" height="100" fill="rgba(52,152,219,0.1)" stroke="#3498db" stroke-width="1" stroke-dasharray="3,3"/>
  <text x="400" y="300" text-anchor="middle" font-family="Arial" font-size="12" fill="#2c3e50">Area de Exposicao</text>
  <rect x="360" y="142" width="80" height="8" fill="#27ae60" stroke="#229954" stroke-width="2"/>
  <text x="400" y="138" text-anchor="middle" font-family="Arial" font-size="10" font-weight="bold" fill="#27ae60">ENTRADA</text>
  <text x="400" y="480" text-anchor="middle" font-family="Arial" font-size="11" fill="#7f8c8d">PLANTA BAIXA TECNICA - SISTEMA ESTAVEL</text>
  <text x="20" y="580" font-family="Arial" font-size="9" fill="#bdc3c7">CrewAI V2 | Gerador de Plantas Baixas | Modo Emergencia</text>
</svg>'''


# Instância da ferramenta especializada
planta_baixa_svg_tool = PlantaBaixaSvgTool()

# Manter compatibilidade com nome antigo
svg_generator_tool = planta_baixa_svg_tool