# BrainStream

BrainStream é um projeto acadêmico em Django para apoiar o aprendizado por meio do método socrático. A proposta inclui o tutor Enéas e três modos de estudo: Guiado, Quiz e Speedrun.

## Estado atual

Implementado:

- Projeto Django monolítico com os apps `core`, `accounts` e `estudos`.
- Painel do estudante em `/painel/` (Figura 8): histórico de sessões e perfil na lateral (gaveta no celular), tema em texto livre (qualquer matéria, com sugestões rápidas opcionais), três modos (Guiado, Quiz, Speedrun) e início de sessão, indicadores de sessões concluídas na semana, taxa de acerto e sequência de dias, e ranking semanal com a posição do estudante destacada. Dados reais do banco, com estados vazios para contas novas.
- Modo Guiado em `/estudo/<id>/` (Figura 9): ao iniciar uma sessão guiada pelo painel, o estudante vai direto para a conversa com o Enéas, que abre com uma mensagem contextualizada pelo tema. Lateral recolhível com "Voltar ao Painel" e histórico, balões do Enéas à esquerda e do estudante à direita, envio por POST tradicional ou `fetch` (Enter envia, Shift+Enter quebra linha) e rolagem automática até a última mensagem. Cada estudante só acessa as próprias sessões (outras dão 404). Pontuação antifarme: cada resposta legítima (não bloqueada, com 3+ palavras e sem repetir uma anterior) vale 5 pontos, até 30; o botão "Concluir Estudo" exige 3 respostas legítimas, pede ao Enéas uma síntese do que o próprio estudante descobriu, soma 10 de bônus e conclui a sessão (que então entra no ranking). Enquanto o Enéas responde, o feed mostra três pontos animados (com "Enéas digitando…" para leitores de tela) e o campo fica travado.
- Modo Quiz em `/estudo/quiz/<id>/` (Figura 10): 5 questões de múltipla escolha geradas pelo Gemini em JSON estruturado (banco simulado por tema quando não há IA ou a geração falha, com aviso "Questões simuladas"). Cada clique é validado no servidor, que só revela a correta e a explicação depois da resposta; feedback imediato ("Correto! +10 pontos" ou a alternativa certa com explicação), próxima questão logo abaixo, pontos atualizados no topo e card final com "Voltar ao Painel". Ao responder a 5ª, a sessão é finalizada com acertos e pontos, que entram no ranking e nos indicadores do painel. Funciona com e sem JavaScript.
- Modo Speedrun em `/estudo/speedrun/<id>/` (Figura 11): 5 afirmações de Verdadeiro ou Falso geradas pelo Gemini (ou banco simulado, com aviso "Afirmações simuladas"), 10 segundos cada. Começa por um card de preparação com as regras e o botão "Iniciar Speedrun": o prazo da 1ª afirmação só é registrado no clique. Efeitos sonoros sintetizados com a Web Audio API (acerto, erro e cliques nos últimos 3 s), com botão para silenciar salvo no navegador, e vibração no celular. Faixa "Tempo restante" com contagem regressiva; ao zerar, a página envia "tempo esgotado". O prazo também é conferido no servidor (com 2 s de tolerância de rede), então respostas atrasadas não pontuam nem sem JavaScript. Feedback imediato ("Correto! +10 pontos", "Incorreto. Era Verdadeiro/Falso" ou "Tempo esgotado") com justificativa, botões largos Verdadeiro/Falso (atalhos V e F no teclado) e tela final com acertos, pontos e tempo total.
- Context locking (`estudos/services/context_locking.py`): pré-filtro sem IA que intercepta ofensas, desvios não acadêmicos, tentativas de mudar as regras do tutor e pedidos de resposta pronta, respondendo com orientação educativa; e o prompt de sistema socrático do Enéas (Overholser, 1992).
- Serviço de IA (`estudos/services/tutor.py`): Google Gemini (SDK `google-genai`) ou Claude API (SDK `anthropic`), escolhido por `AI_PROVIDER` ou pelo formato da chave (`AIza...` = Gemini), com modelo em `AI_MODEL` (padrões: `gemini-3.5-flash-lite` e `claude-opus-5-5`). Sem chave, um tutor simulado devolve perguntas socráticas fixas (a interface mostra "Tutor simulado"). As chamadas ao Gemini pedem o raciocínio mínimo do modelo (`thinkingLevel: minimal` na família Gemini 3, que recusa `thinking_budget=0`), para respostas em cerca de 1 s. Com Gemini e `AI_SEARCH=True` (padrão), o Enéas usa a busca do Google (grounding) só quando o tema ou a mensagem pedem fatos atuais (ex.: "dados recentes", "atualmente", um ano como 2026); `AI_SEARCH=False` desliga a busca; as consultas feitas pelo modelo vão para o log, e, se o plano da chave recusar a busca, ele responde sem ela e pausa a busca por 10 minutos.
- Estudos (`estudos`): modelos `Tema` (12 temas curados via migração de dados; temas digitados são criados sob demanda em "Geral"), `SessaoEstudo` (com `dificuldade` fácil/médio/difícil, usada para calibrar as questões do Quiz e as afirmações do Speedrun) e `MensagemSessao` (autor, conteúdo, data e tokens); métricas e ranking em `estudos/metricas.py`.
- Meu Perfil em `/perfil/` (acesso pelo rodapé da lateral do painel e das telas de estudo): aba "Dados da Conta" com nome, e-mail (somente leitura), foto de perfil opcional (JPG/PNG/WebP até 2 MB, recortada em 256 px, gravada em WebP sem metadados EXIF) e troca de senha com confirmação da senha atual; aba "Desempenho" com sessões concluídas, tempo de estudo, taxa de acerto geral e por modo, pontos, melhor posição já alcançada no ranking semanal e aproveitamento por matéria. Sem foto, aparecem as iniciais.
- Contas (`accounts`): usuário customizado `Estudante` (login por e-mail único, nome completo), rotas `/cadastro/`, `/login/`, `/logout/` (POST) e recuperação de senha por e-mail (`/recuperar-senha/`), com telas das Figuras 6 e 7 na identidade da landing. Após entrar, o estudante vai para `/painel/`. "Continuar com Google" usa OAuth 2.0 (OpenID Connect, com PKCE e `state` de uso único): entra numa conta existente pelo e-mail verificado pelo Google ou cria uma nova, sem senha, aproveitando nome e foto. Sem `GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET`, o botão avisa que o login com Google não está configurado.
- Landing na rota `/`, com o produto como vitrine: hero com a janela do Enéas em profundidade, tour fixo "Como o Enéas ensina" (4 etapas), modos Guiado/Quiz/Speedrun interativos, painel de evolução, bento com fragmentos de interface, demonstração "Pergunte ao Enéas" (respostas pré-escritas, sem IA real) e CTA. Todas as interfaces são HTML/CSS com dados ilustrativos rotulados e coerentes entre si. Todo o conteúdo é legível sem JavaScript e com movimento reduzido.
- Páginas de erro personalizadas `templates/404.html` (estende `base.html`; leva ao painel se o estudante estiver logado, senão ao início) e `templates/500.html` (HTML independente, sem request, context processors nem banco), com estilos em `static/css/erro.css`. Só aparecem com `DJANGO_DEBUG` desativado.
- Painel: régua de dificuldade (Fácil, Médio, Difícil) que aparece ao escolher Quiz ou Speedrun; exclusão de sessões do histórico (lixeira com confirmação, `POST /estudo/<id>/excluir/`, só do próprio estudante): a sessão sai do histórico e a página dela passa a dar 404, mas os pontos continuam no total, no ranking e nas métricas (exclusão lógica por `visivel_no_historico`).
- Identidade: favicon SVG (também usado como marca) e avatar vetorial do Enéas nos balões do Guiado, Quiz e Speedrun; a marca leva o estudante logado ao painel.
- Carregamento ao iniciar uma sessão: o botão do painel trava com spinner e a mensagem do modo, e, se a página seguinte (com as questões geradas pela IA) demorar mais de 500 ms, entra uma camada com a marca do BrainStream pulsando.
- Configuração global de templates e arquivos estáticos.
- Suíte inicial para a rota principal e configurações estáticas.
- Design system com tema escuro padrão, tema claro alternativo, navbar e footer reutilizáveis; tokens em `static/css/base.css`.
- Sistema de janela do produto reutilizável (`.app-window` e primitivas de chat, métricas, barras e alternativas) em `static/css/product-ui.css`.
- Bootstrap 5.3.8, Bootstrap Icons 1.13.1 e a fonte Hanken Grotesk (SIL OFL) disponibilizados localmente em `static/vendor/`.

Planejado:

- Exibir as sugestões e fontes da busca do Google junto às respostas do Enéas.

Pendente:

- Configuração de produção (hosts, HTTPS, cookies seguros e servir `/media/` pelo servidor web).

## Tecnologias

- Python 3.9.6
- Django 4.2.30
- Django Templates
- Bootstrap 5 e Bootstrap Icons
- CSS3 personalizado e JavaScript Vanilla
- Pillow para as fotos de perfil (uploads em `MEDIA_ROOT`, servidos pelo Django só com `DEBUG=True`).
- MySQL via PyMySQL; credenciais e `SECRET_KEY` carregadas do `.env` da raiz com python-dotenv.

## Estrutura

```text
brainstream/
├── brainstream/       # Configurações e URLs do projeto Django
├── accounts/          # Estudante, cadastro, login, logout e recuperação de senha
├── core/              # App compartilhado, landing e painel
├── estudos/           # Tema, SessaoEstudo, mensagens, Modos Guiado, Quiz e Speedrun, context locking e IA
├── manage.py
├── static/            # CSS e JavaScript globais
├── templates/         # Templates globais
└── tests/             # Testes transversais e executor central
```

## Requisitos

- Python 3.9 ou compatível com Django 4.2.
- Ambiente virtual Python.
- MySQL em execução local, com banco e usuário definidos no `.env`.

## Instalação local

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
```

As settings carregam o `.env` da raiz automaticamente (variáveis já definidas no ambiente têm prioridade). Preencha `DJANGO_SECRET_KEY`, `DJANGO_DEBUG` e `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`. Sem `DJANGO_SECRET_KEY`, uma chave insegura só é aceita com `DJANGO_DEBUG=True`. O usuário MySQL precisa de permissão para criar o banco `test_<DB_NAME>` usado pelos testes. Para o login com Google, crie um ID do cliente OAuth (Aplicativo da Web) no Google Cloud Console, cadastre `GOOGLE_REDIRECT_URI` (padrão `http://localhost:8000/accounts/google/callback/`) como URI de redirecionamento e preencha `GOOGLE_CLIENT_ID` e `GOOGLE_CLIENT_SECRET`. Para o tutor real, preencha `AI_API_KEY` e `AI_PROVIDER` (`gemini` ou `anthropic`); `AI_MODEL` é opcional e deve ser um modelo ativo do provedor (`gemini-1.5-flash` foi desativado pelo Google). Deixe a chave vazia para o tutor simulado. Nunca coloque segredos reais no `.env.example`.

## Execução

Na pasta `brainstream/`:

```bash
python manage.py runserver
```

Antes da primeira execução, aplique as migrações com `python manage.py migrate`. Para acessar o admin, crie uma conta com `python manage.py createsuperuser` (pede e-mail e nome). Em desenvolvimento, o e-mail de recuperação de senha é exibido no console do servidor (`EMAIL_BACKEND` pode ser trocado via `.env`).

Abra `http://localhost:8000/`.

## Testes

Na pasta `brainstream/`, execute:

```bash
python manage.py check
python tests/testar_tudo.py
python manage.py test
```

Os testes rodam com `brainstream.test_runner.SemIARealRunner`, que zera `AI_API_KEY`, `AI_PROVIDER` e `AI_MODEL`: nenhum teste chama a IA real, mesmo com chave no `.env`. O executor `testar_tudo.py` delega ao runner do Django, que faz a descoberta dos testes `unittest`, e executa a suíte uma única vez.

Bootstrap, Bootstrap Icons e as fontes são servidos localmente a partir de `static/vendor/`; suas licenças acompanham os respectivos diretórios. A página não carrega nenhum recurso externo.

## Scroll do Painel de Evolução

O painel usa um trecho de 190svh e um container sticky de 100svh em telas
com pelo menos 992 × 760px. Isso oferece 90svh de rolagem narrativa. O progresso é
`p = clamp(-track.getBoundingClientRect().top / (track.height - innerHeight), 0, 1)`.
Em cada evento de scroll, um único requestAnimationFrame pendente atualiza as
variáveis CSS; não há loop permanente nem interceptação de wheel/touch.
A mesma fórmula funciona ao descer e subir.

- 0–20%: opacidade crescente, escala de 0,78 a 0,86.
- 20–40%: escala até 1, perspectiva e desfoque leve chegam a zero.
- 40–55%: cartão de início de sessão (tema, modos e dificuldade).
- 50–80%: três indicadores escalonados e ranking semanal.
- 85–100%: painel completo.

Clique ou foco de teclado no painel libera imediatamente o estado completo pelo
restante da visita, preservando a altura do trecho. A demonstração espelha o painel
real: escolher modo, dificuldade ou sugestão funciona e não reinicia a montagem. Mobile, janelas baixas e
`prefers-reduced-motion` usam conteúdo completo sem sticky prolongado.
Sem JavaScript, o HTML inicial contém indicadores, gráfico e ranking legíveis.

## Movimento da landing

As animações só existem sob `html.js` (classe adicionada no `<head>`) e
`prefers-reduced-motion: no-preference`; sem isso, tudo aparece no estado final.
Usam `transform`, `opacity` e 3D em CSS (`perspective`, `translateZ`, `rotateX/Y`).
Um único `requestAnimationFrame` por evento (motor de efeitos em `landing.js`)
atualiza cabeçalho, a cena hero/tour, o painel e os contadores. Entradas por seção
usam `IntersectionObserver` e disparam uma vez; o autoplay da conversa e o relógio
do Speedrun pausam fora da tela.

Cena hero/tour (≥ 992 × 700px, sem movimento reduzido): um trilho de 440svh com
palco fixo. 0–6%: hero com paralaxe de ponteiro (2–4°, só mouse); 6–30%: a janela
endireita, cresce e aterrissa enquanto texto e cartões saem; 34–100%: quatro
etapas de tour, uma por faixa de scroll, reversíveis. Clicar numa etapa salta
instantaneamente para ela (o palco é fixo, então só o estado muda). Fora dessas
condições, hero e tour ficam no fluxo normal e os passos controlam a janela.

O runner central também descobre `tests/test_dashboard_browser.py`. Ele executa
Chromium headless via protocolo DevTools com Node nativo, sem instalar pacotes.
Usa Chromium já disponível no cache local ou o executável indicado por
`BRAINSTREAM_BROWSER`. Sem Node/Chromium, o teste é explicitamente marcado como
ignorado; testes Django de HTML não comprovam animações.

Validação automatizada realizada em Chromium: fases nos dois sentidos de scroll,
sticky, clique antes do fim da montagem, quatro abas, foco/teclado, altura estável
ao interagir, cena hero/tour (aterrissagem, quatro etapas nos dois sentidos e clique),
demonstração de pergunta (texto digitado tratado como texto), abas dos modos por
teclado, Quiz e Speedrun, ausência de overflow horizontal em 320/375/768/1280/1440px, dark/light,
movimento reduzido e HTML sem JS. Isso não substitui revisão visual humana de
contraste nem validação em Safari/Firefox e dispositivos físicos.
