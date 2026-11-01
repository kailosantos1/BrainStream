from django import forms
from django.db import transaction
from django.db.models import Count

from .models import CATEGORIA_GERAL, MensagemSessao, SessaoEstudo, Tema, normalizar_nome_tema

LIMITE_SUGESTOES = 6


class IniciarSessaoForm(forms.Form):
    tema = forms.CharField(
        label='Tema de estudo',
        min_length=2,
        max_length=Tema._meta.get_field('nome').max_length,
        error_messages={
            'required': 'Digite um tema para começar.',
            'min_length': 'Digite um tema com pelo menos %(limit_value)d letras.',
            'max_length': 'Use até %(limit_value)d caracteres para o tema.',
        },
    )
    modo = forms.ChoiceField(
        label='Modo de estudo',
        choices=SessaoEstudo.Modo.choices,
        initial=SessaoEstudo.Modo.GUIADO,
        widget=forms.RadioSelect,
        error_messages={'required': 'Escolha um modo de estudo.', 'invalid_choice': 'Escolha um dos três modos.'},
    )
    # Só vale para Quiz e Speedrun; sem escolha (ou no Modo Guiado), fica no nível médio.
    dificuldade = forms.ChoiceField(
        label='Dificuldade',
        choices=SessaoEstudo.Dificuldade.choices,
        initial=SessaoEstudo.Dificuldade.MEDIO,
        required=False,
        widget=forms.RadioSelect,
        error_messages={'invalid_choice': 'Escolha Fácil, Médio ou Difícil.'},
    )

    def clean_tema(self):
        return normalizar_nome_tema(self.cleaned_data['tema'])

    def clean(self):
        dados = super().clean()
        if not dados.get('dificuldade') or dados.get('modo') == SessaoEstudo.Modo.GUIADO:
            dados['dificuldade'] = SessaoEstudo.Dificuldade.MEDIO
        return dados

    @transaction.atomic
    def save(self, estudante):
        tema = Tema.objects.resolver(self.cleaned_data['tema'])
        sessao = SessaoEstudo.objects.create(
            estudante=estudante, tema=tema, modo=self.cleaned_data['modo'], dificuldade=self.cleaned_data['dificuldade'])
        if sessao.modo == SessaoEstudo.Modo.GUIADO:
            MensagemSessao.abrir_modo_guiado(sessao)
        return sessao

    @staticmethod
    def sugestoes():
        """Temas curados mais estudados; temas digitados por estudantes ('Geral') não viram sugestão pública."""
        return list(
            Tema.objects.exclude(categoria=CATEGORIA_GERAL)
            .annotate(total_sessoes=Count('sessoes'))
            .order_by('-total_sessoes', 'nome')
            .values_list('nome', flat=True)[:LIMITE_SUGESTOES]
        )


class MensagemForm(forms.Form):
    conteudo = forms.CharField(
        label='Sua resposta',
        max_length=1500,
        strip=True,
        error_messages={
            'required': 'Escreva sua resposta antes de enviar.',
            'max_length': 'Use até %(limit_value)d caracteres por mensagem.',
        },
    )
