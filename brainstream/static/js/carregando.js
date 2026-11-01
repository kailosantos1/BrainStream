(function () {
  // Navegações lentas (a IA gerando questões no servidor): o retorno imediato fica no próprio controle;
  // se a próxima página demorar mais de 500 ms, entra a camada com a marca pulsando e a mensagem.
  const camada = document.querySelector('[data-carregando-camada]');
  if (!camada) {
    return;
  }
  const texto = camada.querySelector('[data-carregando-texto]');
  const restauracoes = [];
  let espera = null;

  const mostrar = function (mensagem) {
    clearTimeout(espera);
    espera = setTimeout(function () {
      camada.hidden = false;
      texto.textContent = mensagem; // depois de exibir, para o leitor de tela anunciar
      document.body.setAttribute('aria-busy', 'true');
    }, 500);
  };

  const limpar = function () {
    clearTimeout(espera);
    camada.hidden = true;
    texto.textContent = '';
    document.body.removeAttribute('aria-busy');
    restauracoes.splice(0).forEach(function (restaurar) { restaurar(); });
  };

  // Ao voltar pelo histórico do navegador (bfcache), a página não pode reaparecer travada.
  window.addEventListener('pageshow', function (evento) {
    if (evento.persisted) {
      limpar();
    }
  });

  document.addEventListener('click', function (evento) {
    const link = evento.target.closest('a[data-carregando]');
    if (!link || evento.defaultPrevented || evento.button !== 0 || evento.metaKey || evento.ctrlKey
        || evento.shiftKey || evento.altKey || link.getAttribute('aria-current') === 'page') {
      return;
    }
    mostrar(link.dataset.carregando);
  });

  window.BrainStreamCarregando = {
    mostrar: mostrar,
    aoRestaurar: function (restaurar) { restauracoes.push(restaurar); },
  };
}());
