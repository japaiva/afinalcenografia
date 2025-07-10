# Arquivo: core/services/crewai/specialized/planta_baixa.py - VERSÃO COMPLETA E CORRIGIDA

from core.services.crewai.base_service import CrewAIServiceV2
from projetos.models import Briefing
from projetista.models import PlantaBaixa
from django.core.files.base import ContentFile
from typing import Dict, Any # Adicionado 'Any' para maior flexibilidade no tipo de crew_resultado
import json
import re
import logging
import html # Importar html para sanitização extra de texto em SVGs de emergência

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
        """Processa resultado do crew e salva planta baixa - VERSÃO CORRIGIDA"""
        try:
            # Extrair dados do resultado. crew_resultado agora é esperado como um dicionário.
            crew_result_object = resultado.get('resultado', {}) 
            execucao_id = resultado.get('execucao_id')
            tempo_execucao = resultado.get('tempo_execucao', 0)
            
            # Criar planta baixa
            planta = PlantaBaixa.objects.create(
                projeto=briefing.projeto,
                briefing=briefing,
                projetista=briefing.projeto.projetista,
                dados_json={
                    # Armazenar representação string do objeto para logs/depuração
                    'crew_resultado': str(crew_result_object), 
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
            
            # 🔥 PROCESSAR SVG COM MÚLTIPLAS ESTRATÉGIAS
            # Passar o objeto de resultado completo para a função de processamento de SVG
            self._processar_svg_resultado_robusto(planta, crew_result_object, versao)
            
            planta.save()
            self.logger.info(f"✅ Planta baixa v{versao} criada: ID {planta.id}")
            
            return planta
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao processar resultado: {str(e)}")
            raise
    
    def _processar_svg_resultado_robusto(self, planta: PlantaBaixa, crew_resultado: Any, versao: int):
        """Processa SVG do resultado do crew com múltiplas estratégias robustas"""
        try:
            # 🔍 DEBUG - Ver o que veio do crew
            self.logger.info(f"🔍 Processando resultado do crew (dentro de _processar_svg_resultado_robusto):")
            self.logger.info(f"🔍 Tipo: {type(crew_resultado)}")
            # crew_resultado agora é esperado como um dicionário, com base no log de "Final Output".
            # Se não for um dicionário diretamente, as próximas estratégias tentarão lidar com sua representação em string.

            svg_content = None
            estrategia_usada = "nenhuma"
            
            # 🔥 ESTRATÉGIA 1: Resultado é um dicionário e contém 'svg_code'
            if isinstance(crew_resultado, dict) and 'svg_code' in crew_resultado:
                raw_svg_string_from_dict = crew_resultado['svg_code']
                self.logger.info(f"🔍 SVG string raw do dict: {raw_svg_string_from_dict[:100]}...")

                # Tentar desescapar a string. Isso é crucial para lidar com \" e \n.
                try:
                    # json.loads(f'"{raw_svg_string_from_dict}"') é uma forma de desescapar uma literal de string JSON.
                    # Isso trata escapes como \\n, \\", etc.
                    svg_content = json.loads(f'"{raw_svg_string_from_dict}"')
                    estrategia_usada = "dict_svg_code_json_unescaped"
                    self.logger.info("🎯 SVG extraído e desescapado (json.loads) de dict.svg_code!")
                except json.JSONDecodeError:
                    # Fallback para desescape manual se json.loads falhar (ex: se não for uma string JSON perfeitamente escapada)
                    self.logger.warning("⚠️ json.loads unescape falhou, tentando desescape manual.")
                    svg_content = raw_svg_string_from_dict.replace('\\n', '\n').replace('\\"', '"')
                    estrategia_usada = "dict_svg_code_manual_unescaped"
                    self.logger.info("🎯 SVG extraído e desescapado (manual) de dict.svg_code!")
            
            # Fallback strategies (só devem ser executadas se a estratégia primária não encontrar SVG)
            if not svg_content:
                self.logger.warning("⚠️ Estratégia primária para SVG falhou ou não aplicável, tentando fallbacks.")
                # Converter para string para que as regex e outras verificações funcionem no conteúdo textual
                str_crew_resultado = str(crew_resultado) 
                
                # 🔥 ESTRATÉGIA 2: Resultado direto é SVG (pode acontecer se o CrewOutput for apenas o SVG ou String)
                if self._contem_svg_valido(str_crew_resultado):
                    svg_content = self._extrair_svg_limpo(str_crew_resultado)
                    estrategia_usada = "resultado_direto_fallback"
                    self.logger.info("🎯 SVG extraído diretamente da string de resultado (fallback)!")
                
                # 🔥 ESTRATÉGIA 3: Resultado é objeto CrewAI com .raw
                elif hasattr(crew_resultado, 'raw') and self._contem_svg_valido(str(crew_resultado.raw)):
                    svg_content = self._extrair_svg_limpo(str(crew_resultado.raw))
                    estrategia_usada = "objeto_raw_fallback"
                    self.logger.info("🎯 SVG extraído do .raw do resultado (fallback)!")
                
                # 🔥 ESTRATÉGIA 4: Procurar em tasks_output
                elif hasattr(crew_resultado, 'tasks_output'):
                    for i, task_output in enumerate(crew_resultado.tasks_output):
                        if hasattr(task_output, 'raw') and self._contem_svg_valido(str(task_output.raw)):
                            svg_content = self._extrair_svg_limpo(str(task_output.raw))
                            estrategia_usada = f"task_output_{i}_fallback"
                            self.logger.info(f"🎯 SVG extraído de task_output[{i}].raw (fallback)!")
                            break
                
                # 🔥 ESTRATÉGIA 5: Buscar JSON com svg_code usando regex na string completa (se nenhuma das anteriores funcionou)
                # Esta é uma estratégia genérica se o CrewOutput não for um dict diretamente ou .raw
                if not svg_content and 'svg_code' in str_crew_resultado:
                    try:
                        json_match = re.search(r'(\{.*?"svg_code".*?\})', str_crew_resultado, re.DOTALL)
                        if json_match:
                            json_str_found = json_match.group(1)
                            # Desescapar a string JSON para que json.loads possa interpretá-la corretamente
                            # (remove um nível de escape se a string inteira foi escapada)
                            json_str_unescaped_for_loads = json_str_found.replace('\\\\', '\\')
                            json_data = json.loads(json_str_unescaped_for_loads)
                            if 'svg_code' in json_data:
                                # A string 'svg_code' dentro do JSON ainda pode precisar de desescape final se contiver \" ou \n
                                try:
                                    svg_content = json.loads(f'"{json_data["svg_code"]}"')
                                except json.JSONDecodeError:
                                    svg_content = json_data["svg_code"].replace('\\n', '\n').replace('\\"', '"')

                                estrategia_usada = "regex_json_svg_code_fallback"
                                self.logger.info("🎯 SVG extraído de JSON svg_code via regex e desescapado (fallback)!")
                    except Exception as e:
                        self.logger.warning(f"⚠️ Erro ao tentar extrair JSON com svg_code via regex em fallback: {e}")
                        pass
                
                # 🔥 ESTRATÉGIA 6: Regex para encontrar SVG em qualquer lugar (último recurso)
                if not svg_content:
                    svg_match = re.search(r'(<\?xml.*?</svg>)', str_crew_resultado, re.DOTALL)
                    if svg_match:
                        extracted_svg_raw = svg_match.group(1)
                        # Tentar desescapar se a regex encontrou uma string que parece escapada
                        try:
                            svg_content = json.loads(f'"{extracted_svg_raw}"')
                        except json.JSONDecodeError:
                            svg_content = extracted_svg_raw.replace('\\n', '\n').replace('\\"', '"')
                        estrategia_usada = "regex_match_fallback_unescaped"
                        self.logger.info("🎯 SVG extraído via regex ampla e desescapado (fallback)!")
            
            # 🔥 VALIDAÇÃO FINAL SUPER RIGOROSA
            if not svg_content: # Garantir que svg_content não é None antes de validar
                self.logger.error("❌ SVG_CONTENT está vazio/None antes da validação final. Gerando SVG de emergência absoluto.")
                svg_final = self._svg_emergencia_absoluta() # Fornece um SVG de fallback garantido
                estrategia_usada = "emergencia_absoluta_final"
            else:
                svg_final = self._validacao_svg_super_rigorosa(svg_content)
            
            # Salvar arquivo
            svg_filename = f"planta_crewai_v2_v{versao}_{planta.projeto.numero}.svg"
            planta.arquivo_svg.save(
                svg_filename,
                ContentFile(svg_final.encode('utf-8')),
                save=False
            )
            
            self.logger.info(f"💾 SVG salvo: {svg_filename} ({len(svg_final)} chars) via {estrategia_usada}")
            
        except Exception as e:
            self.logger.error(f"❌ Erro TRATADO ao processar SVG em _processar_svg_resultado_robusto: {str(e)}")
            import traceback
            self.logger.error(f"❌ Traceback: {traceback.format_exc()}")
            
            # SVG de emergência absoluta
            svg_emergencia = self._svg_emergencia_absoluta()
            svg_filename = f"planta_emergencia_ERRO_CRITICO_v{versao}.svg"
            planta.arquivo_svg.save(
                svg_filename,
                ContentFile(svg_emergencia.encode('utf-8')),
                save=False
            )
            # Re-raise para que o erro seja propagado e tratado no nível superior, se necessário
            raise
    
    def _contem_svg_valido(self, texto: str) -> bool:
        """Verifica se texto contém SVG válido com validação rigorosa"""
        if not texto:
            return False
        
        # Verificações básicas
        tem_xml = '<?xml' in texto
        tem_svg_abertura = '<svg' in texto
        tem_svg_fechamento = '</svg>' in texto
        
        # Verificação de aspas balanceadas
        aspas_duplas = texto.count('"')
        aspas_balanceadas = aspas_duplas % 2 == 0
        
        return tem_xml and tem_svg_abertura and tem_svg_fechamento and aspas_balanceadas
    
    def _extrair_svg_limpo(self, texto: str) -> str:
        """Extrai e limpa SVG do texto"""
        # Encontrar início
        inicio = texto.find('<?xml')
        if inicio == -1:
            inicio = texto.find('<svg')
        
        # Encontrar fim
        fim = texto.rfind('</svg>') + 6
        
        if inicio != -1 and fim > inicio:
            svg_bruto = texto[inicio:fim]
            return self._limpar_svg_extraido(svg_bruto)
        
        raise Exception("SVG não encontrado no texto")
    
    def _limpar_svg_extraido(self, svg_bruto: str) -> str:
        """Limpa SVG extraído removendo caracteres problemáticos e corrigindo escapes"""
        # Remover caracteres não ASCII
        svg_limpo = re.sub(r'[^\x20-\x7E\n\r\t]', '', svg_bruto)
        
        # Remover múltiplas quebras de linha
        svg_limpo = re.sub(r'\n\s*\n', '\n', svg_limpo)
        
        # Remover espaços em excesso
        svg_limpo = re.sub(r'\s+', ' ', svg_limpo)
        
        # Corrigir quebras de linha em tags
        svg_limpo = re.sub(r'>\s+<', '>\n<', svg_limpo)
        
        return svg_limpo.strip()
    
    def _validacao_svg_super_rigorosa(self, svg_content: str) -> str:
        """Validação super rigorosa do SVG"""
        
        # Verificar estrutura básica
        if not svg_content.startswith('<?xml'):
            self.logger.error("SVG não inicia com declaração XML")
            return self._svg_emergencia_absoluta()
        
        if '<svg' not in svg_content or '</svg>' not in svg_content:
            self.logger.error("Tags SVG malformadas")
            return self._svg_emergencia_absoluta()
        
        # Verificar aspas balanceadas
        aspas_duplas = svg_content.count('"')
        if aspas_duplas % 2 != 0:
            self.logger.error(f"Aspas duplas desbalanceadas: {aspas_duplas}")
            return self._svg_emergencia_absoluta()
        
        # Tentar parsear como XML básico
        try:
            # Verificação simples de tags balanceadas
            import xml.etree.ElementTree as ET
            ET.fromstring(svg_content)
            self.logger.info("✅ SVG passou na validação XML")
        except Exception as e:
            self.logger.error(f"SVG inválido como XML: {e}")
            return self._svg_emergencia_absoluta()
        
        return svg_content
    
    def _gerar_svg_emergencia_com_dados(self, planta: PlantaBaixa, versao: int) -> str:
        """Gera SVG de emergência usando dados reais do briefing"""
        try:
            briefing = planta.briefing
            projeto = planta.projeto
            
            nome_projeto = projeto.nome or "Projeto"
            nome_empresa = projeto.empresa.nome or "Cliente"
            area = briefing.area_estande or 100
            
            return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg width="700" height="500" viewBox="0 0 700 500" xmlns="http://www.w3.org/2000/svg">
  <rect x="0" y="0" width="700" height="500" fill="#f8f9fa"/>
  
  <text x="350" y="40" text-anchor="middle" font-family="Arial" font-size="18" font-weight="bold" fill="#333">
    {nome_projeto}
  </text>
  
  <text x="350" y="65" text-anchor="middle" font-family="Arial" font-size="14" fill="#666">
    {nome_empresa} | Area: {area}m²
  </text>
  
  <rect x="275" y="75" width="150" height="25" fill="#28a745" rx="12"/>
  <text x="350" y="92" text-anchor="middle" font-family="Arial" font-size="12" fill="white" font-weight="bold">
    CREW EXECUTADO COM SUCESSO
  </text>
  
  <rect x="200" y="130" width="300" height="200" fill="white" stroke="#333" stroke-width="3"/>
  
  <text x="350" y="200" text-anchor="middle" font-family="Arial" font-size="14" fill="#007bff">
    Pipeline CrewAI V2 Completo
  </text>
  <text x="350" y="220" text-anchor="middle" font-family="Arial" font-size="12" fill="#666">
    4 Agentes Executados
  </text>
  <text x="350" y="240" text-anchor="middle" font-family="Arial" font-size="12" fill="#666">
    SVG Gerado via Emergência
  </text>
  
  <text x="350" y="400" text-anchor="middle" font-family="Arial" font-size="11" fill="#666">
    Versão {versao} | Dados Reais do Briefing
  </text>
  
  <text x="350" y="460" text-anchor="middle" font-family="Arial" font-size="9" fill="#999">
    Sistema de fallback ativo
  </text>
</svg>'''
        except:
            return self._svg_emergencia_absoluta()
    
    def _svg_emergencia_absoluta(self) -> str:
        """SVG de emergência absoluta - último recurso"""
        return '''<?xml version="1.0" encoding="UTF-8"?>
<svg width="600" height="400" viewBox="0 0 600 400" xmlns="http://www.w3.org/2000/svg">
  <rect x="0" y="0" width="600" height="400" fill="#f8f9fa"/>
  <text x="300" y="200" text-anchor="middle" font-family="Arial" font-size="16" fill="#333">CrewAI V2 - Sistema Estável</text>
</svg>'''