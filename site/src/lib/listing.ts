// Filtering, sorting and the cards/table switch on category pages. The page is complete
// without this script; it only hides and reorders what the server rendered.
type Item = {
  slug: string; name: string; kind: string; status: string; os: string[]; mobile: boolean; stars: number | null;
  authors90: number | null; commits365: number | null; lastCommit: string | null;
  commits90: number | null; commitsAll: number | null; authors365: number | null; authorsAll: number | null; tags365: number | null;
  firstCommit: string | null; mscs: number | null; usedBy: number | null; busFactor: number | null; loc: number | null; policy: string; dev: string; product: string;
};
const STATUS_RANK = ['active', 'small-team', 'slowing', 'dormant', 'abandoned', 'archived', 'no-repo', 'unknown'];
const DESKTOP = ['windows', 'macos', 'linux'];
const MOBILE = ['android', 'ios', 'ipados', 'sailfish', 'ubuntu-touch', 'harmonyos'];

export function initListing() {
  const root = document.querySelector<HTMLElement>('[data-listing]');
  if (!root) return;
  const items: Record<string, Item & { text: string }> = JSON.parse(root.querySelector('[data-items]')!.textContent!);
  for (const [slug, it] of Object.entries(items)) {
    const card = root.querySelector(`.card[data-slug="${slug}"]`);
    it.text = `${it.name} ${it.kind} ${card?.textContent ?? ''}`.toLowerCase();
  }
  const form = root.querySelector('form')!;
  const cards = root.querySelector<HTMLElement>('[data-cards]')!;
  const table = root.querySelector<HTMLElement>('[data-table]')!;
  const tbody = table.querySelector('tbody')!;
  const count = root.querySelector('[data-count]')!;
  const none = root.querySelector<HTMLElement>('[data-none]')!;
  let dir = 1;

  const params = new URLSearchParams(location.search);
  for (const el of form.elements as unknown as HTMLInputElement[]) {
    if (!el.name || !params.has(el.name)) continue;
    if (el.type === 'checkbox') el.checked = params.get(el.name) === '1';
    else el.value = params.get(el.name)!;
  }
  let view = params.get('view') === 'table' ? 'table' : 'cards';
  try { if (!params.has('view')) view = localStorage.getItem('vc-view') === 'table' ? 'table' : 'cards'; } catch { /* no storage */ }

  const val = (n: string) => (form.elements.namedItem(n) as HTMLInputElement | HTMLSelectElement | null);

  function sortKey(it: Item, by: string): number | string {
    switch (by) {
      case 'activity': return -(it.commits365 ?? -1);
      case 'authors': return -(it.authors90 ?? -1);
      case 'stars': return -(it.stars ?? -1);
      case 'commits90': return -(it.commits90 ?? -1);
      case 'commitsAll': return -(it.commitsAll ?? -1);
      case 'authors365': return -(it.authors365 ?? -1);
      case 'authorsAll': return -(it.authorsAll ?? -1);
      case 'releases': return -(it.tags365 ?? -1);
      case 'bus': return -(it.busFactor ?? -1);
      case 'loc': return -(it.loc ?? -1);
      case 'usedBy': return -(it.usedBy ?? -1);
      case 'mscs': return -(it.mscs ?? -1);
      case 'oldest': return it.firstCommit ? Date.parse(it.firstCommit) : Number.MAX_SAFE_INTEGER;
      case 'recent': return -(it.lastCommit ? Date.parse(it.lastCommit) : 0);
      case 'status': return STATUS_RANK.indexOf(it.status);
      default: return it.name.toLowerCase();
    }
  }

  function apply() {
    const q = (val('q')?.value ?? '').trim().toLowerCase();
    const status = val('status')?.value ?? '';
    const os = val('os')?.value ?? '';
    const mobile = (val('mobile') as HTMLInputElement | null)?.checked ?? false;
    const pol = val('policy')?.value ?? '', dev = val('dev_usage')?.value ?? '', prod = val('in_product')?.value ?? '';
    const by = val('sort')?.value ?? 'name';
    const shown = Object.values(items).filter((it) => {
      if (q && !q.split(/\s+/).every((w) => it.text.includes(w))) return false;
      if (status && it.status !== status) return false;
      if (mobile && !it.mobile) return false;
      if (os === 'mobile' && !it.os.some((o) => MOBILE.includes(o))) return false;
      if (os === 'desktop' && !it.os.some((o) => DESKTOP.includes(o))) return false;
      if (os && !['mobile', 'desktop'].includes(os) && !it.os.includes(os)) return false;
      if (pol && it.policy !== pol) return false;
      if (dev && it.dev !== dev) return false;
      if (prod && it.product !== prod) return false;
      return true;
    });
    shown.sort((a, b) => {
      const ka = sortKey(a, by), kb = sortKey(b, by);
      const c = ka < kb ? -1 : ka > kb ? 1 : a.name.localeCompare(b.name);
      return c * dir;
    });
    const keep = new Set(shown.map((s) => s.slug));
    for (const el of cards.children as unknown as HTMLElement[]) el.hidden = !keep.has(el.dataset.slug!);
    for (const el of tbody.children as unknown as HTMLElement[]) el.hidden = !keep.has(el.dataset.slug!);
    for (const s of shown) {
      const c = cards.querySelector(`[data-slug="${s.slug}"]`); if (c) cards.appendChild(c);
      const r = tbody.querySelector(`[data-slug="${s.slug}"]`); if (r) tbody.appendChild(r);
    }
    table.querySelectorAll('th[data-sort]').forEach((th) => {
      const k = (th as HTMLElement).dataset.sort;
      if (k === by) th.setAttribute('aria-sort', dir === 1 ? 'ascending' : 'descending');
      else th.removeAttribute('aria-sort');
    });
    count.textContent = `${shown.length} of ${Object.keys(items).length} shown`;
    none.hidden = shown.length > 0;
    cards.hidden = view !== 'cards' || !shown.length;
    table.hidden = view !== 'table' || !shown.length;
    root!.querySelectorAll('[data-view]').forEach((b) => b.setAttribute('aria-pressed', String((b as HTMLElement).dataset.view === view)));
    const p = new URLSearchParams();
    for (const el of form.elements as unknown as HTMLInputElement[]) {
      if (!el.name) continue;
      if (el.type === 'checkbox') { if (el.checked) p.set(el.name, '1'); }
      else if (el.value && !(el.name === 'sort' && el.value === 'name')) p.set(el.name, el.value);
    }
    if (view === 'table') p.set('view', 'table');
    history.replaceState(null, '', p.toString() ? `?${p}` : location.pathname);
  }

  form.addEventListener('input', () => { dir = 1; apply(); });
  root.querySelectorAll<HTMLButtonElement>('[data-view]').forEach((b) =>
    b.addEventListener('click', () => {
      view = b.dataset.view!;
      try { localStorage.setItem('vc-view', view); } catch { /* no storage */ }
      apply();
    }),
  );
  table.querySelectorAll<HTMLElement>('th[data-sort] button').forEach((btn) =>
    btn.addEventListener('click', () => {
      const k = (btn.parentElement as HTMLElement).dataset.sort!;
      const sel = val('sort') as HTMLSelectElement;
      if (sel.value === k) dir = -dir;
      else { sel.value = k; dir = 1; }
      apply();
    }),
  );
  apply();
}
