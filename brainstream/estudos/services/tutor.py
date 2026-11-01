"""
Serviço de IA do Enéas.

Com ``AI_API_KEY`` configurada, a resposta vem do Google Gemini ou da Claude API, conforme
``AI_PROVIDER`` (ou o formato da chave), no modelo de ``AI_MODEL``. Sem chave, um tutor simulado
devolve perguntas socráticas fixas, para desenvolver e testar sem custo nem rede.
A camada de context locking roda antes deste serviço (ver ``conversa.enviar_mensagem``).
"""
import logging
import re
from dataclasses import dataclass

from django.conf import settings
from django.core.cache import cache

from ..models import MensagemSessao
from . import context_locking

logger = logging.getLogger(__name__)

GEMINI = 'gemini'
ANTHROPIC = 'anthropic'
# Versão fixa (comportamento estável): ~1 s por resposta socrática em 2026-10-31. Revise quando o Google
# aposentar a versão (gemini-1.5-flash e gemini-2.5-flash-lite já retornam 404).
MODELO_PADRAO = {GEMINI: 'gemini-3.5-flash-lite', ANTHROPIC: 'claude-opus-5-5'}
PREFIXO_MODELO = {GEMINI: 'gemini', ANTHROPIC: 'claude'}
# Motivos de término do Gemini que indicam resposta bloqueada pelos filtros do Google.
GEMINI_BLOQUEIOS = {'SAFETY', 'PROHIBITED_CONTENT', 'BLOCKLIST', 'SPII', 'RECITATION'}

# Busca na web (Google Search grounding): quando o Gemini a recusa (plano sem a ferramenta, cota),
# o Enéas responde sem busca e não tenta de novo por um tempo, para não pagar a latência da recusa.
CHAVE_BUSCA_PAUSADA = 'estudos:gemini-busca-pausada'
PAUSA_BUSCA_SEGUNDOS = 600
# A busca custa segundos por resposta, então só entra quando o tema ou a mensagem pedem fatos atuais
# (padrões já normalizados: minúsculas e sem acentos). Conceitos estáveis dispensam a web.
PEDE_FATOS_ATUAIS = re.compile(
    r'\b(hoje em dia|atualmente|atua(l|is)|recente(s|mente)?|noticias?|cotacao|estatisticas?|20[2-3]\d'
    r'|ultim[oa]s? (noticias?|dados|anos?|meses|pesquisas?|descobertas?|eleic\w*)'
    r'|(neste|nesse|este|esse) ano|ano passado|ainda (existe|vale|esta em vigor))\b'
)

# Limita o custo por chamada: o Enéas responde em poucas frases, então o histórico recente basta.
LIMITE_HISTORICO = 30
# Modelos que aceitam o fallback automático do servidor quando um classificador recusa a resposta.
MODELOS_COM_FALLBACK = {'claude-fable-5-1', 'claude-opus-5-5', 'claude-opus-5', 'claude-sonnet-5-5'}

PERGUNTAS_SIMULADAS = [
    'Interessante! Você trouxe um ponto importante. O que te leva a pensar assim sobre {tema}?',
    'Vamos aprofundar: como isso se relaciona com o contexto maior de {tema}? '
    'O que aconteceria se uma das condições fosse alterada?',
    'Consegue pensar em um exemplo concreto que ilustre o que você acabou de dizer?',
    'Se alguém discordasse de você, qual seria o argumento mais forte contra a sua ideia? Como você responderia?',
    'Que evidência ou raciocínio sustenta essa conclusão? Como você poderia testá-la?',
    'Com suas palavras: o que você entende agora sobre {tema} que não estava claro no começo?',
]


class TutorIndisponivel(Exception):
    """A IA não respondeu (configuração, rede, limite ou recusa); a view mostra um aviso ao estudante."""


@dataclass(frozen=True)
class RespostaTutor:
    texto: str
    tokens: int = 0


def simulacao_ativa():
    return not settings.AI_API_KEY


def provedor():
    """``AI_PROVIDER`` explícito; sem ele, chaves do Google (``AIza...``) usam o Gemini e as demais, a Claude API."""
    escolhido = settings.AI_PROVIDER
    if escolhido in ('', 'auto'):
        return GEMINI if settings.AI_API_KEY.startswith('AIza') else ANTHROPIC
    if escolhido in (GEMINI, 'google'):
        return GEMINI
    if escolhido in (ANTHROPIC, 'claude'):
        return ANTHROPIC
    logger.error('AI_PROVIDER inválido: use "gemini" ou "anthropic".')
    raise TutorIndisponivel('provedor desconhecido')


def modelo(nome_provedor):
    """``AI_MODEL`` quando pertence ao provedor; caso contrário, o padrão dele (evita mandar "claude-*" ao Gemini)."""
    configurado = settings.AI_MODEL
    if configurado and configurado.startswith(PREFIXO_MODELO[nome_provedor]):
        return configurado
    if configurado:
        logger.warning('AI_MODEL não corresponde ao provedor %s; usando %s.', nome_provedor, MODELO_PADRAO[nome_provedor])
    return MODELO_PADRAO[nome_provedor]


def montar_historico(sessao, mensagens):
    """
    Converte as mensagens salvas no formato da API: começa pelo estudante, alterna papéis e deixa
    de fora avisos do sistema e mensagens que o context locking bloqueou.
    """
    abertura = {'role': 'user', 'content': f'Quero estudar {sessao.tema.nome} no Modo Guiado.'}
    historico = [abertura]
    relevantes = [
        mensagem for mensagem in mensagens
        if mensagem.autor == MensagemSessao.Autor.ENEAS
        or (mensagem.autor == MensagemSessao.Autor.ESTUDANTE
            and context_locking.verificar(mensagem.conteudo, sessao.tema.nome) is None)
    ]
    for mensagem in relevantes[-LIMITE_HISTORICO:]:
        papel = 'assistant' if mensagem.autor == MensagemSessao.Autor.ENEAS else 'user'
        if historico[-1]['role'] == papel:
            historico[-1]['content'] += '\n\n' + mensagem.conteudo
        else:
            historico.append({'role': papel, 'content': mensagem.conteudo})
    return historico


def responder(sessao, mensagens):
    """Gera a próxima fala do Enéas a partir das mensagens da sessão (a última é do estudante)."""
    if simulacao_ativa():
        return _simular(sessao, mensagens)
    nome_provedor = provedor()
    chamar = _chamar_gemini if nome_provedor == GEMINI else _chamar_claude
    return chamar(sessao, montar_historico(sessao, mensagens), modelo(nome_provedor))


def sintetizar(sessao, mensagens):
    """Síntese socrática de encerramento: 2–3 frases com o que o próprio estudante descobriu."""
    if simulacao_ativa():
        return sintese_simulada(sessao, mensagens)
    historico = montar_historico(sessao, mensagens)
    if historico[-1]['role'] == 'user':
        historico[-1]['content'] += '\n\n' + context_locking.PEDIDO_SINTESE
    else:
        historico.append({'role': 'user', 'content': context_locking.PEDIDO_SINTESE})
    sistema = context_locking.prompt_de_sintese(sessao.tema.nome)
    nome_provedor = provedor()
    if nome_provedor == GEMINI:
        texto, tokens = gerar_com_gemini(sistema, historico, modelo(GEMINI))  # síntese não usa busca na web
        return RespostaTutor(texto, tokens=tokens)
    return _chamar_claude(sessao, historico, modelo(nome_provedor), sistema)


def _trecho(texto, palavras=12):
    partes = texto.split()
    trecho = ' '.join(partes[:palavras]).rstrip('.,;:!?')
    return trecho + ('…' if len(partes) > palavras else '')


def sintese_simulada(sessao, mensagens):
    """Síntese sem IA (modo simulado ou falha da API): retoma trechos das próprias respostas do estudante."""
    respostas = [
        mensagem.conteudo for mensagem in mensagens
        if mensagem.autor == MensagemSessao.Autor.ESTUDANTE
        and context_locking.verificar(mensagem.conteudo, sessao.tema.nome) is None
    ]
    destaques = sorted(respostas, key=lambda texto: len(texto.split()), reverse=True)[:2]
    tema = sessao.tema.nome
    if len(destaques) >= 2:
        miolo = f'Com suas próprias palavras, você chegou a ideias como “{_trecho(destaques[0])}” e “{_trecho(destaques[1])}”.'
    elif destaques:
        miolo = f'Com suas próprias palavras, você chegou à ideia de que “{_trecho(destaques[0])}”.'
    else:
        miolo = 'Você explorou o tema com as suas próprias perguntas.'
    return RespostaTutor(
        f'Você percorreu um bom caminho em {tema}. {miolo} '
        'Guarde essas descobertas: elas são o entendimento que você mesmo construiu.'
    )


def _simular(sessao, mensagens):
    respostas = sum(1 for mensagem in mensagens if mensagem.autor == MensagemSessao.Autor.ESTUDANTE)
    pergunta = PERGUNTAS_SIMULADAS[max(respostas - 1, 0) % len(PERGUNTAS_SIMULADAS)]
    return RespostaTutor(pergunta.format(tema=sessao.tema.nome))


def _chamar_claude(sessao, historico, modelo, sistema=None):
    try:
        import anthropic
    except ImportError as erro:
        logger.error('AI_API_KEY está definida, mas o pacote "anthropic" não está instalado.')
        raise TutorIndisponivel('sdk ausente') from erro

    extras = {'output_config': {'effort': 'low'}}
    betas = []
    if modelo in MODELOS_COM_FALLBACK:
        extras['fallbacks'] = 'default'
        betas.append('server-side-fallback-2026-07-01')

    client = anthropic.Anthropic(api_key=settings.AI_API_KEY, timeout=settings.AI_TIMEOUT, max_retries=2)
    try:
        resposta = client.beta.messages.create(
            model=modelo,
            max_tokens=16000,
            system=sistema or context_locking.prompt_de_sistema(sessao.tema.nome),
            messages=historico,
            betas=betas,
            extra_body=extras,
        )
    except (anthropic.AuthenticationError, anthropic.PermissionDeniedError,
            anthropic.NotFoundError, anthropic.BadRequestError) as erro:
        logger.error('Configuração da IA rejeitada (%s): confira AI_API_KEY e AI_MODEL.', type(erro).__name__)
        raise TutorIndisponivel('configuração') from erro
    except anthropic.RateLimitError as erro:
        logger.warning('Limite de uso da IA atingido.')
        raise TutorIndisponivel('limite') from erro
    except anthropic.APIStatusError as erro:
        logger.warning('IA respondeu com erro %s.', erro.status_code)
        raise TutorIndisponivel('erro da api') from erro
    except anthropic.APIConnectionError as erro:
        logger.warning('Falha de conexão com a IA.')
        raise TutorIndisponivel('conexão') from erro

    if resposta.stop_reason == 'refusal':
        raise TutorIndisponivel('recusa')
    texto = '\n\n'.join(bloco.text for bloco in resposta.content if bloco.type == 'text').strip()
    if not texto:
        raise TutorIndisponivel('resposta vazia')
    uso = resposta.usage
    return RespostaTutor(texto, tokens=(uso.input_tokens or 0) + (uso.output_tokens or 0))


def busca_ativa():
    return settings.AI_SEARCH_ENABLED and not cache.get(CHAVE_BUSCA_PAUSADA)


def pede_fatos_atuais(tema, mensagem):
    return bool(PEDE_FATOS_ATUAIS.search(context_locking.normalizar(f'{tema} {mensagem}')))


def _chamar_gemini(sessao, historico, modelo):
    # Só o diálogo do Modo Guiado usa a busca na web: Quiz e Speedrun pedem saída em JSON (ver geracao.py).
    ultima = historico[-1]['content'] if historico[-1]['role'] == 'user' else ''
    buscar = busca_ativa() and pede_fatos_atuais(sessao.tema.nome, ultima)
    texto, tokens = gerar_com_gemini(
        context_locking.prompt_de_sistema(sessao.tema.nome), historico, modelo, buscar=buscar)
    return RespostaTutor(texto, tokens=tokens)


def raciocinio_minimo(modelo, types):
    """
    Configuração de raciocínio mais curto que o modelo aceita: o Enéas responde em poucas frases e não
    precisa de rascunho interno. A família Gemini 3 recusa ``thinking_budget=0`` (400) e usa
    ``thinkingLevel``, que o SDK 1.47 ainda não expõe: vai no corpo da requisição (mesclado ao restante).
    """
    if modelo.startswith('gemini-3'):
        return {'http_options': types.HttpOptions(
            extra_body={'generationConfig': {'thinkingConfig': {'thinkingLevel': 'minimal'}}})}
    if modelo.startswith('gemini-2.5-flash'):
        return {'thinking_config': types.ThinkingConfig(thinking_budget=0)}
    return {}


def gerar_com_gemini(sistema, historico, modelo, buscar=False, rapido=True, **config):
    """
    Uma chamada ao Gemini com a instrução de sistema e o histórico no formato ``{'role', 'content'}``.
    Devolve ``(texto, tokens)``; qualquer falha, bloqueio ou resposta vazia vira ``TutorIndisponivel``.
    ``buscar`` liga a ferramenta oficial de busca do Google (grounding); se o Gemini a recusar, a
    chamada é refeita sem ela. ``rapido`` pede o raciocínio mínimo do modelo (ver ``raciocinio_minimo``);
    se o modelo o recusar, a chamada é refeita no padrão dele. ``config`` vai direto para ``GenerateContentConfig`` (ex.: JSON no Quiz).
    """
    try:
        import httpx
        from google import genai
        from google.genai import errors, types
    except ImportError as erro:
        logger.error('AI_PROVIDER aponta para o Gemini, mas o pacote "google-genai" não está instalado.')
        raise TutorIndisponivel('sdk ausente') from erro

    # Com a busca ligada, um 429 costuma ser o plano recusando a ferramenta: não vale repetir (o fallback
    # sem busca resolve na hora). Erros transitórios do servidor continuam com novas tentativas.
    repetir = types.HttpRetryOptions(attempts=3, http_status_codes=[408, 500, 502, 503, 504]) if buscar \
        else types.HttpRetryOptions(attempts=3)
    client = genai.Client(
        api_key=settings.AI_API_KEY,
        http_options=types.HttpOptions(
            timeout=int(settings.AI_TIMEOUT * 1000),  # milissegundos no SDK do Google
            retry_options=repetir,
        ),
    )
    # O Gemini chama a fala do assistente de "model".
    conteudos = [
        types.Content(role='model' if item['role'] == 'assistant' else 'user', parts=[types.Part(text=item['content'])])
        for item in historico
    ]
    extras = raciocinio_minimo(modelo, types) if rapido else {}
    if buscar:
        extras['tools'] = [types.Tool(google_search=types.GoogleSearch())]
    try:
        resposta = client.models.generate_content(
            model=modelo,
            contents=conteudos,
            config=types.GenerateContentConfig(system_instruction=sistema, **{**extras, **config}),
        )
    except errors.ClientError as erro:
        if buscar and erro.code in (400, 403, 429):
            logger.warning('Busca na web do Gemini recusada (%s %s); respondendo sem busca e pausando por %d min.',
                           erro.code, erro.status, PAUSA_BUSCA_SEGUNDOS // 60)
            cache.set(CHAVE_BUSCA_PAUSADA, True, PAUSA_BUSCA_SEGUNDOS)
            return gerar_com_gemini(sistema, historico, modelo, buscar=False, rapido=rapido, **config)
        if erro.code == 400 and rapido and raciocinio_minimo(modelo, types):
            logger.warning('O modelo %s recusou o raciocínio mínimo; repetindo com o padrão dele.', modelo)
            return gerar_com_gemini(sistema, historico, modelo, buscar=False, rapido=False, **config)
        if erro.code == 429:
            logger.warning('Limite de uso do Gemini atingido.')
            raise TutorIndisponivel('limite') from erro
        logger.error('Gemini rejeitou a requisição (%s %s): confira AI_API_KEY e AI_MODEL.', erro.code, erro.status)
        raise TutorIndisponivel('configuração') from erro
    except errors.APIError as erro:
        logger.warning('Gemini respondeu com erro %s.', erro.code)
        raise TutorIndisponivel('erro da api') from erro
    except httpx.HTTPError as erro:
        logger.warning('Falha de conexão com o Gemini.')
        raise TutorIndisponivel('conexão') from erro

    feedback = resposta.prompt_feedback
    if feedback is not None and feedback.block_reason:
        raise TutorIndisponivel('recusa')
    candidatos = resposta.candidates or []
    motivo = candidatos[0].finish_reason if candidatos else None
    if motivo is not None and getattr(motivo, 'name', str(motivo)) in GEMINI_BLOQUEIOS:
        raise TutorIndisponivel('recusa')
    metadados = candidatos[0].grounding_metadata if candidatos else None
    if metadados is not None and metadados.web_search_queries:
        consultas = [consulta[:100] for consulta in metadados.web_search_queries]
        logger.info('Enéas consultou a web (%d busca(s)): %s', len(consultas), ' | '.join(consultas))
    texto = (resposta.text or '').strip()
    if not texto:
        raise TutorIndisponivel('resposta vazia')
    uso = resposta.usage_metadata
    tokens = 0
    if uso is not None:
        tokens = uso.total_token_count or (uso.prompt_token_count or 0) + (uso.candidates_token_count or 0)
    return texto, tokens
