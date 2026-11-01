# Modo Guiado, tutor Enéas e context locking

Figura 9 e Seções 3.2 e 3.4.3 do PDF. Ver também [[painel-e-metricas]].

## Fluxo

1. No painel, `IniciarSessaoForm.save` cria a sessão; no Modo Guiado também cria a abertura do Enéas (`MensagemSessao.abrir_modo_guiado`, texto em `ABERTURA_MODO_GUIADO`) e o painel redireciona para `/estudo/<id>/`. Quiz e Speedrun continuam voltando ao painel até terem interface.
2. `estudos.views.modo_guiado` busca a sessão com `estudante=request.user` e `modo=guiado`: sessão alheia ou de outro modo dá **404** (não revela existência).
3. `services/conversa.enviar_mensagem` salva a mensagem do estudante → `context_locking.verificar` → se bloqueada, responde com mensagem `sistema` sem chamar a IA → senão `tutor.responder`; falha da IA vira mensagem `sistema` (`AVISO_FALHA`) e a resposta do estudante fica salva.
4. Mesma view atende POST tradicional (redirect para `#mensagem-<id>`) e `fetch` (`Accept: application/json` → `{"mensagens": [html]}` renderizado por `estudos/_mensagem.html`, que escapa o conteúdo). Erros: 400 (vazio/longo), 409 (sessão encerrada), 429 (limite de 80 mensagens do estudante por sessão).

## Pontuação antifarme e conclusão

- Regras em `services/conversa.py`. Resposta **legítima** = do estudante, não bloqueada pelo context locking, com pelo menos 3 palavras e sem repetir uma anterior (comparação sem acentos, caixa e pontuação). Vale 5 pontos, teto 30.
- Os pontos são **recalculados a partir das mensagens** (`atualizar_pontuacao` após cada mensagem não bloqueada), não acumulados em contador: não há o que adulterar e as regras podem mudar sem migrar dados. A sessão aberta mostra os pontos no topo, mas só entra no ranking quando `concluida` (critério do painel).
- `acao=concluir` (mesma view): com menos de 3 legítimas, o Enéas grava uma orientação para aprofundar e nada muda (sem pontos, sem chamar a IA). Com 3+, pede `tutor.sintetizar` (prompt próprio `PROMPT_SINTESE`, 2–3 frases só com o que o estudante formulou, sem busca na web), grava a mensagem final e chama `finalizar(pontuacao=participação + 10, status=CONCLUIDA)`.
- A síntese é pedida **fora** da transação; a sessão é travada (`select_for_update`) só para gravar, e uma conclusão simultânea vira 409 (`SessaoEncerrada`), sem bônus em dobro.
- Falha da IA na síntese não impede concluir: entra `sintese_simulada`, que retoma trechos das próprias respostas do estudante (também usada no modo simulado).
- Concluída: selo "Concluído", botão some, campo vira aviso; novas mensagens e nova conclusão → 409. Sem `acertos`/`total_questoes`, a sessão não afeta a taxa de acerto.

## Autores de mensagem

- `eneas`: só respostas do tutor (LLM ou simulado) e a abertura.
- `sistema`: respostas do context locking e avisos de falha. **Nunca** vão para a LLM.
- `tokens_utilizados` = `input_tokens + output_tokens` da API; 0 para simulado e bloqueios.

## Context locking

- Pré-filtro determinístico por regex sobre texto normalizado (minúsculas, sem acentos): ofensa, manipulação de regras/prompt injection, pedido de resposta pronta, desvio não acadêmico. Ordem de checagem nessa sequência.
- Desvio só bloqueia se a palavra não fizer parte do tema (tema livre: "História do futebol" pode falar de futebol). "série" ficou fora da lista porque é termo de matemática/escola.
- O histórico enviado à LLM reaplica `verificar` e descarta mensagens do estudante bloqueadas, para não reinjetar ofensas ou tentativas de manipulação. Começa com um `user` sintético ("Quero estudar X no Modo Guiado."), une papéis consecutivos e usa só as 30 últimas mensagens relevantes.
- Prompt de sistema: persona socrática (Overholser, 1992), nunca entrega respostas, termina com exatamente uma pergunta, máx. ~4 frases, só conteúdo acadêmico. O nome do tema vai entre `<tema>` como dado; `<` e `>` são removidos dele.
- O filtro é heurístico: pega o óbvio, sem custo. Desvios sutis ficam a cargo do prompt.

## IA: provedores

- `tutor.provedor()`: `AI_PROVIDER` (`gemini`/`google` ou `anthropic`/`claude`); vazio ou `auto` detecta pela chave (`AIza...` = Gemini, senão Claude). Valor desconhecido → erro no log e `TutorIndisponivel` (não adivinha).
- `tutor.modelo()`: usa `AI_MODEL` só se o nome for do provedor (`gemini*`/`claude*`); senão usa o padrão e avisa no log. Evita mandar `claude-*` ao Gemini quando se troca de provedor.
- Testes precisam fixar `AI_PROVIDER` também: o `.env` local define `AI_PROVIDER=gemini`, e `override_settings(AI_API_KEY=...)` sozinho deixaria o teste da Claude cair no Gemini.

### Google Gemini

- SDK `google-genai` 1.47.0 (o `google-generativeai` foi descontinuado pelo Google). Funciona no Python 3.9, com avisos de fim de vida do `google-auth`.
- Padrão fixo `gemini-3.5-flash-lite` (decisão do usuário: versão fixa, não alias `-latest`). Medição em 2026-10-31 com o prompt do Enéas: 3.5-flash-lite 1,2 s; 3.1-flash-lite 1,0 s; 3.5-flash 5,3 s e o dobro de tokens; `gemini-flash-latest` 25–52 s (raciocina antes; deu 504 com timeout de 60 s). Retornam 404: `gemini-1.5-flash` (e `-latest`/`-002`), `gemini-2.5-flash`, `gemini-2.5-flash-lite`. O usuário chegou a pedir `gemini-1.5-flash` como padrão; após confirmar o 404, escolheu fixar uma versão ativa. Versões fixas são aposentadas: revise o padrão quando começar a dar 404. O SDK 1.47 não tem `thinking_level`, só `thinking_budget`.
- `system_instruction` = `prompt_de_sistema`; papéis `user`/`model`; `HttpOptions(timeout=ms, retry_options=3 tentativas)`. Sem `max_output_tokens`: o raciocínio consome a cota de saída e poderia cortar a resposta.
- **Raciocínio mínimo** (`tutor.raciocinio_minimo`, em todas as chamadas: diálogo, síntese, Quiz e Speedrun). Medido em 2026-10-31: `gemini-3.5-flash-lite` **recusa `thinking_budget=0` com 400 INVALID_ARGUMENT** (a família Gemini 3 usa `thinkingLevel`); `thinkingLevel: minimal` é aceito (~1 s, sem tokens de raciocínio), `low` dobra a latência (~2 s, ~450 tokens de raciocínio). O padrão atual do modelo já se comporta como `minimal`; fixar o nível protege contra mudança de padrão do Google. Como o SDK 1.47 não expõe `thinking_level`, o nível vai em `HttpOptions(extra_body=...)` por chamada — o SDK mescla recursivamente com o corpo (o JSON do Quiz é preservado) e com o timeout/retry do cliente. `gemini-2.5-flash*` usa `thinking_budget=0`; outros modelos ficam no padrão. Se o modelo recusar (400), a chamada é refeita sem a configuração. Latências com a chave real após a mudança: Guiado ~1 s, Speedrun ~1,7 s, Quiz ~3 s; picos de 5–20 s observados vieram do servidor do Google, não da configuração.
- Bloqueio por segurança (`prompt_feedback.block_reason` ou `finish_reason` SAFETY/PROHIBITED_CONTENT/BLOCKLIST/SPII/RECITATION) e texto vazio viram `TutorIndisponivel`. `ClientError` 429 = limite; outros 4xx = configuração (log de erro); `ServerError`/`httpx.HTTPError` = indisponibilidade.
- Tokens = `usage_metadata.total_token_count` (inclui tokens de raciocínio).

### Busca na web (Google Search grounding)

- `AI_SEARCH_ENABLED` (env `AI_SEARCH`, padrão `True`; `AI_SEARCH=False` desliga de vez). Só o diálogo do Modo Guiado usa, e **só sob demanda**: `_chamar_gemini` busca quando `busca_ativa()` e `pede_fatos_atuais(tema, última mensagem)` (regex `PEDE_FATOS_ATUAIS`: "atualmente", "recentes", "notícias", anos 2020–2039, "ainda vale" etc.). Conceitos estáveis não pagam a latência da busca. `gerar_com_gemini` acrescenta `tools=[Tool(google_search=GoogleSearch())]`.
- Quiz e Speedrun **não** usam a busca: pedem saída em JSON (`response_json_schema`) e a combinação busca + JSON não pôde ser validada com a chave (teste garante `tools=None`).
- Consultas do modelo (`grounding_metadata.web_search_queries`) vão para o log em INFO, truncadas em 100 caracteres. Elas derivam do que o estudante escreveu: tratar o log como dado pessoal.
- **Recusa da busca:** em 2026-10-31 a chave do projeto respondia normalmente sem busca, mas **toda** chamada com a ferramenta dava 429 RESOURCE_EXHAUSTED (em `gemini-3.5-flash-lite` e `gemini-3.5-flash`), sem detalhar a cota — provavelmente o plano não inclui grounding. Por isso, 400/403/429 com a busca ligada refazem a chamada sem ela e gravam `estudos:gemini-busca-pausada` no cache (10 min) para não pagar a recusa a cada mensagem. O cache padrão é local por processo. Na chamada com busca, o retry do SDK não repete 429 (só 408/5xx): com repetição, a 1ª resposta levava 6,8 s; sem, 2,0 s.
- **Pendente:** os termos da busca do Google exigem exibir as sugestões de busca (`search_entry_point`) e as fontes junto à resposta quando o grounding é usado; a interface ainda não mostra. Resolver antes de produção.

### Claude API

- `AI_API_KEY` vazia → tutor simulado (perguntas fixas em rodízio) e chip "Tutor simulado" na interface. Útil em dev; em produção, configure a chave.
- Com chave: SDK oficial `anthropic` (pinado em `0.125.0`, última versão compatível com Python 3.9; 1.x exige 3.10+). Import é preguiçoso: sem o pacote instalado, a falha vira `TutorIndisponivel` e é registrada no log.
- Modelo padrão `claude-opus-5-5`, `effort: low` (respostas curtas), `max_tokens` 16000, timeout `AI_TIMEOUT` (60 s) e 2 retentativas do SDK. Para modelos que aceitam, envia `fallbacks: "default"` com o beta `server-side-fallback-2026-07-01` (recusa de classificador é refeita em outro modelo). `stop_reason == "refusal"` final vira `TutorIndisponivel`.
- `output_config` e `fallbacks` vão em `extra_body` para não depender de a versão 0.x do SDK conhecer esses parâmetros.
- Chamada é síncrona dentro da request; com IA real a resposta pode levar segundos (a interface mostra "pensando").

## Pendências conhecidas

- Busca na web implementada só no Modo Guiado e sem exibir sugestões/fontes do Google (ver acima); caminho real não verificado porque a chave do projeto recusa a ferramenta.
- Caminho real da Claude API não foi exercitado contra a API: o SDK não estava instalado no ambiente quando isto foi escrito; os testes mockam `_chamar_claude`.
