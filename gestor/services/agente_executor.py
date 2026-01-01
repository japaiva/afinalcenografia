# gestor/services/agente_executor.py
"""
Serviço para execução de agentes individuais de IA.
Suporta OpenAI (GPT-4, GPT-4o) e Anthropic (Claude).
"""

import logging
import base64
import requests
from typing import Dict, Any, List, Optional
from io import BytesIO

import openai
from anthropic import Anthropic
from django.conf import settings
from core.models import Agente

logger = logging.getLogger(__name__)


class AgenteService:
    """
    Serviço para executar agentes individuais de IA.

    Suporta:
    - OpenAI (gpt-4, gpt-4o, gpt-4-turbo)
    - Anthropic (claude-3-opus, claude-3-sonnet, claude-3-haiku, claude-3-5-sonnet)
    - Visão (imagens via URL ou base64)
    """

    def __init__(self):
        # Configurar APIs
        openai.api_key = settings.OPENAI_API_KEY
        self.anthropic_client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    def executar_agente(
        self,
        agente: Agente,
        prompt_usuario: str,
        imagens: Optional[List[str]] = None
    ) -> str:
        """
        Executa um agente individual com um prompt.

        Args:
            agente: Instância do modelo Agente
            prompt_usuario: Prompt/conteúdo para o agente processar
            imagens: Lista opcional de URLs ou paths de imagens

        Returns:
            String com a resposta do agente

        Raises:
            ValueError: Se configuração do agente é inválida
            RuntimeError: Se execução falhar
        """

        # Validar agente
        if not agente.ativo:
            raise ValueError(f"Agente '{agente.nome}' está inativo")

        # Aceitar tanto 'individual' quanto 'crew_member' para execução individual
        if agente.tipo not in ["individual", "crew_member"]:
            raise ValueError(f"Agente '{agente.nome}' tem tipo inválido: {agente.tipo}")

        # Log da execução
        logger.info(f"[AGENTE] Executando: {agente.nome}")
        logger.info(f"[AGENTE] Provider: {agente.llm_provider}")
        logger.info(f"[AGENTE] Modelo: {agente.llm_model}")
        logger.info(f"[AGENTE] Temperatura: {agente.llm_temperature}")
        logger.info(f"[AGENTE] Prompt: {len(prompt_usuario)} chars")
        if imagens:
            logger.info(f"[AGENTE] Imagens: {len(imagens)}")

        # Executar baseado no provider
        try:
            provider_lower = agente.llm_provider.lower()
            if provider_lower == "openai":
                # Verificar se é modelo de imagem (DALL-E)
                if "dall-e" in agente.llm_model.lower() or "image" in agente.llm_model.lower():
                    return self._gerar_imagem_openai(agente, prompt_usuario)
                else:
                    return self._executar_openai(agente, prompt_usuario, imagens)
            elif provider_lower == "anthropic":
                return self._executar_anthropic(agente, prompt_usuario, imagens)
            else:
                raise ValueError(f"Provider '{agente.llm_provider}' não suportado")

        except Exception as e:
            logger.error(f"[AGENTE] Erro na execução: {str(e)}", exc_info=True)
            raise RuntimeError(f"Falha ao executar agente: {str(e)}")

    def _executar_openai(
        self,
        agente: Agente,
        prompt_usuario: str,
        imagens: Optional[List[str]] = None
    ) -> str:
        """Executa agente usando OpenAI API."""

        # Construir mensagens
        messages = []

        # System prompt (se houver)
        if agente.llm_system_prompt:
            messages.append({
                "role": "system",
                "content": agente.llm_system_prompt
            })

        # User message (com ou sem imagens)
        if imagens and len(imagens) > 0:
            # Modelo precisa suportar visão
            if "vision" not in agente.llm_model and "gpt-4o" not in agente.llm_model:
                logger.warning(f"Modelo {agente.llm_model} pode não suportar visão, tentando mesmo assim")

            # Construir content com texto + imagens
            content = [
                {"type": "text", "text": prompt_usuario}
            ]

            # Adicionar imagens
            for img_url in imagens:
                img_data = self._preparar_imagem_openai(img_url)
                content.append(img_data)

            messages.append({
                "role": "user",
                "content": content
            })
        else:
            # Apenas texto
            messages.append({
                "role": "user",
                "content": prompt_usuario
            })

        # Chamar API
        logger.info(f"[OPENAI] Chamando API com {len(messages)} mensagens")

        response = openai.chat.completions.create(
            model=agente.llm_model,
            messages=messages,
            temperature=agente.llm_temperature,
            max_tokens=getattr(agente, 'llm_max_tokens', 4096) or 4096
        )

        resultado = response.choices[0].message.content
        logger.info(f"[OPENAI] Resposta recebida: {len(resultado)} chars")

        return resultado

    def _executar_anthropic(
        self,
        agente: Agente,
        prompt_usuario: str,
        imagens: Optional[List[str]] = None
    ) -> str:
        """Executa agente usando Anthropic API."""

        # System prompt
        system_prompt = agente.llm_system_prompt or ""

        # Construir mensagem do usuário
        if imagens and len(imagens) > 0:
            # Content com texto + imagens
            content = []

            # Adicionar imagens primeiro
            for img_url in imagens:
                img_data = self._preparar_imagem_anthropic(img_url)
                content.append(img_data)

            # Adicionar texto
            content.append({
                "type": "text",
                "text": prompt_usuario
            })
        else:
            # Apenas texto
            content = prompt_usuario

        # Chamar API
        logger.info(f"[ANTHROPIC] Chamando API")

        response = self.anthropic_client.messages.create(
            model=agente.llm_model,
            max_tokens=getattr(agente, 'llm_max_tokens', 4096) or 4096,
            temperature=agente.llm_temperature,
            system=system_prompt,
            messages=[
                {
                    "role": "user",
                    "content": content
                }
            ]
        )

        resultado = response.content[0].text
        logger.info(f"[ANTHROPIC] Resposta recebida: {len(resultado)} chars")

        return resultado

    def _preparar_imagem_openai(self, img_url_ou_path: str) -> Dict[str, Any]:
        """
        Prepara imagem para OpenAI Vision API.

        Args:
            img_url_ou_path: URL pública ou path local da imagem

        Returns:
            Dict no formato esperado pela OpenAI
        """
        # Se for URL pública (http/https), usar diretamente
        if img_url_ou_path.startswith("http://") or img_url_ou_path.startswith("https://"):
            logger.info(f"[OPENAI] Usando URL direta: {img_url_ou_path[:80]}...")
            return {
                "type": "image_url",
                "image_url": {
                    "url": img_url_ou_path,
                    "detail": "high"
                }
            }

        # Caso contrário, converter para base64
        logger.info(f"[OPENAI] Convertendo para base64: {img_url_ou_path[:80]}...")

        # Se for path local ou URL relativa, baixar/ler e converter
        try:
            if img_url_ou_path.startswith("/"):
                # Path local
                with open(img_url_ou_path, "rb") as f:
                    img_data = f.read()
            else:
                # Tentar baixar como URL
                response = requests.get(img_url_ou_path, timeout=30)
                response.raise_for_status()
                img_data = response.content

            # Converter para base64
            base64_img = base64.b64encode(img_data).decode('utf-8')

            # Detectar tipo MIME (simplificado)
            if img_url_ou_path.lower().endswith('.png'):
                mime_type = "image/png"
            elif img_url_ou_path.lower().endswith('.jpg') or img_url_ou_path.lower().endswith('.jpeg'):
                mime_type = "image/jpeg"
            elif img_url_ou_path.lower().endswith('.webp'):
                mime_type = "image/webp"
            else:
                mime_type = "image/jpeg"  # fallback

            return {
                "type": "image_url",
                "image_url": {
                    "url": f"data:{mime_type};base64,{base64_img}",
                    "detail": "high"
                }
            }

        except Exception as e:
            logger.error(f"Erro ao processar imagem: {str(e)}")
            raise ValueError(f"Falha ao processar imagem: {str(e)}")

    def _preparar_imagem_anthropic(self, img_url_ou_path: str) -> Dict[str, Any]:
        """
        Prepara imagem para Anthropic Vision API.

        Args:
            img_url_ou_path: URL ou path da imagem

        Returns:
            Dict no formato esperado pela Anthropic
        """
        logger.info(f"[ANTHROPIC] Processando imagem: {img_url_ou_path[:80]}...")

        # Anthropic requer base64, não aceita URLs diretas
        try:
            # Baixar/ler imagem
            if img_url_ou_path.startswith("/"):
                # Path local
                with open(img_url_ou_path, "rb") as f:
                    img_data = f.read()
            else:
                # URL - baixar
                response = requests.get(img_url_ou_path, timeout=30)
                response.raise_for_status()
                img_data = response.content

            # Converter para base64
            base64_img = base64.b64encode(img_data).decode('utf-8')

            # Detectar tipo MIME
            if img_url_ou_path.lower().endswith('.png'):
                media_type = "image/png"
            elif img_url_ou_path.lower().endswith('.jpg') or img_url_ou_path.lower().endswith('.jpeg'):
                media_type = "image/jpeg"
            elif img_url_ou_path.lower().endswith('.webp'):
                media_type = "image/webp"
            else:
                media_type = "image/jpeg"  # fallback

            return {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": media_type,
                    "data": base64_img
                }
            }

        except Exception as e:
            logger.error(f"Erro ao processar imagem para Anthropic: {str(e)}")
            raise ValueError(f"Falha ao processar imagem: {str(e)}")

    def _refinar_prompt_para_dalle(self, prompt: str) -> str:
        """
        Usa GPT-4 para refinar/otimizar o prompt antes de enviar ao DALL-E.
        Isso simula o comportamento do ChatGPT que pré-processa prompts de imagem.

        Args:
            prompt: Prompt original

        Returns:
            Prompt refinado e otimizado para DALL-E
        """
        logger.info("[GPT-4] Refinando prompt para DALL-E...")

        system_prompt = """Você é um especialista em criar prompts para DALL-E 3.
Sua tarefa é transformar a descrição técnica de um stand de feira em um prompt visual otimizado.

REGRAS IMPORTANTES:
1. Mantenha TODAS as informações de layout e dimensões
2. Adicione detalhes visuais específicos para cada área mencionada
3. Inclua instruções para que cada área seja CLARAMENTE IDENTIFICÁVEL na imagem
4. Peça labels/placas visíveis com os nomes das áreas (ex: "Workshop", "Depósito", "Área de Exposição")
5. Especifique perspectiva 3/4 que mostre bem o layout interno
6. Descreva materiais, cores e iluminação de forma visual
7. O prompt final deve ter no máximo 3500 caracteres
8. Seja direto e visual, não use linguagem técnica demais

FORMATO DE SAÍDA:
Retorne APENAS o prompt refinado, sem explicações ou comentários."""

        try:
            response = openai.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Transforme esta descrição técnica em um prompt visual para DALL-E:\n\n{prompt}"}
                ],
                max_tokens=1500,
                temperature=0.7
            )

            prompt_refinado = response.choices[0].message.content.strip()
            logger.info(f"[GPT-4] Prompt refinado: {len(prompt_refinado)} chars")
            logger.info(f"[GPT-4] Preview: {prompt_refinado[:200]}...")

            return prompt_refinado

        except Exception as e:
            logger.warning(f"[GPT-4] Erro ao refinar prompt, usando original: {str(e)}")
            return prompt

    def _gerar_imagem_openai(self, agente: Agente, prompt: str) -> str:
        """
        Gera imagem usando API de imagens da OpenAI (gpt-image-1, DALL-E 3, DALL-E 2).

        Args:
            agente: Instância do modelo Agente
            prompt: Descrição da imagem a ser gerada

        Returns:
            URL da imagem gerada
        """
        logger.info(f"[OPENAI-IMAGE] Gerando imagem com modelo '{agente.llm_model}'")
        logger.info(f"[OPENAI-IMAGE] Prompt original: {len(prompt)} chars")

        # Usar o modelo exatamente como está cadastrado
        modelo = agente.llm_model
        logger.info(f"[OPENAI-IMAGE] Usando modelo: {modelo}")

        # NOVO: Refinar prompt com GPT-4 (simula comportamento do ChatGPT)
        prompt_refinado = self._refinar_prompt_para_dalle(prompt)

        # Preparar system prompt se houver
        prompt_final = prompt_refinado
        if agente.llm_system_prompt:
            prompt_final = f"{agente.llm_system_prompt}\n\n{prompt_refinado}"

        # Truncar prompt se necessário (DALL-E 3 tem limite de 4000 caracteres)
        if len(prompt_final) > 4000:
            logger.warning(f"[DALL-E] Prompt muito longo ({len(prompt_final)} chars), truncando para 4000")
            prompt_final = prompt_final[:4000]

        try:
            # Gerar imagem
            # gpt-image-1 aceita quality: 'low', 'medium', 'high', 'auto'
            # dall-e-3 aceita quality: 'standard', 'hd'
            if modelo == 'gpt-image-1':
                quality = "high"
            else:
                quality = "hd"  # Para dall-e-3 e dall-e-2

            # Configurar parâmetros baseado no modelo
            params = {
                "model": modelo,
                "prompt": prompt_final,
                "size": "1792x1024" if modelo == "dall-e-3" else "1024x1024",
                "quality": quality,
                "n": 1
            }

            # DALL-E 3 suporta style (vivid = mais dramático, natural = mais realista)
            if modelo == "dall-e-3":
                params["style"] = "vivid"

            response = openai.images.generate(**params)

            # Extrair URL da imagem
            imagem_url = response.data[0].url
            logger.info(f"[DALL-E] Imagem gerada com sucesso: {imagem_url[:80]}...")

            return imagem_url

        except Exception as e:
            logger.error(f"[DALL-E] Erro ao gerar imagem: {str(e)}", exc_info=True)
            raise RuntimeError(f"Falha ao gerar imagem: {str(e)}")
