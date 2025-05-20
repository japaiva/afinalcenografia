# core/services/multiplas_vistas_service.py
from django.conf import settings
import json
import requests
import base64
import os
from django.core.files.base import ContentFile
import logging

logger = logging.getLogger(__name__)

class MultiplasVistasService:
    """Serviço para geração de múltiplas vistas a partir da imagem principal"""
    
    def __init__(self, agente):
        self.agente = agente
        self.api_key = settings.OPENAI_API_KEY
        self.model = agente.llm_model  # dall-e-3
        self.temperature = float(agente.llm_temperature)  # 0.6
        self.system_prompt = agente.llm_system_prompt
        self.task_instructions = agente.task_instructions or ""
    
    def gerar_vista(self, conceito, imagem_principal, angulo_vista):
        """Gera uma vista específica com base na imagem principal"""
        prompt = self._build_prompt(conceito, imagem_principal, angulo_vista)
        
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
    
    def _build_prompt(self, conceito, imagem_principal, angulo_vista):
        """Constrói o prompt mantendo consistência com a imagem principal"""
        # Descrição do ângulo de visualização
        angulos_desc = {
            'frontal': 'vista frontal completa do estande, mostrando toda a fachada principal',
            'lateral_esquerda': 'vista da lateral esquerda do estande',
            'lateral_direita': 'vista da lateral direita do estande',
            'interior': 'vista do interior do estande, mostrando o ambiente interno',
            'superior': 'vista superior (planta baixa) do estande, mostrando a distribuição de áreas',
            'detalhe': 'detalhe aproximado de um elemento importante do estande'
        }
        descricao_angulo = angulos_desc.get(angulo_vista, 'outra perspectiva do estande')
        
        # Prompt final combinando o system prompt e as instruções específicas
        prompt = f"{self.system_prompt}\n\n"
        
        prompt += f"""
        Crie uma imagem fotorrealista do MESMO estande mostrado na imagem principal, mas agora com {descricao_angulo}.
        
        ESTE ESTANDE JÁ FOI VISUALIZADO EM UMA IMAGEM ANTERIOR em {imagem_principal.get_angulo_vista_display()}. Agora preciso de uma visualização com {angulo_vista}.
        
        DESCRIÇÃO DO ESTANDE:
        {conceito.descricao}
        
        CARACTERÍSTICAS VISUAIS A MANTER:
        - Manter EXATAMENTE a mesma paleta de cores: {conceito.paleta_cores}
        - Manter EXATAMENTE os mesmos materiais: {conceito.materiais_principais}
        - Manter EXATAMENTE o mesmo estilo de design e elementos arquitetônicos
        - Manter EXATAMENTE a mesma iluminação e atmosfera
        
        {self.task_instructions}
        """
        
        return prompt