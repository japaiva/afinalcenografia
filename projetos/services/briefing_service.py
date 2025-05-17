from django.shortcuts import get_object_or_404
from projetos.models import Projeto, Briefing


def proxima_etapa_logica(tipo_projeto: str, etapa_atual: int) -> int:
    """
    Define a próxima etapa do briefing com base no tipo de projeto.
    Exemplo: se o tipo for 'outros' e estiver na etapa 2, pula para a 4.
    """
    tipo = tipo_projeto.strip().lower()
    if tipo == 'outros' and etapa_atual == 2:
        return 4
    return etapa_atual + 1


def salvar_rascunho_briefing(projeto_id, form_class, arquivos=None):
    """
    Salva os dados de rascunho do briefing.
    Recebe:
      - projeto_id
      - form_class (BriefingEtapaXForm)
      - arquivos: dicionário com 'data' e 'files' (opcional)
    Retorna:
      - (True, form) se salvou com sucesso
      - (False, form) se falhou na validação
    """
    projeto = get_object_or_404(Projeto, pk=projeto_id)
    briefing, _ = Briefing.objects.get_or_create(projeto=projeto)

    form = form_class(
        data=arquivos.get('data') if arquivos else None,
        files=arquivos.get('files') if arquivos else None,
        instance=briefing
    )

    if form.is_valid():
        form.save()
        return True, form

    return False, form


def concluir_briefing(request, projeto_id):
    """
    Conclui o briefing após validação e muda o status para 'enviado'.
    Só permite a conclusão se todas as seções estiverem aprovadas.
    """
    empresa = request.user.empresa
    projeto = get_object_or_404(Projeto, pk=projeto_id, empresa=empresa)

    if not projeto.has_briefing:
        from django.contrib import messages
        from django.shortcuts import redirect
        messages.error(request, "Este projeto não possui um briefing iniciado.")
        return redirect("projetos:projeto_detail", pk=projeto_id)

    briefing = projeto.briefing
    validacoes = briefing.validacoes.all()
    todas_aprovadas = all((v.status == 'aprovado' for v in validacoes))

    from django.contrib import messages
    from django.shortcuts import render, redirect

    if request.method == 'POST':
        if todas_aprovadas:
            briefing.status = 'enviado'
            briefing.save(update_fields=['status'])
            projeto.briefing_status = 'enviado'
            projeto.save(update_fields=['briefing_status'])
            messages.success(request, 'Briefing enviado com sucesso para análise!')
            return redirect('projetos:projeto_detail', pk=projeto_id)
        else:
            messages.error(request, 'O briefing não pode ser enviado pois existem seções que precisam ser corrigidas.')

    context = {
        'empresa': empresa,
        'projeto': projeto,
        'briefing': briefing,
        'validacoes': validacoes,
        'todas_aprovadas': todas_aprovadas,
    }
    return render(request, 'briefing/concluir_briefing.html', context)

def obter_titulo_etapa(etapa):
    """Retorna o título de cada etapa"""
    titulos = {
        1: 'Local Estande',
        2: 'Características',
        3: 'Divisões',
        4: 'Referências Visuais'
    }
    return titulos.get(etapa, 'Etapa do Briefing')