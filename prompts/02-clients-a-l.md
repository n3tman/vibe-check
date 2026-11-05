# Lane 2: clients, slugs a to l

Follow `prompts/_research.md`. Your notes file is `notes/02.md`.

Scope: every Matrix client whose slug starts with a to l: the matrix.org clients list, the
extra clients in `PLAN.md` "Sources" (Cinny, Commet, Element Web and Element X, FluffyChat
and the others in range), and any you find. Lane 3 does m to z with the same sources; both
of you build the full catalogue, and each writes only its own half.

Also check https://github.com/matrix-axon/matrix-axon: decide its category from the repo;
if it is a client, it is yours; otherwise put it in your notes under "For lane N".

Client specifics:
- Fill every client feature in `docs/schema.md`, especially `sdk`, `sliding_sync`,
  `oidc_auth`, `e2ee`, `cross_signing`, `key_backup`, `threads`, `spaces`, `telemetry`,
  `default_homeserver` and `fork_friendliness`.
- Fill `apps` for every OS the client ships for: is there a mobile app (Android, iOS, or the
  smaller mobile OSes), what tech it is built with, the lowest OS version supported, its
  status, and the stores it is in (store pages are good sources). A web client with no
  mobile app says so; a PWA counts as `tech: pwa`, not as a native app.
- One project, several repos: Element has Web, Desktop, X Android, X iOS; FluffyChat ships
  one Flutter repo. List every repo with its `role`, one YAML file per product family
  (`element-web`, `element-x`, … are separate slugs when they are separate apps).
- Forks (Sable from Cinny, SchildiChat from Element, …): set `fork_of` and note what the
  fork adds.
