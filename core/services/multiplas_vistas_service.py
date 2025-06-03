# core/services/multiplas_vistas_service.py

import logging
import json
import requests
import base64
import time
from typing import List, Dict, Any
from django.core.files.base import ContentFile
from django.conf import settings
from projetista.models import ImagemConceitoVisual

logger = logging.getLogger(__name__)

class MultiplasVistasService:
    """
    Serviço para geração de múltiplas vistas usando DALL-E 3
    """
    
    def __init__(self, agente):
        self.agente = agente
        self.api_key = settings.OPENAI_API_KEY  # Mesma API da imagem principal
        self.model = agente.llm_model  # dall-e-3
        self.system_prompt = getattr(agente, 'llm_system_prompt', '')
        self.task_instructions = getattr(agente, 'task_instructions', '')
        
        # Mapeamento de vistas com prompts específicos
        self.prompts_vistas = {
            # VISTAS PARA CLIENTE
            'perspectiva_externa': "Vista em perspectiva 3/4 do estande, mostrando a fachada principal e lateral direita, ângulo diagonal",
            'entrada_recepcao': "Vista frontal da entrada do estande, destacando a recepção e primeira impressão do visitante",
            'interior_principal': "Vista interna principal do estande, mostrando o espaço central e fluxo de visitantes, perspectiva de dentro",
            'area_produtos': "Vista da área de exposição de produtos, destacando displays e zona comercial, foco nos produtos",
            
            # VISTAS TÉCNICAS EXTERNAS
            'elevacao_frontal': "Elevação frontal técnica do estande, vista ortogonal da fachada principal, desenho arquitetônico",
            'elevacao_lateral_esquerda': "Elevação lateral esquerda, vista ortogonal da lateral, desenho técnico",
            'elevacao_lateral_direita': "Elevação lateral direita, vista ortogonal da lateral, desenho técnico",
            'elevacao_fundos': "Elevação dos fundos do estande, vista ortogonal traseira, desenho técnico",
            'quina_frontal_esquerda': "Vista em ângulo da quina frontal esquerda, perspectiva diagonal 45 graus",
            'quina_frontal_direita': "Vista em ângulo da quina frontal direita, perspectiva diagonal 45 graus",
            
            # PLANTAS E VISTAS SUPERIORES
            'planta_baixa': "Planta baixa do estande vista de cima, mostrando layout e distribuição espacial, desenho técnico superior",
            'vista_superior': "Vista superior isométrica do estande, perspectiva aérea em 45 graus",
            
            # VISTAS INTERNAS SISTEMÁTICAS
            'interior_parede_norte': "Vista interna da parede norte do estande, perspectiva de dentro olhando para a parede",
            'interior_parede_sul': "Vista interna da parede sul do estande, perspectiva de dentro olhando para a parede",
            'interior_parede_leste': "Vista interna da parede leste do estande, perspectiva de dentro olhando para a parede",
            'interior_parede_oeste': "Vista interna da parede oeste do estande, perspectiva de dentro olhando para a parede",
            'interior_perspectiva_1': "Perspectiva interna 1, vista geral do espaço interno do estande",
            'interior_perspectiva_2': "Perspectiva interna 2, vista alternativa do espaço interno do estande",
            'interior_perspectiva_3': "Perspectiva interna 3, vista detalhada de área específica do estande",
            
            # DETALHES ESPECÍFICOS
            'detalhe_balcao': "Detalhe do balcão de atendimento, vista aproximada e focada",
            'detalhe_display': "Detalhe dos displays de produtos, vista aproximada e focada",
            'detalhe_iluminacao': "Detalhe do sistema de iluminação, vista específica das luminárias",
            'detalhe_entrada': "Detalhe da entrada do estande, vista aproximada do acesso",
        }
    
    def gerar_multiplas_vistas(self, conceito, imagem_principal, vistas_desejadas: List[str], **config) -> Dict[str, Any]:
        """
        Gera múltiplas vistas baseadas na imagem principal usando DALL-E 3
        """
        try:
            resultados = {
                'success': True,
                'vistas_geradas': [],
                'vistas_falharam': [],
                'total_solicitadas': len(vistas_desejadas)
            }
            
            # Extrair configurações
            estilo = config.get('estilo_visualizacao', 'fotorrealista')
            iluminacao = config.get('iluminacao', 'diurna')
            instrucoes_extras = config.get('instrucoes_adicionais', '')
            prioridade_cliente = config.get('prioridade_cliente', True)
            
            # Ordenar vistas por prioridade se solicitado
            if prioridade_cliente:
                vistas_desejadas = self._ordenar_por_prioridade(vistas_desejadas)
            
            logger.info(f"Iniciando geração de {len(vistas_desejadas)} vistas para conceito {conceito.id}")
            
            # Gerar cada vista
            for i, vista in enumerate(vistas_desejadas, 1):
                try:
                    logger.info(f"Gerando vista {i}/{len(vistas_desejadas)}: {vista}")
                    
                    resultado_vista = self._gerar_vista_individual(
                        conceito, imagem_principal, vista, estilo, iluminacao, instrucoes_extras
                    )
                    
                    if resultado_vista['success']:
                        resultados['vistas_geradas'].append({
                            'vista': vista,
                            'imagem_id': resultado_vista['imagem_id'],
                            'descricao': resultado_vista['descricao']
                        })
                        logger.info(f"Vista {vista} gerada com sucesso - ID: {resultado_vista['imagem_id']}")
                    else:
                        resultados['vistas_falharam'].append({
                            'vista': vista,
                            'erro': resultado_vista['error']
                        })
                        logger.error(f"Falha ao gerar vista {vista}: {resultado_vista['error']}")
                    
                    # Pequena pausa entre gerações para evitar rate limiting
                    if i < len(vistas_desejadas):
                        time.sleep(2)
                        
                except Exception as e:
                    logger.error(f"Erro ao gerar vista {vista}: {str(e)}", exc_info=True)
                    resultados['vistas_falharam'].append({
                        'vista': vista,
                        'erro': str(e)
                    })
            
            # Calcular estatísticas finais
            if len(vistas_desejadas) > 0:
                resultados['taxa_sucesso'] = (len(resultados['vistas_geradas']) / len(vistas_desejadas)) * 100
            else:
                resultados['taxa_sucesso'] = 0
            
            logger.info(f"Geração concluída - {len(resultados['vistas_geradas'])}/{len(vistas_desejadas)} vistas criadas")
            
            return resultados
            
        except Exception as e:
            logger.error(f"Erro geral ao gerar múltiplas vistas: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'vistas_geradas': [],
                'vistas_falharam': []
            }
    
    def _gerar_vista_individual(self, conceito, imagem_principal, vista, estilo, iluminacao, instrucoes_extras):
        """
        Gera uma vista individual usando DALL-E 3
        """
        try:
            # Construir prompt específico para a vista
            prompt_completo = self._construir_prompt_completo(
                conceito, vista, estilo, iluminacao, instrucoes_extras
            )
            
            # Gerar imagem usando a mesma lógica da imagem principal
            resultado_api = self._gerar_imagem_com_api(prompt_completo)
            
            if resultado_api['success']:
                # Criar objeto ImagemConceitoVisual
                imagem = self._criar_imagem_conceito(
                    conceito, vista, resultado_api, prompt_completo
                )
                
                return {
                    'success': True,
                    'imagem_id': imagem.id,
                    'descricao': imagem.descricao,
                    'prompt_usado': prompt_completo
                }
            else:
                return {
                    'success': False,
                    'error': resultado_api['error']
                }
                
        except Exception as e:
            logger.error(f"Erro ao gerar vista individual {vista}: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }
    
    def _gerar_imagem_com_api(self, prompt):
        """
        Gera imagem usando API DALL-E (mesma lógica da ImagemPrincipalService)
        """
        try:
            # Timeout adequado para geração
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
                timeout=timeout
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
            logger.error("Timeout na geração de imagem - API da OpenAI demorou muito")
            return {
                'success': False,
                'error': "A geração de imagem demorou mais que o esperado",
                'details': "Timeout na API da OpenAI. Tente novamente em alguns instantes."
            }
        except requests.exceptions.ConnectionError:
            logger.error("Erro de conexão com a API da OpenAI")
            return {
                'success': False,
                'error': "Erro de conexão com a API",
                'details': "Não foi possível conectar com a OpenAI. Verifique sua conexão."
            }
        except Exception as e:
            logger.error(f"Erro não previsto ao gerar imagem: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': "Erro ao processar a solicitação",
                'details': str(e)
            }
    
    def _construir_prompt_completo(self, conceito, vista, estilo, iluminacao, instrucoes_extras):
        """
        Constrói o prompt completo para a vista (baseado na ImagemPrincipalService)
        """
        # Obter prompt base para a vista
        prompt_base_vista = self.prompts_vistas.get(vista, f"Vista {vista} do estande")
        
        # Estilos visuais
        estilos = {
            'fotorrealista': 'fotorrealista com materiais realistas',
            'renderizado': 'render 3D de alta qualidade',
            'tecnico': 'desenho técnico arquitetônico',
            'estilizado': 'visualização estilizada e colorida'
        }
        descricao_estilo = estilos.get(estilo, estilos['fotorrealista'])
        
        # Iluminação
        iluminacoes = {
            'diurna': 'iluminação diurna natural',
            'noturna': 'iluminação noturna com LED',
            'evento': 'iluminação de evento com spots',
            'mista': 'iluminação balanceada'
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
        
        Crie uma imagem {descricao_estilo} de um estande de feira com {prompt_base_vista}.
        
        TÍTULO: {titulo}
        
        DESCRIÇÃO: {descricao}
        
        CARACTERÍSTICAS:
        - Tipo: estande {tipo_stand} em feira
        - Dimensões: {medida_frente}m x {medida_fundo}m
        - Paleta de cores: {paleta_cores}
        - Materiais: {materiais}
        - Iluminação: {descricao_iluminacao}
        
        REQUISITOS:
        - Manter consistência visual com o conceito
        - Qualidade alta, adequada para cliente
        - Proporção correta sem distorções
        
        {instrucoes_extras}
        
        {self.task_instructions}
        """
        
        # Verificar tamanho do prompt e truncar se necessário
        if len(prompt) > 3800:
            prompt = self._truncar_prompt(prompt, 3800)
        
        return prompt.strip()
    
    def _truncar_prompt(self, prompt, max_len):
        """
        Trunca o prompt para o tamanho máximo, preservando estrutura
        """
        if len(prompt) <= max_len:
            return prompt
            
        # Cortar no meio, preservando início e fim
        inicio_len = int(max_len * 0.7)
        fim_len = max_len - inicio_len - 10  # -10 para "... ..." 
        
        return prompt[:inicio_len] + "...\n...\n" + prompt[-fim_len:]
    
    def _criar_imagem_conceito(self, conceito, vista, resultado_api, prompt_usado):
        """
        Cria o objeto ImagemConceitoVisual
        """
        # Mapeamento de vistas para descrições amigáveis
        descricoes_map = {
            'perspectiva_externa': 'Perspectiva Externa Principal',
            'entrada_recepcao': 'Vista da Entrada e Recepção',
            'interior_principal': 'Vista Interna Principal',
            'area_produtos': 'Área de Exposição de Produtos',
            'elevacao_frontal': 'Elevação Frontal',
            'elevacao_lateral_esquerda': 'Elevação Lateral Esquerda',
            'elevacao_lateral_direita': 'Elevação Lateral Direita',
            'elevacao_fundos': 'Elevação dos Fundos',
            'planta_baixa': 'Planta Baixa',
            'vista_superior': 'Vista Superior',
            'quina_frontal_esquerda': 'Quina Frontal Esquerda',
            'quina_frontal_direita': 'Quina Frontal Direita',
            'interior_parede_norte': 'Interior - Parede Norte',
            'interior_parede_sul': 'Interior - Parede Sul',
            'interior_parede_leste': 'Interior - Parede Leste',
            'interior_parede_oeste': 'Interior - Parede Oeste',
            'interior_perspectiva_1': 'Interior - Perspectiva 1',
            'interior_perspectiva_2': 'Interior - Perspectiva 2',
            'interior_perspectiva_3': 'Interior - Perspectiva 3',
            'detalhe_balcao': 'Detalhe do Balcão',
            'detalhe_display': 'Detalhe dos Displays',
            'detalhe_iluminacao': 'Detalhe da Iluminação',
            'detalhe_entrada': 'Detalhe da Entrada',
        }
        
        descricao = descricoes_map.get(vista, f"Vista {vista.replace('_', ' ').title()}")
        
        # Criar objeto
        imagem = ImagemConceitoVisual(
            conceito=conceito,
            descricao=descricao,
            angulo_vista=vista,
            principal=False,
            ia_gerada=True,
            versao=1,
            prompt_geracao=prompt_usado
        )
        
        # Salvar dados da imagem
        filename = f"vista_{vista}_{conceito.id}_{int(time.time())}.png"
        file_content = ContentFile(resultado_api['image_data'], name=filename)
        imagem.imagem.save(filename, file_content, save=False)
        
        imagem.save()
        return imagem
    
    def _ordenar_por_prioridade(self, vistas):
        """
        Ordena vistas por prioridade (cliente primeiro)
        """
        prioridades = {
            # Cliente (alta prioridade)
            'perspectiva_externa': 1,
            'entrada_recepcao': 2,
            'interior_principal': 3,
            'area_produtos': 4,
            
            # Técnicas importantes
            'planta_baixa': 5,
            'elevacao_frontal': 6,
            
            # Outras vistas técnicas
            'elevacao_lateral_esquerda': 10,
            'elevacao_lateral_direita': 11,
            'elevacao_fundos': 12,
            
            # Internas
            'interior_parede_norte': 20,
            'interior_parede_sul': 21,
            'interior_parede_leste': 22,
            'interior_parede_oeste': 23,
            
            # Detalhes (baixa prioridade)
            'detalhe_balcao': 30,
            'detalhe_display': 31,
            'detalhe_iluminacao': 32,
            'detalhe_entrada': 33,
        }
        
        return sorted(vistas, key=lambda x: prioridades.get(x, 99))
    
    def get_pacotes_predefinidos(self):
        """
        Retorna os pacotes pré-definidos de vistas
        """
        return {
            'cliente': {
                'nome': 'Apresentação para Cliente',
                'vistas': ['perspectiva_externa', 'entrada_recepcao', 'interior_principal', 'area_produtos'],
                'descricao': '4 vistas impactantes para apresentação ao cliente',
                'tempo_estimado': '8-12 minutos'
            },
            'tecnico_basico': {
                'nome': 'Técnico Básico',
                'vistas': [
                    'perspectiva_externa', 'planta_baixa', 'elevacao_frontal', 
                    'elevacao_lateral_esquerda', 'elevacao_lateral_direita', 'elevacao_fundos',
                    'interior_principal', 'entrada_recepcao'
                ],
                'descricao': '8 vistas essenciais para desenvolvimento técnico',
                'tempo_estimado': '16-24 minutos'
            },
            'fotogrametria': {
                'nome': 'Fotogrametria Completa',
                'vistas': [
                    'perspectiva_externa', 'planta_baixa', 'vista_superior',
                    'elevacao_frontal', 'elevacao_lateral_esquerda', 'elevacao_lateral_direita', 'elevacao_fundos',
                    'quina_frontal_esquerda', 'quina_frontal_direita',
                    'interior_parede_norte', 'interior_parede_sul', 'interior_parede_leste', 'interior_parede_oeste',
                    'interior_perspectiva_1', 'interior_perspectiva_2', 'interior_perspectiva_3'
                ],
                'descricao': '16 vistas para reconstrução 3D completa',
                'tempo_estimado': '32-48 minutos'
            }
        }