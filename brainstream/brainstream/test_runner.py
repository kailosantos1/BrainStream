from django.conf import settings
from django.test.runner import DiscoverRunner


class SemIARealRunner(DiscoverRunner):
    """
    Desliga a IA externa durante os testes, mesmo com AI_API_KEY no .env: nenhum teste chama a API real
    por esquecimento. Testes do caminho real usam ``override_settings(AI_API_KEY=...)`` com mocks.
    """

    def setup_test_environment(self, **kwargs):
        super().setup_test_environment(**kwargs)
        settings.AI_API_KEY = ''
        settings.AI_PROVIDER = ''
        settings.AI_MODEL = ''
