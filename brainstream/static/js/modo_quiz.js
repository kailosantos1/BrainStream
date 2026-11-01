(function () {
  const estudo = window.BrainStreamEstudo;
  const feed = document.querySelector('[data-estudo-feed]');
  const pontos = document.querySelector('[data-estudo-pontos]');
  const numero = document.querySelector('[data-quiz-numero]');
  const erro = document.querySelector('[data-quiz-erro]');
  const dica = document.querySelector('[data-quiz-dica]');
  estudo.irParaFim(false);

  if (!feed || !window.fetch) {
    return; // sem fetch, cada alternativa envia o formulário normalmente
  }

  const mostrarErro = function (texto) {
    erro.textContent = texto || '';
    erro.hidden = !texto;
  };

  feed.addEventListener('submit', function (evento) {
    const form = evento.target.closest('[data-quiz-form]');
    const escolha = evento.submitter;
    if (!form || !escolha || form.dataset.enviando) {
      return;
    }
    evento.preventDefault();
    form.dataset.enviando = 'true';
    const botoes = form.querySelectorAll('button');
    botoes.forEach(function (botao) { botao.disabled = true; });
    escolha.classList.add('is-sending');
    mostrarErro('');

    const dados = new FormData(form);
    dados.set('resposta', escolha.value);

    fetch(form.action, {
      method: 'POST',
      body: dados,
      headers: { Accept: 'application/json' },
      credentials: 'same-origin',
    })
      .then(function (resposta) {
        return resposta.json().catch(function () { return {}; }).then(function (corpo) {
          if (!resposta.ok || !corpo.respondida) {
            throw new Error(corpo.erro || 'Não foi possível enviar sua resposta. Confira a conexão e tente de novo.');
          }
          return corpo;
        });
      })
      .then(function (corpo) {
        // Resposta, feedback e próxima questão (ou card final) entram logo abaixo da questão respondida.
        const molde = document.createElement('template');
        molde.innerHTML = corpo.novas;
        const chegaram = Array.from(molde.content.children);
        chegaram.forEach(function (filho) { filho.classList.add('estudo-entrando'); });
        const card = form.closest('[data-quiz-questao]');
        card.after.apply(card, chegaram);
        card.outerHTML = corpo.respondida; // versão travada, com a correta e a escolhida marcadas

        pontos.textContent = corpo.pontos;
        if (numero) {
          numero.textContent = corpo.numero_atual;
        }
        if (corpo.concluida && dica) {
          dica.textContent = 'Quiz concluído. Seus pontos já aparecem no painel.';
        }
        estudo.irPara(chegaram.find(function (filho) { return filho.id.indexOf('feedback-') === 0; }));
        const proximo = feed.querySelector('[data-quiz-form] button, #estudo-final a');
        if (proximo) {
          proximo.focus({ preventScroll: true });
        }
      })
      .catch(function (falha) {
        delete form.dataset.enviando;
        botoes.forEach(function (botao) { botao.disabled = false; });
        escolha.classList.remove('is-sending');
        mostrarErro(falha.message);
        escolha.focus();
      });
  });
}());
