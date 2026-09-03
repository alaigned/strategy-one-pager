# strategy-to-one-pager

A plugin bundling the **strategy-to-one-pager** Agent Skill. It reads the decks, memos and plans
you already have and writes a company one-pager plus a linked one-pager for every team — each one
provably derived from the company's, and checked against the Alaigned methodology. The result
renders as HTML, PDF or Word.

## Install

This repository is also a marketplace, so Claude Code can install the plugin from it directly:

```
/plugin marketplace add alaigned/strategy-to-one-pager
/plugin install alaigned-strategy@alaigned
```

## Layout

| Path | What it is |
|---|---|
| `.claude-plugin/plugin.json` | The plugin manifest |
| `.claude-plugin/marketplace.json` | The marketplace manifest, listing this one plugin |
| `skills/strategy-to-one-pager/` | The skill — instructions, references, templates, and the validator and renderer scripts |
| `examples/` | Three synthetic strategy documents to try the skill on, and a note on what each one exercises |
| `LICENSE` | The PolyForm Shield License 1.0.0, plus the notices it requires you to pass on |

`skills/strategy-to-one-pager/README.md` is the skill's own documentation: what it produces, what
it needs installed, worked examples and troubleshooting.

## Try it without a strategy document of your own

`examples/` holds three source documents for three fictional companies, deliberately different
shapes — a complete strategy brief, a founder's note with no numbers, and a memo full of unresolved
options. Attach one and ask for a cascade; `examples/README.md` says what each should produce.

## Support

Questions and bug reports: email **support@alaigned.com**.

## This tree is generated

It is built and published from Alaigned's development repository, so editing files here has no
effect beyond the next release, which overwrites them. Each release is a single commit tagged
`v<version>`, matching the `version` in the skill's frontmatter; the commit message also records
the fingerprint of the methodology schema that release validates against.

Issues and questions are welcome on this repository.

## License

Everything in this repository — the skill instructions, the methodology references and the inlined
methodology schema, the templates, and the Python validator and renderer — is licensed under the
**[PolyForm Shield License 1.0.0](LICENSE)**, and nothing here is under any other terms. It is a
source-available licence, not an open-source one: it grants broad rights for every purpose except
competing with us.

You may:

- **use it, including commercially** — inside a company, for clients, for paid work, at any scale;
- **change it** and build new works on it;
- **pass copies on**, changed or not — to a colleague, a friend, another company — provided
  whoever gets a copy also gets these terms (or the URL at the top of [LICENSE](LICENSE)) and the
  `Required Notice:` lines that come with them.

You may not:

- **use it to provide a product that competes** with this software, or with any product Alaigned
  provides using it. The licence reads "competes" broadly: a different interface, a different
  platform, or giving it away free does not stop something from competing;
- **sublicense it or transfer your licence** to someone else. Everyone gets their own licence
  from Alaigned, on these same terms;
- **use the Alaigned name or wordmark.** No trademark rights are granted here. The renderer
  embeds the Alaigned wordmark in the HTML, PDF and Word artifacts it produces — a changed copy
  you distribute must remove or replace it.

Read [LICENSE](LICENSE) for the terms that actually bind; the summary above is not a substitute
for them.

The development repository this tree is generated from is not public and is separately licensed;
that licence does not apply to anything in this repository.
