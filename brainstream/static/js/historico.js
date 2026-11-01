(function () {
  // Exclusão no histórico: a lixeira abre uma confirmação no próprio item; só "Excluir" envia o POST.
  document.querySelectorAll('[data-excluir-sessao]').forEach(function (form) {
    const lixeira = form.querySelector('[data-excluir-botao]');
    const confirmacao = form.querySelector('[data-excluir-confirmacao]');
    const confirmar = form.querySelector('[data-excluir-confirmar]');
    const cancelar = form.querySelector('[data-excluir-cancelar]');
    const item = form.closest('.painel-history-item');
    lixeira.setAttribute('aria-expanded', 'false');
    lixeira.setAttribute('aria-controls', confirmacao.id);

    const abrir = function (aberta) {
      confirmacao.hidden = !aberta;
      lixeira.setAttribute('aria-expanded', String(aberta));
      item.classList.toggle('is-confirming', aberta);
      (aberta ? cancelar : lixeira).focus(); // foco seguro: Enter por engano não exclui
    };

    lixeira.addEventListener('click', function (evento) {
      evento.preventDefault();
      abrir(confirmacao.hidden);
    });
    cancelar.addEventListener('click', function () {
      abrir(false);
    });
    form.addEventListener('keydown', function (evento) {
      if (evento.key === 'Escape' && !confirmacao.hidden) {
        evento.stopPropagation(); // não fecha o offcanvas do celular junto
        abrir(false);
      }
    });
    form.addEventListener('submit', function (evento) {
      if (confirmacao.hidden) {
        evento.preventDefault();
        return;
      }
      confirmar.disabled = true;
      cancelar.disabled = true;
      confirmar.textContent = 'Excluindo…';
      item.classList.add('is-removing');
    });
  });

  // Ao voltar pelo histórico do navegador, um item em "Excluindo…" já foi removido: recarrega a lista.
  window.addEventListener('pageshow', function (evento) {
    if (evento.persisted && document.querySelector('.painel-history-item.is-removing')) {
      window.location.reload();
    }
  });

  // Avisos flutuantes das telas de estudo somem sozinhos.
  document.querySelectorAll('[data-aviso]').forEach(function (aviso) {
    window.setTimeout(function () {
      aviso.classList.add('is-leaving');
      window.setTimeout(function () { aviso.remove(); }, 250);
    }, 6000);
  });
}());
