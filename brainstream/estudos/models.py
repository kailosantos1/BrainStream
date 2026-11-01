from django.conf import settings
from django.db import IntegrityError, models, transaction
from django.utils import timezone
from django.utils.text import slugify

CATEGORIA_GERAL = 'Geral'


def normalizar_nome_tema(nome):
    """Remove espaços extras para que "  fotossíntese " e "Fotossíntese" caiam no mesmo tema."""
    return ' '.join(nome.split())


class TemaManager(models.Manager):
    def resolver(self, nome):
        """Devolve o tema com esse nome (sem diferenciar maiúsculas) ou cria um novo em 'Geral'."""
        nome = normalizar_nome_tema(nome)
        existente = self.filter(nome__iexact=nome).order_by('pk').first()
        if existente:
            return existente
        base = slugify(nome)[:130] or 'tema'
        slug, sufixo = base, 2
        # Nomes diferentes podem gerar o mesmo slug (ex.: "C" e "C++"); o sufixo evita reaproveitar o tema errado.
        while self.filter(slug=slug).exists():
            slug, sufixo = f'{base}-{sufixo}', sufixo + 1
        try:
            with transaction.atomic():
                tema, _ = self.get_or_create(nome=nome, defaults={'slug': slug, 'categoria': CATEGORIA_GERAL})
                return tema
        except IntegrityError:
            # Outra requisição criou o mesmo tema entre a busca e o insert.
            return self.filter(nome__iexact=nome).order_by('pk').first() or self.get(slug=slug)


class Tema(models.Model):
    nome = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True)
    categoria = models.CharField(max_length=60)
    descricao = models.TextField('descrição', blank=True)

    objects = TemaManager()

    class Meta:
        ordering = ('categoria', 'nome')

    def __str__(self):
        if self.categoria == CATEGORIA_GERAL:
            return self.nome
        return f'{self.categoria}: {self.nome}'


class SessaoEstudo(models.Model):
    class Modo(models.TextChoices):
        GUIADO = 'guiado', 'Guiado'
        QUIZ = 'quiz', 'Quiz'
        SPEEDRUN = 'speedrun', 'Speedrun'

    class Status(models.TextChoices):
        EM_ANDAMENTO = 'em_andamento', 'Em progresso'
        CONCLUIDA = 'concluida', 'Concluído'
        REVISAR = 'revisar', 'Revisar'

    class Dificuldade(models.TextChoices):
        FACIL = 'facil', 'Fácil'
        MEDIO = 'medio', 'Médio'
        DIFICIL = 'dificil', 'Difícil'

    estudante = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sessoes')
    tema = models.ForeignKey(Tema, on_delete=models.PROTECT, related_name='sessoes')
    modo = models.CharField(max_length=10, choices=Modo.choices)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.EM_ANDAMENTO)
    # Calibra as questões do Quiz e as afirmações do Speedrun geradas pela IA; o Modo Guiado não usa.
    dificuldade = models.CharField(max_length=7, choices=Dificuldade.choices, default=Dificuldade.MEDIO)
    # "Excluir do histórico" só esconde a sessão: pontos, ranking e métricas continuam contando com ela.
    visivel_no_historico = models.BooleanField('visível no histórico', default=True, db_index=True)
    data_inicio = models.DateTimeField('início', default=timezone.now)
    data_fim = models.DateTimeField('fim', null=True, blank=True)
    # Resultado preenchido pelos modos Quiz/Speedrun ao finalizar; base da taxa de acerto e do ranking.
    acertos = models.PositiveSmallIntegerField(default=0)
    total_questoes = models.PositiveSmallIntegerField('total de questões', default=0)
    pontuacao = models.PositiveIntegerField('pontuação', default=0)

    class Meta:
        verbose_name = 'sessão de estudo'
        verbose_name_plural = 'sessões de estudo'
        ordering = ('-data_inicio',)
        indexes = [
            models.Index(fields=('estudante', '-data_inicio')),
            models.Index(fields=('status', 'data_fim')),
        ]
        constraints = [
            models.CheckConstraint(check=models.Q(acertos__lte=models.F('total_questoes')), name='sessao_acertos_lte_total'),
        ]

    def __str__(self):
        return f'{self.tema} ({self.get_modo_display()})'

    def finalizar(self, *, acertos=0, total_questoes=0, pontuacao=0, status=Status.CONCLUIDA, quando=None):
        self.acertos = acertos
        self.total_questoes = total_questoes
        self.pontuacao = pontuacao
        self.status = status
        self.data_fim = quando or timezone.now()
        self.save(update_fields=['acertos', 'total_questoes', 'pontuacao', 'status', 'data_fim'])

    @property
    def taxa_acerto(self):
        if not self.total_questoes:
            return None
        return round(100 * self.acertos / self.total_questoes)


LETRAS = ('A', 'B', 'C', 'D')


class QuestaoQuiz(models.Model):
    """Questão de múltipla escolha do Modo Quiz; a letra correta só sai do servidor depois da resposta."""

    class Origem(models.TextChoices):
        IA = 'ia', 'Gerada por IA'
        SIMULADA = 'simulada', 'Simulada'

    sessao = models.ForeignKey(SessaoEstudo, on_delete=models.CASCADE, related_name='questoes')
    ordem = models.PositiveSmallIntegerField()
    enunciado = models.TextField()
    alternativa_a = models.CharField(max_length=255)
    alternativa_b = models.CharField(max_length=255)
    alternativa_c = models.CharField(max_length=255)
    alternativa_d = models.CharField(max_length=255)
    correta = models.CharField(max_length=1, choices=[(letra, letra) for letra in LETRAS])
    explicacao = models.TextField('explicação')
    resposta = models.CharField(max_length=1, blank=True, default='')
    respondida_em = models.DateTimeField(null=True, blank=True)
    origem = models.CharField(max_length=10, choices=Origem.choices, default=Origem.IA)
    criada_em = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = 'questão do quiz'
        verbose_name_plural = 'questões do quiz'
        ordering = ('sessao', 'ordem')
        constraints = [
            models.UniqueConstraint(fields=('sessao', 'ordem'), name='quiz_ordem_unica_por_sessao'),
            models.CheckConstraint(check=models.Q(correta__in=LETRAS), name='quiz_correta_valida'),
            models.CheckConstraint(check=models.Q(resposta__in=('',) + LETRAS), name='quiz_resposta_valida'),
        ]

    def __str__(self):
        return f'Questão {self.ordem}: {self.enunciado[:40]}'

    @property
    def alternativas(self):
        return [(letra, getattr(self, f'alternativa_{letra.lower()}')) for letra in LETRAS]

    def texto_da(self, letra):
        return getattr(self, f'alternativa_{letra.lower()}')

    @property
    def texto_resposta(self):
        return self.texto_da(self.resposta) if self.resposta else ''

    @property
    def texto_correta(self):
        return self.texto_da(self.correta)

    @property
    def respondida(self):
        return bool(self.resposta)

    @property
    def acertou(self):
        return self.resposta == self.correta


class AfirmacaoSpeedrun(models.Model):
    """
    Afirmação de Verdadeiro ou Falso do Modo Speedrun. O gabarito só sai do servidor depois da resposta,
    e o prazo é medido no servidor a partir de ``apresentada_em`` (o relógio da tela é só visual).
    """

    Origem = QuestaoQuiz.Origem

    sessao = models.ForeignKey(SessaoEstudo, on_delete=models.CASCADE, related_name='afirmacoes')
    ordem = models.PositiveSmallIntegerField()
    texto = models.CharField(max_length=300)
    verdadeira = models.BooleanField()
    justificativa = models.TextField()
    # None = sem resposta válida (ainda não respondida ou tempo esgotado).
    resposta = models.BooleanField(null=True, blank=True)
    tempo_esgotado = models.BooleanField(default=False)
    apresentada_em = models.DateTimeField(null=True, blank=True)
    respondida_em = models.DateTimeField(null=True, blank=True)
    origem = models.CharField(max_length=10, choices=QuestaoQuiz.Origem.choices, default=QuestaoQuiz.Origem.IA)
    criada_em = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = 'afirmação do speedrun'
        verbose_name_plural = 'afirmações do speedrun'
        ordering = ('sessao', 'ordem')
        constraints = [
            models.UniqueConstraint(fields=('sessao', 'ordem'), name='speedrun_ordem_unica_por_sessao'),
        ]

    def __str__(self):
        return f'Afirmação {self.ordem}: {self.texto[:40]}'

    @property
    def respondida(self):
        return self.respondida_em is not None

    @property
    def acertou(self):
        return self.respondida and not self.tempo_esgotado and self.resposta == self.verdadeira

    @property
    def gabarito(self):
        return 'Verdadeiro' if self.verdadeira else 'Falso'

    @property
    def segundos(self):
        """Tempo gasto na afirmação, em segundos (nulo enquanto não respondida)."""
        if not (self.respondida and self.apresentada_em):
            return None
        return max((self.respondida_em - self.apresentada_em).total_seconds(), 0)


ABERTURA_MODO_GUIADO = (
    'Olá! Vou te guiar na exploração de {tema} por meio de perguntas que estimulam seu raciocínio '
    '— em vez de dar respostas prontas. Vamos construir o entendimento juntos.\n\n'
    'Para começarmos: o que você já sabe sobre esse tema? Tente descrever com suas próprias palavras.'
)


class MensagemSessao(models.Model):
    class Autor(models.TextChoices):
        ESTUDANTE = 'estudante', 'Estudante'
        ENEAS = 'eneas', 'Enéas'
        # Respostas do context locking e avisos de falha: nunca vêm da LLM.
        SISTEMA = 'sistema', 'Sistema'

    sessao = models.ForeignKey(SessaoEstudo, on_delete=models.CASCADE, related_name='mensagens')
    autor = models.CharField(max_length=10, choices=Autor.choices)
    conteudo = models.TextField('conteúdo')
    data_envio = models.DateTimeField('enviada em', default=timezone.now)
    tokens_utilizados = models.PositiveIntegerField('tokens utilizados', default=0)

    class Meta:
        verbose_name = 'mensagem da sessão'
        verbose_name_plural = 'mensagens da sessão'
        ordering = ('data_envio', 'pk')
        indexes = [models.Index(fields=('sessao', 'data_envio'))]

    def __str__(self):
        return f'{self.get_autor_display()}: {self.conteudo[:40]}'

    @classmethod
    def abrir_modo_guiado(cls, sessao):
        return cls.objects.create(
            sessao=sessao, autor=cls.Autor.ENEAS, conteudo=ABERTURA_MODO_GUIADO.format(tema=sessao.tema.nome),
        )
