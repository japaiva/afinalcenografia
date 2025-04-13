# gestor/views/feira.py

import json
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import JsonResponse
from django.db.models import Q
from django.views.decorators.http import require_POST, require_GET

from core.models import Feira, FeiraManualChunk, FeiraManualQA, Parametro
from core.forms import FeiraForm, ParametroForm
from core.tasks import processar_manual_feira, pesquisar_manual_feira
from core.services.qa_generator import QAGenerator, process_all_chunks_for_feira

logger = logging.getLogger(__name__)

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
            processar_manual_feira.delay(feira.id)
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
                processar_manual_feira.delay(feira.id)
            
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
def feira_detail(request, pk):
    feira = get_object_or_404(Feira, pk=pk)
    total_chunks = feira.chunks_manual.count() if hasattr(feira, 'chunks_manual') else 0
    qa_count = FeiraManualQA.objects.filter(feira=feira).count()
    
    context = {
        'feira': feira,
        'total_chunks': total_chunks,
        'manual_processado': feira.manual_processado,
        'qa_count': qa_count,
    }
    
    return render(request, 'gestor/feira_detail.html', context)

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
    
    if hasattr(feira, 'reset_processamento'):
        feira.reset_processamento()
    else:
        feira.manual_processado = False
        feira.processamento_status = 'pendente'
        feira.progresso_processamento = 0
    feira.save()
    
    try:
        resultado = processar_manual_feira(feira.id)
        if resultado.get('status') == 'success':
            messages.success(request, f'Manual da feira "{feira.nome}" processado com sucesso.')
        else:
            messages.error(request, f'Erro ao processar manual: {resultado.get("message")}')
    except Exception as e:
        messages.error(request, f'Erro ao processar manual: {str(e)}')
    
    return redirect('gestor:feira_detail', pk=feira.id)

@login_required
def feira_progress(request, pk):
    try:
        feira = Feira.objects.get(pk=pk)
        return JsonResponse({
            'success': True,
            'progress': feira.progresso_processamento,
            'status': feira.processamento_status,
            'message': feira.mensagem_erro if feira.mensagem_erro else None,
            'processed': feira.manual_processado,
            'total_chunks': feira.total_chunks,
            'total_paginas': feira.total_paginas
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
    
    context = {
        'feira': feira,
        'qa_pairs': qa_pairs,
        'qa_count': qa_count,
        'query': query,
        'processando': processando,
    }
    
    return render(request, 'gestor/feira_qa_list.html', context)

@login_required
@require_POST
def feira_qa_regenerate(request, feira_id):
    feira = get_object_or_404(Feira, pk=feira_id)
    
    if feira.processamento_status == 'processando':
        return JsonResponse({
            'success': False,
            'message': 'Já existe um processamento em andamento.'
        })
    
    FeiraManualQA.objects.filter(feira=feira).delete()
    
    feira.processamento_status = 'processando'
    feira.progresso_processamento = 0
    feira.save()
    
    try:
        process_all_chunks_for_feira(feira.id)
        return JsonResponse({
            'success': True,
            'message': 'Processamento iniciado com sucesso.'
        })
    except Exception as e:
        feira.processamento_status = 'erro'
        feira.mensagem_erro = str(e)
        feira.save()
        
        return JsonResponse({
            'success': False,
            'message': f'Erro ao iniciar processamento: {str(e)}'
        })

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
        
        generator = QAGenerator()
        new_qa_pairs = generator.generate_qa_from_chunk(chunk)
        
        if not new_qa_pairs:
            return JsonResponse({
                'success': False,
                'message': 'Não foi possível gerar novas perguntas e respostas.'
            })
        
        new_qa = new_qa_pairs[0]
        
        qa.question = new_qa.get('q', qa.question)
        qa.answer = new_qa.get('a', qa.answer)
        qa.context = new_qa.get('t', qa.context)
        qa.similar_questions = new_qa.get('sq', qa.similar_questions)
        qa.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Pergunta e resposta regenerada com sucesso.'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        })
    
    # Views de Parâmetro

@login_required
def parametro_list(request):
    parametros_list = Parametro.objects.all().order_by('parametro')
    
    paginator = Paginator(parametros_list, 10)
    page = request.GET.get('page', 1)
    
    try:
        parametros = paginator.page(page)
    except PageNotAnInteger:
        parametros = paginator.page(1)
    except EmptyPage:
        parametros = paginator.page(paginator.num_pages)
    
    return render(request, 'gestor/parametro_list.html', {'parametros': parametros})

@login_required
def parametro_create(request):
    if request.method == 'POST':
        form = ParametroForm(request.POST)
        if form.is_valid():
            parametro = form.save()
            messages.success(request, 'Parâmetro criado com sucesso.')
            storage = messages.get_messages(request)
            storage.used = True
            return redirect('gestor:parametro_list')
    else:
        form = ParametroForm()
    return render(request, 'gestor/parametro_form.html', {'form': form})

@login_required
def parametro_update(request, pk):
    parametro = get_object_or_404(Parametro, pk=pk)
    if request.method == 'POST':
        form = ParametroForm(request.POST, instance=parametro)
        if form.is_valid():
            parametro = form.save()
            messages.success(request, 'Parâmetro atualizado com sucesso.')
            storage = messages.get_messages(request)
            storage.used = True
            return redirect('gestor:parametro_list')
    else:
        form = ParametroForm(instance=parametro)
    return render(request, 'gestor/parametro_form.html', {'form': form})

@login_required
def parametro_delete(request, pk):
    parametro = get_object_or_404(Parametro, pk=pk)
    if request.method == 'POST':
        parametro.delete()
        messages.success(request, 'Parâmetro excluído com sucesso.')
        storage = messages.get_messages(request)
        storage.used = True
        return redirect('gestor:parametro_list')
    return render(request, 'gestor/parametro_confirm_delete.html', {'parametro': parametro})