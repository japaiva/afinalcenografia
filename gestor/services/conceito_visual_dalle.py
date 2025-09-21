# gestor/services/conceito_visual_dalle.py

import openai
import requests
import base64
from typing import Dict, Any, Optional
from django.conf import settings
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

class ConceitoVisualDalleService:
    """
    Serviço dedicado para geração de conceitos visuais usando DALL-E
    Integra dados do layout, inspirações e briefing
    """
    
    def __init__(self):
        openai.api_key = settings.OPENAI_API_KEY
        
    def gerar_conceito_visual(
        self, 
        briefing, 
        layout: Dict[str, Any], 
        inspiracoes: Dict[str, Any],
        prompt_customizado: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Gera conceito visual integrando todas as informações
        
        Args:
            briefing: Objeto Briefing com dados do projeto
            layout: JSON do layout identificado (Etapa 1)
            inspiracoes: JSON das inspirações visuais (Etapa 2)
            prompt_customizado: Prompt fornecido pelo usuário (opcional)
            
        Returns:
            Dict com sucesso, url da imagem, prompt usado, etc.
        """
        try:
            # Se tem prompt customizado, usar direto
            if prompt_customizado:
                prompt_final = prompt_customizado
            else:
                # Construir prompt integrando todas as informações
                prompt_final = self._construir_prompt_integrado(briefing, layout, inspiracoes)
            
            # Gerar imagem com DALL-E
            logger.info(f"Gerando conceito visual para projeto {briefing.projeto.id}")
            
            response = openai.images.generate(
                model="dall-e-3",
                prompt=prompt_final[:4000],  # DALL-E tem limite de 4000 chars
                size="1792x1024",  # Landscape HD
                quality="hd",
                n=1
            )
            
            image_url = response.data[0].url
            
            # Baixar a imagem para salvar localmente
            image_data = self._baixar_imagem(image_url)
            
            # Preparar resposta
            return {
                "sucesso": True,
                "image_url": image_url,
                "image_data": image_data,
                "prompt_usado": prompt_final,
                "modelo": "dall-e-3",
                "timestamp": timezone.now().isoformat(),
                "metricas": {
                    "tamanho_prompt": len(prompt_final),
                    "resolucao": "1792x1024",
                    "qualidade": "hd"
                }
            }
            
        except openai.error.InvalidRequestError as e:
            logger.error(f"Erro de requisição DALL-E: {str(e)}")
            return {
                "sucesso": False,
                "erro": f"Erro na requisição: {str(e)}",
                "tipo_erro": "invalid_request"
            }
            
        except openai.error.RateLimitError as e:
            logger.error(f"Rate limit DALL-E: {str(e)}")
            return {
                "sucesso": False,
                "erro": "Limite de requisições excedido. Tente novamente em alguns minutos.",
                "tipo_erro": "rate_limit"
            }
            
        except Exception as e:
            logger.error(f"Erro ao gerar conceito visual: {str(e)}", exc_info=True)
            return {
                "sucesso": False,
                "erro": f"Erro inesperado: {str(e)}",
                "tipo_erro": "unknown"
            }
    
    def _construir_prompt_integrado(
        self, 
        briefing, 
        layout: Dict[str, Any], 
        inspiracoes: Dict[str, Any]
    ) -> str:
        """
        Constrói prompt integrando dados do briefing, layout e inspirações
        """
        # Dados do briefing
        empresa = briefing.projeto.empresa.nome
        descricao_empresa = briefing.projeto.empresa.descricao or ""
        tipo_stand = briefing.get_tipo_stand_display() or "personalizado"
        
        # Dimensões
        largura = float(briefing.medida_frente) if briefing.medida_frente else 6.0
        profundidade = float(briefing.medida_fundo) if briefing.medida_fundo else 8.0
        altura = 3.0  # Padrão para feiras
        area_total = briefing.area_estande or (largura * profundidade)
        
        # Estilo e materiais
        estilo_estande = briefing.estilo_estande or "moderno e profissional"
        material = briefing.get_material_display() if briefing.material else "misto"
        piso_elevado = briefing.get_piso_elevado_display() if briefing.piso_elevado else "sem elevação"
        
        # Objetivo e funcionalidades
        objetivo = briefing.objetivo_estande or briefing.objetivo_evento or "exposição de produtos e atendimento"
        tipo_venda = briefing.get_tipo_venda_display() if briefing.tipo_venda else "não haverá venda"
        ativacao = briefing.tipo_ativacao or ""
        
        # Processar áreas do layout (Etapa 1)
        areas_texto = self._processar_areas_layout(layout)
        
        # Processar inspirações visuais (Etapa 2)
        cores = self._processar_cores(inspiracoes)
        estilo_visual = self._processar_estilo(inspiracoes)
        materiais_ref = self._processar_materiais(inspiracoes)
        elementos_destaque = self._processar_elementos(inspiracoes)
        
        # Montar prompt estruturado
        prompt = f"""Crie uma imagem fotorrealística em alta resolução de um estande de feira de negócios profissional.

EMPRESA: {empresa}
{f'DESCRIÇÃO: {descricao_empresa[:200]}' if descricao_empresa else ''}

ESPECIFICAÇÕES TÉCNICAS:
- Dimensões: {largura}m (frente) x {profundidade}m (fundo) x {altura}m (altura)
- Área total: {area_total}m²
- Tipo: {tipo_stand}
- Material: {material}
- Piso: {piso_elevado}

LAYOUT E ÁREAS:
{areas_texto}

OBJETIVO E FUNCIONALIDADES:
- Objetivo principal: {objetivo}
- Vendas: {tipo_venda}
{f'- Ativação: {ativacao}' if ativacao else ''}

IDENTIDADE VISUAL:
- Estilo arquitetônico: {estilo_estande}
- Estilo visual: {estilo_visual}
- Paleta de cores: {cores}
- Materiais principais: {materiais_ref}

ELEMENTOS IMPORTANTES:
{elementos_destaque}
- Logo da empresa em destaque na testeira
- Iluminação profissional de feira

REQUISITOS DA IMAGEM:
- Vista em perspectiva 3/4 mostrando fachada principal e lateral
- Pessoas interagindo naturalmente com o espaço
- Ambiente de feira comercial movimentado
- Iluminação realista com spots e luz ambiente
- Acabamento fotorrealístico e moderno
- Qualidade de renderização arquitetônica profissional

Criar uma imagem que demonstre profissionalismo, funcionalidade e seja visualmente atrativa para visitantes de feira."""

        return prompt.strip()
    
    def _processar_areas_layout(self, layout: Dict[str, Any]) -> str:
        """Processa as áreas identificadas no layout"""
        if not layout or "areas" not in layout:
            return "- Espaço único integrado para exposição e atendimento"
        
        areas = layout.get("areas", [])
        if isinstance(areas, list):
            # Se é lista de objetos
            texto_areas = []
            for area in areas:
                if isinstance(area, dict):
                    nome = area.get("id", area.get("nome", "área"))
                    m2 = area.get("m2_estimado", 0)
                    if m2 > 0:
                        texto_areas.append(f"- {nome}: {m2:.1f}m²")
                    else:
                        texto_areas.append(f"- {nome}")
            return "\n".join(texto_areas) if texto_areas else "- Layout aberto integrado"
        
        elif isinstance(areas, dict):
            # Se é dicionário
            texto_areas = []
            for nome, dados in areas.items():
                if isinstance(dados, dict):
                    m2 = dados.get("m2", dados.get("area", 0))
                    if m2 > 0:
                        texto_areas.append(f"- {nome}: {m2:.1f}m²")
                    else:
                        texto_areas.append(f"- {nome}")
            return "\n".join(texto_areas) if texto_areas else "- Layout aberto integrado"
        
        return "- Espaço único integrado"
    
    def _processar_cores(self, inspiracoes: Dict[str, Any]) -> str:
        """Processa paleta de cores das inspirações"""
        cores_predominantes = inspiracoes.get("cores_predominantes", [])
        if cores_predominantes and isinstance(cores_predominantes, list):
            cores_hex = []
            for cor in cores_predominantes[:5]:  # Máximo 5 cores
                if isinstance(cor, dict) and "hex" in cor:
                    hex_value = cor["hex"]
                    uso = cor.get("uso", "")
                    if uso:
                        cores_hex.append(f"{hex_value} ({uso})")
                    else:
                        cores_hex.append(hex_value)
            
            if cores_hex:
                return ", ".join(cores_hex)
        
        return "tons neutros profissionais com detalhes em cores corporativas"
    
    def _processar_estilo(self, inspiracoes: Dict[str, Any]) -> str:
        """Processa estilo identificado nas referências"""
        estilo = inspiracoes.get("estilo_identificado", {})
        if isinstance(estilo, dict):
            principal = estilo.get("principal", "moderno").replace("_", " ")
            secundario = estilo.get("secundario", "").replace("_", " ")
            if secundario:
                return f"{principal} com toques de {secundario}"
            return principal
        return "moderno e profissional"
    
    def _processar_materiais(self, inspiracoes: Dict[str, Any]) -> str:
        """Processa materiais sugeridos"""
        materiais = inspiracoes.get("materiais_sugeridos", [])
        if materiais and isinstance(materiais, list):
            lista_materiais = []
            for mat in materiais[:4]:  # Máximo 4 materiais
                if isinstance(mat, dict):
                    material = mat.get("material", "")
                    aplicacao = mat.get("aplicacao", "")
                    if material:
                        if aplicacao:
                            lista_materiais.append(f"{material} ({aplicacao})")
                        else:
                            lista_materiais.append(material)
            
            if lista_materiais:
                return ", ".join(lista_materiais)
        
        return "madeira, vidro e metal com acabamento premium"
    
    def _processar_elementos(self, inspiracoes: Dict[str, Any]) -> str:
        """Processa elementos de destaque"""
        elementos = inspiracoes.get("elementos_destaque", [])
        if elementos and isinstance(elementos, list):
            # Filtrar e formatar elementos
            elementos_formatados = []
            for elem in elementos[:6]:  # Máximo 6 elementos
                if isinstance(elem, str):
                    elementos_formatados.append(f"- {elem}")
            
            if elementos_formatados:
                return "\n".join(elementos_formatados)
        
        return "- Displays iluminados\n- Área de demonstração\n- Pontos de interação"
    
    def _baixar_imagem(self, url: str) -> bytes:
        """Baixa a imagem da URL do DALL-E"""
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            return response.content
        except Exception as e:
            logger.error(f"Erro ao baixar imagem: {str(e)}")
            return b""
    
    def validar_prompt(self, prompt: str) -> Dict[str, Any]:
        """
        Valida se o prompt está adequado para DALL-E
        """
        problemas = []
        avisos = []
        
        # Verificar tamanho
        if len(prompt) > 4000:
            problemas.append(f"Prompt muito longo ({len(prompt)} chars). Máximo: 4000")
        elif len(prompt) > 3500:
            avisos.append(f"Prompt próximo do limite ({len(prompt)}/4000 chars)")
        
        # Verificar conteúdo proibido (política DALL-E)
        palavras_proibidas = ["violência", "sangue", "político", "celebridade"]
        for palavra in palavras_proibidas:
            if palavra.lower() in prompt.lower():
                problemas.append(f"Conteúdo potencialmente proibido: '{palavra}'")
        
        # Verificar complexidade
        if prompt.count("\n") > 50:
            avisos.append("Prompt muito complexo, considere simplificar")
        
        return {
            "valido": len(problemas) == 0,
            "problemas": problemas,
            "avisos": avisos,
            "tamanho": len(prompt)
        }