(function () {
  // Sugestões de tema: sem JS ficam ocultas e o campo de texto continua funcionando sozinho.
  const grupo = document.querySelector('[data-tema-sugestoes]');
  const campo = document.getElementById('id_tema');
  if (!grupo || !campo) {
    return;
  }
  const botoes = Array.from(grupo.querySelectorAll('[data-tema]'));
  const marcarAtivo = function () {
    const valor = campo.value.trim().toLocaleLowerCase('pt-BR');
    botoes.forEach(function (botao) {
      botao.setAttribute('aria-pressed', String(botao.dataset.tema.toLocaleLowerCase('pt-BR') === valor));
    });
  };
  grupo.hidden = false;
  grupo.addEventListener('click', function (evento) {
    const botao = evento.target.closest('[data-tema]');
    if (!botao) {
      return;
    }
    campo.value = botao.dataset.tema;
    marcarAtivo();
    campo.focus();
  });
  campo.addEventListener('input', marcarAtivo);
  marcarAtivo();
}());

(function () {
  // O botão do ranking só aparece com JS; sem JS a lista fica sempre visível.
  const toggle = document.querySelector('[data-ranking-toggle]');
  const lista = document.getElementById('ranking-lista');
  if (!toggle || !lista) {
    return;
  }
  toggle.hidden = false;
  lista.addEventListener('hide.bs.collapse', function () {
    toggle.querySelector('span').textContent = 'Mostrar';
    toggle.querySelector('i').className = 'bi bi-chevron-down';
  });
  lista.addEventListener('show.bs.collapse', function () {
    toggle.querySelector('span').textContent = 'Ocultar';
    toggle.querySelector('i').className = 'bi bi-chevron-up';
  });
}());

(function () {
  // Iniciar sessão: botão travado com spinner e a mensagem do modo; a camada entra se a IA demorar.
  const form = document.querySelector('[data-iniciar-form]');
  const carregando = window.BrainStreamCarregando;
  if (!form || !carregando) {
    return;
  }
  const botao = form.querySelector('[data-iniciar-botao]');
  const original = botao.innerHTML;
  form.addEventListener('submit', function (evento) {
    if (botao.disabled) {
      evento.preventDefault();
      return;
    }
    const modo = form.querySelector('input[type="radio"]:checked');
    const mensagem = modo ? modo.dataset.carregandoTexto : 'Preparando sua sessão…';
    const spinner = document.createElement('span');
    spinner.className = 'spinner-border painel-start-spinner';
    spinner.setAttribute('aria-hidden', 'true');
    botao.replaceChildren(spinner, document.createTextNode(mensagem));
    botao.disabled = true; // o botão não tem name: travá-lo não altera os dados enviados
    botao.setAttribute('aria-busy', 'true');
    carregando.mostrar(mensagem);
    carregando.aoRestaurar(function () {
      botao.innerHTML = original;
      botao.disabled = false;
      botao.removeAttribute('aria-busy');
    });
  });
}());

(function () {
  // Ranking ao vivo: busca o trecho do servidor a cada 30 s, só com a aba visível.
  // Sem JS, o ranking do carregamento continua legível; a busca não renova a sessão por inatividade.
  const lista = document.querySelector('[data-ranking-url]');
  if (!lista || !window.fetch) {
    return;
  }
  const INTERVALO_MS = 30000;
  let timer = null;
  let buscando = false;

  const agendar = function () {
    window.clearTimeout(timer);
    if (document.visibilityState === 'visible') {
      timer = window.setTimeout(atualizar, INTERVALO_MS);
    }
  };

  const atualizar = function () {
    if (buscando) {
      return;
    }
    buscando = true;
    fetch(lista.dataset.rankingUrl, { headers: { Accept: 'text/html' }, credentials: 'same-origin' })
      .then(function (resposta) {
        if (resposta.status === 401) {
          window.location.reload(); // sessão expirou: a página leva ao login
          return null;
        }
        return resposta.ok ? resposta.text() : null;
      })
      .then(function (html) {
        if (html !== null && html.trim() !== lista.innerHTML.trim()) {
          lista.innerHTML = html;
        }
      })
      .catch(function () { /* rede instável: tenta de novo no próximo ciclo */ })
      .finally(function () {
        buscando = false;
        agendar();
      });
  };

  document.addEventListener('visibilitychange', function () {
    if (document.visibilityState === 'visible') {
      atualizar(); // voltou para a aba: atualiza na hora
    } else {
      window.clearTimeout(timer);
    }
  });
  agendar();
}());
