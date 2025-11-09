# projetos/services/briefing_areas_processor.py

"""
Processador de áreas do briefing - Etapa 3
Centraliza a lógica de processamento de todas as áreas do estande
"""

import logging
from typing import Dict, List, Type, Any
from django.db import models
from django.http import HttpRequest

from projetos.models.briefing import (
    Briefing, AreaExposicao, SalaReuniao, Copa, Deposito, Palco, Workshop
)

logger = logging.getLogger(__name__)


class AreaConfig:
    """Configuração de um tipo de área"""

    def __init__(
        self,
        model: Type[models.Model],
        checkbox_name: str,
        prefix: str,
        is_multiple: bool = True,
        checkbox_fields: List[str] = None,
        text_fields: List[str] = None,
        number_fields: List[str] = None
    ):
        self.model = model
        self.checkbox_name = checkbox_name
        self.prefix = prefix
        self.is_multiple = is_multiple
        self.checkbox_fields = checkbox_fields or []
        self.text_fields = text_fields or []
        self.number_fields = number_fields or []


# Configuração de todas as áreas
AREA_CONFIGS = {
    'area_exposicao': AreaConfig(
        model=AreaExposicao,
        checkbox_name='tem_area_exposicao',
        prefix='area_exposicao',
        is_multiple=True,
        checkbox_fields=[
            'tem_lounge', 'tem_vitrine_exposicao', 'tem_balcao_recepcao',
            'tem_mesas_atendimento', 'tem_balcao_cafe', 'tem_balcao_vitrine',
            'tem_caixa_vendas'
        ],
        text_fields=['equipamentos', 'observacoes'],
        number_fields=['metragem']
    ),
    'sala_reuniao': AreaConfig(
        model=SalaReuniao,
        checkbox_name='tem_sala_reuniao',
        prefix='sala_reuniao',
        is_multiple=True,
        text_fields=['equipamentos', 'tipo_sala'],
        number_fields=['metragem', 'capacidade']
    ),
    'palco': AreaConfig(
        model=Palco,
        checkbox_name='tem_palco',
        prefix='palco',
        is_multiple=True,
        checkbox_fields=[
            'tem_elevacao_podium', 'tem_sistema_som', 'tem_microfone',
            'tem_telao_tv', 'tem_iluminacao_cenica', 'tem_backdrop_cenario',
            'tem_bancada_demonstracao', 'tem_espaco_plateia'
        ],
        text_fields=['equipamentos', 'observacoes'],
        number_fields=['metragem']
    ),
    'workshop': AreaConfig(
        model=Workshop,
        checkbox_name='tem_workshop',
        prefix='workshop',
        is_multiple=True,
        checkbox_fields=[
            'tem_bancada_trabalho', 'tem_mesas_participantes', 'tem_cadeiras_bancos',
            'tem_quadro_flipchart', 'tem_projetor_tv', 'tem_pia_bancada_molhada',
            'tem_armario_materiais', 'tem_pontos_eletricos_extras'
        ],
        text_fields=['equipamentos', 'observacoes'],
        number_fields=['metragem']
    ),
    'copa': AreaConfig(
        model=Copa,
        checkbox_name='tem_copa',
        prefix='copa',
        is_multiple=False,
        text_fields=['equipamentos'],
        number_fields=['metragem']
    ),
    'deposito': AreaConfig(
        model=Deposito,
        checkbox_name='tem_deposito',
        prefix='deposito',
        is_multiple=False,
        text_fields=['equipamentos'],
        number_fields=['metragem']
    ),
}


class BriefingAreasProcessor:
    """Processa as áreas do briefing na Etapa 3"""

    def __init__(self, request: HttpRequest, briefing: Briefing):
        self.request = request
        self.briefing = briefing
        self.POST = request.POST

    def process_all_areas(self) -> Dict[str, int]:
        """
        Processa todas as áreas do briefing
        Retorna estatísticas de áreas processadas
        """
        stats = {}

        for area_key, config in AREA_CONFIGS.items():
            # Verificar se essa área foi marcada
            tem_area = self.POST.get(config.checkbox_name) == 'on'

            if not tem_area:
                # Limpar áreas não selecionadas
                config.model.objects.filter(briefing=self.briefing).delete()
                stats[area_key] = 0
            else:
                # Processar áreas selecionadas
                if config.is_multiple:
                    count = self._process_multiple_area(config)
                else:
                    count = self._process_single_area(config)

                stats[area_key] = count

        logger.info(f"Áreas processadas: {stats}")
        return stats

    def _process_multiple_area(self, config: AreaConfig) -> int:
        """Processa áreas que podem ter múltiplas instâncias"""
        # Limpar áreas existentes
        config.model.objects.filter(briefing=self.briefing).delete()

        # Obter número de instâncias
        num_key = f'num_{config.prefix}s' if not config.prefix.endswith('o') else f'num_{config.prefix}es'
        if config.prefix == 'sala_reuniao':
            num_key = 'num_salas_reuniao'
        elif config.prefix == 'area_exposicao':
            num_key = 'num_areas_exposicao'

        num_instances = int(self.POST.get(num_key, 1))
        created_count = 0

        for i in range(num_instances):
            # Verificar se essa instância tem dados
            metragem_key = f'{config.prefix}-{i}-metragem'
            if metragem_key not in self.POST:
                continue

            # Criar nova instância
            instance = config.model(briefing=self.briefing)

            # Processar checkboxes
            for field in config.checkbox_fields:
                field_key = f'{config.prefix}-{i}-{field}'
                setattr(instance, field, self.POST.get(field_key) == 'on')

            # Processar campos de texto
            for field in config.text_fields:
                field_key = f'{config.prefix}-{i}-{field}'
                setattr(instance, field, self.POST.get(field_key, ''))

            # Processar campos numéricos
            for field in config.number_fields:
                field_key = f'{config.prefix}-{i}-{field}'
                value = self.POST.get(field_key, '0')
                try:
                    if field in ['capacidade']:
                        setattr(instance, field, int(value) if value else 0)
                    else:
                        setattr(instance, field, float(value) if value else 0)
                except (ValueError, TypeError):
                    setattr(instance, field, 0)

            instance.save()
            created_count += 1

        return created_count

    def _process_single_area(self, config: AreaConfig) -> int:
        """Processa áreas que têm apenas uma instância (Copa, Depósito)"""
        # Obter ou criar instância
        instance, created = config.model.objects.get_or_create(briefing=self.briefing)

        # Processar campos de texto
        for field in config.text_fields:
            # Para Copa e Depósito, os campos vêm em arrays
            field_values = self.POST.getlist(field)

            # Copa é índice 0, Depósito é índice 1
            index = 0 if config.model == Copa else 1
            value = field_values[index] if len(field_values) > index else ''

            setattr(instance, field, value)

        # Processar campos numéricos
        for field in config.number_fields:
            field_values = self.POST.getlist(field)

            # Copa é índice 0, Depósito é índice 1
            index = 0 if config.model == Copa else 1
            value = field_values[index] if len(field_values) > index else '0'

            try:
                setattr(instance, field, float(value) if value else 0)
            except (ValueError, TypeError):
                setattr(instance, field, 0)

        instance.save()
        return 1

    def get_context_data(self) -> Dict[str, Any]:
        """
        Retorna dados de contexto para renderizar a Etapa 3
        """
        context = {}

        for area_key, config in AREA_CONFIGS.items():
            if config.is_multiple:
                instances = list(config.model.objects.filter(briefing=self.briefing)) or [None]
                context[f'{config.prefix}s' if not config.prefix.endswith('o') else f'{config.prefix}es'] = instances

                # Tratamento especial para nomes no plural
                if config.prefix == 'sala_reuniao':
                    context['salas_reuniao'] = instances
                    context['num_salas_reuniao'] = len(instances)
                elif config.prefix == 'area_exposicao':
                    context['areas_exposicao'] = instances
                    context['num_areas_exposicao'] = len(instances)
                elif config.prefix == 'palco':
                    context['palcos'] = instances
                    context['num_palcos'] = len(instances)
                elif config.prefix == 'workshop':
                    context['workshops'] = instances
                    context['num_workshops'] = len(instances)
            else:
                # Copa e Depósito (instância única)
                instance = config.model.objects.filter(briefing=self.briefing).first()
                context[f'{config.prefix}'] = instance

        return context
