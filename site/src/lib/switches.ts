// The theme switch (system → light → dark) and the AI stance switch, both remembered.
const root = document.documentElement;

function store(key: string, value: string | null) {
  try {
    if (value === null) localStorage.removeItem(key);
    else localStorage.setItem(key, value);
  } catch {
    /* private mode: the choice lasts for this page only */
  }
}

export function initSwitches() {
  const themeBtn = document.querySelector<HTMLButtonElement>('[data-theme-btn]');
  const names: Record<string, string> = { auto: 'follows the system', light: 'light', dark: 'dark' };
  const syncTheme = () => {
    const t = root.dataset.theme ?? 'auto';
    themeBtn?.setAttribute('aria-label', `Colour theme: ${names[t]}. Change`);
    themeBtn?.setAttribute('title', `Theme: ${names[t]}`);
  };
  themeBtn?.addEventListener('click', () => {
    const order = ['auto', 'light', 'dark'];
    const next = order[(order.indexOf(root.dataset.theme ?? 'auto') + 1) % 3];
    if (next === 'auto') delete root.dataset.theme;
    else root.dataset.theme = next;
    store('vc-theme', next === 'auto' ? null : next);
    syncTheme();
  });
  syncTheme();

  const radios = [...document.querySelectorAll<HTMLButtonElement>('[data-stance-set]')];
  const syncStance = () => {
    const s = root.dataset.stance ?? 'neutral';
    radios.forEach((b) => {
      const on = b.dataset.stanceSet === s;
      b.setAttribute('aria-checked', String(on));
      b.tabIndex = on ? 0 : -1;
    });
  };
  const set = (s: string) => {
    root.dataset.stance = s;
    store('vc-stance', s === 'neutral' ? null : s);
    syncStance();
    document.dispatchEvent(new CustomEvent('vc-stance', { detail: s }));
  };
  radios.forEach((b, i) => {
    b.addEventListener('click', () => set(b.dataset.stanceSet!));
    b.addEventListener('keydown', (e) => {
      const d = e.key === 'ArrowRight' || e.key === 'ArrowDown' ? 1 : e.key === 'ArrowLeft' || e.key === 'ArrowUp' ? -1 : 0;
      if (!d) return;
      e.preventDefault();
      const n = radios[(i + d + radios.length) % radios.length];
      set(n.dataset.stanceSet!);
      n.focus();
    });
  });
  syncStance();
}
