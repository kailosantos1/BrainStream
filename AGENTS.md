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

## Convenções de testes

- Mantenha testes de projeto em `brainstream/tests/` e testes específicos junto ao app correspondente.
- Use `django.test.TestCase` para apps, models, views, formulários, regras de negócio e permissões.
- Isole integrações externas com mocks; testes não devem depender de serviços externos.
- Execute a suíte central com `python testar_tudo.py` a partir de `brainstream/`.
