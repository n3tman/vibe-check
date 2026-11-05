# Lane 8 (spare): SDKs

Follow `prompts/_research.md`. Your notes file is `notes/08.md`. Run only when budget remains.

Scope: Matrix SDKs and libraries on https://matrix.org/ecosystem/sdks/ and beyond:
matrix-js-sdk, matrix-rust-sdk, matrix-react-sdk's successors, matrix-dart-sdk, Trixnity,
libQuotient, mtxclient, mautrix-go / -python, matrix-nio, matrix-bot-sdk, Ruma, simplematrixlib,
… One file per SDK in `data/projects/sdk/`, `kind` = language. Features: `e2ee` (and which
crypto: vodozemac, libolm, own), `sliding_sync`, `oidc_auth`, `threads`, `spaces`, and which
clients, bots and bridges in `data/projects/` use it (a list of slugs, from their `sdk` or
`framework` fields once merged; otherwise from the SDK's own "used by" list).
