// The compare view: two to four projects side by side, kept in ?p=a,b,c.
import type { Summary } from './view.ts';

const esc = (s: unknown) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]!);
const num = (n: number | null) => (n == null ? '—' : n >= 10000 ? `${Math.round(n / 1000)}k` : n >= 1000 ? `${(n / 1000).toFixed(1)}k` : String(n));
const date = (s: string | null) => (s ? new Date(s).toLocaleDateString('en-GB', { year: 'numeric', month: 'short', day: 'numeric', timeZone: 'UTC' }) : '—');
const STATE_TEXT: Record<string, string> = { yes: 'Yes', partial: 'Partial', no: 'No', planned: 'Planned', 'not-found': 'Not found' };

function spark(weeks: number[] | null) {
  if (!weeks?.length) return '<span class="muted small">no data</span>';
  const w = 160, h = 30, max = Math.max(1, ...weeks), step = w / (weeks.length - 1);
  const pts = weeks.map((v, i) => `${i ? 'L' : 'M'}${(i * step).toFixed(1)},${(h - 2 - (v / max) * (h - 4)).toFixed(1)}`).join('');
  const total = weeks.reduce((a, b) => a + b, 0);
  return `<svg class="spark" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}" role="img" aria-label="Commits per week: ${total} in 52 weeks"><path class="spark-area" d="${pts}L${w},${h}L0,${h}Z"/><path class="spark-line" fill="none" d="${pts}"/></svg>`;
}

export function initCompare() {
  const root = document.querySelector<HTMLElement>('[data-compare]');
  if (!root) return;
  const { all, labels, os, cats } = JSON.parse(root.querySelector('[data-all]')!.textContent!) as {
    all: Summary[]; labels: Record<string, string>; os: Record<string, string>; cats: Record<string, string>;
  };
  const bySlug = new Map(all.map((s) => [s.slug, s]));
  const tpl = (sel: string) => (root.querySelector<HTMLTemplateElement>(`template[${sel}]`)?.innerHTML ?? '').trim();
  const select = root.querySelector<HTMLSelectElement>('select[name=add]')!;
  const picked = root.querySelector<HTMLElement>('[data-picked]')!;
  const out = root.querySelector<HTMLElement>('[data-out]')!;
  const hint = root.querySelector<HTMLElement>('[data-hint]')!;
  let chosen = (new URLSearchParams(location.search).get('p') ?? '').split(',').filter((s) => bySlug.has(s)).slice(0, 4);

  const feat = (v: string | undefined) => {
    if (v === undefined) return `<span class="fchip" data-state="not-found">${tpl('data-ficon="not-found"')}Not found</span>`;
    const st = STATE_TEXT[v] ? v : 'text';
    return `<span class="fchip" data-state="${st}">${tpl(`data-ficon="${st}"`)}${esc(STATE_TEXT[v] ?? v)}</span>`;
  };

  function render() {
    picked.innerHTML = chosen.map((s) => `<li class="pick">${esc(bySlug.get(s)!.name)}<button type="button" data-remove="${esc(s)}" aria-label="Remove ${esc(bySlug.get(s)!.name)}">×</button></li>`).join('');
    for (const o of select.options) o.disabled = !!o.value && (chosen.includes(o.value) || chosen.length >= 4);
    const url = chosen.length ? `?p=${chosen.join(',')}` : location.pathname;
    history.replaceState(null, '', url);
    hint.hidden = chosen.length >= 2;
    hint.textContent = chosen.length >= 4 ? '' : chosen.length === 1 ? 'Choose at least one more.' : 'Choose at least two projects to compare.';
    if (!chosen.length) { out.hidden = true; return; }
    const ps = chosen.map((s) => bySlug.get(s)!);
    const rows: [string, (p: Summary) => string][] = [
      ['Category', (p) => esc(cats[p.category])],
      ['Kind', (p) => esc(p.kind || '—')],
      ['Activity', (p) => tpl(`data-status="${p.status}"`)],
      ['Platforms', (p) => esc(p.os.map((o) => os[o] ?? o).join(', ') || '—')],
      ['Licence', (p) => esc(p.licence ?? '—')],
      ['Language', (p) => esc(p.language ?? '—')],
      ['Weekly commits', (p) => spark(p.weekly)],
      ['Commits, last year', (p) => num(p.commits365)],
      ['Authors, 90 days', (p) => num(p.authors90)],
      ['Bus factor', (p) => num(p.busFactor)],
      ['Last commit', (p) => date(p.lastCommit)],
      ['Last release', (p) => (p.lastTag ? `${esc(p.lastTag)} <span class="muted small">${date(p.lastTagDate)}</span>` : '—')],
      ['Stars', (p) => num(p.stars)],
      ['Lines of code', (p) => num(p.loc)],
      ['AI policy', (p) => tpl(`data-mark="policy:${p.policy}"`)],
      ['AI in development', (p) => tpl(`data-mark="dev_usage:${p.dev}"`) + (p.aiShare != null ? ` <span class="muted small">${(p.aiShare * 100).toFixed(1)} % of commits credit AI</span>` : '')],
      ['AI in the product', (p) => tpl(`data-mark="in_product:${p.product}"`)],
      ['Telemetry SDKs', (p) => esc(p.telemetry.length ? p.telemetry.join(', ') : 'none found')],
      ['Checked', (p) => date(p.checked)],
    ];
    const keys = [...new Set(ps.flatMap((p) => Object.keys(p.features)))];
    keys.sort((a, b) => (labels[a] ?? a).localeCompare(labels[b] ?? b));
    for (const k of keys) rows.push([labels[k] ?? k, (p) => feat(p.features[k])]);
    out.innerHTML = `<table class="data compare-table"><caption class="sr-only">Comparison</caption><thead><tr><td></td>${ps
      .map((p) => `<th scope="col"><a href="../p/${esc(p.slug)}/">${esc(p.name)}</a></th>`)
      .join('')}</tr></thead><tbody>${rows.map(([label, f]) => `<tr><th scope="row">${esc(label)}</th>${ps.map((p) => `<td>${f(p)}</td>`).join('')}</tr>`).join('')}</tbody></table>`;
    out.hidden = false;
  }

  select.addEventListener('change', () => {
    if (select.value && chosen.length < 4 && !chosen.includes(select.value)) chosen.push(select.value);
    select.value = '';
    render();
  });
  picked.addEventListener('click', (e) => {
    const b = (e.target as HTMLElement).closest<HTMLButtonElement>('[data-remove]');
    if (!b) return;
    chosen = chosen.filter((s) => s !== b.dataset.remove);
    render();
    select.focus();
  });
  root.querySelector('[data-clear]')!.addEventListener('click', () => { chosen = []; render(); });
  render();
}
