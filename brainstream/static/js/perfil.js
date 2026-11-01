(function () {
  // Abre a aba indicada no endereço (#desempenho ou #conta) e mantém o endereço em sincronia ao trocar
  // de aba, para que recarregar ou compartilhar o link volte à mesma aba.
  const abas = document.querySelector('[data-perfil-abas]');
  if (!abas || !window.bootstrap) {
    return;
  }
  const porHash = { '#desempenho': 'aba-desempenho', '#conta': 'aba-conta' };

  const abrirPeloEndereco = function () {
    const id = porHash[window.location.hash];
    const aba = id ? document.getElementById(id) : null;
    if (aba) {
      window.bootstrap.Tab.getOrCreateInstance(aba).show();
    }
  };

  abas.addEventListener('shown.bs.tab', function (evento) {
    const hash = evento.target.id === 'aba-desempenho' ? '#desempenho' : '#conta';
    if (window.location.hash !== hash) {
      history.replaceState(null, '', hash);
    }
  });
  window.addEventListener('hashchange', abrirPeloEndereco);
  abrirPeloEndereco();
}());
