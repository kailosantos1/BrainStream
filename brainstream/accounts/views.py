from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render, resolve_url
from django.utils.http import url_has_allowed_host_and_scheme
from django.db import IntegrityError
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from estudos.metricas import desempenho, iniciais
from estudos.models import SessaoEstudo

from . import google
from .avatar import salvar_avatar
from .forms import CadastroForm, DefinirSenhaForm, LoginForm, PerfilForm, TrocarSenhaForm
from .models import Estudante, normalizar_email


def _destino(request):
    """Respeita ?next= apenas para URLs do próprio site."""
    destino = request.POST.get('next') or request.GET.get('next')
    if destino and url_has_allowed_host_and_scheme(destino, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        return destino
    return resolve_url(settings.LOGIN_REDIRECT_URL)


@require_http_methods(['GET', 'POST'])
def cadastro(request):
    if request.user.is_authenticated:
        return redirect(_destino(request))
    form = CadastroForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        login(request, user, backend='django.contrib.auth.backends.ModelBackend')
        return redirect(_destino(request))
    return render(request, 'accounts/cadastro.html', {'form': form, 'next': request.GET.get('next', '')})


@require_http_methods(['GET', 'POST'])
def entrar(request):
    if request.user.is_authenticated:
        return redirect(_destino(request))
    form = LoginForm(request, data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        login(request, form.get_user())
        return redirect(_destino(request))
    return render(request, 'accounts/login.html', {'form': form, 'next': request.POST.get('next') or request.GET.get('next', '')})


@require_POST
def sair(request):
    logout(request)
    return redirect('core:index')


@login_required
@require_http_methods(['GET', 'POST'])
def perfil(request):
    """Meu Perfil: dados da conta (nome, foto, senha) e aba de desempenho. Cada formulário tem seu botão."""
    acao = request.POST.get('acao') if request.method == 'POST' else None
    perfil_form = PerfilForm(request.POST if acao == 'perfil' else None, request.FILES if acao == 'perfil' else None,
                             instance=request.user)
    # Contas criadas pelo Google não têm senha: definem a primeira sem informar a atual.
    form_senha = TrocarSenhaForm if request.user.has_usable_password() else DefinirSenhaForm
    senha_form = form_senha(request.user, request.POST if acao == 'senha' else None)

    if acao == 'perfil' and perfil_form.is_valid():
        perfil_form.save()
        messages.success(request, 'Dados da conta atualizados.')
        return redirect('accounts:perfil')
    if acao == 'senha' and senha_form.is_valid():
        usuario = senha_form.save()
        update_session_auth_hash(request, usuario)  # trocar a senha não desconecta esta sessão
        messages.success(request, 'Senha salva. Use a nova senha no próximo acesso.')
        return redirect('accounts:perfil')
    if acao == 'perfil':
        request.user.refresh_from_db()  # o formulário inválido não deve alterar o nome exibido

    return render(request, 'accounts/perfil.html', {
        'perfil_form': perfil_form,
        'senha_form': senha_form,
        'senha_aberta': acao == 'senha',
        'iniciais': iniciais(request.user),
        'historico': SessaoEstudo.objects.filter(
            estudante=request.user, visivel_no_historico=True).select_related('tema')[:8],
        'desempenho': desempenho(request.user),
    }, status=400 if acao and (perfil_form.errors or senha_form.errors) else 200)


# ---------- Login com Google ----------

def _destino_seguro(request, destino):
    if destino and url_has_allowed_host_and_scheme(destino, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        return destino
    return resolve_url(settings.LOGIN_REDIRECT_URL)


@require_GET
def google_login(request):
    if not google.configurado():
        messages.warning(request, 'Login com Google não configurado neste ambiente. Entre com e-mail e senha.')
        return redirect('accounts:login')
    if request.user.is_authenticated:
        return redirect(_destino(request))
    return redirect(google.iniciar(request.session, _destino(request)))


def _estudante_do_google(dados):
    """Encontra a conta pelo e-mail (verificado pelo Google) ou cria uma nova, sem senha."""
    email = normalizar_email(dados['email'])
    estudante = Estudante.objects.filter(email__iexact=email).first()
    criado = False
    if estudante is None:
        try:
            estudante = Estudante.objects.create_user(email=email, nome=dados['nome'] or email.split('@')[0])
            criado = True
        except IntegrityError:  # dois retornos simultâneos para o mesmo e-mail
            estudante = Estudante.objects.get(email__iexact=email)
    if not estudante.is_active:
        raise google.FalhaGoogle('Esta conta está desativada. Fale com o suporte do BrainStream.')
    if not estudante.avatar and dados['foto']:
        foto = google.baixar_foto(dados['foto'])
        if foto is not None:
            salvar_avatar(estudante, foto)
            estudante.save(update_fields=['avatar'])
    return estudante, criado


@require_GET
def google_callback(request):
    try:
        guardado = google.validar_retorno(request.session, request.GET.get('state'))
        if request.GET.get('error'):
            raise google.FalhaGoogle('Login com Google cancelado. Você pode tentar de novo ou entrar com e-mail e senha.')
        codigo = request.GET.get('code')
        if not codigo:
            raise google.FalhaGoogle('O Google não confirmou o login. Tente de novo.')
        dados = google.dados_do_usuario(google.trocar_codigo(codigo, guardado['verificador']))
        estudante, criado = _estudante_do_google(dados)
    except google.FalhaGoogle as falha:
        messages.error(request, falha.mensagem)
        return redirect('accounts:login')

    login(request, estudante, backend='django.contrib.auth.backends.ModelBackend')
    if criado:
        messages.success(request, f'Conta criada com o Google. Boas-vindas, {estudante.get_short_name()}!')
    return redirect(_destino_seguro(request, guardado.get('destino')))
