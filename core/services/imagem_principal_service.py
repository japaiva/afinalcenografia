# core/services/imagem_principal_service.py
from django.conf import settings
import json
import requests
import base64
import os
from django.core.files.base import ContentFile
import logging

logger = logging.getLogger(__name__)

class ImagemPrincipalService:
    """Serviço para geração da imagem principal usando DALL-E 3"""
    
    def __init__(self, agente):
        self.agente = agente
        self.api_key = settings.OPENAI_API_KEY
        self.model = agente.llm_model  # dall-e-3
        self.temperature = float(agente.llm_temperature)  # 0.7
        self.system_prompt = agente.llm_system_prompt
        self.task_instructions = agente.task_instructions or ""
    
    def gerar_imagem_principal(self, conceito, angulo_vista='perspectiva'):
        """Gera a imagem principal do conceito visual"""
        prompt = self._build_prompt(conceito, angulo_vista)
        
        try:
            # Chamada à API da OpenAI (DALL-E 3)
            response = requests.post(
                "https://api.openai.com/v1/images/generations",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}"
                },
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "n": 1,
                    "size": "1024x1024",
                    "response_format": "b64_json"
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                image_data = result['data'][0]['b64_json']
                
                # Convertendo base64 para arquivo de imagem
                img_data = base64.b64decode(image_data)
                img_filename = f"estande_{conceito.id}_{angulo_vista}.png"
                
                return {
                    'success': True,
                    'image_data': img_data,
                    'filename': img_filename,
                    'prompt_used': prompt,
                    'raw_response': result
                }
            else:
                logger.error(f"Erro na API DALL-E: {response.status_code} - {response.text}")
                return {
                    'success': False,
                    'error': f"Erro na API: {response.status_code}",
                    'details': response.text
                }
        
        except Exception as e:
            logger.error(f"Exceção ao gerar imagem: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _build_prompt(self, conceito, angulo_vista):
        """Constrói o prompt para o modelo de geração de imagens"""
        # Extrair dados do conceito e briefing
        briefing = conceito.briefing
        
        # Descrição do ângulo de visualização
        angulos_desc = {
            'perspectiva': 'vista em perspectiva 3/4 do estande completo, mostrando frente e uma lateral',
            'frontal': 'vista frontal completa do estande',
            'lateral_esquerda': 'vista da lateral esquerda do estande',
            'lateral_direita': 'vista da lateral direita do estande',
            'interior': 'vista do interior do estande, mostrando o ambiente interno',
            'superior': 'vista superior (planta baixa) do estande, mostrando a distribuição de áreas',
            'detalhe': 'detalhe aproximado de um elemento importante do estande'
        }
        descricao_angulo = angulos_desc.get(angulo_vista, 'vista em perspectiva do estande')
        
        # Prompt final combinando o system prompt e as instruções específicas
        prompt = f"{self.system_prompt}\n\n"
        
        prompt += f"""
        Crie uma imagem fotorrealista de um estande de feira em estilo {briefing.estilo_estande or conceito.titulo or "moderno"} com {descricao_angulo}.
        
        DESCRIÇÃO DO ESTANDE:
        {conceito.descricao}
        
        CARACTERÍSTICAS FÍSICAS:
        - Tipo: estande {briefing.tipo_stand or "padrão"} em feira de exposição
        - Dimensões aproximadas: {briefing.medida_frente}m x {briefing.medida_fundo}m
        - Paleta de cores: {conceito.paleta_cores}
        - Materiais principais: {conceito.materiais_principais}
        
        {self.task_instructions}
        """
        
        return prompt