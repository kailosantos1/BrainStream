from datetime import timedelta

from django import template
from django.utils import formats, timezone

register = template.Library()


@register.filter
def dia_relativo(valor):
    """'Hoje', 'Ontem' ou a data curta ('11 ago') no fuso local."""
    if not valor:
        return ''
    dia = timezone.localtime(valor).date()
    hoje = timezone.localdate()
    if dia == hoje:
        return 'Hoje'
    if dia == hoje - timedelta(days=1):
        return 'Ontem'
    return formats.date_format(dia, 'j M').lower()


@register.filter
def duracao(valor):
    """timedelta → '3 h 25 min', '42 min' ou '0 min'."""
    minutos = int(valor.total_seconds() // 60) if valor else 0
    horas, minutos = divmod(minutos, 60)
    if horas:
        return f'{horas} h {minutos} min' if minutos else f'{horas} h'
    return f'{minutos} min'


@register.inclusion_tag('core/_avatar.html')
def avatar(estudante, classe=''):
    """Foto de perfil, quando houver; senão as iniciais no círculo de destaque."""
    from estudos.metricas import iniciais
    return {'estudante': estudante, 'iniciais': iniciais(estudante), 'classe': classe}


@register.inclusion_tag('core/_perfil_rodape.html', takes_context=True)
def rodape_perfil(context):
    """Rodapé da lateral (painel e telas de estudo): avatar, nome, pontos, link para "Meu Perfil" e sair."""
    from estudos.metricas import pontos_totais
    request = context['request']
    return {
        'estudante': request.user,
        'pontos_totais': pontos_totais(request.user),
        'csrf_token': context.get('csrf_token'),
        'no_perfil': request.resolver_match and request.resolver_match.view_name == 'accounts:perfil',
    }
