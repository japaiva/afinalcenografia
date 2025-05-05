# core/services/extracao_service.py

import logging
from django.db import models
from core.models import Feira, FeiraManualQA

logger = logging.getLogger(__name__)

class ExtracaoService:
    """
    Serviço para extrair informações dos Q&As existentes e preencher campos do cadastro.
    """
    
    def extrair_dados_feira(self, feira_id):
        """
        Extrai dados para o cadastro a partir dos Q&As existentes.
        Usa apenas os Q&As associados a campos específicos.
        """
        try:
            feira = Feira.objects.get(pk=feira_id)
            
            # Verificar se existem Q&As
            if not FeiraManualQA.objects.filter(feira_id=feira_id).exists():
                return {
                    'status': 'error',
                    'message': 'Não existem perguntas e respostas geradas para esta feira.'
                }
            
            # Obter todos os Q&As associados a campos
            field_qas = FeiraManualQA.objects.filter(
                feira_id=feira_id,
                campo_relacionado__isnull=False
            ).exclude(campo_relacionado='').order_by('-confianca_extracao')
            
            if not field_qas.exists():
                return {
                    'status': 'error',
                    'message': 'Não foram encontradas perguntas associadas a campos do cadastro.'
                }
            
            # Agrupar por campo e obter o melhor para cada campo
            resultados = {}
            campos_processados = set()
            
            for qa in field_qas:
                campo = qa.campo_relacionado
                
                if campo not in campos_processados:
                    campos_processados.add(campo)
                    
                    resultados[campo] = {
                        'valor': qa.answer,
                        'confianca': qa.confianca_extracao,
                        'pergunta': qa.question,
                        'id': qa.id
                    }
            
            if not resultados:
                return {
                    'status': 'empty',
                    'message': 'Não foi possível extrair dados relevantes.'
                }
            
            return {
                'status': 'success',
                'data': resultados
            }
            
        except Feira.DoesNotExist:
            return {
                'status': 'error',
                'message': 'Feira não encontrada.'
            }
        except Exception as e:
            logger.error(f"Erro ao extrair dados: {str(e)}")
            return {
                'status': 'error',
                'message': f'Erro ao processar extração: {str(e)}'
            }
    
    def aplicar_dados(self, feira_id, dados_selecionados):
        """
        Aplica os dados extraídos ao cadastro da feira.
        """
        try:
            feira = Feira.objects.get(pk=feira_id)
            campos_atualizados = []
            
            for nome_campo, valor in dados_selecionados.items():
                if hasattr(feira, nome_campo):
                    setattr(feira, nome_campo, valor)
                    campos_atualizados.append(nome_campo)
            
            if campos_atualizados:
                feira.save(update_fields=campos_atualizados)
                
                return {
                    'status': 'success',
                    'message': f'Dados aplicados com sucesso: {", ".join(campos_atualizados)}',
                    'campos_atualizados': campos_atualizados
                }
            else:
                return {
                    'status': 'warning',
                    'message': 'Nenhum campo foi atualizado.'
                }
                
        except Feira.DoesNotExist:
            return {
                'status': 'error',
                'message': 'Feira não encontrada.'
            }
        except Exception as e:
            logger.error(f"Erro ao aplicar dados: {str(e)}")
            return {
                'status': 'error',
                'message': f'Erro ao aplicar dados: {str(e)}'
            }