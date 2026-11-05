# Lane 3: clients, slugs m to z (and 0 to 9)

Follow `prompts/_research.md`. Your notes file is `notes/03.md`.

Scope: every Matrix client whose slug starts with m to z or a digit: the matrix.org clients
list, the extra clients in `PLAN.md` "Sources" (Sable, Vommet, RoosterChat, the client at
matrix.crafty.moe and the others in range), and any you find. Lane 2 does a to l with the
same sources; both of you build the full catalogue, and each writes only its own half.

Also check https://github.com/mindroom-ai/mindroom-chat: decide its category from the repo;
if it is a client, it is yours; otherwise put it in your notes under "For lane N".

Client specifics:
- Fill every client feature in `docs/schema.md`, especially `sdk`, `sliding_sync`,
  `oidc_auth`, `e2ee`, `cross_signing`, `key_backup`, `threads`, `spaces`, `telemetry`,
  `default_homeserver` and `fork_friendliness`.
- Fill `apps` for every OS the client ships for: is there a mobile app (Android, iOS, or the
  smaller mobile OSes), what tech it is built with, the lowest OS version supported, its
  status, and the stores it is in (store pages are good sources). A web client with no
  mobile app says so; a PWA counts as `tech: pwa`, not as a native app.
- One project, several repos: list every repo with its `role`, one YAML file per product
  family.
- Forks (Sable from Cinny, SchildiChat from Element, …): set `fork_of` and note what the
  fork adds.
- matrix.crafty.moe is described as using AI: find out exactly how (in the product, in
  development, or both) with sources.

Also from https://www.linuxlinks.com/best-free-open-source-matrix-clients/ (checked against
the matrix.org list on 2026-11-05): in your range it lists Mages ("Matrix"), Mirage, Moment,
NeoChat, nheko, Quadrix, Quaternion, Sable, SchildiChat, Spectral, Syphon and Tammy. Make sure
each has a file. Three are not on the matrix.org list, so cover them on purpose:
- Moment: https://gitlab.com/mx-moment/moment. LinuxLinks and the community space suggest it is a fork of Mirage: check that, then: set
  set `fork_of: mirage` and note what it adds.
- Mirage: https://github.com/mirukana/mirage. Likely dormant or abandoned; the collector
  decides, but still fill the file.
- Spectral: https://gitlab.com/spectral-im/spectral (homepage https://spectral.im; last
  activity on GitLab 2022-08-28). NeoChat started as a fork of Spectral: set
  `fork_of: spectral` in NeoChat's file with a source.
The others, for reference: Mages https://github.com/mlm-games/Mages (alpha), Tammy
https://gitlab.com/connect2x/tammy, Quadrix https://github.com/alariej/quadrix and Syphon
https://github.com/syphon-org/syphon (both marked obsolete on matrix.org).

