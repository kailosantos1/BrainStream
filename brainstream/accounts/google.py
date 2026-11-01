"""
Login com Google (OAuth 2.0 + OpenID Connect, fluxo "authorization code" com PKCE).

Os dados do usuário vêm do endpoint userinfo, chamado pelo servidor com o token recém-trocado
diretamente com o Google por HTTPS; por isso não é preciso validar a assinatura do id_token.
"""
import base64
import hashlib
import logging
import secrets
import time
from io import BytesIO
from urllib.parse import urlencode, urlsplit

import httpx
from django.conf import settings

from .avatar import AVATAR_LIMITE_BYTES, ImagemInvalida, processar_avatar

logger = logging.getLogger(__name__)

URL_AUTORIZACAO = 'https://accounts.google.com/o/oauth2/v2/auth'
URL_TOKEN = 'https://oauth2.googleapis.com/token'
URL_USERINFO = 'https://openidconnect.googleapis.com/v1/userinfo'
ESCOPOS = 'openid email profile'
CHAVE_SESSAO = 'google_oauth'
VALIDADE_SEGUNDOS = 600
TIMEOUT_SEGUNDOS = 10


class FalhaGoogle(Exception):
    """Algo impediu o login com Google; ``mensagem`` é segura para mostrar ao estudante."""

    def __init__(self, mensagem):
        super().__init__(mensagem)
        self.mensagem = mensagem


def configurado():
    return bool(settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET)


def _desafio_pkce(verificador):
    resumo = hashlib.sha256(verificador.encode('ascii')).digest()
    return base64.urlsafe_b64encode(resumo).rstrip(b'=').decode('ascii')


def iniciar(sessao, destino):
    """Gera ``state`` e o verificador PKCE, guarda na sessão e devolve a URL de autorização do Google."""
    state = secrets.token_urlsafe(32)
    verificador = secrets.token_urlsafe(64)
    sessao[CHAVE_SESSAO] = {'state': state, 'verificador': verificador, 'destino': destino, 'criado': time.time()}
    parametros = {
        'client_id': settings.GOOGLE_CLIENT_ID,
        'redirect_uri': settings.GOOGLE_REDIRECT_URI,
        'response_type': 'code',
        'scope': ESCOPOS,
        'state': state,
        'code_challenge': _desafio_pkce(verificador),
        'code_challenge_method': 'S256',
        'prompt': 'select_account',
    }
    return f'{URL_AUTORIZACAO}?{urlencode(parametros)}'


def validar_retorno(sessao, state_recebido):
    """
    Consome (uso único) o que foi guardado em ``iniciar`` e confere o ``state`` em tempo constante.
    Devolve os dados guardados; ``state`` ausente, vencido ou diferente vira ``FalhaGoogle``.
    """
    guardado = sessao.pop(CHAVE_SESSAO, None)
    if (
        not guardado or not state_recebido
        or time.time() - guardado.get('criado', 0) > VALIDADE_SEGUNDOS
        or not secrets.compare_digest(str(guardado.get('state', '')), str(state_recebido))
    ):
        raise FalhaGoogle('Não foi possível confirmar o login com Google. Tente de novo.')
    return guardado


def trocar_codigo(codigo, verificador):
    """Troca o ``code`` pelo access token (servidor → Google)."""
    try:
        resposta = httpx.post(URL_TOKEN, data={
            'code': codigo,
            'client_id': settings.GOOGLE_CLIENT_ID,
            'client_secret': settings.GOOGLE_CLIENT_SECRET,
            'redirect_uri': settings.GOOGLE_REDIRECT_URI,
            'grant_type': 'authorization_code',
            'code_verifier': verificador,
        }, timeout=TIMEOUT_SEGUNDOS)
    except httpx.HTTPError as erro:
        logger.warning('Falha de rede ao trocar o código do Google (%s).', type(erro).__name__)
        raise FalhaGoogle('O Google não respondeu agora. Tente de novo em instantes.') from erro
    if resposta.status_code != 200:
        # Não registra o corpo: pode ecoar o código de autorização.
        logger.warning('Google recusou a troca do código (HTTP %s).', resposta.status_code)
        raise FalhaGoogle('O Google não confirmou o login. Tente de novo.')
    token = resposta.json().get('access_token')
    if not token:
        raise FalhaGoogle('O Google não confirmou o login. Tente de novo.')
    return token


def dados_do_usuario(token):
    """E-mail (obrigatoriamente verificado), nome e foto da conta Google."""
    try:
        resposta = httpx.get(URL_USERINFO, headers={'Authorization': f'Bearer {token}'}, timeout=TIMEOUT_SEGUNDOS)
    except httpx.HTTPError as erro:
        logger.warning('Falha de rede ao ler os dados da conta Google (%s).', type(erro).__name__)
        raise FalhaGoogle('O Google não respondeu agora. Tente de novo em instantes.') from erro
    if resposta.status_code != 200:
        logger.warning('Google recusou a leitura dos dados da conta (HTTP %s).', resposta.status_code)
        raise FalhaGoogle('O Google não confirmou o login. Tente de novo.')
    dados = resposta.json()
    email = (dados.get('email') or '').strip()
    # Sem e-mail verificado, alguém poderia entrar na conta de outra pessoa que usa o mesmo endereço.
    if not email or dados.get('email_verified') is not True:
        raise FalhaGoogle('Sua conta Google não tem um e-mail verificado. Verifique o e-mail no Google ou entre com e-mail e senha.')
    nome = ' '.join((dados.get('name') or '').split())[:150]
    return {'email': email, 'nome': nome, 'foto': dados.get('picture') or ''}


def baixar_foto(url):
    """
    Baixa a foto do perfil Google (só HTTPS em *.googleusercontent.com, até 2 MB) e devolve o
    conteúdo já processado como avatar, ou None. Falhas não impedem o login.
    """
    partes = urlsplit(url or '')
    if partes.scheme != 'https' or not (partes.hostname or '').endswith('.googleusercontent.com'):
        return None
    if url.endswith('=s96-c'):
        url = url[:-len('=s96-c')] + '=s256-c'  # tamanho próximo ao do avatar
    try:
        with httpx.stream('GET', url, timeout=TIMEOUT_SEGUNDOS, follow_redirects=False) as resposta:
            if resposta.status_code != 200:
                return None
            conteudo = BytesIO()
            for bloco in resposta.iter_bytes():
                conteudo.write(bloco)
                if conteudo.tell() > AVATAR_LIMITE_BYTES:
                    return None
        return processar_avatar(conteudo)
    except (httpx.HTTPError, ImagemInvalida) as erro:
        logger.info('Foto da conta Google não aproveitada (%s).', type(erro).__name__)
        return None
