# Shared procedure for the research lanes (2 to 6, 8)

Read `CLAUDE.md`, `PLAN.md` and `docs/schema.md` first. Your lane prompt names your scope.

## 1. Catalogue (first 20 minutes)
- Build the full list for your scope from the sources in `PLAN.md` "Sources": the matrix.org
  list (and its source files in the website repo), the extra URLs, topic searches, awesome
  lists. Write it to `notes/<lane>.md` as a table: name, slug, homepage, repo URL, forge,
  where found, status guess.
- Drop nothing silently: a project without a reachable repo or homepage gets a row with
  "no repo found" and is skipped with that reason; a closed-source one gets a file anyway
  (features and AI policy can still be checked) with `repos: []`.
- Order the work: most-used and actively developed first, so the site is useful even if the
  time runs out. Push the catalogue as your first checkpoint.

## 2. One file per project
For each project, in that order:
1. Blobless clone into `cache/repos/<slug>/` (`git clone --filter=blob:none --no-checkout`).
   Read what you need with `git show HEAD:<path>`, `git ls-tree -r --name-only HEAD`,
   `git grep` on a sparse checkout, `git log`. Never run anything from the clone.
2. Fill `data/projects/<category>/<slug>.yaml` per `docs/schema.md`. Features: README and
   docs for `claimed`, the code for `code` (grep for the MSC numbers, unstable prefixes like
   `org.matrix.msc4186`, SDK calls). Pin source URLs to the commit you read (`/blob/<sha>/`).
3. AI, all three axes (`CLAUDE.md` "AI rubric"):
   - policy: read CONTRIBUTING, the PR template, CODE_OF_CONDUCT, README, the docs site; search
     the forge's issues and discussions for "AI", "LLM", "Copilot", "ChatGPT", "Claude",
     "generated" and quote the maintainers' own words with a link;
   - dev usage: list agent files (`git ls-tree`), and count commits of the last 365 days whose
     message or trailers name an AI tool (`git log --since=1.year --format='%H%x00%an%x00%B%x1e'`
     and match `Co-authored-by:` trailers and "Generated with" lines). The collector
     (lane 1) will recount this; your numbers are a check and your judgment of the evidence
     is what goes in the file;
   - in product: features that call an LLM or other generative AI, from docs and code
     (OpenAI, Anthropic, Ollama, Gemini, LiteLLM SDKs and endpoints in manifests and source).
4. Set `checked:` to today. Commit per project or per few projects; push every 30 to 45
   minutes.

## 3. Quality bar
- Every `yes`, `no` and `partial` has a `source`. Unsure → `not-found` plus a note.
- Neutral wording. "Uses AI" is a fact with a link, not a judgment.
- Don't guess from the name or from memory: projects change; read the current repo.

## 4. Finish (by 2:15 after the start, or when your scope is done)
- `notes/<lane>.md`: covered, skipped (why), "For lane N" items, open questions, anything the
  site should show that the schema lacks.
- Final commit and push. Tell the user the branch name and that it is ready to merge.
