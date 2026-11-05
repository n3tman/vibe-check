# Lane 7: integrate and publish

Run on `main` after lanes 1 to 6 are merged. Read `CLAUDE.md`, `PLAN.md`, `docs/schema.md`
and every `notes/*.md` first.

1. Schema check: build the site; fix every malformed project file (keep the facts, fix the
   shape). Reconcile duplicates (the same project written by two lanes, or slugs that clash).
2. "For lane N" items in the notes: research and add them now, most important first.
3. Run the collector over every project (`GH_TOKEN` set). Read its summary; fix collector
   bugs it shows; rerun the failed repos only.
4. Cross-check the AI marks: where a lane's `ai.dev_usage` judgment and the collector's
   `ai_scan` disagree, open the evidence and settle it in the project file, with a note.
5. Pick from `PLAN.md` "Ideas beyond the brief" what the data supports, cheapest first.
6. Polish: headless-browser screenshots of every page type at phone and desktop widths in both
   themes and with both AI stances; fix layout, contrast and empty states ("not found" must
   look different from "no").
7. Methodology page: sources, the date of the data, the AI rubric and its limits (attribution
   is a lower bound), the activity thresholds, the bot filter, how to send corrections (issues
   on this repo), and this project's own AI use: researched and built with Claude in Claude
   Code, the models named in the commits' `Co-Authored-By` lines (list them from `git log`).
8. Commit, push, and tell the user to merge to `main` (or push to `main` if the user said so):
   the deploy workflow publishes https://n3tman.github.io/vibe-check/. Then open the live site
   and check that every page loads with the right base path.
