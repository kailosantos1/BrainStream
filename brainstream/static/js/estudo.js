// Comportamento comum das telas de estudo: lateral recolhível e rolagem até a última mensagem.
window.BrainStreamEstudo = (function () {
  const layout = document.querySelector('[data-estudo-layout]');
  const scroll = document.querySelector('[data-estudo-scroll]');
  const reduzMovimento = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  const irParaFim = function (suave) {
    if (scroll) {
      scroll.scrollTo({ top: scroll.scrollHeight, behavior: suave && !reduzMovimento ? 'smooth' : 'auto' });
    }
  };

  // Rola só a área da conversa (scrollIntoView também rolaria a janela e esconderia o topo).
  const irPara = function (elemento) {
    if (scroll && elemento) {
      const topo = scroll.scrollTop + elemento.getBoundingClientRect().top - scroll.getBoundingClientRect().top - 16;
      scroll.scrollTo({ top: topo, behavior: reduzMovimento ? 'auto' : 'smooth' });
    }
  };

  // Em telas largas a lateral pode ser recolhida; a preferência fica salva entre sessões.
  if (layout) {
    const recolher = layout.querySelector('[data-side-collapse]');
    const expandir = layout.querySelector('[data-side-expand]');
    const aplicar = function (recolhida, focar) {
      layout.classList.toggle('is-side-collapsed', recolhida);
      recolher.setAttribute('aria-expanded', String(!recolhida));
      expandir.setAttribute('aria-expanded', String(!recolhida));
      try {
        localStorage.setItem('brainstream-lateral', recolhida ? 'recolhida' : 'aberta');
      } catch (erro) { /* armazenamento indisponível: só não lembra a escolha */ }
      if (focar) {
        (recolhida ? expandir : recolher).focus();
      }
    };
    let salva = null;
    try {
      salva = localStorage.getItem('brainstream-lateral');
    } catch (erro) { /* idem */ }
    aplicar(salva === 'recolhida', false);
    recolher.addEventListener('click', function () { aplicar(true, true); });
    expandir.addEventListener('click', function () { aplicar(false, true); });
  }

  return { irParaFim: irParaFim, irPara: irPara };
}());
