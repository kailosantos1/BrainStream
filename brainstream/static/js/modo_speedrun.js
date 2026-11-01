(function () {
  const estudo = window.BrainStreamEstudo;
  const feed = document.querySelector('[data-estudo-feed]');
  const pontos = document.querySelector('[data-estudo-pontos]');
  const timer = document.querySelector('[data-speedrun-timer]');
  const form = document.querySelector('[data-speedrun-form]');
  const inicio = document.querySelector('[data-speedrun-iniciar]');
  const erro = document.querySelector('[data-speedrun-erro]');
  const dica = document.querySelector('[data-speedrun-dica]');
  const botaoSom = document.querySelector('[data-speedrun-som]');
  const reduzMovimento = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  estudo.irParaFim(false);

  if (!form || !timer || !window.fetch) {
    return; // sem JS os formulários enviam normalmente e o servidor confere o prazo
  }

  // ---------- Som (Web Audio, sintetizado na hora) e vibração ----------
  const som = (function () {
    const CHAVE = 'brainstream-speedrun-som';
    const Contexto = window.AudioContext || window.webkitAudioContext;
    let contexto = null;
    let ligado = true;
    try {
      ligado = localStorage.getItem(CHAVE) !== 'mudo';
    } catch (falha) { /* sem armazenamento: começa ligado */ }

    const atualizarBotao = function () {
      if (!botaoSom) {
        return;
      }
      botaoSom.setAttribute('aria-pressed', String(ligado));
      botaoSom.title = ligado ? 'Silenciar efeitos sonoros' : 'Ativar efeitos sonoros';
      botaoSom.querySelector('i').className = ligado ? 'bi bi-volume-up' : 'bi bi-volume-mute';
    };

    // Navegadores só liberam áudio depois de um gesto do usuário: chamado no clique em "Iniciar".
    const preparar = function () {
      if (!Contexto) {
        return;
      }
      contexto = contexto || new Contexto();
      if (contexto.state === 'suspended') {
        contexto.resume();
      }
    };

    const tom = function (frequencia, inicioS, duracaoS, opcoes) {
      const config = opcoes || {};
      const t0 = contexto.currentTime + inicioS;
      const oscilador = contexto.createOscillator();
      const ganho = contexto.createGain();
      oscilador.type = config.forma || 'sine';
      oscilador.frequency.setValueAtTime(frequencia, t0);
      if (config.ate) {
        oscilador.frequency.exponentialRampToValueAtTime(config.ate, t0 + duracaoS);
      }
      // Envelope curto (ataque rápido, queda exponencial) para não estalar.
      ganho.gain.setValueAtTime(0.0001, t0);
      ganho.gain.exponentialRampToValueAtTime(config.volume || 0.12, t0 + 0.012);
      ganho.gain.exponentialRampToValueAtTime(0.0001, t0 + duracaoS);
      oscilador.connect(ganho).connect(contexto.destination);
      oscilador.start(t0);
      oscilador.stop(t0 + duracaoS + 0.02);
    };

    const tocar = function (efeito) {
      if (!ligado || !contexto || contexto.state !== 'running') {
        return;
      }
      if (efeito === 'acerto') {
        tom(660, 0, 0.11); // dois tons ascendentes (Mi → Lá)
        tom(880, 0.09, 0.16);
      } else if (efeito === 'erro') {
        tom(330, 0, 0.28, { forma: 'triangle', ate: 180, volume: 0.14 });
      } else if (efeito === 'tique') {
        tom(1200, 0, 0.035, { forma: 'square', volume: 0.025 });
      }
    };

    const vibrar = function (padrao) {
      if (navigator.vibrate) {
        navigator.vibrate(padrao);
      }
    };

    if (botaoSom) {
      botaoSom.hidden = false;
      atualizarBotao();
      botaoSom.addEventListener('click', function () {
        ligado = !ligado;
        try {
          localStorage.setItem(CHAVE, ligado ? 'ligado' : 'mudo');
        } catch (falha) { /* só não lembra a escolha */ }
        if (ligado) {
          preparar();
        }
        atualizarBotao();
      });
    }

    return {
      preparar: preparar,
      acerto: function () { tocar('acerto'); vibrar(50); },
      erro: function () { tocar('erro'); vibrar([80, 40, 80]); },
      tique: function () { tocar('tique'); },
    };
  }());

  // ---------- Relógio ----------
  const TEMPO_ESGOTADO = 'tempo';
  const limiteMs = Number(timer.dataset.limite) * 1000;
  const numero = timer.querySelector('[data-speedrun-segundos]');
  const barra = timer.querySelector('[data-speedrun-barra]');
  const aviso = timer.querySelector('[data-speedrun-aviso]');
  const ordem = form.querySelector('[data-speedrun-ordem]');
  const botoes = Array.from(form.querySelectorAll('button[name="resposta"]'));
  let fim = 0;
  let quadro = null;
  let ultimoSegundo = null;
  let enviando = false;

  const pintar = function (restante) {
    const segundos = Math.ceil(restante / 1000);
    if (segundos !== ultimoSegundo) {
      const primeiraPintura = ultimoSegundo === null;
      ultimoSegundo = segundos;
      numero.textContent = segundos;
      timer.classList.toggle('is-warning', segundos <= 5 && segundos > 3);
      timer.classList.toggle('is-urgent', segundos <= 3);
      if (segundos === 5 || segundos === 3) {
        aviso.textContent = segundos + ' segundos';
      }
      if (segundos >= 1 && segundos <= 3 && !primeiraPintura) {
        som.tique();
      }
      if (reduzMovimento) {
        barra.style.transform = 'scaleX(' + Math.min(segundos * 1000 / limiteMs, 1) + ')';
      }
    }
    if (!reduzMovimento) {
      barra.style.transform = 'scaleX(' + Math.min(restante / limiteMs, 1) + ')';
    }
  };

  const parar = function () {
    if (quadro) {
      cancelAnimationFrame(quadro);
      quadro = null;
    }
  };

  const tique = function () {
    const restante = Math.max(fim - performance.now(), 0);
    pintar(restante);
    if (restante === 0) {
      quadro = null;
      aviso.textContent = 'Tempo esgotado';
      enviar(TEMPO_ESGOTADO, null);
      return;
    }
    quadro = requestAnimationFrame(tique);
  };

  const iniciarRelogio = function (restanteMs) {
    parar();
    ultimoSegundo = null;
    fim = performance.now() + restanteMs;
    tique();
  };

  // ---------- Envio ----------
  const mostrarErro = function (texto) {
    erro.textContent = texto || '';
    erro.hidden = !texto;
  };

  const travar = function (travado, escolhido) {
    botoes.forEach(function (botao) {
      botao.disabled = travado;
      botao.classList.toggle('is-sending', travado && botao === escolhido);
    });
  };

  const atualizarDica = function () {
    // Atalhos só fazem sentido com teclado físico; em telas de toque a dica fica sem eles.
    const atalhos = window.matchMedia('(hover: hover) and (pointer: fine)').matches
      ? ' · atalhos: V (Verdadeiro) e F (Falso)' : '';
    dica.textContent = (limiteMs / 1000) + ' segundos por afirmação' + atalhos;
  };

  const encerrar = function () {
    timer.hidden = true;
    form.remove();
    dica.textContent = 'Speedrun concluído. Seus pontos já aparecem no painel.';
  };

  const postar = function (dados) {
    return fetch(form.action, {
      method: 'POST',
      body: dados,
      headers: { Accept: 'application/json' },
      credentials: 'same-origin',
    }).then(function (resposta) {
      return resposta.json().catch(function () { return {}; }).then(function (corpo) {
        if (resposta.status === 409) {
          window.location.reload(); // a tela ficou para trás (outra aba ou reenvio): recarrega o estado real
          return null;
        }
        if (!resposta.ok || typeof corpo.novas !== 'string') {
          throw new Error(corpo.erro || 'Não foi possível enviar. Confira a conexão e tente de novo.');
        }
        return corpo;
      });
    });
  };

  const acrescentar = function (html) {
    const molde = document.createElement('template');
    molde.innerHTML = html;
    const chegaram = Array.from(molde.content.children);
    chegaram.forEach(function (item) { item.classList.add('estudo-entrando'); });
    feed.append.apply(feed, chegaram);
    return chegaram;
  };

  const comecar = function (restanteMs, proxima) {
    ordem.value = proxima;
    timer.hidden = false;
    form.hidden = false;
    travar(false, null);
    atualizarDica();
    iniciarRelogio(restanteMs);
  };

  function enviar(valor, botao) {
    if (enviando) {
      return;
    }
    enviando = true;
    parar();
    travar(true, botao);
    mostrarErro('');

    const dados = new FormData(form);
    dados.set('resposta', valor);
    postar(dados)
      .then(function (corpo) {
        if (!corpo) {
          return;
        }
        if (corpo.acertou) {
          som.acerto();
        } else {
          som.erro();
        }
        const chegaram = acrescentar(corpo.novas);
        pontos.textContent = corpo.pontos;
        estudo.irPara(chegaram.find(function (item) { return item.id.indexOf('feedback-') === 0; }));
        enviando = false;
        if (corpo.concluida) {
          encerrar();
          const voltar = document.querySelector('#estudo-final a');
          if (voltar) {
            voltar.focus({ preventScroll: true });
          }
          return;
        }
        comecar(corpo.restante_ms, corpo.proxima);
      })
      .catch(function (falha) {
        enviando = false;
        travar(false, null);
        mostrarErro(falha.message);
        // O prazo continua correndo no servidor; o relógio segue de onde estava.
        if (valor !== TEMPO_ESGOTADO) {
          quadro = requestAnimationFrame(tique);
        }
      });
  }

  form.addEventListener('submit', function (evento) {
    evento.preventDefault();
    if (evento.submitter) {
      enviar(evento.submitter.value, evento.submitter);
    }
  });

  // Atalhos: V para Verdadeiro e F para Falso (fora de campos de texto e só com o relógio correndo).
  document.addEventListener('keydown', function (evento) {
    const tecla = evento.key.toLowerCase();
    if ((tecla !== 'v' && tecla !== 'f') || evento.ctrlKey || evento.metaKey || evento.altKey || form.hidden
        || /input|textarea|select/i.test(evento.target.tagName) || !document.body.contains(form)) {
      return;
    }
    const botao = botoes.find(function (item) { return item.value === tecla.toUpperCase(); });
    if (botao && !botao.disabled) {
      evento.preventDefault();
      enviar(botao.value, botao);
    }
  });

  // ---------- Início ----------
  if (inicio) {
    inicio.addEventListener('submit', function (evento) {
      evento.preventDefault();
      const botao = inicio.querySelector('button');
      if (botao.disabled) {
        return;
      }
      botao.disabled = true;
      som.preparar(); // o clique é o gesto que libera o áudio
      mostrarErro('');
      postar(new FormData(inicio))
        .then(function (corpo) {
          if (!corpo) {
            return;
          }
          inicio.closest('li').remove();
          const chegaram = acrescentar(corpo.novas);
          estudo.irPara(chegaram[0]);
          comecar(corpo.restante_ms, corpo.proxima);
          botoes[0].focus({ preventScroll: true });
        })
        .catch(function (falha) {
          botao.disabled = false;
          mostrarErro(falha.message);
        });
    });
  } else if (timer.dataset.restante !== '') {
    // Speedrun já em andamento (página recarregada): o relógio retoma o tempo que resta no servidor,
    // e o áudio é liberado no primeiro toque ou tecla (sem gesto, o navegador o mantém suspenso).
    document.addEventListener('pointerdown', som.preparar, { once: true });
    document.addEventListener('keydown', som.preparar, { once: true });
    atualizarDica();
    iniciarRelogio(Number(timer.dataset.restante));
  }
}());
