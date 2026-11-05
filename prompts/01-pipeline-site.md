# Lane 1: collector and site

Read `CLAUDE.md`, `PLAN.md` and `docs/schema.md` first. Your notes file is `notes/01.md`.
You write the code; lanes 2 to 6 write the data at the same time, so build against the
schema and a few fixtures, not against their files.

## Collector (`collector/`, Python 3.12, managed with uv)
- Input: every `data/projects/**/*.yaml` (and `fixtures/projects/**/*.yaml` with `--fixtures`).
  Write three or four fixtures yourself (a client with three repos on GitHub, a server, a
  project on Codeberg or GitLab.com, one with `repos: []`), with real repo URLs.
- Per repo: blobless clone or fetch into `cache/repos/` (reuse and `git fetch` when present),
  then compute every metric in `docs/schema.md` "Metrics" from `git log` (bot authors
  filtered, `.mailmap` honoured, authors deduplicated by email and name), plus forge API data:
  GitHub (REST or GraphQL, `$GH_TOKEN`), GitLab (any instance, `/api/v4`), Forgejo / Gitea
  (`/api/v1`), SourceHut where possible. A forge it can't read gives `null`s, not a crash.
- `ai_scan` and `telemetry_scan` exactly as `CLAUDE.md` "AI rubric" and `docs/schema.md`
  describe: file presence from `git ls-tree`, commit trailers and bot authors from `git log`,
  workflows from `.github/workflows/`, `.gitlab-ci.yml`, `.forgejo/workflows/`; telemetry from
  dependency manifests (package.json, Cargo.toml, pubspec.yaml, build.gradle*, go.mod,
  pyproject.toml, …): Sentry, PostHog, Matomo, Firebase Analytics / Crashlytics, Mixpanel,
  Amplitude, Segment, Bugsnag, Datadog, …
- Lines of code with `scc` or `tokei` on a shallow checkout (download a release binary; never
  build the scanned repo).
- `status` per `CLAUDE.md` "Activity status".
- Output `data/metrics/<slug>.json`; idempotent; `--only <slug>`, `--since-cache` and a
  parallelism limit per forge host; a short summary at the end (repos done, failed, why).
- Tests with pytest for the parsers (trailers, bot filter, bus factor, status thresholds).

## Site (`site/`, Astro, static)
- Read `data/projects/`, `data/metrics/`, `data/mscs.yaml` at build time, validate against
  the schema (fail the build on a malformed file, with the file name), and render everything
  `CLAUDE.md` "Site" lists: overview, category pages (sortable, filterable table plus cards),
  project pages, the server × MSC matrix, compare, methodology.
- At a glance, per project card: name, kind, platforms (for clients: OS icons from `apps`,
  with mobile clearly visible, and a "mobile" filter on the clients page), licence, main
  language, the activity
  badge, a 52-week sparkline, authors in 90 days, last release, the three AI marks, and the
  headline features of its category as icons with text.
- Project page: every feature with its evidence link, the daily heatmap, weekly bars,
  authors per quarter, language bar, AI evidence list, health signals (bus factor, issue
  response, release cadence, CI, tests, security policy, funding), and "checked on" dates.
- Design: make it beautiful and calm: a clear type scale, generous spacing, good contrast in
  both themes, responsive down to phones, keyboard and screen-reader friendly (WCAG AA). Self-
  hosted variable font. Check it in a headless browser (Playwright) at phone and desktop
  widths in both themes and fix what looks wrong.
- The AI stance switch and the theme switch exactly as `CLAUDE.md` describes, both remembered.

## Publishing (`.github/workflows/`)
- `deploy.yml`: on push to `main`, build `site/` and deploy to GitHub Pages
  (actions/upload-pages-artifact + actions/deploy-pages). The base path is `/vibe-check/`.
- `refresh.yml`: weekly (and manual) run of the collector with the workflow's `GITHUB_TOKEN`,
  committing changed `data/metrics/` to `main` with a plain-sentence message, which triggers
  the deploy.
- `ci.yml`: on pull requests, pytest, schema validation and a site build.

## Finish (by 2:15 after the start)
- `README.md` "Develop" section: how to run the collector and the site locally.
- `notes/01.md`: what works, what doesn't, what lane 7 must do. Push; tell the user the branch.
