# Landing e identidade visual

Código: `templates/core/landing.html`, `templates/core/dashboard_demo.html`, `static/css/base.css` (tokens), `static/css/product-ui.css` (sistema de janela), `static/css/landing.css`, `static/js/landing.js`.

## Direção vigente: SaaS tecnológico, o produto é a vitrine

Decidida pelo usuário em 2026-10-30. Cada seção mostra uma interface real do BrainStream (HTML/CSS, nunca PNG/mockup). Efeito visual só com função: profundidade para dar destaque ao produto, animação para explicar o produto, interação para demonstrar o produto. Referência de qualidade: produtos como Linear, Vercel, Stripe, sem copiar nenhum.

Fora da direção (não reintroduzir): estética editorial/artística/museu, pinturas ou obras clássicas, narrativa filosófica, partículas, redes neurais decorativas, blobs, gradiente ou brilho decorativo, excesso de glassmorphism.

## Identidade

- Escuro padrão: fundo `#0A0B10`, superfícies `#11131A` / `#181B24` / `#20242F`, texto `#ECEEF3` / `#9097A6`. Claro usa os mesmos papéis de token.
- Um acento: `#2EE6C5`, com moderação (CTA, estado ativo, indicadores, foco, destaque da interface ativa). Como texto no tema claro usa `--color-accent-text` (`#087A67`); o foco tem token próprio (`--color-focus`) porque o acento puro não tem contraste sobre fundo claro.
- Cores de dado só dentro das interfaces: verde = acerto, âmbar = alerta, azul = informação. Sem violeta.
- Favicon `static/img/favicon.svg`, também usado como `.brand-mark` (marca da navbar e das laterais). A arte foi redesenhada pelo usuário depois da 1ª versão (hoje um monograma "B" de fluxo); o arquivo é a fonte da verdade. É a única exceção pedida à regra "sem gradientes decorativos".
- Avatar do Enéas `static/img/eneas.svg` (partial `estudos/_avatar_eneas.html` nas telas de estudo; `.msg > .estudo-avatar-eneas` em `product-ui.css` na landing): substitui o capelo `bi-mortarboard` e o "E" das janelas ilustrativas. A arte também foi redesenhada pelo usuário (hoje um robô tutor); não descreva o desenho em código ou testes. Única `<img>` permitida na landing (o produto continua em HTML).
- A marca leva o estudante logado ao painel (`core:painel`); visitantes vão à landing.
- Tipografia: apenas Hanken Grotesk (OFL, local, pesos 400–700). Títulos 650–700 com tracking negativo; números de métrica tabulares; monoespaçada (fonte do sistema) só em timer.

## Sistema de janela do produto

`.app-window` + `.app-bar` + `.app-body`/`.app-main`/`.app-side` e primitivas (`.msg`, `.typing`, `.note-card`, `.chip`, `.bar`, `.option`, `.seg`, `.ring`) em `product-ui.css`. Hero, tour, modos, painel, bento, demo e CTA usam a mesma janela. Ao criar uma nova interface na landing, compor com essas peças em vez de estilizar do zero.

## Dados ilustrativos coerentes

Conjunto único: 12 sessões concluídas (11 → 12 ao fim do tour), 78% de acerto, sequência de 4 dias, 65% da meta semanal, ritmo Seg–Sex 34/56/43/78/65%, ranking Alex, Sam, Você (3º). Toda janela tem selo "Dados ilustrativos". Um teste Django verifica a consistência; não introduzir números diferentes.

## Arquitetura do movimento

- Gate: classe `js` no `<html>` + `prefers-reduced-motion: no-preference`. Sem JS ou com movimento reduzido, tudo no estado final (a janela do tour sem `data-state` mostra a conversa completa).
- Motor único em `landing.js`: `effects` (funções chamadas no mesmo `requestAnimationFrame`) + `tweens` curtos (contadores). Não criar listeners de scroll ou loops paralelos; registrar um efeito.
- Cena hero/tour (`.story.is-scene`, ≥ 992 × 700px): trilho de 440svh com palco sticky; fases e mapeamento de etapas descritos no README. O estado da janela é `data-state` 1–4 e as partes da conversa usam `data-from`/`data-until`. Clique numa etapa faz `scrollTo` instantâneo para o centro da faixa (o palco é fixo, então só o estado muda) para scroll e estado nunca divergirem.
- Autoplay da conversa só no hero e visível; relógio do Speedrun só começa na primeira resposta e pausa fora da tela ou de outra aba.
- Painel de evolução (`dashboard_demo.html`): **espelha o painel real** (`core/painel.html`) desde 2026-10-31 — lateral com histórico e perfil, tema livre com sugestões, três modos com régua de dificuldade (some no Guiado, como no real), 3 indicadores (azul/verde/âmbar) e ranking semanal com "Você" em destaque. As 4 abas fictícias (Visão geral/Meus estudos/Desempenho/Ranking) e o gráfico semanal saíram: o produto real não os tem. Controles são `<button aria-pressed>` de escolha única. Abaixo de 1200 px a lateral some (no real ela vira gaveta). Contrato de scroll preservado (190svh); fases: início 40–55%, indicadores 50–80% escalonados, ranking 65–80% (`--dashboard-start`, `--dashboard-stat-0..2`, `--dashboard-ranking`).
- Modos da landing seguem os modos reais: Quiz "Questão 3 de 5" com "+10 pontos"; Speedrun com 10 s por afirmação (o relógio recomeça a cada resposta e no tempo esgotado), rodada de 5 e 10 pontos por acerto.
- GSAP/ScrollTrigger, Three.js e Lenis foram avaliados e não são necessários; o motor próprio sustentou a cena. Só reconsiderar com motivo técnico concreto e autorização (`AGENTS.md`).

## Armadilhas de layout

- Ícone do menu (hambúrguer): o `<html>` recebe `data-bs-theme`, e o Bootstrap já troca o ícone para branco no escuro; `filter: invert(1)` em cima disso o deixava **preto no fundo escuro**. Hoje o ícone é máscara SVG pintada com `--color-ink`. No menu aberto (< 992 px), os links precisam de `.navbar-collapse .navbar-nav .nav-link` para vencer `.navbar-expand-lg .navbar-nav .nav-link`.

- Grades de 12 colunas com `gap: 2rem` estouram em 320px; abaixo de 768px tudo vira uma coluna. Em grades de coluna única use `minmax(0, 1fr)`, não `1fr` (o painel vazava dentro da janela).
- Nunca `overflow: hidden` em ancestral de `sticky`; para conter elementos em `translateZ`, use `overflow-x: clip` (está no `.site-main`).
- Fora da cena, o HTML do hero tem o tour antes da janela; a ordem visual (texto → produto → faixa → tour) vem de `order` no CSS.
- No celular, sem cartões flutuantes e sem perspectiva: leitura e interação primeiro.

## Páginas de erro

- `404.html` estende `base.html` (o Django renderiza com request, então `user` existe) sem a navbar da landing, cujas âncoras não funcionam fora dela.
- `500.html` não estende nada: o handler do Django renderiza sem request nem context processors, e o erro pode ter vindo do banco. Só use `{% static %}` (lê settings) e links fixos como `/`; nada de `{% url %}`, `user` ou tags do projeto. O botão "Recarregar" é um `href=""`, sem JS. Um teste garante zero consultas ao banco.
- A fala do Enéas reaproveita o balão do Modo Guiado; o ícone do 500 usa o tom de aviso, não o acento.

## Histórico

- 2026-10-30, primeira versão: direção editorial "tinta e latão" (Fraunces, frase-pôster com *A Morte de Sócrates*, verbos sobre obras em domínio público). Descartada no mesmo dia pelo usuário por ser artística/editorial demais e não representar o produto. Imagens e Fraunces removidas do repositório. A recusa da Zodiak/Switzer (licença ITF FFL proíbe redistribuição em repositório) continua válida para qualquer fonte nova: só licenças que permitam versionar o arquivo.

Relacionado: [[testes-de-navegador]].
