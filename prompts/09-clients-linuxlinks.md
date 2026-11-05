# Lane 9: clients from the LinuxLinks roundup

Follow `prompts/_research.md`. Your notes file is `notes/09.md`.

This lane was added while lanes 2 (clients a to l) and 3 (clients m to z) were already
running, so it fills only the gaps one source leaves and must not collide with them.

Source: https://www.linuxlinks.com/best-free-open-source-matrix-clients/ (LinuxLinks, 22
clients, published 2026-08-10, no repo links). Checked against the matrix.org clients list on
2026-11-05 (website repo `matrix-org/matrix.org` at `041599b`): 18 of the 22 are on it, so
lanes 2 and 3 cover them. The four that are not:

| Client | Repo | Notes |
|---|---|---|
| Moment | https://gitlab.com/mx-moment/moment | Said to be a fork of Mirage: check in the repo, then set `fork_of: mirage` and note what it adds |
| Mirage | https://github.com/mirukana/mirage | Probably dormant; the collector decides, fill the file anyway |
| Spectral | https://gitlab.com/spectral-im/spectral (homepage https://spectral.im) | Last GitLab activity 2022-08-28; NeoChat started as a fork of it |
| "Chats" | https://gitlab.gnome.org/World/Chatty | The current display name of Chatty (same repo). Chatty is on matrix.org, so lane 2 writes `chatty`; you write no file |

## Files you own
Only `data/projects/client/mirage.yaml`, `moment.yaml`, `spectral.yaml` and `notes/09.md`.
Lane 3 may have found Mirage or Moment through the community space anyway. Before writing each
file, and again before each push, run `git fetch origin` and check `main` and every
`origin/claude/*` branch for that path (`git ls-tree -r --name-only <ref> -- data/projects/client/<slug>.yaml`).
If it exists anywhere, don't write it: put what you found in your notes under "For lane 7"
instead, so the integration lane can merge the evidence into the one file.

## Not yours: notes "For lane 7"
Write these as checks for the integration lane, with sources, without editing the files:
- `neochat`: `fork_of: spectral`, with a source (NeoChat's README or history).
- `chatty`: add "Chats" as its newer name, with a source (the app's metadata or a release
  note).
- Cross-check the other 18 against the files lanes 2 and 3 pushed (Cinny, Commet, Element,
  Extera, FluffyChat, Fractal, Hydrogen, kazv, Mages, NeoChat, nheko, Quadrix, Quaternion,
  Sable, SchildiChat, Syphon, Tammy, Chatty). List any that have no file yet. Also note that
  matrix.org lists Extera twice (https://github.com/officialdakari/Extera, obsolete, and
  https://github.com/ExteraApp/Extera, "Extera Next") and that LinuxLinks calls it
  FluffyChat-derived: check that `fork_of` and the repo roles are right.
