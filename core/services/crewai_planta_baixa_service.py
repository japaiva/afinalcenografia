# core/services/crewai_planta_service.py - FASE 1: TESTE BÁSICO

import json
import logging
from typing import Dict, List, Optional
from django.utils import timezone
from django.core.files.base import ContentFile

from core import models
from core.models import Crew, CrewMembro, CrewTask, CrewExecucao, Agente
from projetos.models import Briefing
from projetista.models import PlantaBaixa

logger = logging.getLogger(__name__)

class CrewAIPlantaService:
    """
    Serviço para geração de plantas baixas usando CrewAI
    FASE 1: Implementação básica para teste
    """
    
    def __init__(self):
        self.crew_nome = "Arquiteto de Plantas"
        self.crew = None
        self._inicializar_crew()
    
    def _inicializar_crew(self):
        """Inicializa o crew para geração de plantas baixas"""
        try:
            # Buscar crew específico para plantas baixas
            self.crew = Crew.objects.filter(
                nome__icontains="planta",
                ativo=True
            ).first()
            
            if not self.crew:
                logger.warning("⚠️ Crew para plantas baixas não encontrado")
                return
            
            logger.info(f"✅ Crew '{self.crew.nome}' carregado com sucesso")
            
        except Exception as e:
            logger.error(f"❌ Erro ao inicializar crew: {str(e)}")
            self.crew = None
    
    def crew_disponivel(self) -> bool:
        """Verifica se o crew está disponível e configurado"""
        if not self.crew:
            return False
        
        # Verificar se tem membros ativos
        membros_ativos = self.crew.membros.filter(ativo=True).count()
        if membros_ativos == 0:
            logger.warning(f"Crew '{self.crew.nome}' não tem membros ativos")
            return False
        
        # Verificar se tem tasks ativas
        tasks_ativas = self.crew.tasks.filter(ativo=True).count()
        if tasks_ativas == 0:
            logger.warning(f"Crew '{self.crew.nome}' não tem tarefas ativas")
            return False
        
        return True
    
    def validar_crew(self) -> Dict:
        """Valida a configuração do crew (FASE 1: validação simples)"""
        try:
            if not self.crew:
                return {
                    'valido': False,
                    'erro': 'Crew não encontrado',
                    'detalhes': 'Nenhum crew para geração de plantas baixas foi encontrado'
                }
            
            # Contar membros e tasks
            membros = self.crew.membros.filter(ativo=True)
            tasks = self.crew.tasks.filter(ativo=True)
            
            # Validações básicas
            problemas = []
            avisos = []
            
            if membros.count() == 0:
                problemas.append("Nenhum membro ativo no crew")
            
            if tasks.count() == 0:
                problemas.append("Nenhuma tarefa ativa no crew")
            
            # Verificar se agentes dos membros estão ativos
            for membro in membros:
                if not membro.agente.ativo:
                    avisos.append(f"Agente '{membro.agente.nome}' está inativo")
                
                if not membro.agente.llm_model:
                    problemas.append(f"Agente '{membro.agente.nome}' sem modelo LLM")
            
            return {
                'valido': len(problemas) == 0,
                'crew': {
                    'nome': self.crew.nome,
                    'processo': self.crew.processo,
                    'membros_ativos': membros.count(),
                    'tasks_ativas': tasks.count()
                },
                'problemas': problemas,
                'avisos': avisos,
                'detalhes': f"Crew '{self.crew.nome}' com {membros.count()} membros e {tasks.count()} tarefas"
            }
            
        except Exception as e:
            logger.error(f"Erro na validação do crew: {str(e)}")
            return {
                'valido': False,
                'erro': f'Erro técnico na validação: {str(e)}',
                'detalhes': str(e)
            }
    
    def gerar_planta_crew_basico(self, briefing: Briefing, versao: int = 1) -> Dict:
        """
        FASE 1: Geração básica usando crew (sem executar ainda)
        Apenas valida e prepara os dados
        """
        try:
            logger.info(f"🚀 FASE 1: Preparando geração com crew para projeto {briefing.projeto.nome}")
            
            # 1. Validar crew
            validacao = self.validar_crew()
            if not validacao['valido']:
                return {
                    'success': False,
                    'fase': 1,
                    'error': f"Crew inválido: {validacao['erro']}",
                    'detalhes_crew': validacao,
                    'pode_prosseguir': False
                }
            
            # 2. Preparar dados do briefing (simplificado para Fase 1)
            dados_briefing = self._extrair_dados_briefing_basico(briefing)
            
            # 3. FASE 1: Simular execução (retornar dados mock)
            resultado_simulado = self._simular_execucao_crew(dados_briefing, versao)
            
            logger.info(f"✅ FASE 1: Simulação concluída para v{versao}")
            
            return {
                'success': True,
                'fase': 1,
                'simulacao': True,
                'crew_usado': validacao['crew'],
                'dados_briefing': dados_briefing,
                'resultado_simulado': resultado_simulado,
                'message': f'FASE 1: Crew validado e dados preparados para v{versao}',
                'proxima_fase': 'Implementar execução real do CrewAI'
            }
            
        except Exception as e:
            logger.error(f"❌ Erro na FASE 1: {str(e)}", exc_info=True)
            return {
                'success': False,
                'fase': 1,
                'error': f'Erro técnico na FASE 1: {str(e)}',
                'pode_prosseguir': False
            }
    
    def _extrair_dados_briefing_basico(self, briefing: Briefing) -> Dict:
        """Extrai dados básicos do briefing para o crew (FASE 1)"""
        try:
            # Dados essenciais
            area_total = briefing.area_estande or 0
            medida_frente = briefing.medida_frente or 0
            medida_fundo = briefing.medida_fundo or 0
            
            # Calcular área se não informada
            if not area_total and medida_frente and medida_fundo:
                area_total = float(medida_frente) * float(medida_fundo)
            
            dados = {
                'projeto': {
                    'numero': briefing.projeto.numero,
                    'nome': briefing.projeto.nome,
                    'empresa': briefing.projeto.empresa.nome
                },
                'estande': {
                    'area_total': area_total,
                    'medida_frente': medida_frente,
                    'medida_fundo': medida_fundo,
                    'tipo_stand': getattr(briefing, 'tipo_stand', 'ilha') or 'ilha'
                },
                'objetivos': {
                    'objetivo_evento': briefing.objetivo_evento or '',
                    'objetivo_estande': briefing.objetivo_estande or '',
                    'estilo_estande': briefing.estilo_estande or ''
                },
                'metadata': {
                    'briefing_id': briefing.id,
                    'briefing_versao': briefing.versao,
                    'preparado_em': timezone.now().isoformat()
                }
            }
            
            # Contar áreas solicitadas (simplificado)
            try:
                if hasattr(briefing, 'areas_exposicao'):
                    dados['areas_solicitadas'] = {
                        'exposicao': briefing.areas_exposicao.count(),
                        'reuniao': briefing.salas_reuniao.count() if hasattr(briefing, 'salas_reuniao') else 0,
                        'copa': briefing.copas.count() if hasattr(briefing, 'copas') else 0,
                        'deposito': briefing.depositos.count() if hasattr(briefing, 'depositos') else 0
                    }
            except Exception:
                dados['areas_solicitadas'] = {'exposicao': 0, 'reuniao': 0, 'copa': 0, 'deposito': 0}
            
            logger.info(f"📋 Dados extraídos: {area_total:.1f}m², {dados['areas_solicitadas']}")
            return dados
            
        except Exception as e:
            logger.error(f"Erro ao extrair dados do briefing: {str(e)}")
            return {'erro': str(e)}
    
    def _simular_execucao_crew(self, dados_briefing: Dict, versao: int) -> Dict:
        """FASE 1: Simula execução do crew com dados mock"""
        try:
            # Dados simulados para teste
            resultado_mock = {
                'crew_executado': True,
                'versao_gerada': versao,
                'tipo_estande': dados_briefing.get('estande', {}).get('tipo_stand', 'ilha'),
                'area_total_usada': dados_briefing.get('estande', {}).get('area_total', 0) * 0.85,  # 85% da área
                'ambientes_criados': [
                    f"Área de Exposição Principal: {dados_briefing.get('estande', {}).get('area_total', 0) * 0.6:.1f}m²",
                    f"Núcleo Central: {dados_briefing.get('estande', {}).get('area_total', 0) * 0.25:.1f}m²"
                ],
                'lados_abertos': ['frente', 'direita'] if dados_briefing.get('estande', {}).get('tipo_stand') == 'esquina' else ['frente'],
                'resumo_decisoes': f"SIMULAÇÃO FASE 1: Layout {dados_briefing.get('estande', {}).get('tipo_stand')} para {dados_briefing.get('projeto', {}).get('empresa')}",
                'svg_gerado': False,  # FASE 1: não gera SVG ainda
                'executado_em': timezone.now().isoformat(),
                'crew_info': {
                    'nome': self.crew.nome if self.crew else 'Simulado',
                    'processo': self.crew.processo if self.crew else 'sequential',
                    'membros_executados': self.crew.membros.filter(ativo=True).count() if self.crew else 1
                }
            }
            
            return resultado_mock
            
        except Exception as e:
            logger.error(f"Erro na simulação: {str(e)}")
            return {'erro_simulacao': str(e)}
    
    def listar_crews_disponiveis(self) -> List[Dict]:
        """Lista todos os crews disponíveis para plantas baixas"""
        try:
            crews = Crew.objects.filter(ativo=True).annotate(
                num_membros=models.Count('membros', filter=models.Q(membros__ativo=True)),
                num_tasks=models.Count('tasks', filter=models.Q(tasks__ativo=True))
            )
            
            crews_info = []
            for crew in crews:
                crews_info.append({
                    'id': crew.id,
                    'nome': crew.nome,
                    'descricao': crew.descricao,
                    'processo': crew.processo,
                    'membros_ativos': crew.num_membros,
                    'tasks_ativas': crew.num_tasks,
                    'adequado_para_plantas': 'planta' in crew.nome.lower() or 'arquitet' in crew.nome.lower()
                })
            
            return crews_info
            
        except Exception as e:
            logger.error(f"Erro ao listar crews: {str(e)}")
            return []
    
    def debug_crew_info(self) -> Dict:
        """Retorna informações detalhadas do crew para debug"""
        if not self.crew:
            return {'erro': 'Crew não carregado'}
        
        try:
            membros = []
            for membro in self.crew.membros.filter(ativo=True).order_by('ordem_execucao'):
                membros.append({
                    'ordem': membro.ordem_execucao,
                    'agente_nome': membro.agente.nome,
                    'agente_ativo': membro.agente.ativo,
                    'agente_modelo': membro.agente.llm_model,
                    'pode_delegar': membro.pode_delegar,
                    'max_iter': membro.max_iter
                })
            
            tasks = []
            for task in self.crew.tasks.filter(ativo=True).order_by('ordem_execucao'):
                tasks.append({
                    'ordem': task.ordem_execucao,
                    'nome': task.nome,
                    'agente_responsavel': task.agente_responsavel.nome if task.agente_responsavel else 'Não definido',
                    'async_execution': task.async_execution,
                    'dependencias': task.dependencias.count()
                })
            
            return {
                'crew': {
                    'nome': self.crew.nome,
                    'processo': self.crew.processo,
                    'verbose': self.crew.verbose,
                    'memory': self.crew.memory,
                    'ativo': self.crew.ativo
                },
                'membros': membros,
                'tasks': tasks,
                'estatisticas': {
                    'total_membros': len(membros),
                    'total_tasks': len(tasks),
                    'execucoes_anteriores': self.crew.execucoes.count()
                }
            }
            
        except Exception as e:
            return {'erro': f'Erro no debug: {str(e)}'}

# PRÓXIMAS FASES:
# FASE 2: Implementar execução real do CrewAI
# FASE 3: Integrar geração de SVG
# FASE 4: Adicionar refinamento e feedback
# FASE 5: Otimizar performance e adicionar cache