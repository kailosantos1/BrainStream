from django.db import migrations
from django.utils.text import slugify

TEMAS = [
    ('Biologia', 'Fotossíntese', 'Como plantas transformam luz em energia química.'),
    ('Biologia', 'Divisão celular', 'Mitose, meiose e o ciclo celular.'),
    ('Física', 'Termodinâmica', 'Calor, trabalho e as leis da termodinâmica.'),
    ('Física', 'Leis de Newton', 'Força, massa e movimento.'),
    ('Geografia', 'Clima e vegetação do Brasil', 'Biomas e fatores climáticos brasileiros.'),
    ('História', '2ª Guerra Mundial', 'Causas, fases e consequências do conflito.'),
    ('História', 'Revolução Industrial', 'Transformações técnicas, sociais e econômicas.'),
    ('Matemática', 'Funções do 2º grau', 'Parábolas, raízes e vértice.'),
    ('Matemática', 'Probabilidade', 'Eventos, espaço amostral e combinatória básica.'),
    ('Português', 'Análise sintática', 'Termos da oração e período composto.'),
    ('Química', 'Ligações iônicas', 'Transferência de elétrons e compostos iônicos.'),
    ('Química', 'Estequiometria', 'Proporções e cálculos em reações químicas.'),
]


def criar_temas(apps, schema_editor):
    Tema = apps.get_model('estudos', 'Tema')
    for categoria, nome, descricao in TEMAS:
        Tema.objects.get_or_create(
            slug=slugify(f'{categoria} {nome}'),
            defaults={'categoria': categoria, 'nome': nome, 'descricao': descricao},
        )


def remover_temas(apps, schema_editor):
    Tema = apps.get_model('estudos', 'Tema')
    Tema.objects.filter(slug__in=[slugify(f'{c} {n}') for c, n, _ in TEMAS], sessoes__isnull=True).delete()


class Migration(migrations.Migration):
    dependencies = [('estudos', '0001_initial')]
    operations = [migrations.RunPython(criar_temas, remover_temas)]
