# strategy-to-one-pager

An [Agent Skill](https://code.claude.com/docs/en/skills) that converts a company's existing
strategy documents into an **Alaigned-methodology one-pager cascade**: a company-level (L0)
one-pager plus team-level (L1) one-pagers with explicit, machine-checkable alignment links.

What makes it different from "strategy prompts": the output is a JSON bundle **validated against
the same methodology schema the Alaigned product enforces** — structurally correct, alignment
verifiable, and import-ready.

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
| `prompt-variant/` | Plain-prompt version for ChatGPT/Gemini users |

## Requirements

- The `schemas/` directory must be present (produced by the packaging step; in the monorepo:
  `mix alaigned.plg.export_methodology` or the `plg/scripts/package_skill_*.sh` packagers).
- For the validator, either `uv` (the script declares its `jsonschema` dependency via PEP 723
  inline metadata, so `uv run scripts/validate_cascade.py …` self-provisions) or plain `python3`
  with `jsonschema` importable. In the monorepo, `plg/.mise.toml` pins uv and
  the packagers resolve it automatically via `mise x`.

## Versioning

`version` lives in the `SKILL.md` frontmatter. The methodology artifact carries its own
fingerprint (`schemas/fingerprint.json`), embedded in every generated bundle so downstream
imports can check compatibility.
