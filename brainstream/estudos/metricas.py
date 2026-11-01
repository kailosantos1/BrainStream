"""Indicadores de gamificação do painel: sessões da semana, taxa de acerto, sequência e ranking.

Datas são convertidas para o fuso local em Python (sem lookups __date), porque o MySQL
só converte fusos em SQL quando as tabelas de timezone estão carregadas.
"""
from collections import defaultdict
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db.models import Max, Min, Sum
from django.utils import timezone

from .models import CATEGORIA_GERAL, SessaoEstudo

LIMITE_RANKING = 5
LIMITE_MATERIAS = 5
# Uma sessão esquecida aberta não deve inflar o tempo de estudo: cada uma conta no máximo 2 h.
TETO_TEMPO_SESSAO = timedelta(hours=2)


def intervalo_da_semana(agora=None):
    """Semana de segunda 00:00 até a segunda seguinte, no fuso local."""
    local = timezone.localtime(agora or timezone.now())
    inicio = (local - timedelta(days=local.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    return inicio, inicio + timedelta(days=7)


def _concluidas_no_intervalo(inicio, fim):
    return SessaoEstudo.objects.filter(status=SessaoEstudo.Status.CONCLUIDA, data_fim__gte=inicio, data_fim__lt=fim)


def sessoes_na_semana(estudante, agora=None):
    return _concluidas_no_intervalo(*intervalo_da_semana(agora)).filter(estudante=estudante).count()


def taxa_de_acerto(estudante):
    """Percentual de acertos em todas as sessões com questões; None se ainda não houver questões."""
    totais = SessaoEstudo.objects.filter(estudante=estudante, total_questoes__gt=0).aggregate(
        acertos=Sum('acertos'), questoes=Sum('total_questoes'))
    if not totais['questoes']:
        return None
    return round(100 * totais['acertos'] / totais['questoes'])


def sequencia_de_dias(estudante, agora=None):
    """Dias consecutivos com pelo menos uma sessão, terminando hoje ou ontem (o dia atual ainda pode ser estudado)."""
    hoje = timezone.localtime(agora or timezone.now()).date()
    dias = {
        timezone.localtime(inicio).date()
        for inicio in SessaoEstudo.objects.filter(estudante=estudante, data_inicio__lte=agora or timezone.now())
        .values_list('data_inicio', flat=True)
    }
    dia = hoje if hoje in dias else hoje - timedelta(days=1)
    sequencia = 0
    while dia in dias:
        sequencia += 1
        dia -= timedelta(days=1)
    return sequencia


def pontos_totais(estudante):
    return SessaoEstudo.objects.filter(estudante=estudante, status=SessaoEstudo.Status.CONCLUIDA).aggregate(
        total=Sum('pontuacao'))['total'] or 0


def nome_publico(estudante):
    """Primeiro nome + inicial do último sobrenome: o ranking não expõe nomes completos."""
    partes = (estudante.nome or estudante.email.split('@')[0]).split()
    return f'{partes[0]} {partes[-1][0]}.' if len(partes) > 1 else partes[0]


def iniciais(estudante):
    partes = (estudante.nome or estudante.email).split()
    return (partes[0][0] + (partes[-1][0] if len(partes) > 1 else '')).upper()


def ranking_semanal(estudante, agora=None, limite=LIMITE_RANKING):
    """Top da semana por pontos de sessões concluídas e a posição do estudante (mesmo fora do top)."""
    agora = agora or timezone.now()
    inicio, fim = intervalo_da_semana(agora)
    placar = list(
        _concluidas_no_intervalo(inicio, fim).values('estudante')
        .annotate(pontos=Sum('pontuacao')).filter(pontos__gt=0)
        .order_by('-pontos', 'estudante__nome', 'estudante')
    )
    ids = [linha['estudante'] for linha in placar[:limite]]
    estudantes = get_user_model().objects.in_bulk(ids)

    def linha(posicao, aluno, pontos):
        return {
            'posicao': posicao,
            'nome': nome_publico(aluno),
            'iniciais': iniciais(aluno),
            'pontos': pontos,
            'sequencia': sequencia_de_dias(aluno, agora),
            'eu': aluno.pk == estudante.pk,
        }

    linhas = [linha(i, estudantes[item['estudante']], item['pontos']) for i, item in enumerate(placar[:limite], start=1)]
    posicao = next((i for i, item in enumerate(placar, start=1) if item['estudante'] == estudante.pk), None)
    minha_linha = None
    if posicao and posicao > limite:
        minha_linha = linha(posicao, estudante, placar[posicao - 1]['pontos'])
    return {
        'linhas': linhas,
        'minha_linha': minha_linha,
        'posicao': posicao,
        'dias_para_reset': (fim.date() - timezone.localtime(agora).date()).days,
    }


def resumo_do_painel(estudante, agora=None):
    agora = agora or timezone.now()
    return {
        'sessoes_semana': sessoes_na_semana(estudante, agora),
        'taxa_acerto': taxa_de_acerto(estudante),
        'sequencia': sequencia_de_dias(estudante, agora),
        'pontos': pontos_totais(estudante),
        'ranking': ranking_semanal(estudante, agora),
    }


def _taxa(acertos, questoes):
    return round(100 * acertos / questoes) if questoes else None


def tempo_de_sessao(sessao):
    """Duração de uma sessão: início ao fim nas concluídas; no Modo Guiado, da 1ª à última mensagem."""
    if sessao.data_fim:
        duracao = sessao.data_fim - sessao.data_inicio
    elif getattr(sessao, 'primeira_msg', None) and getattr(sessao, 'ultima_msg', None):
        duracao = sessao.ultima_msg - sessao.primeira_msg
    else:
        return timedelta(0)
    return min(max(duracao, timedelta(0)), TETO_TEMPO_SESSAO)


def melhor_posicao_no_ranking(estudante):
    """
    Melhor colocação semanal já alcançada, com o mesmo critério de ``ranking_semanal`` (pontos de
    sessões concluídas, desempate por nome). Devolve ``{'posicao', 'semana'}`` ou None.
    """
    placares = defaultdict(lambda: defaultdict(int))
    nomes = {}
    sessoes = SessaoEstudo.objects.filter(status=SessaoEstudo.Status.CONCLUIDA, pontuacao__gt=0, data_fim__isnull=False)
    for aluno, nome, fim, pontos in sessoes.values_list('estudante', 'estudante__nome', 'data_fim', 'pontuacao'):
        placares[intervalo_da_semana(fim)[0]][aluno] += pontos
        nomes[aluno] = nome or ''
    melhor = None
    for semana, placar in placares.items():
        if estudante.pk not in placar:
            continue
        ordem = sorted(placar, key=lambda aluno: (-placar[aluno], nomes[aluno], aluno))
        posicao = ordem.index(estudante.pk) + 1
        if melhor is None or (posicao, -semana.timestamp()) < (melhor['posicao'], -melhor['semana'].timestamp()):
            melhor = {'posicao': posicao, 'semana': semana}
    return melhor


def desempenho(estudante):
    """Consolidado da página "Meu Perfil": totais, acerto por modo, ranking e matérias mais estudadas."""
    sessoes = list(
        SessaoEstudo.objects.filter(estudante=estudante).select_related('tema')
        .annotate(primeira_msg=Min('mensagens__data_envio'), ultima_msg=Max('mensagens__data_envio'))
    )
    concluidas = [sessao for sessao in sessoes if sessao.status == SessaoEstudo.Status.CONCLUIDA]

    modos = []
    for modo, icone in ((SessaoEstudo.Modo.QUIZ, 'bi-file-earmark-text'), (SessaoEstudo.Modo.SPEEDRUN, 'bi-lightning-charge')):
        do_modo = [sessao for sessao in concluidas if sessao.modo == modo]
        acertos = sum(sessao.acertos for sessao in do_modo)
        questoes = sum(sessao.total_questoes for sessao in do_modo)
        modos.append({
            'modo': modo.value, 'rotulo': modo.label, 'icone': icone, 'concluidas': len(do_modo),
            'acertos': acertos, 'questoes': questoes, 'taxa': _taxa(acertos, questoes),
            'pontos': sum(sessao.pontuacao for sessao in do_modo),
        })

    # Matéria = categoria do tema; temas digitados ("Geral") contam pelo próprio nome.
    materias = defaultdict(lambda: {'sessoes': 0, 'acertos': 0, 'questoes': 0})
    for sessao in sessoes:
        nome = sessao.tema.nome if sessao.tema.categoria == CATEGORIA_GERAL else sessao.tema.categoria
        item = materias[nome]
        item['sessoes'] += 1
        item['acertos'] += sessao.acertos
        item['questoes'] += sessao.total_questoes
    ranking_materias = [
        {'nome': nome, **dados, 'taxa': _taxa(dados['acertos'], dados['questoes'])}
        for nome, dados in sorted(materias.items(), key=lambda par: (-par[1]['sessoes'], par[0]))[:LIMITE_MATERIAS]
    ]

    return {
        'sessoes_total': len(sessoes),
        'sessoes_concluidas': len(concluidas),
        'tempo_total': sum((tempo_de_sessao(sessao) for sessao in sessoes), timedelta(0)),
        'taxa_acerto': taxa_de_acerto(estudante),
        'modos': modos,
        'pontos': pontos_totais(estudante),
        'melhor_posicao': melhor_posicao_no_ranking(estudante),
        'materias': ranking_materias,
    }
