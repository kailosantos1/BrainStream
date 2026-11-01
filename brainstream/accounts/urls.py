from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy

from . import views
from .forms import RecuperarSenhaForm, RedefinirSenhaForm

app_name = 'accounts'

urlpatterns = [
    path('cadastro/', views.cadastro, name='cadastro'),
    path('login/', views.entrar, name='login'),
    path('logout/', views.sair, name='logout'),
    path('perfil/', views.perfil, name='perfil'),
    path('accounts/google/login/', views.google_login, name='google_login'),
    path('accounts/google/callback/', views.google_callback, name='google_callback'),
    path('recuperar-senha/', auth_views.PasswordResetView.as_view(
        form_class=RecuperarSenhaForm,
        template_name='accounts/recuperar_senha.html',
        email_template_name='accounts/emails/recuperar_senha.txt',
        subject_template_name='accounts/emails/recuperar_senha_assunto.txt',
        success_url=reverse_lazy('accounts:recuperar_senha_enviado'),
    ), name='recuperar_senha'),
    path('recuperar-senha/enviado/', auth_views.PasswordResetDoneView.as_view(
        template_name='accounts/recuperar_senha_enviado.html',
    ), name='recuperar_senha_enviado'),
    path('redefinir-senha/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        form_class=RedefinirSenhaForm,
        template_name='accounts/redefinir_senha.html',
        success_url=reverse_lazy('accounts:redefinir_senha_concluido'),
    ), name='redefinir_senha'),
    path('redefinir-senha/concluido/', auth_views.PasswordResetCompleteView.as_view(
        template_name='accounts/redefinir_senha_concluido.html',
    ), name='redefinir_senha_concluido'),
]
