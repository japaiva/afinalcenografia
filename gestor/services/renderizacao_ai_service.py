"""
Service para Renderização AI (Módulo 2)

Responsável por:
1. Enriquecer JSON (planta_baixa + briefing + inspirações)
2. Gerar prompt DALL-E
3. Gerar imagem DALL-E
4. Interpretar ajustes conversacionais
5. Regenerar conceito
"""

import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from django.utils import timezone

logger = logging.getLogger(__name__)


class RenderizacaoAIService:
    """
    Serviço para geração de conceitos visuais usando IA
    """

    def __init__(self, projeto):
        """
        Args:
            projeto: Instância do modelo Projeto
        """
        self.projeto = projeto
        self.briefing = projeto.briefings.first() if projeto.has_briefing else None

    def etapa1_enriquecer_json(self) -> Dict[str, Any]:
        """
        Etapa 1: Enriquece o JSON da planta baixa com dados do briefing e inspirações

        Returns:
            Dict com JSON enriquecido ou erro
        """
        logger.info(f"[Renderização AI] Etapa 1 - Projeto {self.projeto.id}")

        # Verificar se planta baixa foi processada
        if not self.projeto.planta_baixa_json:
            return {
                "sucesso": False,
                "erro": "Planta baixa não foi gerada. Execute o módulo de Planta Baixa primeiro."
            }

        if not self.briefing:
            return {
                "sucesso": False,
                "erro": "Briefing não encontrado para este projeto."
            }

        try:
            # Extrair dados do briefing
            dados_briefing = self._extrair_dados_briefing()

            # Extrair inspirações visuais
            inspiracoes = self._extrair_inspiracoes()

            # Criar JSON enriquecido
            json_enriquecido = {
                "planta": self.projeto.planta_baixa_json,
                "briefing": dados_briefing,
                "estilo": inspiracoes,
                "elementos_visuais": self._criar_elementos_default(),
                "historico_ajustes": [],
                "metadata": {
                    "versao": "1.0",
                    "data_criacao": timezone.now().isoformat(),
                    "ultima_modificacao": timezone.now().isoformat(),
                    "total_regeneracoes": 0
                }
            }

            # Salvar no projeto
            self.projeto.renderizacao_ai_json = json_enriquecido
            self.projeto.save(update_fields=['renderizacao_ai_json'])

            logger.info(f"[Renderização AI] Etapa 1 concluída - Projeto {self.projeto.id}")

            return {
                "sucesso": True,
                "json_enriquecido": json_enriquecido,
                "processado_em": timezone.now().isoformat()
            }

        except Exception as e:
            logger.error(f"[Renderização AI] Erro na Etapa 1 - Projeto {self.projeto.id}: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                "sucesso": False,
                "erro": f"Erro ao enriquecer JSON: {str(e)}"
            }

    def etapa2_gerar_prompt_e_imagem(self) -> Dict[str, Any]:
        """
        Etapa 2: Gera prompt E imagem usando o Agente de Imagem Principal

        O Agente 6 já gera a imagem diretamente usando gpt-image-1

        Returns:
            Dict com prompt + imagem ou erro
        """
        logger.info(f"[Renderização AI] Etapa 2 - Projeto {self.projeto.id}")

        if not self.projeto.renderizacao_ai_json:
            return {
                "sucesso": False,
                "erro": "Execute a Etapa 1 (enriquecimento) primeiro"
            }

        try:
            from gestor.services.agente_executor import AgenteService
            from core.models import Agente

            # Buscar agente de geração de imagem
            agente = Agente.objects.get(nome="Agente de Imagem Principal")

            # Preparar payload com os dados do conceito visual
            conceito = self.projeto.renderizacao_ai_json
            planta = conceito.get('planta', {})
            briefing_data = conceito.get('briefing', {})
            estilo = conceito.get('estilo', {})
            elementos = conceito.get('elementos_visuais', {})

            # Montar prompt estruturado conforme task_instructions do agente
            prompt_estruturado = self._montar_prompt_estruturado(
                planta, briefing_data, estilo, elementos
            )

            # Executar agente
            service = AgenteService()
            imagem_url = service.executar_agente(
                agente=agente,
                prompt_usuario=prompt_estruturado
            )

            # Salvar prompt e imagem
            self.projeto.prompt_dalle_atual = prompt_estruturado
            self.projeto.imagem_conceito_url = imagem_url
            self.projeto.renderizacao_ai_processada = True
            self.projeto.data_renderizacao_ai = timezone.now()

            self.projeto.save(update_fields=[
                'prompt_dalle_atual',
                'imagem_conceito_url',
                'renderizacao_ai_processada',
                'data_renderizacao_ai'
            ])

            # Atualizar metadata
            if self.projeto.renderizacao_ai_json:
                metadata = self.projeto.renderizacao_ai_json.get('metadata', {})
                metadata['imagem_atual'] = imagem_url
                metadata['ultima_modificacao'] = timezone.now().isoformat()
                metadata['total_regeneracoes'] = metadata.get('total_regeneracoes', 0) + 1

                self.projeto.renderizacao_ai_json['metadata'] = metadata
                self.projeto.save(update_fields=['renderizacao_ai_json'])

            logger.info(f"[Renderização AI] Etapa 2 concluída - Projeto {self.projeto.id}")

            return {
                "sucesso": True,
                "prompt": prompt_estruturado,
                "imagem_url": imagem_url,
                "processado_em": timezone.now().isoformat()
            }

        except Agente.DoesNotExist:
            return {
                "sucesso": False,
                "erro": "Agente 'Agente de Imagem Principal' não encontrado."
            }
        except Exception as e:
            logger.error(f"[Renderização AI] Erro na Etapa 2 - Projeto {self.projeto.id}: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                "sucesso": False,
                "erro": f"Erro ao gerar imagem: {str(e)}"
            }

    # ========================================
    # MÉTODOS AUXILIARES
    # ========================================

    def _montar_prompt_estruturado(self, planta, briefing_data, estilo, elementos) -> str:
        """
        Monta prompt estruturado seguindo o template do Agente de Imagem Principal
        """
        # Extrair dados da planta
        dimensoes = planta.get('dimensoes_totais', {})
        largura = dimensoes.get('largura', 0)
        profundidade = dimensoes.get('profundidade', 0)
        altura = dimensoes.get('altura', 3.0)
        area_total = dimensoes.get('area_total', 0)
        tipo_stand = planta.get('tipo_stand', 'ilha')

        # Mapear tipo de stand para português
        tipos_stand_map = {
            'ilha': 'Ilha (4 lados abertos)',
            'esquina': 'Esquina (2 lados abertos)',
            'corredor': 'Corredor (1 lado aberto)',
            'ponta_ilha': 'Ponta de Ilha (3 lados abertos)'
        }

        # Montar lista de áreas
        areas = planta.get('areas', [])
        layout_areas = []
        for area in areas:
            nome = area.get('id', '')
            geometria = area.get('geometria', {})
            m2 = geometria.get('area', 0)
            layout_areas.append(f"- {nome.title()}: {m2}m²")

        # Montar paleta de cores
        cores = estilo.get('paleta_cores', {})
        cores_texto = []
        if cores.get('primaria'):
            cores_texto.append(f"Primária: {cores['primaria']}")
        if cores.get('secundaria'):
            cores_texto.append(f"Secundária: {cores['secundaria']}")
        if cores.get('acento'):
            cores_texto.append(f"Acento: {cores['acento']}")

        # Montar materiais
        materiais = estilo.get('materiais', [])
        materiais_texto = ", ".join(materiais) if materiais else "A definir"

        # Montar elementos visuais
        iluminacao = elementos.get('iluminacao', {})
        mobiliario = elementos.get('mobiliario', {})
        vegetacao = elementos.get('vegetacao', {})

        # Criar prompt estruturado
        prompt = f"""Renderização fotorrealística de estande para feira comercial.

IDENTIFICAÇÃO DO PROJETO:
{briefing_data.get('objetivo_principal', 'Stand comercial')}
Público-alvo: {briefing_data.get('publico_alvo', 'Geral')}

ESPECIFICAÇÕES TÉCNICAS:
Dimensões: {largura}m (frente) × {profundidade}m (fundo) × {altura}m (altura)
Tipo: {tipos_stand_map.get(tipo_stand, tipo_stand.title())}
Área total: {area_total}m²

LAYOUT ESPACIAL:
{chr(10).join(layout_areas) if layout_areas else '- Layout em desenvolvimento'}

DESIGN VISUAL:
Estilo arquitetônico: {estilo.get('referencias_visuais', [{}])[0].get('nota', 'Moderno e profissional') if estilo.get('referencias_visuais') else 'Moderno e profissional'}
Conceito: {briefing_data.get('mensagem_chave', 'Inovação e qualidade')}

Paleta de cores:
{chr(10).join(cores_texto) if cores_texto else 'Paleta corporativa neutra'}

Materiais e acabamentos:
{materiais_texto}

SISTEMAS TÉCNICOS:
Iluminação: {iluminacao.get('tipo', 'LED moderno com spots direcionados')}
Temperatura de luz: {iluminacao.get('ambiente', 'Luz branca neutra (4000K)')}

MOBILIÁRIO:
Estilo: {mobiliario.get('estilo', 'Moderno e funcional')}
Balcões: {mobiliario.get('balcoes', 'Clean com acabamento premium')}

ELEMENTOS DE DESTAQUE:
{vegetacao.get('tipo', 'Sem vegetação') if vegetacao.get('tipo') else 'Layout clean sem elementos verdes'}

REQUISITOS DA IMAGEM:
- Perspectiva 3/4 mostrando frente principal e lateral direita
- Respeitar fielmente o posicionamento das áreas conforme layout
- Incluir pessoas diversas interagindo naturalmente (visitantes e expositores)
- Iluminação profissional de centro de convenções
- Ambiente de feira comercial movimentado
- Renderização fotorrealística em alta resolução
- Acabamento premium e contemporâneo
- Horário: período diurno com boa iluminação
- Incluir contexto do pavilhão (outros estandes ao fundo)
"""
        return prompt

    def _extrair_dados_briefing(self) -> Dict[str, Any]:
        """Extrai dados relevantes do briefing"""
        return {
            "objetivo_principal": getattr(self.briefing, 'objetivo_stand', '') or '',
            "publico_alvo": getattr(self.briefing, 'publico_alvo', '') or '',
            "mensagem_chave": getattr(self.briefing, 'mensagem_principal', '') or '',
            "produtos_destaque": getattr(self.briefing, 'produtos_servicos', '') or '',
            "atividades": getattr(self.briefing, 'atividades_stand', '') or ''
        }

    def _extrair_inspiracoes(self) -> Dict[str, Any]:
        """Extrai inspirações visuais do briefing"""
        # TODO: Implementar extração de referências visuais
        # Por enquanto, retorna estrutura básica
        return {
            "paleta_cores": {
                "primaria": None,
                "secundaria": None,
                "acento": None
            },
            "materiais": [],
            "referencias_visuais": []
        }

    def _criar_elementos_default(self) -> Dict[str, Any]:
        """Cria estrutura padrão de elementos visuais"""
        return {
            "iluminacao": {
                "tipo": None,
                "destaques": None,
                "ambiente": None
            },
            "mobiliario": {
                "estilo": None,
                "balcoes": None,
                "cadeiras": None
            },
            "graficos": {
                "tipo": None,
                "localizacao": None,
                "conteudo": None
            },
            "vegetacao": {
                "tipo": None,
                "especies": None,
                "quantidade": None
            },
            "pisos": {
                "material": None,
                "cor": None
            },
            "paredes": {
                "acabamento": None,
                "detalhe": None
            }
        }

    def _resumir_briefing(self) -> str:
        """Cria resumo textual do briefing"""
        if not self.briefing:
            return ""

        partes = []

        if hasattr(self.briefing, 'objetivo_stand') and self.briefing.objetivo_stand:
            partes.append(f"Objetivo: {self.briefing.objetivo_stand}")

        if hasattr(self.briefing, 'publico_alvo') and self.briefing.publico_alvo:
            partes.append(f"Público: {self.briefing.publico_alvo}")

        if hasattr(self.briefing, 'mensagem_principal') and self.briefing.mensagem_principal:
            partes.append(f"Mensagem: {self.briefing.mensagem_principal}")

        return ". ".join(partes)
