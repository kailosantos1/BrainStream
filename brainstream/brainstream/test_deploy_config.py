"""Testes das configurações de infraestrutura para implantação (Vercel, TiDB Cloud, Supabase S3 e OAuth HTTPS)."""
from io import BytesIO
from urllib.parse import parse_qs, urlsplit

from django.conf import settings
from django.contrib.sessions.middleware import SessionMiddleware
from django.core.exceptions import ImproperlyConfigured
from django.test import RequestFactory, SimpleTestCase, override_settings
from PIL import Image

from accounts import views as accounts_views
from accounts.avatar import AVATAR_TAMANHO, processar_avatar
from brainstream.settings import (
    _configurar_allowed_hosts,
    _configurar_banco,
    _configurar_csrf_trusted_origins,
    _configurar_storages,
)


class BancoDeDadosConfigTests(SimpleTestCase):
    def test_banco_local_sem_tls_obrigatorio(self):
        cfg = _configurar_banco({
            'DB_NAME': 'brainstream',
            'DB_USER': 'brainstream',
            'DB_PASSWORD': 'segredo-local',
            'DB_HOST': 'localhost',
            'DB_PORT': '3306',
            'DB_SSL_CA': '',
        })
        self.assertEqual(cfg['ENGINE'], 'django.db.backends.mysql')
        self.assertEqual(cfg['HOST'], 'localhost')
        self.assertEqual(cfg['PORT'], '3306')
        self.assertEqual(cfg['CONN_MAX_AGE'], 0)
        self.assertNotIn('OPTIONS', cfg)

    def test_banco_remoto_tidb_com_tls_e_verificacao_de_identidade(self):
        cfg = _configurar_banco({
            'DB_NAME': 'brainstream',
            'DB_USER': 'abc.root',
            'DB_PASSWORD': 'segredo-remoto',
            'DB_HOST': 'gateway01.us-east-1.prod.aws.tidbcloud.com',
            'DB_PORT': '4000',
            'DB_SSL_CA': '/etc/ssl/certs/ca-certificates.crt',
        })
        self.assertEqual(cfg['ENGINE'], 'django.db.backends.mysql')
        self.assertEqual(cfg['PORT'], '4000')
        self.assertEqual(cfg['CONN_MAX_AGE'], 0)
        self.assertEqual(cfg['OPTIONS'], {
            'ssl_ca': '/etc/ssl/certs/ca-certificates.crt',
            'ssl_verify_cert': True,
            'ssl_verify_identity': True,
        })


class SupabaseStorageConfigTests(SimpleTestCase):
    SUPABASE_COMPLETO = {
        'SUPABASE_PROJECT_REF': 'projexemplo123',
        'SUPABASE_S3_ENDPOINT': 'https://projexemplo123.storage.supabase.co/storage/v1/s3/',
        'SUPABASE_S3_REGION': 'sa-east-1',
        'SUPABASE_S3_BUCKET': 'avatars',
        'SUPABASE_S3_ACCESS_KEY': 'chave-acesso-teste',
        'SUPABASE_S3_SECRET_KEY': 'chave-secreta-teste',
    }

    def test_sem_variaveis_supabase_usa_armazenamento_local(self):
        storages = _configurar_storages({}, debug=True)
        self.assertEqual(storages['default']['BACKEND'], 'django.core.files.storage.FileSystemStorage')
        self.assertEqual(storages['staticfiles']['BACKEND'], 'django.contrib.staticfiles.storage.StaticFilesStorage')

    def test_configuracao_parcial_supabase_falha_explicitamente(self):
        parcial = {
            'SUPABASE_PROJECT_REF': 'projexemplo123',
            'SUPABASE_S3_BUCKET': 'avatars',
        }
        with self.assertRaises(ImproperlyConfigured) as ctx:
            _configurar_storages(parcial, debug=False)
        mensagem = str(ctx.exception)
        self.assertIn('SUPABASE_S3_ENDPOINT', mensagem)
        self.assertIn('SUPABASE_S3_REGION', mensagem)
        self.assertIn('SUPABASE_S3_ACCESS_KEY', mensagem)
        self.assertIn('SUPABASE_S3_SECRET_KEY', mensagem)

    def test_configuracao_completa_supabase_s3_e_whitenoise_em_producao(self):
        storages = _configurar_storages(self.SUPABASE_COMPLETO, debug=False)
        default = storages['default']
        self.assertEqual(default['BACKEND'], 'storages.backends.s3.S3Storage')
        opts = default['OPTIONS']
        self.assertEqual(opts['bucket_name'], 'avatars')
        self.assertEqual(opts['region_name'], 'sa-east-1')
        self.assertEqual(opts['endpoint_url'], 'https://projexemplo123.storage.supabase.co/storage/v1/s3')
        self.assertEqual(opts['custom_domain'], 'projexemplo123.supabase.co/storage/v1/object/public/avatars')
        self.assertEqual(opts['addressing_style'], 'path')
        self.assertEqual(opts['signature_version'], 's3v4')
        self.assertIs(opts['querystring_auth'], False)
        self.assertIsNone(opts['default_acl'])
        self.assertEqual(storages['staticfiles']['BACKEND'], 'whitenoise.storage.CompressedStaticFilesStorage')

    def test_geracao_url_publica_avatar_no_s3_storage(self):
        try:
            from storages.backends.s3 import S3Storage
        except ImportError:
            self.skipTest('django-storages[s3] não instalado neste ambiente.')
        storages = _configurar_storages(self.SUPABASE_COMPLETO, debug=False)
        storage = S3Storage(**storages['default']['OPTIONS'])
        self.assertEqual(
            storage.url('avatares/teste123.webp'),
            'https://projexemplo123.supabase.co/storage/v1/object/public/avatars/avatares/teste123.webp',
        )


class VercelEProducaoConfigTests(SimpleTestCase):
    def test_hosts_e_csrf_incluem_vercel_e_variaveis_da_plataforma(self):
        env = {
            'VERCEL_URL': 'brainstream-preview.vercel.app',
            'VERCEL_PROJECT_PRODUCTION_URL': 'brainstream.vercel.app',
        }
        hosts = _configurar_allowed_hosts(env, debug=False)
        origens = _configurar_csrf_trusted_origins(env, debug=False)
        self.assertIn('.vercel.app', hosts)
        self.assertIn('brainstream-preview.vercel.app', hosts)
        self.assertIn('brainstream.vercel.app', hosts)
        self.assertIn('https://*.vercel.app', origens)
        self.assertIn('https://brainstream.vercel.app', origens)

    def test_hosts_e_csrf_respeitam_variaveis_explicitas(self):
        env = {
            'DJANGO_ALLOWED_HOSTS': 'meuapp.vercel.app, localhost',
            'DJANGO_CSRF_TRUSTED_ORIGINS': 'https://meuapp.vercel.app',
        }
        self.assertEqual(_configurar_allowed_hosts(env, debug=False), ['meuapp.vercel.app', 'localhost'])
        self.assertEqual(_configurar_csrf_trusted_origins(env, debug=False), ['https://meuapp.vercel.app'])

    def test_estaticos_proxy_e_timeout_ia_configurados(self):
        self.assertTrue(settings.STATIC_ROOT)
        self.assertEqual(settings.SECURE_PROXY_SSL_HEADER, ('HTTP_X_FORWARDED_PROTO', 'https'))
        self.assertTrue(settings.USE_X_FORWARDED_HOST)
        sec_idx = settings.MIDDLEWARE.index('django.middleware.security.SecurityMiddleware')
        wn_idx = settings.MIDDLEWARE.index('whitenoise.middleware.WhiteNoiseMiddleware')
        self.assertEqual(wn_idx, sec_idx + 1)
        self.assertLessEqual(settings.AI_TIMEOUT, 60)


class OAuthHttpsEAvatarTests(SimpleTestCase):
    @override_settings(
        ALLOWED_HOSTS=['brainstream.vercel.app', 'testserver'],
        GOOGLE_CLIENT_ID='client-id-teste',
        GOOGLE_CLIENT_SECRET='client-secret-teste',
    )
    def test_google_login_gera_callback_https_com_pkce_e_state_sob_proxy_vercel(self):
        request = RequestFactory().get(
            '/accounts/google/login/',
            HTTP_HOST='brainstream.vercel.app',
            HTTP_X_FORWARDED_PROTO='https',
        )
        request.user = type('Anon', (), {'is_authenticated': False})()
        SessionMiddleware(lambda r: None).process_request(request)

        resposta = accounts_views.google_login(request)
        self.assertEqual(resposta.status_code, 302)

        partes = urlsplit(resposta['Location'])
        self.assertEqual(partes.netloc, 'accounts.google.com')
        params = parse_qs(partes.query)
        self.assertEqual(params['redirect_uri'], ['https://brainstream.vercel.app/accounts/google/callback/'])
        self.assertEqual(params['code_challenge_method'], ['S256'])
        self.assertTrue(params.get('code_challenge'))
        self.assertEqual(params['state'], [request.session['google_oauth']['state']])
        self.assertEqual(
            request.session['google_oauth']['redirect_uri'],
            'https://brainstream.vercel.app/accounts/google/callback/',
        )

    def test_processamento_avatar_preservado_webp_256_sem_exif(self):
        buf = BytesIO()
        img = Image.new('RGB', (600, 400), color=(40, 120, 200))
        exif = img.getexif()
        exif[0x010E] = 'descricao-sensivel-gps'
        img.save(buf, format='JPEG', exif=exif.tobytes())

        processado = processar_avatar(buf.getvalue())
        with Image.open(BytesIO(processado.read())) as resultado:
            self.assertEqual(resultado.format, 'WEBP')
            self.assertEqual(resultado.size, (AVATAR_TAMANHO, AVATAR_TAMANHO))
            self.assertEqual(len(resultado.getexif()), 0)
