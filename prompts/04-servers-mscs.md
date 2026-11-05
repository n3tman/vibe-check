# Lane 4: servers and the MSC matrix

Follow `prompts/_research.md`. Your notes file is `notes/04.md`. You also own
`data/mscs.yaml`.

Scope: every Matrix homeserver on the matrix.org servers list and any you find (Synapse,
Dendrite, Conduit, conduwuit and its successors such as continuwuity and Tuwunel, Grapevine,
Construct, and the rest; archived ones too, marked archived). Include the server-side pieces
that the servers list carries (Matrix Authentication Service, sliding sync proxy, …) as
`category: server` with a `kind` that says what they are.

MSC work, the core of this lane:
1. For each server, find every MSC it implements: grep the code for `msc\d{3,4}` (config
   flags, unstable prefixes like `org.matrix.msc3575`, route definitions, feature lists in
   `/_matrix/client/versions` `unstable_features`). Record each in `features.msc` with its
   `state` (stable, unstable, experimental, partial, removed), the flag that enables it, and a
   source pinned to a commit.
2. Record the spec versions each server advertises (`spec_versions`).
3. Build `data/mscs.yaml` for every MSC that any server (or client lane note) mentions: title
   and status from https://github.com/matrix-org/matrix-spec-proposals (PR state and labels:
   `proposal-in-review`, `finished-final-comment-period`, `spec-pr-merged`, `obsolete`, …) and
   the spec version it landed in (the spec changelog at https://spec.matrix.org/).
4. In your notes, list the MSCs that matter most to users (sliding sync, next-gen auth,
   authenticated media, MatrixRTC, threads, extensible events, …) so the site's MSC matrix can
   lead with them.

Optional, if time: query `/_matrix/client/versions` and `/_matrix/federation/v1/version` of
a few large public servers per implementation to confirm what versions run in the wild
(read-only GETs, one at a time).
