from pathlib import Path

from django.conf import settings
from django.test import TestCase, override_settings
from django.urls import reverse


@override_settings(ALLOWED_HOSTS=['testserver', 'localhost'])
class LandingPageTests(TestCase):
    def test_index_url_resolves_and_returns_success(self):
        response = self.client.get(reverse('core:index'))

        self.assertEqual(response.status_code, 200)

    def test_index_uses_expected_templates_and_content(self):
        response = self.client.get('/')

        self.assertTemplateUsed(response, 'core/landing.html')
        self.assertTemplateUsed(response, 'base.html')
        self.assertContains(response, 'BrainStream')

    def test_unknown_url_returns_not_found(self):
        response = self.client.get('/rota-inexistente/')

        self.assertEqual(response.status_code, 404)


class StaticFilesConfigurationTests(TestCase):
    def test_global_static_directory_is_configured(self):
        self.assertEqual(settings.STATIC_URL, '/static/')
        self.assertIn(Path(settings.BASE_DIR) / 'static', settings.STATICFILES_DIRS)
