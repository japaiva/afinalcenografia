# core/services/conceito_textual_service.py
from django.conf import settings
import json
import requests
import logging

# Configurar logger
logger = logging.getLogger(__name__)

class ConceitoTextualService:
    """Serviço para geração de conceitos textuais usando IA"""
    
    def __init__(self, agente):
        self.agente = agente
        self.api_key = settings.OPENAI_API_KEY
        self.model = agente.llm_model  # gpt-4o-mini
        self.temperature = float(agente.llm_temperature)  # 0.7

    def gerar_conceito(self, briefing_data):
        """Gera um conceito textual a partir dos dados do briefing"""
        prompt = self._build_prompt(briefing_data)
        
        # Log do prompt para debug
        logger.debug(f"Prompt gerado: {prompt}")
        
        try:
            # Log das informações da requisição
            system_prompt = self.agente.llm_system_prompt
            # Adicionar instruções explícitas para retornar JSON
            system_prompt += "\n\nIMPORTANTE: Formate sua resposta como um JSON válido com os seguintes campos: titulo, descricao, paleta_cores, materiais_principais, elementos_interativos."
            
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt + "\n\nPor favor, responda em formato JSON."}
                ],
                "temperature": self.temperature,
                "response_format": {"type": "json_object"}
            }
            logger.debug(f"Payload da requisição: {json.dumps(payload, indent=2)}")
            
            # Chamada à API da OpenAI
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}"
                },
                json=payload,
                timeout=60  # Adicionar timeout para evitar espera infinita
            )
            
            # Processar resposta
            if response.status_code == 200:
                result = response.json()
                content = json.loads(result['choices'][0]['message']['content'])
                logger.info(f"Resposta bem-sucedida da API: {json.dumps(content, indent=2)}")
                return {
                    'success': True,
                    'data': content,
                    'raw_response': result
                }
            else:
                # Log detalhado do erro
                error_message = f"Erro na API: {response.status_code}"
                error_details = response.text
                logger.error(f"{error_message}\nDetalhes da resposta: {error_details}")
                
                # Verificar se há mensagem de erro específica da OpenAI
                try:
                    error_json = response.json()
                    if 'error' in error_json:
                        openai_error = error_json['error'].get('message', 'Sem detalhes')
                        logger.error(f"Erro OpenAI: {openai_error}")
                        error_message = f"{error_message}: {openai_error}"
                except (json.JSONDecodeError, KeyError):
                    logger.error("Não foi possível decodificar detalhes do erro")
                
                return {
                    'success': False,
                    'error': error_message,
                    'details': error_details
                }
        
        except requests.exceptions.Timeout:
            error_msg = "Timeout ao chamar a API da OpenAI"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }
        except requests.exceptions.RequestException as e:
            error_msg = f"Erro de conexão com a API: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }
        except json.JSONDecodeError as e:
            error_msg = f"Erro ao decodificar JSON: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }
        except Exception as e:
            error_msg = f"Erro desconhecido: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                'success': False,
                'error': error_msg
            }
    
    def _build_prompt(self, briefing_data):
        """Constrói o prompt para o modelo de IA fornecendo apenas os dados estruturados do briefing"""
        # Extrair os dados do briefing
        basic_info = briefing_data['informacoes_basicas']
        physical = briefing_data['caracteristicas_fisicas']
        areas = briefing_data['areas_funcionais']
        visual = briefing_data['elementos_visuais']
        goals = briefing_data['objetivos_projeto']
        
        # Construir um JSON com os dados principais do briefing para o prompt
        briefing_json = {
            "projeto": {
                "nome": basic_info['nome_projeto'],
                "tipo_estande": basic_info['tipo_stand'],
                "feira": basic_info['feira'],
                "orcamento": str(basic_info['orcamento']) if basic_info['orcamento'] else "Não especificado"
            },
            "caracteristicas_fisicas": {
                "area_total": f"{physical['area_total']} m²" if physical['area_total'] else "Não especificado",
                "dimensoes": f"{physical['dimensoes']['frente']}m x {physical['dimensoes']['fundo']}m" if physical['dimensoes']['frente'] and physical['dimensoes']['fundo'] else "Não especificado",
                "estilo_desejado": physical['estilo_estande'] or "Não especificado",
                "material_predominante": physical['material_predominante'] or "Não especificado"
            },
            "areas_funcionais": {
                "tipo_venda": areas['tipo_venda'],
                "tipo_ativacao": areas['tipo_ativacao'] or "Não especificado",
                "areas_exposicao": len(areas['areas_exposicao']),
                "salas_reuniao": len(areas['salas_reuniao']),
                "tem_copa": len(areas['copas']) > 0,
                "tem_deposito": len(areas['depositos']) > 0
            },
            "elementos_visuais": {
                "logotipo": visual['logotipo'] or "Não especificado",
                "referencias": visual['referencias_dados'] or "Não especificado",
                "campanha": visual['campanha_dados'] or "Não especificado"
            },
            "objetivos": {
                "evento": goals['objetivo_evento'] or "Não especificado",
                "estande": goals['objetivo_estande'] or "Não especificado"
            }
        }
        
        # Usar o task_instructions como base e apenas inserir os dados do briefing
        task_instructions = self.agente.task_instructions or "Analise o seguinte briefing e crie um conceito visual adequado:"
        
        return f"{task_instructions}\n\n{json.dumps(briefing_json, indent=2, ensure_ascii=False)}"