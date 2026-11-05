// Reads data/projects, data/metrics and data/mscs.yaml (or fixtures/ with VIBE_DATA=fixtures)
// at build time and validates them. Any malformed file stops the build with its name.
import fs from 'node:fs';
import path from 'node:path';
import { parse } from 'yaml';
import { CATEGORIES, FEATURE_VALUES, TELEMETRY, isFreeTextFeature, metricsSchema, mscSchema, projectSchema, type Msc, type Project } from './schema.ts';

export type Category = (typeof CATEGORIES)[number];

export interface Metrics {
  slug: string;
  fetched_at: string;
  combined: Record<string, any> | null;
  repos: Record<string, any>[];
}

export interface Entry extends Project {
  file: string;
  metrics: Metrics | null;
}

export interface Dataset {
  dir: string;
  projects: Entry[];
  mscs: Msc[];
  collector: Record<string, any> | null;
  /** Malformed files: the build stops. */
  errors: string[];
  /** Things to reconcile by hand: `npm run validate` lists them, `--strict` fails on them. */
  warnings: string[];
}

function repoRoot() {
  // site/ is the working directory for astro and for scripts/validate.ts
  const cwd = process.cwd();
  return fs.existsSync(path.join(cwd, 'astro.config.mjs')) ? path.resolve(cwd, '..') : cwd;
}

function walk(dir: string, ext: string): string[] {
  if (!fs.existsSync(dir)) return [];
  return fs
    .readdirSync(dir, { withFileTypes: true, recursive: true })
    .filter((d) => d.isFile() && d.name.endsWith(ext))
    .map((d) => path.join(d.parentPath ?? (d as any).path, d.name))
    .sort();
}

function fmtIssues(file: string, issues: { path: (string | number)[]; message: string }[]) {
  return issues.map((i) => `${file}: ${i.path.join('.') || '(root)'}: ${i.message}`);
}

export function loadDataset(): Dataset {
  const root = repoRoot();
  const name = process.env.VIBE_DATA || 'data';
  const dir = path.isAbsolute(name) ? name : path.join(root, name);
  const errors: string[] = [];
  const rel = (f: string) => path.relative(root, f);

  const metrics = new Map<string, Metrics>();
  for (const f of walk(path.join(dir, 'metrics'), '.json')) {
    if (path.basename(f).startsWith('_')) continue;
    try {
      const r = metricsSchema.safeParse(JSON.parse(fs.readFileSync(f, 'utf8')));
      if (r.success) metrics.set(r.data.slug, r.data as Metrics);
      else errors.push(...fmtIssues(rel(f), r.error.issues));
    } catch (e) {
      errors.push(`${rel(f)}: ${(e as Error).message}`);
    }
  }

  // Icons live with the site, not with the data, so fixtures share the same folder.
  const iconDir = path.join(root, 'site', 'public', 'icons');
  const iconFiles = fs.existsSync(iconDir) ? fs.readdirSync(iconDir).filter((x) => /\.(svg|webp|png)$/.test(x)) : [];
  const projects: Entry[] = [];
  const seen = new Map<string, string>();
  for (const f of walk(path.join(dir, 'projects'), '.yaml')) {
    let doc: unknown;
    try {
      doc = parse(fs.readFileSync(f, 'utf8'));
    } catch (e) {
      errors.push(`${rel(f)}: YAML: ${(e as Error).message.split('\n')[0]}`);
      continue;
    }
    const r = projectSchema.safeParse(doc);
    if (!r.success) {
      errors.push(...fmtIssues(rel(f), r.error.issues));
      continue;
    }
    const p = r.data;
    const folder = path.basename(path.dirname(f));
    if (folder !== p.category) errors.push(`${rel(f)}: category "${p.category}" but the file is in ${folder}/`);
    if (path.basename(f, '.yaml') !== p.slug) errors.push(`${rel(f)}: slug "${p.slug}" does not match the file name`);
    if (seen.has(p.slug)) errors.push(`${rel(f)}: slug "${p.slug}" already used by ${seen.get(p.slug)}`);
    seen.set(p.slug, rel(f));
    const icon = (p as { icon?: { file: string } }).icon;
    if (icon) {
      if (path.basename(icon.file).replace(/\.[a-z]+$/, '') !== p.slug) errors.push(`${rel(f)}: icon.file "${icon.file}" should be named after the slug`);
      if (!fs.existsSync(path.join(iconDir, icon.file))) errors.push(`${rel(f)}: icon.file "${icon.file}" is missing from ${rel(iconDir)}/`);
    }
    // Only for the real dataset: fixtures share the icons folder but carry no icon keys.
    if (!icon && name === 'data' && iconFiles.some((x) => x.replace(/\.[a-z]+$/, '') === p.slug)) errors.push(`${rel(f)}: ${rel(iconDir)}/ has an icon for "${p.slug}" but the file has no icon key (source and licence)`);
    projects.push({ ...p, file: rel(f), metrics: metrics.get(p.slug) ?? null });
  }

  let mscs: Msc[] = [];
  const mscFile = path.join(dir, 'mscs.yaml');
  if (fs.existsSync(mscFile)) {
    try {
      const r = mscSchema.safeParse(parse(fs.readFileSync(mscFile, 'utf8')) ?? []);
      if (r.success) mscs = r.data.sort((a, b) => a.msc - b.msc);
      else errors.push(...fmtIssues(rel(mscFile), r.error.issues));
    } catch (e) {
      errors.push(`${rel(mscFile)}: ${(e as Error).message.split('\n')[0]}`);
    }
  }

  let collector = null;
  const cf = path.join(dir, 'metrics', '_collector.json');
  if (fs.existsSync(cf)) collector = JSON.parse(fs.readFileSync(cf, 'utf8'));

  const warnings: string[] = [];
  crossCheck(projects, metrics, errors, warnings);

  projects.sort((a, b) => a.name.localeCompare(b.name, 'en', { sensitivity: 'base' }));
  return { dir: rel(dir) || '.', projects, mscs, collector, errors, warnings };
}

const NOT_FOUND = new Set(['not-found', 'none-found']);
const valueOf = (raw: unknown) => (raw && typeof raw === 'object' && !Array.isArray(raw) ? (raw as { value?: unknown }).value : raw);

/** Rules across fields and files that the per-file schema cannot express. */
function crossCheck(projects: Entry[], metrics: Map<string, Metrics>, errors: string[], warnings: string[]) {
  const slugs = new Set(projects.map((p) => p.slug));
  for (const m of metrics.keys()) if (!slugs.has(m)) warnings.push(`metrics/${m}.json: no project file has the slug "${m}" (stale after a rename?)`);
  for (const p of projects) {
    const f = (p.features ?? {}) as Record<string, unknown>;
    // fork_of names a project in the dataset, or is a URL.
    if (p.fork_of && !/^https?:\/\//.test(p.fork_of) && !slugs.has(p.fork_of)) errors.push(`${p.file}: fork_of "${p.fork_of}" is neither a slug in the dataset nor a URL`);
    for (const [k, raw] of Object.entries(f)) {
      if (k === 'msc' || Array.isArray(raw)) continue;
      const v = valueOf(raw);
      // Bare values ("threads: yes") get the same check as maps ({value: yes, …}).
      if (k === 'telemetry') {
        if (typeof v === 'string' && !(TELEMETRY as readonly string[]).includes(v)) errors.push(`${p.file}: features.telemetry: "${v}" is not one of ${TELEMETRY.join(', ')}`);
        continue;
      }
      if (isFreeTextFeature(k)) continue;
      if (typeof v === 'string' && !(FEATURE_VALUES as readonly string[]).includes(v)) errors.push(`${p.file}: features.${k}: "${v}" is not one of ${FEATURE_VALUES.join(', ')} (or add the key to FREE_TEXT in schema.ts)`);
      // Every yes / partial / no is a claim and carries its source.
      const src = raw && typeof raw === 'object' ? (raw as { source?: unknown }).source : null;
      if (typeof v === 'string' && ['yes', 'partial', 'no'].includes(v) && !src) warnings.push(`${p.file}: features.${k} is "${v}" with no source`);
    }
    const c = p.metrics?.combined;
    if (p.repos.length && !p.metrics) warnings.push(`${p.file}: has repositories but no metrics yet (run the collector)`);
    // The collector found an analytics or crash-report SDK; the hand value must say what it does.
    const sdks = (c?.telemetry_sdks as string[] | undefined) ?? [];
    if (p.category === 'client' && sdks.length) {
      const t = f.telemetry;
      const v = valueOf(t);
      const note = t && typeof t === 'object' ? (t as { note?: string }).note : null;
      if ((v == null || NOT_FOUND.has(String(v))) && !note)
        warnings.push(`${p.file}: the collector found ${sdks.join(', ')} in the manifests but features.telemetry is "${v ?? 'missing'}" with no note: check whether it is opt-in, opt-out or compiled out`);
    }
  }
}

let cached: Dataset | null = null;

/** The dataset for pages: throws (failing the build) when any file is malformed. */
export function dataset(): Dataset {
  if (cached) return cached;
  const d = loadDataset();
  if (d.errors.length) {
    throw new Error(`Malformed data files (${d.errors.length} problems):\n  ${d.errors.join('\n  ')}`);
  }
  cached = d;
  return d;
}
