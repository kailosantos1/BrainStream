from pathlib import Path
from html.parser import HTMLParser
from django.conf import settings
from django.contrib.staticfiles import finders
from django.test import TestCase, override_settings
from django.urls import reverse


class Elements(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.items = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        self.items.append((tag, dict(attrs)))


@override_settings(ALLOWED_HOSTS=['testserver', 'localhost'])
class LandingPageTests(TestCase):
    def test_index_renders_successfully(self):
        response = self.client.get(reverse('core:index'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'core/landing.html')

    def test_landing_order_and_dashboard(self):
        content = self.client.get('/').content.decode()
        order = ['inicio', 'como-funciona', 'modos-estudo', 'painel-evolucao', 'capacidades', 'pergunte', 'comecar']
        positions = [content.index('id="%s"' % section) for section in order]
        self.assertEqual(positions, sorted(positions))
        self.assertIn('Dados exclusivamente ilustrativos', content)
        self.assertIn('data-dashboard-demo', content)
        self.assertIn('data-dashboard-part', content)

    def test_removed_sections_and_broken_links_are_absent(self):
        content = self.client.get('/').content.decode()
        for value in ('id="recursos"', 'id="gamificacao"', 'id="para-quem"', 'href="#recursos"'):
            self.assertNotIn(value, content)

    def test_landing_assets_and_accessibility_are_present(self):
        response = self.client.get('/')
        self.assertContains(response, 'js/landing.js')
        self.assertContains(response, 'aria-label="Navegação principal"')
        self.assertContains(response, 'aria-label="Demonstração ilustrativa do painel de estudos"')
        self.assertContains(response, 'role="tablist"')  # abas da seção de modos
        self.assertContains(response, 'aria-selected="true"')

    def test_unknown_url_returns_not_found(self):
        self.assertEqual(self.client.get('/rota-inexistente/').status_code, 404)

    def test_dashboard_demo_mirrors_the_real_painel(self):
        response = self.client.get('/')
        self.assertTemplateUsed(response, 'core/dashboard_demo.html')
        content = response.content.decode()
        demo = content[content.index('id="painel-evolucao"'):content.index('id="capacidades"')]
        textos = [
            # a) tema livre com sugestões
            'Tema de estudo', 'O que você quer aprender agora?', 'Biologia: Fotossíntese', 'História', 'Física',
            # b) indicadores oficiais
            'Sessões nesta semana', '4 <small>concl.</small>', 'Taxa de acerto', '78%', 'Sequência', '4 dias',
            # c) modos reais e régua de dificuldade
            'Modo Guiado', 'Modo Quiz', 'Modo Speedrun', 'Dificuldade', 'Fácil', 'Médio', 'Difícil',
            'Iniciar sessão de estudo',
            # d) ranking semanal com o estudante em destaque
            'Ranking semanal', 'Alex', 'Sam', '1.480 pts', '1.320 pts', 'class="is-you"', '1.240 pts',
            # e) lateral com histórico e perfil
            'Histórico de estudos', 'História: 2ª Guerra Mundial', 'Meu perfil',
        ]
        for texto in textos:
            self.assertIn(texto, demo)
        # As abas fictícias do painel antigo saíram: o painel real não tem abas.
        for antigo in ('data-dashboard-tab', 'Visão geral', 'Progresso semanal', 'weekly-chart'):
            self.assertNotIn(antigo, demo)
        # Quiz com a régua visível no HTML inicial (estado final sem JS); escolhas únicas com aria-pressed.
        elements = Elements(demo).items
        modos = [attrs for tag, attrs in elements if 'data-dashboard-modo' in attrs]
        niveis = [attrs for tag, attrs in elements if 'data-dashboard-nivel' in attrs]
        self.assertEqual([m['data-dashboard-modo'] for m in modos if m['aria-pressed'] == 'true'], ['quiz'])
        self.assertEqual(sum(n['aria-pressed'] == 'true' for n in niveis), 1)
        self.assertTrue(all(attrs['type'] == 'button' for attrs in modos + niveis))
        for tag, attrs in elements:
            if 'data-dashboard-demo' in attrs or 'data-dashboard-dificuldade' in attrs:
                self.assertNotIn('hidden', attrs)
                self.assertNotEqual(attrs.get('aria-hidden'), 'true')

    def test_landing_modes_match_the_real_study_modes(self):
        content = self.client.get('/').content.decode()
        self.assertIn('Questão 3 de 5', content)
        self.assertNotIn('Questão 3 de 10', content)
        self.assertIn('data-speed-clock>0:10<', content)
        self.assertIn('Pontos: <span class="app-mono" data-speed-score>0</span>', content)
        # O Enéas fala com o avatar vetorial no hero, no Modo Guiado e na demonstração de pergunta.
        self.assertEqual(content.count('<img src="/static/img/eneas.svg" alt="Enéas" width="28" height="28">'), 4)
        self.assertNotIn('<span class="avatar" aria-hidden="true">E</span>', content)

    def test_all_landing_links_resolve(self):
        elements = Elements(self.client.get('/').content.decode()).items
        ids = {attrs['id'] for tag, attrs in elements if 'id' in attrs}
        for tag, attrs in elements:
            if tag != 'a':
                continue
            href = attrs['href']
            if href.startswith('#'):
                self.assertIn(href[1:], ids)
            else:
                self.assertEqual(self.client.get(href).status_code, 200)

    def test_single_h1_names_the_product(self):
        elements = Elements(self.client.get('/').content.decode()).items
        self.assertEqual([tag for tag, attrs in elements].count('h1'), 1)
        self.assertContains(self.client.get('/'), 'Tutor de estudos com IA que guia seu raciocínio com perguntas.')

    def test_ask_demo_is_labelled_and_works_without_javascript(self):
        response = self.client.get('/')
        elements = Elements(response.content.decode()).items
        inputs = [attrs for tag, attrs in elements if 'data-ask-input' in attrs]
        self.assertEqual(len(inputs), 1)
        field = inputs[0]
        labels = [attrs for tag, attrs in elements if tag == 'label' and attrs.get('for') == field['id']]
        self.assertEqual(len(labels), 1)
        self.assertEqual(field['maxlength'], '80')
        self.assertIn(field['aria-describedby'], {attrs['id'] for tag, attrs in elements if 'id' in attrs})
        replies = [attrs for tag, attrs in elements if 'data-ask-reply' in attrs]
        self.assertEqual(replies[0].get('aria-live'), 'polite')
        # Sem JS, pergunta e resposta iniciais já estão na conversa; o campo começa vazio.
        self.assertContains(response, 'data-ask-question>Por que o céu é azul?</p>')
        self.assertNotIn('value', field)
        self.assertContains(response, 'o que você acha que acontece com as cores')
        self.assertContains(response, 'Demonstração com respostas pré-escritas')
        examples = [attrs for tag, attrs in elements if 'data-ask-example' in attrs]
        self.assertEqual(len(examples), 3)
        for example in examples:
            self.assertEqual(example['type'], 'button')

    def test_mode_tabs_are_accessible_and_open_without_javascript(self):
        elements = Elements(self.client.get('/').content.decode()).items
        ids = {attrs['id'] for tag, attrs in elements if 'id' in attrs}
        tabs = [attrs for tag, attrs in elements if 'data-seg-tab' in attrs]
        panels = [attrs for tag, attrs in elements if 'data-seg-panel' in attrs]
        self.assertEqual([tab['id'] for tab in tabs], ['tab-guiado', 'tab-quiz', 'tab-speedrun'])
        self.assertEqual(len(panels), 3)
        self.assertEqual([tab['aria-selected'] for tab in tabs], ['true', 'false', 'false'])
        for tab, panel in zip(tabs, panels):
            self.assertEqual(tab['role'], 'tab')
            self.assertEqual(tab['type'], 'button')
            self.assertEqual(tab['aria-controls'], panel['id'])
            self.assertEqual(panel['role'], 'tabpanel')
            self.assertEqual(panel['aria-labelledby'], tab['id'])
            self.assertIn(tab['aria-controls'], ids)
            # Sem JS os três modos ficam visíveis em sequência.
            self.assertNotIn('hidden', panel)
        options = [attrs for tag, attrs in elements if 'data-quiz-option' in attrs]
        self.assertEqual(len(options), 4)
        self.assertEqual(len([option for option in options if 'data-correct' in option]), 1)
        self.assertTrue(all(option['type'] == 'button' for option in options))

    def test_tour_steps_control_the_product_window(self):
        response = self.client.get('/')
        elements = Elements(response.content.decode()).items
        steps = [attrs for tag, attrs in elements if 'data-tour-step' in attrs]
        self.assertEqual([step['data-tour-step'] for step in steps], ['1', '2', '3', '4'])
        for step in steps:
            self.assertEqual(step['type'], 'button')
            self.assertEqual(step['aria-controls'], 'tour-window')
        window = [attrs for tag, attrs in elements if attrs.get('id') == 'tour-window'][0]
        # Sem JS a janela não tem estado: a conversa aparece completa.
        self.assertNotIn('data-state', window)
        for text in ('Você pergunta', 'O Enéas responde com uma pergunta',
                     'Você raciocina e recebe uma dica', 'Seu insight vira progresso',
                     'Dica do Enéas', 'Conceito entendido'):
            self.assertContains(response, text)

    def test_product_is_shown_as_html_not_images(self):
        content = self.client.get('/').content.decode()
        elements = Elements(content).items
        # Nada de capturas de tela: a única imagem é o avatar vetorial do Enéas nos balões.
        imagens = {attrs['src'] for tag, attrs in elements if tag == 'img'}
        self.assertEqual(imagens, {'/static/img/eneas.svg'})
        self.assertGreaterEqual(len([attrs for tag, attrs in elements if 'app-window' in attrs.get('class', '')]), 5)
        self.assertGreaterEqual(content.count('Dados ilustrativos'), 2)
        self.assertIn('Dados exclusivamente ilustrativos', content)

    def test_illustrative_data_is_consistent_across_sections(self):
        content = self.client.get('/').content.decode()
        # Sequência, acerto, sessões e meta semanal são os mesmos em todas as interfaces.
        self.assertGreaterEqual(content.count('>4 dias<'), 4)
        self.assertGreaterEqual(content.count('78%'), 4)
        self.assertGreaterEqual(content.count('>12<'), 3)
        self.assertGreaterEqual(content.count('65%'), 3)
        self.assertNotIn('5 dias', content)

    def test_page_loads_no_external_assets(self):
        elements = Elements(self.client.get('/').content.decode()).items
        for tag, attrs in elements:
            for key in ('src', 'href'):
                value = attrs.get(key, '')
                if tag in ('link', 'script', 'img'):
                    self.assertFalse(value.startswith(('http:', 'https:', '//')), value)


class StaticFilesConfigurationTests(TestCase):
    def test_static_files_are_available(self):
        self.assertEqual(settings.STATIC_URL, '/static/')
        self.assertIn(Path(settings.BASE_DIR) / 'static', settings.STATICFILES_DIRS)
        for asset in ('css/base.css', 'css/product-ui.css', 'css/landing.css', 'js/base.js', 'js/landing.js', 'vendor/bootstrap/css/bootstrap.min.css'):
            self.assertIsNotNone(finders.find(asset), asset)

    def test_fonts_are_vendored_with_licenses(self):
        for font in ('hanken-grotesk/hanken-grotesk-latin-var.woff2', 'hanken-grotesk/OFL.txt'):
            self.assertIsNotNone(finders.find('vendor/fonts/' + font), font)
        # A Fraunces saiu com a direção editorial; só a Hanken Grotesk é usada.
        self.assertIsNone(finders.find('vendor/fonts/fraunces/fraunces-latin-var.woff2'))
        css = Path(finders.find('css/base.css')).read_text(encoding='utf-8')
        self.assertNotIn('Fraunces', css)
        self.assertNotIn('fonts.googleapis', css)
        self.assertNotIn('fontshare', css)


@override_settings(ALLOWED_HOSTS=['testserver', 'localhost'], DEBUG=False)
class PaginasDeErroTests(TestCase):
    def test_rota_inexistente_renderiza_404_personalizado(self):
        response = self.client.get('/caminho-que-nao-existe/')
        self.assertEqual(response.status_code, 404)
        self.assertTemplateUsed(response, '404.html')
        self.assertContains(response, 'Página não encontrada', status_code=404)
        self.assertContains(response, 'Só sei que nada sei', status_code=404)
        self.assertContains(response, 'bi-compass', status_code=404)
        self.assertContains(response, 'href="%s"' % reverse('core:index'), status_code=404)
        self.assertNotContains(response, 'href="%s"' % reverse('core:painel'), status_code=404)

    def test_404_autenticado_leva_ao_painel(self):
        from django.contrib.auth import get_user_model
        estudante = get_user_model().objects.create_user(email='ana@email.com', password='Senha-forte-123', nome='Ana')
        self.client.force_login(estudante)
        response = self.client.get('/caminho-que-nao-existe/')
        self.assertEqual(response.status_code, 404)
        self.assertContains(response, 'href="%s"' % reverse('core:painel'), status_code=404)
        self.assertContains(response, 'Painel de Estudos', status_code=404)

    def test_500_renderiza_sem_request_nem_banco(self):
        from django.test import RequestFactory
        from django.views.defaults import server_error
        # O handler do Django renderiza sem contexto de request; o template não pode consultar o banco.
        with self.assertNumQueries(0):
            response = server_error(RequestFactory().get('/qualquer/'))
        self.assertEqual(response.status_code, 500)
        content = response.content.decode()
        self.assertIn('Algo inesperado aconteceu', content)
        self.assertIn('bi-exclamation-triangle', content)
        self.assertIn('tente recarregar a página', content)
        self.assertIn('href="/"', content)
        self.assertIsNotNone(finders.find('css/erro.css'))
        self.assertIn('/static/css/erro.css', content)
        for tag, attrs in Elements(content).items:
            if tag in ('link', 'script'):
                self.assertFalse(attrs.get('href', attrs.get('src', '')).startswith(('http:', 'https:', '//')))


@override_settings(ALLOWED_HOSTS=['testserver', 'localhost'])
class LogoEFaviconTests(TestCase):
    def test_logo_leads_to_landing_or_to_painel_when_logged_in(self):
        from django.contrib.auth import get_user_model
        pagina = self.client.get(reverse('core:index'))
        self.assertContains(pagina, '<a class="navbar-brand" href="%s">' % reverse('core:index'), html=False)
        estudante = get_user_model().objects.create_user(email='ana@email.com', password='Senha-forte-123', nome='Ana')
        self.client.force_login(estudante)
        pagina = self.client.get(reverse('core:index'))
        self.assertContains(pagina, '<a class="navbar-brand" href="%s">' % reverse('core:painel'), html=False)
        painel = self.client.get(reverse('core:painel'))
        self.assertContains(painel, '<a class="painel-brand" href="%s">' % reverse('core:painel'), html=False)

    def test_svg_favicon_and_eneas_avatar_are_served_locally(self):
        pagina = self.client.get(reverse('core:index'))
        self.assertContains(pagina, '<link rel="icon" href="/static/img/favicon.svg" type="image/svg+xml">', html=False)
        for nome in ('img/favicon.svg', 'img/eneas.svg'):
            caminho = finders.find(nome)
            self.assertIsNotNone(caminho, nome)
            svg = Path(caminho).read_text(encoding='utf-8')
            self.assertTrue(svg.startswith('<svg xmlns="http://www.w3.org/2000/svg"'), nome)
            self.assertNotIn('<script', svg)
            self.assertNotIn('href="http', svg)
