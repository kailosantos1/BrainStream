# Painel do estudante e métricas

Código: `estudos/models.py`, `estudos/metricas.py`, `estudos/forms.py`, `core/views.py` (`painel`), `templates/core/painel.html`, `_ranking_linha.html`, `static/css/painel.css`, `static/js/painel.js`, `tests/test_painel.py`.

## Modelagem (diagrama de classes, Apêndice C)

- App `estudos` separado do `core`: `Tema` (nome, slug, categoria, descrição) e `SessaoEstudo` (estudante, tema, modo, status, data_inicio, data_fim).
- Campos além do diagrama em `SessaoEstudo`: `acertos`, `total_questoes`, `pontuacao`. São necessários para a taxa de acerto e o ranking. `finalizar()` grava o resultado; os modos (Figuras 9–11) devem usá-lo.
- Status: `em_andamento` (Em progresso), `concluida` (Concluído), `revisar` (Revisar).
- `RankingSemanal`, `Estatistica` e `HistoricoEstudo` do diagrama **não viraram tabelas**: são calculados em `metricas.py` a partir das sessões (sem dado duplicado para sincronizar). Reavaliar só se o volume exigir cache.
- Temas iniciais: migração de dados `0002_temas_iniciais` (12 temas, incluindo os da Figura 8).
- Tema é texto livre (Seção 1, 2.1.3): `Tema.objects.resolver(nome)` normaliza espaços, reaproveita um tema com o mesmo nome sem diferenciar maiúsculas e, se não houver, cria um em `CATEGORIA_GERAL` ('Geral'), sem inferir matéria. Slug único com sufixo (`c`, `c-2`) porque nomes diferentes podem gerar o mesmo slug; `IntegrityError` concorrente cai na releitura.
- Temas 'Geral' exibem só o nome (`__str__`) e **nunca** viram sugestão: as pílulas listam apenas temas curados, ordenados por número de sessões. Assim, texto digitado por um estudante não aparece para outros.
- O texto do tema ainda não é filtrado quanto a conteúdo; quando o Enéas consumir o tema, trate-o como entrada não confiável (prompt injection).

## Regras das métricas

- Semana: segunda 00:00 até a segunda seguinte, no fuso local (`America/Sao_Paulo`).
- Sessões na semana: só `concluida` com `data_fim` na semana.
- Taxa de acerto: soma de acertos / soma de questões de todas as sessões com questões; sem questões → "—".
- Sequência: dias locais consecutivos com qualquer sessão iniciada, terminando hoje **ou ontem** (o dia atual ainda pode ser estudado).
- Ranking: soma de `pontuacao` das sessões concluídas na semana, só quem tem pontos > 0; desempate por nome. Top 5 + linha própria do estudante se estiver fora. Nome público "Ana S." (não expõe nome completo).
- Pontos no perfil da lateral: total histórico. "Nível" da figura ficou de fora: não há regra definida.

## Armadilha: datas no MySQL

Não usar lookups `__date`/`TruncDate` com `USE_TZ`: o MySQL só converte fuso em SQL se as tabelas de timezone estiverem carregadas (senão retorna NULL). Filtrar por intervalos de datetime aware e converter datas em Python, como faz `metricas.py`.

## Interface

Iniciar sessão faz POST no próprio `/painel/` (PRG): cria a sessão `em_andamento` e mostra mensagem; erro de formulário volta com status 400. Lateral é `offcanvas-lg` do Bootstrap (gaveta abaixo de 992px). Modos são rádios nativos estilizados. Cores de dado nos indicadores: azul (sessões), verde (acerto), âmbar (sequência). Os ícones dos modos são os mesmos da coluna lateral do login/cadastro.

**Carregamento:** a geração do Quiz/Speedrun acontece no GET da página do modo (`garantir_questoes`), antes de qualquer HTML sair; por isso o retorno visual fica na página de origem. Ao enviar, `painel.js` trava o botão (com `aria-busy`, mantendo o acento) com spinner e a mensagem do modo (5º item de `modos` na view); `carregando.js` mostra a camada `core/_carregando.html` (marca pulsando) se a próxima página demorar mais de 500 ms. A camada está no painel e em `base_estudo.html` (links do histórico com `data-carregando`) e é desfeita no `pageshow` do bfcache. No teste Chromium (`tests/test_painel_browser.py`, que também cobre a régua de dificuldade e a exclusão), o CDP não responde durante a navegação pendente: a própria página registra a camada no `sessionStorage`.

**Ranking como leaderboard:** pódio por `:nth-child(1..3)` da lista (ouro/prata/bronze; as linhas do top vêm primeiro no `<ol>`, e a linha do próprio estudante fora do top entra depois do "…", então nunca cai nas três primeiras posições). Medalhas 🥇🥈🥉 no template ao lado do número; `.is-me` (gradiente ciano→azul, borda e glow no acento) vem depois no CSS e vence o pódio. Pontos em pill com troféu ("pts" visual, "pontos" para leitor de tela); sequência em badge com fogo. Cores do pódio em variáveis por tema (mais fechadas no claro para o número passar contraste). No celular, os 3 indicadores ficam lado a lado como widgets e a nota de cada um fica só para leitores de tela. Toque: modos, sugestões, pílulas, alternativas do Quiz e `.btn` afundam para `scale(0.98)` (desligado com movimento reduzido); alternativas do Quiz têm 52px no celular.

**Régua de dificuldade:** `SessaoEstudo.dificuldade` (`facil`/`medio`/`dificil`, padrão `medio`; migração `estudos.0006`). O pedido do usuário pôs o campo na sessão; no diagrama de classes (pág. 28 do PDF) ele aparece como `nivel_dificuldade` em `ModoGuiado`. Só Quiz e Speedrun usam: o form força `medio` no Modo Guiado e quando nada vem. No painel, as pílulas somem com o Modo Guiado marcado via CSS `:has(#modo-guiado:checked)` (sem JS). A dificuldade entra no prompt (`NIVEIS` em `quiz.py`/`speedrun.py`) e aparece como chip na tela do modo; o banco simulado não varia por nível.

**Exclusão de sessões (exclusão lógica):** `POST /estudo/<id>/excluir/` (`estudos:excluir_sessao`, CSRF, `get_object_or_404(..., estudante=request.user, visivel_no_historico=True)` → 404 para sessões alheias ou já excluídas). Só marca `visivel_no_historico=False` (migração `estudos.0007`, campo indexado): **pontos, ranking semanal, taxa de acerto e desempenho continuam contando a sessão** — decisão do usuário, para que excluir não vire um jeito de mexer na pontuação (a 1ª versão apagava a sessão e tirava os pontos). Mensagens, questões e afirmações ficam no banco. Toda consulta de histórico (painel, telas de estudo, Meu Perfil) filtra `visivel_no_historico=True`, e as views dos três modos também, então a página da sessão excluída dá 404. As métricas em `estudos/metricas.py` **não** filtram por visibilidade de propósito. Redireciona para `next` (validado por `url_has_allowed_host_and_scheme`), exceto se `next` for a página da própria sessão excluída, que vai para o painel; o aviso vem do framework de mensagens (inline no painel, toast nas telas de estudo). Sem JS a lixeira exclui direto; com `historico.js`, abre uma confirmação no item (foco em "Cancelar", Esc fecha sem fechar o offcanvas). O botão "Excluir" usa `--color-canvas` como texto: branco sobre o vermelho do tema escuro não passava AA.

Relacionado: [[contas-e-autenticacao]], [[landing-e-identidade-visual]].

## Desempenho acumulado (página Meu Perfil)

- `metricas.desempenho(estudante)`: sessões iniciadas e concluídas (status `concluida`, mesmo critério do painel), tempo de estudo, taxa de acerto global (`taxa_de_acerto`) e por modo (Quiz/Speedrun, só sessões concluídas), pontos totais, melhor posição no ranking e as 5 matérias mais estudadas.
- **Tempo de estudo:** concluídas = `data_fim - data_inicio`; Modo Guiado (nunca finaliza) = da 1ª à última mensagem. Cada sessão conta no máximo 2 h (`TETO_TEMPO_SESSAO`), para uma aba esquecida não inflar o total. No Speedrun inclui a espera antes de "Iniciar".
- **Matéria:** categoria do tema; temas digitados (categoria "Geral") contam pelo próprio nome, para "Geral" não virar uma matéria que mistura tudo.
- **Melhor posição:** recalcula o placar de cada semana em Python com o mesmo critério de `ranking_semanal` (pontos de concluídas, desempate por nome); empate de posição fica com a semana mais recente. Lê todas as sessões pontuadas do sistema — revisar se o volume crescer muito.
