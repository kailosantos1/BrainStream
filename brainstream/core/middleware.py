from functools import wraps

from django.contrib.sessions.middleware import SessionMiddleware


def sem_renovar_sessao(view):
    """Requisições automáticas (ex.: atualização do ranking) não contam como atividade do estudante."""
    @wraps(view)
    def envolvida(request, *args, **kwargs):
        request.sem_renovar_sessao = True
        return view(request, *args, **kwargs)
    return envolvida


class SessaoMiddleware(SessionMiddleware):
    """SessionMiddleware que não regrava a sessão (nem renova o prazo de inatividade) nas views marcadas."""

    def process_response(self, request, response):
        if getattr(request, 'sem_renovar_sessao', False):
            return response
        return super().process_response(request, response)
