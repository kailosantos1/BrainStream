# Modo Quiz

Figura 10 e Seção 3.4.4 do PDF. Ver também [[modo-guiado-e-context-locking]] (provedores de IA) e [[painel-e-metricas]] (ranking e KPIs).

## Fluxo

1. Painel com `modo=quiz` → `/estudo/quiz/<id>/` (`estudos.views.modo_quiz`; sessão filtrada por `estudante=request.user` e `modo=quiz`, senão 404).
2. Primeira visita (GET) chama `quiz.garantir_questoes`: bloqueia a linha da sessão (`select_for_update`), confere de novo e só então gera — duas abas abertas não geram (nem pagam) duas vezes.
3. Cada clique é um POST (`questao`, `resposta`). `quiz.responder` bloqueia a sessão, aceita só a questão atual (a primeira sem resposta) e grava uma única vez: fora de ordem, repetida ou sessão concluída → 409; letra inválida → 400.
4. Na 5ª resposta: `sessao.finalizar(acertos, total_questoes=5, pontuacao=acertos×10)` → status `concluida`, entra em `sessoes_na_semana`, `taxa_de_acerto` e `ranking_semanal`.
5. A mesma view atende fetch (`Accept: application/json` → `respondida`, `novas`, `pontos`, `numero_atual`, `concluida`) e POST tradicional (redirect para `#feedback-<n>`).

## Modelagem

- `QuestaoQuiz` (modelo leve, não `request.session`): ordem, enunciado, alternativas A–D, correta, explicação, resposta, `respondida_em`, `origem` (`ia`/`simulada`). Única por (sessão, ordem); checks de letra.
- O feed é derivado das questões (boas-vindas, card, resposta, feedback, próxima, card final); o quiz não usa `MensagemSessao`.
- **Segurança:** a letra correta e a explicação só saem no HTML depois da resposta (testado).
- Pontuação: 10 por acerto (`PONTOS_POR_ACERTO`), sem bônus; status final sempre `concluida` (o "Revisar" do painel ainda não tem regra).

## Geração

- Gemini com `response_mime_type='application/json'` + `response_json_schema` (exatamente 5 itens, A–D, `correta` em enum). Mesmo assim, `quiz.validar` confere tudo (vazio, repetidas, tamanho) — JSON inválido cai no banco simulado com log de aviso.
- `_embaralhar` sorteia a posição da correta (modelos tendem a repetir a mesma letra).
- Banco simulado: questões revisadas para Fotossíntese (`BANCO_SIMULADO`, chave normalizada sem acentos); para outros temas, questões de estratégia de estudo que valem para qualquer assunto. Interface mostra "Questões simuladas".
- O prompt recebe `{nivel}` de `NIVEIS[sessao.dificuldade]` (fácil = conceitos fundamentais e distratores claros; médio = aplicação; difícil = análise e vestibular, distratores próximos). Ver [[painel-e-metricas]].
- Provedor `anthropic` ainda usa o banco simulado no quiz (só o Gemini gera questões).
- Medido em 2026-10-31: `gemini-3.5-flash-lite`, 5 questões corretas em ~3,6 s.
- `tutor.gerar_com_gemini(sistema, historico, modelo, **config)` é o ponto único de chamada ao Gemini (tutor e quiz), com o mapeamento de erros para `TutorIndisponivel`.

## Interface

- `estudos/base_estudo.html` é a base comum de Guiado e Quiz (lateral, topo, pontos com `data-estudo-pontos`); CSS comum em `estudo.css` (prefixo `estudo-`), específico em `modo_quiz.css`; JS comum em `estudo.js` (lateral recolhível, `irParaFim`, `irPara`).
- **Armadilha:** `.visually-hidden` é `position: absolute`; dentro da área rolável sem ancestral posicionado, esses textos alongavam o documento e `scrollIntoView` rolava a janela inteira (o topo sumia). Correção: `.estudo-scroll { position: relative }` e rolagem calculada só no contêiner (`irPara`).

## Testes

- `tests/test_modo_quiz.py`: validação do JSON, embaralhamento, fallback, fluxo completo (3/5 → 30 pts e painel), validação no servidor, POST sem JS, privacidade.
- `brainstream/test_runner.py` (`SemIARealRunner`) zera a IA na suíte inteira: um teste do painel que seguia o redirect para o quiz chegou a chamar o Gemini real antes disso.
