// Presentation helpers shared by pages and components.
import type { Category, Entry } from './data.ts';
import { isFreeTextFeature } from './schema.ts';

export const base = import.meta.env.BASE_URL.replace(/\/?$/, '/');
export const href = (p = '') => base + p.replace(/^\//, '');

export const CATEGORY_LABEL: Record<Category, { one: string; many: string; blurb: string }> = {
  client: { one: 'Client', many: 'Clients', blurb: 'Apps people chat in: web, desktop, mobile and terminal.' },
  server: { one: 'Server', many: 'Servers', blurb: 'Homeservers that store rooms and federate with each other.' },
  bot: { one: 'Bot', many: 'Bots', blurb: 'Bots and integrations: moderation, notifications, feeds, games.' },
  bridge: { one: 'Bridge', many: 'Bridges', blurb: 'Links between Matrix and other chat networks.' },
  sdk: { one: 'SDK', many: 'SDKs', blurb: 'Libraries for building Matrix clients, bots and bridges.' },
  tool: { one: 'Tool', many: 'Tools', blurb: 'Admin, moderation and deployment tools.' },
};

// ---- activity status ------------------------------------------------------------------
export const STATUS: Record<string, { label: string; icon: string; desc: string; rank: number }> = {
  active: { label: 'Active', icon: 'pulse', desc: 'A commit in the last 30 days and 3 or more authors in the last 90 days', rank: 0 },
  'small-team': { label: 'Small team', icon: 'pulse', desc: 'A commit in the last 30 days, fewer than 3 authors in 90 days', rank: 1 },
  slowing: { label: 'Slowing', icon: 'slow', desc: 'Last commit 31 to 180 days ago', rank: 2 },
  dormant: { label: 'Dormant', icon: 'moon', desc: 'No commit for 180 days to 2 years', rank: 3 },
  abandoned: { label: 'Abandoned', icon: 'stop', desc: 'No commit for over 2 years', rank: 4 },
  archived: { label: 'Archived', icon: 'box', desc: 'The forge marks the repository archived, or the project says it is no longer maintained', rank: 5 },
  'no-repo': { label: 'No public repo', icon: 'lock', desc: 'No public source repository to measure', rank: 6 },
  unknown: { label: 'Not measured yet', icon: 'dash', desc: 'The collector has not run for this project yet', rank: 7 },
};

export function statusOf(p: Entry): string {
  // A project its maintainers have archived or deprecated stays archived, even when the forge
  // flag is not set or its last commit (often the deprecation notice itself) is recent.
  if (p.maturity === 'archived') return 'archived';
  if (!p.repos?.length) return 'no-repo';
  return (p.metrics?.combined?.status as string) || 'unknown';
}

/** JSON for a <script type="application/json"> block: `<` is escaped so no string in the data
 *  (a quoted README line, say) can close the script element. */
export const jsonForScript = (v: unknown) =>
  JSON.stringify(v).replace(/</g, '\\u003c').replace(/\u2028/g, '\\u2028').replace(/\u2029/g, '\\u2029');

/** Whether the licence the repository's files or forge show is the one in the project file,
 *  ignoring -only / -or-later (forges report the bare id) and taking any id in an OR / AND
 *  expression ("MIT OR Apache-2.0" matches a repo that shows Apache-2.0). */
export function sameLicence(stated: string | null | undefined, detected: string | null | undefined): boolean {
  if (!stated || !detected) return true;
  const norm = (id: string) => id.trim().replace(/(-only|-or-later|\+)$/i, '').toUpperCase();
  const ids = stated.split(/\s+(?:OR|AND|WITH)\s+|[()]/i).filter(Boolean).map(norm);
  return ids.includes(norm(detected));
}

// ---- AI marks -------------------------------------------------------------------------
// Each axis value gets a polarity: "ai" (AI used or welcomed), "noai" (no AI found or AI
// declined), "mixed" (restricted), "unknown" (nothing found where "nothing" is not a no).
// The stance switch decides only how a polarity is drawn, never the data.
export type Polarity = 'ai' | 'noai' | 'mixed' | 'unknown';
export const AXES = {
  policy: {
    label: 'AI policy',
    short: 'Policy',
    question: 'What the project says about AI-made contributions',
    values: {
      banned: { text: 'Banned', pol: 'noai' },
      restricted: { text: 'Restricted', pol: 'mixed' },
      allowed: { text: 'Allowed', pol: 'ai' },
      encouraged: { text: 'Encouraged', pol: 'ai' },
      'none-found': { text: 'No policy found', pol: 'unknown' },
    },
  },
  dev_usage: {
    label: 'AI in development',
    short: 'Dev use',
    question: 'Whether the developers use AI tools on the repository',
    values: {
      'none-found': { text: 'None found', pol: 'noai' },
      'config-only': { text: 'Config only', pol: 'ai' },
      occasional: { text: 'Occasional', pol: 'ai' },
      regular: { text: 'Regular', pol: 'ai' },
    },
  },
  in_product: {
    label: 'AI in the product',
    short: 'In product',
    question: 'Whether the product itself has AI features',
    values: {
      'none-found': { text: 'None found', pol: 'noai' },
      optional: { text: 'Optional', pol: 'ai' },
      core: { text: 'Core', pol: 'ai' },
    },
  },
} as const satisfies Record<string, { label: string; short: string; question: string; values: Record<string, { text: string; pol: Polarity }> }>;
export type Axis = keyof typeof AXES;

export function aiMark(axis: Axis, value: string | undefined): { text: string; pol: Polarity; value: string } {
  const v = (AXES[axis].values as Record<string, { text: string; pol: Polarity }>)[value ?? ''];
  return v ? { ...v, value: value! } : { text: 'Not found', pol: 'unknown', value: value ?? 'none-found' };
}

// ---- features -------------------------------------------------------------------------
export type FeatureState = 'yes' | 'partial' | 'no' | 'planned' | 'not-found' | 'text';
export interface FeatureView {
  key: string;
  label: string;
  state: FeatureState;
  value: string;
  how?: string | null;
  source?: string | string[] | null;
  note?: string | null;
}

const LABELS: Record<string, string> = {
  sdk: 'SDK', e2ee: 'Encryption (E2EE)', cross_signing: 'Cross-signing', key_backup: 'Key backup', sliding_sync: 'Sliding sync',
  oidc_auth: 'Next-gen auth (OIDC)', multi_account: 'Multiple accounts', threads: 'Threads', spaces: 'Spaces', voip_1to1: '1:1 calls',
  group_calls: 'Group calls', reactions: 'Reactions', edits: 'Edits', replies: 'Replies', polls: 'Polls', custom_emoji: 'Custom emoji',
  stickers: 'Stickers', location: 'Location', voice_messages: 'Voice messages', rich_text_editor: 'Rich text editor',
  url_previews: 'URL previews', push_notifications: 'Push notifications', private_read_receipts: 'Private read receipts',
  presence: 'Presence', room_upgrades: 'Room upgrades', moderation_tools: 'Moderation tools', accessibility: 'Accessibility',
  translations: 'Translations', telemetry: 'Telemetry', default_homeserver: 'Default homeserver', fork_friendliness: 'Fork-friendliness',
  language: 'Language', database: 'Database', federation: 'Federation', spec_versions: 'Spec versions', appservices: 'Appservices',
  admin_api: 'Admin API', oidc_delegation: 'OIDC delegation (MAS)', native_sliding_sync: 'Native sliding sync',
  workers_scaling: 'Workers / scaling', media_auth: 'Authenticated media', resource_needs: 'Resource needs', purpose: 'Purpose',
  framework: 'Framework', hosting: 'Hosting', config: 'Configuration', ai_backend: 'AI backend', network: 'Network',
  puppeting: 'Puppeting', backfill: 'Backfill', media: 'Media', reactions_edits: 'Reactions and edits', group_chats: 'Group chats',
  login_methods: 'Login methods', network_tos_risk: 'Terms-of-service risk',
};
export const featureLabel = (k: string) => LABELS[k] ?? k.replace(/_/g, ' ').replace(/^./, (c) => c.toUpperCase());

export const HEADLINE: Record<Category, string[]> = {
  client: ['e2ee', 'sliding_sync', 'oidc_auth', 'threads', 'spaces', 'group_calls'],
  server: ['federation', 'native_sliding_sync', 'oidc_delegation', 'media_auth', 'appservices', 'workers_scaling'],
  bot: ['purpose', 'e2ee', 'hosting'],
  bridge: ['network', 'puppeting', 'e2ee', 'backfill', 'reactions_edits'],
  sdk: ['e2ee', 'sliding_sync', 'oidc_auth', 'threads'],
  tool: ['purpose', 'e2ee', 'hosting'],
};

/** The client features shown in the clients × features matrix and counted on client cards, with the
 *  MSCs each one rests on (numbers from data/mscs.yaml; an empty list means no single MSC: either
 *  older core spec, or a client-side feature). Order: the protocol work that matters most first. */
export const CLIENT_FEATURES: { key: string; mscs: number[] }[] = [
  { key: 'e2ee', mscs: [] },
  { key: 'cross_signing', mscs: [1756] },
  { key: 'key_backup', mscs: [1219] },
  { key: 'sliding_sync', mscs: [4186, 3575] },
  { key: 'oidc_auth', mscs: [3861] },
  { key: 'threads', mscs: [3440] },
  { key: 'spaces', mscs: [1772] },
  { key: 'voip_1to1', mscs: [] },
  { key: 'group_calls', mscs: [4143, 3401] },
  { key: 'reactions', mscs: [2677] },
  { key: 'edits', mscs: [2676] },
  { key: 'replies', mscs: [] },
  { key: 'polls', mscs: [3381] },
  { key: 'custom_emoji', mscs: [2545] },
  { key: 'stickers', mscs: [] },
  { key: 'location', mscs: [3488, 3489] },
  { key: 'voice_messages', mscs: [3245] },
  { key: 'private_read_receipts', mscs: [2285] },
  { key: 'presence', mscs: [] },
  { key: 'room_upgrades', mscs: [1501] },
  { key: 'url_previews', mscs: [] },
  { key: 'push_notifications', mscs: [] },
  { key: 'rich_text_editor', mscs: [] },
  { key: 'moderation_tools', mscs: [] },
];

const STATES = new Set(['yes', 'partial', 'no', 'planned', 'not-found']);

export function feature(key: string, raw: unknown): FeatureView {
  const label = featureLabel(key);
  if (raw === undefined || raw === null) return { key, label, state: 'not-found', value: 'not found' };
  if (typeof raw === 'boolean') return { key, label, state: raw ? 'yes' : 'no', value: raw ? 'yes' : 'no' };
  if (typeof raw === 'string' || typeof raw === 'number') {
    const s = String(raw);
    if (STATES.has(s) && !isFreeTextFeature(key)) return { key, label, state: s as FeatureState, value: s };
    return { key, label, state: 'text', value: s };
  }
  if (Array.isArray(raw)) return { key, label, state: 'text', value: raw.map(String).join(', ') };
  const o = raw as Record<string, any>;
  const v = o.value === undefined || o.value === null ? 'not-found' : typeof o.value === 'boolean' ? (o.value ? 'yes' : 'no') : String(o.value);
  // A free-text feature whose value is a "not found" word is drawn as not found, not as text.
  if (v === 'not-found' || (v === 'none-found' && key !== 'telemetry' && key !== 'ai_backend')) return { key, label, state: 'not-found', value: 'not found', how: o.how, source: o.source, note: o.note };
  const state: FeatureState = STATES.has(v) && !isFreeTextFeature(key) && key !== 'telemetry' ? (v as FeatureState) : 'text';
  return { key, label, state, value: v, how: o.how, source: o.source, note: o.note };
}

export function features(p: Entry): FeatureView[] {
  const f = (p.features ?? {}) as Record<string, unknown>;
  return Object.entries(f)
    .filter(([k]) => k !== 'msc')
    .map(([k, v]) => feature(k, v));
}

/** How many of the client features were found (yes) or found partly. "Not found" counts as unknown, not as no. */
export function featureScore(p: Entry): { yes: number; partial: number; no: number; total: number } | null {
  if (p.category !== 'client') return null;
  const f = (p.features ?? {}) as Record<string, unknown>;
  const states = CLIENT_FEATURES.map(({ key }) => feature(key, f[key]).state);
  return { yes: states.filter((s) => s === 'yes').length, partial: states.filter((s) => s === 'partial').length, no: states.filter((s) => s === 'no').length, total: states.length };
}

export const STATE_TEXT: Record<FeatureState, string> = {
  yes: 'Yes', partial: 'Partial', no: 'No', planned: 'Planned', 'not-found': 'Not found', text: '',
};

// ---- platforms -------------------------------------------------------------------------
export const OS_LABEL: Record<string, string> = {
  android: 'Android', ios: 'iOS', ipados: 'iPadOS', windows: 'Windows', macos: 'macOS', linux: 'Linux', web: 'Web',
  terminal: 'Terminal', sailfish: 'Sailfish OS', 'ubuntu-touch': 'Ubuntu Touch', harmonyos: 'HarmonyOS', other: 'Other', server: 'Server',
};
export const MOBILE_OS = new Set(['android', 'ios', 'ipados', 'sailfish', 'ubuntu-touch', 'harmonyos']);
export const OS_ICON: Record<string, string> = {
  android: 'phone', ios: 'phone', ipados: 'tablet', sailfish: 'phone', 'ubuntu-touch': 'phone', harmonyos: 'phone',
  windows: 'desktop', macos: 'desktop', linux: 'desktop', web: 'globe', terminal: 'terminal', server: 'server', other: 'dot',
};

export function osList(p: Entry): string[] {
  const order = ['android', 'ios', 'ipados', 'sailfish', 'ubuntu-touch', 'harmonyos', 'web', 'windows', 'macos', 'linux', 'terminal', 'server', 'other'];
  const set = new Set<string>();
  for (const a of p.apps ?? []) if (a.status !== 'discontinued') set.add(a.os);
  if (!set.size) for (const pl of p.platforms ?? []) set.add(pl);
  return [...set].sort((a, b) => order.indexOf(a) - order.indexOf(b));
}
export const isMobile = (p: Entry) => osList(p).some((o) => MOBILE_OS.has(o));

// ---- formatting -----------------------------------------------------------------------
export function fmtDate(iso?: string | null): string {
  if (!iso) return '—';
  const d = new Date(iso);
  if (Number.isNaN(+d)) return String(iso);
  return d.toLocaleDateString('en-GB', { year: 'numeric', month: 'short', day: 'numeric', timeZone: 'UTC' });
}
export function fmtNum(n?: number | null): string {
  if (n === null || n === undefined) return '—';
  if (n >= 10000) return `${Math.round(n / 1000)}k`;
  if (n >= 1000) return `${(n / 1000).toFixed(1)}k`;
  return String(n);
}
export function ago(iso: string | null | undefined, now: Date): string {
  if (!iso) return '—';
  const days = Math.floor((+now - +new Date(iso)) / 86400000);
  if (days < 1) return 'today';
  if (days < 2) return 'yesterday';
  if (days < 60) return `${days} days ago`;
  if (days < 730) return `${Math.round(days / 30.4)} months ago`;
  return `${Math.round(days / 365)} years ago`;
}
/** A date as a stat value: recent dates read as "12 days ago", older ones as the month ("Aug 2025"). */
export function dateStat(iso: string | null | undefined, now: Date): { big: string; small: string } | null {
  if (!iso) return null;
  const d = new Date(iso);
  if (Number.isNaN(+d)) return null;
  const days = Math.floor((+now - +d) / 86400000);
  const rel = ago(iso, now);
  if (days < 60) return { big: rel, small: fmtDate(iso) };
  const day = d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', timeZone: 'UTC' });
  return { big: d.toLocaleDateString('en-GB', { month: 'short', year: 'numeric', timeZone: 'UTC' }), small: `${rel} · ${day}` };
}
/** Split a release tag into the version people read and the package or branch prefix:
 *  "@scope/pkg@2.1.0" → 2.1.0 + @scope/pkg, "release/26.10.8" → 26.10.8 + release. */
export function splitTag(tag: string): { version: string; prefix: string | null } {
  const npm = /^(@?[^@]+)@([^@/]+)$/.exec(tag);
  if (npm) return { version: npm[2], prefix: npm[1] };
  const i = tag.lastIndexOf('/');
  if (i > 0 && i < tag.length - 1) return { version: tag.slice(i + 1), prefix: tag.slice(0, i) };
  return { version: tag, prefix: null };
}
export const pct = (x?: number | null, digits = 1) => (x === null || x === undefined ? '—' : `${(x * 100).toFixed(digits)} %`);

export function host(u?: string | null): string {
  if (!u) return '';
  try {
    const x = new URL(u);
    return x.hostname.replace(/^www\./, '') + (x.pathname.length > 1 ? x.pathname.replace(/\/$/, '') : '');
  } catch {
    return u;
  }
}

/** A compact record of a project for client-side filtering, sorting and compare. */
export function summary(p: Entry) {
  const c = p.metrics?.combined ?? {};
  return {
    slug: p.slug,
    name: p.name,
    category: p.category,
    kind: p.kind ?? '',
    status: statusOf(p),
    os: osList(p),
    mobile: isMobile(p),
    licence: p.licence ?? c.licence_detected ?? null,
    language: c.main_language ?? (typeof p.features?.language === 'string' ? p.features.language : null),
    stars: c.stars ?? null,
    authors90: c.authors_90d ?? null,
    commits365: c.commits_365d ?? null,
    commits90: c.commits_90d ?? null,
    commitsAll: c.commits_all ?? null,
    authors365: c.authors_365d ?? null,
    authorsAll: c.authors_all ?? null,
    tags365: c.tags_365d ?? null,
    firstCommit: c.first_commit ?? null,
    usedBy: Array.isArray((p.features as any)?.used_by) ? ((p.features as any).used_by as unknown[]).length : null,
    mscs: Array.isArray((p.features as any)?.msc) ? ((p.features as any).msc as { state: string }[]).filter((m) => m.state !== 'removed').length : null,
    lastCommit: c.last_commit ?? null,
    lastTag: c.last_tag ?? null,
    lastTagDate: c.last_tag_date ?? null,
    policy: p.ai.policy.value,
    dev: p.ai.dev_usage.value,
    product: p.ai.in_product.value,
    aiShare: c.ai?.share_365d ?? null,
    weekly: (c.weekly_commits as number[] | undefined) ?? null,
    features: Object.fromEntries(features(p).map((f) => [f.key, f.state === 'text' ? f.value : f.state])),
    busFactor: c.bus_factor_365d ?? null,
    featYes: featureScore(p)?.yes ?? null,
    featPartial: featureScore(p)?.partial ?? null,
    loc: c.loc_total ?? null,
    telemetry: c.telemetry_sdks ?? [],
    checked: p.checked,
  };
}
export type Summary = ReturnType<typeof summary>;
