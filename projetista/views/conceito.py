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
    ExportacaoConceitoForm,
    GeracaoMultiplasVistasForm, FiltroVistasForm
)

import logging
import requests
import base64
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
            paleta_cores = conceito_data.get('paleta_cores', {})
            materiais = conceito_data.get('materiais_principais', [])
            elementos = conceito_data.get('elementos_interativos', {})
            
            # Para paleta de cores
            if isinstance(paleta_cores, list):
                cores_formatadas = []
                for cor in paleta_cores:
                    if isinstance(cor, dict):
                        # Verificar várias possíveis chaves
                        nome = cor.get('cor', 
                                    cor.get('nome', 
                                            cor.get('color', 
                                                    cor.get('hex', ''))))
                        descricao = cor.get('descricao', 
                                        cor.get('description', ''))
                        
                        if nome:
                            linha = f"• {nome}"
                            if descricao:
                                linha += f": {descricao}"
                        else:
                            # Se não encontrou chaves específicas, usar a primeira chave do dicionário
                            if cor:
                                chave = list(cor.keys())[0]
                                valor = cor[chave]
                                if isinstance(valor, str):
                                    linha = f"• {chave}: {valor}"
                                elif isinstance(valor, list) and valor:  # Se for uma lista de cores
                                    subcores = []
                                    for subcor in valor:
                                        if isinstance(subcor, dict):
                                            subcor_nome = subcor.get('cor', subcor.get('nome', ''))
                                            subcor_desc = subcor.get('descricao', '')
                                            if subcor_nome:
                                                subcor_texto = f"{subcor_nome}"
                                                if subcor_desc:
                                                    subcor_texto += f" - {subcor_desc}"
                                                subcores.append(subcor_texto)
                                        elif isinstance(subcor, str):
                                            subcores.append(subcor)
                                    linha = f"• {chave}: {', '.join(subcores)}"
                                else:
                                    linha = f"• {chave}"
                            else:
                                linha = "• Cor não especificada"
                            
                        cores_formatadas.append(linha)
                
                conceito.paleta_cores = "\n".join(cores_formatadas)
            elif isinstance(paleta_cores, dict):
                # Se for um dicionário com categorias de cores
                cores_formatadas = []
                for categoria, cores in paleta_cores.items():
                    if isinstance(cores, list):
                        # Lista de cores dentro de uma categoria
                        subcores = []
                        for cor in cores:
                            if isinstance(cor, dict):
                                cor_nome = cor.get('cor', cor.get('nome', ''))
                                cor_desc = cor.get('descricao', '')
                                if cor_nome:
                                    subcor_texto = f"{cor_nome}"
                                    if cor_desc:
                                        subcor_texto += f" - {cor_desc}"
                                    subcores.append(subcor_texto)
                            elif isinstance(cor, str):
                                subcores.append(cor)
                        
                        if subcores:
                            cores_formatadas.append(f"• {categoria.capitalize()}: {', '.join(subcores)}")
                
                conceito.paleta_cores = "\n".join(cores_formatadas)

            # Para materiais principais
            if isinstance(materiais, list):
                materiais_texto = []
                for mat in materiais:
                    if isinstance(mat, dict):
                        material_nome = mat.get('material', '')
                        acabamento = mat.get('acabamento', '')
                        linha = f"• {material_nome}"
                        if acabamento:
                            linha += f": {acabamento}"
                        materiais_texto.append(linha)
                
                conceito.materiais_principais = "\n".join(materiais_texto)

                # Para elementos interativos
                if isinstance(elementos, list):
                    elementos_texto = []
                    for elem in elementos:
                        if isinstance(elem, dict):
                            # Verificar várias possíveis chaves para o nome do elemento
                            elemento = elem.get('elemento', 
                                            elem.get('nome', 
                                                    elem.get('tipo', 
                                                            elem.get('title', ''))))
                            descricao = elem.get('descricao', 
                                                elem.get('description', 
                                                        elem.get('texto', '')))
                            
                            if elemento:
                                linha = f"• {elemento}"
                                if descricao:
                                    linha += f": {descricao}"
                            else:
                                # Se não encontrou nenhuma chave específica, usar a primeira chave do dicionário
                                if elem:
                                    chave = list(elem.keys())[0]
                                    valor = elem[chave]
                                    linha = f"• {chave}: {valor}"
                                else:
                                    linha = "• Item não especificado"
                                    
                            elementos_texto.append(linha)
                    
                    conceito.elementos_interativos = "\n".join(elementos_texto)

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
    
    # Histórico de versões (se existir imagem principal)
    versoes_anteriores = []
    if imagem_principal:
        # Obter versões anteriores da imagem
        versoes_anteriores = conceito.imagens.filter(
            principal=False,  # Não são mais a principal
            angulo_vista='perspectiva'  # Mesmo ângulo da principal
        ).order_by('-versao')[:5]  # Mostrar até 5 versões anteriores
    
    # Formulário para geração de imagem
    form_geracao = GeracaoImagemForm()
    
    # Formulário para upload manual
    form_upload = ImagemConceitoForm()
    
    # Formulário para modificação
    form_modificacao = ModificacaoImagemForm() if imagem_principal else None
    
    if request.method == 'POST':
        if 'gerar_imagem' in request.POST:
            # Processar geração de imagem via IA
            estilo_visualizacao = request.POST.get('estilo_visualizacao', 'fotorrealista')
            iluminacao = request.POST.get('iluminacao', 'diurna')
            instrucoes_adicionais = request.POST.get('instrucoes_adicionais', '')
            
            try:
                # Obter agente de imagem principal
                try:
                    agente = Agente.objects.get(nome='Agente de Imagem Principal')
                    
                    # Verificar se o agente está ativo
                    if not agente.ativo:
                        messages.warning(request, 'O Agente de Imagem Principal está inativo. Por favor, contate o administrador.')
                        return redirect('projetista:conceito_etapa2', projeto_id=projeto.id)
                        
                except Agente.DoesNotExist:
                    messages.warning(request, 'Agente de Imagem Principal não encontrado. Por favor, cadastre este agente no painel de administração.')
                    return redirect('projetista:conceito_etapa2', projeto_id=projeto.id)
                
                # Inicializar serviço
                from core.services.imagem_principal_service import ImagemPrincipalService
                imagem_service = ImagemPrincipalService(agente)
                
                # Gerar imagem
                result = imagem_service.gerar_imagem_principal(
                    conceito, 
                    estilo_visualizacao=estilo_visualizacao,
                    iluminacao=iluminacao,
                    instrucoes_adicionais=instrucoes_adicionais
                )
                
                if result['success']:
                    # Se já existir uma imagem principal, desmarcar como principal
                    if imagem_principal:
                        imagem_principal.principal = False
                        imagem_principal.save(update_fields=['principal'])
                    
                    # Criar nova imagem
                    img_data = result['image_data']
                    filename = result['filename']
                    
                    # Criar objeto de imagem
                    nova_imagem = ImagemConceitoVisual(
                        conceito=conceito,
                        descricao=f"Perspectiva principal ({estilo_visualizacao}, {iluminacao})",
                        angulo_vista='perspectiva',
                        principal=True,
                        ia_gerada=True,
                        versao=1 if not imagem_principal else imagem_principal.versao + 1,
                        imagem_anterior=imagem_principal,
                        prompt_geracao=result['prompt_used']
                    )
                    
                    # Criar ContentFile a partir dos dados da imagem
                    from django.core.files.base import ContentFile
                    file_content = ContentFile(img_data)
                    nova_imagem.imagem.save(filename, file_content, save=False)
                    nova_imagem.save()
                    
                    messages.success(request, 'Imagem principal gerada com sucesso!')
                    return redirect('projetista:conceito_etapa2', projeto_id=projeto.id)
                else:
                    messages.error(request, f"Erro ao gerar imagem: {result.get('error', 'Erro desconhecido')}")
                    
            except Exception as e:
                import traceback
                tb = traceback.format_exc()
                logger.error(f"Erro ao gerar imagem principal: {str(e)}", exc_info=True)
                messages.error(request, f"Erro ao processar solicitação: {str(e)}")
        
        elif 'upload_imagem' in request.POST:
            # Processar upload manual de imagem
            form_upload = ImagemConceitoForm(request.POST, request.FILES)
            if form_upload.is_valid():
                imagem = form_upload.save(commit=False)
                imagem.conceito = conceito
                imagem.principal = True
                imagem.angulo_vista = 'perspectiva'  # Forçar ângulo perspectiva
                
                # Se já existir uma imagem principal, desmarcar como principal
                if imagem_principal:
                    imagem_principal.principal = False
                    imagem_principal.save(update_fields=['principal'])
                    
                    # Definir versão e relacionamento
                    imagem.versao = imagem_principal.versao + 1
                    imagem.imagem_anterior = imagem_principal
                else:
                    imagem.versao = 1
                
                imagem.save()
                
                messages.success(request, 'Imagem principal adicionada com sucesso!')
                return redirect('projetista:conceito_etapa2', projeto_id=projeto.id)
        
        elif 'modificar_imagem' in request.POST and imagem_principal:
            # Processar modificação de imagem
            instrucoes_modificacao = request.POST.get('instrucoes_modificacao', '')
            imagem_id = request.POST.get('imagem_id')
            
            if not instrucoes_modificacao.strip():
                messages.warning(request, "Por favor, forneça instruções para modificação da imagem.")
                return redirect('projetista:conceito_etapa2', projeto_id=projeto.id)
            
            try:
                # Obter a imagem a ser modificada
                imagem = get_object_or_404(ImagemConceitoVisual, pk=imagem_id, conceito=conceito)
                
                # Obter agente de imagem principal
                try:
                    agente = Agente.objects.get(nome='Agente de Imagem Principal')
                    if not agente.ativo:
                        messages.warning(request, 'O Agente de Imagem Principal está inativo.')
                        return redirect('projetista:conceito_etapa2', projeto_id=projeto.id)
                except Agente.DoesNotExist:
                    messages.warning(request, 'Agente de Imagem Principal não encontrado.')
                    return redirect('projetista:conceito_etapa2', projeto_id=projeto.id)
                
                # Inicializar serviço
                from core.services.imagem_principal_service import ImagemPrincipalService
                imagem_service = ImagemPrincipalService(agente)
                
                # Obter prompt original e adicionar modificações
                prompt_original = imagem.prompt_geracao or "Estande em perspectiva 3/4"
                prompt_atualizado = f"{prompt_original}\n\nMODIFICAÇÕES ADICIONAIS:\n{instrucoes_modificacao}"
                
                # Limitar tamanho do prompt
                if len(prompt_atualizado) > 4000:
                    prompt_atualizado = prompt_atualizado[:4000]
                
                # Gerar nova versão da imagem
                result = imagem_service._gerar_imagem_com_api(prompt_atualizado)
                
                if result['success']:
                    # Desmarcar imagem atual como principal
                    imagem.principal = False
                    imagem.save(update_fields=['principal'])
                    
                    # Criar nova imagem (nova versão)
                    img_data = result['image_data']
                    filename = f"estande_{conceito.id}_v{imagem.versao + 1}.png"
                    
                    # Criar objeto de imagem
                    nova_imagem = ImagemConceitoVisual(
                        conceito=conceito,
                        descricao=f"{imagem.descricao} (refinada)",
                        angulo_vista='perspectiva',
                        principal=True,
                        ia_gerada=True,
                        versao=imagem.versao + 1,
                        imagem_anterior=imagem,
                        prompt_geracao=prompt_atualizado
                    )
                    
                    # Criar ContentFile a partir dos dados da imagem
                    from django.core.files.base import ContentFile
                    file_content = ContentFile(img_data)
                    nova_imagem.imagem.save(filename, file_content, save=False)
                    nova_imagem.save()
                    
                    messages.success(request, 'Imagem refinada com sucesso!')
                    return redirect('projetista:conceito_etapa2', projeto_id=projeto.id)
                else:
                    messages.error(request, f"Erro ao refinar imagem: {result.get('error', 'Erro desconhecido')}")
                
            except Exception as e:
                logger.error(f"Erro ao modificar imagem: {str(e)}", exc_info=True)
                messages.error(request, f"Erro ao processar modificação: {str(e)}")
        
        elif 'restaurar_versao' in request.POST:
            # Restaurar uma versão anterior como principal
            versao_id = request.POST.get('versao_id')
            if versao_id:
                try:
                    # Obter a versão a ser restaurada
                    versao = get_object_or_404(ImagemConceitoVisual, pk=versao_id, conceito=conceito)
                    
                    # Desmarcar imagem atual como principal
                    if imagem_principal:
                        imagem_principal.principal = False
                        imagem_principal.save(update_fields=['principal'])
                    
                    # Marcar versão selecionada como principal
                    versao.principal = True
                    versao.save(update_fields=['principal'])
                    
                    messages.success(request, 'Versão anterior restaurada como principal!')
                    return redirect('projetista:conceito_etapa2', projeto_id=projeto.id)
                except Exception as e:
                    messages.error(request, f'Erro ao restaurar versão: {str(e)}')
        
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
        'versoes_anteriores': versoes_anteriores,
        'form_geracao': form_geracao,
        'form_upload': form_upload,
        'form_modificacao': form_modificacao,
        'etapa_atual': 2,
        'etapa_concluida': conceito.etapa_concluida(2),
    }
    
    return render(request, 'projetista/conceito/etapa2_imagem.html', context)

# Método auxiliar para gerar imagem com API
def _gerar_imagem_com_api(self, prompt):
    """Método auxiliar para gerar imagem usando a API DALL-E"""
    try:
        # Chamada à API da OpenAI (DALL-E 3)
        response = requests.post(
            "https://api.openai.com/v1/images/generations",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            },
            json={
                "model": self.model,
                "prompt": prompt,
                "n": 1,
                "size": "1024x1024",
                "response_format": "b64_json"
            }
        )
        
        if response.status_code == 200:
            result = response.json()
            image_data = result['data'][0]['b64_json']
            
            # Convertendo base64 para arquivo de imagem
            img_data = base64.b64decode(image_data)
            
            return {
                'success': True,
                'image_data': img_data,
                'prompt_used': prompt,
                'raw_response': result
            }
        else:
            logger.error(f"Erro na API DALL-E: {response.status_code} - {response.text}")
            return {
                'success': False,
                'error': f"Erro na API: {response.status_code}",
                'details': response.text
            }
    
    except Exception as e:
        logger.error(f"Exceção ao gerar imagem: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }

@login_required
def conceito_etapa3(request, projeto_id):
    """
    Etapa 3: Geração de múltiplas vistas - Versão Simplificada
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
    
    # Obter as outras imagens (vistas complementares) organizadas por categoria
    imagens_por_categoria = {}
    for categoria_code, categoria_nome in ImagemConceitoVisual.CATEGORIA_CHOICES:
        imagens_por_categoria[categoria_code] = conceito.imagens.filter(
            categoria=categoria_code, 
            principal=False
        ).order_by('ordem', 'criado_em')
    
    # Estatísticas das vistas
    total_vistas = conceito.imagens.filter(principal=False).count()
    vistas_essenciais = conceito.imagens.filter(essencial_fotogrametria=True).count()
    completude_fotogrametria = conceito.get_completude_fotogrametria()
    
    # Formulários
    form_geracao_multiplas = GeracaoMultiplasVistasForm()
    form_upload = ImagemConceitoForm()
    form_filtro = FiltroVistasForm()
    
    if request.method == 'POST':
        if 'gerar_multiplas_vistas' in request.POST:
            form_geracao_multiplas = GeracaoMultiplasVistasForm(request.POST)
            if form_geracao_multiplas.is_valid():
                try:
                    # Obter agente de múltiplas vistas
                    try:
                        agente = Agente.objects.get(nome='Agente de Múltiplas Vistas')
                        if not agente.ativo:
                            messages.warning(request, 'O Agente de Múltiplas Vistas está inativo.')
                            return redirect('projetista:conceito_etapa3', projeto_id=projeto.id)
                    except Agente.DoesNotExist:
                        messages.warning(request, 'Agente de Múltiplas Vistas não encontrado.')
                        return redirect('projetista:conceito_etapa3', projeto_id=projeto.id)
                    
                    # Coletar vistas selecionadas dos checkboxes
                    vistas_para_gerar = []
                    vistas_para_gerar.extend(form_geracao_multiplas.cleaned_data.get('vistas_cliente', []))
                    vistas_para_gerar.extend(form_geracao_multiplas.cleaned_data.get('vistas_externas', []))
                    vistas_para_gerar.extend(form_geracao_multiplas.cleaned_data.get('plantas_elevacoes', []))
                    vistas_para_gerar.extend(form_geracao_multiplas.cleaned_data.get('vistas_internas', []))
                    vistas_para_gerar.extend(form_geracao_multiplas.cleaned_data.get('detalhes', []))
                    
                    if not vistas_para_gerar:
                        messages.warning(request, 'Selecione pelo menos uma vista para gerar.')
                        return redirect('projetista:conceito_etapa3', projeto_id=projeto.id)
                    
                    # Filtrar vistas que já existem
                    vistas_existentes = conceito.imagens.values_list('angulo_vista', flat=True)
                    vistas_para_gerar = [v for v in vistas_para_gerar if v not in vistas_existentes]
                    
                    if not vistas_para_gerar:
                        messages.info(request, 'Todas as vistas selecionadas já existem.')
                        return redirect('projetista:conceito_etapa3', projeto_id=projeto.id)
                    
                    # Inicializar serviço de múltiplas vistas
                    from core.services.multiplas_vistas_service import MultiplasVistasService
                    multiplas_service = MultiplasVistasService(agente)
                    
                    # Configurações de geração
                    config_geracao = {
                        'estilo_visualizacao': form_geracao_multiplas.cleaned_data.get('estilo_visualizacao', 'fotorrealista'),
                        'iluminacao': form_geracao_multiplas.cleaned_data.get('iluminacao', 'diurna'),
                        'instrucoes_adicionais': form_geracao_multiplas.cleaned_data.get('instrucoes_adicionais', ''),
                        'prioridade_cliente': form_geracao_multiplas.cleaned_data.get('prioridade_cliente', False)
                    }
                    
                    # Gerar vistas
                    result = multiplas_service.gerar_multiplas_vistas(
                        conceito, 
                        imagem_principal,
                        vistas_para_gerar,
                        **config_geracao
                    )
                    
                    if result['success']:
                        total_geradas = len(result['vistas_geradas'])
                        total_falharam = len(result['vistas_falharam'])
                        
                        if total_geradas > 0:
                            messages.success(request, f"{total_geradas} vistas geradas com sucesso!")
                        
                        if total_falharam > 0:
                            vistas_com_erro = [f['vista'] for f in result['vistas_falharam']]
                            messages.warning(request, f"{total_falharam} vistas falharam: {', '.join(vistas_com_erro)}")
                            
                        return redirect('projetista:conceito_etapa3', projeto_id=projeto.id)
                    else:
                        messages.error(request, f"Erro ao gerar vistas: {result.get('error', 'Erro desconhecido')}")
                        
                except Exception as e:
                    logger.error(f"Erro ao gerar múltiplas vistas: {str(e)}", exc_info=True)
                    messages.error(request, f"Erro ao processar solicitação: {str(e)}")
            else:
                # Mostrar erros de validação do formulário
                for field, errors in form_geracao_multiplas.errors.items():
                    for error in errors:
                        messages.error(request, f"{field}: {error}")
        
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
        
        # IMPORTANTE: Se chegou até aqui (POST sem match), redirecionar
        return redirect('projetista:conceito_etapa3', projeto_id=projeto.id)
    
    # Preparar context para GET ou after POST
    context = {
        'projeto': projeto,
        'conceito': conceito,
        'imagem_principal': imagem_principal,
        'imagens_por_categoria': imagens_por_categoria,
        'total_vistas': total_vistas,
        'vistas_essenciais': vistas_essenciais,
        'completude_fotogrametria': completude_fotogrametria,
        'form_geracao_multiplas': form_geracao_multiplas,
        'form_upload': form_upload,
        'form_filtro': form_filtro,
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