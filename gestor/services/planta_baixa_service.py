# gestor/services/planta_baixa_service.py
"""
Serviço para geração de planta baixa em 4 etapas usando agentes individuais.

Fluxo:
1. Analisador de Esboços (Agente 10) → Interpreta esboço manual
2. Estruturador (Agente 16) → Cria coordenadas precisas
3. Validador (Agente 17) → Valida contra regras
4. Renderizador SVG (Agente 9) → Gera visualização
"""

import logging
import json
from typing import Dict, Any, Optional, List
from datetime import datetime

from django.utils import timezone
from core.models import Agente
from projetos.models import Projeto

logger = logging.getLogger(__name__)


def _run_agent(nome_agente: str, payload: Dict[str, Any], imagens: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Executa um agente individual.

    Args:
        nome_agente: Nome do agente a executar
        payload: Dados a enviar para o agente
        imagens: URLs de imagens (opcional)

    Returns:
        Dict com resultado do agente ou erro
    """
    try:
        # Importar função de execução de agentes
        from gestor.views.agents_crews import run_agent as RUN_AGENT_EXECUTOR

        resultado = RUN_AGENT_EXECUTOR(nome_agente, payload, imagens)

        if not resultado or "erro" in resultado:
            return {
                "sucesso": False,
                "erro": resultado.get("erro", "Agente não retornou resultado válido")
            }

        return {"sucesso": True, "dados": resultado}

    except Exception as e:
        logger.error(f"Erro ao executar agente {nome_agente}: {str(e)}")
        return {
            "sucesso": False,
            "erro": f"Erro ao executar agente: {str(e)}"
        }


class PlantaBaixaService:
    """
    Serviço para geração de planta baixa em 4 etapas.
    """

    # IDs dos agentes
    AGENTE_ANALISADOR_ID = 10
    AGENTE_ESTRUTURADOR_ID = 16
    AGENTE_VALIDADOR_ID = 17
    AGENTE_RENDERIZADOR_ID = 9

    def __init__(self, projeto: Projeto):
        """
        Inicializa o serviço para um projeto.

        Args:
            projeto: Instância do modelo Projeto
        """
        self.projeto = projeto
        self.briefing = projeto.briefings.first()

        if not self.briefing:
            raise ValueError("Projeto não possui briefing")

    def etapa1_analisar_esboco(self) -> Dict[str, Any]:
        """
        Etapa 1: Analisa o esboço da planta baixa.

        Returns:
            Dict com layout identificado ou erro
        """
        logger.info(f"[Planta Baixa] Etapa 1 - Projeto {self.projeto.id}")

        # Verificar se tem esboço
        esbocos = self.briefing.arquivos.filter(tipo="planta")
        if not esbocos.exists():
            return {
                "sucesso": False,
                "erro": "Nenhum esboço de planta encontrado no briefing"
            }

        esboco = esbocos.first()

        # Usar lateral (priorizar esquerda, depois direita)
        lateral = self.briefing.medida_lateral_esquerda or self.briefing.medida_lateral_direita

        # Preparar payload
        payload = {
            "projeto_id": self.projeto.id,
            "briefing_id": self.briefing.id,
            "briefing": {
                "tipo_stand": self.briefing.tipo_stand,
                "medida_frente_m": float(self.briefing.medida_frente) if self.briefing.medida_frente else None,
                "medida_lateral_m": float(lateral) if lateral else None,
                "altura_m": 3.0,
            }
        }

        # Executar agente
        resultado = _run_agent(
            "Analisador de Esboços de Planta",
            payload,
            imagens=[esboco.arquivo.url]
        )

        if not resultado["sucesso"]:
            return resultado

        # Salvar no projeto
        self.projeto.layout_identificado = resultado["dados"]
        self.projeto.save(update_fields=["layout_identificado"])

        logger.info(f"[Planta Baixa] Etapa 1 concluída - Projeto {self.projeto.id}")

        return {
            "sucesso": True,
            "layout": resultado["dados"],
            "arquivo": {
                "nome": esboco.nome or esboco.arquivo.name,
                "url": esboco.arquivo.url
            },
            "processado_em": timezone.now().isoformat()
        }

    def etapa2_estruturar_planta(self) -> Dict[str, Any]:
        """
        Etapa 2: Estrutura a planta com coordenadas precisas.

        Returns:
            Dict com planta estruturada ou erro
        """
        logger.info(f"[Planta Baixa] Etapa 2 - Projeto {self.projeto.id}")

        # Verificar se etapa 1 foi executada
        if not self.projeto.layout_identificado:
            return {
                "sucesso": False,
                "erro": "Execute a Etapa 1 (análise do esboço) primeiro"
            }

        # Usar lateral (priorizar esquerda, depois direita)
        lateral = self.briefing.medida_lateral_esquerda or self.briefing.medida_lateral_direita

        # Preparar payload com análise da etapa 1
        payload = {
            "projeto_id": self.projeto.id,
            "layout_analise": self.projeto.layout_identificado,
            "briefing_completo": {
                "tipo_stand": self.briefing.tipo_stand,
                "medida_frente": float(self.briefing.medida_frente) if self.briefing.medida_frente else 6.0,
                "medida_lateral": float(lateral) if lateral else 8.0,
                "area_total": float(self.briefing.area_estande) if self.briefing.area_estande else 48.0,
                "altura": 3.0,
            },
            "regras_feira": self.projeto.feira.regras_planta_baixa if self.projeto.feira else {}
        }

        # Executar agente
        resultado = _run_agent(
            "Estruturador de Planta Baixa",
            payload
        )

        if not resultado["sucesso"]:
            return resultado

        # Salvar no projeto (ainda não marca como processada, só depois da etapa 4)
        self.projeto.planta_baixa_json = resultado["dados"]
        self.projeto.save(update_fields=["planta_baixa_json"])

        logger.info(f"[Planta Baixa] Etapa 2 concluída - Projeto {self.projeto.id}")

        return {
            "sucesso": True,
            "planta_estruturada": resultado["dados"],
            "processado_em": timezone.now().isoformat()
        }

    def etapa3_validar_conformidade(self) -> Dict[str, Any]:
        """
        Etapa 3: Valida a planta contra regras e normas.

        Returns:
            Dict com resultado da validação ou erro
        """
        logger.info(f"[Planta Baixa] Etapa 3 - Projeto {self.projeto.id}")

        # Verificar se etapa 2 foi executada
        if not self.projeto.planta_baixa_json:
            return {
                "sucesso": False,
                "erro": "Execute a Etapa 2 (estruturação) primeiro"
            }

        # Preparar payload
        payload = {
            "projeto_id": self.projeto.id,
            "planta_estruturada": self.projeto.planta_baixa_json,
            "regras_feira": self.projeto.feira.regras_planta_baixa if self.projeto.feira else {},
            "tipo_projeto": self.projeto.tipo_projeto
        }

        # Executar agente
        resultado = _run_agent(
            "Validador de Conformidade de Planta",
            payload
        )

        if not resultado["sucesso"]:
            return resultado

        logger.info(f"[Planta Baixa] Etapa 3 concluída - Projeto {self.projeto.id}")

        return {
            "sucesso": True,
            "validacao": resultado["dados"],
            "processado_em": timezone.now().isoformat()
        }

    def etapa4_gerar_svg(self, validacao: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Etapa 4: Gera representação SVG da planta.

        Args:
            validacao: Resultado da etapa 3 (opcional)

        Returns:
            Dict com SVG gerado ou erro
        """
        logger.info(f"[Planta Baixa] Etapa 4 - Projeto {self.projeto.id}")

        # Verificar se etapa 2 foi executada
        if not self.projeto.planta_baixa_json:
            return {
                "sucesso": False,
                "erro": "Execute a Etapa 2 (estruturação) primeiro"
            }

        # Preparar payload
        payload = {
            "projeto_id": self.projeto.id,
            "nome_projeto": self.projeto.nome,
            "planta_estruturada": self.projeto.planta_baixa_json,
            "validacao": validacao or {}
        }

        # Executar agente
        resultado = _run_agent(
            "Renderizador SVG Profissional",
            payload
        )

        if not resultado["sucesso"]:
            return resultado

        # Salvar SVG e marcar como processada
        svg_content = resultado["dados"]

        # Extrair SVG do resultado (pode vir em diferentes formatos)
        svg_content = self._extrair_svg(svg_content)

        if not svg_content or not svg_content.strip().startswith('<'):
            return {
                "sucesso": False,
                "erro": "Agente não retornou SVG válido. Resposta recebida: " + str(svg_content)[:200]
            }

        self.projeto.planta_baixa_svg = svg_content
        self.projeto.planta_baixa_processada = True
        self.projeto.data_planta_baixa = timezone.now()
        self.projeto.save(update_fields=[
            "planta_baixa_svg",
            "planta_baixa_processada",
            "data_planta_baixa"
        ])

        logger.info(f"[Planta Baixa] Etapa 4 concluída - Projeto {self.projeto.id}")

        return {
            "sucesso": True,
            "svg": svg_content,
            "processado_em": timezone.now().isoformat()
        }

    def _extrair_svg(self, dados: Any) -> str:
        """
        Extrai código SVG de diferentes formatos de resposta.

        Args:
            dados: Pode ser string, dict ou outro formato

        Returns:
            String com código SVG puro
        """
        import re

        # Se já é string, processar diretamente
        if isinstance(dados, str):
            svg = dados

        # Se é dict, tentar extrair de campos conhecidos
        elif isinstance(dados, dict):
            # Tentar campos comuns
            svg = (dados.get("svg") or
                   dados.get("codigo_svg") or
                   dados.get("resultado") or
                   dados.get("output") or
                   dados.get("content") or
                   str(dados))
        else:
            svg = str(dados)

        # Remover markdown code blocks se houver
        # ```svg ... ``` ou ```xml ... ```
        svg = re.sub(r'^```(?:svg|xml)?\s*\n', '', svg, flags=re.MULTILINE)
        svg = re.sub(r'\n```\s*$', '', svg, flags=re.MULTILINE)

        # Remover espaços em branco no início e fim
        svg = svg.strip()

        # Se não começa com < mas tem <svg em algum lugar, tentar extrair
        if not svg.startswith('<') and '<svg' in svg:
            match = re.search(r'(<svg[\s\S]*?</svg>)', svg, re.IGNORECASE)
            if match:
                svg = match.group(1)

        return svg

    def executar_todas_etapas(self) -> Dict[str, Any]:
        """
        Executa todas as 4 etapas sequencialmente.

        Returns:
            Dict com resultado completo ou erro
        """
        logger.info(f"[Planta Baixa] Executando todas as etapas - Projeto {self.projeto.id}")

        resultados = {
            "projeto_id": self.projeto.id,
            "inicio": timezone.now().isoformat(),
            "etapas": {}
        }

        # Etapa 1
        resultado1 = self.etapa1_analisar_esboco()
        resultados["etapas"]["etapa1"] = resultado1
        if not resultado1["sucesso"]:
            resultados["sucesso"] = False
            resultados["erro_etapa"] = 1
            return resultados

        # Etapa 2
        resultado2 = self.etapa2_estruturar_planta()
        resultados["etapas"]["etapa2"] = resultado2
        if not resultado2["sucesso"]:
            resultados["sucesso"] = False
            resultados["erro_etapa"] = 2
            return resultados

        # Etapa 3
        resultado3 = self.etapa3_validar_conformidade()
        resultados["etapas"]["etapa3"] = resultado3
        if not resultado3["sucesso"]:
            resultados["sucesso"] = False
            resultados["erro_etapa"] = 3
            return resultados

        # Etapa 4
        resultado4 = self.etapa4_gerar_svg(validacao=resultado3.get("validacao"))
        resultados["etapas"]["etapa4"] = resultado4
        if not resultado4["sucesso"]:
            resultados["sucesso"] = False
            resultados["erro_etapa"] = 4
            return resultados

        resultados["sucesso"] = True
        resultados["fim"] = timezone.now().isoformat()

        logger.info(f"[Planta Baixa] Todas as etapas concluídas - Projeto {self.projeto.id}")

        return resultados
