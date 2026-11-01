from django import forms
from django.contrib.auth import password_validation
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm, PasswordResetForm, SetPasswordForm

from .avatar import AVATAR_FORMATOS, AVATAR_LIMITE_BYTES, AVATAR_LIMITE_PIXELS, processar_avatar, salvar_avatar
from .models import Estudante, normalizar_email


class CamposEstilizadosMixin:
    """Aplica as classes do formulário de autenticação e marca campos inválidos para leitores de tela."""

    classe_campo = 'form-control auth-input'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if not isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs['class'] = self.classe_campo

    def full_clean(self):
        super().full_clean()
        for name in self.errors:
            if name in self.fields:
                attrs = self.fields[name].widget.attrs
                attrs['class'] += ' is-invalid'
                attrs['aria-invalid'] = 'true'
                attrs['aria-describedby'] = f'id_{name}-erro'


class CadastroForm(CamposEstilizadosMixin, forms.ModelForm):
    password = forms.CharField(
        label='Senha',
        strip=False,
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password', 'placeholder': 'Mínimo de 8 caracteres'}),
    )

    class Meta:
        model = Estudante
        fields = ('nome', 'email')
        labels = {'nome': 'Nome completo', 'email': 'E-mail'}
        widgets = {
            'nome': forms.TextInput(attrs={'autocomplete': 'name', 'placeholder': 'Maria Souza', 'autofocus': True}),
            'email': forms.EmailInput(attrs={'autocomplete': 'email', 'placeholder': 'maria@email.com'}),
        }

    def clean_nome(self):
        return ' '.join(self.cleaned_data['nome'].split())

    def clean_email(self):
        email = normalizar_email(self.cleaned_data['email'])
        if Estudante.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('Já existe uma conta com este e-mail. Entre ou recupere a senha.', code='email_duplicado')
        return email

    def _post_clean(self):
        super()._post_clean()
        # A validação de senha roda depois de nome e e-mail estarem na instância (checagem de similaridade).
        password = self.cleaned_data.get('password')
        if password:
            try:
                password_validation.validate_password(password, self.instance)
            except forms.ValidationError as error:
                self.add_error('password', error)

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
        return user


class LoginForm(CamposEstilizadosMixin, AuthenticationForm):
    error_messages = {
        'invalid_login': 'E-mail ou senha incorretos. Confira os dados e tente novamente.',
        'inactive': 'Esta conta está desativada.',
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'] = forms.EmailField(
            label='E-mail',
            widget=forms.EmailInput(attrs={'autocomplete': 'email', 'autofocus': True, 'placeholder': 'maria@email.com', 'class': 'form-control auth-input'}),
        )
        self.fields['password'].widget.attrs['placeholder'] = 'Sua senha'

    def clean_username(self):
        return normalizar_email(self.cleaned_data['username'])


class RecuperarSenhaForm(CamposEstilizadosMixin, PasswordResetForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].label = 'E-mail'
        self.fields['email'].widget.attrs.update({'placeholder': 'maria@email.com', 'autofocus': True})


class RedefinirSenhaForm(CamposEstilizadosMixin, SetPasswordForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['new_password1'].label = 'Nova senha'
        self.fields['new_password2'].label = 'Confirme a nova senha'
        self.fields['new_password1'].help_text = ''


class PerfilForm(CamposEstilizadosMixin, forms.ModelForm):
    """Nome completo e foto opcional. A foto é sempre reprocessada: quadrada, 256 px, WebP e sem EXIF."""

    classe_campo = 'form-control painel-input'
    avatar = forms.ImageField(
        label='Foto de perfil', required=False,
        widget=forms.FileInput(attrs={'accept': 'image/jpeg,image/png,image/webp'}),
        error_messages={'invalid_image': 'Envie uma imagem JPG, PNG ou WebP válida.'},
    )
    remover_avatar = forms.BooleanField(label='Remover foto e usar as iniciais', required=False)

    class Meta:
        model = Estudante
        fields = ('nome',)
        labels = {'nome': 'Nome completo'}
        widgets = {'nome': forms.TextInput(attrs={'autocomplete': 'name'})}
        error_messages = {'nome': {'required': 'Informe seu nome completo.'}}

    def clean_nome(self):
        nome = ' '.join(self.cleaned_data['nome'].split())
        if len(nome) < 2:
            raise forms.ValidationError('Informe seu nome completo.')
        return nome

    def clean_avatar(self):
        arquivo = self.cleaned_data.get('avatar')
        if not arquivo:
            return None
        if arquivo.size > AVATAR_LIMITE_BYTES:
            raise forms.ValidationError('A foto pode ter até 2 MB.')
        # O ImageField do Django já abriu e verificou a imagem com o Pillow; aqui conferimos formato e tamanho.
        imagem = getattr(arquivo, 'image', None)
        if imagem is None or imagem.format not in AVATAR_FORMATOS:
            raise forms.ValidationError('Envie uma imagem JPG, PNG ou WebP.')
        if max(imagem.size) > AVATAR_LIMITE_PIXELS:
            raise forms.ValidationError(f'A foto pode ter até {AVATAR_LIMITE_PIXELS} px de lado.')
        return arquivo

    def save(self, commit=True):
        estudante = super().save(commit=False)
        novo = self.cleaned_data.get('avatar')
        if novo:
            salvar_avatar(estudante, processar_avatar(novo))
        elif self.cleaned_data.get('remover_avatar') and estudante.avatar:
            estudante.avatar.delete(save=False)
        if commit:
            estudante.save()
        return estudante


class DefinirSenhaForm(CamposEstilizadosMixin, SetPasswordForm):
    """Para contas criadas pelo Google (sem senha): define a primeira senha sem pedir a atual."""

    classe_campo = 'form-control painel-input'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['new_password2'].label = 'Confirme a nova senha'


class TrocarSenhaForm(CamposEstilizadosMixin, PasswordChangeForm):
    classe_campo = 'form-control painel-input'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['old_password'].label = 'Senha atual'
        self.fields['new_password2'].label = 'Confirme a nova senha'
        self.fields['old_password'].widget.attrs.pop('autofocus', None)  # a aba abre no nome, não aqui
