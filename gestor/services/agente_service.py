# gestor/services/agente_service.py - NOVO ARQUIVO

import openai
import anthropic
from django.conf import settings

class AgenteService:
    """Serviço para executar agentes individuais"""
    
    def executar_agente(self, agente, prompt_usuario):
        """Executa um agente individual com prompt específico"""
        
        if agente.llm_provider == "openai":
            return self._executar_openai(agente, prompt_usuario)
        elif agente.llm_provider == "anthropic":
            return self._executar_anthropic(agente, prompt_usuario)
        else:
            raise ValueError(f"Provider {agente.llm_provider} não suportado")
    
    def _executar_openai(self, agente, prompt_usuario):
        """Executa agente via OpenAI"""
        openai.api_key = settings.OPENAI_API_KEY
        
        # Para modelos com visão
        if "vision" in agente.llm_model:
            # TODO: Implementar com imagens quando necessário
            messages = [
                {"role": "system", "content": agente.llm_system_prompt},
                {"role": "user", "content": prompt_usuario}
            ]
        else:
            messages = [
                {"role": "system", "content": agente.llm_system_prompt}, 
                {"role": "user", "content": prompt_usuario}
            ]
        
        response = openai.chat.completions.create(
            model=agente.llm_model,
            messages=messages,
            temperature=agente.llm_temperature,
            max_tokens=4000
        )
        
        return response.choices[0].message.content
    
    def _executar_anthropic(self, agente, prompt_usuario):
        """Executa agente via Anthropic"""
        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        
        message = client.messages.create(
            model=agente.llm_model,
            max_tokens=4000,
            temperature=agente.llm_temperature,
            system=agente.llm_system_prompt,
            messages=[{"role": "user", "content": prompt_usuario}]
        )
        
        return message.content[0].text