# core/services/planta_baixa_service.py

import json
import logging
from django.core.files.base import ContentFile
from django.conf import settings
from core.models import Agente
from projetista.models import PlantaBaixa
import xml.etree.ElementTree as ET
from PIL import Image, ImageDraw
import io

logger = logging.getLogger(__name__)

# =============================================================================
# PLANTA BAIXA SERVICE
# =============================================================================

class PlantaBaixaService:
    """
    Serviço para geração de plantas baixas algorítmicas
    """
    
    def __init__(self, agente=None):
        self.agente = agente
        self.largura_svg = 800
        self.altura_svg = 600
        self.escala = 20  # pixels por metro
        
    def gerar_planta_baixa(self, briefing, versao=1, planta_anterior=None):
        """
        Gera planta baixa baseada no briefing
        """
        try:
            # 1. Extrair dados do briefing
            dados_briefing = self._extrair_dados_briefing(briefing)
            
            # 2. Calcular layout algorítmico
            layout_data = self._calcular_layout(dados_briefing)
            
            # 3. Gerar arquivo SVG
            svg_content = self._gerar_svg(layout_data)
            
            # 4. Gerar preview PNG
            png_content = self._gerar_preview_png(layout_data)
            
            # 5. Criar objeto PlantaBaixa
            planta = PlantaBaixa(
                projeto=briefing.projeto,
                briefing=briefing,
                projetista=briefing.projeto.projetista,
                dados_json=layout_data,
                algoritmo_usado='layout_generator_v1',
                parametros_geracao=dados_briefing,
                versao=versao,
                planta_anterior=planta_anterior,
                status='pronta'
            )
            
            # 6. Salvar arquivos
            svg_filename = f"planta_{briefing.projeto.id}_v{versao}.svg"
            png_filename = f"planta_{briefing.projeto.id}_v{versao}.png"
            
            planta.arquivo_svg.save(svg_filename, ContentFile(svg_content.encode('utf-8')))
            planta.arquivo_png.save(png_filename, ContentFile(png_content))
            
            planta.save()
            
            return {
                'success': True,
                'planta': planta,
                'dados': layout_data
            }
            
        except Exception as e:
            logger.error(f"Erro ao gerar planta baixa: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }
    
    def _extrair_dados_briefing(self, briefing):
        """
        Extrai dados relevantes do briefing para gerar layout
        """
        dados = {
            'dimensoes': {
                'frente': float(briefing.medida_frente or 6),
                'fundo': float(briefing.medida_fundo or 4),
                'lateral_esquerda': float(briefing.medida_lateral_esquerda or 4),
                'lateral_direita': float(briefing.medida_lateral_direita or 4),
                'area_total': float(briefing.area_estande or 24)
            },
            'tipo_stand': briefing.tipo_stand or 'esquina',
            'areas_exposicao': [],
            'salas_reuniao': [],
            'copas': [],
            'depositos': []
        }
        
        # Extrair áreas do briefing
        if hasattr(briefing, 'areas_exposicao'):
            for area in briefing.areas_exposicao.all():
                dados['areas_exposicao'].append({
                    'metragem': float(area.metragem or 0),
                    'tem_lounge': area.tem_lounge,
                    'tem_vitrine': area.tem_vitrine_exposicao,
                    'tem_balcao_recepcao': area.tem_balcao_recepcao,
                    'tem_mesas_atendimento': area.tem_mesas_atendimento,
                    'observacoes': area.observacoes or ''
                })
        
        if hasattr(briefing, 'salas_reuniao'):
            for sala in briefing.salas_reuniao.all():
                dados['salas_reuniao'].append({
                    'capacidade': sala.capacidade,
                    'metragem': float(sala.metragem or 0),
                    'equipamentos': sala.equipamentos or ''
                })
        
        return dados
    
    def _calcular_layout(self, dados):
        """
        Algoritmo principal para calcular posicionamento dos ambientes
        """
        dimensoes = dados['dimensoes']
        largura = dimensoes['frente']
        altura = dimensoes['fundo']
        
        # Layout básico algorítmico
        layout = {
            'dimensoes_estande': dimensoes,
            'ambientes': [],
            'paredes': self._calcular_paredes(largura, altura),
            'area_total': largura * altura,
            'escala': self.escala
        }
        
        # Definir áreas por prioridade
        areas_prioritarias = self._definir_areas_prioritarias(dados)
        
        # Posicionar ambientes
        area_ocupada = 0
        y_atual = 0.5  # Margem inicial
        
        for ambiente in areas_prioritarias:
            if area_ocupada + ambiente['area'] <= layout['area_total'] * 0.9:  # 90% máximo
                posicao = self._calcular_posicao_ambiente(
                    ambiente, 
                    largura, 
                    altura, 
                    y_atual
                )
                
                layout['ambientes'].append({
                    'tipo': ambiente['tipo'],
                    'nome': ambiente['nome'],
                    'area': ambiente['area'],
                    'posicao': posicao,
                    'dimensoes': ambiente['dimensoes'],
                    'componentes': ambiente.get('componentes', [])
                })
                
                area_ocupada += ambiente['area']
                y_atual += ambiente['dimensoes']['altura'] + 0.5  # Espaçamento
        
        # Calcular circulação
        layout['area_circulacao'] = layout['area_total'] - area_ocupada
        layout['percentual_ocupacao'] = (area_ocupada / layout['area_total']) * 100
        
        return layout
    
    def _definir_areas_prioritarias(self, dados):
        """
        Define ordem de prioridade e dimensões dos ambientes
        """
        areas = []
        
        # Área de exposição (sempre prioritária)
        if dados['areas_exposicao']:
            for idx, area_exp in enumerate(dados['areas_exposicao']):
                metragem = area_exp['metragem'] or 12  # Padrão 12m²
                dimensoes = self._calcular_dimensoes_retangulo(metragem, proporcao=1.5)
                
                componentes = []
                if area_exp['tem_balcao_recepcao']:
                    componentes.append({'tipo': 'balcao_recepcao', 'posicao': 'frontal'})
                if area_exp['tem_lounge']:
                    componentes.append({'tipo': 'lounge', 'posicao': 'lateral'})
                if area_exp['tem_vitrine']:
                    componentes.append({'tipo': 'vitrine', 'posicao': 'parede'})
                
                areas.append({
                    'tipo': 'exposicao',
                    'nome': f'Área de Exposição {idx + 1}',
                    'area': metragem,
                    'dimensoes': dimensoes,
                    'prioridade': 1,
                    'componentes': componentes
                })
        
        # Salas de reunião
        for idx, sala in enumerate(dados['salas_reuniao']):
            metragem = sala['metragem'] or (sala['capacidade'] * 1.5)  # 1.5m² por pessoa
            dimensoes = self._calcular_dimensoes_retangulo(metragem, proporcao=1.2)
            
            areas.append({
                'tipo': 'reuniao',
                'nome': f'Sala de Reunião {idx + 1}',
                'area': metragem,
                'dimensoes': dimensoes,
                'prioridade': 2,
                'componentes': [
                    {'tipo': 'mesa_reuniao', 'capacidade': sala['capacidade']},
                    {'tipo': 'cadeiras', 'quantidade': sala['capacidade']}
                ]
            })
        
        # Copas e depósitos
        if dados['copas']:
            for idx, copa in enumerate(dados['copas']):
                metragem = copa['metragem'] or 4
                areas.append({
                    'tipo': 'copa',
                    'nome': f'Copa {idx + 1}',
                    'area': metragem,
                    'dimensoes': self._calcular_dimensoes_retangulo(metragem, proporcao=1.0),
                    'prioridade': 3
                })
        
        if dados['depositos']:
            for idx, deposito in enumerate(dados['depositos']):
                metragem = deposito['metragem'] or 3
                areas.append({
                    'tipo': 'deposito',
                    'nome': f'Depósito {idx + 1}',
                    'area': metragem,
                    'dimensoes': self._calcular_dimensoes_retangulo(metragem, proporcao=0.8),
                    'prioridade': 4
                })
        
        # Ordenar por prioridade
        return sorted(areas, key=lambda x: x['prioridade'])
    
    def _calcular_dimensoes_retangulo(self, area, proporcao=1.5):
        """
        Calcula largura e altura de um retângulo dada a área e proporção
        """
        altura = (area / proporcao) ** 0.5
        largura = area / altura
        return {
            'largura': round(largura, 2),
            'altura': round(altura, 2)
        }
    
    def _calcular_posicao_ambiente(self, ambiente, largura_total, altura_total, y_sugerido):
        """
        Calcula posição x,y do ambiente dentro do estande
        """
        dim = ambiente['dimensoes']
        
        # Posicionamento simples: centralizado horizontalmente
        x = (largura_total - dim['largura']) / 2
        y = min(y_sugerido, altura_total - dim['altura'] - 0.5)
        
        return {
            'x': round(x, 2),
            'y': round(y, 2)
        }
    
    def _calcular_paredes(self, largura, altura):
        """
        Define coordenadas das paredes do estande
        """
        return {
            'frontal': {'x1': 0, 'y1': 0, 'x2': largura, 'y2': 0},
            'direita': {'x1': largura, 'y1': 0, 'x2': largura, 'y2': altura},
            'fundo': {'x1': largura, 'y1': altura, 'x2': 0, 'y2': altura},
            'esquerda': {'x1': 0, 'y1': altura, 'x2': 0, 'y2': 0}
        }
    
    def _gerar_svg(self, layout_data):
        """
        Gera arquivo SVG da planta baixa
        """
        dimensoes = layout_data['dimensoes_estande']
        escala = layout_data['escala']
        
        # Calcular dimensões do SVG
        svg_largura = dimensoes['frente'] * escala + 100  # Margem
        svg_altura = dimensoes['fundo'] * escala + 100
        
        # Criar SVG
        svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{svg_largura}" height="{svg_altura}" viewBox="0 0 {svg_largura} {svg_altura}">
  <defs>
    <style>
      .parede {{ stroke: #000; stroke-width: 3; fill: none; }}
      .ambiente {{ stroke: #666; stroke-width: 1; fill: rgba(200,220,255,0.3); }}
      .texto {{ font-family: Arial; font-size: 12px; text-anchor: middle; }}
      .componente {{ stroke: #333; stroke-width: 1; fill: rgba(255,200,200,0.5); }}
    </style>
  </defs>
  
  <!-- Fundo -->
  <rect x="0" y="0" width="{svg_largura}" height="{svg_altura}" fill="#f8f9fa"/>
  
  <!-- Estande (contorno) -->
  <rect x="50" y="50" width="{dimensoes['frente'] * escala}" height="{dimensoes['fundo'] * escala}" 
        class="parede" stroke-width="4"/>
'''
        
        # Adicionar ambientes
        for ambiente in layout_data['ambientes']:
            pos = ambiente['posicao']
            dim = ambiente['dimensoes']
            
            x = 50 + (pos['x'] * escala)
            y = 50 + (pos['y'] * escala)
            w = dim['largura'] * escala
            h = dim['altura'] * escala
            
            svg += f'''
  <!-- {ambiente['nome']} -->
  <rect x="{x}" y="{y}" width="{w}" height="{h}" class="ambiente"/>
  <text x="{x + w/2}" y="{y + h/2}" class="texto">{ambiente['nome']}</text>
  <text x="{x + w/2}" y="{y + h/2 + 15}" class="texto" font-size="10">{ambiente['area']:.1f}m²</text>
'''
            
            # Adicionar componentes
            for componente in ambiente.get('componentes', []):
                comp_svg = self._gerar_componente_svg(componente, x, y, w, h)
                svg += comp_svg
        
        # Adicionar dimensões e cotas
        svg += f'''
  <!-- Dimensões -->
  <text x="{50 + (dimensoes['frente'] * escala / 2)}" y="40" class="texto" font-size="10">
    {dimensoes['frente']}m
  </text>
  <text x="30" y="{50 + (dimensoes['fundo'] * escala / 2)}" class="texto" font-size="10" transform="rotate(-90 30 {50 + (dimensoes['fundo'] * escala / 2)})">
    {dimensoes['fundo']}m
  </text>
  
  <!-- Área total -->
  <text x="{svg_largura - 20}" y="30" class="texto" font-size="12" text-anchor="end">
    Área: {layout_data['area_total']:.1f}m²
  </text>
</svg>'''
        
        return svg
    
    def _gerar_componente_svg(self, componente, x, y, w, h):
        """
        Gera SVG para componentes específicos (balcões, mesas, etc.)
        """
        tipo = componente['tipo']
        svg = ""
        
        if tipo == 'balcao_recepcao':
            # Balcão na parte frontal
            svg = f'''
  <rect x="{x + w*0.1}" y="{y}" width="{w*0.8}" height="{h*0.2}" class="componente"/>
  <text x="{x + w/2}" y="{y + h*0.1}" class="texto" font-size="8">Balcão</text>
'''
        elif tipo == 'lounge':
            # Área de lounge com poltronas
            svg = f'''
  <circle cx="{x + w*0.3}" cy="{y + h*0.7}" r="{min(w,h)*0.1}" class="componente"/>
  <circle cx="{x + w*0.7}" cy="{y + h*0.7}" r="{min(w,h)*0.1}" class="componente"/>
  <text x="{x + w/2}" y="{y + h*0.9}" class="texto" font-size="8">Lounge</text>
'''
        elif tipo == 'vitrine':
            # Vitrine na parede
            svg = f'''
  <rect x="{x}" y="{y + h*0.8}" width="{w}" height="{h*0.2}" class="componente"/>
  <text x="{x + w/2}" y="{y + h*0.9}" class="texto" font-size="8">Vitrine</text>
'''
        elif tipo == 'mesa_reuniao':
            # Mesa de reunião no centro
            svg = f'''
  <ellipse cx="{x + w/2}" cy="{y + h/2}" rx="{w*0.3}" ry="{h*0.2}" class="componente"/>
  <text x="{x + w/2}" y="{y + h/2}" class="texto" font-size="8">Mesa</text>
'''
        
        return svg
    
    def _gerar_preview_png(self, layout_data):
        """
        Gera preview PNG da planta baixa
        """
        dimensoes = layout_data['dimensoes_estande']
        escala = 30  # Escala maior para PNG
        
        # Calcular dimensões da imagem
        img_largura = int(dimensoes['frente'] * escala + 100)
        img_altura = int(dimensoes['fundo'] * escala + 100)
        
        # Criar imagem
        img = Image.new('RGB', (img_largura, img_altura), 'white')
        draw = ImageDraw.Draw(img)
        
        # Desenhar contorno do estande
        x0, y0 = 50, 50
        x1 = x0 + dimensoes['frente'] * escala
        y1 = y0 + dimensoes['fundo'] * escala
        
        draw.rectangle([x0, y0, x1, y1], outline='black', width=3)
        
        # Desenhar ambientes
        for ambiente in layout_data['ambientes']:
            pos = ambiente['posicao']
            dim = ambiente['dimensoes']
            
            ax = x0 + (pos['x'] * escala)
            ay = y0 + (pos['y'] * escala)
            aw = dim['largura'] * escala
            ah = dim['altura'] * escala
            
            # Retângulo do ambiente
            draw.rectangle([ax, ay, ax + aw, ay + ah], 
                         outline='gray', fill='lightblue', width=1)
        
        # Converter para bytes
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        return buffer.getvalue()


# =============================================================================
# CONCEITO VISUAL SERVICE
# =============================================================================

class ConceitoVisualService:
    """
    Serviço para geração de conceitos visuais baseados em planta baixa
    """
    
    def __init__(self, agente=None):
        self.agente = agente
        
    def gerar_conceito_visual(self, briefing, planta_baixa, **config):
        """
        Gera conceito visual baseado no briefing e planta baixa
        """
        try:
            # Extrair configurações
            estilo = config.get('estilo_visualizacao', 'fotorrealista')
            iluminacao = config.get('iluminacao', 'feira')
            instrucoes_extras = config.get('instrucoes_adicionais', '')
            versao = config.get('versao', 1)
            conceito_anterior = config.get('conceito_anterior', None)
            
            # Obter agente para geração de imagem
            if not self.agente:
                try:
                    self.agente = Agente.objects.get(nome='Agente de Conceito Visual')
                    if not self.agente.ativo:
                        return {
                            'success': False,
                            'error': 'Agente de Conceito Visual está inativo'
                        }
                except Agente.DoesNotExist:
                    return {
                        'success': False,
                        'error': 'Agente de Conceito Visual não encontrado'
                    }
            
            # Usar ImagemPrincipalService para gerar a imagem
            from core.services.imagem_principal_service import ImagemPrincipalService
            imagem_service = ImagemPrincipalService(self.agente)
            
            # Construir prompt baseado na planta baixa
            prompt_customizado = self._construir_prompt_com_planta(
                briefing, planta_baixa, estilo, iluminacao, instrucoes_extras
            )
            
            # Gerar imagem usando prompt customizado
            resultado_imagem = imagem_service._gerar_imagem_com_api(prompt_customizado)
            
            if resultado_imagem['success']:
                # Importar modelo aqui para evitar imports circulares
                from projetista.models import ConceitoVisualNovo
                
                # Criar objeto ConceitoVisualNovo
                conceito = ConceitoVisualNovo(
                    projeto=briefing.projeto,
                    briefing=briefing,
                    planta_baixa=planta_baixa,
                    projetista=briefing.projeto.projetista,
                    descricao=f"Conceito visual {estilo} - {iluminacao}",
                    estilo_visualizacao=estilo,
                    iluminacao=iluminacao,
                    ia_gerado=True,
                    agente_usado=self.agente,
                    prompt_geracao=prompt_customizado,
                    instrucoes_adicionais=instrucoes_extras,
                    versao=versao,
                    conceito_anterior=conceito_anterior,
                    status='pronto'
                )
                
                # Salvar imagem
                filename = f"conceito_{briefing.projeto.id}_v{versao}.png"
                from django.core.files.base import ContentFile
                file_content = ContentFile(resultado_imagem['image_data'])
                conceito.imagem.save(filename, file_content, save=False)
                conceito.save()
                
                return {
                    'success': True,
                    'conceito': conceito,
                    'prompt_usado': prompt_customizado
                }
            else:
                return {
                    'success': False,
                    'error': resultado_imagem['error'],
                    'details': resultado_imagem.get('details', '')
                }
                
        except Exception as e:
            logger.error(f"Erro ao gerar conceito visual: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }
    
    def _construir_prompt_com_planta(self, briefing, planta_baixa, estilo, iluminacao, instrucoes_extras):
        """
        Constrói prompt incluindo informações da planta baixa
        """
        # Obter dados da planta baixa
        dados_planta = planta_baixa.dados_json if planta_baixa.dados_json else {}
        
        # Extrair informações relevantes
        area_total = dados_planta.get('area_total', 'não especificada')
        ambientes = dados_planta.get('ambientes', [])
        
        # Listar ambientes
        lista_ambientes = []
        for ambiente in ambientes:
            nome = ambiente.get('nome', 'Ambiente')
            area = ambiente.get('area', 0)
            lista_ambientes.append(f"- {nome} ({area:.1f}m²)")
        
        ambientes_texto = '\n'.join(lista_ambientes) if lista_ambientes else "- Espaço principal"
        
        # Informações do briefing
        nome_projeto = briefing.projeto.nome
        tipo_stand = briefing.tipo_stand or 'personalizado'
        estilo_estande = briefing.estilo_estande or 'moderno'
        
        # Construir prompt
        prompt = f"""
        Crie uma imagem {estilo} em perspectiva 3/4 de um estande de feira com {iluminacao}.
        
        PROJETO: {nome_projeto}
        TIPO: {tipo_stand}
        ESTILO: {estilo_estande}
        
        LAYOUT BASEADO NA PLANTA BAIXA:
        - Área total: {area_total}m²
        - Ambientes:
        {ambientes_texto}
        
        REQUISITOS:
        - Vista em perspectiva mostrando fachada e lateral
        - Layout interno coerente com a planta baixa
        - Materiais e acabamentos adequados ao estilo
        - Iluminação {iluminacao} realista
        - Logotipo visível na entrada
        - Fluxo de visitantes bem definido
        
        {instrucoes_extras}
        """
        
        return prompt.strip()
