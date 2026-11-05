# Vibe check

The Matrix ecosystem at a glance: clients, servers, bots and bridges compared by features,
development activity, and how each project treats AI.

Site: https://n3tman.github.io/vibe-check/

- Data: `data/projects/` (researched and written by an AI agent, each claim with its source;
  not checked by a person), `data/metrics/` (generated weekly from the repositories),
  `data/mscs.yaml`.
- How the data is gathered and what the marks mean: the site's methodology page, and
  `CLAUDE.md`.
- Corrections are welcome as issues; please link the source.
- Researched and built with Claude (Anthropic) in Claude Code; each commit's
  `Co-Authored-By` line names the model and version that wrote it.

Code under the MIT licence (`LICENSE`); data under CC BY 4.0.

## Develop

Needs Python 3.12+ with [uv](https://docs.astral.sh/uv/), Node 22.6+, and git.

### Collector (`collector/`)

```bash
uv run --project collector vibecheck-collect
```

Reads every `data/projects/**/*.yaml`, keeps blobless clones in `cache/repos/` (gitignored) and
writes `data/metrics/<slug>.json` plus a run summary in `data/metrics/_collector.json`. Set
`GH_TOKEN` for the GitHub API. Useful flags: `--fixtures` (read `fixtures/` instead of `data/`),
`--only <slug>` (repeatable), `--since-cache` (no fetch, reuse the clones), `--max-age <hours>`
(skip fresh files), `--per-host <n>` (requests in flight per forge host, default 1), `--jobs <n>`,
`--no-api`, `--no-loc`. It never runs code from a scanned repository; `scc` (lines of code) is a
checksum-verified release download in `cache/bin/`.

```bash
uv run --project collector --group dev pytest collector/tests -q
```

### Site (`site/`)

```bash
cd site && npm ci
```

```bash
npm run dev
```

```bash
npm run build
```

Reads `data/` at build time (or `fixtures/` with `VIBE_DATA=fixtures`) and fails on a malformed
file, naming it. `npm run validate` checks the data without building. `npm run shots [dir]`
screenshots every page type at phone and desktop widths in both themes (needs Playwright; with
a global install, prefix `NODE_PATH=$(npm root -g)`).

### Workflows (`.github/workflows/`)

- `deploy.yml`: builds `site/` and publishes to GitHub Pages on every push to `main`. In the
  repository settings, Pages must use "GitHub Actions" as its source.
- `refresh.yml`: weekly (Mondays) and manual collector run; commits changed `data/metrics/` to
  `main`, then deploys.
- `ci.yml`: on pull requests, pytest, schema validation of `data/` and `fixtures/`, and both builds.
