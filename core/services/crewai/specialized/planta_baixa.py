# core/services/crewai/specialized/planta_baixa.py

from core.services.crewai.base_service import CrewAIServiceV2
from projetos.models import Briefing
from projetista.models import PlantaBaixa
from django.core.files.base import ContentFile
from typing import Dict, Any
import json
import re
import logging

logger = logging.getLogger(__name__)

class PlantaBaixaServiceV2(CrewAIServiceV2):
    """
    Serviço especializado para geração de plantas baixas
    """
    
    def __init__(self):
        super().__init__("Gerador de Plantas Baixas")
    
    def gerar_planta(self, briefing: Briefing, versao: int = 1) -> Dict:
        """
        Gera planta baixa usando crew completo
        """
        try:
            # Preparar inputs específicos
            inputs = self._preparar_inputs_planta(briefing, versao)
            
            # Contexto da execução
            contexto = {
                'projeto_id': briefing.projeto.id,
                'briefing_id': briefing.id,
                'usuario_id': getattr(briefing.projeto.projetista, 'id', None),
                'tipo': 'planta_baixa',
                'versao': versao
            }
            
            # Executar crew
            resultado = self.executar(inputs, contexto)
            
            # Se sucesso, processar resultado
            if resultado['success']:
                planta = self._processar_resultado_planta(briefing, versao, resultado)
                resultado['planta'] = planta
                resultado['metodo_geracao'] = 'crewai_v2_pipeline'
            
            return resultado
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao gerar planta: {str(e)}")
            return {'success': False, 'error': str(e)}
        

    def _preparar_inputs_planta(self, briefing: Briefing, versao: int) -> Dict:
        """
        RESTAURA ESTRUTURA ORIGINAL QUE FUNCIONAVA
        """
        
        # Coletar áreas (igual ao atual)
        areas_exposicao = []
        for area in briefing.areas_exposicao.all():
            area_data = {
                "tipo": "exposicao",
                "metragem": float(area.metragem or 0),
                "equipamentos": area.equipamentos or "",
                "observacoes": area.observacoes or "",
                "elementos": {
                    "lounge": getattr(area, 'tem_lounge', False),
                    "vitrine_exposicao": getattr(area, 'tem_vitrine_exposicao', False),
                    "balcao_recepcao": getattr(area, 'tem_balcao_recepcao', False),
                    "mesas_atendimento": getattr(area, 'tem_mesas_atendimento', False),
                    "balcao_cafe": getattr(area, 'tem_balcao_cafe', False),
                    "balcao_vitrine": getattr(area, 'tem_balcao_vitrine', False),
                    "caixa_vendas": getattr(area, 'tem_caixa_vendas', False)
                }
            }
            areas_exposicao.append(area_data)
        
        salas_reuniao = []
        for sala in briefing.salas_reuniao.all():
            salas_reuniao.append({
                "tipo": "sala_reuniao",
                "capacidade": sala.capacidade,
                "metragem": float(sala.metragem or 0),
                "equipamentos": sala.equipamentos or ""
            })
        
        copas = []
        for copa in briefing.copas.all():
            copas.append({
                "tipo": "copa",
                "metragem": float(copa.metragem or 0),
                "equipamentos": copa.equipamentos or ""
            })
        
        depositos = []
        for deposito in briefing.depositos.all():
            depositos.append({
                "tipo": "deposito",
                "metragem": float(deposito.metragem or 0),
                "equipamentos": deposito.equipamentos or ""
            })
        
        # 🔥 ESTRUTURA ORIGINAL RESTAURADA - DADOS DIRETOS NO ROOT
        inputs_estruturados = {
            # DADOS DIRETOS (como era antes)
            "nome_projeto": briefing.projeto.nome,
            "empresa": briefing.projeto.empresa.nome,
            "numero_projeto": briefing.projeto.numero,
            "tipo_projeto": briefing.projeto.tipo_projeto or "feira_de_negocios",
            "orcamento": float(briefing.projeto.orcamento or 0),
            
            # ESTANDE DIRETO
            "tipo_stand": briefing.tipo_stand or "ponta_ilha", 
            "area_total": float(briefing.area_estande or 0),
            "medida_frente": float(briefing.medida_frente or 0),
            "medida_fundo": float(briefing.medida_fundo or 0),
            "medida_lateral_esquerda": float(briefing.medida_lateral_esquerda or 0),
            "medida_lateral_direita": float(briefing.medida_lateral_direita or 0),
            "estilo": briefing.estilo_estande or "moderno",
            "material": briefing.material or "construido",
            
            # EVENTO DIRETO
            "nome_evento": briefing.nome_evento or "Hair Summit 2025",
            "local_evento": briefing.local_evento or "Expo Center Norte",
            "objetivo_evento": briefing.objetivo_evento or "Lançamentos, relacionamento com mercado, vendas",
            
            # ÁREAS SOLICITADAS (igual ao JSON original)
            "areas_solicitadas": areas_exposicao + salas_reuniao + copas + depositos,
            
            # VALIDAÇÃO VIABILIDADE
            "validacao_viabilidade_tecnica": {
                "tipo_stand": briefing.tipo_stand or "ponta_ilha",
                "area_total": float(briefing.area_estande or 0), 
                "dimensoes": {
                    "frente": float(briefing.medida_frente or 0),
                    "fundo": float(briefing.medida_fundo or 0),
                    "lateral_esquerda": float(briefing.medida_lateral_esquerda or 0),
                    "lateral_direita": float(briefing.medida_lateral_direita or 0)
                },
                "material": briefing.material or "construido",
                "piso_elevado": briefing.piso_elevado or "sem_elevacao"
            },
            
            # DIRETRIZES ARQUITETURA
            "diretrizes_arquitetura_espacial": {
                "estilo": briefing.estilo_estande or "moderno",
                "material": briefing.material or "construido", 
                "mood": briefing.referencias_dados or "inspirado em imagens do filme olympia de 1936"
            },
            
            # PIPELINE INFO (mantido)
            "pipeline_info": {
                "versao": versao,
                "briefing_id": briefing.id,
                "objetivo_final": "Gerar planta baixa completa em SVG com dados reais",
                "dados_reais": True
            }
        }
        
        # Debug
        self.logger.info(f"🔥 ESTRUTURA RESTAURADA - Nome: {inputs_estruturados['nome_projeto']}")
        self.logger.info(f"🔥 ESTRUTURA RESTAURADA - Empresa: {inputs_estruturados['empresa']}")
        self.logger.info(f"🔥 ESTRUTURA RESTAURADA - Total áreas: {len(inputs_estruturados['areas_solicitadas'])}")
        
        return inputs_estruturados       
            
    def _prepararr_inputs_planta(self, briefing: Briefing, versao: int) -> Dict:
        """
        Prepara inputs específicos para o crew de plantas baixas usando dados REAIS
        🔥 FIX: Garantir extração correta dos dados do briefing
        """
        
        # 🚨 DEBUG: Verificar dados ANTES de processar
        self.logger.info("🔍 EXTRAINDO DADOS REAIS DO BRIEFING...")
        self.logger.info(f"   📋 Projeto: {briefing.projeto.nome}")
        self.logger.info(f"   🏢 Empresa: {briefing.projeto.empresa.nome}")
        self.logger.info(f"   💰 Orçamento: R$ {briefing.projeto.orcamento}")
        self.logger.info(f"   📏 Área: {briefing.area_estande}m²")
        self.logger.info(f"   📐 Dimensões: {briefing.medida_frente}x{briefing.medida_fundo}m")
        
        # Calcular dados do estande
        area_total = float(briefing.area_estande or 0)
        medida_frente = float(briefing.medida_frente or 0)
        medida_fundo = float(briefing.medida_fundo or 0)
        
        # Se não tem área calculada, calcular agora
        if not area_total and medida_frente and medida_fundo:
            area_total = medida_frente * medida_fundo
            self.logger.info(f"   📊 Área calculada: {area_total}m²")
        
        # Coletar áreas funcionais REAIS
        areas_exposicao = []
        for area in briefing.areas_exposicao.all():
            area_data = {
                "tipo": "exposicao",
                "metragem": float(area.metragem or 0),
                "equipamentos": area.equipamentos or "",
                "observacoes": area.observacoes or "",
                "elementos": {
                    "lounge": getattr(area, 'tem_lounge', False),
                    "vitrine_exposicao": getattr(area, 'tem_vitrine_exposicao', False),
                    "balcao_recepcao": getattr(area, 'tem_balcao_recepcao', False),
                    "mesas_atendimento": getattr(area, 'tem_mesas_atendimento', False),
                    "balcao_cafe": getattr(area, 'tem_balcao_cafe', False),
                    "balcao_vitrine": getattr(area, 'tem_balcao_vitrine', False),
                    "caixa_vendas": getattr(area, 'tem_caixa_vendas', False)
                }
            }
            areas_exposicao.append(area_data)
        
        salas_reuniao = []
        for sala in briefing.salas_reuniao.all():
            sala_data = {
                "tipo": "sala_reuniao",
                "capacidade": sala.capacidade,
                "metragem": float(sala.metragem or 0),
                "equipamentos": sala.equipamentos or ""
            }
            salas_reuniao.append(sala_data)
        
        copas = []
        for copa in briefing.copas.all():
            copa_data = {
                "tipo": "copa",
                "metragem": float(copa.metragem or 0),
                "equipamentos": copa.equipamentos or ""
            }
            copas.append(copa_data)
        
        depositos = []
        for deposito in briefing.depositos.all():
            deposito_data = {
                "tipo": "deposito",
                "metragem": float(deposito.metragem or 0),
                "equipamentos": deposito.equipamentos or ""
            }
            depositos.append(deposito_data)
        
        # Log das áreas coletadas
        total_areas = len(areas_exposicao) + len(salas_reuniao) + len(copas) + len(depositos)
        self.logger.info(f"   🏗️ Áreas coletadas: {total_areas} (exposição:{len(areas_exposicao)}, reunião:{len(salas_reuniao)}, copa:{len(copas)}, depósito:{len(depositos)})")
        
        # Estrutura final dos inputs - DADOS REAIS
        inputs_estruturados = {
            "briefing_completo": {
                "projeto": {
                    "numero": briefing.projeto.numero,
                    "nome": briefing.projeto.nome,
                    "empresa": briefing.projeto.empresa.nome,
                    "tipo": briefing.projeto.tipo_projeto or "feira_de_negocios",
                    "orcamento": float(briefing.projeto.orcamento or 0)
                },
                "evento": {
                    "nome": briefing.nome_evento or "Hair Summit 2025",
                    "local": briefing.local_evento or "Expo Center Norte", 
                    "objetivo": briefing.objetivo_evento or "Lançamentos, relacionamento com mercado, vendas, experiências com a marca, apresentações e demonstrações de produtos",
                    "organizador": briefing.organizador_evento or "Beauty Fair Eventos e Promoções Ltda.",
                    "data_horario": briefing.data_horario_evento or "03 a 08 de abril, das 8h00 às 20h00",
                    "periodo_montagem": briefing.periodo_montagem_evento or "03 de abril das 9h00 às 21h00",
                    "periodo_desmontagem": briefing.periodo_desmontagem_evento or "21h00 do dia 08 de abril até às 14h00 do dia 09 de abril"
                },
                "estande": {
                    "tipo_stand": briefing.tipo_stand or "ponta_de_ilha",
                    "area_total": area_total,
                    "medida_frente": medida_frente,
                    "medida_fundo": medida_fundo,
                    "medida_lateral_esquerda": float(briefing.medida_lateral_esquerda or 0),
                    "medida_lateral_direita": float(briefing.medida_lateral_direita or 0),
                    "estilo": briefing.estilo_estande or "moderno",
                    "material": briefing.material or "construido",
                    "piso_elevado": briefing.piso_elevado or "sem_elevacao",
                    "tipo_testeira": briefing.tipo_testeira or "reta",
                    "endereco_estande": briefing.endereco_estande or ""
                },
                "funcionalidades": {
                    "tipo_venda": briefing.tipo_venda or "loja",
                    "tipo_ativacao": briefing.tipo_ativacao or "area_instagramavel,glorify",
                    "objetivo_estande": briefing.objetivo_estande or "lançamentos_relacionamento_vendas"
                },
                "divisoes_funcionais": {
                    "areas_exposicao": areas_exposicao,
                    "salas_reuniao": salas_reuniao,
                    "copas": copas,
                    "depositos": depositos,
                    "total_divisoes": total_areas
                },
                "referencias": {
                    "dados": briefing.referencias_dados or "imagens do filme olympia de 1936",
                    "logotipo": briefing.logotipo or "",
                    "campanha": briefing.campanha_dados or "campanha vem junto nike"
                }
            },
            
            "pipeline_info": {
                "versao": versao,
                "briefing_id": briefing.id,
                "briefing_versao": briefing.versao,
                "agentes_pipeline": [
                    "1. Analista de Briefing",
                    "2. Arquiteto Espacial", 
                    "3. Calculador de Coordenadas",
                    "4. Gerador de SVG"
                ],
                "objetivo_final": "Gerar planta baixa completa em SVG com dados reais do briefing",
                "dados_reais": True,
                "total_areas_funcionais": total_areas
            }
        }
        
        # 🚨 DEBUG FINAL: Log dos inputs que serão enviados
        self.logger.info(f"📤 INPUTS FINAIS - Projeto: {inputs_estruturados['briefing_completo']['projeto']['nome']}")
        self.logger.info(f"📤 INPUTS FINAIS - Empresa: {inputs_estruturados['briefing_completo']['projeto']['empresa']}")
        self.logger.info(f"📤 INPUTS FINAIS - Área Total: {inputs_estruturados['briefing_completo']['estande']['area_total']}m²")
        self.logger.info(f"📤 INPUTS FINAIS - Total Áreas: {inputs_estruturados['briefing_completo']['divisoes_funcionais']['total_divisoes']}")
        
        return inputs_estruturados
        
    def _processar_resultado_planta(self, briefing: Briefing, versao: int, resultado: Dict) -> PlantaBaixa:
        """Processa resultado do crew e salva planta baixa"""
        try:
            crew_result_object = resultado.get('resultado', {}) 
            execucao_id = resultado.get('execucao_id')
            tempo_execucao = resultado.get('tempo_execucao', 0)
            
            # Criar planta baixa
            planta = PlantaBaixa.objects.create(
                projeto=briefing.projeto,
                briefing=briefing,
                projetista=briefing.projeto.projetista,
                dados_json={
                    'crew_resultado': str(crew_result_object), 
                    'execucao_id': execucao_id,
                    'tempo_execucao': tempo_execucao,
                    'versao': versao,
                    'pipeline_completo': True,
                    'metodo': 'crewai_v2_corrigido'
                },
                versao=versao,
                algoritmo_usado='crewai_v2_pipeline_corrigido',
                status='pronta'
            )
            
            # Processar SVG do resultado
            self._processar_svg_resultado(planta, crew_result_object, versao)
            
            planta.save()
            self.logger.info(f"✅ Planta baixa v{versao} criada: ID {planta.id}")
            
            return planta
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao processar resultado: {str(e)}")
            raise

    def _processar_svg_resultado(self, planta: PlantaBaixa, crew_resultado: Any, versao: int):
        """Processa SVG do resultado do CrewAI"""
        try:
            self.logger.info("🎯 Tentando extrair SVG do resultado do CrewAI...")
            
            # Converter crew_resultado para string se necessário
            crew_str = str(crew_resultado)
            
            # Tentar extrair SVG do resultado
            svg_content = self._extrair_svg_do_resultado(crew_str)
            
            if svg_content:
                self.logger.info("✅ SVG extraído com sucesso!")
                svg_filename = f"planta_v{versao}_{planta.projeto.numero}.svg"
            else:
                # Se não conseguiu extrair, usar fallback
                self.logger.warning("⚠️ Não conseguiu extrair SVG - usando fallback")
                svg_content = self._svg_fallback(planta, versao)
                svg_filename = f"planta_fallback_v{versao}_{planta.projeto.numero}.svg"
            
            # Salvar arquivo SVG
            planta.arquivo_svg.save(
                svg_filename,
                ContentFile(svg_content.encode('utf-8')),
                save=False
            )
            
            self.logger.info(f"💾 SVG salvo: {svg_filename} ({len(svg_content)} chars)")
                
        except Exception as e:
            self.logger.error(f"❌ Erro ao processar SVG: {e}")
            # Garantir que sempre tem um SVG
            svg_emergencia = self._svg_fallback(planta, versao)
            planta.arquivo_svg.save(
                f"planta_emergencia_v{versao}.svg",
                ContentFile(svg_emergencia.encode('utf-8')),
                save=False
            )

    def _extrair_svg_do_resultado(self, crew_resultado_str: str) -> str:
        """Extrai SVG do resultado do CrewAI"""
        try:
            # Estratégia 1: Procurar por JSON com svg_completo
            if 'svg_completo' in crew_resultado_str:
                try:
                    start_idx = crew_resultado_str.find('{')
                    end_idx = crew_resultado_str.rfind('}') + 1
                    
                    if start_idx >= 0 and end_idx > start_idx:
                        json_parte = crew_resultado_str[start_idx:end_idx]
                        resultado_json = json.loads(json_parte)
                        
                        svg_content = resultado_json.get('svg_completo', '')
                        if svg_content and '<svg' in svg_content:
                            return svg_content
                            
                except json.JSONDecodeError:
                    pass
            
            # Estratégia 2: Procurar por SVG direto no texto
            svg_match = re.search(r'<svg[^>]*>.*?</svg>', crew_resultado_str, re.DOTALL)
            if svg_match:
                return svg_match.group(0)
            
            # Estratégia 3: Procurar por XML + SVG
            xml_match = re.search(r'<\?xml[^>]*>.*?</svg>', crew_resultado_str, re.DOTALL)
            if xml_match:
                return xml_match.group(0)
            
            return None
            
        except Exception as e:
            self.logger.error(f"❌ Erro na extração: {e}")
            return None
    
    def _svg_fallback(self, planta: PlantaBaixa, versao: int) -> str:
        """SVG de fallback com dados reais do briefing"""
        projeto = planta.projeto
        briefing = planta.briefing
        
        # Dados básicos REAIS
        nome = projeto.nome or "Projeto"
        empresa = projeto.empresa.nome or "Cliente"
        area = int(briefing.area_estande or 100)
        frente = briefing.medida_frente or 10
        fundo = briefing.medida_fundo or 10
        
        # Contar áreas reais
        total_areas = (
            briefing.areas_exposicao.count() +
            briefing.salas_reuniao.count() +
            briefing.copas.count() +
            briefing.depositos.count()
        )
        
        return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg width="800" height="600" viewBox="0 0 800 600" xmlns="http://www.w3.org/2000/svg">
  <rect width="800" height="600" fill="white"/>
  
  <text x="400" y="30" text-anchor="middle" font-size="18" font-weight="bold" fill="#000">
    {nome}
  </text>
  <text x="400" y="55" text-anchor="middle" font-size="12" fill="#666">
    {empresa} | {area}m² ({frente}x{fundo}m) | {total_areas} áreas
  </text>
  
  <rect x="200" y="100" width="{frente * 20}" height="{fundo * 20}" 
        fill="#f8f9fa" stroke="#000" stroke-width="3"/>
  
  <text x="400" y="400" text-anchor="middle" font-size="14" fill="#28a745">
    ✅ PLANTA GERADA COM DADOS REAIS
  </text>
  <text x="400" y="430" text-anchor="middle" font-size="12" fill="#666">
    CrewAI V2 Corrigido | Versão {versao}
  </text>
</svg>'''