# projetista/views/conceito.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.db.models import Count
from django.core.paginator import Paginator
from django.conf import settings

from projetos.models import Projeto, Briefing
from projetista.models import ConceitoVisual, ImagemConceitoVisual
from projetista.forms import (
    ConceitoVisualForm, ImagemConceitoForm, 
    GeracaoImagemForm, ModificacaoImagemForm,
    ExportacaoConceitoForm
)

import logging
logger = logging.getLogger(__name__)

# Importe as classes/serviços necessários no topo do arquivo conceito.py
from django.urls import reverse
from core.models import Agente
try:
    from core.services.briefing_extractor import BriefingExtractor
    from core.services.conceito_textual_service import ConceitoTextualService
except ImportError:
    # Placeholders temporários para testes
    class BriefingExtractor:
        def __init__(self, briefing):
            self.briefing = briefing
        def extract_data(self):
            return {
                'informacoes_basicas': {
                    'nome_projeto': self.briefing.projeto.nome,
                    'tipo_stand': getattr(self.briefing, 'tipo_stand', 'padrão'),
                    'feira': getattr(self.briefing.feira, 'nome', 'Não especificado') if hasattr(self.briefing, 'feira') and self.briefing.feira else 'Não especificado',
                    'orcamento': getattr(self.briefing, 'orcamento', None)
                },
                'caracteristicas_fisicas': {},
                'areas_funcionais': {},
                'elementos_visuais': {},
                'objetivos_projeto': {}
            }
            
    class ConceitoTextualService:
        def __init__(self, agente):
            self.agente = agente
        def gerar_conceito(self, briefing_data):
            return {
                'success': True,
                'data': {
                    'titulo': f"Conceito para {briefing_data['informacoes_basicas']['nome_projeto']}",
                    'descricao': "Conceito gerado para demonstração.",
                    'paleta_cores': "Cores neutras com destaques em azul (#1E5AA8) e laranja (#FF6B35).",
                    'materiais_principais': "Estrutura em alumínio, painéis em MDF, vidro temperado e iluminação LED.",
                    'elementos_interativos': "Tela touch screen para demonstração de produtos e área de descanso confortável."
                }
            }
        

@login_required
@require_POST
def gerar_conceito_ia(request, projeto_id):
    """View para geração automática de conceito textual via IA"""
    projeto = get_object_or_404(Projeto, pk=projeto_id, projetista=request.user)
    
    try:
        # Obter briefing mais recente
        briefing = projeto.briefings.latest('versao')
        
        # Extrair dados do briefing
        extractor = BriefingExtractor(briefing)
        briefing_data = extractor.extract_data()
        
        # Obter agente de conceito textual
        try:
            agente = Agente.objects.get(nome='Agente de Conceito Textual')
            
            # Verificar se o agente está ativo
            if not agente.ativo:
                return JsonResponse({
                    'success': False,
                    'message': 'O Agente de Conceito Textual está configurado como inativo. Por favor, ative-o no painel de administração.'
                })
                
        except Agente.DoesNotExist:
            # Na produção, melhor pedir para cadastrar o agente do que criar um temporário
            return JsonResponse({
                'success': False,
                'message': 'Agente de Conceito Textual não encontrado. Por favor, cadastre este agente no painel de administração.'
            })
        
        # Inicializar serviço
        conceito_service = ConceitoTextualService(agente)
        
        # Gerar conceito
        result = conceito_service.gerar_conceito(briefing_data)
        
        if result['success']:
            # Obter o conceito existente ou criar um novo
            conceito = ConceitoVisual.objects.filter(projeto=projeto).first()
            if not conceito:
                conceito = ConceitoVisual(
                    projeto=projeto,
                    briefing=briefing,
                    projetista=request.user,
                    etapa_atual=1,
                    ia_gerado=True
                )
                try:
                    conceito.agente_usado = agente
                except:
                    pass  # Ignorar se o campo não existir
            
            # Atualizar com os dados gerados pela IA
            conceito_data = result['data']
            
            # Processar título e descrição (formatos simples)
            conceito.titulo = conceito_data.get('titulo', f"Conceito para {projeto.nome}")
            conceito.descricao = conceito_data.get('descricao', "Conceito gerado por IA.")

            # Processar paleta de cores (formato complexo - dicionário ou lista)
            paleta_cores = conceito_data.get('paleta_cores', {})
            if isinstance(paleta_cores, dict):
                # Formatar como texto legível
                cores_texto = []
                
                # Processar cores específicas se existirem
                if 'primaria' in paleta_cores:
                    cores_texto.append(f"• Primária: {paleta_cores['primaria']}")
                if 'secundaria' in paleta_cores:
                    cores_texto.append(f"• Secundária: {paleta_cores['secundaria']}")
                if 'terciaria' in paleta_cores:
                    cores_texto.append(f"• Terciária: {paleta_cores['terciaria']}")
                
                # Processar outras cores no dicionário que não são as padrão
                for chave, valor in paleta_cores.items():
                    if chave not in ['primaria', 'secundaria', 'terciaria', 'justificativa'] and not isinstance(valor, dict):
                        cores_texto.append(f"• {chave.capitalize()}: {valor}")
                
                # Adicionar a justificativa se existir
                if 'justificativa' in paleta_cores:
                    cores_texto.append(f"\nJustificativa: {paleta_cores['justificativa']}")
                
                conceito.paleta_cores = "\n".join(cores_texto)
            elif isinstance(paleta_cores, list):
                # Se for uma lista, formatar cada item
                cores_formatadas = []
                for cor in paleta_cores:
                    if isinstance(cor, dict):
                        # Tentar vários formatos possíveis de cores
                        nome = cor.get('nome', cor.get('name', ''))
                        codigo = cor.get('codigo', cor.get('code', cor.get('hex', '')))
                        descricao = cor.get('descricao', cor.get('description', ''))
                        
                        linha = "• "
                        if nome:
                            linha += f"{nome}: "
                        if codigo:
                            linha += f"{codigo}"
                        if descricao and (nome or codigo):
                            linha += f" - {descricao}"
                        elif descricao:
                            linha += descricao
                            
                        cores_formatadas.append(linha)
                    else:
                        cores_formatadas.append(f"• {cor}")
                conceito.paleta_cores = "\n".join(cores_formatadas)
            else:
                # Se for string, usar diretamente
                conceito.paleta_cores = str(paleta_cores)

            # Processar materiais principais (formato complexo - lista ou string)
            materiais = conceito_data.get('materiais_principais', [])
            if isinstance(materiais, list):
                # Formatar cada material como texto legível
                materiais_texto = []
                for mat in materiais:
                    if isinstance(mat, dict):
                        material_nome = mat.get('material', '')
                        acabamento = mat.get('acabamento', '')
                        justificativa = mat.get('justificativa', '')
                        
                        linha = "• "
                        if material_nome:
                            linha += material_nome
                        if acabamento:
                            linha += f" com acabamento {acabamento}"
                        if justificativa:
                            linha += f" - {justificativa}"
                        
                        # Garantir que não haja linhas vazias
                        if linha != "• ":
                            materiais_texto.append(linha)
                        else:
                            # Se não tem material, acabamento ou justificativa, formatar o dicionário inteiro
                            for chave, valor in mat.items():
                                materiais_texto.append(f"• {chave.capitalize()}: {valor}")
                    else:
                        # Se for um item simples, adicionar diretamente
                        materiais_texto.append(f"• {mat}")
                
                conceito.materiais_principais = "\n".join(materiais_texto)
            elif isinstance(materiais, dict):
                # Se for um dicionário, formatar as chaves e valores
                materiais_texto = []
                for chave, valor in materiais.items():
                    materiais_texto.append(f"• {chave.capitalize()}: {valor}")
                conceito.materiais_principais = "\n".join(materiais_texto)
            else:
                # Se for uma string, usar diretamente
                conceito.materiais_principais = str(materiais)

            # Processar elementos interativos (formato complexo - dicionário ou lista)
            elementos = conceito_data.get('elementos_interativos', {})
            if isinstance(elementos, dict):
                if 'descricao' in elementos:
                    conceito.elementos_interativos = elementos['descricao']
                else:
                    # Se não tiver descrição, formatar o dicionário inteiro
                    elementos_texto = []
                    for chave, valor in elementos.items():
                        elementos_texto.append(f"• {chave}: {valor}")
                    conceito.elementos_interativos = "\n".join(elementos_texto)
            elif isinstance(elementos, list):
                # Formatar cada elemento da lista
                elementos_texto = []
                for elem in elementos:
                    if isinstance(elem, dict):
                        tipo = elem.get('tipo', '')
                        descricao = elem.get('descricao', '')
                        if tipo and descricao:
                            elementos_texto.append(f"• {tipo}: {descricao}")
                        elif tipo:
                            elementos_texto.append(f"• {tipo}")
                        elif descricao:
                            elementos_texto.append(f"• {descricao}")
                        else:
                            # Se não tiver tipo ou descrição, formatar o dicionário inteiro
                            for chave, valor in elem.items():
                                elementos_texto.append(f"• {chave}: {valor}")
                    else:
                        elementos_texto.append(f"• {elem}")
                conceito.elementos_interativos = "\n".join(elementos_texto)
            else:
                # Se for outro formato, converter para string
                conceito.elementos_interativos = str(elementos)
            
            # Salvar o conceito
            conceito.save()
            
            # Preparar URL para redirecionamento
            redirect_url = request.build_absolute_uri(
                reverse('projetista:conceito_etapa1', args=[projeto.id])
            )
            
            return JsonResponse({
                'success': True,
                'message': 'Conceito gerado com sucesso!',
                'conceito_id': conceito.id,
                'redirect_url': redirect_url
            })
        else:
            # Log detalhado do erro
            error_msg = result.get('error', 'Erro desconhecido')
            details = result.get('details', 'Sem detalhes adicionais')
            logger.error(f"Erro ao gerar conceito: {error_msg}")
            logger.error(f"Detalhes do erro: {details}")
            
            # Fornecer uma resposta mais informativa
            return JsonResponse({
                'success': False, 
                'message': f'Erro ao gerar conceito: {error_msg}',
                'details': details if settings.DEBUG else 'Verifique os logs para mais detalhes'
            })
            
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        logger.error(f"Exceção ao gerar conceito: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': f'Erro ao processar solicitação: {str(e)}',
            'traceback': tb if settings.DEBUG else 'Verifique os logs para mais detalhes'
        }, status=500)

# Função auxiliar para verificar permissão
def verificar_permissao_projeto(user, projeto_id):
    """Verifica se o usuário tem permissão para acessar o projeto"""
    projeto = get_object_or_404(Projeto, pk=projeto_id)
    if projeto.projetista != user:
        return None
    return projeto

@login_required
def conceito_visual(request, projeto_id):
    """
    View principal que redireciona para a etapa adequada do conceito visual
    """
    projeto = get_object_or_404(Projeto, pk=projeto_id, projetista=request.user)
    
    # Verificar se já existe um conceito
    conceito = ConceitoVisual.objects.filter(projeto=projeto).order_by('-criado_em').first()
    
    if not conceito:
        # Se não existir, redirecionar para criação inicial (etapa 1)
        return redirect('projetista:conceito_etapa1', projeto_id=projeto.id)
    
    # Redirecionar para a etapa atual
    if conceito.etapa_atual == 1:
        return redirect('projetista:conceito_etapa1', projeto_id=projeto.id)
    elif conceito.etapa_atual == 2:
        return redirect('projetista:conceito_etapa2', projeto_id=projeto.id)
    elif conceito.etapa_atual == 3:
        return redirect('projetista:conceito_etapa3', projeto_id=projeto.id)
    else:
        return redirect('projetista:conceito_completo', conceito_id=conceito.id)

@login_required
def conceito_etapa1(request, projeto_id):
    """
    Etapa 1: Elaboração do conceito textual - Abordagem Unificada
    """
    projeto = get_object_or_404(Projeto, pk=projeto_id, projetista=request.user)
    
    # Obter briefing
    try:
        briefing = projeto.briefings.latest('versao')
    except Briefing.DoesNotExist:
        messages.error(request, "Não foi encontrado um briefing para este projeto.")
        return redirect('projetista:projeto_detail', pk=projeto_id)
    
    # Verificar se já existe um conceito
    conceito = ConceitoVisual.objects.filter(projeto=projeto).order_by('-criado_em').first()
    
    # Formulário para edição/visualização do conceito
    form = ConceitoVisualForm(instance=conceito) if conceito else ConceitoVisualForm()
    
    if request.method == 'POST':
        if 'gerar_conceito' in request.POST:
            # Processar geração de conceito via IA (simplificado)
            try:
                # Criar ou atualizar conceito básico
                if not conceito:
                    conceito = ConceitoVisual(
                        projeto=projeto,
                        briefing=briefing,
                        projetista=request.user,
                        etapa_atual=1,
                        ia_gerado=True
                    )
                
                # Valores temporários simplificados
                conceito.titulo = f"Conceito para {projeto.nome}"
                conceito.descricao = "Esta funcionalidade está em desenvolvimento. No futuro, a IA gerará automaticamente uma descrição baseada no briefing."
                conceito.paleta_cores = "Funcionalidade em desenvolvimento."
                conceito.materiais_principais = "Funcionalidade em desenvolvimento."
                conceito.elementos_interativos = "Funcionalidade em desenvolvimento."
                
                # Salvar o conceito
                conceito.save()
                
                messages.success(request, 'Conceito criado com sucesso! A geração automática via IA será implementada em breve. Você pode editar os campos abaixo manualmente.')
                
                # Atualizar o formulário com o conceito gerado
                form = ConceitoVisualForm(instance=conceito)
                
            except Exception as e:
                logger.error(f"Erro ao gerar conceito: {str(e)}")
                messages.error(request, f"Ocorreu um erro ao gerar o conceito: {str(e)}")
                
        elif 'salvar' in request.POST or 'avancar' in request.POST:
            # Processar edição manual após geração
            form = ConceitoVisualForm(request.POST, instance=conceito)
            if form.is_valid():
                conceito = form.save(commit=False)
                conceito.projeto = projeto
                conceito.briefing = briefing
                conceito.projetista = request.user
                conceito.etapa_atual = 1
                conceito.save()
                
                messages.success(request, 'Conceito textual salvo com sucesso!')
                
                # Verificar se o usuário clicou em "Avançar"
                if 'avancar' in request.POST and conceito.etapa_concluida(1):
                    conceito.etapa_atual = 2
                    conceito.save(update_fields=['etapa_atual'])
                    return redirect('projetista:conceito_etapa2', projeto_id=projeto.id)
                
                # Recarregar a página com o formulário atualizado
                return redirect('projetista:conceito_etapa1', projeto_id=projeto.id)
    
    context = {
        'projeto': projeto,
        'briefing': briefing,
        'conceito': conceito,
        'form': form,
        'etapa_atual': 1,
        'etapa_concluida': conceito and conceito.etapa_concluida(1),
    }
    
    # Use o template existente
    return render(request, 'projetista/conceito/etapa1_conceito.html', context)

@login_required
def conceito_etapa2(request, projeto_id):
    """
    Etapa 2: Geração da imagem principal
    """
    projeto = get_object_or_404(Projeto, pk=projeto_id, projetista=request.user)
    
    # Verificar se existe um conceito
    conceito = get_object_or_404(ConceitoVisual, projeto=projeto)
    
    # Verificar se o conceito textual está completo
    if not conceito.etapa_concluida(1):
        messages.warning(request, "Complete o conceito textual antes de prosseguir.")
        return redirect('projetista:conceito_etapa1', projeto_id=projeto.id)
    
    # Obter imagem principal se existir
    imagem_principal = conceito.imagens.filter(principal=True).first()
    
    # Formulário para geração de imagem
    form_geracao = GeracaoImagemForm()
    
    # Formulário para upload manual
    form_upload = ImagemConceitoForm()
    
    # Formulário para modificação
    form_modificacao = ModificacaoImagemForm() if imagem_principal else None
    
    if request.method == 'POST':
        if 'gerar_imagem' in request.POST:
            # Simulação de geração de imagem via IA (será implementada posteriormente)
            form_geracao = GeracaoImagemForm(request.POST)
            if form_geracao.is_valid():
                # Aqui entraria a lógica real de geração via IA
                messages.info(request, "A funcionalidade de geração automática será implementada em breve.")
        
        elif 'upload_imagem' in request.POST:
            # Processar upload manual de imagem
            form_upload = ImagemConceitoForm(request.POST, request.FILES)
            if form_upload.is_valid():
                imagem = form_upload.save(commit=False)
                imagem.conceito = conceito
                imagem.principal = True
                
                # Se já existir uma imagem principal, desmarcar como principal
                if imagem_principal:
                    imagem_principal.principal = False
                    imagem_principal.save(update_fields=['principal'])
                
                imagem.save()
                
                messages.success(request, 'Imagem principal adicionada com sucesso!')
                return redirect('projetista:conceito_etapa2', projeto_id=projeto.id)
        
        elif 'modificar_imagem' in request.POST and imagem_principal:
            # Simulação de modificação de imagem via IA (será implementada posteriormente)
            form_modificacao = ModificacaoImagemForm(request.POST)
            if form_modificacao.is_valid():
                # Aqui entraria a lógica real de modificação via IA
                messages.info(request, "A funcionalidade de modificação será implementada em breve.")
        
        elif 'remover_imagem' in request.POST:
            imagem_id = request.POST.get('imagem_id')
            if imagem_id:
                try:
                    imagem = get_object_or_404(ImagemConceitoVisual, pk=imagem_id, conceito=conceito)
                    imagem.delete()
                    messages.success(request, 'Imagem removida com sucesso!')
                    return redirect('projetista:conceito_etapa2', projeto_id=projeto.id)
                except Exception as e:
                    messages.error(request, f'Erro ao remover imagem: {str(e)}')
        
        elif 'avancar' in request.POST:
            # Avançar para a próxima etapa se houver uma imagem principal
            if conceito.etapa_concluida(2):
                conceito.etapa_atual = 3
                conceito.save(update_fields=['etapa_atual'])
                return redirect('projetista:conceito_etapa3', projeto_id=projeto.id)
            else:
                messages.warning(request, "É necessário ter uma imagem principal para avançar.")
        
        elif 'voltar' in request.POST:
            # Voltar para a etapa anterior
            conceito.etapa_atual = 1
            conceito.save(update_fields=['etapa_atual'])
            return redirect('projetista:conceito_etapa1', projeto_id=projeto.id)
    
    context = {
        'projeto': projeto,
        'conceito': conceito,
        'imagem_principal': imagem_principal,
        'form_geracao': form_geracao,
        'form_upload': form_upload,
        'form_modificacao': form_modificacao,
        'etapa_atual': 2,
        'etapa_concluida': conceito.etapa_concluida(2),
    }
    
    return render(request, 'projetista/conceito/etapa2_imagem.html', context)

@login_required
def conceito_etapa3(request, projeto_id):
    """
    Etapa 3: Geração de múltiplas vistas
    """
    projeto = get_object_or_404(Projeto, pk=projeto_id, projetista=request.user)
    
    # Verificar se existe um conceito
    conceito = get_object_or_404(ConceitoVisual, projeto=projeto)
    
    # Verificar se a imagem principal existe
    if not conceito.etapa_concluida(2):
        messages.warning(request, "Defina uma imagem principal antes de prosseguir.")
        return redirect('projetista:conceito_etapa2', projeto_id=projeto.id)
    
    # Obter a imagem principal
    imagem_principal = conceito.imagens.filter(principal=True).first()
    
    # Obter as outras imagens (vistas complementares)
    imagens_complementares = conceito.imagens.filter(principal=False)
    
    # Agrupar imagens por categoria
    imagens_por_categoria = {}
    for angulo, nome in ImagemConceitoVisual.ANGULOS_CHOICES:
        imagens_por_categoria[angulo] = imagens_complementares.filter(angulo_vista=angulo)
    
    # Formulário para geração de vistas adicionais
    form_geracao = GeracaoImagemForm()
    
    # Formulário para upload manual
    form_upload = ImagemConceitoForm()
    
    if request.method == 'POST':
        if 'gerar_vistas' in request.POST:
            # Simulação de geração de múltiplas vistas via IA (será implementada posteriormente)
            form_geracao = GeracaoImagemForm(request.POST)
            if form_geracao.is_valid():
                # Aqui entraria a lógica real de geração via IA
                messages.info(request, "A funcionalidade de geração automática de vistas adicionais será implementada em breve.")
        
        elif 'upload_imagem' in request.POST:
            # Processar upload manual de imagem complementar
            form_upload = ImagemConceitoForm(request.POST, request.FILES)
            if form_upload.is_valid():
                imagem = form_upload.save(commit=False)
                imagem.conceito = conceito
                imagem.principal = False
                imagem.save()
                
                messages.success(request, 'Vista adicional adicionada com sucesso!')
                return redirect('projetista:conceito_etapa3', projeto_id=projeto.id)
        
        elif 'remover_imagem' in request.POST:
            imagem_id = request.POST.get('imagem_id')
            if imagem_id:
                try:
                    imagem = get_object_or_404(ImagemConceitoVisual, pk=imagem_id, conceito=conceito)
                    imagem.delete()
                    messages.success(request, 'Imagem removida com sucesso!')
                    return redirect('projetista:conceito_etapa3', projeto_id=projeto.id)
                except Exception as e:
                    messages.error(request, f'Erro ao remover imagem: {str(e)}')
        
        elif 'concluir' in request.POST:
            # Concluir o processo de conceito visual
            if conceito.etapa_concluida(3):
                conceito.etapa_atual = 4
                conceito.status = 'finalizado'
                conceito.save(update_fields=['etapa_atual', 'status'])
                return redirect('projetista:conceito_completo', conceito_id=conceito.id)
            else:
                messages.warning(request, "É necessário ter pelo menos 3 vistas diferentes para concluir.")
        
        elif 'voltar' in request.POST:
            # Voltar para a etapa anterior
            conceito.etapa_atual = 2
            conceito.save(update_fields=['etapa_atual'])
            return redirect('projetista:conceito_etapa2', projeto_id=projeto.id)
    
    context = {
        'projeto': projeto,
        'conceito': conceito,
        'imagem_principal': imagem_principal,
        'imagens_complementares': imagens_complementares,
        'imagens_por_categoria': imagens_por_categoria,
        'total_vistas': imagens_complementares.count(),
        'form_geracao': form_geracao,
        'form_upload': form_upload,
        'etapa_atual': 3,
        'etapa_concluida': conceito.etapa_concluida(3),
    }
    
    return render(request, 'projetista/conceito/etapa3_vistas.html', context)

@login_required
def conceito_completo(request, conceito_id):
    """
    Visualização do conceito visual completo
    """
    conceito = get_object_or_404(ConceitoVisual, pk=conceito_id)
    projeto = conceito.projeto
    
    # Verificar permissão
    if projeto.projetista != request.user:
        messages.error(request, 'Você não tem permissão para acessar este conceito.')
        return redirect('projetista:projeto_list')
    
    # Obter a imagem principal
    imagem_principal = conceito.imagens.filter(principal=True).first()
    
    # Agrupar imagens por categoria
    imagens_por_categoria = {}
    for angulo, nome in ImagemConceitoVisual.ANGULOS_CHOICES:
        imagens_por_categoria[angulo] = conceito.imagens.filter(angulo_vista=angulo)
    
    # Formulário de exportação
    form_exportacao = ExportacaoConceitoForm()
    
    if request.method == 'POST':
        if 'exportar' in request.POST:
            form_exportacao = ExportacaoConceitoForm(request.POST)
            if form_exportacao.is_valid():
                # Aqui entraria a lógica de exportação (será implementada posteriormente)
                messages.info(request, "A funcionalidade de exportação será implementada em breve.")
    
    context = {
        'conceito': conceito,
        'projeto': projeto,
        'imagem_principal': imagem_principal,
        'imagens_por_categoria': imagens_por_categoria,
        'total_imagens': conceito.imagens.count(),
        'form_exportacao': form_exportacao,
    }
    
    return render(request, 'projetista/conceito/conceito_completo.html', context)

@login_required
@require_POST
def gerar_imagem_ia(request, conceito_id):
    """
    View para geração automática de imagem principal via IA
    """
    conceito = get_object_or_404(ConceitoVisual, pk=conceito_id)
    projeto = conceito.projeto
    
    # Verificar permissão
    if projeto.projetista != request.user:
        return JsonResponse({
            'success': False,
            'message': 'Você não tem permissão para acessar este conceito.'
        }, status=403)
    
    # Na implementação real, aqui seria feita a chamada para o Agente de Imagem Principal
    
    # Por enquanto, apenas retornar uma mensagem
    return JsonResponse({
        'success': False,
        'message': 'Esta funcionalidade será implementada em breve.'
    })

@login_required
@require_POST
def gerar_vistas_ia(request, conceito_id):
    """
    View para geração automática de múltiplas vistas via IA
    """
    conceito = get_object_or_404(ConceitoVisual, pk=conceito_id)
    projeto = conceito.projeto
    
    # Verificar permissão
    if projeto.projetista != request.user:
        return JsonResponse({
            'success': False,
            'message': 'Você não tem permissão para acessar este conceito.'
        }, status=403)
    
    # Na implementação real, aqui seria feita a chamada para o Agente de Múltiplas Vistas
    
    # Por enquanto, apenas retornar uma mensagem
    return JsonResponse({
        'success': False,
        'message': 'Esta funcionalidade será implementada em breve.'
    })

@login_required
@require_POST
def modificar_imagem_ia(request, imagem_id):
    """
    View para modificação de imagem existente via IA
    """
    imagem = get_object_or_404(ImagemConceitoVisual, pk=imagem_id)
    conceito = imagem.conceito
    projeto = conceito.projeto
    
    # Verificar permissão
    if projeto.projetista != request.user:
        return JsonResponse({
            'success': False,
            'message': 'Você não tem permissão para acessar este conceito.'
        }, status=403)
    
    # Na implementação real, aqui seria feita a chamada para o Agente de Imagem Principal
    # para modificação da imagem existente
    
    # Por enquanto, apenas retornar uma mensagem
    return JsonResponse({
        'success': False,
        'message': 'Esta funcionalidade será implementada em breve.'
    })

@login_required
def exportar_conceito(request, conceito_id, formato='pdf'):
    """
    View para exportação do conceito visual em diferentes formatos
    """
    conceito = get_object_or_404(ConceitoVisual, pk=conceito_id)
    projeto = conceito.projeto
    
    # Verificar permissão
    if projeto.projetista != request.user:
        messages.error(request, 'Você não tem permissão para acessar este conceito.')
        return redirect('projetista:projeto_list')
    
    # Na implementação real, aqui seria feita a geração do arquivo no formato solicitado
    
    # Por enquanto, apenas retornar uma mensagem
    messages.info(request, f"A exportação em formato {formato} será implementada em breve.")
    return redirect('projetista:conceito_completo', conceito_id=conceito.id)


@login_required
def gerar_conceito(request, projeto_id):
    return conceito_visual(request, projeto_id)

@login_required
def conceito_detalhes(request, conceito_id):
    conceito = get_object_or_404(ConceitoVisual, pk=conceito_id)
    return conceito_completo(request, conceito_id)

@login_required
def upload_imagem(request, conceito_id):
    # Verificar se o conceito existe
    conceito = get_object_or_404(ConceitoVisual, pk=conceito_id)
    # Verificar permissão
    if conceito.projeto.projetista != request.user:
        return JsonResponse({
            'status': 'error',
            'message': 'Permissão negada'
        }, status=403)

    if request.method == 'POST':
        form = ImagemConceitoForm(request.POST, request.FILES)
        if form.is_valid():
            imagem = form.save(commit=False)
            imagem.conceito = conceito
            imagem.ordem = conceito.imagens.count() + 1
            
            # Definir como principal se for perspectiva e não houver imagem principal
            if imagem.angulo_vista == 'perspectiva' and not conceito.imagens.filter(principal=True).exists():
                imagem.principal = True
            
            imagem.save()
            
            return JsonResponse({
                'status': 'success',
                'message': 'Imagem adicionada com sucesso',
                'id': imagem.id,
                'url': imagem.imagem.url
            })
        
        return JsonResponse({
            'status': 'error',
            'message': 'Formulário inválido',
            'errors': form.errors
        }, status=400)

    # Redirecionar para a etapa adequada com base no status do conceito
    if conceito.etapa_atual == 1:
        return redirect('projetista:conceito_etapa1', projeto_id=conceito.projeto.id)
    elif conceito.etapa_atual == 2:
        return redirect('projetista:conceito_etapa2', projeto_id=conceito.projeto.id)
    elif conceito.etapa_atual == 3:
        return redirect('projetista:conceito_etapa3', projeto_id=conceito.projeto.id)
    else:
        return redirect('projetista:conceito_completo', conceito_id=conceito.id)

@login_required
def excluir_imagem(request, imagem_id):
    imagem = get_object_or_404(ImagemConceitoVisual, pk=imagem_id)
    conceito = imagem.conceito
    # Verificar permissão
    if conceito.projeto.projetista != request.user:
        messages.error(request, 'Permissão negada.')
        return redirect('projetista:projeto_list')

    if request.method == 'POST':
        imagem.delete()
        messages.success(request, 'Imagem excluída com sucesso.')

    # Redirecionar para a etapa adequada com base no status do conceito
    if conceito.etapa_atual == 1:
        return redirect('projetista:conceito_etapa1', projeto_id=conceito.projeto.id)
    elif conceito.etapa_atual == 2:
        return redirect('projetista:conceito_etapa2', projeto_id=conceito.projeto.id)
    elif conceito.etapa_atual == 3:
        return redirect('projetista:conceito_etapa3', projeto_id=conceito.projeto.id)
    else:
        return redirect('projetista:conceito_completo', conceito_id=conceito.id)