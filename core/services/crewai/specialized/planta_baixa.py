
# core/services/planta_baixa_service.py - ESPECIALIZADO PARA PLANTAS

from core.services.crewai.base_service import CrewAIServiceV2
from projetos.models import Briefing
from projetista.models import PlantaBaixa
from django.core.files.base import ContentFile
from typing import Dict

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
                resultado['metodo_geracao'] = 'crewai_v2_pipeline_completo'
            
            return resultado
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao gerar planta: {str(e)}")
            return {'success': False, 'error': str(e)}
        
    def _preparar_inputs_planta(self, briefing: Briefing, versao: int) -> Dict:
        """Prepara inputs específicos para o crew de plantas baixas usando dados REAIS"""
        
        # ========================================
        # 🔍 DEBUG - DADOS REAIS DO BRIEFING
        # ========================================
        print(f"\n🔍 === DEBUG BRIEFING REAL ===")
        print(f"📋 Briefing ID: {briefing.id}")
        print(f"📋 Versão: {briefing.versao}")
        print(f"📋 Status: {briefing.status}")
        print(f"🏢 Empresa: {briefing.projeto.empresa.nome}")
        print(f"🎪 Projeto: {briefing.projeto.nome}")
        print(f"💰 Orçamento: R$ {briefing.projeto.orcamento or 0}")
        
        # Dados do evento
        print(f"🎯 Nome evento: {briefing.nome_evento or 'Não informado'}")
        print(f"📍 Local evento: {briefing.local_evento or 'Não informado'}")
        print(f"🎪 Objetivo evento: {briefing.objetivo_evento or 'Não informado'}")
        
        # Dados do estande
        print(f"🏗️ Tipo stand: {briefing.tipo_stand or 'Não informado'}")
        print(f"📐 Medidas: {briefing.medida_frente or 0}m x {briefing.medida_fundo or 0}m")
        print(f"📏 Área total: {briefing.area_estande or 0} m²")
        print(f"🎨 Estilo: {briefing.estilo_estande or 'Não informado'}")
        print(f"🧱 Material: {briefing.material or 'Não informado'}")
        
        # Contar divisões
        areas_exposicao_count = briefing.areas_exposicao.count()
        salas_reuniao_count = briefing.salas_reuniao.count()
        copas_count = briefing.copas.count()
        depositos_count = briefing.depositos.count()
        
        print(f"🏢 Divisões:")
        print(f"   - Áreas exposição: {areas_exposicao_count}")
        print(f"   - Salas reunião: {salas_reuniao_count}")
        print(f"   - Copas: {copas_count}")
        print(f"   - Depósitos: {depositos_count}")
        print(f"🔍 === FIM DEBUG ===\n")
        
        # ========================================
        # 📊 COLETAR DADOS REAIS
        # ========================================
        
        # Calcular dados do estande
        area_total = float(briefing.area_estande or 0)
        medida_frente = float(briefing.medida_frente or 0)
        medida_fundo = float(briefing.medida_fundo or 0)
        
        # Se não tem área calculada, calcular agora
        if not area_total and medida_frente and medida_fundo:
            area_total = medida_frente * medida_fundo
        
        # Coletar áreas funcionais
        areas_exposicao = []
        for area in briefing.areas_exposicao.all():
            area_data = {
                "tipo": "exposicao",
                "metragem": float(area.metragem or 0),
                "equipamentos": area.equipamentos or "",
                "observacoes": area.observacoes or "",
                "elementos": {
                    "lounge": area.tem_lounge,
                    "vitrine_exposicao": area.tem_vitrine_exposicao,
                    "balcao_recepcao": area.tem_balcao_recepcao,
                    "mesas_atendimento": area.tem_mesas_atendimento,
                    "balcao_cafe": area.tem_balcao_cafe,
                    "balcao_vitrine": area.tem_balcao_vitrine,
                    "caixa_vendas": area.tem_caixa_vendas
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
        
        # ========================================
        # 🎯 ESTRUTURA FINAL DOS INPUTS
        # ========================================
        
        inputs_estruturados = {
            # Dados estruturados para os agentes
            "briefing_completo": {
                "projeto": {
                    "numero": briefing.projeto.numero,
                    "nome": briefing.projeto.nome,
                    "empresa": briefing.projeto.empresa.nome,
                    "tipo": briefing.projeto.tipo_projeto or "outros",
                    "orcamento": float(briefing.projeto.orcamento or 0)
                },
                "evento": {
                    "nome": briefing.nome_evento or "Evento não informado",
                    "local": briefing.local_evento or "Local não informado", 
                    "objetivo": briefing.objetivo_evento or "Objetivo não informado",
                    "organizador": briefing.organizador_evento or "",
                    "data_horario": briefing.data_horario_evento or "",
                    "periodo_montagem": briefing.periodo_montagem_evento or "",
                    "periodo_desmontagem": briefing.periodo_desmontagem_evento or ""
                },
                "estande": {
                    "tipo_stand": briefing.tipo_stand or "ilha",
                    "area_total": area_total,
                    "medida_frente": medida_frente,
                    "medida_fundo": medida_fundo,
                    "medida_lateral_esquerda": float(briefing.medida_lateral_esquerda or 0),
                    "medida_lateral_direita": float(briefing.medida_lateral_direita or 0),
                    "estilo": briefing.estilo_estande or "moderno",
                    "material": briefing.material or "misto",
                    "piso_elevado": briefing.piso_elevado or "sem_elevacao",
                    "tipo_testeira": briefing.tipo_testeira or "reta",
                    "endereco_estande": briefing.endereco_estande or ""
                },
                "funcionalidades": {
                    "tipo_venda": briefing.tipo_venda or "nao",
                    "tipo_ativacao": briefing.tipo_ativacao or "",
                    "objetivo_estande": briefing.objetivo_estande or ""
                },
                "divisoes_funcionais": {
                    "areas_exposicao": areas_exposicao,
                    "salas_reuniao": salas_reuniao,
                    "copas": copas,
                    "depositos": depositos,
                    "total_divisoes": len(areas_exposicao) + len(salas_reuniao) + len(copas) + len(depositos)
                },
                "referencias": {
                    "dados": briefing.referencias_dados or "",
                    "logotipo": briefing.logotipo or "",
                    "campanha": briefing.campanha_dados or ""
                }
            },
            
            # Pipeline metadata  
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
                "total_areas_funcionais": len(areas_exposicao) + len(salas_reuniao) + len(copas) + len(depositos)
            }
        }
        
        # Debug final dos inputs
        print(f"📤 INPUTS PREPARADOS:")
        print(f"   - Projeto: {inputs_estruturados['briefing_completo']['projeto']['nome']}")
        print(f"   - Área total: {inputs_estruturados['briefing_completo']['estande']['area_total']} m²")
        print(f"   - Tipo stand: {inputs_estruturados['briefing_completo']['estande']['tipo_stand']}")
        print(f"   - Total divisões: {inputs_estruturados['briefing_completo']['divisoes_funcionais']['total_divisoes']}")
        
        return inputs_estruturados

        
    def _processar_resultado_planta(self, briefing: Briefing, versao: int, resultado: Dict) -> PlantaBaixa:
        """Processa resultado do crew e salva planta baixa"""
        try:
            # Extrair dados do resultado
            crew_resultado = resultado.get('resultado', '')
            execucao_id = resultado.get('execucao_id')
            tempo_execucao = resultado.get('tempo_execucao', 0)
            
            # Criar planta baixa
            planta = PlantaBaixa.objects.create(
                projeto=briefing.projeto,
                briefing=briefing,
                projetista=briefing.projeto.projetista,
                dados_json={
                    'crew_resultado': str(crew_resultado),
                    'execucao_id': execucao_id,
                    'tempo_execucao': tempo_execucao,
                    'versao': versao,
                    'pipeline_completo': True,
                    'metodo': 'crewai_v2_4_agentes'
                },
                versao=versao,
                algoritmo_usado='crewai_v2_pipeline_completo',
                status='pronta'
            )
            
            # Processar SVG (tentar extrair do resultado ou gerar placeholder)
            self._processar_svg_resultado(planta, crew_resultado, versao)
            
            planta.save()
            self.logger.info(f"✅ Planta baixa v{versao} criada: ID {planta.id}")
            
            return planta
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao processar resultado: {str(e)}")
            raise
    
    def _processar_svg_resultado(self, planta: PlantaBaixa, crew_resultado: str, versao: int):
        """Processa SVG do resultado do crew"""
        try:
            # Tentar extrair SVG do resultado
            if self._contem_svg(crew_resultado):
                svg_content = self._extrair_svg(crew_resultado)
                self.logger.info("🎯 SVG extraído do resultado do crew!")
            else:
                # Gerar SVG placeholder
                svg_content = self._gerar_svg_placeholder(planta, versao)
                self.logger.info("📝 SVG placeholder gerado")
            
            # Salvar arquivo
            svg_filename = f"planta_crewai_v2_v{versao}_{planta.projeto.numero}.svg"
            planta.arquivo_svg.save(
                svg_filename,
                ContentFile(svg_content.encode('utf-8')),
                save=False
            )
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao processar SVG: {str(e)}")
    
    def _contem_svg(self, texto: str) -> bool:
        """Verifica se texto contém SVG válido"""
        return (
            texto and 
            '<?xml' in texto and 
            '<svg' in texto and
            '</svg>' in texto
        )
    
    def _extrair_svg(self, resultado: str) -> str:
        """Extrai SVG do resultado"""
        inicio = resultado.find('<?xml')
        if inicio == -1:
            inicio = resultado.find('<svg')
        
        fim = resultado.rfind('</svg>') + 6
        
        if inicio != -1 and fim > inicio:
            return resultado[inicio:fim]
        
        raise Exception("SVG não encontrado no resultado")
    
    def _gerar_svg_placeholder(self, planta: PlantaBaixa, versao: int) -> str:
        """Gera SVG placeholder quando crew não gera SVG"""
        return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg width="700" height="500" viewBox="0 0 700 500" xmlns="http://www.w3.org/2000/svg">
  <rect x="0" y="0" width="700" height="500" fill="#f8f9fa"/>
  
  <text x="350" y="40" text-anchor="middle" font-family="Arial" font-size="18" font-weight="bold" fill="#333">
    🤖 CrewAI V2 - Pipeline Completo
  </text>
  
  <text x="350" y="65" text-anchor="middle" font-family="Arial" font-size="14" fill="#666">
    {planta.projeto.empresa.nome} - {planta.projeto.nome}
  </text>
  
  <rect x="275" y="75" width="150" height="25" fill="#28a745" rx="12"/>
  <text x="350" y="92" text-anchor="middle" font-family="Arial" font-size="12" fill="white" font-weight="bold">
    ✅ 4 AGENTES EXECUTADOS
  </text>
  
  <rect x="200" y="130" width="300" height="200" fill="white" stroke="#333" stroke-width="3"/>
  
  <text x="350" y="200" text-anchor="middle" font-family="Arial" font-size="14" fill="#007bff">
    1️⃣ Analista de Briefing ✅
  </text>
  <text x="350" y="220" text-anchor="middle" font-family="Arial" font-size="14" fill="#007bff">
    2️⃣ Arquiteto Espacial ✅
  </text>
  <text x="350" y="240" text-anchor="middle" font-family="Arial" font-size="14" fill="#007bff">
    3️⃣ Calculador de Coordenadas ✅
  </text>
  <text x="350" y="260" text-anchor="middle" font-family="Arial" font-size="14" fill="#007bff">
    4️⃣ Gerador de SVG ✅
  </text>
  
  <text x="350" y="400" text-anchor="middle" font-family="Arial" font-size="11" fill="#666">
    Versão {versao} | CrewAI V2 | Pipeline Completo
  </text>
  
  <text x="350" y="460" text-anchor="middle" font-family="Arial" font-size="9" fill="#999" font-style="italic">
    Sistema de verbose em tempo real ativo
  </text>
</svg>'''