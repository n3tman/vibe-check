# UI polish round (site only)

Picked from the proposals: direction C (polish), the readable heatmap, collapsing "nothing
found", and the list of small fixes. Touches only `site/` and `notes/ui-polish.md` (plus one
anchor id on the methodology page).

## Done
- Project page stat tiles: release tags show the version big and the package or branch prefix
  small (`@scope/pkg@2.1.0` → `2.1.0`), in the monospace face, sized to the tile with a
  container query; the full tag stays in `title`. Dates older than 60 days show the month
  ("Aug 2025") with the relative time underneath. Stars and open issues/PRs are left out while
  the forge APIs return nothing for them (null for all 271 projects today); empty values get a
  dashed "nil" tile. The tiles fill whole rows (6 across, 3 × 2, 2 × 3).
- AI section: when all three axes are "none found" and there is no quote or collector
  disagreement, one panel replaces the three; notes and the collector line stay. Short panels
  no longer stretch to the tallest one.
- Activity: the heatmap scales to the panel width (scrolls on phones, starting at the latest
  weeks), marks the collection day, and has a hover and keyboard tooltip (arrow keys,
  Home/End). A year without commits shows one line instead of empty charts.
- Cards: flat by default, the whole card is the link (hover lift and focus ring), AI marks and
  feature chips pinned to the bottom so they line up across a row, features not found fold
  into one chip, a year without commits is text instead of a flat sparkline.
- Header: nav no longer clipped at 1280 px (one row from 1200 px, measured 44 px spare); the
  fade on the scrolling nav goes away at its end where scroll-driven animations exist.
- Colour tokens written once with `light-dark()`; browsers without it get the light palette.
- New logo mark (a check inside Matrix brackets), also the favicon.
- `text-wrap: balance` on headings, `pretty` on paragraphs; long URLs in project notes wrap
  (the Jenkins plugin page scrolled sideways at 390 px before).

## Checked
`npm run build`, then `scripts/screenshots.mjs` over the default pages plus the Jenkins,
NeoBoard, vommet and SchildiChat Next pages and the bot and SDK lists: no console errors, no
sideways scroll at 390 or 1280 px, both themes.

## Open
- vommet reports 41,333 tags in a year (its `pre-sync/...` tags): a collector question, not UI.
