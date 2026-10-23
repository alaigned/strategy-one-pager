# Changelog

Notable changes to the published skill. Every version has three lines: what changed for you,
the fingerprint of the methodology schema it validates against, and the model it was tested on.
The GitHub Release for each tag carries the same three lines.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versions follow
the `version` in `skills/strategy-one-pager/SKILL.md`; the tag is `v<version>`.

## [0.17.0] - 2026-10-22

- Changed: the recommended ceiling for values is five, down from eight, and it is never an error.
  The skill keeps every value your sources state; above five, the Gap Report asks which five you
  run by. A pillar with four or five initiatives still validates, but gets a Gap Report note
  naming the count, and the skill moves an extra initiative to a better pillar or reports it as a
  gap instead of merging two into one sentence.
- Methodology: `sha256:7e291576`
- Tested on: the skill's own validator against the golden bundles (no model run)

## [0.16.0] - 2026-10-22

- Changed: the guidance follows the latest Alaigned methodology. Purpose, Vision and Mission
  are all optional — the skill fills the ones your sources support. The Strategic Ambition may
  combine a few linked figures, say revenue and profitability. Each pillar aims for at most three
  initiatives, and the target sits in the initiative's goal — a number or a clearly checkable
  state. A team is named critical only when a distinct part of the initiative lands on its page,
  not because it is needed. Enablers are named for the change they bring ("Upgraded CRM
  platform"), and routine operations stay off the page. The either/or "DNA" note on the company
  page is gone.
- Methodology: `sha256:794b7d8f`
- Tested on: the skill's own validator against the golden bundles (no model run)

## [0.15.2] - 2026-10-14

- Changed: the bundle envelope schema (`cascade-bundle.schema.json` in the skill) now describes
  every property — what each field holds, in the same words the Alaigned connector uses when it
  returns a cascade — so a tool reading the schema needs no prose beside it.
- Methodology: `sha256:794b7d8f`
- Tested on: the skill's own validator against the golden bundles (no model run)

## [0.15.1] - 2026-09-30

- Fixed: on a Mac, running the skill in Codex no longer brings up "Google Chrome quit
  unexpectedly" twice for every PDF. The sandbox there keeps Chrome from starting, so the renderer
  checks first and goes straight to the next PDF engine.
- Methodology: `sha256:794b7d8f`
- Tested on: the renderer under the Codex sandbox on macOS (no model run)

## [0.15.0] - 2026-09-14

- Changed: the skill is now called Strategy One-Pager. Its name in the skill list, the slash
  command and the repository address follow: `/strategy-one-pager`,
  github.com/alaigned/strategy-one-pager. The old repository address redirects.
- Changed: the rendered document is titled "<Company> — Strategy One-Pager" (HTML title, PDF and
  Word metadata) instead of "<Company> — Strategy One-Pager Cascade".
- Fixed: pages no longer break halfway down — the renderer's print-height estimates were
  re-measured (0.14.1). Source pillars that are really enablers are now sorted as enablers.
- Methodology: `sha256:794b7d8f`
- Tested on: Claude Opus 5 in Claude Code

## [0.14.0] - 2026-09-14

- Changed: one word for the whole idea. The skill, its templates and its validator say "cascade"
  throughout; "propagate" is gone from the rendered pages, the alignment map and the validator's
  messages.
- Methodology: `sha256:794b7d8f`
- Tested on: Claude Opus 5 in Claude Code

## [0.13.2] - 2026-09-08

- Changed: Czech and Slovak artifacts print the element labels (Purpose, Strategic pillars, Goal,
  Enablers, Values) in the artifact's language, and the Czech and Slovak vocabulary was reviewed
  with the methodology's owners: Goal replaces Picture of Success, an enabler is a "podmínka", the
  pillar line reads "Definition of success". Long value and enabler lists no longer cut a page in
  the middle, and continued pages fill properly.
- Methodology: `sha256:794b7d8f`
- Tested on: Claude Opus 5 in Claude Code

## [0.12.4] - 2026-09-03

- Changed: the license is the PolyForm Shield License 1.0.0 (previously Apache-2.0). The repository
  doubles as a marketplace, so Claude Code installs the plugin with
  `/plugin marketplace add alaigned/strategy-one-pager`. Three synthetic sample documents ship
  in `examples/`, and the support contact is support@alaigned.com.
- Methodology: `sha256:794b7d8f`
- Tested on: Claude Opus 5 in Claude Code

## [0.12.3] - 2026-08-26

- Changed: the skill's text is written for a public audience; every reference to Alaigned's
  internal tooling is gone from the published files.
- Methodology: `sha256:794b7d8f`
- Tested on: Claude Opus 5 in Claude Code
