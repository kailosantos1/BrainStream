(function () {
  const feed = document.querySelector('[data-estudo-feed]');
  const form = document.querySelector('[data-estudo-form]');
  const irParaFim = window.BrainStreamEstudo.irParaFim;
  irParaFim(false);

  if (!form || !feed || !window.fetch) {
    return;
  }

  const campo = form.querySelector('textarea');
  const botao = form.querySelector('[type="submit"]');
  const erro = document.querySelector('[data-estudo-erro]');
  const ajuda = document.querySelector('[data-estudo-ajuda]');
  const modeloEstudante = document.getElementById('estudo-modelo-estudante');
  const modeloDigitando = document.getElementById('estudo-modelo-digitando');
  let enviando = false;

  ajuda.textContent = 'Enter para enviar · Shift+Enter para nova linha';

  const ajustarAltura = function () {
    campo.style.height = 'auto';
    campo.style.height = Math.min(campo.scrollHeight, 160) + 'px';
  };

  const mostrarErro = function (texto) {
    erro.textContent = texto || '';
    erro.hidden = !texto;
    form.classList.toggle('is-invalid', Boolean(texto));
    if (texto) {
      campo.setAttribute('aria-invalid', 'true');
    } else {
      campo.removeAttribute('aria-invalid');
    }
  };

  const clonar = function (modelo) {
    return modelo.content.firstElementChild.cloneNode(true);
  };

  campo.addEventListener('input', function () {
    ajustarAltura();
    if (!erro.hidden) {
      mostrarErro('');
    }
  });

  campo.addEventListener('keydown', function (evento) {
    if (evento.key === 'Enter' && !evento.shiftKey && !evento.isComposing) {
      evento.preventDefault();
      form.requestSubmit();
    }
  });

  const concluirForm = document.querySelector('[data-concluir-form]');
  const concluirBotao = concluirForm ? concluirForm.querySelector('button') : null;
  const pontos = document.querySelector('[data-estudo-pontos]');

  // Enquanto o Enéas pensa: indicador de três pontos no feed e campo, envio e conclusão travados.
  const travar = function (travado) {
    enviando = travado;
    campo.disabled = travado;
    botao.disabled = travado;
    if (concluirBotao) {
      concluirBotao.disabled = travado;
    }
    form.setAttribute('aria-busy', String(travado));
  };

  const encerrar = function (html) {
    const rodape = form.parentElement;
    rodape.innerHTML = html; // aviso de sessão concluída, renderizado pelo servidor
    if (concluirForm) {
      concluirForm.remove();
    }
    const chips = document.querySelector('.estudo-chips');
    const modeloConcluido = document.getElementById('estudo-modelo-concluido');
    if (chips && modeloConcluido && !chips.querySelector('[data-estudo-concluido]')) {
      chips.firstElementChild.after(clonar(modeloConcluido));
    }
    // O histórico da lateral também passa a mostrar a sessão como concluída, sem recarregar.
    const status = document.querySelector('.painel-history-item.is-current .chip');
    if (status) {
      status.className = 'chip chip-success';
      status.textContent = 'Concluído';
    }
  };

  const enviar = function (dados, provisoria) {
    travar(true);
    mostrarErro('');
    const digitando = clonar(modeloDigitando);
    if (provisoria) {
      feed.append(provisoria);
    }
    feed.append(digitando);
    irParaFim(true);

    return fetch(form.action, {
      method: 'POST',
      body: dados,
      headers: { Accept: 'application/json' },
      credentials: 'same-origin',
    })
      .then(function (resposta) {
        return resposta.json().catch(function () { return {}; }).then(function (corpo) {
          if (!resposta.ok || !corpo.mensagens) {
            throw new Error(corpo.erro || 'Não foi possível enviar agora. Confira sua conexão e tente de novo.');
          }
          return corpo;
        });
      })
      .then(function (corpo) {
        if (provisoria) {
          provisoria.remove();
        }
        digitando.remove();
        feed.insertAdjacentHTML('beforeend', corpo.mensagens.join(''));
        if (pontos && typeof corpo.pontos === 'number') {
          pontos.textContent = corpo.pontos;
        }
        irParaFim(true);
        if (corpo.concluida) {
          encerrar(corpo.encerramento);
          return true;
        }
        return false;
      })
      .catch(function (falha) {
        if (provisoria) {
          provisoria.remove();
        }
        digitando.remove();
        mostrarErro(falha.message);
        throw falha;
      })
      .finally(function () {
        if (document.body.contains(form)) {
          travar(false);
          campo.focus();
        }
      });
  };

  form.addEventListener('submit', function (evento) {
    evento.preventDefault();
    const texto = campo.value.trim();
    if (enviando) {
      return;
    }
    if (!texto) {
      mostrarErro('Escreva sua resposta antes de enviar.');
      campo.focus();
      return;
    }
    // Mostra a mensagem na hora; a versão salva pelo servidor substitui esta ao chegar.
    const provisoria = clonar(modeloEstudante);
    provisoria.querySelector('[data-texto]').textContent = texto;
    const dados = new FormData(form);
    dados.set('conteudo', texto);
    campo.value = '';
    ajustarAltura();
    enviar(dados, provisoria).catch(function () {
      campo.value = texto;
      ajustarAltura();
    });
  });

  if (concluirForm) {
    concluirForm.addEventListener('submit', function (evento) {
      evento.preventDefault();
      if (!enviando) {
        enviar(new FormData(concluirForm), null).catch(function () { /* o erro já aparece no rodapé */ });
      }
    });
  }
}());
