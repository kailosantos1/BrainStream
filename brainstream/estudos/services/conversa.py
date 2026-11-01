"""
Fluxo do Modo Guiado: registra a mensagem, aplica o context locking, obtém a resposta, pontua a
participação e conclui a sessão com a síntese socrática.

Pontuação antifarme: só contam respostas "legítimas" — não bloqueadas pelo context locking, com pelo
menos 3 palavras e sem repetir uma resposta anterior. Cada uma vale 5 pontos, com teto de 30; concluir
(exige 3 legítimas) soma 10 de bônus. Os pontos são recalculados a partir das mensagens salvas, então
não há contador para adulterar, e só entram no ranking quando a sessão é concluída.
"""
import re

from django.db import transaction

from ..models import MensagemSessao, SessaoEstudo
from . import context_locking, tutor

# Teto de mensagens do estudante por sessão, para conter custo e abuso.
LIMITE_MENSAGENS = 80
PONTOS_POR_RESPOSTA = 5
TETO_PONTOS_RESPOSTAS = 30
BONUS_CONCLUSAO = 10
MINIMO_RESPOSTAS_PARA_CONCLUIR = 3
MINIMO_PALAVRAS = 3

AVISO_FALHA = (
    'O Enéas não conseguiu responder agora. Sua mensagem foi salva: envie de novo em instantes '
    'ou reformule a resposta.'
)


class SessaoEncerrada(Exception):
    pass


def limite_atingido(sessao):
    return sessao.mensagens.filter(autor=MensagemSessao.Autor.ESTUDANTE).count() >= LIMITE_MENSAGENS


def respostas_legitimas(sessao, mensagens):
    """Respostas do estudante que contam pontos e valem para a conclusão."""
    vistas = set()
    legitimas = []
    for mensagem in mensagens:
        if mensagem.autor != MensagemSessao.Autor.ESTUDANTE:
            continue
        # Sem acentos, caixa e pontuação: a mesma frase com outro ponto final não conta de novo.
        normalizada = ' '.join(re.sub(r'[^\w\s]', ' ', context_locking.normalizar(mensagem.conteudo)).split())
        if (
            len(normalizada.split()) < MINIMO_PALAVRAS
            or normalizada in vistas
            or context_locking.verificar(mensagem.conteudo, sessao.tema.nome) is not None
        ):
            continue
        vistas.add(normalizada)
        legitimas.append(mensagem)
    return legitimas


def pontos_de_participacao(quantidade):
    return min(quantidade * PONTOS_POR_RESPOSTA, TETO_PONTOS_RESPOSTAS)


def atualizar_pontuacao(sessao):
    """Recalcula os pontos da sessão aberta a partir das mensagens (mostrados no topo da conversa)."""
    pontos = pontos_de_participacao(len(respostas_legitimas(sessao, sessao.mensagens.all())))
    if pontos != sessao.pontuacao:
        SessaoEstudo.objects.filter(pk=sessao.pk, status=SessaoEstudo.Status.EM_ANDAMENTO).update(pontuacao=pontos)
        sessao.pontuacao = pontos
    return pontos


def enviar_mensagem(sessao, texto):
    """Devolve as mensagens novas (a do estudante e a resposta) na ordem em que aparecem no chat."""
    criar = MensagemSessao.objects.create
    mensagem = criar(sessao=sessao, autor=MensagemSessao.Autor.ESTUDANTE, conteudo=texto)

    bloqueio = context_locking.verificar(texto, sessao.tema.nome)
    if bloqueio:
        return [mensagem, criar(sessao=sessao, autor=MensagemSessao.Autor.SISTEMA, conteudo=bloqueio.resposta)]

    atualizar_pontuacao(sessao)
    try:
        resposta = tutor.responder(sessao, list(sessao.mensagens.all()))
    except tutor.TutorIndisponivel:
        return [mensagem, criar(sessao=sessao, autor=MensagemSessao.Autor.SISTEMA, conteudo=AVISO_FALHA)]
    return [mensagem, criar(
        sessao=sessao, autor=MensagemSessao.Autor.ENEAS, conteudo=resposta.texto, tokens_utilizados=resposta.tokens,
    )]


def _orientacao_para_aprofundar(quantidade):
    if quantidade == 0:
        ate_aqui = 'ainda não temos respostas suas com as suas próprias ideias'
    elif quantidade == 1:
        ate_aqui = 'até aqui você trouxe 1 resposta com as suas próprias ideias'
    else:
        ate_aqui = f'até aqui você trouxe {quantidade} respostas com as suas próprias ideias'
    return (
        f'Ainda é cedo para a síntese: {ate_aqui}, e ela fica rica a partir de '
        f'{MINIMO_RESPOSTAS_PARA_CONCLUIR}. Vamos aprofundar mais um pouco? Volte à última pergunta e '
        'explique com as suas palavras o porquê da sua resposta. Respostas muito curtas ou repetidas não contam.'
    )


def concluir(sessao):
    """
    Pede a conclusão. Com menos de 3 respostas legítimas, o Enéas orienta a aprofundar e nada muda.
    Com 3 ou mais, registra a síntese final e finaliza a sessão com os pontos + bônus.
    Devolve ``(mensagens_novas, concluida)``.
    """
    mensagens = list(sessao.mensagens.all())
    quantidade = len(respostas_legitimas(sessao, mensagens))
    if quantidade < MINIMO_RESPOSTAS_PARA_CONCLUIR:
        orientacao = MensagemSessao.objects.create(
            sessao=sessao, autor=MensagemSessao.Autor.ENEAS, conteudo=_orientacao_para_aprofundar(quantidade))
        return [orientacao], False

    # A síntese é pedida fora da transação (pode levar segundos); a sessão é travada só para gravar.
    try:
        sintese = tutor.sintetizar(sessao, mensagens)
    except tutor.TutorIndisponivel:
        sintese = tutor.sintese_simulada(sessao, mensagens)
    with transaction.atomic():
        travada = SessaoEstudo.objects.select_for_update().get(pk=sessao.pk)
        if travada.status != SessaoEstudo.Status.EM_ANDAMENTO:
            raise SessaoEncerrada
        final = MensagemSessao.objects.create(
            sessao=sessao, autor=MensagemSessao.Autor.ENEAS, conteudo=sintese.texto, tokens_utilizados=sintese.tokens)
        travada.finalizar(pontuacao=pontos_de_participacao(quantidade) + BONUS_CONCLUSAO,
                          status=SessaoEstudo.Status.CONCLUIDA)
    sessao.refresh_from_db()
    return [final], True
