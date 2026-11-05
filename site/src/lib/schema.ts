// The project file schema (docs/schema.md) as zod. The build fails on a file that does not
// match, naming the file and the field. Unknown extra fields are allowed (passthrough), so a
// lane can add a field before the schema learns about it; known fields must have the right
// shape.
import { z } from 'zod';

export const CATEGORIES = ['client', 'server', 'bot', 'bridge', 'sdk', 'tool'] as const;
export const FORGES = ['github', 'gitlab', 'forgejo', 'gitea', 'sourcehut', 'other'] as const;
export const PLATFORMS = ['web', 'windows', 'macos', 'linux', 'android', 'ios', 'terminal', 'server'] as const;
export const APP_OS = ['android', 'ios', 'ipados', 'windows', 'macos', 'linux', 'web', 'terminal', 'sailfish', 'ubuntu-touch', 'harmonyos', 'other'] as const;
export const APP_TECH = ['native', 'flutter', 'react-native', 'electron', 'tauri', 'qt', 'gtk', 'webview', 'pwa', 'tui', 'other'] as const;
export const FEATURE_VALUES = ['yes', 'partial', 'no', 'planned', 'not-found'] as const;
export const POLICY = ['banned', 'restricted', 'allowed', 'encouraged', 'none-found'] as const;
export const DEV_USAGE = ['none-found', 'config-only', 'occasional', 'regular'] as const;
export const IN_PRODUCT = ['none-found', 'optional', 'core'] as const;
export const MSC_STATE = ['stable', 'unstable', 'experimental', 'partial', 'removed'] as const;
export const MSC_STATUS = ['merged', 'fcp', 'open', 'closed', 'postponed'] as const;

const url = z.string().url();
const nullableUrl = url.nullable().optional();
// YAML dates may arrive as strings or Date objects depending on the parser.
const date = z.union([z.string().regex(/^\d{4}-\d{2}-\d{2}/), z.date()]).transform((d) => (d instanceof Date ? d.toISOString().slice(0, 10) : d.slice(0, 10)));

const repo = z
  .object({
    url,
    forge: z.enum(FORGES).optional(),
    role: z.string().optional(),
  })
  .passthrough();

const store = z.union([z.object({ name: z.string(), url: nullableUrl }).passthrough(), z.string()]);

const app = z
  .object({
    os: z.enum(APP_OS),
    tech: z.enum(APP_TECH).nullable().optional(),
    min_os: z.union([z.string(), z.number()]).nullable().optional(),
    status: z.enum(['alpha', 'beta', 'stable', 'discontinued']).nullable().optional(),
    stores: z.array(store).nullable().optional(),
    source: nullableUrl,
  })
  .passthrough();

const featureObject = z
  .object({
    value: z.union([z.string(), z.number(), z.boolean()]).nullable().optional(),
    how: z.enum(['claimed', 'code', 'tested']).nullable().optional(),
    source: z.union([url, z.array(url)]).nullable().optional(),
    note: z.string().nullable().optional(),
  })
  .passthrough();

const mscEntry = z
  .object({
    msc: z.number().int(),
    state: z.enum(MSC_STATE),
    flag: z.string().nullable().optional(),
    source: nullableUrl,
    note: z.string().nullable().optional(),
  })
  .passthrough();

export const feature = z.union([z.string(), z.number(), z.boolean(), z.null(), featureObject, z.array(z.any())]);

const evidence = z.union([z.string(), z.object({}).passthrough()]);

export const projectSchema = z
  .object({
    slug: z.string().regex(/^[a-z0-9][a-z0-9-]*$/, 'lowercase kebab-case'),
    name: z.string().min(1),
    category: z.enum(CATEGORIES),
    kind: z.string().nullable().optional(),
    homepage: nullableUrl,
    summary: z.string().nullable().optional(),
    repos: z.array(repo).default([]),
    sources: z
      .object({ matrix_org_listing: nullableUrl, other: z.array(z.union([url, z.string()])).nullable().optional() })
      .passthrough()
      .nullable()
      .optional(),
    maturity: z.enum(['alpha', 'beta', 'stable', 'unmaintained', 'archived']).nullable().optional(),
    platforms: z.array(z.enum(PLATFORMS)).nullable().optional(),
    apps: z.array(app).nullable().optional(),
    licence: z.string().nullable().optional(),
    fork_of: z.string().nullable().optional(),
    distribution: z.array(z.string()).nullable().optional(),
    funding: z.array(z.string()).nullable().optional(),
    features: z
      .record(z.string(), feature)
      .nullable()
      .optional()
      .superRefine((f, ctx) => {
        if (!f) return;
        if (f.msc !== undefined && f.msc !== null) {
          const r = z.array(mscEntry).safeParse(f.msc);
          if (!r.success) r.error.issues.forEach((i) => ctx.addIssue({ ...i, path: ['msc', ...i.path] }));
        }
        for (const [k, v] of Object.entries(f)) {
          if (k === 'msc') continue;
          if (Array.isArray(v)) continue;
          if (v && typeof v === 'object' && 'value' in v && typeof v.value === 'string' && k !== 'telemetry' && !isFreeText(k)) {
            if (!(FEATURE_VALUES as readonly string[]).includes(v.value))
              ctx.addIssue({ code: z.ZodIssueCode.custom, path: [k, 'value'], message: `"${v.value}" is not one of ${FEATURE_VALUES.join(', ')}` });
          }
        }
      }),
    ai: z
      .object({
        policy: z.object({ value: z.enum(POLICY), quote: z.string().nullable().optional(), source: nullableUrl }).passthrough(),
        dev_usage: z.object({ value: z.enum(DEV_USAGE), evidence: z.array(evidence).nullable().optional() }).passthrough(),
        in_product: z.object({ value: z.enum(IN_PRODUCT), note: z.string().nullable().optional(), source: nullableUrl }).passthrough(),
      })
      .passthrough(),
    notes: z.string().nullable().optional(),
    checked: date,
  })
  .passthrough();

// Features whose value is free text rather than yes / partial / no.
const FREE_TEXT = new Set([
  'sdk', 'language', 'database', 'spec_versions', 'resource_needs', 'default_homeserver', 'translations', 'fork_friendliness',
  'purpose', 'framework', 'hosting', 'config', 'ai_backend', 'network', 'puppeting', 'login_methods', 'network_tos_risk', 'accessibility',
]);
function isFreeText(k: string) {
  return FREE_TEXT.has(k);
}
export const isFreeTextFeature = isFreeText;

export const mscSchema = z.array(
  z
    .object({
      msc: z.number().int(),
      title: z.string(),
      status: z.enum(MSC_STATUS),
      spec_version: z.union([z.string(), z.number()]).nullable().optional().transform((v) => (v == null ? null : String(v))),
      url: nullableUrl,
    })
    .passthrough(),
);

// Metrics are generated, so the check is loose: the shape the pages read.
const repoMetrics = z
  .object({
    url: z.string(),
    forge: z.string(),
    role: z.string().nullable().optional(),
    ok: z.boolean(),
    error: z.string().nullable().optional(),
  })
  .passthrough();

export const metricsSchema = z
  .object({
    slug: z.string(),
    fetched_at: z.string(),
    combined: z.object({}).passthrough().nullable(),
    repos: z.array(repoMetrics),
  })
  .passthrough();

export type Project = z.infer<typeof projectSchema>;
export type Msc = z.infer<typeof mscSchema>[number];
