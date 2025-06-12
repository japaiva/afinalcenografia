# gestor/views/feira_rag.py

# - feira_reset_data_confirm
# - feira_search_unified
# - briefing_vincular_feira
# - briefing_responder_pergunta
# - feira_reset_data

import json
import logging
import os  # Para manipulação de arquivos no reset_data_confirm
import threading
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from core.models import Feira, FeiraManualChunk, FeiraManualQA, Agente
from core.services.rag_service import integrar_feira_com_briefing, RAGService
from projetos.models.briefing import Briefing

logger = logging.getLogger(__name__)

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
def feira_search_unified(request, feira_id):
    """
    Realiza uma busca unificada nos blocos e QAs da feira.
    """
    feira = get_object_or_404(Feira, pk=feira_id)
    query = request.GET.get('q', '')
    
    if not query:
        return render(request, 'gestor/feira_search_unified.html', {
            'feira': feira,
            'query': '',
            'results': None
        })
    
    try:
        # Inicializar o serviço RAG
        rag_service = RAGService(agent_name='Assistente RAG de Feiras')
        
        # Buscar nos blocos do manual
        from core.tasks import pesquisar_manual_feira
        blocos_results = pesquisar_manual_feira(query, feira_id=feira_id, num_resultados=3)
        
        # Buscar nos QAs
        from core.tasks import pesquisar_qa_feira
        qa_results = pesquisar_qa_feira(query, feira_id=feira_id, num_resultados=3)
        
        # Unificar resultados
        unified_results = {
            'blocos': blocos_results if isinstance(blocos_results, list) else [],
            'qa': qa_results if isinstance(qa_results, list) else []
        }
        
        return render(request, 'gestor/feira_search_unified.html', {
            'feira': feira,
            'query': query,
            'results': unified_results
        })
        
    except Exception as e:
        return render(request, 'gestor/feira_search_unified.html', {
            'feira': feira,
            'query': query,
            'error': str(e)
        })


@login_required
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
        
        # 4. Excluir os vetores do banco vetorial (namespace de QA)
        vector_count = 0
        if qa_embedding_ids:
            try:
                from core.utils.pinecone_utils import get_index
                index = get_index()
                if index:
                    namespace = feira.get_qa_namespace()
                    # Excluir por IDs específicos
                    index.delete(ids=qa_embedding_ids, namespace=namespace)
                    vector_count = len(qa_embedding_ids)
                    # Excluir todo o namespace
                    try:
                        index.delete(delete_all=True, namespace=namespace)
                    except:
                        pass
            except Exception as e:
                logger.error(f"Erro ao excluir vetores: {str(e)}")
                messages.warning(request, f"Alguns vetores podem não ter sido excluídos: {str(e)}")
        
        # 5. Resetar o status de processamento de chunks e QA
        feira.chunks_processados = False
        feira.chunks_processamento_status = 'pendente'
        feira.chunks_progresso = 0
        feira.qa_processado = False
        feira.qa_processamento_status = 'pendente'
        feira.qa_progresso = 0
        feira.mensagem_erro = None
        feira.save(update_fields=[
            'chunks_processados', 'chunks_processamento_status', 'chunks_progresso',
            'qa_processado', 'qa_processamento_status', 'qa_progresso', 'mensagem_erro'
        ])
        
        messages.success(
            request,
            f'Dados da feira "{feira.nome}" excluídos com sucesso: '
            f'{chunk_count} chunks, {qa_count} perguntas/respostas e {vector_count} vetores.'
        )
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
    Lida com GET (exibe estatísticas) e POST (executa a exclusão).
    """
    feira = get_object_or_404(Feira, pk=pk)
    
    # Permissões
    if not request.user.nivel in ['admin', 'gestor']:
        messages.error(request, 'Você não tem permissão para esta operação.')
        return redirect('gestor:feira_detail', pk=feira.id)
    
    # Estatísticas iniciais
    stats = {
        'chunks': FeiraManualChunk.objects.filter(feira=feira).count(),
        'qa_pairs': FeiraManualQA.objects.filter(feira=feira).count(),
        'embeddings': FeiraManualQA.objects.filter(feira=feira)
                        .exclude(embedding_id__isnull=True)
                        .exclude(embedding_id='')
                        .count()
    }
    tem_manual = bool(feira.manual)
    
    if request.method == 'POST':
        try:
            qa_embedding_ids = [
                qa.embedding_id
                for qa in FeiraManualQA.objects.filter(feira=feira)
                if qa.embedding_id
            ]
            
            # Excluir chunks e QAs
            chunk_count = stats['chunks']
            FeiraManualChunk.objects.filter(feira=feira).delete()
            qa_count = stats['qa_pairs']
            FeiraManualQA.objects.filter(feira=feira).delete()
            
            # Excluir vetores de QA
            vector_count = 0
            if qa_embedding_ids:
                from core.utils.pinecone_utils import get_index
                index = get_index()
                if index:
                    namespace = feira.get_qa_namespace()
                    index.delete(ids=qa_embedding_ids, namespace=namespace)
                    vector_count = len(qa_embedding_ids)
                    try:
                        index.delete(delete_all=True, namespace=namespace)
                    except:
                        pass
            
            # Reset status chunks e QA
            feira.chunks_processados = False
            feira.chunks_processamento_status = 'pendente'
            feira.chunks_progresso = 0
            feira.qa_processado = False
            feira.qa_processamento_status = 'pendente'
            feira.qa_progresso = 0
            feira.mensagem_erro = None
            
            # Opcional: excluir arquivo manual
            if request.POST.get('excluir_manual') == 'on' and feira.manual:
                manual_path = getattr(feira.manual, 'path', None)
                feira.manual = None
                if manual_path and os.path.exists(manual_path):
                    try:
                        os.remove(manual_path)
                    except Exception as e:
                        logger.error(f"Erro ao excluir arquivo físico: {str(e)}")
                        messages.warning(request, f"O arquivo físico pode não ter sido excluído: {str(e)}")
            
            feira.save()
            
            msg = (
                f'Dados da feira "{feira.nome}" excluídos: '
                f'{chunk_count} chunks, {qa_count} QAs, {vector_count} vetores.'
            )
            if request.POST.get('excluir_manual') == 'on':
                msg += " Manual excluído."
            messages.success(request, msg)
            logger.info(
                f"Usuário {request.user.username} resetou dados da feira {feira.id}: "
                f"{chunk_count} chunks, {qa_count} QAs, {vector_count} vetores, "
                f"manual excluído: {request.POST.get('excluir_manual') == 'on'}"
            )
            return redirect('gestor:feira_detail', pk=feira.id)
        
        except Exception as e:
            messages.error(request, f'Erro ao resetar dados: {str(e)}')
            logger.error(f"Erro no reset_data_confirm para feira {feira.id}: {str(e)}")
            return redirect('gestor:feira_detail', pk=feira.id)
    
    # GET: exibir confirmação
    return render(request, 'gestor/feira_reset_confirm.html', {
        'feira': feira,
        'stats': stats,
        'manual_processado': feira.chunks_processados,
        'tem_manual': tem_manual
    })


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
        agente_nome = data.get('agente_nome', 'Assistente RAG de Feiras')
        
        if not pergunta:
            return JsonResponse({'success': False, 'message': 'Forneça uma pergunta.'}, status=400)
        if not feira_id:
            return JsonResponse({'success': False, 'message': 'Especifique uma feira.'}, status=400)
        
        feira = get_object_or_404(Feira, pk=feira_id)
        if not feira.chunks_processados:
            return JsonResponse({
                'success': False,
                'message': 'O manual desta feira ainda não foi totalmente processado.'
            })
        
        # Verificar agente
        try:
            agente = Agente.objects.get(nome=agente_nome, ativo=True)
        except Agente.DoesNotExist:
            agente_nome = 'Assistente RAG de Feiras'
            if not Agente.objects.filter(nome=agente_nome, ativo=True).exists():
                agente_nome = 'Assistente de Briefing'
        
        rag_service = RAGService(agent_name=agente_nome)
        rag_result = rag_service.gerar_resposta_rag(pergunta, feira_id)
        
        if rag_result.get('status') == 'error':
            return JsonResponse({'success': False, 'message': rag_result.get('error')})
        if rag_result.get('status') == 'no_results':
            return JsonResponse({
                'success': True,
                'resposta': 'Não encontrei informações específicas no manual.',
                'contextos': [],
                'agente_usado': agente_nome
            })
        
        logger.info(f"Consulta RAG – Feira: {feira.nome}, Pergunta: '{pergunta}'")
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
