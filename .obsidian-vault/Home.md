# BrainStream — Memória do projeto

Este vault guarda o conhecimento persistente do projeto: decisões, regras, integrações, trade-offs e histórico.

- `AGENTS.md` (raiz do projeto) contém as instruções de trabalho.
- O código é a fonte da verdade sobre o comportamento atual.
- Detalhes, decisões, regras de negócio e histórico ficam aqui, em notas por assunto.

## Categorias

- `arquitetura/` — estrutura do sistema, decisões técnicas, modelagem.
- `regras-de-negocio/` — regras do domínio e invariantes.
- `integracoes/` — serviços externos, contratos e particularidades.
- `infraestrutura/` — configuração, deploy, operação.
- `testes/` — estratégia de testes e cobertura por área.
- `historico/` — decisões datadas e mudanças de rumo.
- `relatorios/` — registros técnicos de alterações relevantes.

## Notas

Adicione aqui um link `[[nota]]` para cada nota criada, agrupado pela categoria.

### Arquitetura

- [[landing-e-identidade-visual]] — direção SaaS "produto como vitrine", tokens, sistema de janela, dados ilustrativos, motor de movimento, armadilhas e histórico da direção descartada.
- [[contas-e-autenticacao]] — `Estudante` (login por e-mail), rotas de conta, recuperação de senha, login com Google (OAuth + PKCE), perfil, visual das Figuras 6/7 e armadilha da troca de user model.
- [[painel-e-metricas]] — `Tema`/`SessaoEstudo`, regras de semana, acerto, sequência e ranking calculados, e a armadilha de `__date` no MySQL.
- [[modo-guiado-e-context-locking]] — fluxo do Modo Guiado, `MensagemSessao`, pré-filtro e prompt socrático, Claude API e tutor simulado.
- [[modo-quiz]] — geração de questões (Gemini em JSON + banco simulado), validação no servidor, finalização e pontuação, base comum das telas de estudo.
- [[modo-speedrun]] — Verdadeiro ou Falso com 10 s medidos no servidor, tempo esgotado, tempo total, geração estruturada compartilhada.

### Infraestrutura

- [[configuracao-ambiente-e-banco]] — carregamento do `.env`, PyMySQL, regras de `SECRET_KEY`/`DEBUG` e permissões do banco de testes.

### Testes

- [[testes-de-navegador]] — teste Chromium central, o que cobre e por que usa tolerância.
