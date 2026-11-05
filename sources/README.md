# Sources (read-only inputs, shared by every lane)

## `community-space.tsv`
Every room and subspace listed in the `#community:matrix.org` space's hierarchy, as Element
showed it on 2026-11-05 (408 rows, tab-separated). Columns: `section` (the subspace it sits in:
Chat Clients, Not-chat Clients, Bots, Bridges, Servers/Hosting, SDKs, Other Projects, …, or
"(top level)"), `type` (room or space), `members`, `archived` (yes when the name or topic says
archived, deprecated or obsolete: a guess, rooms marked "(OLD)" are left blank), `name`,
`topic` (links kept as `text <url>`).

Use it as a list of leads: a room points to a project, the project counts once it has a
reachable repo or homepage. Many rooms are old or replaced; a room's member count says
nothing about the project's current state. Filter by section first, for example:
`awk -F'\t' '$1 ~ /Chat Clients/' sources/community-space.tsv`.

## `candidates.tsv`
Repositories that the discovery sweep found and that no project file names yet (generated, not
hand-edited). Each is a lead for triage, not a project: triage turns it into a project file or
gives a reason to leave it out.

Regenerate it with:

```
git clone --filter=blob:none --no-checkout https://github.com/matrix-org/matrix.org cache/matrix.org-site
git -C cache/matrix.org-site sparse-checkout set --no-cone '/content/blog/**/*.md'
git -C cache/matrix.org-site checkout main
GH_TOKEN=… GITLAB_TOKEN=… uv run --project collector vibecheck-discover
```

`GITLAB_TOKEN` is optional: a gitlab.com personal access token with the `read_api` scope, sent
only to gitlab.com. Without it, gitlab.com rate-limits the per-project lookups after a few
hundred calls and asks for waits of up to an hour; those rows then stay without metadata.

Sources: the repository topics in `TOPICS` (`collector/src/vibecheck/discover.py`) on GitHub
(search API, sliced by creation date under 1,000 results, forks left out by the search),
GitLab.com (`/api/v4/projects?topic=`) and Codeberg (`/api/v1/repos/search?topic=true`); the
awesome lists that a GitHub search finds and whose README is about Matrix; and every This Week
in Matrix post in the matrix.org website repository. Repositories found only through the
`matrix` or `element` topics (also maths and UI words) are kept only when another Matrix topic,
the description or, with no description, the README names Matrix. API responses are cached in
`cache/discover/`; `--refresh` fetches them again. A summary of the last run is in
`cache/discover-log.json`. `--topic-report` lists Matrix-looking topics on five or more kept
repositories that `TOPICS` doesn't have yet.

Repositories that are archived, no longer exist, or have had no push for two years (`--years`)
are left out. Repositories on forges whose API isn't read (SourceHut, self-hosted ones) have no
date and stay in.

Columns:
- `url`: the repository (the forge's current name when it was renamed or moved).
- `forge`: `github`, `gitlab`, `forgejo`, `gitea`, `sourcehut`.
- `name`, `description`, `stars`, `archived` (`no`, or blank when unknown), `pushed_at` (last
  push, any branch; GitLab: last activity): from the forge API when it was read.
- `sources`: where it was found, `; `-separated: `gh:<topic>`, `gitlab:<topic>`,
  `codeberg:<topic>`, `awesome:<list owner>`, `twim:<date>` or `twim:<n> posts <first>..<last>`.
- `twim_last`, `twim_posts`, `twim_heading`: the latest This Week in Matrix post linking it, the
  number of posts, and the heading the link sat under in the latest one (usually the project's name).
- `found`: the number of sources; all This Week in Matrix posts count as one. Rows are sorted by
  `found`, then `stars`.
- `same_name_as`: the slug of a project whose slug, name or repository name matches this
  repository's name: often a fork, a mirror or a move of a listed project, sometimes a coincidence.
