# Testes de navegador da landing

- `tests/test_dashboard_browser.py` é descoberto pelo runner central (`python tests/testar_tudo.py`) e executa `tests/dashboard_browser.mjs` em Chromium headless via DevTools Protocol, só com módulos nativos do Node. Sem Node/Chromium local (cache do Playwright ou `BRAINSTREAM_BROWSER`), o teste é marcado como ignorado: reporte isso.
- Cobre: cena hero/tour (aterrissagem, quatro etapas nos dois sentidos, clique numa etapa), painel ilustrativo espelhado do real (fases nos dois sentidos, sticky, modo/dificuldade/sugestão por mouse e teclado, régua some no Guiado, geometria estável), demo "Pergunte ao Enéas" (texto digitado nunca vira HTML), modos (abas por teclado, Quiz erro/acerto com +10, Speedrun de 10 s por afirmação), ausência de overflow em 320/375/768/1280×720/1440, dark/light, movimento reduzido e página sem JS.
- Seletores do teste miram o componente (`[data-dashboard-modo]`, `[data-dashboard-nivel]`, `[data-dashboard-content]`, `[data-seg-tab]`), nunca o primeiro `[role=tab]`/`[role=tabpanel]` da página. O painel ilustrativo não tem mais abas; o único `tablist` é o da seção de modos.
- `tests/test_painel_browser.py` (painel real, logado) cobre régua de dificuldade, exclusão no histórico e carregamento ao iniciar sessão; usa viewport de desktop porque abaixo de 992 px o histórico fica num offcanvas fechado, que não recebe foco.
- Comparações de escala do painel usam tolerância de 0,001: `scrollTo` arredonda para pixel inteiro e o topo do trilho pode ser fracionário. Não reverter para igualdade exata.
- A verificação de 1280×720 existe porque cartões em `translateZ` criaram rolagem horizontal só nessa largura; foi confirmado que o teste falha sem o `overflow-x: clip`.
- Testes Django (`tests/test_core.py`) validam o HTML sem JS: ordem das seções, abas e painéis acessíveis, passos do tour, só o avatar do Enéas como `<img>` (produto em HTML), selos de dados ilustrativos, consistência dos dados entre seções, fontes locais e ausência de recursos externos.
- Nada disso substitui revisão humana em Safari/Firefox e dispositivos reais.

Relacionado: [[landing-e-identidade-visual]].
