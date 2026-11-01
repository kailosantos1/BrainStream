(function () {
  const motionPreference = window.matchMedia('(prefers-reduced-motion: reduce)');
  const finePointer = window.matchMedia('(hover: hover) and (pointer: fine)');
  const header = document.querySelector('.site-header');

  function clamp(value) {
    return Math.min(1, Math.max(0, value));
  }

  function phase(progress, start, end) {
    return clamp((progress - start) / (end - start));
  }

  function easeInOut(t) {
    return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
  }

  function reduced() {
    return motionPreference.matches;
  }

  // ---------- Motor: um único requestAnimationFrame por evento ----------
  // Efeitos leem geometria e escrevem variáveis CSS; tweens curtos (contadores)
  // pedem novos frames só enquanto estão ativos.
  const effects = [];
  const tweens = [];
  let frame = null;

  function scheduleFrame() {
    if (frame === null) frame = window.requestAnimationFrame(updateFrame);
  }

  function updateFrame(now) {
    frame = null;
    effects.forEach(function (effect) { effect(); });
    for (let index = tweens.length - 1; index >= 0; index -= 1) {
      const tween = tweens[index];
      if (tween.start === null) tween.start = now;
      const t = clamp((now - tween.start) / tween.duration);
      tween.step(1 - Math.pow(1 - t, 3));
      if (t >= 1) tweens.splice(index, 1);
    }
    if (tweens.length) scheduleFrame();
  }

  function addTween(duration, step) {
    tweens.push({ duration: duration, step: step, start: null });
    scheduleFrame();
  }

  function trackProgress(track) {
    const bounds = track.getBoundingClientRect();
    return clamp(-bounds.top / Math.max(1, bounds.height - window.innerHeight));
  }

  function scrollToProgress(track, progress, behavior) {
    const bounds = track.getBoundingClientRect();
    const top = window.scrollY + bounds.top + progress * (bounds.height - window.innerHeight);
    window.scrollTo({ top: Math.round(top), behavior: behavior });
  }

  effects.push(function () {
    header?.classList.toggle('is-scrolled', window.scrollY > 12);
  });

  // ---------- Entradas por partes, uma vez, e contadores ----------
  const reveals = Array.from(document.querySelectorAll('[data-reveal]'));

  function countUp(root) {
    root.querySelectorAll('[data-count]').forEach(function (element) {
      const target = Number(element.dataset.count);
      const suffix = element.dataset.suffix || '';
      addTween(900, function (t) { element.textContent = Math.round(target * t) + suffix; });
    });
  }

  if (reveals.length && !reduced() && 'IntersectionObserver' in window) {
    const counters = new Map();
    reveals.forEach(function (element) {
      const section = element.closest('section') || document.body;
      const index = counters.get(section) || 0;
      counters.set(section, index + 1);
      element.style.setProperty('--reveal-delay', (index * 70) + 'ms');
    });
    const revealObserver = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        entry.target.classList.add('is-in');
        countUp(entry.target);
        revealObserver.unobserve(entry.target);
      });
    }, { rootMargin: '0px 0px -10% 0px', threshold: 0.1 });
    reveals.forEach(function (element) { revealObserver.observe(element); });
  } else {
    reveals.forEach(function (element) { element.classList.add('is-in'); });
  }

  // ---------- Hero + tour: uma janela, uma cena ----------
  const story = document.querySelector('[data-story]');
  const storyTrack = document.querySelector('[data-story-track]');
  const storyVisual = document.querySelector('[data-story-visual]');
  const rig = document.querySelector('[data-hero-rig]');
  const tourWindow = document.querySelector('[data-tour-window]');
  const steps = Array.from(document.querySelectorAll('[data-tour-step]'));
  const sceneQuery = window.matchMedia('(min-width: 992px) and (min-height: 700px)');
  // Fases da cena (fração do trilho): herói, aterrissagem e quatro passos.
  const TOUR_START = 0.34;
  const STEP_SIZE = (1 - TOUR_START) / 4;
  let sceneOn = false;
  let storyVisible = true;
  let userChoseStep = false;
  let inHeroPhase = true;
  let tilt = null;

  function setTourState(state, touring) {
    if (!tourWindow) return;
    if (state === null) {
      delete tourWindow.dataset.state;
    } else {
      tourWindow.dataset.state = String(state);
    }
    tourWindow.classList.toggle('is-touring', Boolean(touring));
    steps.forEach(function (step) {
      if (touring && Number(step.dataset.tourStep) === state) {
        step.setAttribute('aria-current', 'step');
      } else {
        step.removeAttribute('aria-current');
      }
    });
  }

  // A conversa do hero acontece sozinha: pergunta, digitando, resposta, dica, insight.
  const autoplay = (function () {
    const script = [
      { state: 1, wait: 1100 },
      { typing: true, wait: 1300 },
      { state: 2, wait: 2600 },
      { state: 3, wait: 2600 },
      { typing: true, wait: 1100 },
      { state: 4, wait: 3600 }
    ];
    let timer = null;
    let index = 0;

    function run() {
      const item = script[index];
      if (item.state) setTourState(item.state, false);
      tourWindow.classList.toggle('is-typing', Boolean(item.typing));
      index = (index + 1) % script.length;
      timer = window.setTimeout(run, item.wait);
    }

    return {
      start: function () {
        if (timer !== null || !tourWindow || reduced()) return;
        index = 0;
        run();
      },
      stop: function () {
        window.clearTimeout(timer);
        timer = null;
        tourWindow?.classList.remove('is-typing');
      }
    };
  }());

  function syncAutoplay() {
    const allowed = storyVisible && !userChoseStep && !reduced() && (!sceneOn || inHeroPhase);
    if (allowed) autoplay.start(); else autoplay.stop();
  }

  function stepTarget(index) {
    return TOUR_START + (index - 0.5) * STEP_SIZE;
  }

  function updateStory() {
    if (!sceneOn || !story || !storyTrack) return;
    const p = trackProgress(storyTrack);
    const land = easeInOut(phase(p, 0.1, 0.3));
    const tourIn = phase(p, 0.26, 0.34);
    story.style.setProperty('--copy-out', phase(p, 0.08, 0.2).toFixed(4));
    story.style.setProperty('--floats-out', phase(p, 0.06, 0.2).toFixed(4));
    story.style.setProperty('--land', land.toFixed(4));
    story.style.setProperty('--tour-in', tourIn.toFixed(4));
    story.classList.toggle('is-landed', land > 0.5);
    story.classList.toggle('is-touring', tourIn > 0.5);

    const wasHero = inHeroPhase;
    inHeroPhase = p < 0.06;
    if (!inHeroPhase) {
      if (tilt) { tilt = null; rig?.style.setProperty('--tilt-x', '0deg'); rig?.style.setProperty('--tilt-y', '0deg'); }
      const raw = (p - TOUR_START) / STEP_SIZE;
      const index = Math.min(4, Math.max(1, Math.floor(raw) + 1));
      const active = steps[index - 1];
      setTourState(index, tourIn > 0.5);
      active?.style.setProperty('--step-progress', clamp(raw - (index - 1)).toFixed(3));
    }
    if (wasHero !== inHeroPhase) syncAutoplay();
  }

  effects.push(updateStory);

  // Paralaxe sutil no ponteiro (2–4°), só no hero, com mouse e com movimento permitido.
  if (storyVisual && rig) {
    storyVisual.addEventListener('pointermove', function (event) {
      if (!sceneOn || !inHeroPhase || !finePointer.matches || reduced()) return;
      const bounds = storyVisual.getBoundingClientRect();
      tilt = {
        x: ((event.clientY - bounds.top) / bounds.height - 0.5) * -5,
        y: ((event.clientX - bounds.left) / bounds.width - 0.5) * 7
      };
      rig.style.setProperty('--tilt-x', tilt.x.toFixed(2) + 'deg');
      rig.style.setProperty('--tilt-y', tilt.y.toFixed(2) + 'deg');
    });
    storyVisual.addEventListener('pointerleave', function () {
      tilt = null;
      rig.style.setProperty('--tilt-x', '0deg');
      rig.style.setProperty('--tilt-y', '0deg');
    });
  }

  function chooseStep(index) {
    if (sceneOn) {
      // O palco é fixo: o salto instantâneo só troca o estado da janela.
      scrollToProgress(storyTrack, stepTarget(index), 'instant');
      return;
    }
    userChoseStep = true;
    syncAutoplay();
    setTourState(index, true);
    const bounds = tourWindow.getBoundingClientRect();
    if (bounds.top < 0 || bounds.bottom > window.innerHeight) {
      tourWindow.scrollIntoView({ block: 'center', behavior: reduced() ? 'instant' : 'smooth' });
    }
  }

  steps.forEach(function (step) {
    step.addEventListener('click', function () { chooseStep(Number(step.dataset.tourStep)); });
    // Foco tem prioridade: um passo focado fora da fase do tour leva o scroll até ele.
    step.addEventListener('focus', function () {
      if (sceneOn && !story.classList.contains('is-touring')) chooseStep(Number(step.dataset.tourStep));
    });
  });

  story?.querySelector('[data-story-copy]')?.addEventListener('focusin', function () {
    if (sceneOn && story.classList.contains('is-landed')) scrollToProgress(storyTrack, 0, 'instant');
  });

  document.querySelectorAll('a[href="#como-funciona"]').forEach(function (link) {
    link.addEventListener('click', function (event) {
      if (!sceneOn) return;
      event.preventDefault();
      scrollToProgress(storyTrack, stepTarget(1), reduced() ? 'instant' : 'smooth');
    });
  });

  if (story && 'IntersectionObserver' in window) {
    new IntersectionObserver(function (entries) {
      storyVisible = entries[0].isIntersecting;
      syncAutoplay();
    }).observe(story);
  }

  function configureStory() {
    if (!story) return;
    sceneOn = sceneQuery.matches && !reduced();
    story.classList.toggle('is-scene', sceneOn);
    if (!sceneOn) {
      ['--copy-out', '--floats-out', '--land', '--tour-in'].forEach(function (name) { story.style.removeProperty(name); });
      story.classList.remove('is-landed', 'is-touring');
      inHeroPhase = true;
      // Movimento reduzido sem escolha do usuário: a conversa inteira, já concluída.
      if (reduced() && !userChoseStep) setTourState(null, false);
    }
    syncAutoplay();
  }

  window.requestAnimationFrame(function () { story?.classList.add('is-ready'); });

  // ---------- Modos: abas com indicador deslizante ----------
  const seg = document.querySelector('[data-seg]');
  const segTabs = Array.from(document.querySelectorAll('[data-seg-tab]'));
  const segIndicator = seg?.querySelector('.seg-indicator');
  let onModeChange = function () {};

  function placeIndicator() {
    const active = segTabs.find(function (tab) { return tab.getAttribute('aria-selected') === 'true'; });
    if (!active || !segIndicator) return;
    segIndicator.style.setProperty('--seg-x', active.offsetLeft + 'px');
    segIndicator.style.setProperty('--seg-w', active.offsetWidth + 'px');
  }

  function selectMode(tab, focus) {
    segTabs.forEach(function (item) {
      const active = item === tab;
      item.setAttribute('aria-selected', String(active));
      item.tabIndex = active ? 0 : -1;
      document.getElementById(item.getAttribute('aria-controls'))?.classList.toggle('is-active', active);
    });
    if (focus) tab.focus();
    placeIndicator();
    onModeChange(tab.getAttribute('aria-controls'));
  }

  segTabs.forEach(function (tab, index) {
    tab.addEventListener('click', function () { selectMode(tab, false); });
    tab.addEventListener('keydown', function (event) {
      const keys = { ArrowRight: 1, ArrowLeft: -1, Home: 'first', End: 'last' };
      if (!(event.key in keys)) return;
      event.preventDefault();
      const move = keys[event.key];
      const next = move === 'first' ? 0 : move === 'last' ? segTabs.length - 1 : (index + move + segTabs.length) % segTabs.length;
      selectMode(segTabs[next], true);
    });
  });

  if (segTabs.length) selectMode(segTabs[0], false);

  function feedback(container, tone, message, actionLabel, action) {
    container.textContent = '';
    const box = document.createElement('p');
    box.className = 'feedback feedback-' + tone;
    const text = document.createElement('span');
    const lead = document.createElement('b');
    lead.textContent = message[0];
    text.append(lead, ' ' + message[1]);
    box.append(text);
    if (actionLabel) {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'btn btn-ghost';
      button.textContent = actionLabel;
      button.addEventListener('click', action);
      box.append(button);
    }
    container.append(box);
  }

  // ---------- Quiz: escolha, feedback e nova tentativa ----------
  const quiz = document.querySelector('[data-quiz]');
  const quizOptions = Array.from(document.querySelectorAll('[data-quiz-option]'));
  const quizFeedback = document.querySelector('[data-quiz-feedback]');

  function resetQuiz() {
    quizOptions.forEach(function (option) {
      option.disabled = false;
      option.classList.remove('is-correct', 'is-wrong');
    });
    quizFeedback.textContent = '';
    quizOptions[0]?.focus();
  }

  quizOptions.forEach(function (option) {
    option.addEventListener('click', function () {
      const right = option.hasAttribute('data-correct');
      quizOptions.forEach(function (item) { item.disabled = true; });
      option.classList.add(right ? 'is-correct' : 'is-wrong');
      if (right) {
        feedback(quizFeedback, 'success', ['Correto. +10 pontos.', 'As folhas absorvem gás carbônico e, com luz e água, produzem açúcar e oxigênio.'], 'Refazer', resetQuiz);
      } else {
        feedback(quizFeedback, 'warning', ['Ainda não.', 'Pense no gás que sai quando expiramos.'], 'Tentar de novo', resetQuiz);
      }
    });
  });

  // ---------- Speedrun: como o modo real, 5 afirmações com 10 s cada e 10 pontos por acerto ----------
  // O relógio começa na primeira resposta e só corre com a aba visível e a seção na tela.
  const speed = document.querySelector('[data-speedrun]');
  const statements = [
    ['A Lua tem luz própria.', false],
    ['A água ferve a 100 °C ao nível do mar.', true],
    ['Os mamíferos respiram por pulmões.', true],
    ['O Brasil fica inteiramente no hemisfério norte.', false],
    ['A fotossíntese libera oxigênio.', true],
    ['O Sol é um planeta.', false]
  ];
  const speedClock = document.querySelector('[data-speed-clock]');
  const speedScore = document.querySelector('[data-speed-score]');
  const speedBar = document.querySelector('[data-speed-bar]');
  const speedStatement = document.querySelector('[data-speed-statement]');
  const speedFeedback = document.querySelector('[data-speed-feedback]');
  const speedButtons = Array.from(document.querySelectorAll('[data-speed-answer]'));
  const SPEED_TIME = 10;
  const SPEED_ROUND = 5;
  const SPEED_POINTS = 10;
  let speedLeft = SPEED_TIME;
  let speedIndex = 0;
  let speedDone = 0;
  let speedPoints = 0;
  let speedStarted = false;
  let speedOver = false;
  let speedTimer = null;
  let modesVisible = false;
  let speedActive = false;

  function renderSpeed() {
    speedClock.textContent = '0:' + String(speedLeft).padStart(2, '0');
    speedScore.textContent = String(speedPoints);
    speedBar.style.setProperty('--value', String(speedLeft / SPEED_TIME));
    speedStatement.textContent = statements[speedIndex][0];
  }

  function syncSpeedClock() {
    const run = speedStarted && !speedOver && speedActive && modesVisible;
    if (run && speedTimer === null) {
      speedTimer = window.setInterval(function () {
        speedLeft -= 1;
        if (speedLeft > 0) {
          renderSpeed();
          return;
        }
        const truth = statements[speedIndex][1];
        feedback(speedFeedback, 'warning', ['Tempo esgotado.', 'A afirmação era ' + (truth ? 'verdadeira.' : 'falsa.')]);
        nextStatement();
      }, 1000);
    } else if (!run && speedTimer !== null) {
      window.clearInterval(speedTimer);
      speedTimer = null;
    }
  }

  function nextStatement() {
    speedDone += 1;
    if (speedDone >= SPEED_ROUND) {
      speedOver = true;
      speedLeft = 0;
      speedButtons.forEach(function (button) { button.disabled = true; });
      renderSpeed();
      syncSpeedClock();
      feedback(speedFeedback, 'success', ['Fim do Speedrun.', 'Você fez ' + speedPoints + ' pontos.'], 'Jogar de novo', resetSpeed);
      return;
    }
    speedIndex = (speedIndex + 1) % statements.length;
    speedLeft = SPEED_TIME; // cada afirmação tem os próprios 10 segundos
    renderSpeed();
    syncSpeedClock();
  }

  function resetSpeed() {
    speedLeft = SPEED_TIME;
    speedIndex = 0;
    speedDone = 0;
    speedPoints = 0;
    speedStarted = false;
    speedOver = false;
    speedFeedback.textContent = '';
    speedButtons.forEach(function (button) { button.disabled = false; button.classList.remove('is-correct', 'is-wrong'); });
    renderSpeed();
    syncSpeedClock();
    speedButtons[0]?.focus();
  }

  speedButtons.forEach(function (button) {
    button.addEventListener('click', function () {
      if (speedOver) return;
      speedStarted = true;
      const truth = statements[speedIndex][1];
      const right = (button.dataset.speedAnswer === 'true') === truth;
      if (right) speedPoints += SPEED_POINTS;
      speedButtons.forEach(function (item) { item.classList.remove('is-correct', 'is-wrong'); });
      button.classList.add(right ? 'is-correct' : 'is-wrong');
      feedback(speedFeedback, right ? 'success' : 'warning',
        right ? ['Certo. +10 pontos.', 'Próxima afirmação.'] : ['Errado.', 'A afirmação era ' + (truth ? 'verdadeira.' : 'falsa.')]);
      window.setTimeout(function () { button.classList.remove('is-correct', 'is-wrong'); }, reduced() ? 0 : 450);
      nextStatement();
    });
  });

  if (speed) {
    onModeChange = function (panelId) {
      speedActive = panelId === speed.id;
      syncSpeedClock();
    };
    const modesSection = speed.closest('section');
    if ('IntersectionObserver' in window && modesSection) {
      new IntersectionObserver(function (entries) {
        modesVisible = entries[0].isIntersecting;
        syncSpeedClock();
      }).observe(modesSection);
    } else {
      modesVisible = true;
    }
  }

  // ---------- Pergunte ao Enéas (respostas pré-escritas) ----------
  const askForm = document.querySelector('[data-ask-form]');
  const askInput = document.querySelector('[data-ask-input]');
  const askQuestion = document.querySelector('[data-ask-question]');
  const askReply = document.querySelector('[data-ask-reply]');
  const askChat = askReply?.closest('.chat');
  const replies = {
    'por que o céu é azul?': 'Boa pergunta. Quando a luz do Sol atravessa o ar, o que você acha que acontece com as cores que formam essa luz?',
    'como funciona a fotossíntese?': 'Vamos por partes: do que uma planta precisa para crescer, e de onde vem cada uma dessas coisas?',
    'o que causou a revolução francesa?': 'Pense na França de 1789: quem pagava a maior parte dos impostos, e quem tinha os privilégios?',
    'quanto é 7 × 8?': 'Você sabe quanto é 7 × 7? O que acontece se você somar mais um 7?'
  };
  let askTimer = null;
  let typeTimer = null;

  function normalise(text) {
    return text.trim().toLowerCase().replace(/\s+/g, ' ').replace(/(\d)\s*[x*]\s*(\d)/g, '$1 × $2');
  }

  function replyFor(text) {
    const known = replies[normalise(text)] || replies[normalise(text) + '?'];
    if (known) return known;
    const topic = text.trim().replace(/[?!.]+$/, '');
    const short = topic.length > 60 ? topic.slice(0, 57).trimEnd() + '…' : topic;
    return 'Antes de eu responder: o que você já sabe sobre “' + short + '”? Comece pelo que tem certeza.';
  }

  function ask(text) {
    if (!text.trim()) {
      askInput.focus();
      return;
    }
    window.clearTimeout(askTimer);
    // textContent: o texto digitado nunca é interpretado como HTML.
    askQuestion.textContent = text.trim();
    askChat?.classList.add('is-typing');
    askTimer = window.setTimeout(function () {
      askReply.textContent = replyFor(text);
      askChat?.classList.remove('is-typing');
    }, reduced() ? 0 : 900);
    askInput.value = '';
  }

  function typeInto(text) {
    window.clearInterval(typeTimer);
    if (reduced()) {
      ask(text);
      return;
    }
    let length = 0;
    askInput.value = '';
    typeTimer = window.setInterval(function () {
      length += 1;
      askInput.value = text.slice(0, length);
      if (length >= text.length) {
        window.clearInterval(typeTimer);
        ask(text);
      }
    }, 26);
  }

  if (askForm && askInput && askReply && askQuestion) {
    askForm.addEventListener('submit', function (event) {
      event.preventDefault();
      window.clearInterval(typeTimer);
      ask(askInput.value);
    });
    document.querySelectorAll('[data-ask-example]').forEach(function (button) {
      button.addEventListener('click', function () { typeInto(button.dataset.askExample); });
    });
  }

  // ---------- Painel de evolução (espelho do painel real) ----------
  const panel = document.querySelector('[data-dashboard-demo]');
  const desktop = window.matchMedia('(min-width: 992px) and (min-height: 760px)');
  const track = document.querySelector('[data-dashboard-track]');
  const dashboardSection = document.querySelector('#painel-evolucao');
  let userControlsPanel = false;

  // Grupos de escolha única, como os rádios do painel: aria-pressed marca a opção ativa.
  function pressOnly(buttons, chosen) {
    buttons.forEach(function (button) { button.setAttribute('aria-pressed', String(button === chosen)); });
  }

  const demoField = document.querySelector('[data-dashboard-field]');
  const demoTemas = Array.from(document.querySelectorAll('[data-dashboard-tema]'));
  const demoModos = Array.from(document.querySelectorAll('[data-dashboard-modo]'));
  const demoNiveis = Array.from(document.querySelectorAll('[data-dashboard-nivel]'));
  const demoDificuldade = document.querySelector('[data-dashboard-dificuldade]');

  demoTemas.forEach(function (button) {
    button.addEventListener('click', function () {
      pressOnly(demoTemas, button);
      demoField.textContent = button.textContent;
      demoField.classList.add('is-filled');
    });
  });
  demoModos.forEach(function (button) {
    button.addEventListener('click', function () {
      pressOnly(demoModos, button);
      // A régua só vale para Quiz e Speedrun, como no painel real.
      demoDificuldade.hidden = button.dataset.dashboardModo === 'guiado';
    });
  });
  demoNiveis.forEach(function (button) {
    button.addEventListener('click', function () { pressOnly(demoNiveis, button); });
  });

  function applyProgress(progress) {
    const approach = phase(progress, 0.2, 0.4);
    const entry = phase(progress, 0, 0.2);
    const values = {
      '--dashboard-progress': progress,
      '--dashboard-scale': 0.78 + 0.08 * entry + 0.14 * approach,
      '--dashboard-tilt': (8 * (1 - approach)) + 'deg',
      '--dashboard-opacity': 0.15 + 0.85 * entry,
      '--dashboard-blur': (0.6 * (1 - approach)) + 'px',
      // Ordem de leitura do painel: início da sessão, indicadores e ranking.
      '--dashboard-start': phase(progress, 0.4, 0.55),
      '--dashboard-ranking': phase(progress, 0.65, 0.8)
    };
    for (let index = 0; index < 3; index += 1) {
      const start = 0.5 + index * 0.05;
      values['--dashboard-stat-' + index] = phase(progress, start, start + 0.1);
    }
    Object.entries(values).forEach(function ([name, value]) {
      panel.style.setProperty(name, String(value));
    });
  }

  effects.push(function () {
    if (!panel) return;
    const active = dashboardSection?.classList.contains('dashboard-scroll-enabled');
    const progress = active && track ? trackProgress(track) : 1;
    try {
      applyProgress(userControlsPanel ? 1 : progress);
    } catch (error) {
      // Uma falha deixa o HTML no estado final, sem conteúdo escondido.
      dashboardSection?.classList.remove('dashboard-scroll-enabled');
    }
  });

  function takeControl() {
    // Mantém a altura do track: interagir nunca desloca a página.
    userControlsPanel = true;
    dashboardSection?.classList.add('dashboard-user-controlled');
    if (panel) applyProgress(1);
  }

  if (panel) {
    // Não mover o alvo entre pointerdown e click.
    let pointerPressed = false;
    panel.addEventListener('pointerdown', function () { pointerPressed = true; });
    panel.addEventListener('pointercancel', function () { pointerPressed = false; });
    panel.addEventListener('click', function () {
      pointerPressed = false;
      takeControl();
    });
    panel.addEventListener('focusin', function () {
      if (!pointerPressed) takeControl();
    });
  }

  function configureMotion() {
    if (dashboardSection && track && panel) {
      dashboardSection.classList.toggle('dashboard-scroll-enabled', desktop.matches && !reduced());
    }
    configureStory();
    placeIndicator();
    scheduleFrame();
  }

  window.addEventListener('scroll', scheduleFrame, { passive: true });
  window.addEventListener('resize', configureMotion, { passive: true });
  motionPreference.addEventListener('change', configureMotion);
  desktop.addEventListener('change', configureMotion);
  sceneQuery.addEventListener('change', configureMotion);
  document.fonts?.ready.then(placeIndicator);
  configureMotion();
}());
