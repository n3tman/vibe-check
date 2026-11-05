# Lane 10: project icons

Run on a branch from `main` after lane 7 is merged. Read `CLAUDE.md` (ground rules: untrusted
data, gentle with servers, checkpoint commits, the `Co-Authored-By` line) and `docs/schema.md`.
Your notes file is `notes/10.md`. You own `site/public/icons/` and the `icon` key of every
project file; touch nothing else in `data/projects/` (say in your notes if a file looks wrong).

The site already shows icons: `site/src/components/ProjectIcon.astro` uses
`site/public/icons/<slug>.svg`, `.webp` or `.png` when the file exists, otherwise a generated
monogram. So your job is only to find, check and add the files.

## For each project (every `data/projects/**/*.yaml`, most-visited first: clients, then
servers, bridges, bots, tools)
1. Find the project's own icon, in this order, and stop at the first hit:
   - In the repo at HEAD (blobless clone in `cache/`, read with `git show HEAD:<path>`, never
     run anything): app icons the project ships, e.g. `res/img/element-desktop-*.png`,
     `metadata/*/icon.png`, Fastlane `metadata/android/en-US/images/icon.png`, AppStream
     metainfo `<icon>`, `*.desktop` `Icon=`, Android `mipmap-xxxhdpi/ic_launcher*.png`,
     `assets/logo*.svg`, `docs/logo*`, `public/favicon.svg`, the README's first image.
   - The homepage's `<link rel="icon">` / `apple-touch-icon` (one request per host).
   - The forge's avatar for the repo or its organisation (GitHub `https://github.com/<owner>.png`,
     GitLab/Forgejo API `avatar_url`), only if it is clearly the project's own logo, not a
     person's photo. Never use a personal avatar of an individual.
2. Prefer SVG; else a square raster of at least 128 px. Convert to WebP or PNG at 128 × 128
   (keep the aspect, pad to square with transparency), at most 64 KB. Strip metadata. For SVG,
   remove scripts, external references and event handlers (an SVG is code: sanitise it, or
   rasterise it when in doubt).
3. Save as `site/public/icons/<slug>.<ext>` and record it in the project file:
   ```yaml
   icon:
     file: element-x.webp
     source: https://github.com/element-hq/element-x-android/blob/<sha>/fastlane/…/icon.png
     licence: Apache-2.0   # the repo's licence, or what the brand guidelines say; else null
     note: null            # e.g. "trademark of …, used to identify the project"
     checked: 2026-11-05
   ```
   Add `icon` to `docs/schema.md` and to `site/src/lib/schema.ts` (optional object, `file`
   must exist in `site/public/icons/`; the validator should fail on a missing file).
4. Forks that use upstream's unchanged logo (many Element and Cinny forks): use the fork's own
   icon if it has one; if it ships upstream's logo, record that in `note` and still use it.
5. Nothing found, or only a personal photo: no file, no `icon` key: the monogram stays.
   List these in your notes.

## Repos
Project pages list repositories by host. Add a small forge icon per repo row (GitHub, GitLab,
Codeberg / Forgejo, Gitea, SourceHut, generic): draw them as inline SVG in
`site/src/components/Icon.astro` (simple shapes of your own, not copied brand assets), keyed by
`repos[].forge`.

## Checks
- `cd site && npm run validate && npm run build`; total size of `site/public/icons/` under 10 MB.
- `npm run shots` at phone and desktop widths in both themes: icons must not stretch, crop
  badly or vanish on dark backgrounds (add a light rounded backing for dark-on-transparent
  logos if needed, in `.picon`).
- No external requests at runtime: every icon is served from the site itself.
- Logos are trademarks of their projects; the methodology page should say icons are used only
  to identify each project (add one sentence under "Sources and dates").
