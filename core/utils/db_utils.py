"""
Utilitários para operações de banco de dados
"""
import logging
from typing import List, Dict, Any, Optional, Type
from django.db import models, transaction

logger = logging.getLogger(__name__)

class BulkOperations:
    """
    Classe para facilitar operações em massa no banco de dados
    """
    
    @staticmethod
    def bulk_update_or_create(model_class: Type[models.Model], 
                            objects_data: List[Dict[str, Any]], 
                            lookup_fields: List[str],
                            update_fields: Optional[List[str]] = None) -> Dict[str, int]:
        """
        Atualiza ou cria vários objetos em massa
        
        Args:
            model_class: Classe do modelo
            objects_data: Lista de dicionários com dados dos objetos
            lookup_fields: Lista de campos para identificar objetos existentes
            update_fields: Lista de campos para atualizar (opcional)
            
        Returns:
            Dicionário com contadores de operações
        """
        if not objects_data:
            return {'created': 0, 'updated': 0}
        
        # Identificar objetos existentes
        logger.info(f"Processando {len(objects_data)} objetos para bulk_update_or_create")
        
        existing_objects = {}
        objects_to_create = []
        objects_to_update = []
        
        with transaction.atomic():
            # Construir lookup para objetos existentes
            for data in objects_data:
                # Construir filtro para lookup
                lookup = {field: data[field] for field in lookup_fields if field in data}
                
                if not lookup:
                    logger.warning(f"Dados sem campos de lookup: {data}")
                    continue
                
                # Verificar se objeto existe
                try:
                    obj = model_class.objects.get(**lookup)
                    # Guardar para atualização
                    for field, value in data.items():
                        if update_fields is None or field in update_fields:
                            setattr(obj, field, value)
                    objects_to_update.append(obj)
                except model_class.DoesNotExist:
                    # Objeto não existe, criar novo
                    obj = model_class(**data)
                    objects_to_create.append(obj)
                except Exception as e:
                    logger.error(f"Erro ao buscar objeto com lookup {lookup}: {str(e)}")
            
            # Criar objetos em massa
            if objects_to_create:
                logger.info(f"Criando {len(objects_to_create)} novos objetos")
                model_class.objects.bulk_create(objects_to_create)
            
            # Atualizar objetos em massa
            if objects_to_update:
                if update_fields:
                    logger.info(f"Atualizando {len(objects_to_update)} objetos existentes (campos: {update_fields})")
                    model_class.objects.bulk_update(objects_to_update, update_fields)
                else:
                    # Obter todos os campos do modelo exceto pk
                    all_fields = [f.name for f in model_class._meta.fields if not f.primary_key]
                    logger.info(f"Atualizando {len(objects_to_update)} objetos existentes (todos os campos)")
                    model_class.objects.bulk_update(objects_to_update, all_fields)
        
        return {
            'created': len(objects_to_create),
            'updated': len(objects_to_update)
        }