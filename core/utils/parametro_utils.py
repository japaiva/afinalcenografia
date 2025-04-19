"""
Utilitários para gerenciamento de parâmetros de indexação
"""
import logging
from typing import Any, Dict, Optional
from functools import lru_cache

from django.core.cache import cache

from core.models import ParametroIndexacao

logger = logging.getLogger(__name__)

class ParametroManager:
    """
    Classe para gerenciar parâmetros de indexação de forma centralizada
    """
    
    @staticmethod
    def get_param_value(nome: str, categoria: str, default: Any = None) -> Any:
        """
        Obtém o valor de um parâmetro de indexação, com fallback para valor padrão.
        Utiliza cache para evitar consultas repetidas ao banco de dados.
        
        Args:
            nome: Nome do parâmetro
            categoria: Categoria do parâmetro
            default: Valor padrão caso o parâmetro não exista
            
        Returns:
            Valor convertido do parâmetro ou valor padrão
        """
        # Chave para o cache
        cache_key = f"param:{categoria}:{nome}"
        
        # Verificar cache primeiro
        cached_value = cache.get(cache_key)
        if cached_value is not None:
            return cached_value
        
        try:
            param = ParametroIndexacao.objects.get(nome=nome, categoria=categoria)
            valor = param.valor_convertido()
            
            # Armazenar em cache por 5 minutos (300 segundos)
            cache.set(cache_key, valor, 300)
            
            return valor
        except ParametroIndexacao.DoesNotExist:
            logger.warning(f"Parâmetro '{nome}' (categoria: {categoria}) não encontrado. Usando valor padrão: {default}")
            return default
        except Exception as e:
            logger.error(f"Erro ao obter parâmetro '{nome}' (categoria: {categoria}): {str(e)}")
            return default
    
    @staticmethod
    @lru_cache(maxsize=32)
    def get_param_values_for_category(categoria: str) -> Dict[str, Any]:
        """
        Obtém todos os parâmetros de uma categoria específica
        
        Args:
            categoria: Categoria dos parâmetros
            
        Returns:
            Dicionário com os valores dos parâmetros
        """
        try:
            params = ParametroIndexacao.objects.filter(categoria=categoria)
            result = {param.nome: param.valor_convertido() for param in params}
            return result
        except Exception as e:
            logger.error(f"Erro ao obter parâmetros da categoria '{categoria}': {str(e)}")
            return {}
    
    @staticmethod
    def clear_param_cache(nome: Optional[str] = None, categoria: Optional[str] = None) -> None:
        """
        Limpa o cache de parâmetros
        
        Args:
            nome: Nome específico do parâmetro (opcional)
            categoria: Categoria específica (opcional)
        """
        if nome and categoria:
            cache_key = f"param:{categoria}:{nome}"
            cache.delete(cache_key)
            logger.info(f"Cache limpo para parâmetro '{nome}' (categoria: {categoria})")
        elif categoria:
            # Invalidar função em cache para esta categoria
            ParametroManager.get_param_values_for_category.cache_clear()
            logger.info(f"Cache limpo para categoria '{categoria}'")
        else:
            # Invalidar todos os caches
            ParametroManager.get_param_values_for_category.cache_clear()
            cache.clear()
            logger.info("Cache de parâmetros completamente limpo")