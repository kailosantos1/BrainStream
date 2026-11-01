(function () {
  // Mostrar/ocultar senha: o botão só aparece com JS, então sem JS o campo segue funcional.
  document.querySelectorAll('[data-reveal-password]').forEach(function (button) {
    const input = document.getElementById(button.getAttribute('aria-controls'));
    if (!input) {
      return;
    }
    button.hidden = false;
    button.addEventListener('click', function () {
      const visible = input.type === 'password';
      input.type = visible ? 'text' : 'password';
      button.setAttribute('aria-pressed', String(visible));
      button.setAttribute('aria-label', visible ? 'Ocultar senha' : 'Mostrar senha');
      button.querySelector('i').className = visible ? 'bi bi-eye-slash' : 'bi bi-eye';
    });
  });

  // Estado de envio: evita duplo clique e mostra progresso.
  document.querySelectorAll('[data-auth-form]').forEach(function (form) {
    form.addEventListener('submit', function () {
      const submit = form.querySelector('[type="submit"]');
      if (!submit || submit.disabled) {
        return;
      }
      form.querySelectorAll('[data-reveal-password]').forEach(function (button) {
        const input = document.getElementById(button.getAttribute('aria-controls'));
        if (input) {
          input.type = 'password';
        }
      });
      submit.dataset.label = submit.innerHTML;
      submit.setAttribute('aria-busy', 'true');
      submit.innerHTML = '<span class="spinner-border" aria-hidden="true"></span>' + submit.dataset.busyLabel;
      // Desabilita depois do envio começar para não cancelar a submissão.
      window.setTimeout(function () {
        submit.disabled = true;
      }, 0);
    });
  });

  // Ao voltar pelo histórico (bfcache), o botão volta ao estado normal.
  window.addEventListener('pageshow', function (event) {
    if (!event.persisted) {
      return;
    }
    document.querySelectorAll('[data-auth-form] [aria-busy="true"]').forEach(function (submit) {
      submit.disabled = false;
      submit.removeAttribute('aria-busy');
      submit.innerHTML = submit.dataset.label;
    });
  });
}());
