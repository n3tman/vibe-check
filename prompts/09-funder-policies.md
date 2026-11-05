# Lane 9 (follow-up): funders' AI policies

Follow `prompts/_research.md` for evidence and tone. Your notes file is `notes/09.md`. Run it
after lanes 1 to 6 are merged (it edits files across categories), or fold it into lane 7.

## Why
Some projects are paid for by grants whose funder sets rules on generative AI for the funded
work. The first known case: NLnet's "Policy on the use of Generative Artificial Intelligence
for NLnet-funded projects", version 2.0, in force since 2026-10-20
(https://nlnet.nl/foundation/policies/generativeAI/2.0/, FAQ at
https://nlnet.nl/foundation/policies/generativeAI/faq/). It bans using GenAI to produce
artefacts (code, design, documentation) in funded work, allows read-only use (review, finding
flaws) with disclosure, and asks grantees to state their GenAI stance in the README and
website. Versions 1.0 (2025-12-08) and 1.1 (2026-01-26) allowed disclosed use. The FAQ names a
transitional arrangement for NGI / NGI Zero programmes in flight (NGI Zero Commons Fund, NGI
Taler and Fediversity may keep v1.1).

A funder policy is not the project's own policy: it binds the grantee's funded work, not
outside contributors or the whole history. Never copy it into `ai.policy`; record it beside it.

## Shape (already used in `data/projects/tool/draupnir.yaml`)
```yaml
ai:
  funder_policy:
    - funder: NLnet Foundation (NGI Zero Core fund)
      grant: https://nlnet.nl/project/<Name>/
      grant_start: 2024-04
      grant_source: <README line or funding page that states the grant>
      policy: https://nlnet.nl/foundation/policies/generativeAI/2.0/
      policy_version: 2.0, in force since 2026-10-20
      value: banned            # same scale as ai.policy
      quote: <the sentence>
      scope: work delivered within the grant
      transition: <what the FAQ says about this fund, or "not stated">
      transparency: <does the README state a GenAI stance, as the policy asks? found / not found>
      checked: <date>
```
Add the shape to `docs/schema.md` and show it on the project page and in the AI section of
the methodology page, next to (not merged with) the three axes. A project whose funder bans
generation and whose commits carry AI attributions is a fact to show side by side, with dates
(grant period vs commit dates), never a verdict.

## Steps
1. NLnet: the project index https://nlnet.nl/project/index.html (a table: name, fund, year,
   description). Matrix-related rows found on 2026-11-05 by description: Bromal (server,
   NGI0 Commons Fund 2026, https://bromal.im), Draupnir (done), Element Call on Cisco Room
   hardware (RoomKit-Element, https://github.com/TheArcaneBrony/cisco-element-call), Elm Matrix
   SDK (NGI0 Entrust 2023, https://github.com/noordstar/elm-matrix-sdk), Fractal (NGI0 PET
   2020), Improving Matrix E2E encryption UX (Internet Hardening Fund 2017, matrix.org),
   Kazarma and Kazarma Release (ActivityPub bridge, 2020 and 2023), Matridge spaces (Slidge's
   XMPP gateway, NGI0 Commons Fund 2026), NeoChat (NGI Assure 2021). The description search
   misses projects whose blurb does not say "Matrix": also grep every cloned repo's README,
   FUNDING.yml and docs for `nlnet|NGI ?Zero|NGI0|ngi\.eu`, and open each project's NLnet page
   for the fund and start date.
2. Decide per grant which policy version applies, from the grant dates and the FAQ. A grant
   that ended before 2025-12-08 predates every version: record it with `value: none-found`
   and say why in `transition`, or leave it out and mention it in notes.
3. Other funders: look for AI rules from the Sovereign Tech Agency / Fund, Prototype Fund,
   the EU NGI programmes outside NLnet, Open Technology Fund, GitHub Secure Open Source Fund,
   Google Summer of Code, Outreachy and company sponsors. Record a funder only when its rule
   text is found (URL and date); "no rule found" goes in notes.
4. Projects funded by such a funder and also showing AI attributions in the grant period: list
   them in notes with the commit or PR links, neutrally.
