# Project file schema

One YAML file per project: `data/projects/<category>/<slug>.yaml`. The slug is lowercase
kebab-case and unique across categories. The values below show the shape only; none of them
is checked.

## Common fields
```yaml
slug: cinny
name: Cinny
category: client            # client | server | bot | bridge | sdk | tool
kind: web                   # free text within the category: web, desktop, mobile, terminal,
                            # homeserver, moderation, puppeting bridge, …
homepage: https://cinny.in
summary: One neutral line on what it is.
repos:                      # the collector reads these
  - url: https://github.com/cinnyapp/cinny
    forge: github           # github | gitlab | forgejo | gitea | sourcehut | other
    role: main              # main | desktop | android | ios | server | other | mirror | upstream
                            # upstream: a library the app builds on (Trixnity for Tacit), measured
                            # but left out of the project's own numbers; mirror: the same code
                            # elsewhere, counted once (repos sharing half their commits are
                            # treated the same way automatically)
sources:                    # where the project was found
  matrix_org_listing: https://matrix.org/ecosystem/clients/cinny/   # or null
  other: []                 # reddit post, the matrix.org community space, a blog, …
maturity: stable            # alpha | beta | stable | unmaintained | archived (matrix.org's
                            # label when listed, else our own reading; say which in notes)
platforms: [web, windows, macos, linux]   # web | windows | macos | linux | android | ios | terminal | server
apps:                       # clients only: one entry per OS the project ships for
  - os: android             # android | ios | ipados | windows | macos | linux | web |
                            # terminal | sailfish | ubuntu-touch | harmonyos | other
    tech: flutter           # native | flutter | react-native | electron | tauri | qt | gtk |
                            # webview | pwa | tui | other
    min_os: "7.0"           # lowest OS version the project states, else null
    status: stable          # alpha | beta | stable | discontinued
    stores: [{name: f-droid, url: https://f-droid.org/packages/…}, {name: google-play, url: …}]
                            # google-play | f-droid | izzyondroid | app-store | testflight |
                            # flathub | snap | microsoft-store | homebrew | aur | apk | dmg | …
    source: https://…       # where the OS support is stated
licence: AGPL-3.0-only      # SPDX id
fork_of: null               # slug or URL when the project is a fork (Sable, …)
distribution: [flathub]     # f-droid | google-play | app-store | flathub | snap | aur | docker | …
funding: [https://opencollective.com/cinny]
features: {}                # per category, below
ai:
  policy:     {value: none-found, quote: null, source: null}
  dev_usage:  {value: none-found, evidence: []}   # the collector fills evidence; a lane may add
  in_product: {value: none-found, note: null, source: null}
notes: >-
  Anything a reader should know that fits no field.
checked: 2026-11-05
```

## Feature values
Every feature is either a bare value or a map with evidence:
```yaml
threads: {value: yes, how: code, source: https://github.com/…/blob/<sha>/src/…}
```
- `value`: `yes` | `partial` | `no` | `planned` | `not-found`
- `how`: `claimed` (README, docs, store page) | `code` (seen in the source) | `tested`
- `source`: a URL, pinned to a commit where possible
- `note`: optional, short

## Client features
`sdk` (matrix-js-sdk, matrix-rust-sdk, matrix-dart-sdk, Trixnity, libQuotient, mtxclient,
mautrix-go, own, …), `e2ee`, `cross_signing`, `key_backup`, `sliding_sync` (MSC4186
simplified sliding sync, or the older MSC3575 proxy: say which in the note), `oidc_auth`
(next-gen auth, MSC3861 family / MAS), `multi_account`, `threads`, `spaces`, `voip_1to1`,
`group_calls` (Element Call / MatrixRTC), `reactions`, `edits`, `replies`, `polls`,
`custom_emoji` (MSC2545 image packs), `stickers`, `location`, `voice_messages`,
`rich_text_editor`, `url_previews`, `push_notifications`, `private_read_receipts`,
`presence`, `room_upgrades`, `moderation_tools`, `accessibility` (screen-reader work found?),
`translations` (platform and language count), `telemetry` (`none-found` (looked, none) |
`not-found` (could not tell) | `opt-in` | `opt-out`, name the service: Sentry, PostHog, Matomo,
…; when the collector finds an SDK in the manifests and the value is `none-found` or
`not-found`, a `note` says why, or `npm run validate` warns), `default_homeserver` (matrix.org or
none or another), `fork_friendliness` (size in lines, build complexity, licence obligations:
a short note for someone who would fork it).

## Server features
`language`, `database` (PostgreSQL, SQLite, RocksDB, …), `federation`, `spec_versions` (the
`versions` list the code advertises in `/_matrix/client/versions`), `appservices`,
`admin_api`, `oidc_delegation` (MSC3861 / MAS), `native_sliding_sync`, `workers_scaling`,
`media_auth` (authenticated media, MSC3916), `resource_needs` (RAM figure quoted by the
project, with source), `msc` (a list, below).

```yaml
msc:
  - {msc: 4186, state: stable, flag: null, source: …}    # state in this server:
  - {msc: 3861, state: experimental, flag: experimental_features.msc3861, source: …}
```
`state`: `stable` (stable endpoints or always on) | `unstable` (unstable prefix, on by
default) | `experimental` (behind a flag) | `partial` | `removed`. The MSC's own spec status
(merged into the spec, in FCP, open, closed) lives once in `data/mscs.yaml`, not here:
```yaml
- msc: 4186
  title: Simplified sliding sync
  status: merged          # merged | fcp | open | closed | postponed
  spec_version: null      # the spec release it landed in (from the spec changelog), else null
  url: https://github.com/matrix-org/matrix-spec-proposals/pull/4186
```

## Bot and integration features
`purpose` (moderation, notifications, RSS, translation, bridging helper, games, …),
`framework` (the SDK), `e2ee`, `hosting` (self-host, hosted service, both), `config`
(commands, web UI, config file), `ai_backend` (which LLM APIs it calls, if any: this also
feeds `ai.in_product`).

## Bridge features
`network` (IRC, Telegram, Signal, WhatsApp, Discord, Slack, XMPP, email, …), `framework`
(mautrix bridgev2, matrix-appservice-bridge, own), `puppeting` (double, single, relay),
`e2ee`, `backfill`, `media`, `reactions_edits`, `group_chats`, `login_methods`,
`network_tos_risk` (does using it break the other network's terms? quote the project's own
warning when it has one).

## Metrics (generated, `data/metrics/<slug>.json`)
Per repo: `default_branch`, `first_commit`, `last_commit`, `commits_30d` / `90d` / `365d`,
`authors_90d` / `365d` / `all`, `bus_factor_365d` (fewest authors making 50 % of last-year
commits), `weekly_commits` (52 numbers), `daily_commits` (date → count, last 365 days),
`authors_by_quarter`, `languages` (share by bytes), `loc` (lines of code by language),
`last_tag`, `last_tag_date`, `tags_365d`, `stars`, `forks`, `open_issues`, `open_prs`,
`issue_first_response_median_days` (issues opened in the last 180 days), `archived`,
`licence_detected`, `security_policy`, `ci`, `tests_present`, `ai_scan` (agent files with
paths, attributed commits and their share, bot authors, AI workflows), `telemetry_scan`
(analytics or crash-report SDKs found in dependency manifests), `status` (CLAUDE.md
"Activity status"), `fetched_at`, `head_sha`. Fields a forge can't give are `null`.

## Additions made by the lanes (reconciled in lane 7)
- `repos[].first_parent: true`: the collector follows only the branch's own line
  (`git log --first-parent`), for forks that merge upstream, so upstream's commits are not
  credited to the fork (SchildiChat, Sable v1, Rooster, Vommet).
- `icon` (optional, lane 10): the project's own logo, served from `site/public/icons/`.
  `file` (`<slug>.svg`, `.webp` or `.png`; must exist, the validator fails otherwise), `source`
  (the file at a commit, or the page it came from), `licence` (the repo's licence or what the
  brand guidelines say, else null), `note` (e.g. a fork that ships upstream's logo), `checked`,
  and `backing: light | dark` for a dark or light logo on a transparent background (the site
  puts it on a tile of the opposite tone where it would vanish).
  An icon file without this key also fails validation. No key: the site draws a monogram.
- `ai.dev_usage.note`: free text shown under the mark. `ai.dev_usage.checked_at`: the commit read.
- `ai.dev_usage.collector_override`: one sentence saying why the file's value differs from the
  collector's `suggested_dev_usage` (a refusal-only `AGENTS.md`, history rewritten to strip
  trailers, …). The project page shows it instead of "not reconciled yet".
- `ai.funder_policy`: a list, one entry per funder with an AI policy for the work it pays for:
  `funder`, `grant` (URL), `grant_start`, `grant_end` (when the grant has ended), `grant_source`
  (the README line or funding page that states the grant), `policy` (URL), `policy_version` (the
  version that binds this grant, from its dates and the funder's transition rules), `value` (the
  policy enum; `none-found` for a grant that ended before the funder had a policy), `quote`,
  `scope`, `transition`, `transparency` (whether the stance statement the funder asks for was found
  in the README), `checked`. Never merged into `ai.policy`. Example:
  ```yaml
  ai:
    funder_policy:
      - funder: NLnet Foundation (NGI Zero Core fund)
        grant: https://nlnet.nl/project/<Name>/
        grant_start: 2024-04
        grant_source: <README line or funding page that states the grant>
        policy: https://nlnet.nl/foundation/policies/generativeAI/2.0/
        policy_version: 2.0, in force since 2026-10-20
        value: banned
        quote: <the sentence>
        scope: work delivered within the grant
        transition: <what the FAQ says about this fund, or "not stated">
        transparency: <found / not found, with the file>
        checked: 2026-11-05
  ```
- `apps[].note`: short free text about one app (minSdk, unsigned builds).
- `features.crypto` (SDKs): free text naming the crypto library (vodozemac, libolm, …).

## Checks (`npm run validate`)
Errors stop the build: a file that does not match the schema, a feature value outside
`yes | partial | no | planned | not-found` (bare or in a map) for a key not listed in `FREE_TEXT`,
a telemetry value outside its list, a `fork_of` that is neither a slug nor a URL, a slug used
twice. Warnings are listed and fail only with `--strict`: a `yes`, `partial` or `no` without a
`source`, a client whose manifests name a telemetry SDK while `telemetry` says nothing was found
and has no `note`, a project with repositories but no metrics, a metrics file with no project.
- `features.spec_versions` (servers) may be a map with `versions: [...]` and a source.
- `data/mscs.yaml` entries may carry `status_detail`, `labels` and `servers`.
- Bot and tool features `purpose`, `framework`, `hosting`, `config`, `ai_backend` hold free text
  in `value` (listed in `FREE_TEXT` in `site/src/lib/schema.ts`).
