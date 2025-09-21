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
            # IMPORTANTE: Usar o prompt customizado quando fornecido
            if prompt_customizado:
                prompt_final = prompt_customizado
                logger.info(f"Usando prompt customizado com {len(prompt_customizado)} caracteres")
            else:
                # Se não tem prompt customizado, construir um
                prompt_final = self._construir_prompt_integrado(briefing, layout, inspiracoes)
                logger.info(f"Prompt construído automaticamente com {len(prompt_final)} caracteres")
            
            # Log do prompt para debug
            logger.info(f"=== PROMPT ENVIADO PARA DALL-E ===")
            logger.info(f"Primeiros 500 chars: {prompt_final[:500]}")
            logger.info(f"Tamanho total: {len(prompt_final)} caracteres")
            
            # Verificar se o prompt não está vazio ou muito curto
            if len(prompt_final) < 50:
                logger.error(f"Prompt muito curto ou vazio: '{prompt_final}'")
                return {
                    "sucesso": False,
                    "erro": "Prompt inválido - muito curto ou vazio",
                    "tipo_erro": "invalid_prompt"
                }
            
            # Limpar e formatar o prompt - REMOVER CONTEÚDO POTENCIALMENTE PROBLEMÁTICO
            prompt_final = self._sanitizar_prompt(prompt_final)
            
            # Gerar imagem com DALL-E
            logger.info(f"Enviando requisição para DALL-E...")
            
            response = openai.images.generate(
                model="dall-e-3",
                prompt=prompt_final[:4000],  # DALL-E tem limite de 4000 chars
                size="1792x1024",  # Landscape HD
                quality="hd",
                n=1,
                style="natural"  # Estilo natural para evitar imagens muito artísticas
            )
            
            image_url = response.data[0].url
            revised_prompt = getattr(response.data[0], 'revised_prompt', prompt_final)
            
            logger.info(f"Imagem gerada com sucesso: {image_url[:100]}...")
            logger.info(f"Prompt revisado pelo DALL-E: {revised_prompt[:200]}...")
            
            # Baixar a imagem para salvar localmente
            image_data = self._baixar_imagem(image_url)
            
            # Preparar resposta
            return {
                "sucesso": True,
                "image_url": image_url,
                "image_data": image_data,
                "prompt_usado": prompt_final,
                "prompt_revisado": revised_prompt,
                "modelo": "dall-e-3",
                "timestamp": timezone.now().isoformat(),
                "metricas": {
                    "tamanho_prompt": len(prompt_final),
                    "resolucao": "1792x1024",
                    "qualidade": "hd"
                }
            }
            
        except openai.BadRequestError as e:
            # Nova estrutura de exceptions do openai
            error_msg = str(e)
            logger.error(f"Erro BadRequest DALL-E: {error_msg}")
            
            # Verificar se é erro de política de conteúdo
            if "content_policy_violation" in error_msg or "safety system" in error_msg:
                logger.warning("Prompt rejeitado por política de conteúdo. Tentando versão simplificada...")
                
                # Tentar com prompt mais simples e seguro
                prompt_seguro = self._criar_prompt_seguro(briefing)
                try:
                    response = openai.images.generate(
                        model="dall-e-3",
                        prompt=prompt_seguro,
                        size="1792x1024",
                        quality="hd",
                        n=1,
                        style="natural"
                    )
                    
                    image_url = response.data[0].url
                    
                    return {
                        "sucesso": True,
                        "image_url": image_url,
                        "image_data": self._baixar_imagem(image_url),
                        "prompt_usado": prompt_seguro,
                        "modelo": "dall-e-3",
                        "timestamp": timezone.now().isoformat(),
                        "aviso": "Prompt original rejeitado. Usando versão simplificada."
                    }
                    
                except Exception as e2:
                    logger.error(f"Falha também com prompt seguro: {str(e2)}")
                    return {
                        "sucesso": False,
                        "erro": "Não foi possível gerar a imagem. Tente editar o prompt manualmente.",
                        "tipo_erro": "content_policy",
                        "detalhes": str(e2)
                    }
            else:
                return {
                    "sucesso": False,
                    "erro": f"Erro na requisição: {error_msg}",
                    "tipo_erro": "bad_request"
                }
            
        except openai.RateLimitError as e:
            # Nova estrutura de exceptions
            logger.error(f"Rate limit DALL-E: {str(e)}")
            return {
                "sucesso": False,
                "erro": "Limite de requisições excedido. Tente novamente em alguns minutos.",
                "tipo_erro": "rate_limit"
            }
            
        except openai.APIError as e:
            # Erro genérico da API
            logger.error(f"Erro API DALL-E: {str(e)}")
            return {
                "sucesso": False,
                "erro": f"Erro na API do DALL-E: {str(e)}",
                "tipo_erro": "api_error"
            }
            
        except Exception as e:
            logger.error(f"Erro ao gerar conceito visual: {str(e)}", exc_info=True)
            return {
                "sucesso": False,
                "erro": f"Erro inesperado: {str(e)}",
                "tipo_erro": "unknown"
            }
    
    def _sanitizar_prompt(self, prompt: str) -> str:
        """
        Remove ou substitui conteúdo que pode violar políticas do DALL-E
        """
        # Palavras que podem causar problemas
        substituicoes = {
            "executivos": "profissionais",
            "executivas": "profissionais",
            "trajes executivos": "roupas formais",
            "vestidas formalmente": "em ambiente profissional",
            "interagindo": "trabalhando",
            "pessoas": "profissionais",
            "visitantes": "clientes",
        }
        
        prompt_limpo = prompt
        for palavra_original, substituta in substituicoes.items():
            prompt_limpo = prompt_limpo.replace(palavra_original, substituta)
        
        # Remover menções específicas a pessoas se muito detalhadas
        import re
        # Remover descrições muito específicas de pessoas
        prompt_limpo = re.sub(r'pessoas em .+? interagindo', 'ambiente profissional movimentado', prompt_limpo, flags=re.IGNORECASE)
        
        return prompt_limpo
    
    def _criar_prompt_seguro(self, briefing) -> str:
        """
        Cria um prompt simplificado e seguro para casos de rejeição
        """
        # Dados básicos
        largura = float(briefing.medida_frente) if briefing.medida_frente else 6.0
        profundidade = float(briefing.medida_fundo) if briefing.medida_fundo else 8.0
        area = largura * profundidade
        
        empresa = "empresa corporativa"
        if hasattr(briefing, 'projeto') and hasattr(briefing.projeto, 'empresa'):
            empresa = briefing.projeto.empresa.nome or "empresa corporativa"
        
        # Prompt MUITO simplificado e seguro
        prompt = f"""Professional trade show exhibition booth design, modern architecture style.
Dimensions: {largura:.0f}m x {profundidade:.0f}m, total area {area:.0f}m².
Clean modern design with reception area, display zones, and meeting space.
Professional lighting, corporate colors (blue, white, gray).
3D architectural rendering, perspective view, high quality visualization.
Exhibition center environment, trade show setting."""
        
        logger.info(f"Prompt seguro criado: {prompt}")
        return prompt
    
    def _construir_prompt_integrado(
        self, 
        briefing, 
        layout: Dict[str, Any], 
        inspiracoes: Dict[str, Any]
    ) -> str:
        """
        Constrói prompt integrando dados do briefing, layout e inspirações
        VERSÃO SIMPLIFICADA PARA EVITAR REJEIÇÕES
        """
        # Dados do briefing
        empresa = "Corporate Client"
        if hasattr(briefing, 'projeto') and hasattr(briefing.projeto, 'empresa'):
            empresa = briefing.projeto.empresa.nome or "Corporate Client"
        
        # Dimensões
        largura = float(briefing.medida_frente) if briefing.medida_frente else 6.0
        profundidade = float(briefing.medida_fundo) if briefing.medida_fundo else 8.0
        altura = 3.0
        area_total = briefing.area_estande or (largura * profundidade)
        
        # Estilo
        estilo_estande = briefing.estilo_estande or "modern professional"
        
        # Processar áreas do layout
        areas_texto = self._processar_areas_layout(layout)
        
        # Processar inspirações
        cores = self._processar_cores(inspiracoes)
        materiais_ref = self._processar_materiais(inspiracoes)
        
        # PROMPT SIMPLIFICADO E SEGURO
        prompt = f"""Create a photorealistic image of a professional TRADE SHOW EXHIBITION BOOTH.

SPECIFICATIONS:
- Client: {empresa}
- Dimensions: {largura:.0f}m x {profundidade:.0f}m x {altura:.0f}m
- Total area: {area_total:.0f} square meters
- Style: {estilo_estande}

BOOTH AREAS:
{areas_texto}

DESIGN:
- Colors: {cores}
- Materials: {materiais_ref}
- Professional lighting
- Company branding visible

VISUALIZATION:
- 3D perspective view of the booth
- Trade show environment setting
- Professional architectural rendering
- High quality, photorealistic finish
- Modern exhibition design

Create a professional exhibition booth suitable for business trade shows."""

        return prompt.strip()
    
    def _processar_areas_layout(self, layout: Dict[str, Any]) -> str:
        """Processa as áreas identificadas no layout"""
        if not layout or "areas" not in layout:
            return "- Reception area\n- Display zone\n- Meeting space\n- Product showcase"
        
        areas = layout.get("areas", [])
        texto_areas = []
        
        if isinstance(areas, list):
            for area in areas:
                if isinstance(area, dict):
                    nome = area.get("nome", area.get("id", "area"))
                    m2 = area.get("m2_estimado", 0)
                    if m2 > 0:
                        texto_areas.append(f"- {nome}: {m2:.0f} sqm")
                    else:
                        texto_areas.append(f"- {nome}")
        elif isinstance(areas, dict):
            for nome, dados in areas.items():
                if isinstance(dados, dict):
                    m2 = dados.get("m2", dados.get("area", 0))
                    if m2 > 0:
                        texto_areas.append(f"- {nome}: {m2:.0f} sqm")
                    else:
                        texto_areas.append(f"- {nome}")
        
        return "\n".join(texto_areas[:5]) if texto_areas else "- Open exhibition space"
    
    def _processar_cores(self, inspiracoes: Dict[str, Any]) -> str:
        """Processa paleta de cores das inspirações"""
        cores_predominantes = inspiracoes.get("cores_predominantes", [])
        if cores_predominantes and isinstance(cores_predominantes, list):
            cores_hex = []
            for cor in cores_predominantes[:3]:  # Máximo 3 cores
                if isinstance(cor, dict) and "hex" in cor:
                    cores_hex.append(cor["hex"])
            
            if cores_hex:
                return ", ".join(cores_hex)
        
        return "blue, white, gray"
    
    def _processar_materiais(self, inspiracoes: Dict[str, Any]) -> str:
        """Processa materiais sugeridos"""
        materiais = inspiracoes.get("materiais_sugeridos", [])
        if materiais and isinstance(materiais, list):
            lista_materiais = []
            for mat in materiais[:3]:  # Máximo 3 materiais
                if isinstance(mat, dict):
                    material = mat.get("material", "")
                    if material:
                        lista_materiais.append(material)
            
            if lista_materiais:
                return ", ".join(lista_materiais)
        
        return "wood, glass, metal"
    
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
        
        # Verificar se menciona estande/feira
        palavras_importantes = ["booth", "stand", "estande", "feira", "exhibition", "trade show"]
        tem_contexto = any(palavra in prompt.lower() for palavra in palavras_importantes)
        if not tem_contexto:
            avisos.append("Prompt não menciona explicitamente 'estande' ou 'feira'")
        
        # Verificar conteúdo que pode ser problemático para DALL-E
        palavras_cuidado = ["pessoas", "executivos", "crianças", "políticos"]
        for palavra in palavras_cuidado:
            if palavra.lower() in prompt.lower():
                avisos.append(f"Palavra '{palavra}' pode causar rejeição")
        
        return {
            "valido": len(problemas) == 0,
            "problemas": problemas,
            "avisos": avisos,
            "tamanho": len(prompt),
            "tem_contexto_correto": tem_contexto
        }