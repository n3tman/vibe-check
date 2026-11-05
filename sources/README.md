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
