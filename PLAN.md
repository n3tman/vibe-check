# Plan

Research every Matrix client, server, bot and bridge we can find, collect comparable
development metrics for each repo, and publish a static comparison site with an AI stance
switch. Six sessions run in parallel on their own branches, then one integrates and publishes.

## Lanes
| Lane | Prompt | Owns (writes only these) | Needs |
|---|---|---|---|
| 1 | `prompts/01-pipeline-site.md` | `collector/`, `site/`, `.github/`, `fixtures/`, `data/metrics/`, `README.md`, `notes/01.md` | nothing |
| 2 | `prompts/02-clients-a-l.md` | `data/projects/client/` slugs a to l, `notes/02.md` | nothing |
| 3 | `prompts/03-clients-m-z.md` | `data/projects/client/` slugs m to z (and 0 to 9), `notes/03.md` | nothing |
| 4 | `prompts/04-servers-mscs.md` | `data/projects/server/`, `data/mscs.yaml`, `notes/04.md` | nothing |
| 5 | `prompts/05-bots-integrations.md` | `data/projects/bot/`, `data/projects/tool/`, `notes/05.md` | nothing |
| 6 | `prompts/06-bridges.md` | `data/projects/bridge/`, `notes/06.md` | nothing |
| 7 | `prompts/07-integrate-publish.md` | everything | lanes 1 to 6 merged into `main` |
| 8 (spare) | `prompts/08-sdks.md` | `data/projects/sdk/`, `notes/08.md` | nothing; run only if budget remains |
| 9 | `prompts/09-clients-linuxlinks.md` | `data/projects/client/` for `mirage`, `moment`, `spectral` only, `notes/09.md` | nothing; added after lanes 2 and 3 started |

Lanes 1 to 6 write disjoint files, so their branches merge into `main` without conflicts.
A lane that finds a project of another lane's category adds it to its notes under "For
lane N", never writes the file itself.

## Timing (the credit runs about four hours)
- 0:00 start lanes 1 to 6 together.
- Every lane pushes a checkpoint at least every 30 to 45 minutes and stops by 2:15, with its
  notes saying what is done and what is left.
- About 2:15 the user merges the six branches into `main` (pull requests, no conflicts
  expected).
- 2:20 start lane 7 on `main`: run the collector over every project, fill the gaps, polish,
  publish. Lane 8 can run beside it if there is budget.

## Sources
- The official lists: https://matrix.org/ecosystem/clients/, `/servers/`, `/integrations/`,
  `/bridges/`. Their data probably lives in the website's own repo
  (https://github.com/matrix-org/matrix.org): find the per-project files there first, they
  carry repo links, maturity and platforms in a structured form.
- The community space `#community:matrix.org` (many rooms are old or replaced), already
  extracted to `sources/community-space.tsv` (see `sources/README.md`): sections Chat Clients
  and Not-chat Clients (lanes 2, 3), Servers/Hosting (4), Bots and Other Projects (5),
  Bridges (6), SDKs (8). Room directories that need no account: https://matrixrooms.info (its
  search API). Use rooms only as a pointer to projects; a project counts if it has a
  reachable repo or a homepage.
- Projects not on matrix.org that must be covered:
  - Clients: https://vommet.app, https://pondlabs.github.io/roosterchat/,
    https://next.sable.moe (Sable, a Cinny fork), https://commet.chat, https://cinny.in,
    https://fluffychat.im, https://matrix.crafty.moe/ (says it uses AI)
  - Bots and tools: https://github.com/etkecc/komai
  - Category to check first: https://github.com/matrix-axon/matrix-axon (lane 2 checks it:
    if it isn't a client, it goes in lane 2's notes "For lane N"),
    https://github.com/mindroom-ai/mindroom-chat (lane 3, the same way)
- Third-party roundup (clients): https://www.linuxlinks.com/best-free-open-source-matrix-clients/
  (LinuxLinks, 22 clients, published 2026-08-10, no repo links). Checked against the
  matrix.org list on 2026-11-05 (website repo at `041599b`): 18 of the 22 are on it. The four
  that are not (Moment, Mirage, Spectral, and "Chats", the current name of Chatty) are lane
  9's, added after lanes 2 and 3 had started.
- Forges: GitHub, GitLab.com, Codeberg and other Forgejo / Gitea hosts, SourceHut, and
  self-hosted GitLab or Forgejo instances. Use each forge's API for what git can't give
  (stars, issues, archived flag, languages); use `git log` on a blobless clone for activity,
  so every forge gets the same numbers.
- Searches (to find what the lists miss): GitHub topics `matrix-client`, `matrix-org`,
  `matrix-bot`, `matrix-bridge`, `matrix-homeserver`; awesome lists
  (https://github.com/jryans/awesome-matrix and newer ones); This Week in Matrix posts from
  the last year (https://matrix.org/category/this-week-in-matrix/).

## Ideas beyond the brief (lane 7 picks what fits)
- SDKs (lane 8) and moderation, admin and deployment tools (Draupnir, Meowlnir, Mjolnir,
  synapse-admin / Ketesa, matrix-docker-ansible-deploy, the Element Server Suite charts).
- "Fork-friendliness" for clients: lines of code, build steps, licence obligations, SDK.
- Privacy at a glance: telemetry SDKs found in dependency manifests, the default homeserver,
  URL previews on by default.
- Health signals: bus factor, issue first-response time, release cadence, security policy,
  CI, tests, funding links, translation platform, store availability (F-Droid, Flathub).
- A "spec support" view: which spec version each client and server targets.
- A changelog of the data (what changed since the last weekly refresh), driven by the
  scheduled collector workflow.
- An RSS or JSON feed of the dataset so others can reuse it (data under CC BY 4.0).
