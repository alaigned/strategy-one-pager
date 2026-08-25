# strategy-to-one-pager

A plugin bundling the **strategy-to-one-pager** Agent Skill. It converts a company's existing
strategy documents — decks, memos, annual plans, OKR sheets — into a one-pager cascade: a
company-level (L0) page plus one page per team (L1), where each team page carries explicit links
back to the company page. The links are checked against a JSON schema rather than asserted, and
the skill renders the result as HTML, PDF or Word.

## Layout

| Path | What it is |
|---|---|
| `.claude-plugin/plugin.json` | The plugin manifest |
| `skills/strategy-to-one-pager/` | The skill — instructions, references, templates, and the validator and renderer scripts |

`skills/strategy-to-one-pager/README.md` is the skill's own documentation: what it produces, what
it needs installed, worked examples and troubleshooting.

## This tree is generated

It is built and published from Alaigned's development repository, so editing files here has no
effect beyond the next release, which overwrites them. Each release is a single commit tagged
`v<version>`, matching the `version` in the skill's frontmatter; the commit message also records
the fingerprint of the methodology schema that release validates against.

Issues and questions are welcome on this repository.
