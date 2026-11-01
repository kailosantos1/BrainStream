# Regras de trabalho do BrainStream

- Leia este arquivo antes de iniciar cada tarefa.
- Trabalhe somente no escopo solicitado; evite abstrações e dependências desnecessárias.
- Preserve a arquitetura Django MVT e a estrutura existente.
- Priorize segurança, legibilidade, simplicidade e responsividade.
- Toda funcionalidade ou correção deve incluir ou atualizar testes relevantes.
- Registre aqui apenas novas decisões ou regras permanentes, sem logs extensos. Atualize o README quando instalação, arquitetura ou funcionalidades mudarem.
- Nunca exponha credenciais, use segredos hardcoded ou desabilite proteções para fazer testes passarem.
- Execute os testes relacionados e a suíte completa quando viável; reporte falhas e limitações com transparência.
- Não execute alterações destrutivas, instale pacotes novos ou mude o banco sem necessidade e justificativa.
- Encerre cada etapa com um resumo curto: arquivos, testes, resultados e pendências.

## Contas

- `AUTH_USER_MODEL = 'accounts.Estudante'`: o login é o e-mail (único, salvo em minúsculas) e não há `username`. Use `get_user_model()`/`settings.AUTH_USER_MODEL`, nunca `auth.User`.
- Logout só via POST com CSRF. Redirecionamentos `next` passam por `url_has_allowed_host_and_scheme`.
- Login com Google só entra numa conta existente se o Google confirmar `email_verified`; `state` é de uso único e o fluxo usa PKCE. Não relaxe essas checagens.

## Tutor Enéas

- Toda mensagem do estudante passa por `estudos/services/context_locking.verificar` antes da IA; bloqueios nunca chamam a LLM. Sessões são sempre buscadas filtrando `estudante=request.user`. Histórico e páginas de sessão também filtram `visivel_no_historico=True` (excluir só esconde); métricas e ranking nunca filtram, para os pontos serem preservados.
- Testes nunca chamam a API real: o `TEST_RUNNER` do projeto zera `AI_API_KEY`/`AI_PROVIDER`/`AI_MODEL`; para testar o caminho real, use `override_settings(...)` com mocks de `estudos.services.tutor` ou `google.genai.Client`.
- Respostas de Quiz e Speedrun são validadas no servidor; gabarito e explicação nunca vão ao HTML antes da resposta, e o prazo do Speedrun é medido no servidor (o relógio da tela é só visual). Detalhes em `.obsidian-vault/arquitetura/modo-guiado-e-context-locking.md`.

## Convenções de testes

- Mantenha testes de projeto em `brainstream/tests/` e testes específicos junto ao app correspondente.
- Use `django.test.TestCase` para apps, models, views, formulários, regras de negócio e permissões.
- Isole integrações externas com mocks; testes não devem depender de serviços externos.
- Execute a suíte central com `python tests/testar_tudo.py` a partir de `brainstream/`.
- Testes de HTML não substituem testes de interação. O teste opcional Chromium do painel deve continuar descoberto pelo runner central; reporte skips e limitações de navegador.

## Stack frontend

- Use Django Templates, Bootstrap 5, CSS3 personalizado, JavaScript Vanilla e Bootstrap Icons.
- Não use Tailwind CSS, React, Vue, jQuery ou outros frameworks frontend sem autorização explícita.
- Prefira Bootstrap 5 para layout, grid, responsividade e componentes adequados; reserve CSS personalizado para identidade visual, cores, tipografia, animações e componentes exclusivos.
- Implemente dark/light mode com variáveis CSS próprias, preservando a compatibilidade com componentes Bootstrap.
- Evite estilos inline e `!important` sem necessidade; organize CSS e JavaScript para manutenção e reutilização.
- Mantenha Bootstrap 5 e Bootstrap Icons como assets locais em `brainstream/static/vendor/`, com suas licenças preservadas.
- Animações progressivas do painel devem ter estado final legível sem JS e com movimento reduzido; foco/clique tem prioridade sobre efeitos de scroll.
