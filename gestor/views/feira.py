# gestor/views/feira.py

# - processar_manual_background
# - feira_list
# - feira_create
# - feira_update
# - feira_delete
# - feira_toggle_status
# - feira_search
# - feira_reprocess
# - feira_progress
# - feira_detail

import logging
import threading
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import JsonResponse
from django.db.models import Q
from django.urls import reverse

from core.models import Feira, FeiraManualQA, FeiraManualChunk 
from core.forms import FeiraForm
from core.tasks import processar_manual_feira, pesquisar_manual_feira

logger = logging.getLogger(__name__)

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
            
            # Iniciar processamento em background apenas se houver manual
            if feira.manual:
                thread = threading.Thread(target=processar_manual_background, args=(feira.id,))
                thread.daemon = True
                thread.start()
                messages.info(request, "O manual será processado em segundo plano. Isso pode levar alguns minutos.")
            
            return redirect('gestor:feira_list')
    else:
        form = FeiraForm()
    
    return render(request, 'gestor/feira_form.html', {'form': form})

def feira_update(request, pk):
    feira = get_object_or_404(Feira, pk=pk)
    
    # Debug para verificar se as datas estão presentes
    #print(f"DEBUG - Feira {pk}: data_inicio={feira.data_inicio}, data_fim={feira.data_fim}")
    
    if request.method == 'POST':
        # Debug para ver os dados recebidos do POST
        #print(f"DEBUG - POST data: {request.POST}")
        
        form = FeiraForm(request.POST, request.FILES, instance=feira)
        if form.is_valid():
            manual_alterado = 'manual' in request.FILES
            feira = form.save()
            # Debug após salvar
            #print(f"DEBUG - Feira salva: data_inicio={feira.data_inicio}, data_fim={feira.data_fim}")

            if manual_alterado:
                # Reset do processamento apenas se o manual foi alterado
                feira.reset_processamento()
                
                # Iniciar processamento em background
                thread = threading.Thread(target=processar_manual_background, args=(feira.id,))
                thread.daemon = True
                thread.start()
                
                messages.info(request, "O novo manual será processado em segundo plano. Isso pode levar alguns minutos.")
            
            # Verificar a página de retorno (detalhes ou lista)
            next_page = request.POST.get('next', 'list')
            if next_page == 'detail':
                return redirect('gestor:feira_detail', pk=feira.id)
            else:
                return redirect('gestor:feira_list')
    else:
        form = FeiraForm(instance=feira)
    
    # Adicionar o ID da feira para uso pelo JavaScript
    context = {
        'form': form,
        'feira_id': pk,
    }
    
    return render(request, 'gestor/feira_form.html', context)

@login_required
def feira_delete(request, pk):
    feira = get_object_or_404(Feira, pk=pk)
    
    # Verificar se há projetos vinculados
    try:
        from projetos.models import Projeto
        projetos_vinculados = Projeto.objects.filter(feira=feira).count()
    except ImportError:
        projetos_vinculados = 0
    
    # Contar chunks e QAs vinculados
    chunks_vinculados = feira.chunks_manual.count() if hasattr(feira, 'chunks_manual') else 0
    qa_vinculados = FeiraManualQA.objects.filter(feira=feira).count()
    
    if request.method == 'POST':
        confirm = request.POST.get('confirm_delete')
        if confirm == 'sim':
            try:
                nome_feira = feira.nome
                
                # Deletar chunks e QAs primeiro (cascade deve fazer isso, mas garantindo)
                if chunks_vinculados > 0:
                    feira.chunks_manual.all().delete()
                if qa_vinculados > 0:
                    FeiraManualQA.objects.filter(feira=feira).delete()
                
                feira.delete()
                messages.success(request, f'Feira "{nome_feira}" excluída com sucesso.')
                storage = messages.get_messages(request)
                storage.used = True
                return redirect('gestor:feira_list')
            except Exception as e:
                messages.error(request, f'Erro ao excluir feira: {str(e)}')
        else:
            messages.info(request, 'Exclusão cancelada.')
            
            # Verificar de onde veio para redirecionar corretamente
            referer = request.META.get('HTTP_REFERER', '')
            if 'detail' in referer:
                return redirect('gestor:feira_detail', pk=feira.id)
            else:
                return redirect('gestor:feira_list')
    
    context = {
        'feira': feira,
        'projetos_vinculados': projetos_vinculados,
        'chunks_vinculados': chunks_vinculados,
        'qa_vinculados': qa_vinculados,
        'pode_excluir': projetos_vinculados == 0
    }
    return render(request, 'gestor/feira_confirm_delete.html', context)


@login_required
def feira_toggle_status(request, pk):
    feira = get_object_or_404(Feira, pk=pk)
    feira.ativa = not feira.ativa
    feira.save()
    
    status = "ativada" if feira.ativa else "desativada"
    messages.success(request, f'Feira "{feira.nome}" {status} com sucesso.')
    
    # Verificar se deve voltar para a lista ou para detalhes
    referer = request.META.get('HTTP_REFERER', '')
    if 'detail' in referer:
        return redirect('gestor:feira_detail', pk=feira.id)
    else:
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
    
    # Usar o novo método reset_processamento
    if hasattr(feira, 'reset_processamento'):
        feira.reset_processamento()
    else:
        # Fallback para casos onde o método não existe
        feira.chunks_processados = False
        feira.chunks_processamento_status = 'pendente'
        feira.chunks_progresso = 0
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
def feira_progress(request, pk):
    """
    Retorna o progresso atual do processamento do manual da feira.
    Endpoint URL: /feira/<pk>/progress/ e /feira/<pk>/progresso/
    """
    try:
        feira = Feira.objects.get(pk=pk)
        
        # Contar chunks já processados
        chunks_count = FeiraManualChunk.objects.filter(feira=feira).count()
        
        # Auto-correção: se temos chunks mas o status não está correto
        if chunks_count > 0 and chunks_count == feira.chunks_total and not feira.chunks_processados:
            if feira.chunks_processamento_status != 'processando':
                feira.chunks_processados = True
                feira.chunks_processamento_status = 'concluido'
                feira.chunks_progresso = 100
                feira.save(update_fields=['chunks_processados', 'chunks_processamento_status', 'chunks_progresso'])
        
        # Contar QAs para informação adicional
        qa_count = 0
        try:
            qa_count = FeiraManualQA.objects.filter(feira=feira).count()
        except Exception as e:
            logger.debug(f"Erro ao contar QAs para feira {pk}: {str(e)}")
        
        return JsonResponse({
            'success': True,
            'progress': feira.chunks_progresso or 0,
            'status': feira.chunks_processamento_status or 'pendente',
            'message': feira.mensagem_erro if feira.mensagem_erro else None,
            'processed': feira.chunks_processados or False,
            'total_chunks': feira.chunks_total or 0,
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
        logger.error(f"Erro ao verificar progresso da feira {pk}: {str(e)}")
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
    import threading
    qa_processando = any(t.name.startswith(f'QA-{feira.id}') for t in threading.enumerate())
    
    context = {
        'feira': feira,
        'total_chunks': total_chunks,
        'manual_processado': feira.chunks_processados,  # Compatibilidade para o template
        'qa_count': qa_count,
        'qa_processando': qa_processando,
    }
    
    return render(request, 'gestor/feira_detail.html', context)   