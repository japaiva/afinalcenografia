# gestor/views/feira_qa.py

# - feira_qa_list
# - feira_qa_get
# - feira_qa_update
# - feira_qa_delete
# - feira_qa_regenerate_single
# - feira_qa_stats
# - feira_qa_regenerate
# - process_qa_background
# - feira_qa_progress
# - feira_qa_add

import json
import logging
import threading
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.db.models import Q

from core.models import Feira, FeiraManualChunk, FeiraManualQA, Agente
from core.tasks import pesquisar_manual_feira
from core.services.qa_generator import QAGenerator, process_all_chunks_for_feira
from core.services.rag_service import RAGService


logger = logging.getLogger(__name__)

@login_required
def feira_qa_list(request, feira_id):
    feira = get_object_or_404(Feira, pk=feira_id)
    processando = feira.qa_processamento_status == 'processando'
    query = request.GET.get('q', '')
    search_mode = request.GET.get('mode', 'smart')  # 'smart', 'semantic', 'text'
    
    qa_pairs_list = FeiraManualQA.objects.filter(feira=feira).order_by('-created_at')
    
    # Se houver uma query, realizar busca
    if query:
        logger.info(f"Realizando busca QA com query: '{query}', modo: {search_mode}")
        
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
                    # Obter namespace para QAs da feira
                    # Obter namespace para chunks da feira
                    namespace = feira.get_qa_namespace()
                    
                    # Verificar se o índice existe e tem vetores
                    index = get_index()
                    if index:
                        # Configurar parâmetros de busca
                        top_k = 10  
                        filter_obj = {"feira_id": {"$eq": str(feira.id)}}
                        
                        # Realizar consulta vetorial
                        results = query_vectors(query_embedding, namespace, top_k, filter_obj)
                        
                        if results:
                            logger.info(f"Busca semântica retornou {len(results)} resultados")
                            
                            # Extrair IDs dos QAs encontrados
                            qa_ids = []
                            
                            for result in results:
                                try:
                                    # Tentar extrair o ID do QA diretamente do ID do vetor
                                    if 'qa_' in result['id']:
                                        qa_id = result['id'].replace('qa_', '')
                                        try:
                                            qa_ids.append(int(qa_id))
                                            logger.info(f"ID extraído: {qa_id} do resultado: {result['id']}")
                                        except ValueError:
                                            logger.warning(f"Não foi possível converter ID '{qa_id}' para inteiro")
                                    
                                    # Alternativamente, verificar nos metadados
                                    elif 'metadata' in result and 'qa_id' in result['metadata']:
                                        qa_id = result['metadata']['qa_id']
                                        try:
                                            qa_ids.append(int(qa_id))
                                            logger.info(f"ID extraído dos metadados: {qa_id}")
                                        except ValueError:
                                            logger.warning(f"Não foi possível converter ID dos metadados '{qa_id}' para inteiro")
                                except Exception as e:
                                    logger.warning(f"Erro ao extrair ID do QA: {result['id']}, erro: {str(e)}")
                            
                            # Log de diagnóstico dos IDs extraídos
                            logger.info(f"IDs extraídos do Pinecone: {qa_ids}")
                            
                            # Filtrar QAs com base nos IDs encontrados
                            if qa_ids:
                                qa_pairs_list = qa_pairs_list.filter(id__in=qa_ids)
                                
                                # Verificar se encontramos algum QA
                                if qa_pairs_list.exists():
                                    # Preservar a ordem dos resultados da busca semântica
                                    from django.db.models import Case, When, Value, IntegerField
                                    preserved_order = [When(id=pk, then=Value(i)) for i, pk in enumerate(qa_ids)]
                                    qa_pairs_list = qa_pairs_list.annotate(
                                        custom_order=Case(*preserved_order, output_field=IntegerField())
                                    ).order_by('custom_order')
                                    
                                    logger.info(f"QAs ordenados por relevância semântica")
                                    logger.info(f"Busca semântica bem-sucedida, retornando {qa_pairs_list.count()} resultados")
                                else:
                                    logger.warning("QA IDs encontrados mas nenhum QA correspondente no banco")
                                    if search_mode == 'smart':
                                        # Fallback para busca de texto
                                        logger.info("Realizando fallback para busca de texto")
                                        qa_pairs_list = FeiraManualQA.objects.filter(
                                            feira=feira
                                        ).filter(
                                            Q(question__icontains=query) | 
                                            Q(answer__icontains=query) | 
                                            Q(similar_questions__contains=query)
                                        ).order_by('-created_at')
                            else:
                                logger.warning("Nenhum ID de QA válido encontrado nos resultados semânticos")
                                if search_mode == 'smart':
                                    # Fallback para busca de texto
                                    logger.info("Realizando fallback para busca de texto")
                                    qa_pairs_list = FeiraManualQA.objects.filter(
                                        feira=feira
                                    ).filter(
                                        Q(question__icontains=query) | 
                                        Q(answer__icontains=query) | 
                                        Q(similar_questions__contains=query)
                                    ).order_by('-created_at')
                        else:
                            logger.warning("Busca semântica não retornou resultados")
                            if search_mode == 'smart':
                                # Fallback para busca de texto
                                logger.info("Realizando fallback para busca de texto")
                                qa_pairs_list = FeiraManualQA.objects.filter(
                                    feira=feira
                                ).filter(
                                    Q(question__icontains=query) | 
                                    Q(answer__icontains=query) | 
                                    Q(similar_questions__contains=query)
                                ).order_by('-created_at')
                    else:
                        logger.error("Não foi possível obter o índice Pinecone")
                        if search_mode == 'smart':
                            # Fallback para busca de texto
                            logger.info("Realizando fallback para busca de texto")
                            qa_pairs_list = FeiraManualQA.objects.filter(
                                feira=feira
                            ).filter(
                                Q(question__icontains=query) | 
                                Q(answer__icontains=query) | 
                                Q(similar_questions__contains=query)
                            ).order_by('-created_at')
                else:
                    logger.error("Não foi possível gerar embedding para a consulta")
                    if search_mode == 'smart':
                        # Fallback para busca de texto
                        logger.info("Realizando fallback para busca de texto")
                        qa_pairs_list = FeiraManualQA.objects.filter(
                            feira=feira
                        ).filter(
                            Q(question__icontains=query) | 
                            Q(answer__icontains=query) | 
                            Q(similar_questions__contains=query)
                        ).order_by('-created_at')
                        
            except Exception as e:
                logger.error(f"Erro na busca semântica: {str(e)}")
                if search_mode == 'smart':
                    # Fallback para busca de texto
                    logger.info("Realizando fallback para busca de texto após exceção")
                    qa_pairs_list = FeiraManualQA.objects.filter(
                        feira=feira
                    ).filter(
                        Q(question__icontains=query) | 
                        Q(answer__icontains=query) | 
                        Q(similar_questions__contains=query)
                    ).order_by('-created_at')
        
        # Se modo for 'text' ou outras opções falharam e estamos em modo 'smart'
        if search_mode == 'text' or (search_mode == 'smart' and not qa_pairs_list.exists()):
            logger.info("Executando busca textual")
            qa_pairs_list = FeiraManualQA.objects.filter(
                feira=feira
            ).filter(
                Q(question__icontains=query) | 
                Q(answer__icontains=query) | 
                Q(similar_questions__contains=query)
            ).order_by('-created_at')
    
    paginator = Paginator(qa_pairs_list, 10)
    page = request.GET.get('page')
    
    try:
        qa_pairs = paginator.page(page)
    except PageNotAnInteger:
        qa_pairs = paginator.page(1)
    except EmptyPage:
        qa_pairs = paginator.page(paginator.num_pages)
    
    qa_count = qa_pairs_list.count()
    
    agentes = Agente.objects.filter(ativo=True)
    
    context = {
        'feira': feira,
        'qa_pairs': qa_pairs,
        'qa_count': qa_count,
        'query': query,
        'search_mode': search_mode,
        'processando': processando,
        'agentes': agentes
    }
    
    return render(request, 'gestor/feira_qa_list.html', context)
    
@login_required
@require_GET
def feira_qa_get(request):
    qa_id = request.GET.get('id')
    
    if not qa_id:
        return JsonResponse({
            'success': False,
            'message': 'ID não fornecido.'
        })
    
    try:
        qa = get_object_or_404(FeiraManualQA, pk=qa_id)
        
        data = {
            'question': qa.question,
            'answer': qa.answer,
            'context': qa.context,
            'similar_questions': qa.similar_questions,
        }
        
        return JsonResponse({
            'success': True,
            'qa': data
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        })


@login_required
@require_POST
def feira_qa_update(request):
    try:
        data = json.loads(request.body)
        qa_id = data.get('qa_id')
        
        if not qa_id:
            return JsonResponse({
                'success': False,
                'message': 'ID não fornecido.'
            })
        
        qa = get_object_or_404(FeiraManualQA, pk=qa_id)
        
        # Guardar valores antigos para verificar se houve alteração
        old_question = qa.question
        old_answer = qa.answer
        
        # Atualizar com novos valores
        qa.question = data.get('question', qa.question)
        qa.answer = data.get('answer', qa.answer)
        qa.context = data.get('context', qa.context)
        
        # Processar perguntas similares
        similar_questions = data.get('similar_questions', '')
        if isinstance(similar_questions, str):
            # Converter texto em lista, cada linha como um item
            similar_questions = [sq.strip() for sq in similar_questions.split('\n') if sq.strip()]
        qa.similar_questions = similar_questions
        
        qa.save()
        
        # Verificar se conteúdo relevante para busca foi alterado
        conteudo_alterado = (
            old_question != qa.question or 
            old_answer != qa.answer
        )
        
        # Se o conteúdo relevante foi alterado, regenerar embedding
        if conteudo_alterado:
            try:
                # Obter o agente para embedding configurado na interface ou usar o padrão
                agente_nome = data.get('agente_nome', 'Embedding Generator')
                rag_service = RAGService(agent_name=agente_nome)
                
                # Gerar novo embedding
                embedding = rag_service.gerar_embeddings_qa(qa)
                
                if embedding:
                    # Atualizar ou criar o vetor no banco vetorial
                    embedding_id = qa.embedding_id or f"qa_{qa.id}"
                    
                    # Preparar metadados
                    metadata = {
                        'q': qa.question,
                        'a': qa.answer,
                        't': qa.context,
                        'sq': qa.similar_questions,
                        'feira_id': str(qa.feira.id),
                        'feira_nome': qa.feira.nome,
                        'qa_id': str(qa.id)
                    }
                    
                    # Armazenar no banco vetorial
                    from core.utils.pinecone_utils import upsert_vectors
                    namespace = f"feira_{qa.feira.id}"
                    upsert_vectors([(embedding_id, embedding, metadata)], namespace)
                    
                    # Atualizar ID de embedding no registro
                    qa.embedding_id = embedding_id
                    qa.save(update_fields=['embedding_id'])
                    
                    logger.info(f"Embedding atualizado para QA #{qa.id}")
            except Exception as e:
                logger.error(f"Erro ao atualizar embedding: {str(e)}")
                # Não impedimos a atualização do QA se falhar o embedding
        
        return JsonResponse({
            'success': True,
            'message': 'Pergunta e resposta atualizada com sucesso.'
        })
    except Exception as e:
        logger.error(f"Erro na atualização de QA: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': str(e)
        })

@login_required
@require_POST
def feira_qa_delete(request):
    try:
        data = json.loads(request.body)
        qa_id = data.get('qa_id')
        
        if not qa_id:
            return JsonResponse({
                'success': False,
                'message': 'ID não fornecido.'
            })
        
        qa = get_object_or_404(FeiraManualQA, pk=qa_id)
        
        # Excluir do banco vetorial se houver ID de embedding
        if hasattr(qa, 'embedding_id') and qa.embedding_id:
            try:
                from core.utils.pinecone_utils import get_index
                index = get_index()
                if index:
                    namespace = f"feira_{qa.feira.id}"
                    index.delete(ids=[qa.embedding_id], namespace=namespace)
            except Exception as e:
                logger.error(f"Erro ao excluir vetor: {str(e)}")
                # Continuar mesmo se falhar a exclusão do vetor
        
        # Excluir o QA
        qa.delete()
        
        return JsonResponse({
            'success': True,
            'message': 'Pergunta e resposta excluída com sucesso.'
        })
    except FeiraManualQA.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Pergunta e resposta não encontrada.'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        })

@login_required
@require_POST
def feira_qa_regenerate_single(request):
    try:
        data = json.loads(request.body)
        qa_id = data.get('qa_id')
        agente_nome = data.get('agente_nome', 'Gerador de Q&A')  # Nome do agente a ser usado
        
        if not qa_id:
            return JsonResponse({
                'success': False,
                'message': 'ID não fornecido.'
            })
        
        qa = get_object_or_404(FeiraManualQA, pk=qa_id)
        feira = qa.feira
        
        if not qa.chunk_id:
            return JsonResponse({
                'success': False,
                'message': 'Não é possível regenerar: ID do chunk original não disponível.'
            })
        
        try:
            chunk = FeiraManualChunk.objects.get(id=qa.chunk_id)
        except FeiraManualChunk.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Chunk original não encontrado.'
            })
        
        # Verificar se o agente existe
        try:
            Agente.objects.get(nome=agente_nome, ativo=True)
        except Agente.DoesNotExist:
            # Fallback para agente padrão
            agente_nome = 'Gerador de Q&A'
            try:
                Agente.objects.get(nome=agente_nome, ativo=True)
            except Agente.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'message': 'Agente para geração de Q&A não encontrado.'
                })
        
        # Usar o QA Generator com o agente especificado
        generator = QAGenerator(agent_name=agente_nome)
        new_qa_pairs = generator.generate_qa_from_chunk(chunk)
        
        if not new_qa_pairs:
            return JsonResponse({
                'success': False,
                'message': 'Não foi possível gerar novas perguntas e respostas.'
            })
        
        new_qa = new_qa_pairs[0]
        
        # Atualizar o QA existente
        qa.question = new_qa.get('q', qa.question)
        qa.answer = new_qa.get('a', qa.answer)
        qa.context = new_qa.get('t', qa.context)
        qa.similar_questions = new_qa.get('sq', qa.similar_questions)
        qa.save()
        
        # Regenerar embedding se necessário
        try:
            rag_service = RAGService(agent_name='Embedding Generator')
            embedding = rag_service.gerar_embeddings_qa(qa)
            if embedding:
                rag_service._store_in_vector_db(qa, embedding)
        except Exception as e:
            logger.error(f"Erro ao regenerar embedding: {str(e)}")
            # Não impedir o sucesso da regeneração se o embedding falhar
        
        return JsonResponse({
            'success': True,
            'message': 'Pergunta e resposta regenerada com sucesso.',
            'qa': {
                'question': qa.question,
                'answer': qa.answer,
                'context': qa.context,
                'similar_questions': qa.similar_questions
            }
        })
    except Exception as e:
        logger.error(f"Erro ao regenerar QA: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': str(e)
        })

@login_required
def feira_qa_stats(request, feira_id):
    """
    Obtém estatísticas sobre os QAs de uma feira.
    """
    feira = get_object_or_404(Feira, pk=feira_id)
    
    try:
        qa_pairs = FeiraManualQA.objects.filter(feira=feira)
        
        total_qa = qa_pairs.count()
        
        # Se não houver QAs, retornar estatísticas vazias
        if total_qa == 0:
            return JsonResponse({
                'success': True,
                'stats': {
                    'total_qa': 0,
                    'qa_com_embedding': 0,
                    'qa_sem_embedding': 0,
                    'percentual_embedding': 0,
                    'tamanho_medio_pergunta': 0,
                    'tamanho_medio_resposta': 0
                }
            })
        
        # Contar QAs com embedding
        qa_com_embedding = qa_pairs.exclude(embedding_id__isnull=True).exclude(embedding_id='').count()
        qa_sem_embedding = total_qa - qa_com_embedding
        percentual_embedding = int((qa_com_embedding / total_qa) * 100) if total_qa > 0 else 0
        
        # Calcular tamanho médio de perguntas e respostas
        tamanho_perguntas = [len(qa.question) for qa in qa_pairs]
        tamanho_respostas = [len(qa.answer) for qa in qa_pairs]
        
        tamanho_medio_pergunta = sum(tamanho_perguntas) // total_qa if total_qa > 0 else 0
        tamanho_medio_resposta = sum(tamanho_respostas) // total_qa if total_qa > 0 else 0
        
        # Contar perguntas similares
        total_perguntas_similares = 0
        for qa in qa_pairs:
            if isinstance(qa.similar_questions, list):
                total_perguntas_similares += len(qa.similar_questions)
            elif isinstance(qa.similar_questions, str):
                try:
                    similares = json.loads(qa.similar_questions)
                    if isinstance(similares, list):
                        total_perguntas_similares += len(similares)
                except:
                    # Se não for JSON válido, tenta contar por vírgulas
                    if qa.similar_questions:
                        total_perguntas_similares += qa.similar_questions.count(',') + 1
        
        media_perguntas_similares = total_perguntas_similares // total_qa if total_qa > 0 else 0
        
        # Contar QAs por página do manual
        qa_por_pagina = {}
        for qa in qa_pairs:
            try:
                chunk = FeiraManualChunk.objects.get(id=qa.chunk_id)
                pagina = chunk.pagina or 0
                if pagina not in qa_por_pagina:
                    qa_por_pagina[pagina] = 0
                qa_por_pagina[pagina] += 1
            except:
                pass
        
        # Organizar por página
        qa_por_pagina_list = [{"pagina": k, "quantidade": v} for k, v in qa_por_pagina.items()]
        qa_por_pagina_list.sort(key=lambda x: x["pagina"])
        
        return JsonResponse({
            'success': True,
            'stats': {
                'total_qa': total_qa,
                'qa_com_embedding': qa_com_embedding,
                'qa_sem_embedding': qa_sem_embedding,
                'percentual_embedding': percentual_embedding,
                'tamanho_medio_pergunta': tamanho_medio_pergunta,
                'tamanho_medio_resposta': tamanho_medio_resposta,
                'total_perguntas_similares': total_perguntas_similares,
                'media_perguntas_similares': media_perguntas_similares,
                'qa_por_pagina': qa_por_pagina_list
            }
        })
    
    except Exception as e:
        logger.error(f"Erro ao obter estatísticas de QA: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)
    




@login_required
@require_POST
def feira_qa_regenerate(request, feira_id):
    feira = get_object_or_404(Feira, pk=feira_id)
    
    # Verificar se já existe um processamento em andamento
    import threading
    qa_processando = any(t.name.startswith(f'QA-{feira.id}') for t in threading.enumerate())
    
    if qa_processando:
        return JsonResponse({
            'success': False,
            'message': 'Já existe um processamento de Q&A em andamento.'
        })
    
    # Obter o agente selecionado na interface (se houver)
    agente_id = request.POST.get('agente_id')
    agente_nome = None
    
    if agente_id:
        try:
            agente = Agente.objects.get(pk=agente_id, ativo=True)
            agente_nome = agente.nome
        except Agente.DoesNotExist:
            pass
    
    # Limpar QAs existentes no banco de dados
    FeiraManualQA.objects.filter(feira=feira).delete()
    
    try:
        # Iniciar processamento em uma thread separada
        def process_qa_background(feira_id, agent_name):
            try:
                thread_name = f'QA-{feira_id}'
                threading.current_thread().name = thread_name
                
                result = process_all_chunks_for_feira(feira_id, agent_name=agent_name)
                logger.info(f"Processamento QA em background concluído para feira {feira_id}: {result}")
                
            except Exception as e:
                logger.error(f"Erro no processamento QA em background para feira {feira_id}: {str(e)}")
        
        thread = threading.Thread(target=process_qa_background, args=(feira.id, agente_nome))
        thread.name = f'QA-{feira.id}'  # Definir nome para identificação
        thread.daemon = True
        thread.start()
        
        return JsonResponse({
            'success': True,
            'message': 'Processamento Q&A iniciado com sucesso.'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Erro ao iniciar processamento Q&A: {str(e)}'
        })
 
@login_required
@require_POST
def feira_qa_add(request, feira_id):
    """
    Adiciona um novo par QA manualmente.
    """
    feira = get_object_or_404(Feira, pk=feira_id)
    
    try:
        data = json.loads(request.body)
        question = data.get('question', '').strip()
        answer = data.get('answer', '').strip()
        context = data.get('context', '').strip()
        similar_questions = data.get('similar_questions', [])
        
        # Validação básica
        if not question or not answer:
            return JsonResponse({
                'success': False,
                'message': 'Pergunta e resposta são obrigatórias.'
            }, status=400)
        
        # Criar o QA
        qa = FeiraManualQA.objects.create(
            feira=feira,
            question=question,
            answer=answer,
            context=context,
            similar_questions=similar_questions
        )
        
        # Gerar o embedding se possível
        try:
            agente_nome = data.get('agente_nome', 'Embedding Generator')
            rag_service = RAGService(agent_name=agente_nome)
            
            # Verificar se o método existe - em alguns casos pode ter nome diferente
            if hasattr(rag_service, 'embedding_service') and hasattr(rag_service.embedding_service, 'gerar_embeddings_qa'):
                embedding = rag_service.embedding_service.gerar_embeddings_qa(qa)
                
                # Verificar método para armazenar no banco vetorial
                if embedding:
                    if hasattr(rag_service, '_store_in_vector_db'):
                        rag_service._store_in_vector_db(qa, embedding)
                    elif hasattr(rag_service, 'vector_db_service') and hasattr(rag_service.vector_db_service, 'armazenar_vetores'):
                        # Preparar vetores para armazenamento
                        vector_id = f"qa_{qa.id}"
                        metadata = {
                            'q': qa.question,
                            'a': qa.answer,
                            't': qa.context,
                            'sq': qa.similar_questions,
                            'feira_id': str(qa.feira.id),
                            'feira_nome': qa.feira.nome,
                            'qa_id': str(qa.id)
                        }
                        vectors = [(vector_id, embedding, metadata)]
                        namespace = f"feira_{feira_id}"
                        rag_service.vector_db_service.armazenar_vetores(vectors, namespace)
                    
                    # Atualizar ID de embedding
                    qa.embedding_id = f"qa_{qa.id}"
                    qa.save(update_fields=['embedding_id'])
                    
                    logger.info(f"Embedding gerado e armazenado para o QA {qa.id}")
            else:
                logger.warning(f"Métodos de embedding não encontrados no RAGService")
        
        except Exception as e:
            logger.warning(f"Erro ao gerar embedding para o novo QA: {str(e)}")
            # Não impedir a criação do QA se o embedding falhar
        
        return JsonResponse({
            'success': True,
            'message': 'Pergunta e resposta adicionada com sucesso.',
            'qa_id': qa.id
        })
    
    except Exception as e:
        logger.error(f"Erro ao adicionar QA: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)
    
@login_required
def feira_qa_progress(request, pk):
    try:
        feira = Feira.objects.get(pk=pk)
        return JsonResponse({
            'success': True,
            'progress': feira.qa_progresso_processamento if hasattr(feira, 'qa_progresso_processamento') else 0,
            'status': feira.qa_processamento_status if hasattr(feira, 'qa_processamento_status') else 'pendente',
            'message': feira.qa_mensagem_erro if hasattr(feira, 'qa_mensagem_erro') else None,
            'processed': feira.qa_processado if hasattr(feira, 'qa_processado') else False,
            'total_qa': FeiraManualQA.objects.filter(feira=feira).count()
        })
    except Feira.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Feira não encontrada'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False, 
            'error': str(e)
        }, status=500)