# gestor/views/feira_chunk.py

# feira_blocos_list 
# feira_chunk_get          
# feira_chunk_update  
# feira_chunk_delete        
# feira_chunk_add           
# feira_chunk_regenerate_vector 

import json
import logging

from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import JsonResponse
from django.db.models import Max, Case, When, Value, IntegerField
from django.views.decorators.http import require_POST, require_GET

from core.models import Feira, FeiraManualChunk
from core.services.rag_service import RAGService

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# LISTAGEM & BUSCA
# ---------------------------------------------------------------------------
@login_required
def feira_blocos_list(request, feira_id):
    """
    Lista os blocos (chunks) do manual de uma feira.
    Suporta busca semântica (Pinecone + embeddings) com fallback para busca textual.
    """
    feira = get_object_or_404(Feira, pk=feira_id)
    query = request.GET.get('q', '').strip()
    search_mode = request.GET.get('mode', 'smart')  # 'smart', 'semantic' ou 'text'

    chunks_list = FeiraManualChunk.objects.filter(feira=feira).order_by('posicao')

    # -----------------------------------------------------------------------
    # BUSCA
    # -----------------------------------------------------------------------
    if query:
        logger.info(f"[Chunks] Busca '{query}' (modo {search_mode})")

        def fallback_text():
            return FeiraManualChunk.objects.filter(
                feira=feira, texto__icontains=query
            ).order_by('posicao')

        if search_mode in ['smart', 'semantic']:
            try:
                from core.services.rag.embedding_service import EmbeddingService
                from core.utils.pinecone_utils import query_vectors, get_index

                embedding_service = EmbeddingService()
                query_emb = embedding_service.gerar_embedding_consulta(query)

                if query_emb:
                    index = get_index()
                    if index:
                        results = query_vectors(
                            query_emb,
                            namespace=feira.get_chunks_namespace(),
                            top_k=10,
                            filter={"feira_id": {"$eq": str(feira.id)}},
                        )

                        if results:
                            chunk_ids = []
                            for r in results:
                                # formatos aceitos: feira_1_chunk_23  ou  chunk_23
                                if "_chunk_" in r["id"]:
                                    try:
                                        chunk_ids.append(int(r["id"].split("_chunk_")[1]))
                                    except ValueError:
                                        pass
                                elif r["id"].startswith("chunk_"):
                                    try:
                                        chunk_ids.append(int(r["id"].split("chunk_")[1]))
                                    except ValueError:
                                        pass

                            if chunk_ids:
                                chunks_list = chunks_list.filter(id__in=chunk_ids)
                                preserved = [
                                    When(id=pk, then=Value(i))
                                    for i, pk in enumerate(chunk_ids)
                                ]
                                chunks_list = chunks_list.annotate(
                                    custom_order=Case(*preserved, output_field=IntegerField())
                                ).order_by("custom_order")
                            else:
                                chunks_list = fallback_text()
                        else:
                            chunks_list = fallback_text()
                    else:
                        chunks_list = fallback_text()
                else:
                    chunks_list = fallback_text()
            except Exception as e:
                logger.error(f"[Chunks] Erro busca semântica: {e}")
                chunks_list = fallback_text()

        if search_mode == "text" or (search_mode == "smart" and not chunks_list.exists()):
            chunks_list = fallback_text()

    # -----------------------------------------------------------------------
    # PAGINAÇÃO
    # -----------------------------------------------------------------------
    paginator = Paginator(chunks_list, 10)
    page = request.GET.get('page', 1)
    try:
        chunks = paginator.page(page)
    except PageNotAnInteger:
        chunks = paginator.page(1)
    except EmptyPage:
        chunks = paginator.page(paginator.num_pages)

    context = {
        "feira": feira,
        "chunks": chunks,
        "chunks_count": chunks_list.count(),
        "query": query,
        "search_mode": search_mode,
        "next_position": (chunks_list.aggregate(Max('posicao')).get('posicao__max') or -1) + 1,
    }
    return render(request, "gestor/feira_blocos_list.html", context)


# ---------------------------------------------------------------------------
# CRUD CHUNK – GET / UPDATE / DELETE / ADD / REGENERATE VECTOR
# ---------------------------------------------------------------------------
@login_required
@require_GET
def feira_chunk_get(request):
    """Retorna JSON com os dados de um chunk para edição."""
    chunk_id = request.GET.get('id')
    if not chunk_id:
        return JsonResponse({"success": False, "message": "ID não fornecido."})

    chunk = get_object_or_404(FeiraManualChunk, pk=chunk_id)
    return JsonResponse(
        {
            "success": True,
            "chunk": {
                "texto": chunk.texto,
                "pagina": chunk.pagina,
                "posicao": chunk.posicao,
                "pinecone_id": chunk.pinecone_id,
            },
        }
    )


@login_required
@require_POST
def feira_chunk_update(request):
    """Atualiza um chunk existente; opcionalmente regenera seu vetor."""
    try:
        data = json.loads(request.body)
        chunk = get_object_or_404(FeiraManualChunk, pk=data.get('chunk_id'))

        # Atualiza campos
        chunk.texto = data.get('texto', chunk.texto)
        chunk.pagina = data.get('pagina')
        chunk.posicao = data.get('posicao', chunk.posicao)
        chunk.save()

        if data.get('regenerate_vector') and chunk.pinecone_id:
            _regenerate_vector(chunk, agente_nome=data.get('agente_nome'))

        return JsonResponse({"success": True, "message": "Bloco atualizado."})
    except Exception as e:
        return JsonResponse({"success": False, "message": str(e)}, status=500)


@login_required
@require_POST
def feira_chunk_delete(request):
    """Exclui um chunk e seu vetor."""
    try:
        data = json.loads(request.body)
        chunk = get_object_or_404(FeiraManualChunk, pk=data.get('chunk_id'))

        _delete_vector(chunk)
        chunk.delete()

        return JsonResponse({"success": True, "message": "Bloco excluído."})
    except Exception as e:
        return JsonResponse({"success": False, "message": str(e)}, status=500)


@login_required
@require_POST
def feira_chunk_add(request, feira_id):
    """Cria um novo chunk para a feira e gera seu vetor."""
    feira = get_object_or_404(Feira, pk=feira_id)
    try:
        data = json.loads(request.body)
        texto = data.get('texto', '').strip()
        if not texto:
            return JsonResponse({"success": False, "message": "Texto é obrigatório."}, status=400)

        chunk = FeiraManualChunk.objects.create(
            feira=feira,
            texto=texto,
            pagina=data.get('pagina'),
            posicao=data.get('posicao'),
        )
        chunk.pinecone_id = f"feira_{feira.id}_chunk_{chunk.id}"
        chunk.save(update_fields=['pinecone_id'])

        _regenerate_vector(chunk, agente_nome=data.get('agente_nome'))
        return JsonResponse({"success": True, "message": "Bloco criado.", "chunk_id": chunk.id})
    except Exception as e:
        return JsonResponse({"success": False, "message": str(e)}, status=500)


@login_required
@require_POST
def feira_chunk_regenerate_vector(request):
    """Regenera o vetor de um chunk específico."""
    try:
        data = json.loads(request.body)
        chunk = get_object_or_404(FeiraManualChunk, pk=data.get('chunk_id'))

        _regenerate_vector(chunk, agente_nome=data.get('agente_nome'))
        return JsonResponse({"success": True, "message": "Vetor regenerado."})
    except Exception as e:
        return JsonResponse({"success": False, "message": str(e)}, status=500)


# ---------------------------------------------------------------------------
# HELPERS (internos)
# ---------------------------------------------------------------------------
def _delete_vector(chunk):
    """Exclui o vetor do Pinecone (ignora erros)."""
    if not chunk.pinecone_id:
        return
    try:
        from core.utils.pinecone_utils import get_index, delete_vectors

        index = get_index()
        if index:
            delete_vectors([chunk.pinecone_id], namespace=f"feira_{chunk.feira.id}")
    except Exception as e:
        logger.warning(f"[Chunks] Falha ao excluir vetor: {e}")


def _regenerate_vector(chunk, *, agente_nome="Embedding Generator"):
    """Exclui o vetor antigo (se houver) e gera um novo embedding."""
    _delete_vector(chunk)
    try:
        rag_service = RAGService(agent_name=agente_nome or "Embedding Generator")
        embedding = rag_service.gerar_embedding_para_texto(chunk.texto)
        if not embedding:
            logger.warning(f"[Chunks] Embedding não gerado para chunk {chunk.id}")
            return

        from core.utils.pinecone_utils import upsert_vectors

        metadata = {
            "texto": chunk.texto[:1000],
            "pagina": str(chunk.pagina) if chunk.pagina else None,
            "posicao": str(chunk.posicao),
            "feira_id": str(chunk.feira.id),
            "feira_nome": chunk.feira.nome,
        }
        upsert_vectors(
            [(chunk.pinecone_id, embedding, metadata)],
            namespace=f"feira_{chunk.feira.id}",
        )
    except Exception as e:
        logger.error(f"[Chunks] Erro ao regenerar vetor: {e}")