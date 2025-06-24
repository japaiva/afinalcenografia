# core/services/conceito_visual_service.py

import json
import logging
from django.core.files.base import ContentFile
from django.conf import settings
from core.models import Agente
from projetista.models import PlantaBaixa
import xml.etree.ElementTree as ET
from PIL import Image, ImageDraw
import io

logger = logging.getLogger(__name__)

# =============================================================================
# CONCEITO VISUAL SERVICE
# =============================================================================

class ConceitoVisualService:
    """
    Serviço para geração de conceitos visuais baseados em planta baixa
    """
    
    def __init__(self, agente=None):
        self.agente = agente
        
    def gerar_conceito_visual(self, briefing, planta_baixa, **config):
        """
        Gera conceito visual baseado no briefing e planta baixa
        """
        try:
            # Extrair configurações
            estilo = config.get('estilo_visualizacao', 'fotorrealista')
            iluminacao = config.get('iluminacao', 'feira')
            instrucoes_extras = config.get('instrucoes_adicionais', '')
            versao = config.get('versao', 1)
            conceito_anterior = config.get('conceito_anterior', None)
            
            # Obter agente para geração de imagem
            if not self.agente:
                try:
                    self.agente = Agente.objects.get(nome='Agente de Conceito Visual')
                    if not self.agente.ativo:
                        return {
                            'success': False,
                            'error': 'Agente de Conceito Visual está inativo'
                        }
                except Agente.DoesNotExist:
                    return {
                        'success': False,
                        'error': 'Agente de Conceito Visual não encontrado'
                    }
            
            # Usar ImagemPrincipalService para gerar a imagem
            from core.services.imagem_principal_service import ImagemPrincipalService
            imagem_service = ImagemPrincipalService(self.agente)
            
            # Construir prompt baseado na planta baixa
            prompt_customizado = self._construir_prompt_com_planta(
                briefing, planta_baixa, estilo, iluminacao, instrucoes_extras
            )
            
            # Gerar imagem usando prompt customizado
            resultado_imagem = imagem_service._gerar_imagem_com_api(prompt_customizado)
            
            if resultado_imagem['success']:
                # Importar modelo aqui para evitar imports circulares
                from projetista.models import ConceitoVisualNovo
                
                # Criar objeto ConceitoVisualNovo
                conceito = ConceitoVisualNovo(
                    projeto=briefing.projeto,
                    briefing=briefing,
                    planta_baixa=planta_baixa,
                    projetista=briefing.projeto.projetista,
                    descricao=f"Conceito visual {estilo} - {iluminacao}",
                    estilo_visualizacao=estilo,
                    iluminacao=iluminacao,
                    ia_gerado=True,
                    agente_usado=self.agente,
                    prompt_geracao=prompt_customizado,
                    instrucoes_adicionais=instrucoes_extras,
                    versao=versao,
                    conceito_anterior=conceito_anterior,
                    status='pronto'
                )
                
                # Salvar imagem
                filename = f"conceito_{briefing.projeto.id}_v{versao}.png"
                from django.core.files.base import ContentFile
                file_content = ContentFile(resultado_imagem['image_data'])
                conceito.imagem.save(filename, file_content, save=False)
                conceito.save()
                
                return {
                    'success': True,
                    'conceito': conceito,
                    'prompt_usado': prompt_customizado
                }
            else:
                return {
                    'success': False,
                    'error': resultado_imagem['error'],
                    'details': resultado_imagem.get('details', '')
                }
                
        except Exception as e:
            logger.error(f"Erro ao gerar conceito visual: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }
    
    def _construir_prompt_com_planta(self, briefing, planta_baixa, estilo, iluminacao, instrucoes_extras):
        """
        Constrói prompt incluindo informações da planta baixa
        """
        # Obter dados da planta baixa
        dados_planta = planta_baixa.dados_json if planta_baixa.dados_json else {}
        
        # Extrair informações relevantes
        area_total = dados_planta.get('area_total', 'não especificada')
        ambientes = dados_planta.get('ambientes', [])
        
        # Listar ambientes
        lista_ambientes = []
        for ambiente in ambientes:
            nome = ambiente.get('nome', 'Ambiente')
            area = ambiente.get('area', 0)
            lista_ambientes.append(f"- {nome} ({area:.1f}m²)")
        
        ambientes_texto = '\n'.join(lista_ambientes) if lista_ambientes else "- Espaço principal"
        
        # Informações do briefing
        nome_projeto = briefing.projeto.nome
        tipo_stand = briefing.tipo_stand or 'personalizado'
        estilo_estande = briefing.estilo_estande or 'moderno'
        
        # Construir prompt
        prompt = f"""
        Crie uma imagem {estilo} em perspectiva 3/4 de um estande de feira com {iluminacao}.
        
        PROJETO: {nome_projeto}
        TIPO: {tipo_stand}
        ESTILO: {estilo_estande}
        
        LAYOUT BASEADO NA PLANTA BAIXA:
        - Área total: {area_total}m²
        - Ambientes:
        {ambientes_texto}
        
        REQUISITOS:
        - Vista em perspectiva mostrando fachada e lateral
        - Layout interno coerente com a planta baixa
        - Materiais e acabamentos adequados ao estilo
        - Iluminação {iluminacao} realista
        - Logotipo visível na entrada
        - Fluxo de visitantes bem definido
        
        {instrucoes_extras}
        """
        
        return prompt.strip()
