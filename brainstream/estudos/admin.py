from django.contrib import admin

from .models import AfirmacaoSpeedrun, MensagemSessao, QuestaoQuiz, SessaoEstudo, Tema


@admin.register(Tema)
class TemaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'categoria', 'slug')
    list_filter = ('categoria',)
    search_fields = ('nome', 'categoria')
    prepopulated_fields = {'slug': ('categoria', 'nome')}


class MensagemSessaoInline(admin.TabularInline):
    model = MensagemSessao
    extra = 0
    fields = ('autor', 'conteudo', 'data_envio', 'tokens_utilizados')
    readonly_fields = fields
    can_delete = False


class QuestaoQuizInline(admin.TabularInline):
    model = QuestaoQuiz
    extra = 0
    fields = ('ordem', 'enunciado', 'correta', 'resposta', 'respondida_em', 'origem')
    readonly_fields = fields
    can_delete = False


class AfirmacaoSpeedrunInline(admin.TabularInline):
    model = AfirmacaoSpeedrun
    extra = 0
    fields = ('ordem', 'texto', 'verdadeira', 'resposta', 'tempo_esgotado', 'apresentada_em', 'respondida_em', 'origem')
    readonly_fields = fields
    can_delete = False


@admin.register(SessaoEstudo)
class SessaoEstudoAdmin(admin.ModelAdmin):
    inlines = (MensagemSessaoInline, QuestaoQuizInline, AfirmacaoSpeedrunInline)
    list_display = ('estudante', 'tema', 'modo', 'status', 'data_inicio', 'acertos', 'total_questoes', 'pontuacao')
    list_filter = ('modo', 'status')
    search_fields = ('estudante__email', 'estudante__nome', 'tema__nome')
    raw_id_fields = ('estudante',)
    date_hierarchy = 'data_inicio'
