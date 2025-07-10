# Arquivo: /Users/joseantoniopaiva/pythonprojects/afinal_cenografia/projetista/views/planta_baixa.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.contrib import messages # Importa o módulo de mensagens do Django

# Importar seus modelos (verifique se os caminhos estão corretos para o seu projeto)
from projetos.models import Projeto, Briefing
from projetista.models import PlantaBaixa
from core.models import CrewExecucao

# ######################################################################################
# A IMPORTAÇÃO CRÍTICA DO SEU SERVIÇO PlantaBaixaServiceV2
# Este é o caminho correto que você me informou: core/services/crewai/specialized/planta_baixa.py
from core.services.crewai.specialized.planta_baixa import PlantaBaixaServiceV2
# ######################################################################################

import logging

logger = logging.getLogger(__name__)

# Instanciar o serviço de planta baixa. 
# Ele será usado por todas as views definidas neste arquivo.
planta_baixa_service = PlantaBaixaServiceV2()

@login_required
def gerar_planta_baixa(request, projeto_id):
    """
    View para iniciar a geração de uma planta baixa via CrewAI para um projeto.
    """
    projeto = get_object_or_404(Projeto, id=projeto_id)
    # Supondo que você queira usar o briefing mais recente ou um briefing específico
    briefing = get_object_or_404(Briefing, projeto=projeto) 

    if request.method == 'POST':
        logger.info(f"Requisição POST recebida para gerar planta baixa para Projeto ID: {projeto_id}")
        try:
            # Calcula a próxima versão da planta baixa para o briefing atual
            nova_versao = PlantaBaixa.objects.filter(briefing=briefing).count() + 1
            
            # Chama o método 'gerar_planta' do serviço de CrewAI
            resultado_crew = planta_baixa_service.gerar_planta(briefing=briefing, versao=nova_versao)

            if resultado_crew['success']:
                messages.success(request, "Planta baixa gerada com sucesso! Você pode visualizá-la agora.")
                # Redireciona para a visualização da planta recém-gerada ou para o detalhe do projeto
                return redirect('projetista:visualizar_planta_baixa', projeto_id=projeto.id)
            else:
                error_message = resultado_crew.get('error', 'Erro desconhecido na geração da planta baixa.')
                messages.error(request, f"Erro ao gerar planta baixa: {error_message}")
                logger.error(f"Falha na geração da planta baixa para projeto {projeto_id}: {error_message}")
        except Exception as e:
            logger.exception(f"Erro inesperado ao chamar serviço de geração de planta baixa para Projeto ID {projeto_id}")
            messages.error(request, f"Ocorreu um erro interno ao gerar a planta baixa: {e}")
            
    # Para requisições GET ou se o POST falhar, renderiza uma página de confirmação/formulário
    context = {
        'projeto': projeto,
        'briefing': briefing
    }
    return render(request, 'projetista/planta_baixa/gerar.html', context) # Certifique-se de que este template HTML existe

@login_required
def refinar_planta_baixa(request, projeto_id):
    """
    View placeholder para a funcionalidade de refinar uma planta baixa existente.
    """
    messages.info(request, "Funcionalidade de refinamento de planta baixa em desenvolvimento. Será implementada em breve!")
    # Você pode redirecionar para a página de visualização ou detalhe do projeto
    return redirect('projetista:visualizar_planta_baixa', projeto_id=projeto_id)

@login_required
def visualizar_planta_baixa(request, projeto_id):
    """
    View para exibir a planta baixa mais recente de um projeto.
    """
    projeto = get_object_or_404(Projeto, id=projeto_id)
    # Busca a planta baixa mais recente associada ao briefing do projeto
    planta_baixa = PlantaBaixa.objects.filter(briefing__projeto=projeto).order_by('-versao').first()

    svg_content = None
    if planta_baixa and planta_baixa.arquivo_svg:
        try:
            # Lê o conteúdo do arquivo SVG. .read() retorna bytes, então .decode('utf-8') para string.
            svg_content = planta_baixa.arquivo_svg.read().decode('utf-8')
        except Exception as e:
            logger.error(f"Erro ao ler arquivo SVG para planta ID {planta_baixa.id}: {e}")
            # SVG de fallback simples em caso de erro na leitura do arquivo
            svg_content = """<svg width="600" height="400" viewBox="0 0 600 400" xmlns="http://www.w3.org/2000/svg"><rect x="0" y="0" width="600" height="400" fill="#f0f0f0"/><text x="300" y="200" text-anchor="middle" font-family="Arial" font-size="20" fill="red">Erro ao Carregar SVG</text><text x="300" y="230" text-anchor="middle" font-family="Arial" font-size="12" fill="gray">Verifique os logs do servidor.</text></svg>"""

    context = {
        'projeto': projeto,
        'planta_baixa': planta_baixa,
        'svg_content': svg_content,
        'has_planta': planta_baixa is not None # Indica se existe alguma planta para o projeto
    }
    return render(request, 'projetista/planta_baixa/visualizar.html', context) # Certifique-se de que este template HTML existe

@login_required
def download_planta_svg(request, planta_id):
    """
    View para permitir o download do arquivo SVG de uma planta baixa específica.
    """
    planta = get_object_or_404(PlantaBaixa, id=planta_id)
    if planta.arquivo_svg:
        # Define o tipo de conteúdo como SVG e o cabeçalho de disposição para download
        response = HttpResponse(planta.arquivo_svg.read(), content_type='image/svg+xml')
        response['Content-Disposition'] = f'attachment; filename="{planta.arquivo_svg.name}"'
        return response
    
    messages.error(request, "Arquivo SVG não encontrado para download.")
    # Redireciona de volta para a página de detalhe do projeto se o arquivo não for encontrado
    return redirect('projetista:projeto_detail', pk=planta.briefing.projeto.id) 

@login_required
def validar_crew_status(request):
    """
    View para verificar o status de disponibilidade e configuração do CrewAI.
    """
    validation_result = planta_baixa_service.validar_crew() # Usa o método de validação do serviço
    return JsonResponse(validation_result)

@login_required
def obter_logs_execucao(request, execucao_id):
    """
    View para obter logs detalhados de uma execução específica do CrewAI.
    """
    try:
        execucao = get_object_or_404(CrewExecucao, id=execucao_id)
        # Assumindo que 'logs_execucao' é um campo de texto ou JSON no seu modelo CrewExecucao
        logs = execucao.logs_execucao 
        return JsonResponse({'logs': logs})
    except Exception as e:
        logger.error(f"Erro ao obter logs da execução {execucao_id}: {e}")
        return JsonResponse({'error': 'Logs não encontrados ou erro na busca.'}, status=404)

@login_required
def status_execucao(request, execucao_id):
    """
    View para obter o status atual e informações de tempo de uma execução do CrewAI.
    """
    try:
        execucao = get_object_or_404(CrewExecucao, id=execucao_id)
        return JsonResponse({
            'status': execucao.status,
            'tempo_execucao': execucao.tempo_execucao,
            'finalizado_em': execucao.finalizado_em.isoformat() if execucao.finalizado_em else None,
            'erro_detalhado': execucao.erro_detalhado
        })
    except Exception as e:
        logger.error(f"Erro ao obter status da execução {execucao_id}: {e}")
        return JsonResponse({'error': 'Status não encontrado ou erro na busca.'}, status=404)

@login_required
def debug_crew_info(request):
    """
    View de depuração para fornecer informações gerais sobre a configuração do CrewAI.
    """
    # Você pode expandir isso para retornar mais detalhes sobre agentes/tasks do banco, etc.
    return JsonResponse({'info': 'Informações de depuração do CrewAI serão exibidas aqui.'})