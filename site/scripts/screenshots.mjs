// Screenshots of every page type at phone and desktop widths, both themes, with an AI stance.
// Usage: npm run build && node scripts/screenshots.mjs [outDir]
// Serves dist/ under /vibe-check/ on a local port; needs Playwright (preinstalled or npx).
import { createServer } from 'node:http';
import { readFile, mkdir, stat } from 'node:fs/promises';
import path from 'node:path';
import { createRequire } from 'node:module';
// CommonJS resolution so NODE_PATH can point at a globally installed Playwright.
const { chromium } = createRequire(import.meta.url)('playwright');

const out = process.argv[2] ?? 'screenshots';
const dist = path.resolve('dist');
const types = { '.html': 'text/html', '.css': 'text/css', '.js': 'text/javascript', '.svg': 'image/svg+xml', '.woff2': 'font/woff2', '.json': 'application/json' };
const server = createServer(async (req, res) => {
  let p = decodeURIComponent(new URL(req.url, 'http://x').pathname).replace(/^\/vibe-check/, '');
  let f = path.join(dist, p);
  try { if ((await stat(f)).isDirectory()) f = path.join(f, 'index.html'); } catch { f = path.join(dist, '404.html'); res.statusCode = 404; }
  try { res.setHeader('content-type', types[path.extname(f)] ?? 'application/octet-stream'); res.end(await readFile(f)); } catch { res.statusCode = 404; res.end('not found'); }
}).listen(0);
const base = `http://127.0.0.1:${server.address().port}/vibe-check/`;
const fixed = process.env.PAGES ? process.env.PAGES.split(',') : ['', 'client/', 'server/', 'p/element-x/', 'p/beeper/', 'mscs/', 'compare/?p=element-x,conduit', 'methodology/'];
await mkdir(out, { recursive: true });
const browser = await chromium.launch();
const errors = [];
for (const [wname, width] of [['phone', 390], ['desktop', 1280]]) {
  for (const theme of ['light', 'dark']) {
    const ctx = await browser.newContext({ viewport: { width, height: 900 }, colorScheme: theme, deviceScaleFactor: 1 });
    await ctx.addInitScript((s) => localStorage.setItem('vc-stance', s), theme === 'light' ? 'wary' : 'friendly');
    const page = await ctx.newPage();
    page.on('console', (m) => m.type() === 'error' && errors.push(`${page.url()}: ${m.text()}`));
    page.on('pageerror', (e) => errors.push(`${page.url()}: ${e.message}`));
    for (const p of fixed) {
      await page.goto(base + p, { waitUntil: 'networkidle' });
      const sw = await page.evaluate(() => document.documentElement.scrollWidth);
      if (sw > width + 1) errors.push(`${p} at ${width}px: page scrolls sideways (${sw}px)`);
      const name = `${(p || 'home').replace(/[/?=,]+/g, '_').replace(/_$/, '')}-${wname}-${theme}.png`;
      await page.screenshot({ path: path.join(out, name), fullPage: true });
    }
    await ctx.close();
  }
}
await browser.close();
server.close();
console.log(errors.length ? `problems:\n  ${errors.join('\n  ')}` : 'no console errors, no sideways scroll');
