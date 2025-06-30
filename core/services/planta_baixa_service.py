# core/services/planta_baixa_service.py - VERSÃO CORRIGIDA

import json
import math
from typing import Dict, List, Tuple, Optional
from django.core.files.base import ContentFile
from django.utils import timezone
from io import StringIO

from projetista.models import PlantaBaixa
from projetos.models import Briefing
import logging

logger = logging.getLogger(__name__)

class PlantaBaixaService:
    """
    Serviço para geração algorítmica de plantas baixas com validação rigorosa
    """
    
    # Constantes para cálculo de áreas
    CIRCULACAO_PERCENTUAL = 0.25  # 25% da área para circulação
    AREA_MINIMA_AMBIENTE = 4.0    # m² mínimo por ambiente
    LARGURA_CORREDOR = 1.2        # metros
    
    # Dimensões padrão por tipo de ambiente (largura x profundidade em metros)
    DIMENSOES_PADRAO = {
        'recepcao': {'min': (2.0, 2.0), 'ideal': (3.0, 3.0)},
        'exposicao': {'min': (3.0, 3.0), 'ideal': (4.0, 4.0)},
        'reuniao': {'min': (2.5, 3.0), 'ideal': (3.5, 4.0)},
        'copa': {'min': (1.5, 2.0), 'ideal': (2.0, 3.0)},
        'deposito': {'min': (1.5, 1.5), 'ideal': (2.0, 2.5)},
        'escritorio': {'min': (2.0, 2.5), 'ideal': (3.0, 3.5)},
        'demonstracao': {'min': (3.0, 3.0), 'ideal': (4.0, 5.0)},
        'balcao': {'min': (1.0, 2.0), 'ideal': (1.5, 3.0)}
    }

    def __init__(self):
        self.algoritmo_versao = "layout_generator_v2_fixed"

    def gerar_planta_baixa(self, briefing: Briefing, versao: int = 1, 
                          planta_anterior: PlantaBaixa = None) -> Dict:
        """
        MÉTODO PRINCIPAL: Valida tudo antes de gerar qualquer coisa
        """
        try:
            logger.info(f"🚀 Iniciando geração de planta baixa para projeto {briefing.projeto.nome}")
            
            # 📋 ETAPA 1: Validar se briefing tem dados mínimos
            if not self._briefing_tem_dados_minimos(briefing):
                return {
                    'success': False,
                    'error': 'Briefing incompleto - preencha pelo menos a área ou dimensões do estande',
                    'critica': '❌ DADOS INSUFICIENTES: Complete as informações do estande no briefing',
                    'pode_prosseguir': False,
                    'sugestoes': [
                        'Preencha a área total do estande OU',
                        'Preencha as medidas (frente × fundo) do estande',
                        'Defina pelo menos uma área de exposição'
                    ]
                }
            
            # 📋 ETAPA 2: Extrair dados do briefing
            dados_estande = self._extrair_dados_briefing(briefing)
            
            if not dados_estande['valido']:
                return {
                    'success': False,
                    'error': dados_estande['erro'],
                    'critica': f"❌ DADOS INVÁLIDOS: {dados_estande['erro']}",
                    'pode_prosseguir': False,
                    'detalhes': dados_estande
                }
            
            # 🏠 ETAPA 3: Mapear todos os ambientes solicitados
            ambientes_solicitados = self._mapear_ambientes_briefing(briefing)
            
            if not ambientes_solicitados:
                # Criar ambiente mínimo padrão se não há nenhum especificado
                area_padrao = min(dados_estande['area_total'] * 0.6, 12.0)
                ambientes_solicitados = [{
                    'tipo': 'exposicao',
                    'nome': 'Área de Exposição Principal',
                    'area_solicitada': area_padrao,
                    'prioridade': 'alta',
                    'adjacente_entrada': True,
                    'fonte': 'padrao_gerado'
                }]
                logger.info(f"Criado ambiente padrão de exposição com {area_padrao:.1f}m²")
            
            # ⚖️ ETAPA 4: VALIDAÇÃO CRÍTICA DE ESPAÇO
            validacao = self._validar_compatibilidade_espacial(dados_estande, ambientes_solicitados)
            
            if not validacao['pode_prosseguir']:
                # 🛑 PARAR AQUI! Não tentar gerar nada
                return {
                    'success': False,
                    'error': validacao['erro_principal'],
                    'critica': validacao['critica_detalhada'],
                    'detalhes_validacao': validacao,
                    'dados_estande': dados_estande,
                    'ambientes_solicitados': ambientes_solicitados,
                    'pode_prosseguir': False,
                    'sugestoes': validacao['sugestoes']
                }
            
            # ✅ SE CHEGOU ATÉ AQUI: Pode prosseguir para geração
            logger.info(f"✅ Validação passou - gerando planta baixa")
            
            # 🏗️ ETAPA 5: Calcular layout otimizado
            layout = self._calcular_layout_otimizado(dados_estande, ambientes_solicitados)
            
            if not layout or not layout.get('ambientes_posicionados'):
                return {
                    'success': False,
                    'error': 'Não foi possível posicionar os ambientes no espaço disponível',
                    'critica': '❌ LAYOUT IMPOSSÍVEL: Revise as dimensões ou reduza o número de ambientes',
                    'pode_prosseguir': False,
                    'dados_estande': dados_estande,
                    'ambientes_solicitados': ambientes_solicitados
                }
            
            # 🎨 ETAPA 6: Gerar SVG da planta
            try:
                svg_content = self._gerar_svg_planta(layout, dados_estande)
            except Exception as e:
                logger.error(f"Erro ao gerar SVG: {str(e)}")
                return {
                    'success': False,
                    'error': f'Erro ao gerar visualização da planta: {str(e)}',
                    'critica': '❌ ERRO NA VISUALIZAÇÃO: Layout calculado mas falha na geração do SVG',
                    'pode_prosseguir': False
                }
            
            # 💾 ETAPA 7: Criar objeto PlantaBaixa
            try:
                planta = self._criar_objeto_planta(
                    briefing, versao, layout, svg_content, 
                    dados_estande, planta_anterior
                )
            except Exception as e:
                logger.error(f"Erro ao salvar planta: {str(e)}")
                return {
                    'success': False,
                    'error': f'Erro ao salvar planta no banco: {str(e)}',
                    'critica': '❌ ERRO NO SALVAMENTO: Planta gerada mas não foi possível salvar',
                    'pode_prosseguir': False
                }
            
            logger.info(f"🎉 Planta baixa v{versao} gerada com sucesso!")
            
            return {
                'success': True,
                'planta': planta,
                'layout': layout,
                'validacao_ok': True,
                'critica': validacao['critica_detalhada'],
                'detalhes_validacao': validacao,
                'dados_estande': dados_estande,
                'ambientes_solicitados': ambientes_solicitados,
                'pode_prosseguir': True,
                'message': f'Planta baixa v{versao} gerada com sucesso! Área utilizada: {layout.get("area_total_usada", 0):.1f}m²'
            }
            
        except Exception as e:
            logger.error(f"❌ Erro geral na geração: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': f'Erro técnico na geração: {str(e)}',
                'critica': f'❌ ERRO TÉCNICO: {str(e)}',
                'pode_prosseguir': False,
                'stack_trace': str(e) if logger.isEnabledFor(logging.DEBUG) else None
            }

    def _briefing_tem_dados_minimos(self, briefing: Briefing) -> bool:
        """
        Verifica se o briefing tem dados mínimos para gerar planta
        """
        # Verificar se tem área OU dimensões
        tem_area = briefing.area_estande and briefing.area_estande > 0
        tem_dimensoes = (briefing.medida_frente and briefing.medida_frente > 0 and 
                        briefing.medida_fundo and briefing.medida_fundo > 0)
        
        if not (tem_area or tem_dimensoes):
            logger.warning("Briefing sem área nem dimensões definidas")
            return False
        
        # Verificar se tem pelo menos uma área definida ou permitir ambiente padrão
        # (removemos a obrigatoriedade de ter áreas específicas - criaremos padrão se necessário)
        
        return True

    def _extrair_dados_briefing(self, briefing: Briefing) -> Dict:
        """
        Extrai e valida dados básicos do estande do briefing - VERSÃO MAIS ROBUSTA
        """
        dados = {
            'valido': False,
            'erro': '',
            'area_total': 0,
            'largura': 0,
            'profundidade': 0,
            'fonte_dados': '',
            'observacoes': []
        }
        
        try:
            # Tentar obter área total
            if briefing.area_estande and briefing.area_estande > 0:
                dados['area_total'] = float(briefing.area_estande)
                dados['fonte_dados'] = 'area_informada'
                dados['observacoes'].append(f"Área total: {dados['area_total']:.1f}m²")
            
            # Tentar obter dimensões específicas
            if (briefing.medida_frente and briefing.medida_frente > 0 and 
                briefing.medida_fundo and briefing.medida_fundo > 0):
                
                dados['largura'] = float(briefing.medida_frente)
                dados['profundidade'] = float(briefing.medida_fundo)
                area_calculada = dados['largura'] * dados['profundidade']
                
                # Se não tínhamos área, usar a calculada
                if dados['area_total'] == 0:
                    dados['area_total'] = area_calculada
                    dados['fonte_dados'] = 'dimensoes_calculadas'
                    dados['observacoes'].append(f"Área calculada: {dados['largura']:.1f}m × {dados['profundidade']:.1f}m = {dados['area_total']:.1f}m²")
                
                # Se tínhamos área mas não bate, alertar mas usar a área informada
                elif abs(dados['area_total'] - area_calculada) > 1:
                    diferenca = abs(dados['area_total'] - area_calculada)
                    dados['observacoes'].append(f"⚠️ Inconsistência: área informada ({dados['area_total']:.1f}m²) vs calculada ({area_calculada:.1f}m²)")
                    # Usar a área informada (prioridade), mas manter dimensões proporcionais
                    ratio = dados['area_total'] / area_calculada
                    dados['largura'] = dados['largura'] * math.sqrt(ratio)
                    dados['profundidade'] = dados['profundidade'] * math.sqrt(ratio)
                    dados['observacoes'].append(f"Ajustando dimensões proporcionalmente para {dados['largura']:.1f}m × {dados['profundidade']:.1f}m")
            
            # Se não temos dimensões específicas mas temos área, assumir formato retangular otimizado
            if dados['area_total'] > 0 and (dados['largura'] == 0 or dados['profundidade'] == 0):
                # Usar proporção áurea aproximada (1.6:1) para estandes
                ratio = 1.6
                dados['profundidade'] = math.sqrt(dados['area_total'] / ratio)
                dados['largura'] = dados['area_total'] / dados['profundidade']
                dados['observacoes'].append(f"Assumindo formato retangular: {dados['largura']:.1f}m × {dados['profundidade']:.1f}m")
            
            # Validações de segurança
            if dados['area_total'] <= 0:
                dados['erro'] = 'Área do estande deve ser maior que zero. Preencha a área total ou as dimensões.'
                return dados
            
            if dados['area_total'] < 4:
                dados['erro'] = f'Área muito pequena ({dados["area_total"]:.1f}m²). Estandes precisam de pelo menos 4m² para serem viáveis.'
                return dados
            
            if dados['area_total'] > 2000:
                dados['erro'] = f'Área muito grande ({dados["area_total"]:.1f}m²). Verifique se os dados estão corretos (máximo 2000m²).'
                return dados
            
            # Validar dimensões mínimas
            if dados['largura'] < 1.5 or dados['profundidade'] < 1.5:
                dados['erro'] = f'Dimensões muito pequenas ({dados["largura"]:.1f}m × {dados["profundidade"]:.1f}m). Mínimo 1.5m em cada lado.'
                return dados
            
            if dados['largura'] > 100 or dados['profundidade'] > 100:
                dados['erro'] = f'Dimensões muito grandes ({dados["largura"]:.1f}m × {dados["profundidade"]:.1f}m). Máximo 100m em cada lado.'
                return dados
            
            dados['valido'] = True
            return dados
            
        except (ValueError, TypeError, AttributeError) as e:
            dados['erro'] = f'Erro ao processar dados do briefing: {str(e)}'
            logger.error(f"Erro na extração de dados: {str(e)}")
            return dados

    def _mapear_ambientes_briefing(self, briefing: Briefing) -> List[Dict]:
        """
        Mapeia todos os ambientes solicitados no briefing - VERSÃO MAIS ROBUSTA
        """
        ambientes = []
        
        try:
            # Áreas de exposição
            if hasattr(briefing, 'areas_exposicao'):
                for area_exp in briefing.areas_exposicao.all():
                    ambiente = {
                        'tipo': 'exposicao',
                        'nome': 'Área de Exposição',
                        'area_solicitada': float(area_exp.metragem) if area_exp.metragem and area_exp.metragem > 0 else None,
                        'prioridade': 'alta',
                        'adjacente_entrada': True,
                        'equipamentos': getattr(area_exp, 'equipamentos', '') or '',
                        'observacoes': getattr(area_exp, 'observacoes', '') or '',
                        'fonte': 'briefing_areas_exposicao'
                    }
                    
                    # Detectar sub-ambientes baseado nos checkboxes
                    sub_ambientes = []
                    if getattr(area_exp, 'tem_lounge', False):
                        sub_ambientes.append('lounge')
                    if getattr(area_exp, 'tem_balcao_recepcao', False):
                        sub_ambientes.append('recepção')
                    if getattr(area_exp, 'tem_balcao_cafe', False):
                        sub_ambientes.append('café')
                    if getattr(area_exp, 'tem_caixa_vendas', False):
                        sub_ambientes.append('caixa')
                    
                    if sub_ambientes:
                        ambiente['sub_ambientes'] = sub_ambientes
                        ambiente['observacoes'] += f" (inclui: {', '.join(sub_ambientes)})"
                    
                    ambientes.append(ambiente)
            
            # Salas de reunião
            if hasattr(briefing, 'salas_reuniao'):
                for sala in briefing.salas_reuniao.all():
                    ambientes.append({
                        'tipo': 'reuniao',
                        'nome': 'Sala de Reunião',
                        'area_solicitada': float(sala.metragem) if sala.metragem and sala.metragem > 0 else None,
                        'capacidade': getattr(sala, 'capacidade', 0) or 0,
                        'prioridade': 'media',
                        'privacidade': True,
                        'equipamentos': getattr(sala, 'equipamentos', '') or '',
                        'fonte': 'briefing_salas_reuniao'
                    })
            
            # Copas
            if hasattr(briefing, 'copas'):
                for copa in briefing.copas.all():
                    ambientes.append({
                        'tipo': 'copa',
                        'nome': 'Copa',
                        'area_solicitada': float(copa.metragem) if copa.metragem and copa.metragem > 0 else None,
                        'prioridade': 'baixa',
                        'necessita_agua': True,
                        'equipamentos': getattr(copa, 'equipamentos', '') or '',
                        'fonte': 'briefing_copas'
                    })
            
            # Depósitos
            if hasattr(briefing, 'depositos'):
                for deposito in briefing.depositos.all():
                    ambientes.append({
                        'tipo': 'deposito',
                        'nome': 'Depósito',
                        'area_solicitada': float(deposito.metragem) if deposito.metragem and deposito.metragem > 0 else None,
                        'prioridade': 'baixa',
                        'acesso_externo': True,
                        'equipamentos': getattr(deposito, 'equipamentos', '') or '',
                        'fonte': 'briefing_depositos'
                    })
            
        except Exception as e:
            logger.error(f"Erro ao mapear ambientes do briefing: {str(e)}")
            # Continuar sem interromper - se der erro, vai criar ambiente padrão depois
        
        return ambientes

    def _validar_compatibilidade_espacial(self, dados_estande: Dict, ambientes: List[Dict]) -> Dict:
        """
        VALIDAÇÃO CRÍTICA: Verifica se tudo cabe no espaço disponível - SEM PROTEÇÕES
        """
        validacao = {
            'pode_prosseguir': True,
            'erro_principal': '',
            'critica_detalhada': '',
            'problemas': [],
            'alertas': [],
            'sugestoes': [],
            'area_necessaria_total': 0,
            'area_disponivel': dados_estande['area_total'],
            'area_ambientes': 0,
            'area_circulacao': 0,
            'percentual_ocupacao': 0,
            'detalhes_ambientes': []
        }
        
        try:
            # Calcular área necessária para cada ambiente
            area_total_ambientes = 0
            ambientes_grandes = []  # Para identificar problemas
            
            for ambiente in ambientes:
                area_necessaria = 0
                fonte_area = ''
                justificativa = ''
                
                # Prioridade: área solicitada > área mínima por tipo > área padrão
                if ambiente.get('area_solicitada') and ambiente['area_solicitada'] > 0:
                    area_necessaria = float(ambiente['area_solicitada'])
                    fonte_area = 'solicitada'
                    justificativa = f"Área informada no briefing: {area_necessaria:.1f}m²"
                    
                    # Identificar ambientes desproporcionais (sem limitar)
                    percentual = (area_necessaria / dados_estande['area_total']) * 100
                    if percentual > 40:
                        ambientes_grandes.append({
                            'nome': ambiente.get('nome', 'Ambiente'),
                            'area': area_necessaria,
                            'percentual': percentual
                        })
                        
                else:
                    # Calcular área mínima baseada no tipo
                    tipo = ambiente.get('tipo', 'exposicao')
                    if tipo in self.DIMENSOES_PADRAO:
                        dim_min = self.DIMENSOES_PADRAO[tipo]['min']
                        area_necessaria = dim_min[0] * dim_min[1]
                        fonte_area = 'minima_calculada'
                        justificativa = f"Área mínima para {tipo}: {dim_min[0]:.1f}m × {dim_min[1]:.1f}m = {area_necessaria:.1f}m²"
                    else:
                        area_necessaria = self.AREA_MINIMA_AMBIENTE
                        fonte_area = 'padrao_absoluto'
                        justificativa = f"Área mínima padrão: {area_necessaria:.1f}m²"
                
                # Aplicar área mínima absoluta (mantém apenas esta proteção básica)
                if area_necessaria < self.AREA_MINIMA_AMBIENTE:
                    area_original = area_necessaria
                    area_necessaria = self.AREA_MINIMA_AMBIENTE
                    fonte_area = 'ajustada_para_minimo'
                    justificativa += f" → Ajustada para mínimo de {self.AREA_MINIMA_AMBIENTE:.1f}m²"
                
                area_total_ambientes += area_necessaria
                
                # Registrar detalhes
                validacao['detalhes_ambientes'].append({
                    'nome': ambiente.get('nome', 'Sem nome'),
                    'tipo': ambiente.get('tipo', 'indefinido'),
                    'area_necessaria': area_necessaria,
                    'area_solicitada': ambiente.get('area_solicitada'),
                    'fonte_area': fonte_area,
                    'justificativa': justificativa,
                    'prioridade': ambiente.get('prioridade', 'media'),
                    'percentual_estande': (area_necessaria / dados_estande['area_total']) * 100
                })
            
            # Calcular área de circulação
            area_circulacao = area_total_ambientes * self.CIRCULACAO_PERCENTUAL
            
            # Áreas técnicas (instalações, etc.)
            area_tecnica = max(1.0, dados_estande['area_total'] * 0.02)
            
            area_total_necessaria = area_total_ambientes + area_circulacao + area_tecnica
            
            # Atualizar dados de validação
            validacao['area_ambientes'] = area_total_ambientes
            validacao['area_circulacao'] = area_circulacao
            validacao['area_necessaria_total'] = area_total_necessaria
            validacao['percentual_ocupacao'] = (area_total_necessaria / dados_estande['area_total']) * 100
            
            # 🚨 VERIFICAÇÕES CRÍTICAS
            
            if area_total_necessaria > dados_estande['area_total']:
                diferenca = area_total_necessaria - dados_estande['area_total']
                percentual_excesso = (diferenca / dados_estande['area_total']) * 100
                
                validacao['pode_prosseguir'] = False
                validacao['erro_principal'] = f"Espaço insuficiente: faltam {diferenca:.1f}m²"
                
                # Mensagem melhorada com análise dos problemas
                validacao['critica_detalhada'] = f"""Estande disponível: {dados_estande['area_total']:.1f}m²
    Necessários: {area_total_necessaria:.1f}m²

    AMBIENTES: {area_total_ambientes:.1f}m²"""
                
                # Detalhar cada ambiente com percentual
                for detalhe in validacao['detalhes_ambientes']:
                    validacao['critica_detalhada'] += f"\n   • {detalhe['nome']}: {detalhe['area_necessaria']:.1f}m² ({detalhe['percentual_estande']:.0f}% do estande)"

                validacao['critica_detalhada'] += f"""

    CIRCULAÇÃO: {area_circulacao:.1f}m²
    └─ Calculado como {self.CIRCULACAO_PERCENTUAL * 100:.0f}% da área dos ambientes
    └─ {area_total_ambientes:.1f}m² × {self.CIRCULACAO_PERCENTUAL:.0%} = {area_circulacao:.1f}m²

    INSTALAÇÕES TÉCNICAS: {area_tecnica:.1f}m²
    └─ Estruturas, elétrica, acabamentos

    SOMA TOTAL:
    {area_total_ambientes:.1f}m² + {area_circulacao:.1f}m² + {area_tecnica:.1f}m² = {area_total_necessaria:.1f}m²"""
            
            return validacao
            
        except Exception as e:
            logger.error(f"Erro na validação espacial: {str(e)}")
            validacao['pode_prosseguir'] = False
            validacao['erro_principal'] = f"Erro na validação: {str(e)}"
            validacao['critica_detalhada'] = f"❌ ERRO TÉCNICO NA VALIDAÇÃO: {str(e)}"
            return validacao

    def _gerar_svg_planta(self, layout: Dict, dados_estande: Dict) -> str:
        """
        Gera SVG da planta baixa - VERSÃO MAIS ROBUSTA
        """
        try:
            largura = layout['dimensoes']['largura']
            profundidade = layout['dimensoes']['profundidade']
            
            # Configuração do SVG com escala adaptativa
            scale = min(600 / max(largura, profundidade), 50)  # Escala adaptativa, máximo 50px/m
            margin = 50
            svg_width = largura * scale + 2 * margin
            svg_height = profundidade * scale + 2 * margin
            
            svg = StringIO()
            svg.write(f'''<?xml version="1.0" encoding="UTF-8"?>
<svg width="{svg_width}" height="{svg_height}" viewBox="0 0 {svg_width} {svg_height}" 
     xmlns="http://www.w3.org/2000/svg">
  <defs>
    <style>
      .ambiente {{ stroke: #333; stroke-width: 2; opacity: 0.9; }}
      .corredor {{ stroke: #666; stroke-width: 1; fill: #f0f0f0; opacity: 0.5; }}
      .entrada {{ stroke: #e74c3c; stroke-width: 4; fill: none; }}
      .texto {{ font-family: Arial, sans-serif; font-size: {max(10, scale/5)}px; text-anchor: middle; fill: white; font-weight: bold; }}
      .dimensao {{ font-family: Arial, sans-serif; font-size: {max(8, scale/6)}px; fill: #666; }}
      .borda {{ stroke: #000; stroke-width: 3; fill: none; }}
    </style>
  </defs>
  
  <!-- Background -->
  <rect x="{margin}" y="{margin}" width="{largura * scale}" height="{profundidade * scale}" 
        fill="white" class="borda"/>
''')
            
            # Desenhar corredores primeiro (atrás dos ambientes)
            for corredor in layout.get('areas_circulacao', []):
                x = margin + corredor['x'] * scale
                y = margin + corredor['y'] * scale
                w = corredor['largura'] * scale
                h = corredor['profundidade'] * scale
                
                svg.write(f'''  <rect x="{x}" y="{y}" width="{w}" height="{h}" 
                                  class="corredor" fill="{corredor['cor']}"/>
''')
            
            # Desenhar ambientes
            for ambiente in layout['ambientes_posicionados']:
                x = margin + ambiente['x'] * scale
                y = margin + ambiente['y'] * scale
                w = ambiente['largura'] * scale
                h = ambiente['profundidade'] * scale
                
                svg.write(f'''  <rect x="{x}" y="{y}" width="{w}" height="{h}" 
                                  class="ambiente" fill="{ambiente['cor']}"/>
''')
                
                # Texto do ambiente (apenas se tem espaço suficiente)
                if w > 40 and h > 25:  # Espaço mínimo para texto
                    text_x = x + w/2
                    text_y = y + h/2 - 5
                    svg.write(f'''  <text x="{text_x}" y="{text_y}" class="texto">
        {ambiente['nome'][:15]}{'...' if len(ambiente['nome']) > 15 else ''}
      </text>
''')
                    if h > 40:  # Espaço para segunda linha
                        svg.write(f'''  <text x="{text_x}" y="{text_y + 15}" class="texto" style="font-size: {max(8, scale/6)}px;">
        {ambiente['area']:.1f}m²
      </text>
''')
            
            # Desenhar entradas
            for entrada in layout.get('entradas', []):
                x = margin + entrada['x'] * scale
                y = margin + entrada['y'] * scale
                w = entrada['largura'] * scale
                
                svg.write(f'''  <line x1="{x}" y1="{y}" x2="{x + w}" y2="{y}" class="entrada"/>
  <text x="{x + w/2}" y="{y - 10}" class="dimensao" text-anchor="middle">ENTRADA</text>
''')
            
            # Dimensões e informações
            svg.write(f'''  
  <!-- Dimensões -->
  <text x="{margin/2}" y="{margin + profundidade * scale / 2}" class="dimensao" 
        text-anchor="middle" transform="rotate(-90, {margin/2}, {margin + profundidade * scale / 2})">
    {profundidade:.1f}m
  </text>
  <text x="{margin + largura * scale / 2}" y="{margin - 15}" class="dimensao" text-anchor="middle">
    {largura:.1f}m
  </text>
  
  <!-- Informações do projeto -->
  <text x="{margin + largura * scale}" y="{margin + profundidade * scale + 25}" 
        class="dimensao" text-anchor="end">
    Área Total: {dados_estande['area_total']:.1f}m² | Utilizada: {layout.get('area_total_usada', 0):.1f}m²
  </text>
  
  <!-- Legenda de cores -->
  <g transform="translate({margin}, {margin + profundidade * scale + 40})">
    <text x="0" y="0" class="dimensao" style="font-weight: bold;">Legenda:</text>
''')
            
            # Gerar legenda baseada nos ambientes presentes
            tipos_presentes = list(set(amb['tipo'] for amb in layout['ambientes_posicionados']))
            for i, tipo in enumerate(tipos_presentes):
                cor = self._get_cor_ambiente(tipo)
                x_legenda = i * 80
                svg.write(f'''    <rect x="{x_legenda}" y="10" width="12" height="12" fill="{cor}" stroke="#333"/>
    <text x="{x_legenda + 16}" y="20" class="dimensao">{tipo.title()}</text>
''')
            
            svg.write('''  </g>
</svg>''')
            
            return svg.getvalue()
            
        except Exception as e:
            logger.error(f"Erro na geração do SVG: {str(e)}")
            # Retornar SVG de erro simples
            return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg width="400" height="200" xmlns="http://www.w3.org/2000/svg">
  <rect width="400" height="200" fill="#fff" stroke="#ccc"/>
  <text x="200" y="100" text-anchor="middle" font-family="Arial" font-size="14" fill="#666">
    Erro ao gerar visualização: {str(e)[:50]}
  </text>
</svg>'''

    def _criar_objeto_planta(self, briefing: Briefing, versao: int, layout: Dict, 
                           svg_content: str, dados_estande: Dict, 
                           planta_anterior: PlantaBaixa = None) -> PlantaBaixa:
        """
        Cria e salva objeto PlantaBaixa no banco - VERSÃO ROBUSTA
        """
        try:
            # Preparar dados JSON estruturados
            dados_json = {
                'layout': layout,
                'dados_estande': dados_estande,
                'area_total': dados_estande['area_total'],
                'ambientes': layout['ambientes_posicionados'],
                'metadata': {
                    'algoritmo': self.algoritmo_versao,
                    'gerado_em': timezone.now().isoformat(),
                    'versao': versao,
                    'ambientes_posicionados': len(layout['ambientes_posicionados']),
                    'area_utilizada': layout.get('area_total_usada', 0)
                }
            }
            
            # Parâmetros de geração
            parametros_geracao = {
                'considerou_areas_especificas': True,
                'validacao_espaco': True,
                'algoritmo_layout': 'empacotamento_otimizado_v2',
                'area_circulacao_percentual': self.CIRCULACAO_PERCENTUAL,
                'grid_resolucao': 0.5,
                'dimensoes_estande': f"{dados_estande['largura']:.1f}x{dados_estande['profundidade']:.1f}m"
            }
            
            # Criar objeto PlantaBaixa
            planta = PlantaBaixa(
                projeto=briefing.projeto,
                briefing=briefing,
                projetista=briefing.projeto.projetista,
                versao=versao,
                planta_anterior=planta_anterior,
                algoritmo_usado=self.algoritmo_versao,
                parametros_geracao=parametros_geracao,
                dados_json=dados_json,
                status='pronta'
            )
            
            # Salvar arquivo SVG
            arquivo_svg = ContentFile(svg_content.encode('utf-8'))
            nome_arquivo = f"planta_baixa_v{versao}_{briefing.projeto.numero}_{timezone.now().strftime('%Y%m%d_%H%M%S')}.svg"
            planta.arquivo_svg.save(nome_arquivo, arquivo_svg)
            
            planta.save()
            
            logger.info(f"Planta baixa v{versao} salva com sucesso: {nome_arquivo}")
            return planta
            
        except Exception as e:
            logger.error(f"Erro ao criar objeto planta: {str(e)}", exc_info=True)
            raise Exception(f"Falha ao salvar planta baixa: {str(e)}")

    def _calcular_layout_otimizado(self, dados_estande: Dict, ambientes_solicitados: List[Dict]) -> Dict:
        """
        Calcula layout otimizado posicionando ambientes no espaço disponível
        """
        try:
            largura = dados_estande['largura']
            profundidade = dados_estande['profundidade']
            
            # Inicializar grid de ocupação
            grid_res = 0.5  # Resolução do grid em metros
            grid_largura = int(largura / grid_res) + 1
            grid_profundidade = int(profundidade / grid_res) + 1
            grid_ocupado = [[False for _ in range(grid_profundidade)] for _ in range(grid_largura)]
            
            # Layout resultado
            layout = {
                'dimensoes': {
                    'largura': largura,
                    'profundidade': profundidade,
                    'area_total': dados_estande['area_total']
                },
                'ambientes_posicionados': [],
                'areas_circulacao': [],
                'entradas': [],
                'area_total_usada': 0,
                'taxa_ocupacao': 0
            }
            
            # Ordenar ambientes por prioridade (alta -> média -> baixa)
            prioridade_ordem = {'alta': 1, 'media': 2, 'baixa': 3}
            ambientes_ordenados = sorted(
                ambientes_solicitados,
                key=lambda x: prioridade_ordem.get(x.get('prioridade', 'media'), 2)
            )
            
            logger.info(f"Posicionando {len(ambientes_ordenados)} ambientes em {largura:.1f}x{profundidade:.1f}m")
            
            # Posicionar cada ambiente
            for ambiente in ambientes_ordenados:
                posicao = self._encontrar_melhor_posicao(
                    ambiente, grid_ocupado, largura, profundidade, layout, grid_res
                )
                
                if posicao:
                    layout['ambientes_posicionados'].append(posicao)
                    self._marcar_area_ocupada(grid_ocupado, posicao, grid_res)
                    layout['area_total_usada'] += posicao['area']
                    logger.info(f"✅ Posicionado: {posicao['nome']} ({posicao['area']:.1f}m²)")
                else:
                    logger.warning(f"❌ Não foi possível posicionar: {ambiente.get('nome', 'Ambiente')}")
                    # Se é um ambiente de alta prioridade e não conseguiu posicionar, falha
                    if ambiente.get('prioridade') == 'alta':
                        logger.error(f"Falha crítica: ambiente de alta prioridade não posicionado")
                        return None
            
            # Adicionar entrada principal
            layout['entradas'] = [{
                'tipo': 'entrada_principal',
                'x': largura / 2 - 1.0,  # Entrada de 2m no centro da frente
                'y': 0,
                'largura': 2.0,
                'cor': '#e74c3c'
            }]
            
            # Calcular áreas de circulação
            layout['areas_circulacao'] = self._calcular_areas_circulacao(
                layout['ambientes_posicionados'], largura, profundidade
            )
            
            # Calcular estatísticas finais
            layout['taxa_ocupacao'] = (layout['area_total_usada'] / dados_estande['area_total']) * 100
            
            logger.info(f"Layout concluído: {len(layout['ambientes_posicionados'])} ambientes, {layout['area_total_usada']:.1f}m² utilizados ({layout['taxa_ocupacao']:.1f}%)")
            
            return layout
            
        except Exception as e:
            logger.error(f"Erro no cálculo de layout: {str(e)}", exc_info=True)
            return None

    def _encontrar_melhor_posicao(self, ambiente: Dict, grid_ocupado: List[List[bool]], 
                                largura: float, profundidade: float, layout: Dict, 
                                grid_res: float = 0.5) -> Optional[Dict]:
        """
        Encontra a melhor posição para um ambiente - VERSÃO MAIS ROBUSTA
        """
        try:
            tipo = ambiente.get('tipo', 'exposicao')
            nome = ambiente.get('nome', 'Ambiente')
            
            # Calcular dimensões do ambiente
            if ambiente.get('area_solicitada') and ambiente['area_solicitada'] > 0:
                area = float(ambiente['area_solicitada'])
                # Tentar manter proporções ideais do tipo
                if tipo in self.DIMENSOES_PADRAO:
                    dim_ideal = self.DIMENSOES_PADRAO[tipo]['ideal']
                    ratio = dim_ideal[0] / dim_ideal[1]
                    amb_largura = math.sqrt(area * ratio)
                    amb_profundidade = area / amb_largura
                else:
                    # Formato quadrado por padrão
                    amb_largura = math.sqrt(area)
                    amb_profundidade = amb_largura
            else:
                # Usar dimensões ideais padrão
                dimensoes = self.DIMENSOES_PADRAO.get(tipo, {'ideal': (3.0, 3.0)})
                amb_largura = dimensoes['ideal'][0]
                amb_profundidade = dimensoes['ideal'][1]
                area = amb_largura * amb_profundidade
            
            # Ajustar se não couber nas dimensões do estande
            margem = 0.3  # Margem de segurança
            if amb_largura > largura - margem:
                amb_largura = largura - margem
            if amb_profundidade > profundidade - margem:
                amb_profundidade = profundidade - margem
            
            # Recalcular área se houve ajuste
            area = amb_largura * amb_profundidade
            
            # Garantir dimensões mínimas
            if amb_largura < 1.5:
                amb_largura = 1.5
            if amb_profundidade < 1.5:
                amb_profundidade = 1.5
            
            # Tentar diferentes posições (estratégias específicas por tipo)
            posicoes_candidatas = self._gerar_posicoes_candidatas_robusta(
                ambiente, amb_largura, amb_profundidade, largura, profundidade
            )
            
            # Testar cada posição candidata
            for x, y in posicoes_candidatas:
                # Verificar se a posição está dentro dos limites
                if (x >= 0 and y >= 0 and 
                    x + amb_largura <= largura and 
                    y + amb_profundidade <= profundidade):
                    
                    if self._posicao_disponivel_robusta(grid_ocupado, x, y, amb_largura, amb_profundidade, grid_res):
                        return {
                            'tipo': tipo,
                            'nome': nome,
                            'x': round(x, 2),
                            'y': round(y, 2),
                            'largura': round(amb_largura, 2),
                            'profundidade': round(amb_profundidade, 2),
                            'area': round(area, 2),
                            'cor': self._get_cor_ambiente(tipo),
                            'prioridade': ambiente.get('prioridade', 'media')
                        }
            
            logger.warning(f"Não foi possível encontrar posição para {nome}")
            return None
            
        except Exception as e:
            logger.error(f"Erro ao encontrar posição para ambiente: {str(e)}")
            return None

    def _gerar_posicoes_candidatas_robusta(self, ambiente: Dict, amb_largura: float, 
                                        amb_profundidade: float, largura: float, 
                                        profundidade: float) -> List[Tuple[float, float]]:
        """
        Gera lista de posições candidatas priorizadas e robustas
        """
        posicoes = []
        tipo = ambiente.get('tipo', 'exposicao')
        
        try:
            # Estratégias específicas por tipo
            if tipo == 'exposicao' or ambiente.get('adjacente_entrada'):
                # Próximo à entrada (frente) ou posições centrais
                posicoes.extend([
                    (0, 0),  # Canto frontal esquerdo
                    (largura - amb_largura, 0),  # Canto frontal direito
                    (largura/2 - amb_largura/2, 0),  # Centro da frente
                    (largura/2 - amb_largura/2, profundidade/4),  # Centro-frente
                ])
            
            elif tipo in ['reuniao', 'escritorio']:
                # Áreas mais reservadas (fundos e cantos)
                posicoes.extend([
                    (largura - amb_largura, profundidade - amb_profundidade),  # Canto fundo direito
                    (0, profundidade - amb_profundidade),  # Canto fundo esquerdo
                    (largura/2 - amb_largura/2, profundidade - amb_profundidade),  # Centro do fundo
                ])
            
            elif tipo in ['copa', 'deposito']:
                # Cantos e áreas de menor visibilidade
                posicoes.extend([
                    (0, profundidade - amb_profundidade),  # Canto fundo esquerdo
                    (largura - amb_largura, profundidade - amb_profundidade),  # Canto fundo direito
                    (0, 0),  # Canto frontal esquerdo
                    (largura - amb_largura, 0),  # Canto frontal direito
                ])
            
            # Adicionar grid sistemático como fallback
            step_x = max(0.5, amb_largura / 3)  # Passos menores para maior precisão
            step_y = max(0.5, amb_profundidade / 3)
            
            for x in [i * step_x for i in range(int((largura - amb_largura) / step_x) + 1)]:
                for y in [i * step_y for i in range(int((profundidade - amb_profundidade) / step_y) + 1)]:
                    if x <= largura - amb_largura and y <= profundidade - amb_profundidade:
                        posicoes.append((round(x, 2), round(y, 2)))
            
            # Remover duplicatas mantendo ordem
            posicoes_unicas = []
            for pos in posicoes:
                if pos not in posicoes_unicas:
                    posicoes_unicas.append(pos)
            
            return posicoes_unicas
            
        except Exception as e:
            logger.error(f"Erro ao gerar posições candidatas: {str(e)}")
            # Retornar pelo menos a posição origem como fallback
            return [(0, 0)]

    def _posicao_disponivel_robusta(self, grid_ocupado: List[List[bool]], x: float, y: float, 
                                largura: float, profundidade: float, grid_res: float = 0.5) -> bool:
        """
        Verifica se uma posição está disponível no grid - VERSÃO ROBUSTA
        """
        try:
            # Converter coordenadas para índices do grid
            grid_x_start = max(0, int(x / grid_res))
            grid_y_start = max(0, int(y / grid_res))
            grid_x_end = min(len(grid_ocupado), int((x + largura) / grid_res) + 1)
            grid_y_end = min(len(grid_ocupado[0]), int((y + profundidade) / grid_res) + 1)
            
            # Verificar limites
            if (grid_x_end > len(grid_ocupado) or 
                grid_y_end > len(grid_ocupado[0]) or
                grid_x_start < 0 or grid_y_start < 0):
                return False
            
            # Verificar se toda a área está livre
            for gx in range(grid_x_start, grid_x_end):
                for gy in range(grid_y_start, grid_y_end):
                    if gx < len(grid_ocupado) and gy < len(grid_ocupado[0]):
                        if grid_ocupado[gx][gy]:
                            return False
            
            return True
            
        except (IndexError, ValueError) as e:
            logger.error(f"Erro na verificação de posição: {str(e)}")
            return False

    def _marcar_area_ocupada(self, grid_ocupado: List[List[bool]], posicao: Dict, grid_res: float = 0.5):
        """
        Marca uma área como ocupada no grid - VERSÃO ROBUSTA
        """
        try:
            x, y = posicao['x'], posicao['y']
            largura, profundidade = posicao['largura'], posicao['profundidade']
            
            grid_x_start = max(0, int(x / grid_res))
            grid_y_start = max(0, int(y / grid_res))
            grid_x_end = min(len(grid_ocupado), int((x + largura) / grid_res) + 1)
            grid_y_end = min(len(grid_ocupado[0]), int((y + profundidade) / grid_res) + 1)
            
            for gx in range(grid_x_start, grid_x_end):
                for gy in range(grid_y_start, grid_y_end):
                    if gx < len(grid_ocupado) and gy < len(grid_ocupado[0]):
                        grid_ocupado[gx][gy] = True
                        
        except (IndexError, ValueError) as e:
            logger.error(f"Erro ao marcar área ocupada: {str(e)}")

    def _calcular_areas_circulacao(self, ambientes: List[Dict], largura: float, 
                                profundidade: float) -> List[Dict]:
        """
        Calcula áreas de circulação (corredores)
        """
        corredores = []
        
        try:
            if len(ambientes) > 1:
                # Corredor horizontal central
                corredor_y = profundidade / 2
                corredor_largura = min(self.LARGURA_CORREDOR, profundidade * 0.15)
                
                corredores.append({
                    'tipo': 'corredor_horizontal',
                    'x': 0,
                    'y': corredor_y - corredor_largura/2,
                    'largura': largura,
                    'profundidade': corredor_largura,
                    'cor': '#f8f9fa'
                })
                
                # Se tiver muitos ambientes, adicionar corredor vertical
                if len(ambientes) > 3:
                    corredor_x = largura / 2
                    corredor_prof = min(self.LARGURA_CORREDOR, largura * 0.1)
                    
                    corredores.append({
                        'tipo': 'corredor_vertical',
                        'x': corredor_x - corredor_prof/2,
                        'y': 0,
                        'largura': corredor_prof,
                        'profundidade': profundidade,
                        'cor': '#f0f0f0'
                    })
            
        except Exception as e:
            logger.error(f"Erro ao calcular circulação: {str(e)}")
        
        return corredores

    def _get_cor_ambiente(self, tipo: str) -> str:
        """
        Retorna cor para visualização por tipo de ambiente
        """
        cores = {
            'recepcao': '#4CAF50',      # Verde
            'exposicao': '#2196F3',     # Azul
            'reuniao': '#FF9800',       # Laranja
            'copa': '#9C27B0',          # Roxo
            'deposito': '#607D8B',      # Azul acinzentado
            'escritorio': '#795548',    # Marrom
            'demonstracao': '#E91E63',  # Rosa
            'balcao': '#00BCD4'         # Ciano
        }
        return cores.get(tipo, '#9E9E9E')  # Cinza padrão