// The whole dataset as one JSON file, for reuse under CC BY 4.0.
import type { APIRoute } from 'astro';
import { dataset } from '../lib/data.ts';
import { statusOf } from '../lib/view.ts';

export const GET: APIRoute = () => {
  const d = dataset();
  const body = {
    licence: 'CC BY 4.0',
    source: 'https://n3tman.github.io/vibe-check/',
    generated: new Date().toISOString(),
    collector_run: d.collector?.run_at ?? null,
    mscs: d.mscs,
    projects: d.projects.map(({ metrics, file, ...p }) => {
      const c = metrics?.combined ?? null;
      const { daily_commits, ...combined } = c ?? {};
      return { ...p, status: statusOf(p), metrics: c ? { fetched_at: metrics!.fetched_at, ...combined } : null };
    }),
  };
  return new Response(JSON.stringify(body, null, 1), { headers: { 'content-type': 'application/json' } });
};
