# gestor/services/dalle_service.py - NOVO ARQUIVO

import openai
from django.conf import settings

class DalleService:
    """Serviço específico para DALL-E"""
    
    def __init__(self):
        openai.api_key = settings.OPENAI_API_KEY
    
    def gerar_imagem(self, prompt):
        """Gera imagem usando DALL-E 3"""
        try:
            response = openai.images.generate(
                model="dall-e-3",
                prompt=prompt[:4000],  # Limite do DALL-E
                size="1792x1024",      # Formato landscape HD
                quality="hd",
                n=1
            )
            
            return response.data[0].url
            
        except Exception as e:
            raise ValueError(f"Erro ao gerar imagem no DALL-E: {str(e)}")
    
    def gerar_variacao(self, prompt_base, variacao_texto):
        """Gera variação do conceito com modificações"""
        prompt_variacao = f"{prompt_base}\n\nVariação: {variacao_texto}"
        return self.gerar_imagem(prompt_variacao)
