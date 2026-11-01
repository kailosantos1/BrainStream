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
