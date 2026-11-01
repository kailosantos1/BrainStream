(function () {
  const storageKey = 'brainstream-theme';
  const root = document.documentElement;
  const toggle = document.querySelector('#theme-toggle');
  const label = document.querySelector('[data-theme-label]');

  function applyTheme(theme) {
    const isDark = theme === 'dark';

    root.dataset.theme = theme;
    root.dataset.bsTheme = theme;

    if (toggle) {
      toggle.setAttribute('aria-pressed', String(isDark));
      toggle.setAttribute('aria-label', isDark ? 'Ativar tema claro' : 'Ativar tema escuro');
      toggle.querySelector('i').className = isDark ? 'bi bi-sun' : 'bi bi-moon-stars';
    }

    if (label) {
      label.textContent = isDark ? 'Tema escuro ativo' : 'Tema claro ativo';
    }
  }

  let currentTheme = root.dataset.theme || 'dark';
  applyTheme(currentTheme);

  if (toggle) {
    toggle.addEventListener('click', function () {
      currentTheme = currentTheme === 'dark' ? 'light' : 'dark';
      applyTheme(currentTheme);

      try {
        localStorage.setItem(storageKey, currentTheme);
      } catch (error) {
        // O tema continua funcional quando o armazenamento não está disponível.
      }
    });
  }
}());
