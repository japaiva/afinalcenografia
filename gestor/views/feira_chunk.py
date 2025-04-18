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
    Implementa busca semântica quando possível, com fallback para busca textual.
    """
    feira = get_object_or_404(Feira, pk=feira_id)
    query = request.GET.get('q', '')
    search_mode = request.GET.get('mode', 'smart')  # 'smart', 'semantic', 'text'
    
    # Buscar os chunks da feira inicialmente
    chunks_list = FeiraManualChunk.objects.filter(feira=feira).order_by('posicao')
    
    # Se houver uma query, realizar busca
    if query:
        logger.info(f"Realizando busca com query: '{query}', modo: {search_mode}")
        
        if search_mode in ['smart', 'semantic']:
            try:
                # Importar serviços necessários para busca semântica
                from core.services.rag.embedding_service import EmbeddingService
                from core.utils.pinecone_utils import query_vectors, get_index
                
                # Criar serviço de embedding
                embedding_service = EmbeddingService()
                
                # Gerar embedding para a consulta
                query_embedding = embedding_service.gerar_embedding_consulta(query)
                
                if query_embedding:
                    # Obter namespace para chunks da feira
                    namespace = feira.get_chunks_namespace()
                    
                    # Verificar se o namespace existe e tem vetores
                    index = get_index()
                    if index:
                        # Configurar parâmetros de busca
                        top_k = 10  # Ou obter de parâmetros
                        filter_obj = {"feira_id": {"$eq": str(feira.id)}}
                        
                        # Realizar consulta vetorial
                        results = query_vectors(query_embedding, namespace, top_k, filter_obj)
                        
                        if results:
                            logger.info(f"Busca semântica retornou {len(results)} resultados")
                            
                            # Logar todos os resultados para diagnóstico
                            for i, result in enumerate(results):
                                logger.info(f"Resultado {i+1}: ID={result['id']}, Score={result['score']:.4f}")
                                logger.info(f"Metadados: {result['metadata']}")
                            
                            # Extrair IDs dos chunks encontrados
                            chunk_ids = []
                            alt_chunk_ids = []  # Para busca alternativa por texto

                            # Tentar extrair IDs em diferentes formatos
                            for result in results:
                                try:
                                    # Tentar o formato padrão 'feira_1_chunk_23'
                                    if 'feira_' in result['id'] and '_chunk_' in result['id']:
                                        id_parts = result['id'].split('_chunk_')
                                        if len(id_parts) > 1:
                                            chunk_id = id_parts[1]
                                            try:
                                                chunk_ids.append(int(chunk_id))
                                                logger.info(f"ID extraído: {chunk_id} do resultado: {result['id']}")
                                            except ValueError:
                                                logger.warning(f"Não foi possível converter ID '{chunk_id}' para inteiro")
                                    # Outro formato possível: apenas 'chunk_X'
                                    elif 'chunk_' in result['id']:
                                        id_parts = result['id'].split('chunk_')
                                        if len(id_parts) > 1:
                                            chunk_id = id_parts[1]
                                            try:
                                                chunk_ids.append(int(chunk_id))
                                                logger.info(f"ID extraído (formato alternativo): {chunk_id} do resultado: {result['id']}")
                                            except ValueError:
                                                logger.warning(f"Não foi possível converter ID '{chunk_id}' para inteiro")
                                    else:
                                        logger.warning(f"Formato de ID não reconhecido: {result['id']}")
                                    
                                    # Extrair também o texto dos metadados para busca alternativa
                                    if 'metadata' in result and 'texto' in result['metadata'] and result['metadata']['texto']:
                                        texto_preview = result['metadata']['texto'][:50]
                                        logger.info(f"Texto extraído dos metadados: {texto_preview}")
                                except (ValueError, IndexError) as e:
                                    logger.warning(f"Erro ao extrair ID do chunk: {result['id']}, erro: {str(e)}")
                            
                            # Log de diagnóstico dos IDs extraídos
                            logger.info(f"IDs extraídos do Pinecone: {chunk_ids}")
                            
                            # Verificar quais IDs existem no banco
                            chunks_db = FeiraManualChunk.objects.filter(feira=feira)
                            ids_db = list(chunks_db.values_list('id', flat=True))
                            logger.info(f"IDs disponíveis no banco: {ids_db}")
                            
                            # IDs que existem no Pinecone mas não no banco
                            missing_ids = [id for id in chunk_ids if id not in ids_db]
                            if missing_ids:
                                logger.warning(f"IDs não encontrados no banco: {missing_ids}")
                            
                            # Filtrar chunks com base nos IDs encontrados
                            if chunk_ids:
                                chunks_list = chunks_list.filter(id__in=chunk_ids)
                                
                                # Verificar se encontramos algum chunk
                                if chunks_list.exists():
                                    # Preservar a ordem dos resultados da busca semântica
                                    from django.db.models import Case, When, Value, IntegerField
                                    preserved_order = [When(id=pk, then=Value(i)) for i, pk in enumerate(chunk_ids)]
                                    chunks_list = chunks_list.annotate(
                                        custom_order=Case(*preserved_order, output_field=IntegerField())
                                    ).order_by('custom_order')
                                    
                                    logger.info(f"Chunks ordenados por relevância semântica")
                                    logger.info(f"Busca semântica bem-sucedida, retornando {chunks_list.count()} resultados")
                                else:
                                    logger.warning("Chunks IDs encontrados mas nenhum chunk correspondente no banco")
                                    
                                    # Tentativa de fallback usando texto dos metadados
                                    logger.info("Tentando fallback para busca por texto dos metadados")
                                    for result in results:
                                        if 'metadata' in result and 'texto' in result['metadata'] and result['metadata']['texto']:
                                            texto_preview = result['metadata']['texto'][:50]
                                            chunks_by_text = FeiraManualChunk.objects.filter(
                                                feira=feira, 
                                                texto__startswith=texto_preview
                                            )
                                            if chunks_by_text.exists():
                                                for chunk in chunks_by_text:
                                                    logger.info(f"Chunk encontrado pelo texto: {chunk.id}")
                                                    if chunk.id not in alt_chunk_ids:
                                                        alt_chunk_ids.append(chunk.id)
                                    
                                    # Se encontramos chunks pela busca de texto dos metadados
                                    if alt_chunk_ids:
                                        logger.info(f"Encontrados {len(alt_chunk_ids)} chunks pelo texto dos metadados")
                                        chunks_list = FeiraManualChunk.objects.filter(id__in=alt_chunk_ids)
                                    elif search_mode == 'smart':
                                        # Fallback para busca de texto se não encontramos nada
                                        logger.info("Realizando fallback para busca de texto")
                                        chunks_list = FeiraManualChunk.objects.filter(
                                            feira=feira, 
                                            texto__icontains=query
                                        ).order_by('posicao')
                            else:
                                logger.warning("Nenhum ID de chunk válido encontrado nos resultados semânticos")
                                if search_mode == 'smart':
                                    # Fallback para busca de texto
                                    logger.info("Realizando fallback para busca de texto")
                                    chunks_list = FeiraManualChunk.objects.filter(
                                        feira=feira, 
                                        texto__icontains=query
                                    ).order_by('posicao')
                        else:
                            logger.warning("Busca semântica não retornou resultados")
                            if search_mode == 'smart':
                                # Fallback para busca de texto
                                logger.info("Realizando fallback para busca de texto")
                                chunks_list = FeiraManualChunk.objects.filter(
                                    feira=feira, 
                                    texto__icontains=query
                                ).order_by('posicao')
                    else:
                        logger.error("Não foi possível obter o índice Pinecone")
                        if search_mode == 'smart':
                            # Fallback para busca de texto
                            logger.info("Realizando fallback para busca de texto")
                            chunks_list = FeiraManualChunk.objects.filter(
                                feira=feira, 
                                texto__icontains=query
                            ).order_by('posicao')
                else:
                    logger.error("Não foi possível gerar embedding para a consulta")
                    if search_mode == 'smart':
                        # Fallback para busca de texto
                        logger.info("Realizando fallback para busca de texto")
                        chunks_list = FeiraManualChunk.objects.filter(
                            feira=feira, 
                            texto__icontains=query
                        ).order_by('posicao')
                        
            except Exception as e:
                logger.error(f"Erro na busca semântica: {str(e)}")
                if search_mode == 'smart':
                    # Fallback para busca de texto
                    logger.info("Realizando fallback para busca de texto após exceção")
                    chunks_list = FeiraManualChunk.objects.filter(
                        feira=feira, 
                        texto__icontains=query
                    ).order_by('posicao')
        
        # Se modo for 'text' ou outras opções falharam e estamos em modo 'smart'
        if search_mode == 'text' or (search_mode == 'smart' and not chunks_list.exists()):
            logger.info("Executando busca textual")
            chunks_list = FeiraManualChunk.objects.filter(
                feira=feira, 
                texto__icontains=query
            ).order_by('posicao')
    
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
    
    # Adicionar modo de busca ao contexto
    context = {
        'feira': feira,
        'chunks': chunks,
        'chunks_count': chunks_count,
        'query': query,
        'next_position': next_position,
        'search_mode': search_mode
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
