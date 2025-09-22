# gestor/views/conceito_visual.py

import json
import logging
import re
from typing import Dict, Any, List, Optional

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from core.decorators import gestor_required
from core.models import Agente
from projetos.models import Projeto

logger = logging.getLogger(__name__)

# ========================== Funções Helper Básicas ==========================

def _briefing(projeto: Projeto):
    """Retorna o primeiro briefing relacionado ao projeto."""
    return projeto.briefings.first() if hasattr(projeto, 'briefings') else None

def _arquivos(briefing_obj, tipo: str) -> List[Any]:
    """Retorna uma lista de arquivos do briefing por tipo."""
    if not briefing_obj:
        return []
    return list(briefing_obj.arquivos.filter(tipo=tipo))

def _run_agent(nome_agente: str, payload: Dict[str, Any], imagens: Optional[List[str]] = None) -> Dict[str, Any]:
    """Executa agente se disponível"""
    try:
        from .agents_crews import run_agent as RUN_AGENT_EXECUTOR
        resultado = RUN_AGENT_EXECUTOR(nome_agente, payload, imagens)
        if not resultado or "erro" in resultado:
            return {"erro": resultado.get("erro", "Agente não retornou resultado válido"), "sucesso": False}
        return resultado
    except Exception as e:
        logger.error(f"Erro ao executar agente: {str(e)}")
        return {"erro": f"Sistema de agentes não disponível", "sucesso": False}

# ========================== Função Principal: Gerar Prompt ==========================

def gerar_prompt_completo(projeto: Projeto, prompt_customizado: Optional[str] = None) -> str:
    """
    Gera prompt final para DALL-E usando:
    - Template do task_instructions (NÃO usa system_prompt)
    - Dados do briefing, layout e inspirações
    - Formatadores com regras fixas no código
    """
    
    # 1. Se forneceu prompt customizado, retornar ele
    if prompt_customizado:
        return prompt_customizado
    
    # 2. Buscar APENAS o template (task_instructions)
    try:
        agente = Agente.objects.get(
            nome="Agente de Imagem Principal", 
            tipo="individual", 
            ativo=True
        )
        template = agente.task_instructions  # NÃO concatena com system_prompt
        
        if not template:
            raise ValueError("Template vazio")
            
    except (Agente.DoesNotExist, ValueError) as e:
        logger.error(f"Erro ao buscar template: {e}")
        # Template fallback mínimo mas completo
        template = """Estande [TIPO_STAND] para [EMPRESA], [LARGURA]×[PROFUNDIDADE]×3m.
Layout: [LAYOUT_AREAS_DETALHADO]
Design: [ESTILO_VISUAL]
Cores: [CORES_APLICADAS]
Materiais: [MATERIAIS_DETALHADOS]
Perspectiva 3/4 fotorrealística."""
    
    # 3. Carregar os 3 conjuntos de dados
    briefing = projeto.briefings.first()
    layout = projeto.layout_identificado or {}
    inspiracoes = projeto.inspiracoes_visuais or {}
    
    # 4. Importar TODOS os formatadores do arquivo correto
    try:
        from gestor.services.prompt_formatters import (
            interpretar_tipo_stand,
            interpretar_estrutura,
            interpretar_piso,
            formatar_layout_areas_detalhado,
            formatar_cores_aplicadas,
            formatar_materiais_detalhados,
            formatar_elementos_destaque,
            formatar_iluminacao,
            formatar_estilo,
            extrair_areas_por_categoria,
            determinar_lado_perspectiva,
            formatar_lados_abertos,
            formatar_mobiliario,
            formatar_equipamentos
        )
    except ImportError as e:
        logger.error(f"Erro ao importar formatadores: {e}")
        # Se não conseguir importar, usar funções inline básicas
        def interpretar_tipo_stand(t): return t
        def interpretar_estrutura(e): return e
        def interpretar_piso(p): return p
        def formatar_layout_areas_detalhado(l): return "Layout padrão"
        def formatar_cores_aplicadas(i): return "Cores padrão"
        def formatar_materiais_detalhados(i): return "Materiais padrão"
        def formatar_elementos_destaque(i): return "Elementos padrão"
        def formatar_iluminacao(i): return "LED 4000K"
        def formatar_estilo(i): return "moderno"
        def extrair_areas_por_categoria(l, c): return "áreas padrão"
        def determinar_lado_perspectiva(l): return "direita"
        def formatar_lados_abertos(l): return "frente"
        def formatar_mobiliario(b, l): return "mobiliário padrão"
        def formatar_equipamentos(b): return "equipamentos padrão"
    
    # 5. Processar dados básicos
    empresa = projeto.empresa.nome if projeto.empresa else ""
    feira = projeto.feira.nome if projeto.feira else ""
    local_evento = ""
    
    if projeto.feira:
        local_evento = f"{projeto.feira.local}, {projeto.feira.cidade}/{projeto.feira.estado}"
    
    # Dados do briefing com defaults
    if briefing:
        largura = str(briefing.medida_frente or 6)
        profundidade = str(briefing.medida_fundo or 8)
        area_total = str(briefing.area_estande or 48)
        objetivo = briefing.objetivo_estande or "exposição de produtos"
        tipo_stand = briefing.tipo_stand or "ilha"
        tipo_estrutura = briefing.material or "misto"
        piso_elevado = briefing.piso_elevado or "sem_elevacao"
    else:
        largura = "6"
        profundidade = "8"
        area_total = "48"
        objetivo = "exposição"
        tipo_stand = "ilha"
        tipo_estrutura = "misto"
        piso_elevado = "sem_elevacao"
    
    # 6. Criar dicionário de substituições
    replacements = {
        # === IDENTIFICAÇÃO ===
        "[EMPRESA]": empresa,
        "[OBJETIVO_ESTANDE]": objetivo,
        "[NOME_FEIRA]": feira,
        
        # === DIMENSÕES (dados diretos) ===
        "[LARGURA]": largura,
        "[PROFUNDIDADE]": profundidade,
        "[AREA_TOTAL]": area_total,
        
        # === TIPO STAND (interpretado) ===
        "[TIPO_STAND]": interpretar_tipo_stand(tipo_stand),
        
        # === LAYOUT (formatado do JSON) ===
        "[LAYOUT_AREAS_DETALHADO]": formatar_layout_areas_detalhado(layout),
        "[LADOS_ABERTOS]": formatar_lados_abertos(layout),
        "[AREAS_INTERNAS_LISTA]": extrair_areas_por_categoria(layout, 'interna'),
        "[AREAS_EXTERNAS_LISTA]": extrair_areas_por_categoria(layout, 'externa'),
        
        # === DESIGN (formatado do JSON) ===
        "[ESTILO_VISUAL]": formatar_estilo(inspiracoes),
        "[CORES_APLICADAS]": formatar_cores_aplicadas(inspiracoes),
        "[MATERIAIS_DETALHADOS]": formatar_materiais_detalhados(inspiracoes),
        "[ELEMENTOS_DESTAQUE]": formatar_elementos_destaque(inspiracoes),
        "[ILUMINACAO_TIPO]": formatar_iluminacao(inspiracoes),
        
        # === ESTRUTURA (interpretado) ===
        "[TIPO_ESTRUTURA]": interpretar_estrutura(tipo_estrutura),
        "[PISO_ESPECIFICACAO]": interpretar_piso(piso_elevado),
        
        # === PERSPECTIVA ===
        "[LADO_PERSPECTIVA]": determinar_lado_perspectiva(layout),
        
        # === OUTROS CAMPOS DO TEMPLATE ===
        "[LARGURA_CIRCULACAO]": "1.5",
        "[CONCEITO_DESIGN]": formatar_estilo(inspiracoes),
        "[TESTEIRA_SPEC]": "acrílico iluminado com logo",
        "[MATERIAL_DIVISORIAS]": "MDF com pintura",
        "[ALTURA_MAXIMA]": "3",
        "[PONTOS_ELETRICOS]": "distribuídos conforme layout",
        "[CLIMATIZACAO]": "ar condicionado central",
        "[SISTEMA_SOM]": "",
        "[LISTA_MOBILIARIO]": formatar_mobiliario(briefing, layout),
        "[LISTA_EQUIPAMENTOS]": formatar_equipamentos(briefing),
        "[DISPLAYS_ESPECIFICOS]": "displays de produtos",
        "[POSICAO_LOGO]": "testeira frontal",
        "[SINALIZACAO]": "placas direcionais",
        "[MATERIAL_GRAFICO]": "banners informativos",
        "[CAPACIDADES_AREAS]": "",
        "[OBSERVACOES_ADICIONAIS]": ""
    }
    
    # 7. Substituir todos os placeholders
    prompt_final = template
    for placeholder, valor in replacements.items():
        if valor:  # Só substitui se tem valor
            prompt_final = prompt_final.replace(placeholder, str(valor))
        else:
            prompt_final = prompt_final.replace(placeholder, "")
    
    # 8. Limpar linhas com placeholders não substituídos
    linhas = prompt_final.split('\n')
    linhas_limpas = []
    
    for linha in linhas:
        # Se a linha tem placeholder não substituído, pular
        if re.search(r'\[[A-Z_]+\]', linha):
            continue
        # Manter linhas com conteúdo
        if linha.strip():
            linhas_limpas.append(linha)
    
    prompt_final = '\n'.join(linhas_limpas)
    
    # 9. Limpar espaçamentos múltiplos
    prompt_final = re.sub(r'\n{3,}', '\n\n', prompt_final)
    prompt_final = prompt_final.strip()
    
    # 10. Log final
    logger.info(f"Prompt gerado: {len(prompt_final)} caracteres")
    
    return prompt_final

# ========================== Views HTTP ==========================

@login_required
@gestor_required
@require_GET
def conceito_visual(request: HttpRequest, projeto_id: int) -> HttpResponse:
    """
    Tela principal do Conceito Visual
    Renderiza o template HTML com os dados do projeto
    """
    projeto = get_object_or_404(Projeto, pk=projeto_id)
    
    # Verificar se tem briefing
    if not hasattr(projeto, 'briefings') or not projeto.briefings.exists():
        messages.error(request, "Este projeto não possui briefing.")
        return redirect("gestor:projeto_detail", pk=projeto_id)
    
    brief = _briefing(projeto)
    arquivos_planta = _arquivos(brief, "planta")
    arquivos_referencia = _arquivos(brief, "referencia")
    
    context = {
        "projeto": projeto,
        "briefing": brief,
        "arquivos_planta": arquivos_planta,
        "arquivos_referencia": arquivos_referencia,
        "tem_esbocos": bool(arquivos_planta),
        "tem_referencias": bool(arquivos_referencia),
    }
    
    return render(request, "gestor/conceito_visual.html", context)

@login_required
@gestor_required
@require_POST
def conceito_etapa1_esboco(request: HttpRequest, projeto_id: int) -> JsonResponse:
    """
    Etapa 1: Análise do esboço de planta
    Extrai layout, áreas e dimensões
    """
    projeto = get_object_or_404(Projeto, pk=projeto_id)
    brief = _briefing(projeto)
    
    if not brief:
        return JsonResponse({"sucesso": False, "erro": "Briefing não encontrado."}, status=400)
    
    # Verificar arquivos de planta
    esbocos = brief.arquivos.filter(tipo="planta")
    if not esbocos.exists():
        return JsonResponse({"sucesso": False, "erro": "Nenhum esboço de planta encontrado."}, status=400)
    
    esboco = esbocos.first()
    
    # Preparar payload para o agente
    payload = {
        "projeto_id": projeto.id,
        "briefing_id": brief.id,
        "briefing": {
            "tipo_stand": brief.tipo_stand,
            "medida_frente_m": float(brief.medida_frente) if brief.medida_frente else None,
            "medida_fundo_m": float(brief.medida_fundo) if brief.medida_fundo else None,
            "altura_m": 3.0,
        }
    }
    
    # Executar agente de análise
    resultado = _run_agent("Analisador de Esboços de Planta", payload, imagens=[esboco.arquivo.url])
    
    if "erro" in resultado:
        return JsonResponse({"sucesso": False, "erro": resultado["erro"]}, status=400)
    
    # Salvar resultado no projeto
    projeto.layout_identificado = resultado
    projeto.save(update_fields=["layout_identificado"])
    
    logger.info(f"Layout identificado para projeto {projeto_id}: {len(str(resultado))} chars")
    
    return JsonResponse({
        "sucesso": True,
        "layout": resultado,
        "arquivo": {
            "nome": esboco.nome or esboco.arquivo.name,
            "url": esboco.arquivo.url,
        },
        "processado_em": timezone.now().isoformat(),
    })

@login_required
@gestor_required
@require_POST
def conceito_etapa2_referencias(request: HttpRequest, projeto_id: int) -> JsonResponse:
    """
    Etapa 2: Análise das referências visuais
    Extrai cores, estilos, materiais e inspirações
    """
    projeto = get_object_or_404(Projeto, pk=projeto_id)
    brief = _briefing(projeto)
    
    if not brief:
        return JsonResponse({"sucesso": False, "erro": "Briefing não encontrado."}, status=400)
    
    # Verificar arquivos de referência
    refs = brief.arquivos.filter(tipo="referencia")
    if not refs.exists():
        return JsonResponse({"sucesso": False, "erro": "Nenhuma imagem de referência encontrada."}, status=400)
    
    # Coletar URLs das imagens
    imagens = [ref.arquivo.url for ref in refs if ref.arquivo]
    
    # Preparar payload para o agente
    payload = {
        "projeto_id": projeto.id,
        "marca": projeto.empresa.nome if hasattr(projeto, 'empresa') else None
    }
    
    # Executar agente de análise visual
    resultado = _run_agent("Analisador de Referências Visuais", payload, imagens=imagens)
    
    if "erro" in resultado:
        return JsonResponse({"sucesso": False, "erro": resultado["erro"]}, status=400)
    
    # Salvar resultado no projeto
    projeto.inspiracoes_visuais = resultado
    projeto.save(update_fields=["inspiracoes_visuais"])
    
    logger.info(f"Inspirações identificadas para projeto {projeto_id}: {len(str(resultado))} chars")
    
    return JsonResponse({
        "sucesso": True,
        "inspiracoes": resultado,
        "quantidade_imagens": len(imagens),
        "processado_em": timezone.now().isoformat(),
    })

@login_required
@gestor_required
@require_POST
def conceito_etapa3_geracao(request: HttpRequest, projeto_id: int) -> JsonResponse:
    """
    Etapa 3: Geração do conceito visual
    Gera o prompt e chama o serviço DALL-E
    """
    projeto = get_object_or_404(Projeto, pk=projeto_id)
    
    # Verificar pré-requisitos
    if not projeto.layout_identificado:
        return JsonResponse({
            "sucesso": False,
            "erro": "Layout não encontrado. Execute a Etapa 1 primeiro."
        }, status=400)
    
    if not projeto.inspiracoes_visuais:
        return JsonResponse({
            "sucesso": False,
            "erro": "Inspirações não encontradas. Execute a Etapa 2 primeiro."
        }, status=400)
    
    # Verificar se veio prompt customizado do usuário
    body = json.loads(request.body or "{}")
    prompt_customizado = body.get("prompt")
    
    # Gerar ou usar prompt
    if prompt_customizado:
        prompt_final = prompt_customizado
        logger.info(f"Usando prompt customizado do usuário: {len(prompt_customizado)} chars")
    else:
        prompt_final = gerar_prompt_completo(projeto)
        logger.info(f"Prompt gerado automaticamente: {len(prompt_final)} chars")
    
    # Validar prompt
    if not prompt_final or len(prompt_final) < 50:
        return JsonResponse({
            "sucesso": False,
            "erro": "Prompt inválido ou muito curto"
        }, status=400)
    
    # Chamar serviço DALL-E
    from gestor.services.conceito_visual_dalle import ConceitoVisualDalleService
    dalle_service = ConceitoVisualDalleService()
    
    briefing = projeto.briefings.first()
    resultado = dalle_service.gerar_conceito_visual(
        briefing,
        projeto.layout_identificado,
        projeto.inspiracoes_visuais,
        prompt_customizado=prompt_final
    )
    
    if resultado["sucesso"]:
        # Salvar dados no projeto
        if not projeto.layout_identificado:
            projeto.layout_identificado = {}
        
        # Salvar URL da imagem e prompt no layout_identificado
        projeto.layout_identificado['conceito_visual_url'] = resultado["image_url"]
        projeto.layout_identificado['conceito_visual_prompt'] = resultado["prompt_usado"]
        projeto.layout_identificado['conceito_visual_data'] = timezone.now().isoformat()
        
        # Se houver prompt revisado pelo DALL-E, salvar também
        if resultado.get("prompt_revisado"):
            projeto.layout_identificado['conceito_visual_prompt_revisado'] = resultado["prompt_revisado"]
        
        # Marcar como processado
        projeto.analise_visual_processada = True
        projeto.data_analise_visual = timezone.now()
        projeto.save()
        
        logger.info(f"Conceito visual gerado para projeto {projeto_id}")
        
        return JsonResponse({
            "sucesso": True,
            "image_url": resultado["image_url"],
            "prompt_usado": resultado["prompt_usado"],
            "modelo": resultado.get("modelo", "dall-e-3"),
            "processado_em": timezone.now().isoformat()
        })
    else:
        logger.error(f"Erro ao gerar conceito para projeto {projeto_id}: {resultado.get('erro')}")
        return JsonResponse({
            "sucesso": False,
            "erro": resultado.get("erro", "Erro ao gerar imagem"),
            "tipo_erro": resultado.get("tipo_erro", "unknown")
        }, status=400)