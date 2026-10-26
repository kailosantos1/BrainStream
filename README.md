# BrainStream

BrainStream é um projeto acadêmico em Django para apoiar o aprendizado por meio do método socrático. A proposta inclui o tutor Enéas e três modos de estudo: Guiado, Quiz e Speedrun.

## Estado atual

Implementado:

- Projeto Django monolítico com o app `core`.
- Landing provisória na rota `/`, servida por Django Templates.
- Configuração global de templates e arquivos estáticos.
- Suíte inicial para a rota principal e configurações estáticas.

Planejado:

- Tutor Enéas, método socrático e modos Guiado, Quiz e Speedrun.
- Interfaces, autenticação, regras de negócio e integrações de IA.
- Migração futura para MySQL.

Pendente:

- Definição dos modelos, fluxos de estudo e design system.
- Configuração de produção e do banco MySQL.

## Tecnologias

- Python 3.9.6
- Django 4.2.30
- SQLite no desenvolvimento atual; MySQL está planejado para uma etapa futura.

## Estrutura

```text
brainstream/
├── brainstream/       # Configurações e URLs do projeto Django
├── core/              # App compartilhado e rota inicial
├── static/            # CSS e JavaScript globais
├── templates/         # Templates globais
├── tests/             # Testes transversais do projeto
├── manage.py
└── testar_tudo.py     # Executor central de testes
```

## Requisitos

- Python 3.9 ou compatível com Django 4.2.
- Ambiente virtual Python.

## Instalação local

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
```

O projeto ainda não lê variáveis de ambiente automaticamente; `.env.example` serve como referência para a futura configuração local e não deve conter segredos reais.

## Execução

Na pasta `brainstream/`:

```bash
python manage.py runserver
```

Abra `http://localhost:8000/`.

## Testes

Na pasta `brainstream/`, execute:

```bash
python manage.py check
python testar_tudo.py
python manage.py test
```

O executor `testar_tudo.py` delega ao runner nativo do Django, que faz a descoberta dos testes `unittest`, e executa a suíte uma única vez.
