# gestor/views/feira_chunk.py

import json
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import JsonResponse
from django.db.models import Max
from django.views.decorators.http import require_POST, require_GET

from core.models import Feira, FeiraManualChunk
from core.services.rag_service import RAGService

logger = logging.getLogger(__name__)

@login_required
def feira_blocos_list(request, feira_id):
    """
    Exibe a lista de blocos do manual de uma feira, com opções de pesquisa e paginação.
    """
    feira = get_object_or_404(Feira, pk=feira_id)
    query = request.GET.get('q', '')
    
    # Buscar os chunks da feira
    chunks_list = FeiraManualChunk.objects.filter(feira=feira).order_by('posicao')
    
    # Se houver uma query, filtrar pelos blocos que contêm o texto
    if query:
        chunks_list = chunks_list.filter(texto__icontains=query)
    
    # Contagem total
    chunks_count = chunks_list.count()
    
    # Calcular próxima posição disponível para novos blocos
    next_position = chunks_list.aggregate(Max('posicao')).get('posicao__max', 0)
    if next_position is not None:
        next_position += 1
    else:
        next_position = 0
    
    # Paginação
    paginator = Paginator(chunks_list, 10)  # 10 chunks por página
    page = request.GET.get('page')
    
    try:
        chunks = paginator.page(page)
    except PageNotAnInteger:
        chunks = paginator.page(1)
    except EmptyPage:
        chunks = paginator.page(paginator.num_pages)
    
    context = {
        'feira': feira,
        'chunks': chunks,
        'chunks_count': chunks_count,
        'query': query,
        'next_position': next_position
    }
    
    return render(request, 'gestor/feira_blocos_list.html', context)

@login_required
@require_GET
def feira_chunk_get(request):
    """
    Retorna os dados de um chunk específico para edição.
    """
    chunk_id = request.GET.get('id')
    
    if not chunk_id:
        return JsonResponse({
            'success': False,
            'message': 'ID não fornecido.'
        })
    
    try:
        chunk = get_object_or_404(FeiraManualChunk, pk=chunk_id)
        
        data = {
            'texto': chunk.texto,
            'pagina': chunk.pagina,
            'posicao': chunk.posicao,
            'pinecone_id': chunk.pinecone_id
        }
        
        return JsonResponse({
            'success': True,
            'chunk': data
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        })

@login_required
@require_POST
def feira_chunk_update(request):
    """
    Atualiza um chunk existente.
    """
    try:
        data = json.loads(request.body)
        chunk_id = data.get('chunk_id')
        
        if not chunk_id:
            return JsonResponse({
                'success': False,
                'message': 'ID não fornecido.'
            })
        
        chunk = get_object_or_404(FeiraManualChunk, pk=chunk_id)
        
        # Atualizar dados do chunk
        chunk.texto = data.get('texto', chunk.texto)
        chunk.pagina = data.get('pagina')
        chunk.posicao = data.get('posicao', chunk.posicao)
        chunk.save()
        
        # Verificar se precisa regenerar o vetor
        regenerate_vector = data.get('regenerate_vector', False)
        if regenerate_vector and chunk.pinecone_id:
            try:
                # Excluir vetor antigo se existir
                from core.utils.pinecone_utils import get_index, delete_vectors
                index = get_index()
                if index:
                    namespace = f"feira_{chunk.feira.id}"
                    delete_vectors([chunk.pinecone_id], namespace)
                
                # Gerar novo embedding
                agente_nome = data.get('agente_nome', 'Embedding Generator')
                rag_service = RAGService(agent_name=agente_nome)
                
                # Gerar embedding para o texto atualizado
                embedding = rag_service.gerar_embedding_para_texto(chunk.texto)
                
                if embedding:
                    # Metadados para o vetor
                    metadata = {
                        'texto': chunk.texto[:1000],  # Limitando o tamanho
                        'pagina': str(chunk.pagina) if chunk.pagina else None,
                        'posicao': str(chunk.posicao),
                        'feira_id': str(chunk.feira.id),
                        'feira_nome': chunk.feira.nome
                    }
                    
                    # Armazenar no banco vetorial
                    from core.utils.pinecone_utils import upsert_vectors
                    upsert_vectors([(chunk.pinecone_id, embedding, metadata)], namespace)
            except Exception as e:
                # Logar erro mas não impedir a atualização
                print(f"Erro ao regenerar vetor: {str(e)}")
        
        return JsonResponse({
            'success': True,
            'message': 'Bloco atualizado com sucesso.'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        })

@login_required
@require_POST
def feira_chunk_delete(request):
    """
    Exclui um chunk e seu vetor correspondente.
    """
    try:
        data = json.loads(request.body)
        chunk_id = data.get('chunk_id')
        
        if not chunk_id:
            return JsonResponse({
                'success': False,
                'message': 'ID não fornecido.'
            })
        
        chunk = get_object_or_404(FeiraManualChunk, pk=chunk_id)
        
        # Excluir o vetor se existir
        if chunk.pinecone_id:
            try:
                from core.utils.pinecone_utils import get_index, delete_vectors
                index = get_index()
                if index:
                    namespace = f"feira_{chunk.feira.id}"
                    delete_vectors([chunk.pinecone_id], namespace)
            except Exception as e:
                # Logar erro mas continuar com a exclusão
                print(f"Erro ao excluir vetor: {str(e)}")
        
        # Excluir o chunk
        chunk.delete()
        
        return JsonResponse({
            'success': True,
            'message': 'Bloco excluído com sucesso.'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        })

@login_required
@require_POST
def feira_chunk_add(request, feira_id):
    """
    Adiciona um novo chunk e gera seu vetor.
    """
    feira = get_object_or_404(Feira, pk=feira_id)
    
    try:
        data = json.loads(request.body)
        texto = data.get('texto', '').strip()
        pagina = data.get('pagina')
        posicao = data.get('posicao')
        
        # Validação básica
        if not texto:
            return JsonResponse({
                'success': False,
                'message': 'O texto do bloco é obrigatório.'
            }, status=400)
        
        # Criar o chunk
        chunk = FeiraManualChunk.objects.create(
            feira=feira,
            texto=texto,
            pagina=pagina,
            posicao=posicao
        )
        
        # Gerar ID para o Pinecone
        pinecone_id = f"feira_{feira.id}_chunk_{chunk.id}"
        chunk.pinecone_id = pinecone_id
        chunk.save(update_fields=['pinecone_id'])
        
        # Gerar embedding se possível
        try:
            agente_nome = data.get('agente_nome', 'Embedding Generator')
            rag_service = RAGService(agent_name=agente_nome)
            
            # Gerar embedding para o texto
            embedding = rag_service.gerar_embedding_para_texto(texto)
            
            if embedding:
                # Metadados para o vetor
                metadata = {
                    'texto': texto[:1000],  # Limitando o tamanho
                    'pagina': str(pagina) if pagina else None,
                    'posicao': str(posicao),
                    'feira_id': str(feira.id),
                    'feira_nome': feira.nome
                }
                
                # Armazenar no banco vetorial
                from core.utils.pinecone_utils import upsert_vectors
                namespace = f"feira_{feira.id}"
                upsert_vectors([(pinecone_id, embedding, metadata)], namespace)
        except Exception as e:
            # Logar erro mas não impedir a criação do chunk
            print(f"Erro ao gerar embedding para o novo chunk: {str(e)}")
        
        return JsonResponse({
            'success': True,
            'message': 'Bloco adicionado com sucesso.',
            'chunk_id': chunk.id
        })
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)

@login_required
@require_POST
def feira_chunk_regenerate_vector(request):
    """
    Regenera o vetor de um chunk específico.
    """
    try:
        data = json.loads(request.body)
        chunk_id = data.get('chunk_id')
        
        if not chunk_id:
            return JsonResponse({
                'success': False,
                'message': 'ID não fornecido.'
            })
        
        chunk = get_object_or_404(FeiraManualChunk, pk=chunk_id)
        
        # Excluir vetor antigo se existir
        if chunk.pinecone_id:
            try:
                from core.utils.pinecone_utils import get_index, delete_vectors
                index = get_index()
                if index:
                    namespace = f"feira_{chunk.feira.id}"
                    delete_vectors([chunk.pinecone_id], namespace)
            except Exception as e:
                # Logar erro mas continuar
                print(f"Erro ao excluir vetor antigo: {str(e)}")
        
        # Gerar novo embedding
        try:
            agente_nome = data.get('agente_nome', 'Embedding Generator')
            rag_service = RAGService(agent_name=agente_nome)
            
            # Gerar embedding para o texto
            embedding = rag_service.gerar_embedding_para_texto(chunk.texto)
            
            if embedding:
                # Metadados para o vetor
                metadata = {
                    'texto': chunk.texto[:1000],  # Limitando o tamanho
                    'pagina': str(chunk.pagina) if chunk.pagina else None,
                    'posicao': str(chunk.posicao),
                    'feira_id': str(chunk.feira.id),
                    'feira_nome': chunk.feira.nome
                }
                
                # Armazenar no banco vetorial
                from core.utils.pinecone_utils import upsert_vectors
                namespace = f"feira_{chunk.feira.id}"
                upsert_vectors([(chunk.pinecone_id, embedding, metadata)], namespace)
                
                return JsonResponse({
                    'success': True,
                    'message': 'Vetor regenerado com sucesso.'
                })
            else:
                return JsonResponse({
                    'success': False,
                    'message': 'Não foi possível gerar o embedding.'
                })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Erro ao regenerar vetor: {str(e)}'
            })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        })
