from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


def normalizar_email(email):
    return BaseUserManager.normalize_email(email).strip().lower()


class EstudanteManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError('O e-mail é obrigatório.')
        user = self.model(email=normalizar_email(email), **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        if not extra_fields['is_staff'] or not extra_fields['is_superuser']:
            raise ValueError('Superusuário precisa de is_staff e is_superuser.')
        return self._create_user(email, password, **extra_fields)

    def get_by_natural_key(self, email):
        return self.get(email__iexact=normalizar_email(email))


class Estudante(AbstractUser):
    """Conta do estudante: o e-mail é o login e o nome completo substitui first/last name."""

    username = None
    first_name = None
    last_name = None
    nome = models.CharField('nome completo', max_length=150)
    # Foto já processada (quadrada, 256 px, WebP, sem EXIF) por PerfilForm; vazio = mostra as iniciais.
    avatar = models.ImageField('foto de perfil', upload_to='avatares/', blank=True)
    email = models.EmailField(
        'e-mail',
        unique=True,
        error_messages={'unique': 'Já existe uma conta com este e-mail.'},
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['nome']

    objects = EstudanteManager()

    class Meta:
        verbose_name = 'estudante'
        verbose_name_plural = 'estudantes'

    def __str__(self):
        return self.email

    def clean(self):
        super().clean()
        self.email = normalizar_email(self.email)

    def get_full_name(self):
        return self.nome

    def get_short_name(self):
        return self.nome.split()[0] if self.nome else self.email
