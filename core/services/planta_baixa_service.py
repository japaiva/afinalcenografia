# core/services/planta_baixa_service.py - VERSÃO COMPLETA COM AGENTE ARQUITETO

import json
import requests
from typing import Dict, List, Optional
from django.core.files.base import ContentFile
from django.utils import timezone
from django.conf import settings

from projetista.models import PlantaBaixa
from projetos.models import Briefing
from core.models import Agente
import logging

logger = logging.getLogger(__name__)

class PlantaBaixaService:
    """
    Serviço para geração de plantas baixas usando agente Arquiteto de Estandes
    """
    
    def __init__(self):
        self.algoritmo_versao = "agente_arquiteto_v3"
        self.agente = self._get_agente_arquiteto()

    def _get_agente_arquiteto(self):
        """Obtém o agente Arquiteto de Estandes"""
        try:
            agente = Agente.objects.get(nome="Arquiteto de Estandes", ativo=True)
            return agente
        except Agente.DoesNotExist:
            logger.error("Agente 'Arquiteto de Estandes' não encontrado")
            raise Exception("Agente Arquiteto de Estandes não está configurado")

    def gerar_planta_baixa(self, briefing: Briefing, versao: int = 1, 
                          planta_anterior: PlantaBaixa = None) -> Dict:
        """
        MÉTODO PRINCIPAL: Gera planta baixa usando agente IA
        """
        try:
            logger.info(f"🚀 Iniciando geração com agente para projeto {briefing.projeto.nome}")
            
            # 📋 ETAPA 1: Validar dados mínimos
            if not self._briefing_tem_dados_minimos(briefing):
                return {
                    'success': False,
                    'error': 'Briefing incompleto - preencha pelo menos a área ou dimensões do estande',
                    'critica': '❌ DADOS INSUFICIENTES: Complete as informações do estande no briefing',
                    'pode_prosseguir': False,
                    'sugestoes': [
                        'Preencha a área total do estande OU',
                        'Preencha as medidas (frente × fundo) do estande',
                        'Informe o tipo de estande (ilha, esquina, corredor, etc.)'
                    ]
                }
            
            # 📋 ETAPA 2: Construir prompt estruturado para o agente
            prompt_briefing = self._construir_prompt_briefing(briefing)
            
            # 🤖 ETAPA 3: Chamar agente para gerar planta
            resultado_agente = self._chamar_agente_arquiteto(prompt_briefing)
            
            if not resultado_agente['success']:
                return {
                    'success': False,
                    'error': resultado_agente['error'],
                    'critica': f"❌ ERRO DO AGENTE: {resultado_agente['error']}",
                    'pode_prosseguir': False,
                    'detalhes': resultado_agente.get('details', '')
                }
            
            # 📐 ETAPA 4: Processar resposta do agente
            layout_data = resultado_agente['layout_data']
            svg_content = layout_data.get('svg_completo', '')
            
            if not svg_content:
                return {
                    'success': False,
                    'error': 'Agente não gerou SVG válido',
                    'critica': '❌ SVG INVÁLIDO: O agente não conseguiu gerar a visualização',
                    'pode_prosseguir': False
                }
            
            # 💾 ETAPA 5: Criar objeto PlantaBaixa
            try:
                planta = self._criar_objeto_planta_agente(
                    briefing, versao, layout_data, svg_content, planta_anterior
                )
            except Exception as e:
                logger.error(f"Erro ao salvar planta: {str(e)}")
                return {
                    'success': False,
                    'error': f'Erro ao salvar planta no banco: {str(e)}',
                    'critica': '❌ ERRO NO SALVAMENTO: Planta gerada mas não foi possível salvar',
                    'pode_prosseguir': False
                }
            
            logger.info(f"🎉 Planta baixa v{versao} gerada com sucesso pelo agente!")
            
            return {
                'success': True,
                'planta': planta,
                'layout': layout_data,
                'validacao_ok': True,
                'critica': layout_data.get('resumo_decisoes', 'Planta gerada com sucesso'),
                'detalhes_validacao': {
                    'areas_atendidas': layout_data.get('dados_basicos', {}).get('areas_atendidas', []),
                    'area_total_usada': layout_data.get('dados_basicos', {}).get('area_total_usada', 0),
                    'tipo_estande': layout_data.get('dados_basicos', {}).get('tipo_estande', ''),
                    'lados_abertos': layout_data.get('dados_basicos', {}).get('lados_abertos', [])
                },
                'pode_prosseguir': True,
                'message': f'Planta baixa v{versao} gerada com sucesso pelo agente Arquiteto!'
            }
            
        except Exception as e:
            logger.error(f"❌ Erro geral na geração com agente: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': f'Erro técnico na geração: {str(e)}',
                'critica': f'❌ ERRO TÉCNICO: {str(e)}',
                'pode_prosseguir': False
            }

    def _briefing_tem_dados_minimos(self, briefing: Briefing) -> bool:
        """Verifica se o briefing tem dados mínimos para gerar planta"""
        # Verificar se tem área OU dimensões
        tem_area = briefing.area_estande and briefing.area_estande > 0
        tem_dimensoes = (briefing.medida_frente and briefing.medida_frente > 0 and 
                        briefing.medida_fundo and briefing.medida_fundo > 0)
        
        if not (tem_area or tem_dimensoes):
            logger.warning("Briefing sem área nem dimensões definidas")
            return False
        
        return True

    def _construir_prompt_briefing(self, briefing: Briefing) -> str:
        """Constrói prompt estruturado para o agente baseado no briefing"""
        
        # Dados básicos do estande
        area_total = briefing.area_estande or 0
        medida_frente = briefing.medida_frente or 0
        medida_fundo = briefing.medida_fundo or 0
        tipo_estande = getattr(briefing, 'tipo_stand', 'ilha') or 'ilha'  # Corrigido: tipo_stand em vez de tipo_estande
        
        # Se não tem área mas tem dimensões, calcular
        if not area_total and medida_frente and medida_fundo:
            area_total = float(medida_frente) * float(medida_fundo)
        
        # Se não tem dimensões mas tem área, estimar formato retangular
        elif area_total and not (medida_frente and medida_fundo):
            import math
            ratio = 1.6  # Proporção típica de estandes
            medida_fundo = math.sqrt(float(area_total) / ratio)
            medida_frente = float(area_total) / medida_fundo

        # Construir seções do briefing
        prompt_sections = []
        
        # 1. DADOS BÁSICOS
        prompt_sections.append(f"""
=== DADOS BÁSICOS DO ESTANDE ===
Tipo de estande: {tipo_estande}
Dimensões: {medida_frente:.1f}m (frente) x {medida_fundo:.1f}m (fundo)
Área total: {area_total:.1f}m²
Empresa: {briefing.projeto.empresa.nome}
Projeto: {briefing.projeto.nome}
""")

        # 2. ÁREAS DE EXPOSIÇÃO
        areas_exposicao = []
        try:
            if hasattr(briefing, 'areas_exposicao'):
                for idx, area in enumerate(briefing.areas_exposicao.all(), 1):
                    metragem = getattr(area, 'metragem', 0) or 0
                    
                    # Características especiais
                    caracteristicas = []
                    if getattr(area, 'tem_lounge', False):
                        caracteristicas.append('lounge')
                    if getattr(area, 'tem_balcao_recepcao', False):
                        caracteristicas.append('balcão de recepção')
                    if getattr(area, 'tem_balcao_cafe', False):
                        caracteristicas.append('balcão de café')
                    if getattr(area, 'tem_caixa_vendas', False):
                        caracteristicas.append('caixa de vendas')
                    if getattr(area, 'tem_vitrine', False):
                        caracteristicas.append('vitrine')
                    
                    desc_area = f"Área de Exposição {idx}: {metragem:.1f}m²"
                    if caracteristicas:
                        desc_area += f" (inclui: {', '.join(caracteristicas)})"
                    
                    areas_exposicao.append(desc_area)
        except Exception as e:
            logger.warning(f"Erro ao processar áreas de exposição: {e}")
        
        if areas_exposicao:
            prompt_sections.append(f"""
=== ÁREAS DE EXPOSIÇÃO SOLICITADAS ===
{chr(10).join(areas_exposicao)}
""")

        # 3. SALAS DE REUNIÃO
        salas_reuniao = []
        try:
            if hasattr(briefing, 'salas_reuniao'):
                for idx, sala in enumerate(briefing.salas_reuniao.all(), 1):
                    metragem = getattr(sala, 'metragem', 0) or 0
                    capacidade = getattr(sala, 'capacidade', 0) or 0
                    equipamentos = getattr(sala, 'equipamentos', '') or ''
                    
                    desc_sala = f"Sala de Reunião {idx}: {metragem:.1f}m²"
                    if capacidade:
                        desc_sala += f", capacidade {capacidade} pessoas"
                    if equipamentos:
                        desc_sala += f", equipamentos: {equipamentos}"
                    
                    salas_reuniao.append(desc_sala)
        except Exception as e:
            logger.warning(f"Erro ao processar salas de reunião: {e}")
        
        if salas_reuniao:
            prompt_sections.append(f"""
=== SALAS DE REUNIÃO SOLICITADAS ===
{chr(10).join(salas_reuniao)}
""")

        # 4. COPAS
        copas = []
        try:
            if hasattr(briefing, 'copas'):
                for idx, copa in enumerate(briefing.copas.all(), 1):
                    metragem = getattr(copa, 'metragem', 0) or 0
                    equipamentos = getattr(copa, 'equipamentos', '') or ''
                    
                    desc_copa = f"Copa {idx}: {metragem:.1f}m²"
                    if equipamentos:
                        desc_copa += f", equipamentos: {equipamentos}"
                    
                    copas.append(desc_copa)
        except Exception as e:
            logger.warning(f"Erro ao processar copas: {e}")
        
        if copas:
            prompt_sections.append(f"""
=== COPAS SOLICITADAS ===
{chr(10).join(copas)}
""")

        # 5. DEPÓSITOS
        depositos = []
        try:
            if hasattr(briefing, 'depositos'):
                for idx, deposito in enumerate(briefing.depositos.all(), 1):
                    metragem = getattr(deposito, 'metragem', 0) or 0
                    finalidade = getattr(deposito, 'finalidade', '') or ''
                    
                    desc_deposito = f"Depósito {idx}: {metragem:.1f}m²"
                    if finalidade:
                        desc_deposito += f", finalidade: {finalidade}"
                    
                    depositos.append(desc_deposito)
        except Exception as e:
            logger.warning(f"Erro ao processar depósitos: {e}")
        
        if depositos:
            prompt_sections.append(f"""
=== DEPÓSITOS SOLICITADOS ===
{chr(10).join(depositos)}
""")

        # 6. OBSERVAÇÕES GERAIS
        observacoes = []
        if briefing.objetivo_evento:
            observacoes.append(f"Objetivo do evento: {briefing.objetivo_evento}")
        if briefing.objetivo_estande:
            observacoes.append(f"Objetivo do estande: {briefing.objetivo_estande}")
        if briefing.estilo_estande:
            observacoes.append(f"Estilo desejado: {briefing.estilo_estande}")
        if briefing.tipo_ativacao:
            observacoes.append(f"Tipo de ativação: {briefing.tipo_ativacao}")
        if briefing.referencias_dados:
            observacoes.append(f"Referências visuais: {briefing.referencias_dados}")
        
        if observacoes:
            prompt_sections.append(f"""
=== OBSERVAÇÕES E REQUISITOS ESPECIAIS ===
{chr(10).join(observacoes)}
""")

        # 7. INSTRUÇÃO FINAL
        prompt_sections.append(f"""
=== SOLICITAÇÃO ===
Preciso que você crie uma planta baixa otimizada para este estande considerando:

1. O tipo de estande ({tipo_estande}) determina quais lados são abertos
2. Todas as áreas solicitadas devem ser incluídas respeitando as metragens
3. Núcleo central deve conter ambientes fechados (reunião, copa, depósito)
4. Áreas de exposição devem ficar nos lados abertos do estande
5. Layout deve otimizar fluxo de visitantes e funcionalidade

Por favor, retorne sua resposta no formato JSON especificado nas suas instruções de tarefa.
""")

        return '\n'.join(prompt_sections)

    def _chamar_agente_arquiteto(self, prompt_briefing: str) -> Dict:
        """Chama o agente Arquiteto de Estandes via API"""
        try:
            # Configurar headers
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {settings.OPENAI_API_KEY}'
            }
            
            # Construir mensagens para API
            messages = [
                {
                    "role": "system",
                    "content": self.agente.llm_system_prompt
                },
                {
                    "role": "user", 
                    "content": f"{self.agente.task_instructions}\n\n{prompt_briefing}"
                }
            ]
            
            # Dados da requisição
            data = {
                "model": self.agente.llm_model,
                "messages": messages,
                "temperature": float(self.agente.llm_temperature),
                "max_tokens": 4000,
                "response_format": {"type": "json_object"}
            }
            
            logger.info(f"Chamando agente {self.agente.nome} com modelo {self.agente.llm_model}")
            
            # Fazer requisição
            response = requests.post(
                'https://api.openai.com/v1/chat/completions',
                headers=headers,
                json=data,
                timeout=60
            )
            
            if response.status_code != 200:
                error_msg = f"Erro na API: {response.status_code}"
                try:
                    error_detail = response.json().get('error', {}).get('message', '')
                    if error_detail:
                        error_msg += f" - {error_detail}"
                except:
                    pass
                
                return {
                    'success': False,
                    'error': error_msg,
                    'details': response.text
                }
            
            # Processar resposta
            result = response.json()
            
            if 'choices' not in result or not result['choices']:
                return {
                    'success': False,
                    'error': 'Resposta inválida da API',
                    'details': str(result)
                }
            
            # Extrair conteúdo JSON
            content = result['choices'][0]['message']['content']
            
            try:
                layout_data = json.loads(content)
            except json.JSONDecodeError as e:
                return {
                    'success': False,
                    'error': f'Resposta JSON inválida do agente: {str(e)}',
                    'details': content[:500]
                }
            
            # Validar estrutura mínima esperada
            if not self._validar_resposta_agente(layout_data):
                return {
                    'success': False,
                    'error': 'Resposta do agente não tem estrutura esperada',
                    'details': str(layout_data)
                }
            
            return {
                'success': True,
                'layout_data': layout_data,
                'raw_response': result
            }
            
        except requests.exceptions.Timeout:
            return {
                'success': False,
                'error': 'Timeout na chamada do agente - tente novamente',
                'details': 'A requisição demorou mais que 60 segundos'
            }
        except requests.exceptions.ConnectionError:
            return {
                'success': False,
                'error': 'Erro de conexão com a API',
                'details': 'Verifique a conexão com a internet'
            }
        except Exception as e:
            logger.error(f"Erro ao chamar agente: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': f'Erro técnico: {str(e)}',
                'details': str(e)
            }

    def _validar_resposta_agente(self, layout_data: Dict) -> bool:
        """Valida se a resposta do agente tem estrutura mínima esperada"""
        try:
            # Verificar campos obrigatórios
            required_fields = ['resumo_decisoes', 'dados_basicos', 'svg_completo']
            
            for field in required_fields:
                if field not in layout_data:
                    logger.error(f"Campo obrigatório '{field}' ausente na resposta do agente")
                    return False
            
            # Verificar se SVG não está vazio
            svg_content = layout_data.get('svg_completo', '').strip()
            if not svg_content or len(svg_content) < 100:
                logger.error("SVG gerado pelo agente está vazio ou muito pequeno")
                return False
            
            # Verificar se é SVG válido (começa com <?xml ou <svg)
            if not (svg_content.startswith('<?xml') or svg_content.startswith('<svg')):
                logger.error("Conteúdo SVG não parece ser válido")
                return False
            
            # Verificar dados_basicos
            dados_basicos = layout_data.get('dados_basicos', {})
            if not isinstance(dados_basicos, dict):
                logger.error("dados_basicos deve ser um objeto")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Erro na validação da resposta: {str(e)}")
            return False

    def _criar_objeto_planta_agente(self, briefing: Briefing, versao: int, 
                                  layout_data: Dict, svg_content: str,
                                  planta_anterior: PlantaBaixa = None) -> PlantaBaixa:
        """Cria e salva objeto PlantaBaixa baseado na resposta do agente"""
        try:
            # Extrair dados importantes
            dados_basicos = layout_data.get('dados_basicos', {})
            resumo_decisoes = layout_data.get('resumo_decisoes', '')
            
            # Preparar dados JSON estruturados
            dados_json = {
                'layout_agente': layout_data,
                'resumo_decisoes': resumo_decisoes,
                'tipo_estande': dados_basicos.get('tipo_estande', ''),
                'areas_atendidas': dados_basicos.get('areas_atendidas', []),
                'lados_abertos': dados_basicos.get('lados_abertos', []),
                'area_total_usada': dados_basicos.get('area_total_usada', 0),
                'nucleo_central': dados_basicos.get('nucleo_central', {}),
                'metadata': {
                    'algoritmo': self.algoritmo_versao,
                    'agente_usado': self.agente.nome,
                    'agente_id': self.agente.id,
                    'gerado_em': timezone.now().isoformat(),
                    'versao': versao
                }
            }
            
            # Parâmetros de geração
            parametros_geracao = {
                'metodo': 'agente_ia',
                'agente_nome': self.agente.nome,
                'agente_modelo': self.agente.llm_model,
                'tipo_estande': dados_basicos.get('tipo_estande', ''),
                'areas_processadas': len(dados_basicos.get('areas_atendidas', [])),
                'resposta_validada': True
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
            nome_arquivo = f"planta_agente_v{versao}_{briefing.projeto.numero}_{timezone.now().strftime('%Y%m%d_%H%M%S')}.svg"
            planta.arquivo_svg.save(nome_arquivo, arquivo_svg)
            
            planta.save()
            
            logger.info(f"Planta baixa v{versao} criada pelo agente salva: {nome_arquivo}")
            return planta
            
        except Exception as e:
            logger.error(f"Erro ao criar objeto planta do agente: {str(e)}", exc_info=True)
            raise Exception(f"Falha ao salvar planta baixa gerada pelo agente: {str(e)}")

    # ==========================================
    # MÉTODOS DE COMPATIBILIDADE E UTILITÁRIOS
    # ==========================================

    def get_area_total(self, planta: PlantaBaixa) -> float:
        """Retorna área total da planta baixa"""
        try:
            dados = planta.dados_json or {}
            return (dados.get('area_total_usada', 0) or 
                   dados.get('layout_agente', {}).get('dados_basicos', {}).get('area_total_usada', 0) or
                   dados.get('layout', {}).get('area_total_usada', 0))
        except:
            return 0

    def get_ambientes(self, planta: PlantaBaixa) -> List[Dict]:
        """Retorna lista de ambientes da planta"""
        try:
            dados = planta.dados_json or {}
            
            # Se foi gerada pelo agente
            if 'layout_agente' in dados:
                areas_atendidas = dados.get('areas_atendidas', [])
                
                # Converter lista de strings em objetos mais estruturados
                ambientes = []
                for i, area_desc in enumerate(areas_atendidas):
                    # Tentar extrair informações da string descritiva
                    nome = area_desc
                    area = 0
                    tipo = 'indefinido'
                    
                    # Parsing básico para extrair metragem
                    import re
                    match = re.search(r'(\d+(?:\.\d+)?)\s*m²', area_desc)
                    if match:
                        area = float(match.group(1))
                    
                    # Detectar tipo baseado no nome
                    area_lower = area_desc.lower()
                    if 'exposição' in area_lower or 'exposicao' in area_lower:
                        tipo = 'exposicao'
                    elif 'reunião' in area_lower or 'reuniao' in area_lower:
                        tipo = 'reuniao'
                    elif 'copa' in area_lower:
                        tipo = 'copa'
                    elif 'depósito' in area_lower or 'deposito' in area_lower:
                        tipo = 'deposito'
                    
                    ambientes.append({
                        'nome': nome,
                        'tipo': tipo,
                        'area': area,
                        'descricao': area_desc
                    })
                
                return ambientes
            
            # Se foi gerada pelo algoritmo antigo
            elif 'layout' in dados:
                layout_data = dados.get('layout', {})
                ambientes_posicionados = layout_data.get('ambientes_posicionados', [])
                
                return [{
                    'nome': amb.get('nome', 'Ambiente'),
                    'tipo': amb.get('tipo', 'indefinido'),
                    'area': amb.get('area', 0),
                    'descricao': f"{amb.get('nome', 'Ambiente')}: {amb.get('area', 0):.1f}m²"
                } for amb in ambientes_posicionados]
            
            return []
        except Exception as e:
            logger.error(f"Erro ao extrair ambientes: {str(e)}")
            return []

    def get_resumo_decisoes(self, planta: PlantaBaixa) -> str:
        """Retorna resumo das decisões do agente ou algoritmo"""
        try:
            dados = planta.dados_json or {}
            
            # Se foi gerada pelo agente
            if 'resumo_decisoes' in dados:
                return dados.get('resumo_decisoes', '')
            
            # Se foi gerada pelo algoritmo, gerar resumo simples
            elif 'layout' in dados:
                layout_data = dados.get('layout', {})
                num_ambientes = len(layout_data.get('ambientes_posicionados', []))
                area_usada = layout_data.get('area_total_usada', 0)
                taxa_ocupacao = layout_data.get('taxa_ocupacao', 0)
                
                return f"Layout algorítmico com {num_ambientes} ambientes, {area_usada:.1f}m² utilizados ({taxa_ocupacao:.1f}% de ocupação)."
            
            return 'Planta baixa gerada - informações de decisão não disponíveis'
        except:
            return 'Informações não disponíveis'

    def get_tipo_estande(self, planta: PlantaBaixa) -> str:
        """Retorna tipo de estande"""
        try:
            dados = planta.dados_json or {}
            return (dados.get('tipo_estande', '') or
                   dados.get('layout_agente', {}).get('dados_basicos', {}).get('tipo_estande', '') or
                   'não especificado')
        except:
            return 'não especificado'

    def get_metodo_geracao(self, planta: PlantaBaixa) -> str:
        """Retorna método usado para gerar a planta"""
        try:
            if 'agente' in (planta.algoritmo_usado or ''):
                return 'agente'
            elif planta.dados_json and 'layout_agente' in planta.dados_json:
                return 'agente'
            else:
                return 'algoritmo'
        except:
            return 'desconhecido'

    def eh_planta_agente(self, planta: PlantaBaixa) -> bool:
        """Verifica se a planta foi gerada pelo agente"""
        return self.get_metodo_geracao(planta) == 'agente'

    def get_lados_abertos(self, planta: PlantaBaixa) -> List[str]:
        """Retorna lista de lados abertos do estande"""
        try:
            dados = planta.dados_json or {}
            return (dados.get('lados_abertos', []) or
                   dados.get('layout_agente', {}).get('dados_basicos', {}).get('lados_abertos', []))
        except:
            return []

    def get_nucleo_central(self, planta: PlantaBaixa) -> Dict:
        """Retorna informações do núcleo central"""
        try:
            dados = planta.dados_json or {}
            return (dados.get('nucleo_central', {}) or
                   dados.get('layout_agente', {}).get('dados_basicos', {}).get('nucleo_central', {}))
        except:
            return {}

    # ==========================================
    # MÉTODOS PARA REGENERAÇÃO E REFINAMENTO
    # ==========================================

    def regenerar_planta_baixa(self, planta_atual: PlantaBaixa, 
                              instrucoes_modificacao: str = '') -> Dict:
        """Regenera uma planta baixa existente com modificações opcionais"""
        try:
            briefing = planta_atual.briefing
            nova_versao = planta_atual.versao + 1
            
            # Construir prompt com modificações se fornecidas
            prompt_base = self._construir_prompt_briefing(briefing)
            
            if instrucoes_modificacao.strip():
                prompt_modificado = f"""{prompt_base}

=== MODIFICAÇÕES SOLICITADAS ===
Baseado na planta anterior (v{planta_atual.versao}), faça as seguintes modificações:
{instrucoes_modificacao}

Mantenha os aspectos que funcionaram bem na versão anterior, mas implemente as modificações solicitadas.
"""
            else:
                prompt_modificado = prompt_base
            
            # Gerar nova versão
            return self.gerar_planta_baixa(briefing, nova_versao, planta_atual)
            
        except Exception as e:
            logger.error(f"Erro ao regenerar planta baixa: {str(e)}")
            return {
                'success': False,
                'error': f'Erro ao regenerar planta: {str(e)}',
                'critica': f'❌ ERRO NA REGENERAÇÃO: {str(e)}',
                'pode_prosseguir': False
            }

    def refinar_planta_com_feedback(self, planta_atual: PlantaBaixa, 
                                   feedback_usuario: str) -> Dict:
        """Refina uma planta baixa baseado no feedback do usuário"""
        try:
            # Extrair informações da planta atual
            dados_atual = planta_atual.dados_json or {}
            resumo_atual = dados_atual.get('resumo_decisoes', '')
            areas_atuais = dados_atual.get('areas_atendidas', [])
            
            # Construir prompt de refinamento
            prompt_refinamento = f"""
=== REFINAMENTO DE PLANTA BAIXA ===

PLANTA ATUAL (v{planta_atual.versao}):
Decisões tomadas: {resumo_atual}
Áreas incluídas: {', '.join(areas_atuais)}

FEEDBACK DO USUÁRIO:
{feedback_usuario}

=== BRIEFING ORIGINAL ===
{self._construir_prompt_briefing(planta_atual.briefing)}

=== SOLICITAÇÃO DE REFINAMENTO ===
Com base no feedback fornecido, ajuste a planta baixa mantendo os aspectos positivos e corrigindo os pontos mencionados.
Explique claramente as mudanças feitas em relação à versão anterior.
"""
            
            # Chamar agente para refinamento
            resultado_agente = self._chamar_agente_arquiteto(prompt_refinamento)
            
            if not resultado_agente['success']:
                return {
                    'success': False,
                    'error': f"Erro no refinamento: {resultado_agente['error']}",
                    'critica': f"❌ ERRO DO AGENTE NO REFINAMENTO: {resultado_agente['error']}"
                }
            
            # Processar resposta e criar nova versão
            layout_data = resultado_agente['layout_data']
            svg_content = layout_data.get('svg_completo', '')
            
            if not svg_content:
                return {
                    'success': False,
                    'error': 'Agente não gerou SVG válido no refinamento',
                    'critica': '❌ SVG INVÁLIDO NO REFINAMENTO'
                }
            
            # Criar nova versão refinada
            nova_versao = planta_atual.versao + 1
            planta_refinada = self._criar_objeto_planta_agente(
                planta_atual.briefing, nova_versao, layout_data, svg_content, planta_atual
            )
            
            # Marcar planta anterior como substituída
            planta_atual.status = 'substituida'
            planta_atual.save(update_fields=['status'])
            
            return {
                'success': True,
                'planta': planta_refinada,
                'layout': layout_data,
                'message': f'Planta baixa refinada com sucesso (v{nova_versao})!',
                'mudancas': layout_data.get('resumo_decisoes', ''),
                'feedback_aplicado': feedback_usuario
            }
            
        except Exception as e:
            logger.error(f"Erro ao refinar planta: {str(e)}")
            return {
                'success': False,
                'error': f'Erro técnico no refinamento: {str(e)}',
                'critica': f'❌ ERRO TÉCNICO NO REFINAMENTO: {str(e)}'
            }

    # ==========================================
    # MÉTODOS PARA ANÁLISE E VALIDAÇÃO
    # ==========================================

    def analisar_planta_baixa(self, planta: PlantaBaixa) -> Dict:
        """Analisa uma planta baixa e retorna métricas e informações"""
        try:
            dados = planta.dados_json or {}
            
            analise = {
                'versao': planta.versao,
                'metodo_geracao': self.get_metodo_geracao(planta),
                'area_total_usada': self.get_area_total(planta),
                'num_ambientes': len(self.get_ambientes(planta)),
                'tipo_estande': self.get_tipo_estande(planta),
                'lados_abertos': self.get_lados_abertos(planta),
                'resumo_decisoes': self.get_resumo_decisoes(planta),
                'data_criacao': planta.criado_em,
                'data_atualizacao': planta.atualizado_em,
                'status': planta.status
            }
            
            # Adicionar informações específicas do agente se disponível
            if self.eh_planta_agente(planta):
                nucleo = self.get_nucleo_central(planta)
                analise.update({
                    'agente_usado': dados.get('metadata', {}).get('agente_usado', ''),
                    'nucleo_central': nucleo,
                    'areas_atendidas': dados.get('areas_atendidas', [])
                })
            
            # Calcular métricas de eficiência
            if planta.briefing and planta.briefing.area_estande:
                area_briefing = float(planta.briefing.area_estande)
                area_usada = analise['area_total_usada']
                analise['eficiencia_espacial'] = (area_usada / area_briefing) * 100 if area_briefing > 0 else 0
            
            return {
                'success': True,
                'analise': analise
            }
            
        except Exception as e:
            logger.error(f"Erro na análise da planta: {str(e)}")
            return {
                'success': False,
                'error': f'Erro na análise: {str(e)}'
            }

    def comparar_plantas(self, planta1: PlantaBaixa, planta2: PlantaBaixa) -> Dict:
        """Compara duas plantas baixas e retorna as diferenças"""
        try:
            analise1 = self.analisar_planta_baixa(planta1)['analise']
            analise2 = self.analisar_planta_baixa(planta2)['analise']
            
            comparacao = {
                'planta_1': {
                    'versao': analise1['versao'],
                    'metodo': analise1['metodo_geracao'],
                    'area_usada': analise1['area_total_usada'],
                    'num_ambientes': analise1['num_ambientes']
                },
                'planta_2': {
                    'versao': analise2['versao'],
                    'metodo': analise2['metodo_geracao'],
                    'area_usada': analise2['area_total_usada'],
                    'num_ambientes': analise2['num_ambientes']
                },
                'diferencas': {
                    'area_usada': analise2['area_total_usada'] - analise1['area_total_usada'],
                    'num_ambientes': analise2['num_ambientes'] - analise1['num_ambientes'],
                    'mudou_metodo': analise1['metodo_geracao'] != analise2['metodo_geracao']
                }
            }
            
            # Adicionar recomendação
            if comparacao['diferencas']['area_usada'] > 0:
                comparacao['recomendacao'] = f"Versão {analise2['versao']} utiliza {comparacao['diferencas']['area_usada']:.1f}m² a mais"
            elif comparacao['diferencas']['area_usada'] < 0:
                comparacao['recomendacao'] = f"Versão {analise2['versao']} utiliza {abs(comparacao['diferencas']['area_usada']):.1f}m² a menos"
            else:
                comparacao['recomendacao'] = "Ambas as versões utilizam a mesma área"
            
            return {
                'success': True,
                'comparacao': comparacao
            }
            
        except Exception as e:
            logger.error(f"Erro na comparação: {str(e)}")
            return {
                'success': False,
                'error': f'Erro na comparação: {str(e)}'
            }

    # ==========================================
    # MÉTODOS DE EXPORTAÇÃO E UTILIDADES
    # ==========================================

    def exportar_dados_planta(self, planta: PlantaBaixa, formato: str = 'json') -> Dict:
        """Exporta dados da planta em diferentes formatos"""
        try:
            if formato.lower() == 'json':
                dados_exportacao = {
                    'projeto': {
                        'numero': planta.projeto.numero,
                        'nome': planta.projeto.nome,
                        'empresa': planta.projeto.empresa.nome
                    },
                    'planta': {
                        'versao': planta.versao,
                        'metodo_geracao': self.get_metodo_geracao(planta),
                        'algoritmo_usado': planta.algoritmo_usado,
                        'status': planta.status,
                        'criado_em': planta.criado_em.isoformat(),
                        'atualizado_em': planta.atualizado_em.isoformat()
                    },
                    'layout': {
                        'area_total_usada': self.get_area_total(planta),
                        'tipo_estande': self.get_tipo_estande(planta),
                        'lados_abertos': self.get_lados_abertos(planta),
                        'nucleo_central': self.get_nucleo_central(planta),
                        'ambientes': self.get_ambientes(planta)
                    },
                    'decisoes': {
                        'resumo': self.get_resumo_decisoes(planta),
                        'areas_atendidas': planta.dados_json.get('areas_atendidas', []) if planta.dados_json else []
                    }
                }
                
                return {
                    'success': True,
                    'dados': dados_exportacao,
                    'formato': 'json'
                }
            
            else:
                return {
                    'success': False,
                    'error': f'Formato {formato} não suportado'
                }
                
        except Exception as e:
            logger.error(f"Erro na exportação: {str(e)}")
            return {
                'success': False,
                'error': f'Erro na exportação: {str(e)}'
            }

    def get_historico_versoes(self, projeto) -> List[Dict]:
        """Retorna histórico de todas as versões de plantas baixas de um projeto"""
        try:
            plantas = PlantaBaixa.objects.filter(projeto=projeto).order_by('-versao')
            
            historico = []
            for planta in plantas:
                analise = self.analisar_planta_baixa(planta)
                if analise['success']:
                    historico.append(analise['analise'])
            
            return historico
            
        except Exception as e:
            logger.error(f"Erro ao obter histórico: {str(e)}")
            return []

    def validar_configuracao_agente(self) -> Dict:
        """Valida se o agente está configurado corretamente"""
        try:
            # Verificar se agente existe e está ativo
            if not self.agente:
                return {
                    'valido': False,
                    'erro': 'Agente não encontrado'
                }
            
            if not self.agente.ativo:
                return {
                    'valido': False,
                    'erro': 'Agente não está ativo'
                }
            
            # Verificar campos obrigatórios
            campos_obrigatorios = ['llm_model', 'llm_system_prompt', 'task_instructions']
            for campo in campos_obrigatorios:
                if not getattr(self.agente, campo, None):
                    return {
                        'valido': False,
                        'erro': f'Campo {campo} não configurado no agente'
                    }
            
            # Verificar se tem API key
            if not settings.OPENAI_API_KEY:
                return {
                    'valido': False,
                    'erro': 'OPENAI_API_KEY não configurada'
                }
            
            return {
                'valido': True,
                'agente': {
                    'nome': self.agente.nome,
                    'modelo': self.agente.llm_model,
                    'temperatura': self.agente.llm_temperature,
                    'ativo': self.agente.ativo
                }
            }
            
        except Exception as e:
            return {
                'valido': False,
                'erro': f'Erro na validação: {str(e)}'
            }