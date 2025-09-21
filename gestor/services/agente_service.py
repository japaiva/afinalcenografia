# gestor/services/conceito_visual_dalle.py
# VERSÃO SIMPLIFICADA - Apenas wrapper do DALL-E

import openai
import requests
import logging
from typing import Dict, Any, Optional
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

class ConceitoVisualDalleService:
    """
    Wrapper simples para a API do DALL-E 3
    Apenas recebe um prompt pronto e gera a imagem
    
    O prompt é preparado pela view usando:
    - Template do Agente (system_prompt + task_instructions do banco)
    - Dados do layout identificado (etapa 1)
    - Dados das inspirações visuais (etapa 2)
    - Dados do briefing
    """
    
    def __init__(self):
        openai.api_key = settings.OPENAI_API_KEY
        
    def gerar_conceito_visual(
        self, 
        briefing=None,  # Mantido para compatibilidade
        layout=None,     # Mantido para compatibilidade
        inspiracoes=None,  # Mantido para compatibilidade
        prompt_customizado: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executa o prompt no DALL-E 3 e retorna a imagem
        
        Args:
            prompt_customizado: Prompt já processado pela view
            
        Returns:
            Dict com resultado da geração
        """
        
        if not prompt_customizado:
            return {
                "sucesso": False,
                "erro": "Prompt não fornecido",
                "tipo_erro": "missing_prompt"
            }
        
        prompt = prompt_customizado.strip()
        
        # Validações básicas
        if len(prompt) < 10:
            return {
                "sucesso": False,
                "erro": "Prompt muito curto",
                "tipo_erro": "invalid_prompt"
            }
        
        # DALL-E 3 tem limite de 4000 caracteres
        if len(prompt) > 4000:
            logger.warning(f"Prompt com {len(prompt)} chars, truncando para 4000")
            prompt = prompt[:3997] + "..."
        
        try:
            logger.info(f"Gerando imagem com DALL-E 3 - Prompt: {len(prompt)} chars")
            
            # Chamar API do DALL-E 3
            response = openai.images.generate(
                model="dall-e-3",
                prompt=prompt,
                size="1792x1024",  # Landscape HD
                quality="hd",
                n=1,
                style="natural"  # Mais fotorrealista
            )
            
            image_url = response.data[0].url
            revised_prompt = getattr(response.data[0], 'revised_prompt', prompt)
            
            logger.info(f"✓ Imagem gerada com sucesso")
            
            # Retornar resultado
            return {
                "sucesso": True,
                "image_url": image_url,
                "prompt_usado": prompt,
                "prompt_revisado": revised_prompt,
                "modelo": "dall-e-3",
                "timestamp": timezone.now().isoformat()
            }
            
        except openai.BadRequestError as e:
            error_msg = str(e)
            logger.error(f"Erro BadRequest: {error_msg}")
            
            if "content_policy" in error_msg.lower() or "safety" in error_msg.lower():
                return {
                    "sucesso": False,
                    "erro": "Prompt rejeitado pela política de conteúdo. Tente remover referências a pessoas ou ajustar o texto.",
                    "tipo_erro": "content_policy"
                }
            
            return {
                "sucesso": False,
                "erro": f"Erro na requisição: {error_msg}",
                "tipo_erro": "bad_request"
            }
            
        except openai.RateLimitError:
            logger.error("Rate limit excedido")
            return {
                "sucesso": False,
                "erro": "Limite de requisições excedido. Aguarde alguns minutos.",
                "tipo_erro": "rate_limit"
            }
            
        except Exception as e:
            logger.error(f"Erro inesperado: {str(e)}", exc_info=True)
            return {
                "sucesso": False,
                "erro": f"Erro ao gerar imagem: {str(e)}",
                "tipo_erro": "unknown"
            }
    
    def validar_prompt(self, prompt: str) -> Dict[str, Any]:
        """
        Validação opcional do prompt antes de enviar
        """
        problemas = []
        avisos = []
        
        if not prompt:
            problemas.append("Prompt vazio")
        elif len(prompt) < 50:
            avisos.append("Prompt muito curto, pode gerar resultado genérico")
        
        if len(prompt) > 4000:
            problemas.append(f"Prompt excede limite ({len(prompt)}/4000 chars)")
        elif len(prompt) > 3500:
            avisos.append(f"Prompt próximo do limite ({len(prompt)}/4000)")
        
        # Verificar se menciona conceitos importantes
        conceitos_esperados = ["estande", "feira", "booth", "exhibition", "trade show"]
        tem_conceito = any(c in prompt.lower() for c in conceitos_esperados)
        if not tem_conceito:
            avisos.append("Prompt não menciona 'estande' ou conceitos relacionados")
        
        return {
            "valido": len(problemas) == 0,
            "problemas": problemas,
            "avisos": avisos,
            "tamanho": len(prompt) if prompt else 0
        }