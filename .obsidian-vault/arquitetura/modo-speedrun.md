# Modo Speedrun

Figura 11 e Seção 3.4.5 do PDF. Segue o mesmo desenho do [[modo-quiz]] (geração estruturada, validação no servidor, base comum das telas de estudo).

## Regras

- 5 afirmações de Verdadeiro ou Falso, 10 s cada (`LIMITE_SEGUNDOS`), 10 pontos por acerto, sem bônus de velocidade.
- **Estado de espera:** a sessão começa "aguardando" (nenhuma afirmação com `apresentada_em`). A página mostra só o card de preparação; a 1ª afirmação fica oculta e o relógio parado. `POST acao=iniciar` (`speedrun.iniciar`, idempotente) grava o prazo da 1ª. Responder antes disso → 409. GET nunca inicia o prazo.
- O prazo começa em `apresentada_em`: da 1ª no clique em "Iniciar Speedrun", das seguintes na resposta da anterior. Recarregar a página **não** reinicia o prazo; o relógio retoma do tempo restante calculado no servidor (`restante_ms`).
- Resposta conta como **tempo esgotado** se: a página enviar `resposta=tempo` (relógio zerou) **ou** chegar depois de `apresentada_em + 10 s + 2 s` (`TOLERANCIA_SEGUNDOS`, latência de rede). Assim o prazo vale mesmo sem JS ou com o relógio adulterado.
- Esgotada: `tempo_esgotado=True`, `resposta=None`, 0 pontos. Na 5ª: `finalizar(acertos, 5, acertos×10)`.
- Tempo total exibido = soma do tempo de cada resposta, limitado a 10 s por afirmação (esgotadas contam 10 s). Não é gravado: é calculado das afirmações.

## Som e vibração

- Web Audio sintetizado na hora (sem arquivos): acerto = dois senos ascendentes (660 → 880 Hz); erro e tempo esgotado = triângulo descendente (330 → 180 Hz); últimos 3 s = clique quadrado curto e baixo. Envelope exponencial curto para não estalar.
- Navegadores só liberam áudio após um gesto do usuário: o `AudioContext` é criado/retomado no clique em "Iniciar Speedrun" (ou, se a página foi recarregada no meio, no primeiro toque/tecla). `click()` disparado por script não libera; para testar a síntese no headless use `--autoplay-policy=no-user-gesture-required`.
- `navigator.vibrate(50)` no acerto e `[80, 40, 80]` no erro/esgotado, só onde existe a API. O mudo (`brainstream-speedrun-som` no localStorage, botão `bi-volume-up`/`bi-volume-mute` com `aria-pressed`) silencia só o som, não a vibração.

## Modelagem e geração

- `AfirmacaoSpeedrun`: texto, `verdadeira`, justificativa, `resposta` (bool nulo), `tempo_esgotado`, `apresentada_em`, `respondida_em`, `origem`. Único por (sessão, ordem).
- Gemini com `response_json_schema` (5 itens, `verdadeira` booleano). `speedrun.validar` exige pelo menos uma verdadeira e uma falsa (o prompt pede ao menos duas de cada); senão, banco simulado.
- O prompt recebe `{nivel}` de `NIVEIS[sessao.dificuldade]` (fácil = fatos centrais e erro evidente; difícil = detalhes, exceções e erro sutil, sem pegadinha de linguagem).
- `services/geracao.gerar_estruturado` é o caminho comum de Quiz e Speedrun (Gemini em JSON validado ou fallback simulado, com log de aviso).
- **Armadilha corrigida:** embaralhar com `random.shuffle` a lista devolvida pelo banco simulado alterava a lista do módulo (compartilhada entre requisições). Agora usa `random.sample` (cópia).
- Medido em 2026-10-31: `gemini-3.5-flash-lite`, 5 afirmações corretas em ~2,7 s.

## Interface

- Faixa "Tempo restante" sob o topo: número grande + barra (`transform: scaleX`, sem relayout). Cor sólida da marca → aviso (≤5 s) → perigo (≤3 s); sem gradiente (regra de identidade). Com movimento reduzido, a barra anda por segundo, não por quadro. Leitor de tela ouve "5 segundos", "3 segundos" e "Tempo esgotado" (`aria-live` assertivo).
- Botões largos Verdadeiro (success) e Falso (danger) no rodapé; texto escuro no tema escuro e branco no claro, para manter o contraste. Atalhos V/F só com teclado físico (a dica só aparece com `hover: hover` e `pointer: fine`).
- Resposta 409 no fetch (outra aba ou reenvio) recarrega a página para mostrar o estado real.
- Classes compartilhadas com o Quiz migraram para `estudo.css`: `estudo-feedback`, `estudo-veredito`, `estudo-final*` e `estudo-entrando`.

## Testes

- `tests/test_modo_speedrun.py`: validação do JSON, fallback, acerto, erro, expiração pela página, resposta atrasada (servidor), tolerância, fluxo completo (3/5 → 30 pts e painel), soma do tempo total, validação no servidor, POST sem JS e privacidade.
