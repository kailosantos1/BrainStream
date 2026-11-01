from urllib.parse import urlsplit

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_http_methods, require_POST

from estudos.metricas import iniciais

from .forms import MensagemForm
from .models import SessaoEstudo
from .services import conversa, quiz, speedrun, tutor

LIMITE_HISTORICO = 12
ROTA_DO_MODO = {
    SessaoEstudo.Modo.GUIADO: 'estudos:modo_guiado',
    SessaoEstudo.Modo.QUIZ: 'estudos:modo_quiz',
    SessaoEstudo.Modo.SPEEDRUN: 'estudos:modo_speedrun',
}


def _quer_json(request):
    return 'application/json' in request.headers.get('Accept', '')


def _erro(request, contexto, mensagem, status):
    if _quer_json(request):
        return JsonResponse({'erro': mensagem}, status=status)
    contexto['erro'] = mensagem
    return render(request, 'estudos/modo_guiado.html', contexto, status=status)


@login_required
@require_http_methods(['GET', 'POST'])
def modo_guiado(request, sessao_id):
    # Filtrar pelo dono devolve 404 para sessões de outros estudantes, sem revelar que existem; as excluídas
    # do histórico também dão 404.
    sessao = get_object_or_404(
        SessaoEstudo.objects.select_related('tema'),
        pk=sessao_id, estudante=request.user, modo=SessaoEstudo.Modo.GUIADO, visivel_no_historico=True,
    )
    form = MensagemForm(request.POST or None)
    contexto = {
        'sessao': sessao,
        'form': form,
        'iniciais': iniciais(request.user),
        'simulacao': tutor.simulacao_ativa(),
        'historico': SessaoEstudo.objects.filter(
            estudante=request.user, visivel_no_historico=True).select_related('tema')[:LIMITE_HISTORICO],
    }

    if request.method == 'POST':
        if sessao.status != SessaoEstudo.Status.EM_ANDAMENTO:
            return _erro(request, contexto, 'Esta sessão foi encerrada. Inicie uma nova pelo painel.', 409)
        if request.POST.get('acao') == 'concluir':
            return _concluir_guiado(request, sessao, contexto)
        if conversa.limite_atingido(sessao):
            return _erro(request, contexto, 'Esta sessão atingiu o limite de mensagens. Inicie uma nova pelo painel.', 429)
        if not form.is_valid():
            return _erro(request, contexto, form.errors['conteudo'][0], 400)

        novas = conversa.enviar_mensagem(sessao, form.cleaned_data['conteudo'])
        if _quer_json(request):
            return JsonResponse({'mensagens': _renderizar_mensagens(request, novas, contexto), 'pontos': sessao.pontuacao})
        return redirect(f'{request.path}#mensagem-{novas[-1].pk}')

    contexto['mensagens'] = sessao.mensagens.all()
    return render(request, 'estudos/modo_guiado.html', contexto)


def _renderizar_mensagens(request, mensagens, contexto):
    return [
        render_to_string('estudos/_mensagem.html', {'mensagem': m, 'iniciais': contexto['iniciais']}, request)
        for m in mensagens
    ]


def _concluir_guiado(request, sessao, contexto):
    try:
        novas, concluida = conversa.concluir(sessao)
    except conversa.SessaoEncerrada:
        return _erro(request, contexto, 'Esta sessão já foi concluída.', 409)
    if not _quer_json(request):
        return redirect(f'{request.path}#mensagem-{novas[-1].pk}')
    return JsonResponse({
        'mensagens': _renderizar_mensagens(request, novas, contexto),
        'pontos': sessao.pontuacao,
        'concluida': concluida,
        'encerramento': render_to_string('estudos/_guiado_encerrado.html', {'sessao': sessao}, request) if concluida else '',
    })


def _contexto_quiz(request, sessao):
    questoes = list(sessao.questoes.all())
    atual = next((questao for questao in questoes if not questao.respondida), None)
    em_andamento = sessao.status == SessaoEstudo.Status.EM_ANDAMENTO
    return {
        'sessao': sessao,
        'iniciais': iniciais(request.user),
        'historico': SessaoEstudo.objects.filter(
            estudante=request.user, visivel_no_historico=True).select_related('tema')[:LIMITE_HISTORICO],
        'total': len(questoes),
        # Mostra as já respondidas e a atual; as seguintes só aparecem depois da resposta.
        'visiveis': [questao for questao in questoes if questao.respondida or questao is atual],
        'numero_atual': atual.ordem if atual else len(questoes),
        'pontos': quiz.pontos(questoes),
        'pontos_por_acerto': quiz.PONTOS_POR_ACERTO,
        'concluida': sessao.status == SessaoEstudo.Status.CONCLUIDA,
        'aberta': em_andamento,
        'simuladas': any(questao.origem == questao.Origem.SIMULADA for questao in questoes),
        'proxima': atual,
    }


@login_required
@require_http_methods(['GET', 'POST'])
def modo_quiz(request, sessao_id):
    sessao = get_object_or_404(
        SessaoEstudo.objects.select_related('tema'),
        pk=sessao_id, estudante=request.user, modo=SessaoEstudo.Modo.QUIZ, visivel_no_historico=True,
    )
    if request.method == 'GET':
        if sessao.status == SessaoEstudo.Status.EM_ANDAMENTO:
            quiz.garantir_questoes(sessao)
        return render(request, 'estudos/modo_quiz.html', _contexto_quiz(request, sessao))

    try:
        ordem = int(request.POST.get('questao', ''))
    except ValueError:
        ordem = 0
    try:
        respondida = quiz.responder(sessao, ordem, request.POST.get('resposta', '').strip().upper())
    except quiz.RespostaInvalida as erro:
        if _quer_json(request):
            return JsonResponse({'erro': erro.mensagem}, status=erro.status)
        sessao.refresh_from_db()
        contexto = _contexto_quiz(request, sessao)
        contexto['erro'] = erro.mensagem
        return render(request, 'estudos/modo_quiz.html', contexto, status=erro.status)

    sessao.refresh_from_db()
    contexto = _contexto_quiz(request, sessao)
    if not _quer_json(request):
        return redirect(f'{request.path}#feedback-{respondida.ordem}')

    respondida = next(questao for questao in contexto['visiveis'] if questao.ordem == respondida.ordem)
    contexto_questao = {**contexto, 'questao': respondida}
    novas = render_to_string('estudos/_quiz_resposta.html', contexto_questao, request)
    if contexto['proxima']:
        novas += render_to_string('estudos/_quiz_questao.html', {**contexto, 'questao': contexto['proxima']}, request)
    elif contexto['concluida']:
        novas += render_to_string('estudos/_quiz_final.html', contexto, request)
    return JsonResponse({
        'respondida': render_to_string('estudos/_quiz_questao.html', contexto_questao, request),
        'novas': novas,
        'pontos': contexto['pontos'],
        'numero_atual': contexto['numero_atual'],
        'concluida': contexto['concluida'],
        'acertou': respondida.acertou,
    })


def _contexto_speedrun(request, sessao):
    afirmacoes = list(sessao.afirmacoes.all())
    corrente = speedrun.atual(afirmacoes)
    em_andamento = sessao.status == SessaoEstudo.Status.EM_ANDAMENTO
    # Antes do clique em "Iniciar Speedrun" a 1ª afirmação fica oculta e o relógio parado.
    aguardando = em_andamento and corrente is not None and not speedrun.iniciado(afirmacoes)
    restante_ms = None
    if corrente is not None and corrente.apresentada_em is not None:
        restante_ms = max(int((speedrun.prazo(corrente) - timezone.now()).total_seconds() * 1000), 0)
    return {
        'sessao': sessao,
        'iniciais': iniciais(request.user),
        'historico': SessaoEstudo.objects.filter(
            estudante=request.user, visivel_no_historico=True).select_related('tema')[:LIMITE_HISTORICO],
        'total': len(afirmacoes),
        'visiveis': [afirmacao for afirmacao in afirmacoes
                     if afirmacao.respondida or (afirmacao is corrente and not aguardando)],
        'corrente': corrente if em_andamento else None,
        'aguardando': aguardando,
        'restante_ms': restante_ms,
        'limite_segundos': speedrun.LIMITE_SEGUNDOS,
        'pontos': speedrun.pontos(afirmacoes),
        'pontos_por_acerto': speedrun.PONTOS_POR_ACERTO,
        'tempo_total': speedrun.tempo_total(afirmacoes),
        'concluida': sessao.status == SessaoEstudo.Status.CONCLUIDA,
        'simuladas': any(afirmacao.origem == afirmacao.Origem.SIMULADA for afirmacao in afirmacoes),
    }


@login_required
@require_http_methods(['GET', 'POST'])
def modo_speedrun(request, sessao_id):
    sessao = get_object_or_404(
        SessaoEstudo.objects.select_related('tema'),
        pk=sessao_id, estudante=request.user, modo=SessaoEstudo.Modo.SPEEDRUN, visivel_no_historico=True,
    )
    if request.method == 'GET':
        if sessao.status == SessaoEstudo.Status.EM_ANDAMENTO:
            speedrun.garantir_afirmacoes(sessao)
        return render(request, 'estudos/modo_speedrun.html', _contexto_speedrun(request, sessao))

    if request.POST.get('acao') == 'iniciar':
        return _iniciar_speedrun(request, sessao)
    try:
        ordem = int(request.POST.get('afirmacao', ''))
    except ValueError:
        ordem = 0
    try:
        respondida = speedrun.responder(sessao, ordem, request.POST.get('resposta', '').strip())
    except speedrun.RespostaInvalida as erro:
        if _quer_json(request):
            return JsonResponse({'erro': erro.mensagem}, status=erro.status)
        sessao.refresh_from_db()
        contexto = _contexto_speedrun(request, sessao)
        contexto['erro'] = erro.mensagem
        return render(request, 'estudos/modo_speedrun.html', contexto, status=erro.status)

    if not _quer_json(request):
        return redirect(f'{request.path}#feedback-{respondida.ordem}')

    sessao.refresh_from_db()
    contexto = _contexto_speedrun(request, sessao)
    respondida = next(afirmacao for afirmacao in contexto['visiveis'] if afirmacao.ordem == respondida.ordem)
    novas = render_to_string('estudos/_speedrun_resposta.html', {**contexto, 'afirmacao': respondida}, request)
    if contexto['corrente']:
        novas += render_to_string('estudos/_speedrun_afirmacao.html', {**contexto, 'afirmacao': contexto['corrente']}, request)
    elif contexto['concluida']:
        novas += render_to_string('estudos/_speedrun_final.html', contexto, request)
    return JsonResponse({
        'novas': novas,
        'pontos': contexto['pontos'],
        'acertou': respondida.acertou,
        'concluida': contexto['concluida'],
        'proxima': contexto['corrente'].ordem if contexto['corrente'] else None,
        'restante_ms': contexto['restante_ms'],
    })


def _iniciar_speedrun(request, sessao):
    try:
        corrente = speedrun.iniciar(sessao)
    except speedrun.RespostaInvalida as erro:
        if _quer_json(request):
            return JsonResponse({'erro': erro.mensagem}, status=erro.status)
        return redirect(request.path)
    if not _quer_json(request):
        return redirect(f'{request.path}#afirmacao-{corrente.ordem}')
    contexto = _contexto_speedrun(request, sessao)
    return JsonResponse({
        'novas': render_to_string('estudos/_speedrun_afirmacao.html', {**contexto, 'afirmacao': contexto['corrente']}, request),
        'proxima': contexto['corrente'].ordem,
        'restante_ms': contexto['restante_ms'],
    })


@login_required
@require_POST
def excluir_sessao(request, sessao_id):
    """
    Tira a sessão do histórico do próprio estudante. Não apaga: os pontos continuam no total e no ranking
    (excluir não pode ser um jeito de mexer na pontuação), mas a sessão some da lateral e a página dela dá 404.
    """
    # Filtrar pelo dono (e pelas visíveis) devolve 404 para sessões alheias ou já excluídas.
    sessao = get_object_or_404(
        SessaoEstudo.objects.select_related('tema'), pk=sessao_id, estudante=request.user, visivel_no_historico=True)
    endereco = reverse(ROTA_DO_MODO[sessao.modo], kwargs={'sessao_id': sessao.pk})
    nome = str(sessao.tema)
    sessao.visivel_no_historico = False
    sessao.save(update_fields=['visivel_no_historico'])
    messages.success(request, f'Sessão “{nome}” excluída do histórico.')

    # Volta para onde o estudante estava, salvo se era a própria sessão excluída (que agora daria 404).
    destino = request.POST.get('next', '')
    seguro = url_has_allowed_host_and_scheme(destino, allowed_hosts={request.get_host()}, require_https=request.is_secure())
    if not seguro or urlsplit(destino).path == endereco:
        destino = reverse('core:painel')
    return redirect(destino)
