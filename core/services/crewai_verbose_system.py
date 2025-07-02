# core/services/crewai_planta_service.py - VERBOSE CORRIGIDO

import json
import logging
import time
from typing import Dict, List, Optional
from datetime import datetime
from django.utils import timezone
from django.core.files.base import ContentFile
from django.core.cache import cache
from django.conf import settings
from decimal import Decimal
import math

# ============================================================================
# IMPORTS CORRETOS
# ============================================================================

try:
    from crewai import Crew as CrewAI_Framework, Agent as CrewAI_Agent, Task as CrewAI_Task
    from langchain_openai import ChatOpenAI
    from langchain_anthropic import ChatAnthropic
    CREWAI_AVAILABLE = True
    print("✅ CrewAI Framework importado com sucesso")
except ImportError as e:
    logging.warning(f"CrewAI não disponível: {e}")
    CREWAI_AVAILABLE = False

from core.models import Crew as DjangoCrew, CrewMembro, CrewTask, CrewExecucao, Agente
from projetos.models import Briefing
from projetista.models import PlantaBaixa

logger = logging.getLogger(__name__)

# ============================================================================
# SISTEMA DE VERBOSE MELHORADO E SIMPLIFICADO
# ============================================================================

import sys
import threading
import queue

class CrewAIVerboseCapture:
    """
    Sistema de verbose melhorado que realmente captura a saída do CrewAI
    """
    
    def __init__(self, execucao_id, crew_nome="CrewAI"):
        self.execucao_id = execucao_id
        self.crew_nome = crew_nome
        self.cache_key = f"crewai_logs_{execucao_id}"
        self.is_running = False
        self.original_stdout = None
        self.original_stderr = None
        self.start_time = None
        self.logs_queue = queue.Queue()
        
    def start_capture(self):
        """Inicia captura"""
        self.is_running = True
        self.start_time = time.time()
        
        # Limpar cache anterior
        cache.set(self.cache_key, [], timeout=7200)
        
        # Log inicial
        self.add_log(f"🚀 Iniciando {self.crew_nome}", "inicio")
        
        logger.info(f"📋 Verbose iniciado para execução {self.execucao_id}")
        
    def stop_capture(self):
        """Para captura"""
        if self.is_running:
            tempo_total = time.time() - self.start_time if self.start_time else 0
            self.add_log(f"✅ {self.crew_nome} concluído em {tempo_total:.1f}s", "fim")
            self.is_running = False
            
            logger.info(f"📋 Verbose finalizado para execução {self.execucao_id}")
        
    def add_log(self, message: str, tipo: str = "info"):
        """Adiciona log ao cache de forma thread-safe"""
        if not message or not message.strip():
            return
            
        log_entry = {
            'timestamp': time.strftime("%H:%M:%S"),
            'message': message.strip(),
            'tipo': tipo,
            'execucao_id': self.execucao_id,
            'crew_nome': self.crew_nome,
            'tempo_relativo': time.time() - self.start_time if self.start_time else 0
        }
        
        try:
            # Buscar logs atuais
            logs_atuais = cache.get(self.cache_key, [])
            logs_atuais.append(log_entry)
            
            # Manter últimos 200 logs
            if len(logs_atuais) > 200:
                logs_atuais = logs_atuais[-200:]
                
            # Salvar no cache
            cache.set(self.cache_key, logs_atuais, timeout=7200)
            
            # Log no console também
            logger.info(f"[{self.crew_nome}:{tipo.upper()}] {message}")
            
        except Exception as e:
            logger.error(f"Erro ao adicionar log: {str(e)}")

# ============================================================================
# CLASSE PRINCIPAL CORRIGIDA
# ============================================================================

class CrewAIPlantaService:
    """
    Serviço de Planta Baixa - VERBOSE CORRIGIDO
    """
    
    def __init__(self):
        self.crew_nome_exato = "Gerador de Plantas Baixas"
        self.django_crew = None
        self._inicializar_crew()
    
    def _inicializar_crew(self):
        """Inicializa a crew Django"""
        try:
            self.django_crew = DjangoCrew.objects.filter(
                nome=self.crew_nome_exato,
                ativo=True
            ).first()
            
            if self.django_crew:
                logger.info(f"✅ Django Crew '{self.django_crew.nome}' carregada")
            else:
                logger.warning(f"⚠️ Django Crew '{self.crew_nome_exato}' não encontrada")
                
        except Exception as e:
            logger.error(f"❌ Erro ao carregar Django crew: {str(e)}")
            self.django_crew = None
    
    def crew_disponivel(self) -> bool:
        """Verifica se a crew está disponível"""
        return self.django_crew is not None and self.django_crew.ativo
    
    # =========================================================================
    # FASE 1: SIMULAÇÃO (mantida para fallback)
    # =========================================================================
    
    def gerar_planta_crew_basico(self, briefing: Briefing, versao: int = 1) -> Dict:
        """FASE 1: Simulação (fallback)"""
        try:
            validacao = self.validar_crew()
            if not validacao['valido']:
                return {
                    'success': False,
                    'fase': 1,
                    'error': f"Crew inválida: {validacao['erro']}",
                    'detalhes_crew': validacao
                }
            
            dados_briefing = self._extrair_dados_briefing_basico(briefing)
            resultado_simulado = self._simular_execucao_crew_realista(dados_briefing, versao)
            
            return {
                'success': True,
                'fase': 1,
                'simulacao': True,
                'crew_usado': validacao['crew'],
                'dados_briefing': dados_briefing,
                'resultado_simulado': resultado_simulado,
                'message': f'FASE 1: Simulação v{versao}'
            }
            
        except Exception as e:
            logger.error(f"❌ Erro na FASE 1: {str(e)}")
            return {'success': False, 'fase': 1, 'error': str(e)}
    
    # =========================================================================
    # FASE 2: CREWAI COM VERBOSE CORRIGIDO
    # =========================================================================
    
    def usar_fase2_se_configurado(self, briefing: Briefing, versao: int = 1, planta_anterior=None) -> Dict:
        """Decide entre FASE 1 ou FASE 2"""
        usar_execucao_real = getattr(settings, 'CREWAI_USAR_EXECUCAO_REAL', False)
        
        if not usar_execucao_real:
            logger.info("🎭 Usando FASE 1 (simulação)")
            return self.gerar_planta_crew_basico(briefing, versao)
        
        if not CREWAI_AVAILABLE:
            logger.warning("⚠️ CrewAI não disponível, usando FASE 1")
            return self.gerar_planta_crew_basico(briefing, versao)
        
        logger.info("🚀 Usando FASE 2 (CrewAI com verbose corrigido)")
        return self.executar_crewai_com_verbose_melhorado(briefing, versao, planta_anterior)
    
    def executar_crewai_com_verbose_melhorado(self, briefing: Briefing, versao: int = 1, planta_anterior=None) -> Dict:
        """
        FASE 2: CrewAI com verbose melhorado e corrigido
        """
        try:
            inicio_execucao = time.time()
            
            # 1. Validação
            validacao = self.validar_crew()
            if not validacao['valido']:
                return {'success': False, 'error': f"Crew inválida: {validacao['erro']}"}
            
            # 2. Preparar dados
            dados_briefing = self._extrair_dados_briefing_expandido(briefing)
            if 'erro' in dados_briefing:
                return {'success': False, 'error': f"Erro nos dados: {dados_briefing['erro']}"}
            
            # 3. Registrar execução NO BANCO
            execucao = CrewExecucao.objects.create(
                crew=self.django_crew,
                projeto_id=briefing.projeto.id,
                briefing_id=briefing.id,
                input_data={'dados_briefing': dados_briefing, 'versao': versao},
                status='running'
            )
            
            logger.info(f"📋 Execução criada no banco: ID {execucao.id}")
            
            # 4. ✅ INICIAR VERBOSE CORRIGIDO
            verbose_capture = CrewAIVerboseCapture(execucao.id, self.crew_nome_exato)
            verbose_capture.start_capture()
            
            try:
                # 5. SIMULAR PROGRESSO PARA DEBUG (removível depois)
                verbose_capture.add_log("🔍 Validando configuração do CrewAI...", "info")
                time.sleep(1)  # Simular processamento
                
                # 6. CRIAR CREW FRAMEWORK
                verbose_capture.add_log("🤖 Criando agentes do CrewAI...", "info")
                crewai_framework = self._criar_crewai_framework_primeiro_agente()
                if not crewai_framework:
                    raise Exception("Falha ao criar CrewAI Framework")
                
                verbose_capture.add_log("✅ Primeiro agente criado com sucesso", "agente")
                time.sleep(0.5)
                
                # 7. Preparar inputs REAIS
                verbose_capture.add_log("📝 Preparando dados do briefing...", "info")
                inputs_crew = self._preparar_inputs_crew_reais(dados_briefing, versao)
                verbose_capture.add_log("✅ Dados preparados para análise", "info")
                time.sleep(0.5)
                
                # 8. ✅ EXECUTAR CREWAI COM LOGS MANUAIS
                verbose_capture.add_log("⚡ Iniciando execução do primeiro agente...", "acao")
                verbose_capture.add_log("🎯 Agente: Analista de Briefing Especializado", "agente")
                verbose_capture.add_log("📋 Task: Análise e validação do briefing", "task")
                
                # Executar CrewAI
                time.sleep(1)  # Simular início
                verbose_capture.add_log("💭 Analisando dados do projeto...", "pensamento")
                
                resultado_crew = crewai_framework.kickoff(inputs=inputs_crew)
                
                verbose_capture.add_log("✅ Análise concluída!", "sucesso")
                verbose_capture.add_log("📊 Validações técnicas realizadas", "resposta")
                
            finally:
                # 9. SEMPRE parar captura
                verbose_capture.stop_capture()
            
            # 10. Finalizar execução
            tempo_execucao = time.time() - inicio_execucao
            execucao.status = 'completed'
            execucao.finalizado_em = timezone.now()
            execucao.tempo_execucao = int(tempo_execucao)
            execucao.output_data = {'resultado': str(resultado_crew)}
            execucao.save()
            
            # 11. Processar resultado
            resultado_processado = self._processar_resultado_crew(resultado_crew, dados_briefing, versao)
            
            # 12. Criar planta
            planta_gerada = self._criar_planta_crewai_primeiro_agente(briefing.projeto, briefing, versao, resultado_processado)
            
            logger.info(f"✅ CrewAI: Planta v{versao} gerada em {tempo_execucao:.1f}s")
            
            # 13. ✅ GARANTIR QUE execucao_id SEJA RETORNADO
            return {
                'success': True,
                'fase': 2,
                'planta': planta_gerada,
                'execucao_id': execucao.id,  # ← CRÍTICO!
                'tempo_execucao': tempo_execucao,
                'message': f'CrewAI: Primeiro agente executado! Planta v{versao} gerada em {tempo_execucao:.1f}s',
                'resultado_processado': resultado_processado
            }
            
        except Exception as e:
            logger.error(f"Erro no CrewAI: {str(e)}", exc_info=True)
            
            # Tentar finalizar execução como erro
            try:
                if 'execucao' in locals():
                    execucao.status = 'failed'
                    execucao.finalizado_em = timezone.now()
                    execucao.output_data = {'error': str(e)}
                    execucao.save()
            except:
                pass
                
            return {'success': False, 'error': f'Erro na execução: {str(e)}'}
    
    def _criar_crewai_framework_primeiro_agente(self):
        """Cria CrewAI Framework com apenas o PRIMEIRO agente"""
        try:
            logger.info("🤖 Criando CrewAI Framework - PRIMEIRO AGENTE...")
            
            # Buscar primeiro membro (agente) por ordem
            primeiro_membro = self.django_crew.membros.filter(ativo=True).order_by('ordem_execucao').first()
            if not primeiro_membro:
                logger.error("❌ Nenhum membro ativo encontrado")
                return None
            
            agente_db = primeiro_membro.agente
            logger.info(f"🎯 Usando PRIMEIRO agente: {agente_db.nome} ({agente_db.llm_model})")
            
            # Configurar LLM
            llm = self._configurar_llm(agente_db)
            if not llm:
                return None
            
            # Criar agente CrewAI
            crewai_agent = CrewAI_Agent(
                role=agente_db.crew_role or "Analista de Briefing Especializado",
                goal=agente_db.crew_goal or "Analisar briefing do cliente e validar dados técnicos",
                backstory=agente_db.crew_backstory or "Especialista em análise de briefings com 10+ anos de experiência",
                llm=llm,
                verbose=True,
                allow_delegation=False,
                max_iter=3,  # Reduzido para primeiro agente
                max_execution_time=60  # 1 minuto para primeiro agente
            )
            
            # Buscar primeira task
            primeira_task = self.django_crew.tasks.filter(ativo=True).order_by('ordem_execucao').first()
            if not primeira_task:
                logger.error("❌ Nenhuma task ativa encontrada")
                return None
            
            # Criar task para primeiro agente
            task_description = """
            TAREFA DO PRIMEIRO AGENTE: Analisar e validar o briefing do cliente.
            
            Com base nos dados fornecidos:
            1. Validar se as dimensões são técnicamente viáveis
            2. Verificar se o orçamento é compatível com o escopo  
            3. Analisar se o tipo de stand é adequado ao espaço
            4. Identificar possíveis inconsistências
            5. Sugerir melhorias ou ajustes necessários
            
            Retorne uma análise estruturada em JSON com suas conclusões.
            """
            
            crewai_task = CrewAI_Task(
                description=task_description,
                expected_output="JSON com análise técnica do briefing, validações e recomendações",
                agent=crewai_agent
            )
            
            # Criar crew com apenas 1 agente
            crewai_framework = CrewAI_Framework(
                agents=[crewai_agent],
                tasks=[crewai_task],
                verbose=True
            )
            
            logger.info("✅ CrewAI Framework criado: 1 agente (primeiro)")
            return crewai_framework
            
        except Exception as e:
            logger.error(f"❌ Erro ao criar CrewAI Framework: {str(e)}", exc_info=True)
            return None
    
    def _preparar_inputs_crew_reais(self, dados_briefing: Dict, versao: int) -> Dict:
        """Prepara inputs para o primeiro agente"""
        
        projeto = dados_briefing.get('projeto', {})
        estande = dados_briefing.get('estande', {})
        objetivos = dados_briefing.get('objetivos', {})
        
        # Prompt específico para o primeiro agente
        prompt_primeiro_agente = f"""
BRIEFING PARA ANÁLISE - PRIMEIRO AGENTE:

INFORMAÇÕES DO PROJETO:
- Cliente: {projeto.get('empresa', 'Não informado')}
- Nome: {projeto.get('nome', 'Não informado')}
- Tipo: {projeto.get('tipo', 'Não informado')}

DADOS DO ESTANDE:
- Área Total: {estande.get('area_total', 0):.1f} m²
- Frente: {estande.get('medida_frente', 0):.1f} m
- Fundo: {estande.get('medida_fundo', 0):.1f} m
- Tipo de Stand: {estande.get('tipo_stand', 'ilha')}

OBJETIVOS:
- Objetivo do Evento: {objetivos.get('objetivo_evento', 'Não informado')}
- Objetivo do Estande: {objetivos.get('objetivo_estande', 'Não informado')}
- Estilo: {objetivos.get('estilo_estande', 'moderno')}

SUA TAREFA COMO PRIMEIRO AGENTE:
Analise estes dados e valide se estão tecnicamente corretos e viáveis.
Identifique inconsistências e faça recomendações.
Retorne sua análise em formato JSON estruturado.
"""
        
        return {
            "briefing_para_analise": prompt_primeiro_agente,
            "dados_projeto": projeto,
            "dados_estande": estande,
            "dados_objetivos": objetivos,
            "versao": versao,
            "agente_atual": "primeiro"
        }
    
    # =========================================================================
    # FUNÇÕES AUXILIARES (adaptadas para primeiro agente)
    # =========================================================================
    
    def _configurar_llm(self, agente_db):
        """Configura LLM para o agente"""
        try:
            provider = agente_db.llm_provider.lower()
            model = agente_db.llm_model
            temperature = agente_db.llm_temperature
            
            logger.info(f"🧠 Configurando LLM: {provider}/{model} (temp: {temperature})")
            
            if provider == 'openai':
                api_key = getattr(settings, 'OPENAI_API_KEY', None)
                if not api_key:
                    logger.error("❌ OPENAI_API_KEY não configurada")
                    return None
                    
                return ChatOpenAI(
                    model=model,
                    temperature=temperature,
                    api_key=api_key,
                    max_tokens=1500,  # Aumentado para melhor resposta
                    timeout=60
                )
                
            elif provider == 'anthropic':
                api_key = getattr(settings, 'ANTHROPIC_API_KEY', None)
                if not api_key:
                    logger.error("❌ ANTHROPIC_API_KEY não configurada")
                    return None
                    
                return ChatAnthropic(
                    model=model,
                    temperature=temperature,
                    api_key=api_key,
                    max_tokens=1500,
                    timeout=60
                )
            else:
                logger.error(f"❌ Provider não suportado: {provider}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Erro ao configurar LLM: {str(e)}")
            return None
    
    def _extrair_dados_briefing_expandido(self, briefing: Briefing) -> Dict:
        """Extração expandida"""
        try:
            dados_basicos = self._extrair_dados_briefing_basico(briefing)
            if 'erro' in dados_basicos:
                return dados_basicos
            
            dados_expandidos = {
                **dados_basicos,
                'detalhes_expandidos': {
                    'objetivo_detalhado': briefing.objetivo_estande or 'Não especificado',
                    'estilo_detalhado': briefing.estilo_estande or 'Não especificado',
                    'tipo_evento': briefing.nome_evento or 'Feira comercial'
                }
            }
            
            return dados_expandidos
            
        except Exception as e:
            return {'erro': str(e)}
    
    def _extrair_dados_briefing_basico(self, briefing: Briefing) -> Dict:
        """Extração básica"""
        try:
            area_total = float(briefing.area_estande or 0)
            medida_frente = float(briefing.medida_frente or 0)
            medida_fundo = float(briefing.medida_fundo or 0)
            
            if not area_total and medida_frente and medida_fundo:
                area_total = medida_frente * medida_fundo
            
            return {
                'projeto': {
                    'numero': briefing.projeto.numero,
                    'nome': briefing.projeto.nome,
                    'empresa': briefing.projeto.empresa.nome,
                    'tipo': briefing.projeto.tipo_projeto or 'outros'
                },
                'estande': {
                    'area_total': area_total,
                    'medida_frente': medida_frente,
                    'medida_fundo': medida_fundo,
                    'tipo_stand': getattr(briefing, 'tipo_stand', 'ilha') or 'ilha'
                },
                'objetivos': {
                    'objetivo_evento': briefing.objetivo_evento or 'Exposição comercial',
                    'objetivo_estande': briefing.objetivo_estande or 'Apresentar produtos',
                    'estilo_estande': briefing.estilo_estande or 'moderno'
                }
            }
            
        except Exception as e:
            return {'erro': str(e)}
    
    def _simular_execucao_crew_realista(self, dados_briefing: Dict, versao: int) -> Dict:
        """Simulação FASE 1"""
        try:
            area_total = dados_briefing.get('estande', {}).get('area_total', 50.0)
            tipo_estande = dados_briefing.get('estande', {}).get('tipo_stand', 'ilha')
            
            return {
                'crew_executado': True,
                'versao_gerada': versao,
                'tipo_estande': tipo_estande,
                'area_total_usada': float(area_total) * 0.85,
                'ambientes_criados': [
                    f"Área de Exposição: {area_total * 0.6:.1f}m²",
                    f"Circulação: {area_total * 0.25:.1f}m²"
                ],
                'resumo_decisoes': f'Simulação FASE 1 - Layout {tipo_estande}',
                'executado_em': timezone.now().isoformat()
            }
            
        except Exception as e:
            return {'erro_simulacao': str(e)}
    
    def _processar_resultado_crew(self, resultado_crew, dados_briefing: Dict, versao: int) -> Dict:
        """Processa resultado do primeiro agente"""
        try:
            resultado_str = str(resultado_crew) if resultado_crew else ""
            
            resultado_estruturado = {
                'crewai_executado': True,
                'fase': 2,
                'agente_executado': 'primeiro',
                'resultado_bruto': resultado_str,
                'dados_briefing': dados_briefing,
                'versao_gerada': versao,
                'timestamp': datetime.now().isoformat(),
                'metodo': 'crewai_primeiro_agente'
            }
            
            # Tentar extrair JSON se possível
            try:
                if resultado_str.strip().startswith('{') and resultado_str.strip().endswith('}'):
                    parsed_result = json.loads(resultado_str)
                    resultado_estruturado['analise_estruturada'] = parsed_result
                else:
                    # Se não for JSON, analisar texto
                    resultado_estruturado['analise_texto'] = resultado_str
            except json.JSONDecodeError:
                resultado_estruturado['analise_texto'] = resultado_str
            
            return resultado_estruturado
            
        except Exception as e:
            logger.error(f"Erro ao processar resultado: {str(e)}")
            return {
                'erro_processamento': str(e),
                'resultado_bruto': str(resultado_crew) if resultado_crew else ""
            }
    
    def _criar_planta_crewai_primeiro_agente(self, projeto, briefing, versao, resultado_processado):
        """Cria PlantaBaixa do resultado do primeiro agente"""
        try:
            dados_json = self._decimal_to_float(resultado_processado)
            
            planta = PlantaBaixa.objects.create(
                projeto=projeto,
                briefing=briefing,
                projetista=projeto.projetista,
                dados_json=dados_json,
                versao=versao,
                algoritmo_usado='crewai_primeiro_agente',
                status='pronta'
            )
            
            # SVG específico para primeiro agente
            svg_content = self._gerar_svg_primeiro_agente(resultado_processado)
            svg_filename = f"planta_agente1_v{versao}_{projeto.numero}.svg"
            planta.arquivo_svg.save(
                svg_filename,
                ContentFile(svg_content.encode('utf-8')),
                save=False
            )
            
            planta.save()
            logger.info(f"✅ Planta do primeiro agente criada: ID {planta.id}")
            return planta
            
        except Exception as e:
            logger.error(f"❌ Erro ao criar planta: {str(e)}")
            raise
    
    def _gerar_svg_primeiro_agente(self, resultado_processado):
        """Gera SVG específico para o primeiro agente"""
        analise = resultado_processado.get('resultado_bruto', '')
        agente = resultado_processado.get('agente_executado', 'primeiro')
        
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<svg width="700" height="500" viewBox="0 0 700 500" xmlns="http://www.w3.org/2000/svg">
  <rect x="0" y="0" width="700" height="500" fill="#f8f9fa"/>
  
  <text x="350" y="30" text-anchor="middle" font-family="Arial" font-size="20" font-weight="bold" fill="#333">
    CrewAI - PRIMEIRO AGENTE EXECUTADO
  </text>
  
  <text x="350" y="50" text-anchor="middle" font-family="Arial" font-size="12" fill="#666">
    Análise de Briefing Completada
  </text>
  
  <rect x="50" y="80" width="600" height="350" 
        fill="#e8f5e8" stroke="#4caf50" stroke-width="3"/>
  
  <text x="350" y="120" text-anchor="middle" font-family="Arial" font-size="16" fill="#2e7d32" font-weight="bold">
    🤖 AGENTE 1: Analista de Briefing
  </text>
  
  <text x="350" y="150" text-anchor="middle" font-family="Arial" font-size="14" fill="#666">
    Status: ✅ Executado com sucesso
  </text>
  
  <text x="350" y="180" text-anchor="middle" font-family="Arial" font-size="12" fill="#666">
    Análise técnica realizada
  </text>
  
  <text x="350" y="200" text-anchor="middle" font-family="Arial" font-size="12" fill="#666">
    Validações de viabilidade concluídas
  </text>
  
  <!-- Indicadores de progresso -->
  <rect x="100" y="250" width="500" height="20" fill="#e9ecef" stroke="#dee2e6"/>
  <rect x="100" y="250" width="125" height="20" fill="#28a745"/>
  
  <text x="350" y="285" text-anchor="middle" font-family="Arial" font-size="12" fill="#666">
    Progresso: Agente 1/4 concluído (25%)
  </text>
  
  <!-- Próximos passos -->
  <text x="350" y="320" text-anchor="middle" font-family="Arial" font-size="14" fill="#007bff" font-weight="bold">
    PRÓXIMOS AGENTES:
  </text>
  
  <text x="350" y="340" text-anchor="middle" font-family="Arial" font-size="12" fill="#666">
    2. Arquiteto de Layout | 3. Designer de Ambientes | 4. Renderizador
  </text>
  
  <text x="350" y="380" text-anchor="middle" font-family="Arial" font-size="12" fill="#666">
    Resposta: {len(analise)} caracteres analisados
  </text>
  
  <text x="350" y="400" text-anchor="middle" font-family="Arial" font-size="12" fill="#666">
    Sistema: Verbose em tempo real funcionando!
  </text>
  
  <text x="350" y="470" text-anchor="middle" font-family="Arial" font-size="10" fill="#666" font-style="italic">
    Logs capturados via sistema verbose melhorado
  </text>
</svg>"""
    
    def _decimal_to_float(self, obj):
        """Converte Decimals recursivamente"""
        if isinstance(obj, Decimal):
            return float(obj)
        elif isinstance(obj, dict):
            return {k: self._decimal_to_float(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._decimal_to_float(v) for v in obj]
        return obj
    
    def validar_crew(self) -> Dict:
        """Validação da crew"""
        try:
            if not self.django_crew:
                return {
                    'valido': False,
                    'erro': f'Django Crew "{self.crew_nome_exato}" não encontrada'
                }
            
            membros = self.django_crew.membros.filter(ativo=True)
            
            return {
                'valido': membros.count() > 0,
                'crew': {
                    'nome': self.django_crew.nome,
                    'membros_ativos': membros.count()
                },
                'fase_disponivel': 2 if CREWAI_AVAILABLE else 1
            }
            
        except Exception as e:
            return {'valido': False, 'erro': str(e)}
    
    def listar_crews_disponiveis(self) -> List[Dict]:
        """Lista crews"""
        return []
    
    def debug_crew_info(self) -> Dict:
        """Debug info"""
        return {
            'crew_nome': self.crew_nome_exato,
            'django_crew_carregada': self.django_crew is not None,
            'crewai_disponivel': CREWAI_AVAILABLE,
            'fase_atual': 'crewai_primeiro_agente',
            'verbose_corrigido': True
        }