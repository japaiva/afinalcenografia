# gestor/views/feira_rag.py

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
