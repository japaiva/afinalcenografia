# gestor/services/conceito_visual_dalle.py
# VERSÃO COM LOGS NO CONSOLE PARA DEBUG

import json
import openai
import requests
import logging
import traceback
import sys
from typing import Dict, Any, Optional
from django.conf import settings
from django.utils import timezone

# Configurar logger para enviar para console também
logger = logging.getLogger(__name__)

# Adicionar handler para console se não existir
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter('[%(levelname)s] %(asctime)s - DALLE - %(message)s')
console_handler.setFormatter(formatter)

# Remover handlers duplicados e adicionar o console
logger.handlers = []
logger.addHandler(console_handler)
logger.setLevel(logging.INFO)

# Função auxiliar para print direto (garante saída no console)
def console_log(msg, level="INFO"):
    """Print direto no console para garantir visibilidade"""
    print(f"[{level}] DALLE - {msg}", flush=True)
    sys.stdout.flush()

class ConceitoVisualDalleService:
    """
    Wrapper para DALL-E 3 com logs no console
    """
    
    def __init__(self):
        """Inicializa o serviço e valida configurações"""
        console_log("Inicializando serviço DALL-E...")
        
        # Verificar se a API key existe
        self.api_key = getattr(settings, 'OPENAI_API_KEY', None)
        
        if not self.api_key:
            # Tentar pegar do ambiente
            import os
            self.api_key = os.getenv('OPENAI_API_KEY')
            if self.api_key:
                console_log(f"API key obtida do ambiente: ...{self.api_key[-6:]}")
            else:
                console_log("❌ OPENAI_API_KEY não encontrada!", "ERROR")
                raise ValueError("OPENAI_API_KEY não configurada")
        else:
            console_log(f"API key obtida do settings: ...{self.api_key[-6:]}")
        
        # Configurar cliente OpenAI
        try:
            openai.api_key = self.api_key
            console_log(f"✅ OpenAI configurado com sucesso")
        except Exception as e:
            console_log(f"❌ Erro ao configurar OpenAI: {str(e)}", "ERROR")
            raise
        
    def gerar_conceito_visual(
        self, 
        briefing=None,
        layout=None,
        inspiracoes=None,
        prompt_customizado: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Gera conceito visual usando DALL-E 3
        """
        
        console_log("="*60)
        console_log("🎨 INICIANDO GERAÇÃO DE CONCEITO VISUAL")
        console_log("="*60)
        
        # 1. Validação do prompt
        if not prompt_customizado:
            console_log("❌ Prompt não fornecido", "ERROR")
            return {
                "sucesso": False,
                "erro": "Prompt não fornecido",
                "tipo_erro": "missing_prompt"
            }
        
        prompt = prompt_customizado.strip()
        console_log(f"📝 Prompt recebido com {len(prompt)} caracteres")
        console_log(f"Primeiros 200 chars: {prompt[:200]}...")
        
        # Validações básicas
        if len(prompt) < 10:
            console_log(f"❌ Prompt muito curto: {len(prompt)} chars", "ERROR")
            return {
                "sucesso": False,
                "erro": f"Prompt muito curto ({len(prompt)} caracteres)",
                "tipo_erro": "invalid_prompt"
            }
        
        # Truncar se necessário
        if len(prompt) > 4000:
            console_log(f"⚠️ Prompt truncado de {len(prompt)} para 4000 chars", "WARNING")
            prompt = prompt[:3997] + "..."
        
        # 2. Verificar API key antes de chamar
        if not openai.api_key:
            console_log("❌ API key não está configurada no cliente OpenAI", "ERROR")
            return {
                "sucesso": False,
                "erro": "API key não configurada",
                "tipo_erro": "config_error"
            }
        
        console_log(f"✅ API key verificada: ...{openai.api_key[-6:]}")
        
        # 3. Chamar DALL-E
        try:
            console_log("🚀 Enviando requisição para DALL-E 3...")
            console_log("   Configurações:")
            console_log("   - Modelo: dall-e-3")
            console_log("   - Tamanho: 1792x1024")
            console_log("   - Qualidade: HD")
            
            response = openai.images.generate(
                model="dall-e-3",
                prompt=prompt,
                size="1792x1024",
                quality="hd",
                n=1,
                style="natural"
            )
            
            # Verificar resposta
            if not response or not response.data:
                console_log("❌ Resposta vazia do DALL-E", "ERROR")
                return {
                    "sucesso": False,
                    "erro": "Resposta vazia da API",
                    "tipo_erro": "empty_response"
                }
            
            # Extrair dados
            image_url = response.data[0].url
            revised_prompt = getattr(response.data[0], 'revised_prompt', prompt[:100])
            
            console_log("✅ IMAGEM GERADA COM SUCESSO!")
            console_log(f"   URL: {image_url[:80]}...")
            console_log("="*60)
            
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
            console_log(f"❌ BadRequestError: {error_msg}", "ERROR")
            
            if "content_policy" in error_msg.lower() or "safety" in error_msg.lower():
                console_log("Conteúdo rejeitado por política de segurança", "WARNING")
                return {
                    "sucesso": False,
                    "erro": "Prompt rejeitado pela política de conteúdo",
                    "tipo_erro": "content_policy"
                }
            
            return {
                "sucesso": False,
                "erro": f"Requisição inválida: {error_msg}",
                "tipo_erro": "bad_request"
            }
            
        except openai.RateLimitError as e:
            console_log(f"❌ Rate limit excedido: {str(e)}", "ERROR")
            return {
                "sucesso": False,
                "erro": "Limite de requisições excedido",
                "tipo_erro": "rate_limit"
            }
            
        except openai.AuthenticationError as e:
            console_log(f"❌ Erro de autenticação: {str(e)}", "ERROR")
            console_log(f"API key usada: ...{self.api_key[-6:] if self.api_key else 'None'}", "ERROR")
            return {
                "sucesso": False,
                "erro": "Erro de autenticação com a API",
                "tipo_erro": "auth_error"
            }
            
        except openai.APIError as e:
            console_log(f"❌ Erro API OpenAI: {str(e)}", "ERROR")
            return {
                "sucesso": False,
                "erro": f"Erro na API: {str(e)}",
                "tipo_erro": "api_error"
            }
            
        except Exception as e:
            error_type = type(e).__name__
            error_msg = str(e)
            console_log(f"❌ Erro inesperado {error_type}: {error_msg}", "ERROR")
            console_log(f"Traceback:\n{traceback.format_exc()}", "ERROR")
            
            return {
                "sucesso": False,
                "erro": f"Erro inesperado: {error_msg}",
                "tipo_erro": "unknown"
            }
    
    def validar_prompt(self, prompt: str) -> Dict[str, Any]:
        """
        Validação do prompt
        """
        console_log(f"Validando prompt de {len(prompt) if prompt else 0} caracteres")
        
        problemas = []
        avisos = []
        
        if not prompt:
            problemas.append("Prompt vazio")
        elif len(prompt) < 50:
            avisos.append("Prompt muito curto")
        
        if len(prompt) > 4000:
            problemas.append(f"Prompt excede limite ({len(prompt)}/4000)")
        
        conceitos_esperados = ["estande", "feira", "booth", "exhibition", "trade show"]
        tem_conceito = any(c in prompt.lower() for c in conceitos_esperados)
        
        if not tem_conceito:
            avisos.append("Prompt não menciona conceitos de estande")
        
        resultado = {
            "valido": len(problemas) == 0,
            "problemas": problemas,
            "avisos": avisos,
            "tamanho": len(prompt) if prompt else 0
        }
        
        if problemas:
            console_log(f"Problemas encontrados: {problemas}", "WARNING")
        if avisos:
            console_log(f"Avisos: {avisos}", "INFO")
            
        return resultado