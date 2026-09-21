# Changelog

Notable changes to the published skill. Every version has three lines: what changed for you,
the fingerprint of the methodology schema it validates against, and the model it was tested on.
The GitHub Release for each tag carries the same three lines.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versions follow
the `version` in `skills/strategy-one-pager/SKILL.md`; the tag is `v<version>`.

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
