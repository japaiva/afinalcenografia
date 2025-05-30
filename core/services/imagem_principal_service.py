# core/services/imagem_principal_service.py
from django.conf import settings
import json
import requests
import base64
import logging

logger = logging.getLogger(__name__)

class ImagemPrincipalService:
    """Serviço para geração da imagem principal usando DALL-E 3"""
    
    def __init__(self, agente):
        self.agente = agente
        self.api_key = settings.OPENAI_API_KEY
        self.model = agente.llm_model  # dall-e-3
        self.system_prompt = getattr(agente, 'llm_system_prompt', '')
        self.task_instructions = getattr(agente, 'task_instructions', '')
    
    def gerar_imagem_principal(self, conceito, estilo_visualizacao='fotorrealista', 
                               iluminacao='diurna', instrucoes_adicionais=''):
        """Gera a imagem principal do conceito visual"""
        # Forçar perspectiva para imagem principal
        angulo_vista = 'perspectiva'
        
        # Construir prompt
        prompt = self._build_prompt(conceito, angulo_vista, estilo_visualizacao, 
                                   iluminacao, instrucoes_adicionais)
        
        # Verificar tamanho do prompt
        if len(prompt) > 3800:  # Margem de segurança
            prompt = self._truncar_prompt(prompt, 3800)
            
        # Gerar imagem
        result = self._gerar_imagem_com_api(prompt)
        
        # Adicionar filename ao resultado se for bem-sucedido
        if result['success']:
            result['filename'] = f"estande_{conceito.id}_principal.png"
            
        return result
    
    def refinar_imagem(self, imagem_original, instrucoes_modificacao):
        """Refina uma imagem existente com instruções de modificação"""
        # Obter o prompt original 
        prompt_original = imagem_original.prompt_geracao
        
        # Se não existir, criar um básico
        if not prompt_original:
            prompt_original = f"Estande em perspectiva 3/4 para o conceito '{imagem_original.conceito.titulo}'"
        
        # Limitar o tamanho do prompt original se necessário
        max_len_original = 2500
        if len(prompt_original) > max_len_original:
            prompt_original = prompt_original[:max_len_original] + "..."
            
        # Limitar o tamanho das instruções
        max_len_instrucoes = 1000
        if len(instrucoes_modificacao) > max_len_instrucoes:
            instrucoes_modificacao = instrucoes_modificacao[:max_len_instrucoes] + "..."
        
        # Criar prompt de refinamento
        prompt_atualizado = f"{prompt_original}\n\nMODIFICAÇÕES ADICIONAIS:\n{instrucoes_modificacao}"
        
        # Gerar nova imagem
        result = self._gerar_imagem_com_api(prompt_atualizado)
        
        # Adicionar filename ao resultado se for bem-sucedido
        if result['success']:
            result['filename'] = f"estande_{imagem_original.conceito.id}_v{imagem_original.versao + 1}.png"
        
        return result
    
    def _truncar_prompt(self, prompt, max_len):
        """Trunca o prompt para o tamanho máximo, preservando estrutura"""
        if len(prompt) <= max_len:
            return prompt
            
        # Cortar no meio, preservando início e fim
        inicio_len = int(max_len * 0.7)
        fim_len = max_len - inicio_len - 10  # -10 para "... ..." 
        
        return prompt[:inicio_len] + "...\n...\n" + prompt[-fim_len:]
    
    def _gerar_imagem_com_api(self, prompt):
            """Gera imagem usando API DALL-E"""
            try:
                # Aumentar o timeout para 90 segundos (tempo suficiente para geração de imagem)
                timeout = 90
                
                # Chamar API
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
                    },
                    timeout=timeout  # Aumentado para 90 segundos
                )
                
                # Processar resposta
                if response.status_code == 200:
                    result = response.json()
                    if 'data' in result and len(result['data']) > 0 and 'b64_json' in result['data'][0]:
                        image_data = result['data'][0]['b64_json']
                        img_data = base64.b64decode(image_data)
                        
                        return {
                            'success': True,
                            'image_data': img_data,
                            'prompt_used': prompt,
                            'raw_response': result
                        }
                
                # Tratar erros
                error_msg = f"Erro na API: {response.status_code}"
                try:
                    error_json = response.json()
                    if 'error' in error_json and 'message' in error_json['error']:
                        error_msg = error_json['error']['message']
                except:
                    pass
                    
                return {
                    'success': False,
                    'error': error_msg,
                    'details': response.text
                }
                    
            except requests.exceptions.Timeout:
                # Tratamento específico para timeout
                logger.error("Timeout na geração de imagem - a API da OpenAI demorou muito para responder")
                return {
                    'success': False,
                    'error': "A geração de imagem demorou mais que o esperado",
                    'details': "A conexão com a API da OpenAI atingiu o limite de tempo. Isso pode acontecer durante períodos de alto tráfego ou quando o servidor está ocupado. Por favor, tente novamente em alguns instantes."
                }
            except requests.exceptions.ConnectionError:
                # Tratamento para problemas de conexão
                logger.error("Erro de conexão com a API da OpenAI")
                return {
                    'success': False,
                    'error': "Erro de conexão com a API",
                    'details': "Não foi possível estabelecer uma conexão com o servidor da OpenAI. Verifique sua conexão com a internet e tente novamente."
                }
            except Exception as e:
                # Captura outros erros
                logger.error(f"Erro não previsto ao gerar imagem: {str(e)}", exc_info=True)
                return {
                    'success': False,
                    'error': "Erro ao processar a solicitação",
                    'details': str(e)
                }    
            
    def _build_prompt(self, conceito, angulo_vista, estilo_visualizacao='fotorrealista', 
                        iluminacao='diurna', instrucoes_adicionais=''):
            """Constrói o prompt simplificado para geração de imagem"""
            # Descrições simplificadas
            descricao_angulo = 'perspectiva 3/4' if angulo_vista == 'perspectiva' else angulo_vista
            descricao_estilo = estilo_visualizacao
            
            # Obter informações essenciais de forma segura
            titulo = conceito.titulo or "Estande"
            descricao_curta = conceito.descricao[:200] if conceito.descricao else "Estande moderno"
            paleta = conceito.paleta_cores[:100] if conceito.paleta_cores else "Cores neutras"
            materiais = conceito.materiais_principais[:100] if conceito.materiais_principais else "Materiais modernos"
            
            # Construir prompt extremamente simplificado
            prompt = f"""
            Estande de feira em {descricao_estilo}, {descricao_angulo}, {iluminacao}.
            
            Conceito: {titulo}
            Descrição: {descricao_curta}
            Cores: {paleta}
            Materiais: {materiais}
            {instrucoes_adicionais}
            """
            
            return prompt.strip()

    def _build_promptao(self, conceito, angulo_vista, estilo_visualizacao='fotorrealista', 
                     iluminacao='diurna', instrucoes_adicionais=''):
        """Constrói o prompt para geração de imagem"""
        # Descrições de ângulos
        angulos_desc = {
            'perspectiva': 'vista em perspectiva 3/4 do estande completo',
            'frontal': 'vista frontal completa do estande',
            'lateral_esquerda': 'vista lateral esquerda do estande',
            'lateral_direita': 'vista lateral direita do estande',
            'interior': 'vista interior do estande',
            'superior': 'vista superior (planta baixa)'
        }
        descricao_angulo = angulos_desc.get(angulo_vista, 'vista em perspectiva do estande')
        
        # Estilos visuais
        estilos = {
            'fotorrealista': 'fotorrealista com materiais realistas',
            'renderizado': 'render 3D de alta qualidade',
            'estilizado': 'visualização estilizada e colorida'
        }
        descricao_estilo = estilos.get(estilo_visualizacao, estilos['fotorrealista'])
        
        # Iluminação
        iluminacoes = {
            'diurna': 'iluminação diurna natural',
            'noturna': 'iluminação noturna com LED',
            'evento': 'iluminação de evento com spots'
        }
        descricao_iluminacao = iluminacoes.get(iluminacao, iluminacoes['diurna'])
        
        # Garantir valores válidos
        titulo = conceito.titulo or "Estande Personalizado"
        descricao = conceito.descricao or "Estande moderno"
        paleta_cores = conceito.paleta_cores or "Cores neutras"
        materiais = conceito.materiais_principais or "Materiais contemporâneos"
        
        # Briefing
        briefing = conceito.briefing
        tipo_stand = getattr(briefing, 'tipo_stand', 'personalizado') if briefing else 'personalizado'
        
        # Dimensões
        try:
            medida_frente = getattr(briefing, 'medida_frente', '6') if briefing else '6'
            medida_fundo = getattr(briefing, 'medida_fundo', '6') if briefing else '6'
        except:
            medida_frente = '6'
            medida_fundo = '6'
        
        # Construir prompt final
        prompt = f"""
        {self.system_prompt}
        
        Crie uma imagem {descricao_estilo} de um estande de feira com {descricao_angulo}.
        
        TÍTULO: {titulo}
        
        DESCRIÇÃO: {descricao}
        
        CARACTERÍSTICAS:
        - Tipo: estande {tipo_stand} em feira
        - Dimensões: {medida_frente}m x {medida_fundo}m
        - Paleta de cores: {paleta_cores}
        - Materiais: {materiais}
        - Iluminação: {descricao_iluminacao}
        
        REQUISITOS:
        - Logotipo visível na entrada 
        - Áreas bem distribuídas
        - Proporção correta sem distorções
        - Qualidade alta, adequada para cliente
        
        {instrucoes_adicionais}
        
        {self.task_instructions}
        """
        
        return prompt.strip()