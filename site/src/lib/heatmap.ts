// Hover and keyboard tooltip for the activity heatmap. Cells carry their text in data-tip;
// arrow keys move a roving focus (left/right by week, up/down by day), Home/End jump to the ends.
export function initHeatmaps() {
  for (const fig of document.querySelectorAll<HTMLElement>('[data-heatmap]')) {
    if (fig.dataset.ready) continue;
    fig.dataset.ready = '1';
    const tip = fig.querySelector<HTMLElement>('.hm-tip')!;
    const scroller = fig.querySelector<HTMLElement>('.heatmap-scroll')!;
    const cells = [...fig.querySelectorAll<SVGRectElement>('rect[data-tip]')];
    // On narrow screens the chart scrolls; start at the most recent weeks.
    scroller.scrollLeft = scroller.scrollWidth;

    const show = (el: SVGRectElement) => {
      const r = el.getBoundingClientRect();
      const f = fig.getBoundingClientRect();
      tip.textContent = el.dataset.tip ?? '';
      tip.hidden = false;
      const half = tip.offsetWidth / 2;
      const want = r.left - f.left + r.width / 2;
      const x = Math.min(Math.max(want, half), f.width - half);
      tip.style.left = `${x}px`;
      tip.style.setProperty('--arrow', `${want - x}px`); // keep the arrow on the cell when the tip is clamped
      tip.style.top = `${r.top - f.top}px`;
    };
    const hide = () => { tip.hidden = true; };
    fig.addEventListener('pointerover', (e) => {
      const el = (e.target as Element).closest?.('rect[data-tip]') as SVGRectElement | null;
      if (el) show(el);
    });
    fig.addEventListener('pointerleave', () => { if (!fig.contains(document.activeElement)) hide(); });
    fig.addEventListener('focusin', (e) => {
      const el = e.target as SVGRectElement;
      if (el.dataset?.tip) show(el);
    });
    fig.addEventListener('focusout', (e) => { if (!fig.contains(e.relatedTarget as Node)) hide(); });
    fig.addEventListener('keydown', (e) => {
      const i = cells.indexOf(document.activeElement as SVGRectElement);
      if (i < 0) return;
      const j = ({ ArrowLeft: i - 7, ArrowRight: i + 7, ArrowUp: i - 1, ArrowDown: i + 1, Home: 0, End: cells.length - 1 } as Record<string, number>)[e.key];
      if (e.key === 'Escape') { hide(); return; }
      if (j === undefined || !cells[j]) return;
      e.preventDefault();
      cells[i].setAttribute('tabindex', '-1');
      cells[j].setAttribute('tabindex', '0');
      cells[j].focus();
    });
  }
}
