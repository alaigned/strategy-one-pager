# strategy-to-one-pager

An [Agent Skill](https://code.claude.com/docs/en/skills) that reads the decks, memos and plans
you already have and writes a company one-pager plus a linked one-pager for every team — each one
provably derived from the company's, and checked against the Alaigned methodology.

What makes it different from "strategy prompts": the output is a JSON bundle **validated against
the same methodology schema the Alaigned product enforces** — structurally correct, alignment
verifiable, and import-ready.

## Example prompts

Three runs that exercise different paths through the skill. Type the prompt as written; where it
says to attach files, attach or @-mention them.

**1 — Strategy documents in, cascade out** (the primary path)

> Turn these into an Alaigned one-pager cascade.
> *(attach the strategy deck, the annual plan and the OKR sheet)*

The skill confirms which files it will work from, asks at most two questions — none at all from
sources that already name the teams and the horizon — and drafts the company (L0) one-pager plus
one page per team that owns delivery. It validates the bundle with `scripts/validate_cascade.py`,
then renders it with `scripts/render_cascade.py --pdf`. You get the PDF first — one A4 landscape
page per one-pager plus a **Strategy Gap Report** page collecting everything the sources could not
answer — then the validated bundle JSON, then a one-line offer of an editable copy.

**2 — A company website as the only source**

> We have no strategy documents yet. Work from our website:
> https://www.meridian-logistics.example — mid-size parcel and freight carrier in Central Europe.

The URL is the consent: that site, plus public data about that company. The skill announces the
pass, then reads at most ten named sources — the site's core pages, the latest annual report or
investor materials, leadership posts, a Crunchbase-class profile — and never crawls beyond them.
Every drafted statement stays traceable to one of them; the fetched URLs land in the bundle's
`company.sourceDocuments` as `https://… (accessed YYYY-MM-DD)` and appear under **Sources**
on the Gap Report page. Anything composed rather than quoted carries a `[PROPOSED]` marker in
the bundle and is listed on that page instead of being dressed up as fact.

When the public footprint is too thin to carry a strategy — a two-person workshop with one page
online — the run stops before drafting: it names what it searched, says the footprint cannot
carry a cascade, and asks for documents. No bundle, no PDF, no invented strategy. That stop is the
designed answer, not a failure.

**3 — The same cascade as a Word document or a Google Doc**

> Can I also get that in Word?

Asked once a cascade has been delivered, this re-renders from the same validated bundle
(`scripts/render_cascade.py <bundle>.json -o <company>-strategy.html --pdf --docx`), so the `.docx`
carries the artifact's design — landscape A4, brand stripe, Gap Report page — and nothing is
re-drafted. `Make that a Google Doc.` takes that same `.docx` and uploads it with conversion
through a connected Google Drive or Docs tool, then hands back the link; with no such tool in the
environment you get the `.docx` and one sentence saying that uploading it to Drive opens it as a
Google Doc. Asked up front instead — "we're an Office shop, send Word too" — the `.docx` ships
alongside the PDF in the first delivery turn.

## Contents

| Path | Purpose |
|---|---|
| `SKILL.md` | The skill definition (workflow + hard rules) |
| `references/` | Output contract (JSON shape, link model), methodology guide, CZ/SK terminology glossary |
| `templates/` | Markdown rendering templates for the human layer |
| `scripts/render_cascade.py` | Artifact renderer — HTML, PDF (`--pdf`) and Word (`--docx`) from a validated bundle |
| `scripts/validate_cascade.py` | Deterministic validator — run on every bundle before delivery |
| `cascade-bundle.schema.json` | Envelope schema for the bundle |
| `schemas/` | **Generated at package time** — inlined methodology + fingerprint |
| `prompt-variant/` | Plain-prompt version for ChatGPT/Gemini users — in the skill zip only, not in the plugin bundle |

## Requirements

- The `schemas/` directory must be present. It is generated when the skill is packaged and
  ships inside the bundle — if it is missing, the copy you have is incomplete; download the
  bundle again.
- Any `python3` (3.10+), with code execution and file creation available to the assistant. Both
  scripts are stdlib-only: nothing needs installing, no network is used, and the validator runs
  the same check set with or without the `jsonschema` package (it declares that package via PEP
  723 inline metadata, so `uv run scripts/validate_cascade.py …` self-provisions the preferred
  engine).
- Nothing extra for the PDF: the renderer probes for headless Chromium, then WeasyPrint, then
  falls back to its own stdlib writer, so a real PDF comes out of every environment.

## Troubleshooting

**You got markdown pages, but no PDF and no bundle file.** This environment cannot run the
skill's scripts. On claude.ai, switch code execution and file creation on under Settings →
Capabilities; on Team and Enterprise plans an owner has to enable Skills for the organization
first. Without them the cascade still arrives, as markdown pages — the same strategy, just not
the printable artifact.

Anything else: email **support@alaigned.com**.

## Versioning

`version` lives in the `SKILL.md` frontmatter. The methodology artifact carries its own
fingerprint (`schemas/fingerprint.json`), embedded in every generated bundle so downstream
imports can check compatibility.
