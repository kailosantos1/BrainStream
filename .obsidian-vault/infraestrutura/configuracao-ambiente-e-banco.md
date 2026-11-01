# Configuração de ambiente e banco

- `settings.py` carrega `<raiz>/.env` com python-dotenv (`load_dotenv` não sobrescreve variáveis já exportadas — CI/produção vencem o arquivo).
- Driver MySQL: **PyMySQL** (puro Python, sem libs nativas no macOS), registrado via `pymysql.install_as_MySQLdb()` em `brainstream/brainstream/__init__.py`.
- `DJANGO_DEBUG` é falso por padrão; aceita `1/true/yes/on`.
- Sem `DJANGO_SECRET_KEY`: chave insegura de fallback só com DEBUG ativo; com DEBUG desligado as settings levantam `ImproperlyConfigured`.
- A suíte roda em MySQL: o usuário do `.env` precisa de permissão para criar/destruir `test_<DB_NAME>`.
- Testes de settings (`tests/test_settings.py`) importam as settings em subprocesso para testar combinações de variáveis sem afetar o processo de teste.
