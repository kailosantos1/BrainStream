from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from estudos.metricas import ranking_semanal, sequencia_de_dias
from estudos.models import SessaoEstudo, Tema


class RankingAvatarTests(TestCase):
    """O ranking semanal mostra a foto de perfil de quem tem uma e as iniciais de quem não tem."""

    def setUp(self):
        Estudante = get_user_model()
        self.eu = Estudante.objects.create_user('eu@exemplo.com', 'senha-forte-123', nome='Ana Souza')
        self.colega = Estudante.objects.create_user('colega@exemplo.com', 'senha-forte-123', nome='Bruno Lima')
        self.colega.avatar.name = 'avatares/bruno.webp'
        self.colega.save(update_fields=['avatar'])
        tema = Tema.objects.create(nome='Fotossíntese', slug='fotossintese', categoria='Biologia')
        for aluno, pontos in ((self.eu, 50), (self.colega, 80)):
            SessaoEstudo.objects.create(
                estudante=aluno, tema=tema, modo=SessaoEstudo.Modo.QUIZ,
                status=SessaoEstudo.Status.CONCLUIDA, data_fim=timezone.now(), pontuacao=pontos,
            )
        self.client.force_login(self.eu)

    def test_ranking_usa_foto_quando_existe_e_iniciais_quando_nao(self):
        resposta = self.client.get(reverse('core:painel'))
        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, self.colega.avatar.url)
        self.assertContains(resposta, 'painel-avatar painel-avatar-foto painel-avatar-sm')
        self.assertContains(resposta, '<span class="painel-avatar painel-avatar-sm" aria-hidden="true">AS</span>', html=True)


class SessaoOciosaTests(TestCase):
    def test_sessao_expira_por_inatividade_e_renova_a_cada_requisicao(self):
        self.assertEqual(settings.SESSION_COOKIE_AGE, 20 * 60)
        self.assertTrue(settings.SESSION_SAVE_EVERY_REQUEST)

        estudante = get_user_model().objects.create_user('ociosa@exemplo.com', 'senha-forte-123', nome='Carla')
        self.client.force_login(estudante)
        resposta = self.client.get(reverse('core:painel'))
        self.assertEqual(resposta.cookies[settings.SESSION_COOKIE_NAME]['max-age'], 20 * 60)

    def test_sessao_vencida_exige_novo_login(self):
        estudante = get_user_model().objects.create_user('vencida@exemplo.com', 'senha-forte-123', nome='Davi')
        self.client.force_login(estudante)
        sessao = self.client.session
        sessao.set_expiry(-1)
        sessao.save()
        resposta = self.client.get(reverse('core:painel'))
        self.assertRedirects(resposta, f"{reverse('accounts:login')}?next={reverse('core:painel')}", fetch_redirect_response=False)


class RankingConsultasTests(TestCase):
    """As sequências do top do ranking saem de uma consulta só, não uma por estudante."""

    def setUp(self):
        self.tema = Tema.objects.create(nome='Química', slug='quimica', categoria='Química')
        self.agora = timezone.now()

    def _aluno_com_sessoes(self, indice, dias_seguidos):
        aluno = get_user_model().objects.create_user(f'aluno{indice}@exemplo.com', 'senha-forte-123', nome=f'Aluno {indice}')
        for dias_atras in range(dias_seguidos):
            momento = self.agora - timedelta(days=dias_atras)
            SessaoEstudo.objects.create(
                estudante=aluno, tema=self.tema, modo=SessaoEstudo.Modo.QUIZ, status=SessaoEstudo.Status.CONCLUIDA,
                data_inicio=momento, data_fim=momento, pontuacao=10 + indice,
            )
        return aluno

    def _consultas_do_ranking(self, estudante):
        with CaptureQueriesContext(connection) as consultas:
            ranking = ranking_semanal(estudante, self.agora)
        return len(consultas), ranking

    def test_numero_de_consultas_nao_cresce_com_o_top(self):
        primeiro = self._aluno_com_sessoes(0, 1)
        com_um, _ = self._consultas_do_ranking(primeiro)
        for indice in range(1, 5):
            self._aluno_com_sessoes(indice, 1)
        com_cinco, ranking = self._consultas_do_ranking(primeiro)
        self.assertEqual(len(ranking['linhas']), 5)
        self.assertEqual(com_um, com_cinco)

    def test_sequencia_de_cada_linha_continua_correta(self):
        alunos = [self._aluno_com_sessoes(indice, dias) for indice, dias in ((1, 1), (2, 3))]
        _, ranking = self._consultas_do_ranking(alunos[0])
        sequencias = {linha['estudante'].pk: linha['sequencia'] for linha in ranking['linhas']}
        for aluno in alunos:
            self.assertEqual(sequencias[aluno.pk], sequencia_de_dias(aluno, self.agora))
        self.assertEqual(sequencias[alunos[1].pk], 3)


class RankingAoVivoTests(TestCase):
    def setUp(self):
        self.estudante = get_user_model().objects.create_user('vivo@exemplo.com', 'senha-forte-123', nome='Eva Rocha')
        tema = Tema.objects.create(nome='Física', slug='fisica', categoria='Física')
        SessaoEstudo.objects.create(
            estudante=self.estudante, tema=tema, modo=SessaoEstudo.Modo.QUIZ,
            status=SessaoEstudo.Status.CONCLUIDA, data_fim=timezone.now(), pontuacao=40,
        )

    def test_painel_aponta_para_o_ranking_ao_vivo(self):
        self.client.force_login(self.estudante)
        resposta = self.client.get(reverse('core:painel'))
        self.assertContains(resposta, f'data-ranking-url="{reverse("core:ranking")}"')

    def test_trecho_do_ranking_traz_as_linhas_sem_cache(self):
        self.client.force_login(self.estudante)
        resposta = self.client.get(reverse('core:ranking'))
        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, 'painel-ranking-row is-me')
        self.assertNotContains(resposta, '<html')
        self.assertIn('no-store', resposta['Cache-Control'])

    def test_atualizacao_automatica_nao_renova_a_sessao(self):
        self.client.force_login(self.estudante)
        resposta = self.client.get(reverse('core:ranking'))
        self.assertNotIn(settings.SESSION_COOKIE_NAME, resposta.cookies)
        resposta = self.client.get(reverse('core:painel'))
        self.assertIn(settings.SESSION_COOKIE_NAME, resposta.cookies)

    def test_sem_login_responde_401_em_vez_de_redirecionar(self):
        resposta = self.client.get(reverse('core:ranking'))
        self.assertEqual(resposta.status_code, 401)

    def test_so_aceita_get(self):
        self.client.force_login(self.estudante)
        self.assertEqual(self.client.post(reverse('core:ranking')).status_code, 405)
