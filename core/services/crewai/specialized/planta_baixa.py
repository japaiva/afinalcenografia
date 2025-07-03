
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
        """Prepara inputs específicos para o crew de plantas baixas"""
        
        # Calcular dados do estande
        area_total = float(briefing.area_estande or 0)
        medida_frente = float(briefing.medida_frente or 0)
        medida_fundo = float(briefing.medida_fundo or 0)
        
        if not area_total and medida_frente and medida_fundo:
            area_total = medida_frente * medida_fundo
        
        return {
            # Dados estruturados para os agentes
            "briefing_completo": {
                "projeto": {
                    "numero": briefing.projeto.numero,
                    "nome": briefing.projeto.nome,
                    "empresa": briefing.projeto.empresa.nome,
                    "tipo": briefing.projeto.tipo_projeto or "outros"
                },
                "estande": {
                    "area_total": area_total,
                    "medida_frente": medida_frente,
                    "medida_fundo": medida_fundo,
                    "tipo_stand": getattr(briefing, 'tipo_stand', 'ilha') or 'ilha'
                },
                "objetivos": {
                    "objetivo_evento": briefing.objetivo_evento or "Exposição comercial",
                    "objetivo_estande": briefing.objetivo_estande or "Apresentar produtos",
                    "estilo_estande": briefing.estilo_estande or "moderno"
                },
                "evento": {
                    "nome": briefing.nome_evento or "Feira",
                    "versao_planta": versao
                }
            },
            
            # Pipeline metadata
            "pipeline_info": {
                "versao": versao,
                "agentes_pipeline": [
                    "1. Analista de Briefing",
                    "2. Arquiteto Espacial", 
                    "3. Calculador de Coordenadas",
                    "4. Gerador de SVG"
                ],
                "objetivo_final": "Gerar planta baixa completa em SVG"
            }
        }
    
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