# gestor/views/feira.py

import json
import logging
import threading
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import JsonResponse
from django.db.models import Q
from django.views.decorators.http import require_POST, require_GET

from core.models import Feira, FeiraManualChunk, FeiraManualQA, Agente
from core.forms import FeiraForm
from core.tasks import processar_manual_feira, pesquisar_manual_feira
from core.services.qa_generator import QAGenerator, process_all_chunks_for_feira
from core.services.rag_service import integrar_feira_com_briefing, RAGService

from projetos.models import Projeto
from projetos.models.briefing import Briefing, BriefingConversation

logger = logging.getLogger(__name__)

# Função auxiliar para processar o manual em segundo plano
def processar_manual_background(feira_id):
    try:
        resultado = processar_manual_feira(feira_id)
        logger.info(f"Processamento em background concluído para feira {feira_id}: {resultado}")
    except Exception as e:
        logger.error(f"Erro no processamento em background para feira {feira_id}: {str(e)}")

@login_required
def feira_list(request):
    feiras_list = Feira.objects.all().order_by('-data_inicio')
    
    status = request.GET.get('status')
    if status == 'ativa':
        feiras_list = feiras_list.filter(ativa=True)
    elif status == 'inativa':
        feiras_list = feiras_list.filter(ativa=False)
    
    paginator = Paginator(feiras_list, 10)
    page = request.GET.get('page', 1)
    
    try:
        feiras = paginator.page(page)
    except PageNotAnInteger:
        feiras = paginator.page(1)
    except EmptyPage:
        feiras = paginator.page(paginator.num_pages)
    
    return render(request, 'gestor/feira_list.html', {'feiras': feiras, 'status_filtro': status})

@login_required
def feira_create(request):
    if request.method == 'POST':
        form = FeiraForm(request.POST, request.FILES)
        if form.is_valid():
            feira = form.save()
            messages.success(request, f'Feira "{feira.nome}" cadastrada com sucesso.')
            
            # Iniciar processamento em background
            thread = threading.Thread(target=processar_manual_background, args=(feira.id,))
            thread.daemon = True
            thread.start()
            
            return redirect('gestor:feira_list')
    else:
        form = FeiraForm()
    
    return render(request, 'gestor/feira_form.html', {'form': form})

@login_required
def feira_update(request, pk):
    feira = get_object_or_404(Feira, pk=pk)
    
    if request.method == 'POST':
        form = FeiraForm(request.POST, request.FILES, instance=feira)
        if form.is_valid():
            manual_alterado = 'manual' in request.FILES
            feira = form.save()
            messages.success(request, f'Feira "{feira.nome}" atualizada com sucesso.')
            
            if manual_alterado:
                feira.manual_processado = False
                feira.save(update_fields=['manual_processado'])
                
                # Iniciar processamento em background
                thread = threading.Thread(target=processar_manual_background, args=(feira.id,))
                thread.daemon = True
                thread.start()
            
            return redirect('gestor:feira_list')
    else:
        form = FeiraForm(instance=feira)
    
    return render(request, 'gestor/feira_form.html', {'form': form})

@login_required
def feira_toggle_status(request, pk):
    feira = get_object_or_404(Feira, pk=pk)
    feira.ativa = not feira.ativa
    feira.save()
    
    status = "ativada" if feira.ativa else "desativada"
    messages.success(request, f'Feira "{feira.nome}" {status} com sucesso.')
    
    return redirect('gestor:feira_list')

@login_required
def feira_search(request, pk):
    feira = get_object_or_404(Feira, pk=pk)
    
    if request.method != 'POST' or not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'error': 'Método não permitido'}, status=405)
    
    query = request.POST.get('query', '')
    if not query:
        return JsonResponse({'error': 'Consulta vazia'}, status=400)
    
    try:
        resultados = pesquisar_manual_feira(query, feira_id=feira.id)
        
        if isinstance(resultados, dict) and 'status' in resultados and resultados['status'] == 'error':
            return JsonResponse({
                'success': False,
                'error': resultados['message']
            }, status=500)
        
        resultados_json = []
        for resultado in resultados:
            chunk = resultado['chunk']
            resultados_json.append({
                'chunk': {
                    'id': chunk['id'],
                    'posicao': chunk['posicao'],
                    'texto': chunk['texto'],
                    'pagina': chunk['pagina']
                },
                'similaridade': resultado['similaridade']
            })
        
        return JsonResponse({
            'success': True,
            'query': query,
            'results': resultados_json
        })
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
    
@login_required
def feira_reprocess(request, pk):
    feira = get_object_or_404(Feira, pk=pk)
    
    if request.method != 'POST':
        return redirect('gestor:feira_detail', pk=feira.id)
    
    # Obter URL para redirecionamento após processamento (opcional)
    redirect_url = request.POST.get('redirect_url')
    
    if hasattr(feira, 'reset_processamento'):
        feira.reset_processamento()
    else:
        feira.manual_processado = False
        feira.processamento_status = 'pendente'
        feira.progresso_processamento = 0
    feira.save()
    
    # Iniciar processamento em thread separada para não bloquear a resposta
    thread = threading.Thread(target=processar_manual_background, args=(feira.id,))
    thread.daemon = True
    thread.start()
    
    messages.success(request, f'Processamento do manual da feira "{feira.nome}" iniciado.')
    
    # Redirecionar para a URL especificada ou para a página de detalhes
    if redirect_url:
        return redirect(redirect_url)
    else:
        return redirect('gestor:feira_detail', pk=feira.id)

@login_required
def feira_qa_list(request, feira_id):
    feira = get_object_or_404(Feira, pk=feira_id)
    processando = feira.processamento_status == 'processando'
    query = request.GET.get('q', '')
    qa_pairs_list = FeiraManualQA.objects.filter(feira=feira)
    
    if query:
        qa_pairs_list = qa_pairs_list.filter(
            Q(question__icontains=query) | 
            Q(answer__icontains=query) | 
            Q(similar_questions__contains=query)
        )
    
    paginator = Paginator(qa_pairs_list, 10)
    page = request.GET.get('page')
    
    try:
        qa_pairs = paginator.page(page)
    except PageNotAnInteger:
        qa_pairs = paginator.page(1)
    except EmptyPage:
        qa_pairs = paginator.page(paginator.num_pages)
    
    qa_count = qa_pairs_list.count()
    
    # Obter lista de agentes para o formulário de regeneração de QA
    agentes = Agente.objects.filter(ativo=True)
    
    context = {
        'feira': feira,
        'qa_pairs': qa_pairs,
        'qa_count': qa_count,
        'query': query,
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
        
        qa.question = data.get('question', qa.question)
        qa.answer = data.get('answer', qa.answer)
        qa.context = data.get('context', qa.context)
        qa.similar_questions = data.get('similar_questions', qa.similar_questions)
        qa.save()
        
        # Verificar se é necessário atualizar o embedding
        atualizar_embedding = data.get('atualizar_embedding', False)
        if atualizar_embedding:
            try:
                # Obter o agente para embedding configurado na interface ou usar o padrão
                agente_nome = data.get('agente_nome', 'Embedding Generator')
                rag_service = RAGService(agent_name=agente_nome)
                embedding = rag_service.gerar_embeddings_qa(qa)
                if embedding:
                    rag_service._store_in_vector_db(qa, embedding)
                    
                    # Atualizar o registro
                    qa.embedding_id = f"qa_{qa.id}"
                    qa.save(update_fields=['embedding_id'])
            except Exception as e:
                logger.error(f"Erro ao atualizar embedding: {str(e)}")
                # Não impedimos a atualização do QA se falhar o embedding
        
        return JsonResponse({
            'success': True,
            'message': 'Pergunta e resposta atualizada com sucesso.'
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
            embedding = rag_service.gerar_embeddings_qa(qa)
            if embedding:
                rag_service._store_in_vector_db(qa, embedding)
                qa.embedding_id = f"qa_{qa.id}"
                qa.save(update_fields=['embedding_id'])
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
def briefing_vincular_feira(request, briefing_id, feira_id):
    """
    Vincula uma feira a um briefing para usar seu manual como referência.
    """
    # Verificar permissões
    briefing = get_object_or_404(Briefing, pk=briefing_id)
    projeto = briefing.projeto
    
    # Garantir que o usuário tenha acesso ao projeto
    if not (
        request.user.nivel in ['admin', 'gestor'] or 
        request.user == projeto.projetista or 
        request.user == projeto.cliente
    ):
        return JsonResponse({
            'success': False,
            'message': 'Você não tem permissão para realizar esta operação.'
        }, status=403)
    
    # Integrar a feira ao briefing
    result = integrar_feira_com_briefing(briefing_id, feira_id)
    
    return JsonResponse({
        'success': result.get('status') == 'success',
        'message': result.get('message', '')
    })

@login_required
@require_POST
def briefing_responder_pergunta(request):
    """
    Responde a uma pergunta do usuário usando o RAG baseado no manual da feira.
    """
    try:
        data = json.loads(request.body)
        briefing_id = data.get('briefing_id')
        pergunta = data.get('pergunta')
        agente_nome = data.get('agente_nome', 'Assistente de Briefing')  # Nome do agente a ser usado
        
        if not briefing_id or not pergunta:
            return JsonResponse({
                'success': False,
                'message': 'Briefing ID e pergunta são obrigatórios.'
            }, status=400)
        
        # Obter o briefing
        briefing = get_object_or_404(Briefing, pk=briefing_id)
        
        # Verificar se há uma feira vinculada
        if not hasattr(briefing, 'feira') or not briefing.feira:
            return JsonResponse({
                'success': False,
                'message': 'Este briefing não possui uma feira vinculada.'
            })
        
        # Verificar se o agente existe e está ativo
        try:
            agente = Agente.objects.get(nome=agente_nome, ativo=True)
        except Agente.DoesNotExist:
            # Caso o agente não exista, usar o padrão
            agente_nome = 'Assistente de Briefing'
        
        # Inicializar o serviço RAG com o agente especificado
        rag_service = RAGService(agent_name=agente_nome)
        
        # Gerar resposta
        rag_result = rag_service.gerar_resposta_rag(pergunta, briefing.feira.id)
        
        # Registrar a pergunta e resposta no histórico de conversas
        BriefingConversation.objects.create(
            briefing=briefing,
            mensagem=f"Pergunta: {pergunta}",
            origem='cliente' if request.user == briefing.projeto.cliente else 'projetista',
            etapa=briefing.etapa_atual
        )
        
        BriefingConversation.objects.create(
            briefing=briefing,
            mensagem=f"Resposta (Manual da Feira): {rag_result['resposta']}",
            origem='sistema',
            etapa=briefing.etapa_atual
        )
        
        return JsonResponse({
            'success': True,
            'resposta': rag_result['resposta'],
            'contextos': rag_result['contextos'],
            'status': rag_result['status'],
            'agente_usado': agente_nome
        })
        
    except Exception as e:
        logger.error(f"Erro ao responder pergunta: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)
    

@login_required
#@require_admin_or_gestor
@require_POST
def feira_reset_data(request, pk):
    """
    Exclui todos os dados processados de uma feira: chunks, QAs e vetores.
    """
    feira = get_object_or_404(Feira, pk=pk)
    
    try:
            
        # 1. Obter todos os QAs para depois excluir seus vetores
        qa_pairs = FeiraManualQA.objects.filter(feira=feira)
        qa_embedding_ids = [qa.embedding_id for qa in qa_pairs if qa.embedding_id]
        
        # 2. Excluir os chunks processados
        chunk_count = FeiraManualChunk.objects.filter(feira=feira).count()
        FeiraManualChunk.objects.filter(feira=feira).delete()
        
        # 3. Excluir os QAs gerados
        qa_count = qa_pairs.count()
        qa_pairs.delete()
        
        # 4. Excluir os vetores do banco vetorial
        vector_count = 0
        if qa_embedding_ids:
            try:
                from core.utils.pinecone_utils import get_index
                index = get_index()
                if index:
                    namespace = f"feira_{feira.id}"
                    # Tentativa 1: excluir por IDs específicos
                    index.delete(ids=qa_embedding_ids, namespace=namespace)
                    vector_count = len(qa_embedding_ids)
                    
                    # Tentativa 2: excluir todo o namespace (mais confiável)
                    try:
                        # Alguns bancos vetoriais permitem excluir namespaces inteiros
                        index.delete(delete_all=True, namespace=namespace)
                    except:
                        # Se não suportar, já tentamos excluir por IDs acima
                        pass
            except Exception as e:
                logger.error(f"Erro ao excluir vetores: {str(e)}")
                messages.warning(request, f"Alguns vetores podem não ter sido excluídos: {str(e)}")
        
        # 5. Resetar o status de processamento da feira
        feira.manual_processado = False
        feira.processamento_status = 'pendente'
        feira.progresso_processamento = 0
        feira.mensagem_erro = None
        feira.save()
        
        # Contabilizar o que foi excluído para a mensagem
        messages.success(
            request, 
            f'Dados da feira "{feira.nome}" excluídos com sucesso: '
            f'{chunk_count} chunks, {qa_count} perguntas/respostas e {vector_count} vetores.'
        )
        
        # Registrar no log
        logger.info(
            f"Usuário {request.user.username} resetou dados da feira {feira.id}: "
            f"{chunk_count} chunks, {qa_count} QAs, {vector_count} vetores"
        )
        
        return redirect('gestor:feira_detail', pk=feira.id)
        
    except Exception as e:
        messages.error(request, f'Erro ao excluir dados da feira: {str(e)}')
        logger.error(f"Erro ao resetar feira {feira.id}: {str(e)}")
        return redirect('gestor:feira_detail', pk=feira.id)


@login_required
def feira_reset_data_confirm(request, pk):
    """
    Exibe página de confirmação para exclusão de dados processados e manual da feira.
    """
    feira = get_object_or_404(Feira, pk=pk)
    
    # Verificar permissões
    if not request.user.nivel in ['admin', 'gestor']:
        messages.error(request, 'Você não tem permissão para realizar esta operação.')
        return redirect('gestor:feira_detail', pk=feira.id)
    
    # Obter estatísticas para exibir na confirmação
    stats = {
        'chunks': FeiraManualChunk.objects.filter(feira=feira).count(),
        'qa_pairs': FeiraManualQA.objects.filter(feira=feira).count(),
        'embeddings': 0  # Não temos forma direta de contar, será estimado pelos QAs
    }
    
    # Estimar número de embeddings pelos QAs com embedding_id
    qa_com_embedding = FeiraManualQA.objects.filter(feira=feira).exclude(embedding_id__isnull=True).exclude(embedding_id='').count()
    stats['embeddings'] = qa_com_embedding
    
    # Verificar se existe o manual
    tem_manual = bool(feira.manual)
    
    # Se for um POST, processar a exclusão
    if request.method == 'POST':
        try:
            # 1. Obter todos os QAs para depois excluir seus vetores
            qa_pairs = FeiraManualQA.objects.filter(feira=feira)
            qa_embedding_ids = [qa.embedding_id for qa in qa_pairs if qa.embedding_id]
            
            # 2. Excluir os chunks processados
            chunk_count = stats['chunks']
            FeiraManualChunk.objects.filter(feira=feira).delete()
            
            # 3. Excluir os QAs gerados
            qa_count = stats['qa_pairs']
            qa_pairs.delete()
            
            # 4. Excluir os vetores do banco vetorial
            vector_count = 0
            if qa_embedding_ids:
                try:
                    from core.utils.pinecone_utils import get_index
                    index = get_index()
                    if index:
                        namespace = f"feira_{feira.id}"
                        # Excluir por IDs específicos
                        index.delete(ids=qa_embedding_ids, namespace=namespace)
                        vector_count = len(qa_embedding_ids)
                        
                        # Tentar excluir todo o namespace (mais confiável)
                        try:
                            index.delete(delete_all=True, namespace=namespace)
                        except:
                            # Se não suportar, já tentamos excluir por IDs acima
                            pass
                except Exception as e:
                    logger.error(f"Erro ao excluir vetores: {str(e)}")
                    messages.warning(request, f"Alguns vetores podem não ter sido excluídos: {str(e)}")
            
            # 5. Resetar o status de processamento da feira
            feira.manual_processado = False
            feira.processamento_status = 'pendente'
            feira.progresso_processamento = 0
            feira.mensagem_erro = None
            
            # 6. Excluir o arquivo do manual, se solicitado
            excluir_manual = 'excluir_manual' in request.POST and request.POST.get('excluir_manual') == 'on'
            
            if excluir_manual and feira.manual:
                # Armazenar o path do arquivo antes de limpar o campo
                manual_path = feira.manual.path if hasattr(feira.manual, 'path') else None
                
                # Limpar o campo manual no modelo
                feira.manual = None
                
                # Tentar excluir o arquivo físico
                if manual_path and os.path.exists(manual_path):
                    try:
                        import os
                        os.remove(manual_path)
                    except Exception as e:
                        logger.error(f"Erro ao excluir arquivo físico: {str(e)}")
                        messages.warning(request, f"O arquivo físico pode não ter sido excluído completamente: {str(e)}")
            
            # Salvar as alterações
            feira.save()
            
            # Montar mensagem de sucesso
            mensagem = f'Dados da feira "{feira.nome}" excluídos com sucesso: {chunk_count} chunks, {qa_count} perguntas/respostas e {vector_count} vetores.'
            
            if excluir_manual:
                mensagem += " O arquivo do manual também foi excluído."
                
            messages.success(request, mensagem)
            
            # Registrar no log
            logger.info(
                f"Usuário {request.user.username} resetou dados da feira {feira.id}: "
                f"{chunk_count} chunks, {qa_count} QAs, {vector_count} vetores. "
                f"Manual excluído: {excluir_manual}"
            )
            
            return redirect('gestor:feira_detail', pk=feira.id)
            
        except Exception as e:
            messages.error(request, f'Erro ao excluir dados da feira: {str(e)}')
            logger.error(f"Erro ao resetar feira {feira.id}: {str(e)}")
            return redirect('gestor:feira_detail', pk=feira.id)
    
    # Se for GET, apenas exibir a página de confirmação
    context = {
        'feira': feira,
        'stats': stats,
        'manual_processado': feira.manual_processado,
        'tem_manual': tem_manual
    }
    
    return render(request, 'gestor/feira_reset_confirm.html', context)
     
@login_required
def feira_progress(request, pk):
    """
    Retorna o progresso atual do processamento do manual da feira.
    """
    try:
        feira = Feira.objects.get(pk=pk)
        
        # Contar chunks já processados
        chunks_count = FeiraManualChunk.objects.filter(feira=feira).count()
        
        # Auto-correção: se temos chunks mas o status não está correto
        if chunks_count > 0 and chunks_count == feira.total_chunks and not feira.manual_processado:
            if feira.processamento_status != 'processando':
                feira.manual_processado = True
                feira.processamento_status = 'concluido'
                feira.progresso_processamento = 100
                feira.save(update_fields=['manual_processado', 'processamento_status', 'progresso_processamento'])
        
        # Contar QAs para informação adicional
        qa_count = 0
        try:
            qa_count = FeiraManualQA.objects.filter(feira=feira).count()
        except:
            pass
        
        return JsonResponse({
            'success': True,
            'progress': feira.progresso_processamento or 0,
            'status': feira.processamento_status or 'pendente',
            'message': feira.mensagem_erro if feira.mensagem_erro else None,
            'processed': feira.manual_processado or False,
            'total_chunks': feira.total_chunks or 0,
            'current_chunks': chunks_count,
            'total_paginas': feira.total_paginas or 0,
            'qa_count': qa_count  # Adicionar contagem de QA na resposta
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
    
@login_required
def feira_detail(request, pk):
    feira = get_object_or_404(Feira, pk=pk)
    total_chunks = feira.chunks_manual.count() if hasattr(feira, 'chunks_manual') else 0
    qa_count = FeiraManualQA.objects.filter(feira=feira).count()
    
    # Verificar se há QA sendo processado
    # Como não temos o campo no modelo, vamos verificar pela solicitação recente
    import threading
    qa_processando = any(t.name.startswith(f'QA-{feira.id}') for t in threading.enumerate())
    
    context = {
        'feira': feira,
        'total_chunks': total_chunks,
        'manual_processado': feira.manual_processado,
        'qa_count': qa_count,
        'qa_processando': qa_processando,
    }
    
    return render(request, 'gestor/feira_detail.html', context)

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
def feira_qa_progress(request, pk):
    """
    Retorna o progresso atual do processamento de Q&A da feira.
    """
    try:
        feira = Feira.objects.get(pk=pk)
        
        # Contar QAs já criados
        qa_count = FeiraManualQA.objects.filter(feira=feira).count()
        
        # Verificar se há uma thread de processamento de QA ativa
        import threading
        qa_processando = any(t.name.startswith(f'QA-{feira.id}') for t in threading.enumerate())
        
        # Determinar status com base na thread
        if qa_processando:
            status = 'processando'
            processed = False
        elif qa_count > 0:
            status = 'concluido'
            processed = True
        else:
            status = 'pendente'
            processed = False
        
        return JsonResponse({
            'success': True,
            'status': status,
            'message': None,
            'processed': processed,
            'total_qa': qa_count,
            'expected_qa': min(qa_count + 10, 50)  # Estimativa de quantos QAs esperamos no total
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
    

@login_required
@require_POST
def briefing_responder_pergunta(request):
    """
    Responde a uma pergunta do usuário usando o RAG baseado no manual da feira.
    """
    try:
        data = json.loads(request.body)
        pergunta = data.get('pergunta')
        feira_id = data.get('feira_id')
        agente_nome = data.get('agente_nome', 'Assistente RAG de Feiras')  # Nome do agente a ser usado
        
        if not pergunta:
            return JsonResponse({
                'success': False,
                'message': 'Por favor, forneça uma pergunta para consultar.'
            }, status=400)
        
        if not feira_id:
            return JsonResponse({
                'success': False,
                'message': 'É necessário especificar uma feira para a consulta.'
            }, status=400)
        
        # Obter a feira
        try:
            feira = Feira.objects.get(pk=feira_id)
            if not feira.manual_processado:
                return JsonResponse({
                    'success': False,
                    'message': 'O manual desta feira ainda não foi totalmente processado.'
                })
        except Feira.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Feira não encontrada.'
            }, status=404)
        
        # Verificar se o agente existe e está ativo
        try:
            agente = Agente.objects.get(nome=agente_nome, ativo=True)
        except Agente.DoesNotExist:
            # Caso o agente não exista, usar o padrão
            agente_nome = 'Assistente RAG de Feiras'
            try:
                agente = Agente.objects.get(nome=agente_nome, ativo=True)
            except Agente.DoesNotExist:
                # Se nem o padrão existir, usar um nome genérico que será tratado no RAGService
                agente_nome = 'Assistente de Briefing'
        
        # Inicializar o serviço RAG com o agente especificado
        rag_service = RAGService(agent_name=agente_nome)
        
        # Gerar resposta
        rag_result = rag_service.gerar_resposta_rag(pergunta, feira_id)
        
        # Verificar resultado
        if rag_result.get('status') == 'error':
            return JsonResponse({
                'success': False,
                'message': rag_result.get('error', 'Erro ao processar consulta.')
            })
        
        if rag_result.get('status') == 'no_results':
            return JsonResponse({
                'success': True,
                'resposta': "Não encontrei informações específicas sobre isso no manual da feira. Talvez você possa reformular sua pergunta ou consultar o manual completo.",
                'contextos': [],
                'agente_usado': agente_nome
            })
        
        # Registrar no log
        logger.info(f"Consulta RAG processada - Feira: {feira.nome}, Pergunta: '{pergunta}'")
        
        return JsonResponse({
            'success': True,
            'resposta': rag_result['resposta'],
            'contextos': rag_result['contextos'],
            'status': rag_result['status'],
            'agente_usado': agente_nome
        })
        
    except Exception as e:
        logger.error(f"Erro ao responder pergunta: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f"Erro ao processar consulta: {str(e)}"
        }, status=500)

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