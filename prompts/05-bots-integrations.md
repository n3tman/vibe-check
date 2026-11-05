# Lane 5: bots and integrations

Follow `prompts/_research.md`. Your notes file is `notes/05.md`.

Scope: everything on https://matrix.org/ecosystem/integrations/ (bots, widgets, moderation
and admin tools, push gateways, identity servers, …) and what you find beyond it, including
https://github.com/etkecc/komai. Bots go in `data/projects/bot/`; the rest (moderation tools,
admin UIs, deployment playbooks, push gateways) in `data/projects/tool/` with a `kind`.
Bridges are lane 6's: if the integrations list carries bridges, leave them to lane 6.

Bot specifics:
- Fill `purpose`, `framework`, `e2ee`, `hosting`, `config`, `ai_backend`.
- Many bots are LLM front-ends (ChatGPT bots, …): name the backends they call and set
  `ai.in_product` accordingly.
- Small one-person bots are many; cover the listed ones fully, then the most-starred others,
  and list the rest in notes with their repo URL only.
