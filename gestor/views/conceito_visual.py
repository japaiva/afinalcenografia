# gestor/views/conceito_visual.py - VERSÃO 3 COMPLETA COM INTEGRAÇÃO DO AGENTE

import json
import os
from typing import Any, Dict, List, Optional, Tuple

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

# ========================== Tenta importar executor central ===================

_RUN_AGENT_EXECUTOR = None
try:
    from .agents_crews import run_agent as _RUN_AGENT_EXECUTOR
except Exception:
    _RUN_AGENT_EXECUTOR = None

# ============================== Helpers de dados ==============================

def _briefing(projeto: Projeto):
    """Retorna o primeiro briefing relacionado ao projeto."""
    return getattr(projeto, "briefings", None).first()

def _arquivos(briefing_obj, tipo: str) -> List[Any]:
    """Retorna uma lista de arquivos do briefing por tipo."""
    if not briefing_obj:
        return []
    return list(briefing_obj.arquivos.filter(tipo=tipo))

def _float_or(value, default):
    try:
        return float(value) if value is not None else default
    except Exception:
        return default

# ======================= Função para normalizar resposta do agente ======================

def _normalize_agent_response(resp: Dict[str, Any], expected_structure: str) -> Dict[str, Any]:
    """
    Normaliza a resposta do agente para o formato esperado
    """
    if expected_structure == "areas":
        # Se veio como 'layout', mapear para 'areas'
        if "layout" in resp and "areas" not in resp:
            layout_data = resp["layout"]
            
            # Se layout é um dict com áreas
            if isinstance(layout_data, dict):
                # Várias possibilidades de estrutura
                if "areas" in layout_data:
                    resp["areas"] = layout_data["areas"]
                elif "zones" in layout_data:
                    resp["areas"] = layout_data["zones"]
                elif "espacos" in layout_data:
                    resp["areas"] = layout_data["espacos"]
                else:
                    # Se layout tem estrutura direta de áreas
                    areas_encontradas = {}
                    for key, value in layout_data.items():
                        if isinstance(value, dict) and ("bbox" in value or "posicao" in value or "area" in str(key).lower()):
                            areas_encontradas[key] = value
                    
                    if areas_encontradas:
                        resp["areas"] = areas_encontradas
                    else:
                        # Fallback: criar uma área genérica
                        resp["areas"] = {
                            "area_principal": {
                                "nome": "Área Principal",
                                "tipo": resp.get("type", "stand"),
                                "bbox_norm": {"x": 0, "y": 0, "w": 1, "h": 1}
                            }
                        }
            
            # Se ainda não tem areas, criar estrutura mínima
            if "areas" not in resp:
                resp["areas"] = {
                    "area_central": {
                        "nome": "Área Central",
                        "tipo": resp.get("type", "desconhecido"),
                        "dimensoes": resp.get("dimensions", {}),
                        "bbox_norm": {"x": 0, "y": 0, "w": 1, "h": 1}
                    }
                }
        
        # Adicionar campos complementares se não existirem
        if "dimensoes_detectadas" not in resp and "dimensions" in resp:
            resp["dimensoes_detectadas"] = resp["dimensions"]
        
        if "tipo_estande" not in resp and "type" in resp:
            resp["tipo_estande"] = resp["type"]
    
    return resp

# ======================= Execução de agentes COM NORMALIZAÇÃO ===================

def _run_agent(nome_agente: str, payload: Dict[str, Any], imagens: Optional[List[str]] = None) -> Dict[str, Any]:
    """Executa agente com normalização de resposta"""
    if not _RUN_AGENT_EXECUTOR:
        return {"erro": "Sistema de agentes não disponível", "sucesso": False}
    
    try:
        # Construir prompt limpo baseado no tipo de agente
        if "Esboço" in nome_agente or "Esboco" in nome_agente:
            briefing_data = payload.get("briefing", {})
            
            prompt = f"""Analise este esboço de planta baixa e extraia o layout estruturado:

DADOS DO PROJETO:
- ID: {payload.get('projeto_id')}
- Tipo de stand: {briefing_data.get('tipo_stand', 'não informado')}
- Dimensões: {briefing_data.get('medida_frente_m', 'não informado')}m x {briefing_data.get('medida_fundo_m', 'não informado')}m
- Altura máxima: {briefing_data.get('altura_m', 3.0)}m

IMPORTANTE: Retorne um JSON com a estrutura 'areas' contendo as diferentes zonas/espaços identificados no layout.
Exemplo esperado:
{{
  "areas": {{
    "recepcao": {{"nome": "Recepção", "bbox_norm": {{"x": 0, "y": 0, "w": 0.3, "h": 0.4}}}},
    "reuniao": {{"nome": "Sala de Reunião", "bbox_norm": {{"x": 0.3, "y": 0, "w": 0.4, "h": 0.6}}}}
  }},
  "dimensoes_detectadas": {{"largura": {briefing_data.get('medida_frente_m', 6)}, "profundidade": {briefing_data.get('medida_fundo_m', 8)}}},
  "tipo_estande": "{briefing_data.get('tipo_stand', 'corporativo')}"
}}

Por favor, analise a imagem fornecida e retorne o layout estruturado."""

        elif "Referência" in nome_agente or "Referencia" in nome_agente:
            prompt = f"""Analise as imagens de referência para o projeto ID {payload.get('projeto_id')}.
Marca/Cliente: {payload.get('marca', 'não informado')}

Extraia e retorne JSON com:
- estilo_identificado, cores_predominantes, materiais_sugeridos, elementos_destaque, iluminacao, riscos_e_mitigacoes"""
        else:
            prompt = json.dumps(payload, indent=2)
        
        print(f"DEBUG - Prompt enviado: {prompt[:300]}...")
        
        # Executar com prompt específico
        executor_payload = {"prompt": prompt, **payload}
        resultado = _RUN_AGENT_EXECUTOR(nome_agente, executor_payload, imagens)
        
        # Verificar se retornou erro
        if not resultado or "erro" in resultado:
            return {"erro": resultado.get("erro", "Agente não retornou resultado válido"), "sucesso": False}
        
        # Extrair dados se veio do executor genérico
        if "_metadata" in resultado:
            resultado = {k: v for k, v in resultado.items() if k != "_metadata"}
        
        # NORMALIZAR RESPOSTA baseado no tipo de agente
        if "Esboço" in nome_agente or "Esboco" in nome_agente:
            resultado = _normalize_agent_response(resultado, "areas")
        
        return resultado
        
    except Exception as e:
        print(f"ERRO no executor: {str(e)}")
        return {"erro": f"Erro na execução do agente: {str(e)}", "sucesso": False}

# ======================= Consolidação + Prompt ======================

def _consolidar(brief, layout: Dict[str, Any], inspiracoes: Dict[str, Any]) -> Dict[str, Any]:
    """Consolida dados do layout e inspirações em um dataset estruturado"""
    # Tentar extrair dimensões do layout primeiro, depois do briefing
    dimensoes_layout = layout.get("dimensoes_detectadas", {}) if isinstance(layout.get("dimensoes_detectadas"), dict) else {}
    
    largura = dimensoes_layout.get("largura") or _float_or(getattr(brief, "medida_frente", None), 6.0)
    profundidade = dimensoes_layout.get("profundidade") or _float_or(getattr(brief, "medida_fundo", None), 8.0)
    altura = dimensoes_layout.get("altura") or 3.0  # Altura padrão
    
    paleta = []
    if isinstance(inspiracoes.get("cores_predominantes"), list):
        paleta = [c.get("hex") for c in inspiracoes["cores_predominantes"] if isinstance(c, dict) and c.get("hex")]
    
    if not paleta:
        paleta = ["#FFFFFF", "#1A1A1A"]  # Padrão

    dataset = {
        "dimensoes": {
            "largura_m": float(largura),
            "profundidade_m": float(profundidade),
            "altura_m": float(altura),
        },
        "tipo_estande": layout.get("tipo_estande") or getattr(brief, "tipo_stand", None) or "desconhecido",
        "zonas": [],
        "circulacao": {"min_m": 1.2, "rotas": layout.get("circulacao", [])},
        "paleta_final_hex": paleta,
        "materiais": inspiracoes.get("materiais_sugeridos", []),
        "elementos_destaque": inspiracoes.get("elementos_destaque", []),
        "estilo": inspiracoes.get("estilo_identificado", {}),
        "riscos": inspiracoes.get("riscos_e_mitigacoes", []),
        "pronto_para_geracao": True,
    }

    # Processar áreas
    areas = layout.get("areas", {})
    if isinstance(areas, list):
        # Se areas é uma lista
        for a in areas:
            if isinstance(a, dict):
                dataset["zonas"].append({
                    "nome": a.get("id", "area"),
                    "tipo": a.get("subtipo", "generico"),
                    "bbox_norm": a.get("bbox_norm", {"x": 0, "y": 0, "w": 1, "h": 1}),
                    "m2": a.get("m2_estimado", 0),
                })
    elif isinstance(areas, dict):
        # Se areas é um dict
        for nome, a in areas.items():
            if isinstance(a, dict):
                dataset["zonas"].append({
                    "nome": nome,
                    "tipo": a.get("tipo", "generico"),
                    "bbox_norm": a.get("bbox_norm", {"x": 0, "y": 0, "w": 1, "h": 1}),
                    "m2": a.get("m2_estimado", 0),
                })

    return dataset

def _montar_prompt(brief, dataset: Dict[str, Any]) -> str:
    """Monta o prompt final para geração da imagem - FALLBACK"""
    W = dataset["dimensoes"]["largura_m"]
    D = dataset["dimensoes"]["profundidade_m"]
    H = dataset["dimensoes"]["altura_m"]
    tipo = dataset.get("tipo_estande", "desconhecido")

    areas_txt = "\n".join(f"- {z.get('nome')}: {z.get('m2', 0)}m²" for z in dataset.get("zonas", [])) or "- Área central"
    cores = ", ".join(dataset.get("paleta_final_hex", []))
    
    # Materiais
    materiais_txt = ""
    if dataset.get("materiais"):
        materiais_list = [f"{m.get('material')}" for m in dataset["materiais"] if isinstance(m, dict)]
        if materiais_list:
            materiais_txt = f"\nMateriais principais: {', '.join(materiais_list)}"
    
    # Estilo
    estilo_txt = "moderno"
    if isinstance(dataset.get("estilo"), dict):
        estilo_txt = dataset["estilo"].get("principal", "moderno").replace("_", " ")
        if dataset["estilo"].get("secundario"):
            estilo_txt += f", {dataset['estilo']['secundario'].replace('_', ' ')}"

    prompt = f"""Crie uma imagem fotorrealística em alta resolução de um estande de feira de negócios profissional:

ESPECIFICAÇÕES:
- Dimensões: {W}m x {D}m x {H}m
- Tipo: {tipo}
- Estilo: {estilo_txt}

ÁREAS DO ESTANDE:
{areas_txt}

DESIGN:
- Paleta de cores: {cores}
{materiais_txt}

VISUALIZAÇÃO:
- Perspectiva 3/4 mostrando fachada principal e lateral
- Pessoas interagindo naturalmente no espaço
- Iluminação profissional de feira comercial
- Acabamento fotorrealístico e moderno
- Qualidade de renderização arquitetônica

Criar uma imagem que demonstre profissionalismo, funcionalidade e atratividade visual.""".strip()
    
    return prompt

def _gerar_imagem_stub(prompt: str, projeto_id: int) -> Tuple[str, str]:
    """Fallback local com PIL para validar o fluxo."""
    from PIL import Image, ImageDraw

    media_root = getattr(settings, "MEDIA_ROOT", os.path.join(getattr(settings, "BASE_DIR", ""), "media"))
    if not media_root:
        media_root = os.path.join(os.getcwd(), "media")
    media_url = getattr(settings, "MEDIA_URL", "/media/")
    out_dir = os.path.join(media_root, "conceitos")
    os.makedirs(out_dir, exist_ok=True)

    ts = timezone.now().strftime("%Y%m%d_%H%M%S")
    fn = f"conceito_{projeto_id}_{ts}.png"
    out_path = os.path.join(out_dir, fn)

    W, H = 1280, 720
    img = Image.new("RGB", (W, H), (245, 245, 245))
    d = ImageDraw.Draw(img)

    d.text((20, 20), "Conceito Visual (stub)", fill=(20, 20, 20))
    y = 60
    wrap_w = 95
    words = (prompt or "")[:2000].split()
    line = []
    for w in words:
        if len(" ".join(line + [w])) > wrap_w:
            d.text((20, y), " ".join(line), fill=(40, 40, 40))
            y += 20
            line = [w]
        else:
            line.append(w)
    if line:
        d.text((20, y), " ".join(line), fill=(40, 40, 40))

    img.save(out_path, "PNG")
    url = f"{media_url}conceitos/{fn}"
    return url, url

# ======================= NOVA FUNÇÃO: Processar Template do Agente ======================

def _processar_template_agente(template: str, briefing, layout: Dict, inspiracoes: Dict, projeto) -> str:
    """
    Interpola o template do agente com dados reais do projeto
    """
    # Preparar dados do briefing
    largura = float(briefing.medida_frente) if briefing.medida_frente else 6.0
    profundidade = float(briefing.medida_fundo) if briefing.medida_fundo else 8.0
    altura = 3.0  # Padrão para feiras
    area_total = briefing.area_estande or (largura * profundidade)
    
    # Processar áreas do layout
    areas_internas = []
    areas_externas = []
    
    if layout and 'areas' in layout:
        areas = layout['areas']
        if isinstance(areas, dict):
            for nome, dados in areas.items():
                area_desc = f"{nome}"
                if isinstance(dados, dict):
                    if dados.get('m2_estimado'):
                        area_desc += f" ({dados['m2_estimado']:.1f}m²)"
                    
                    # Classificar como interna ou externa
                    tipo = dados.get('tipo', '').lower()
                    if any(x in tipo for x in ['reuniao', 'copa', 'deposito', 'workshop']):
                        areas_internas.append(area_desc)
                    else:
                        areas_externas.append(area_desc)
        elif isinstance(areas, list):
            for area in areas:
                if isinstance(area, dict):
                    nome = area.get('nome', area.get('id', 'área'))
                    m2 = area.get('m2_estimado', 0)
                    area_desc = f"{nome} ({m2:.1f}m²)" if m2 > 0 else nome
                    areas_internas.append(area_desc)
    
    # Se não tem áreas específicas, criar padrão
    if not areas_internas and not areas_externas:
        areas_internas = ["Área de exposição principal", "Balcão de atendimento"]
        areas_externas = ["Área de demonstração", "Lounge de espera"]
    
    # Processar cores e materiais das inspirações
    cores_principais = []
    materiais_principais = []
    estilo_visual = "moderno e profissional"
    
    if inspiracoes:
        # Cores
        if 'cores_predominantes' in inspiracoes and isinstance(inspiracoes['cores_predominantes'], list):
            for cor in inspiracoes['cores_predominantes'][:3]:  # Top 3 cores
                if isinstance(cor, dict) and 'hex' in cor:
                    cor_desc = cor['hex']
                    if cor.get('uso'):
                        cor_desc += f" para {cor['uso']}"
                    cores_principais.append(cor_desc)
        
        # Materiais
        if 'materiais_sugeridos' in inspiracoes and isinstance(inspiracoes['materiais_sugeridos'], list):
            for mat in inspiracoes['materiais_sugeridos'][:4]:
                if isinstance(mat, dict):
                    material = mat.get('material', '')
                    if material:
                        materiais_principais.append(material)
        
        # Estilo
        if 'estilo_identificado' in inspiracoes and isinstance(inspiracoes['estilo_identificado'], dict):
            principal = inspiracoes['estilo_identificado'].get('principal', 'moderno')
            secundario = inspiracoes['estilo_identificado'].get('secundario', '')
            estilo_visual = principal.replace('_', ' ')
            if secundario:
                estilo_visual += f" com toques de {secundario.replace('_', ' ')}"
    
    # Valores padrão se não tiver dados
    if not cores_principais:
        cores_principais = ["tons neutros", "detalhes em azul corporativo", "acentos em branco"]
    
    if not materiais_principais:
        materiais_principais = ["madeira clara", "vidro temperado", "metal escovado", "iluminação LED"]
    
    # Preparar tipo de estrutura baseado no material do briefing
    tipo_estrutura = "misto (parte construída + parte padrão)"
    if briefing.material == 'construido':
        tipo_estrutura = "totalmente construído com estrutura personalizada"
    elif briefing.material == 'padrao':
        tipo_estrutura = "padrão com módulos de vidro e armação metálica"
    
    # Preparar elevação do piso
    elevacao_piso = "sem"
    altura_piso = "0"
    if briefing.piso_elevado:
        if briefing.piso_elevado == '3cm':
            elevacao_piso = "com"
            altura_piso = "3"
        elif briefing.piso_elevado == '10cm':
            elevacao_piso = "com"
            altura_piso = "10"
    
    # Tipo de testeira
    tipo_testeira = briefing.tipo_testeira or "reta"
    material_testeira = "acrílico iluminado com logo em destaque"
    if tipo_testeira == "curva":
        material_testeira = "estrutura curva em acrílico retroiluminado"
    
    # Equipamentos e mobiliário baseado nas áreas
    lista_mobiliario = []
    lista_equipamentos = []
    
    # Analisar áreas de exposição do briefing
    if hasattr(briefing, 'areas_exposicao'):
        for area_expo in briefing.areas_exposicao.all():
            if area_expo.tem_lounge:
                lista_mobiliario.append("sofás e poltronas confortáveis")
            if area_expo.tem_balcao_recepcao:
                lista_mobiliario.append("balcão de recepção moderno")
            if area_expo.tem_mesas_atendimento:
                lista_mobiliario.append("mesas de atendimento com cadeiras")
            if area_expo.tem_balcao_vitrine:
                lista_mobiliario.append("balcão vitrine iluminado")
            if area_expo.equipamentos:
                lista_equipamentos.append(area_expo.equipamentos)
    
    # Analisar salas de reunião
    if hasattr(briefing, 'salas_reuniao'):
        for sala in briefing.salas_reuniao.all():
            if sala.capacidade:
                lista_mobiliario.append(f"sala de reunião para {sala.capacidade} pessoas")
            if sala.equipamentos:
                lista_equipamentos.append(sala.equipamentos)
    
    # Valores padrão se não tiver mobiliário/equipamentos
    if not lista_mobiliario:
        lista_mobiliario = ["balcão de atendimento", "expositores", "banquetas altas", "mesa de centro"]
    
    if not lista_equipamentos:
        lista_equipamentos = ["TVs de LED 55\"", "tablets para apresentação", "sistema de som ambiente"]
    
    # Elementos decorativos baseados no estilo
    elementos_decorativos = []
    if "moderno" in estilo_visual.lower():
        elementos_decorativos.append("plantas ornamentais")
        elementos_decorativos.append("iluminação decorativa em LED")
    if "tecnolog" in estilo_visual.lower() or "digital" in estilo_visual.lower():
        elementos_decorativos.append("displays digitais interativos")
        elementos_decorativos.append("elementos holográficos")
    if "sustentavel" in estilo_visual.lower() or "eco" in estilo_visual.lower():
        elementos_decorativos.append("jardim vertical")
        elementos_decorativos.append("materiais reciclados aparentes")
    
    if not elementos_decorativos:
        elementos_decorativos = ["plantas ornamentais", "displays de produtos", "painéis decorativos"]
    
    # Conceito integrado
    conceito_integrado = f"Estande {estilo_visual} para {projeto.empresa.nome}"
    if projeto.empresa.descricao:
        conceito_integrado += f", refletindo {projeto.empresa.descricao[:100]}"
    if briefing.objetivo_estande:
        conceito_integrado += f", focado em {briefing.objetivo_estande}"
    
    # Dicionário de substituições
    replacements = {
        "[OBJETIVO_ESTANDE]": briefing.objetivo_estande or briefing.objetivo_evento or "exposição e networking",
        "[DESCRICAO_EMPRESA]": projeto.empresa.descricao or f"Empresa líder no setor",
        "[SETOR]": "corporativo",  # Poderia vir de um campo específico
        "[LARGURA]": str(largura),
        "[PROFUNDIDADE]": str(profundidade),
        "[ALTURA]": str(altura),
        "[TIPO]": briefing.get_tipo_stand_display() if briefing.tipo_stand else "ilha",
        "[POSICIONAMENTO]": "posição estratégica com alta visibilidade",
        "[AREAS_INTERNAS]": ", ".join(areas_internas),
        "[TIPO_ESTRUTURA]": tipo_estrutura,
        "[PISO_ELEVADO]": elevacao_piso,
        "[ALTURA_PISO]": altura_piso,
        "[MATERIAL_PISO]": "carpete grafite" if elevacao_piso == "com" else "piso da feira",
        "[TIPO_TESTEIRA]": tipo_testeira,
        "[MATERIAL_TESTEIRA]": material_testeira,
        "[ALTURA_DIVISORIAS]": "2.5",
        "[AREAS_FUNCIONAIS]": ", ".join(areas_externas) if areas_externas else "área de demonstração de produtos",
        "[REFERENCIAS]": f"Estilo {estilo_visual} com paleta de cores em {', '.join(cores_principais[:2])}",
        "[CONCEITO_INTEGRADO]": conceito_integrado,
        "[TIPO_ESTANDE]": briefing.get_tipo_stand_display() if briefing.tipo_stand else "ilha",
        "[LISTA_AREAS_INTERNAS]": ", ".join(areas_internas),
        "[LARGURA_CIRCULACAO]": "1.5",
        "[AREAS_EXTERNAS]": ", ".join(areas_externas) if areas_externas else "área de ativação frontal",
        "[MATERIAIS_PRINCIPAIS]": ", ".join(materiais_principais),
        "[TIPO_PISO]": "elevado" if elevacao_piso == "com" else "nivelado",
        "[ELEVACAO_PISO]": f"{altura_piso}cm de" if elevacao_piso == "com" else "sem",
        "[TIPO_ILUMINACAO]": "profissional com spots direcionados e iluminação ambiente em LED",
        "[CORES_PRINCIPAIS]": ", ".join(cores_principais),
        "[SETOR_EMPRESA]": "o setor de atuação",
        "[LISTA_MOBILIARIO]": ", ".join(lista_mobiliario),
        "[LISTA_EQUIPAMENTOS]": ", ".join(lista_equipamentos),
        "[ELEMENTOS_DECORATIVOS]": ", ".join(elementos_decorativos),
        "[CARACTERISTICAS_ESPECIFICAS]": estilo_visual
    }
    
    # Aplicar todas as substituições
    prompt_final = template
    for key, value in replacements.items():
        prompt_final = prompt_final.replace(key, str(value))
    
    return prompt_final

# =================================== Views ===================================

@login_required
@gestor_required
@require_GET
def conceito_visual(request: HttpRequest, projeto_id: int) -> HttpResponse:
    """Tela principal do Conceito Visual"""
    projeto = get_object_or_404(Projeto, pk=projeto_id)

    if not getattr(projeto, "has_briefing", False):
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
    Etapa 1: Análise APENAS do esboço (layout/geometria)
    Não precisa de inspirações, apenas extrai a estrutura espacial
    """
    projeto = get_object_or_404(Projeto, pk=projeto_id)
    brief = _briefing(projeto)
    if not brief:
        return JsonResponse({"sucesso": False, "erro": "Briefing não encontrado."}, status=400)

    # Verificar agente
    agente_nome = "Analisador de Esboços de Planta"
    agente_id = None
    try:
        agente_obj = Agente.objects.get(nome=agente_nome, tipo="individual", ativo=True)
        agente_id = agente_obj.id
    except Agente.DoesNotExist:
        agente_obj = None

    # Body para arquivo específico
    try:
        body = json.loads(request.body or "{}")
    except Exception:
        body = {}
    arquivo_id = body.get("arquivo_id")

    # Coletar esboços
    esbocos_qs = brief.arquivos.filter(tipo="planta")
    
    if not esbocos_qs.exists():
        return JsonResponse({"sucesso": False, "erro": "Nenhum esboço de planta encontrado."}, status=400)

    if arquivo_id:
        esboco = esbocos_qs.filter(id=arquivo_id).first()
        if not esboco:
            return JsonResponse({"sucesso": False, "erro": f"Esboço id={arquivo_id} não encontrado."}, status=404)
    else:
        esboco = esbocos_qs.first()

    # Path/URL do arquivo
    if not esboco.arquivo:
        return JsonResponse({"sucesso": False, "erro": "Esboço não possui arquivo anexado."}, status=400)
    
    arquivo_nome = esboco.nome or esboco.arquivo.name
    esboco_url = esboco.arquivo.url
    esboco_path = esboco.arquivo.url  # Para MinIO

    # Payload consistente
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

    executor_nome = "agents_crews.run_agent" if _RUN_AGENT_EXECUTOR else "sem_executor"
    imagens_usadas = [esboco_path] if esboco_path else []

    # Chamada do agente
    resp = _run_agent(agente_nome, payload, imagens=imagens_usadas)
    
    # Verificar erros
    if not resp.get("sucesso", True) or "erro" in resp:
        return JsonResponse({
            "sucesso": False, 
            "erro": resp.get("erro", "Agente não conseguiu processar o esboço")
        }, status=400)

    # Verificar estrutura válida
    if "areas" not in resp:
        return JsonResponse({
            "sucesso": False, 
            "erro": f"Agente não retornou estrutura 'areas'. Estrutura retornada: {list(resp.keys())}"
        }, status=400)

    # Persistir APENAS o layout
    projeto.layout_identificado = resp
    projeto.save(update_fields=["layout_identificado"])

    return JsonResponse({
        "sucesso": True,
        "layout": resp,
        "arquivo": {
            "id": getattr(esboco, "id", None),
            "nome": arquivo_nome,
            "url": esboco_url,
        },
        "processado_em": timezone.now().isoformat(),
    })

@login_required
@gestor_required
@require_POST
def conceito_etapa2_referencias(request: HttpRequest, projeto_id: int) -> JsonResponse:
    """
    Etapa 2: Análise APENAS das referências visuais (cores/estilos)
    Não precisa do layout, apenas extrai inspirações visuais
    """
    projeto = get_object_or_404(Projeto, pk=projeto_id)
    brief = _briefing(projeto)
    if not brief:
        return JsonResponse({"sucesso": False, "erro": "Briefing não encontrado."}, status=400)

    # Coletar referências
    refs = _arquivos(brief, "referencia")
    if not refs:
        return JsonResponse({
            "sucesso": False,
            "erro": "Nenhuma imagem de referência encontrada."
        }, status=400)
    
    imagens_ref = []
    for ref in refs:
        if ref.arquivo:
            imagens_ref.append(ref.arquivo.url)

    # Executar agente de referências - SEM PRECISAR DO LAYOUT
    payload = {
        "projeto_id": projeto.id,
        "marca": getattr(projeto.empresa, "nome", None)
    }
    
    inspiracoes = _run_agent("Analisador de Referências Visuais", payload, imagens=imagens_ref)
    
    if "erro" in inspiracoes:
        return JsonResponse({
            "sucesso": False,
            "erro": f"Erro na análise de referências: {inspiracoes.get('erro')}"
        }, status=400)

    # Persistir APENAS as inspirações
    projeto.inspiracoes_visuais = inspiracoes
    projeto.save(update_fields=["inspiracoes_visuais"])

    return JsonResponse({
        "sucesso": True,
        "inspiracoes": inspiracoes,
        "quantidade_imagens": len(imagens_ref),
        "processado_em": timezone.now().isoformat(),
    })

@login_required
@gestor_required
@require_POST
def conceito_etapa3_geracao(request: HttpRequest, projeto_id: int) -> JsonResponse:
    """
    Etapa 3: Consolidação + Geração do conceito visual com DALL-E
    Usa o template do agente com interpolação de variáveis
    """
    projeto = get_object_or_404(Projeto, pk=projeto_id)
    brief = _briefing(projeto)
    
    # Verificar se tem os dados necessários
    layout = getattr(projeto, "layout_identificado", None)
    inspiracoes = getattr(projeto, "inspiracoes_visuais", None)
    
    if not layout:
        return JsonResponse({
            "sucesso": False,
            "erro": "Layout não encontrado. Execute a Etapa 1 primeiro."
        }, status=400)
    
    if not inspiracoes:
        return JsonResponse({
            "sucesso": False,
            "erro": "Inspirações não encontradas. Execute a Etapa 2 primeiro."
        }, status=400)
    
    # Verificar se veio um prompt customizado
    try:
        body = json.loads(request.body or "{}")
    except Exception:
        body = {}
    
    prompt_customizado = body.get("prompt")
    usar_dalle = body.get("usar_dalle", True)
    
    # Se não tem prompt customizado, usar o template do agente
    if not prompt_customizado:
        try:
            # Buscar o agente de imagem principal
            agente_imagem = Agente.objects.get(
                nome="Agente de Imagem Principal",
                tipo="individual",
                ativo=True
            )
            
            # Usar o task_instructions como template
            template = agente_imagem.task_instructions
            
            # Interpolar o template com dados reais
            prompt_final = _processar_template_agente(
                template, 
                brief, 
                layout, 
                inspiracoes, 
                projeto
            )
            
        except Agente.DoesNotExist:
            # Fallback: usar a função antiga de montar prompt
            dataset = _consolidar(brief, layout, inspiracoes)
            prompt_final = _montar_prompt(brief, dataset)
    else:
        prompt_final = prompt_customizado
    
    # Importar serviço DALL-E
    from gestor.services.conceito_visual_dalle import ConceitoVisualDalleService
    dalle_service = ConceitoVisualDalleService()
    
    # Gerar conceito visual
    if usar_dalle:
        # Usar serviço DALL-E real
        resultado = dalle_service.gerar_conceito_visual(
            brief, 
            layout, 
            inspiracoes, 
            prompt_final  # Passa o prompt final processado
        )
        
        if resultado["sucesso"]:
            # Salvar URL e prompt no projeto
            if not hasattr(projeto, 'conceito_visual_url'):
                # Se o campo não existe no modelo, salvar em JSON field
                if not projeto.layout_identificado:
                    projeto.layout_identificado = {}
                projeto.layout_identificado['conceito_visual_url'] = resultado["image_url"]
                projeto.layout_identificado['conceito_visual_prompt'] = resultado["prompt_usado"]
                projeto.layout_identificado['conceito_visual_data'] = timezone.now().isoformat()
            
            # Marcar como processado
            projeto.analise_visual_processada = True
            projeto.data_analise_visual = timezone.now()
            
            projeto.save(update_fields=[
                "layout_identificado",
                "analise_visual_processada", 
                "data_analise_visual"
            ])
            
            # Consolidar dataset para debug
            dataset = _consolidar(brief, layout, inspiracoes)
            
            return JsonResponse({
                "sucesso": True,
                "image_url": resultado["image_url"],
                "download_url": resultado["image_url"],
                "prompt_usado": resultado["prompt_usado"],
                "modelo": resultado["modelo"],
                "metricas": resultado.get("metricas", {}),
                "processado_em": resultado["timestamp"],
                "dataset_consolidado": dataset,
                "template_usado": not bool(prompt_customizado)
            })
        else:
            # Erro na geração
            return JsonResponse({
                "sucesso": False,
                "erro": resultado.get("erro", "Erro ao gerar imagem"),
                "tipo_erro": resultado.get("tipo_erro", "unknown"),
                "detalhes": resultado
            }, status=400)
    else:
        # Fallback para modo stub (desenvolvimento)
        dataset = _consolidar(brief, layout, inspiracoes)
        url_imagem, download_url = _gerar_imagem_stub(prompt_final, projeto_id)
        
        # Marcar projeto como processado
        projeto.analise_visual_processada = True
        projeto.data_analise_visual = timezone.now()
        projeto.save(update_fields=["analise_visual_processada", "data_analise_visual"])
        
        return JsonResponse({
            "sucesso": True,
            "image_url": url_imagem,
            "download_url": download_url,
            "prompt_usado": prompt_final,
            "modelo": "stub",
            "processado_em": timezone.now().isoformat(),
            "dataset_consolidado": dataset,
            "template_usado": not bool(prompt_customizado)
        })