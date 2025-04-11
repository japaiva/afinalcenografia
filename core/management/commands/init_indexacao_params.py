from django.core.management.base import BaseCommand
from core.models import ParametroIndexacao

class Command(BaseCommand):
    help = 'Cria parâmetros iniciais de indexação'

    def handle(self, *args, **kwargs):
        # Parâmetros de Chunking
        ParametroIndexacao.objects.get_or_create(
            nome='CHUNK_SIZE',
            defaults={
                'descricao': 'Tamanho aproximado de cada chunk em tokens',
                'valor': '1000',
                'tipo': 'int',
                'categoria': 'chunk'
            }
        )
        ParametroIndexacao.objects.get_or_create(
            nome='CHUNK_OVERLAP',
            defaults={
                'descricao': 'Quantidade de sobreposição entre chunks em tokens',
                'valor': '100',
                'tipo': 'int',
                'categoria': 'chunk'
            }
        )
        ParametroIndexacao.objects.get_or_create(
            nome='CHUNKING_STRATEGY',
            defaults={
                'descricao': 'Estratégia de divisão ("page" ou "document")',
                'valor': 'page',
                'tipo': 'str',
                'categoria': 'chunk'
            }
        )
        # Parâmetros de Embeddings
        ParametroIndexacao.objects.get_or_create(
            nome='EMBEDDING_MODEL',
            defaults={
                'descricao': 'Modelo de embedding da OpenAI',
                'valor': 'text-embedding-ada-002',
                'tipo': 'str',
                'categoria': 'embedding'
            }
        )
        ParametroIndexacao.objects.get_or_create(
            nome='EMBEDDING_DIMENSION',
            defaults={
                'descricao': 'Dimensionalidade do embedding (1536 para ada-002)',
                'valor': '1536',
                'tipo': 'int',
                'categoria': 'embedding'
            }
        )
        # Parâmetros do Pinecone
        ParametroIndexacao.objects.get_or_create(
            nome='PINECONE_INDEX_NAME',
            defaults={
                'descricao': 'Nome do índice no Pinecone',
                'valor': 'afinal-feira-index',
                'tipo': 'str',
                'categoria': 'pinecone'
            }
        )
        ParametroIndexacao.objects.get_or_create(
            nome='PINECONE_METRIC',
            defaults={
                'descricao': 'Métrica de similaridade usada no Pinecone',
                'valor': 'cosine',
                'tipo': 'str',
                'categoria': 'pinecone'
            }
        )
        # Parâmetros de Busca
        ParametroIndexacao.objects.get_or_create(
            nome='SEARCH_TOP_K',
            defaults={
                'descricao': 'Número de resultados a retornar em buscas',
                'valor': '3',
                'tipo': 'int',
                'categoria': 'search'
            }
        )
        ParametroIndexacao.objects.get_or_create(
            nome='SEARCH_THRESHOLD',
            defaults={
                'descricao': 'Limiar mínimo de similaridade para resultados válidos',
                'valor': '0.7',
                'tipo': 'float',
                'categoria': 'search'
            }
        )
        self.stdout.write(self.style.SUCCESS('Parâmetros de indexação iniciais criados com sucesso!'))