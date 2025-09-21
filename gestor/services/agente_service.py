import os
import base64
import openai
import anthropic
import requests
from django.conf import settings
from typing import List, Optional, Dict, Any

def _file_to_data_url(path: str) -> str:
    """Converte um arquivo local para um data URL."""
    mime = "image/jpeg"
    ext = os.path.splitext(path)[1].lower()
    if ext == ".png":
        mime = "image/png"
    elif ext == ".webp":
        mime = "image/webp"
    elif ext == ".gif":
        mime = "image/gif"
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    return f"data:{mime};base64,{b64}"

class AgenteService:
    """Serviço para executar agentes individuais"""

    def executar_agente(
        self,
        agente,
        prompt_usuario: str,
        imagens: Optional[List[str]] = None,
    ):
        provider = getattr(agente, "llm_provider", "openai")
        if provider == "openai":
            return self._executar_openai(agente, prompt_usuario, imagens)
        elif provider == "anthropic":
            return self._executar_anthropic(agente, prompt_usuario)
        else:
            raise ValueError(f"Provider {provider} não suportado")

    # ------------------- OPENAI - VERSÃO CORRIGIDA COM TASK_INSTRUCTIONS -------------------
    def _executar_openai(
        self,
        agente,
        prompt_usuario: str,
        imagens: Optional[List[str]] = None,
    ):
        openai.api_key = settings.OPENAI_API_KEY

        model = getattr(agente, "llm_model", "gpt-4o")
        temperature = getattr(agente, "llm_temperature", 0.0) or 0.0
        max_tokens = getattr(agente, "llm_max_tokens", 2000) or 2000
        system_prompt = getattr(agente, "llm_system_prompt", "") or ""
        task_instructions = getattr(agente, "task_instructions", "") or ""  # ← ADICIONAR
        forcar_json = getattr(agente, "forcar_json", False)

        # MODIFICAÇÃO: Concatenar task_instructions ao prompt do usuário
        if task_instructions:
            prompt_completo = f"{task_instructions}\n\n{prompt_usuario}"
            print(f"[AGENTE_SERVICE] Task instructions incluídas ({len(task_instructions)} chars)")
        else:
            prompt_completo = prompt_usuario
            print(f"[AGENTE_SERVICE] Sem task instructions, usando prompt direto")

        content_parts: List[Dict[str, Any]] = [{"type": "text", "text": prompt_completo}]  # ← USAR prompt_completo

        # --- LÓGICA DE IMAGEM CORRIGIDA ---
        if imagens:
            print(f"[AGENTE_SERVICE] Processando {len(imagens)} imagens...")
            
            for i, img_source in enumerate(imagens):
                if not img_source:
                    print(f"[AGENTE_SERVICE] Imagem {i+1}: vazia, pulando")
                    continue

                try:
                    print(f"[AGENTE_SERVICE] Imagem {i+1}: {img_source[:100]}...")  # Truncar URL longa
                    
                    # Se for uma URL HTTP/HTTPS, baixe e converta para Base64
                    if img_source.startswith("http://") or img_source.startswith("https://"):
                        print(f"[AGENTE_SERVICE] Baixando URL...")
                        
                        # Headers robustos
                        headers = {
                            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                            'Accept': 'image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
                            'Accept-Language': 'en-US,en;q=0.9',
                            'Connection': 'keep-alive',
                        }
                        
                        # Download com timeout generoso
                        response = requests.get(img_source, headers=headers, timeout=(10, 60))
                        response.raise_for_status()
                        
                        print(f"[AGENTE_SERVICE] Download OK: {response.status_code}, {len(response.content)} bytes")
                        
                        # Determinar MIME type
                        mime_type = response.headers.get('Content-Type', '').split(';')[0].strip()
                        if not mime_type or not mime_type.startswith('image/'):
                            mime_type = 'image/jpeg'  # fallback seguro
                        
                        print(f"[AGENTE_SERVICE] MIME type: {mime_type}")
                        
                        # Converter para base64
                        b64_image = base64.b64encode(response.content).decode('utf-8')
                        data_url = f"data:{mime_type};base64,{b64_image}"
                        
                        content_parts.append({
                            "type": "image_url", 
                            "image_url": {"url": data_url}
                        })
                        
                        print(f"[AGENTE_SERVICE] ✅ Imagem {i+1} processada: {len(data_url)} chars")
                        
                    # Se já for um data URL, use diretamente
                    elif img_source.startswith("data:image/"):
                        print(f"[AGENTE_SERVICE] Data URL detectada, usando diretamente")
                        content_parts.append({
                            "type": "image_url", 
                            "image_url": {"url": img_source}
                        })

                    # Se for um caminho de arquivo local, converta
                    elif os.path.exists(img_source):
                        print(f"[AGENTE_SERVICE] Arquivo local detectado")
                        data_url = _file_to_data_url(img_source)
                        content_parts.append({
                            "type": "image_url", 
                            "image_url": {"url": data_url}
                        })
                    
                    else:
                        print(f"[AGENTE_SERVICE] ❌ Formato não reconhecido: {img_source}")
                        
                except requests.exceptions.RequestException as e:
                    print(f"[AGENTE_SERVICE] ❌ Erro de requisição na imagem {i+1}: {e}")
                    continue
                except Exception as e:
                    print(f"[AGENTE_SERVICE] ❌ Erro geral na imagem {i+1}: {e}")
                    continue

            print(f"[AGENTE_SERVICE] Total de content parts: {len(content_parts)}")

        if forcar_json and system_prompt:
            system_prompt = system_prompt.strip() + "\n\nIMPORTANTE: Responda APENAS com um JSON válido."

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": content_parts},
        ]

        try:
            print(f"[AGENTE_SERVICE] Enviando para OpenAI: modelo={model}, {len(content_parts)} parts")
            
            # Debug: mostrar tamanhos
            print(f"[AGENTE_SERVICE] System prompt: {len(system_prompt)} chars")
            print(f"[AGENTE_SERVICE] User prompt completo: {len(prompt_completo)} chars")
            
            resp = openai.chat.completions.create(
                model=model,
                messages=messages,
                temperature=float(temperature),
                max_tokens=int(max_tokens),
            )
            
            result = resp.choices[0].message.content
            print(f"[AGENTE_SERVICE] ✅ Resposta recebida: {len(result) if result else 0} chars")
            return result
            
        except openai.APIError as e:
            print(f"[AGENTE_SERVICE] ❌ Erro OpenAI API: {e}")
            raise e

    # ------------------- ANTHROPIC - TAMBÉM CORRIGIDA -------------------
    def _executar_anthropic(self, agente, prompt_usuario: str):
        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        model = getattr(agente, "llm_model", "claude-3-5-sonnet-latest")
        temperature = getattr(agente, "llm_temperature", 0.2) or 0.2
        system_prompt = getattr(agente, "llm_system_prompt", "") or ""
        task_instructions = getattr(agente, "task_instructions", "") or ""  # ← ADICIONAR
        
        # MODIFICAÇÃO: Concatenar task_instructions
        if task_instructions:
            prompt_completo = f"{task_instructions}\n\n{prompt_usuario}"
            print(f"[AGENTE_SERVICE] Task instructions incluídas para Anthropic ({len(task_instructions)} chars)")
        else:
            prompt_completo = prompt_usuario
        
        msg = client.messages.create(
            model=model,
            max_tokens=2000,
            temperature=float(temperature),
            system=system_prompt,
            messages=[{"role": "user", "content": prompt_completo}],
        )
        return msg.content[0].text if msg.content else ""