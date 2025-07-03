# core/services/crewai/__init__.py
from .base_service import CrewAIServiceV2
from .specialized.planta_baixa import PlantaBaixaServiceV2

__all__ = ['CrewAIServiceV2', 'PlantaBaixaServiceV2']