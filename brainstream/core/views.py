from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from estudos.forms import IniciarSessaoForm
from estudos.metricas import iniciais, resumo_do_painel
from estudos.models import SessaoEstudo

LIMITE_HISTORICO = 8


def index(request):
    return render(request, 'core/landing.html')


@login_required
@require_http_methods(['GET', 'POST'])
def painel(request):
    form = IniciarSessaoForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        sessao = form.save(estudante=request.user)
        if sessao.modo == SessaoEstudo.Modo.GUIADO:
            return redirect('estudos:modo_guiado', sessao_id=sessao.pk)
        if sessao.modo == SessaoEstudo.Modo.QUIZ:
            return redirect('estudos:modo_quiz', sessao_id=sessao.pk)
        return redirect('estudos:modo_speedrun', sessao_id=sessao.pk)

    historico = SessaoEstudo.objects.filter(
        estudante=request.user, visivel_no_historico=True).select_related('tema')[:LIMITE_HISTORICO]
    return render(request, 'core/painel.html', {
        'form': form,
        'historico': historico,
        'iniciais': iniciais(request.user),
        'sugestoes': form.sugestoes(),
        'modos': [
            # O último item é a mensagem do carregamento enquanto a sessão (e o conteúdo da IA) é preparada.
            ('guiado', 'Modo Guiado', 'Diálogo guiado por perguntas', 'bi-chat-dots',
             'Abrindo sua sala de estudos…'),
            ('quiz', 'Modo Quiz', 'Múltipla escolha com feedback', 'bi-file-earmark-text',
             'O Enéas está elaborando suas perguntas com IA…'),
            ('speedrun', 'Modo Speedrun', 'Verdadeiro ou falso cronometrado', 'bi-lightning-charge',
             'Preparando suas afirmações…'),
        ],
        **resumo_do_painel(request.user),
    }, status=400 if form.errors else 200)
