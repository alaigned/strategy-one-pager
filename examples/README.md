# Strategy One-Pager — example documents

Everything in this folder is here so you can exercise the skill end to end without
supplying a strategy document of your own.

## The sample documents

Three fictional companies, one source document each. They are deliberately different
shapes, because the skill behaves differently depending on how much it is given.

| File | What it is | What it exercises |
|---|---|---|
| `meridian-strategy-brief.md` | A complete 2026–2028 strategy brief for a Central-European logistics operator | The rich-input path: the skill should ask **no** questions and deliver in one pass |
| `perpetua-founders-note.md` | A founder's note — narrative, no numbers, no org chart | The thin-input path: the skill has to name the gaps rather than invent answers |
| `verdana-where-next-memo.md` | A "where do we go next" memo with competing options | The ambiguity path: unresolved choices become open questions, not decisions |

All three are synthetic. The companies do not exist, and no customer data of any kind is
involved — each file says so in its own header.

## Running the skill

Attach one document (start with `meridian-strategy-brief.md`) and ask:

> Turn this strategy document into an Alaigned one-pager cascade.

A complete run delivers a printable PDF, a schema-validated JSON cascade bundle, and a
list of open questions. The skill validates its own output before handing it over — it
runs a bundled Python validator in the session's own sandbox, with no network access and
no call to any Alaigned server. Nothing you attach is uploaded to Alaigned; the only
outward step the skill ever takes is a public-data search it asks you to approve first.

To see the skill decline rather than guess, try it with no document at all:

> Use the skill for Tallow & Pike, a two-person carpentry workshop; their website
> is https://tallow-and-pike.example — I have no documents.

It should stop, say what it searched, and ask for documents. It should not produce a
cascade.

## No account needed

Every rendered page carries a link to `https://try.alaigned.com`. That page is public — no
account is needed to follow it, and none is needed for anything else here either. The skill
runs entirely inside this session: it reads what you attach, drafts the cascade, renders it
and runs its validator locally, and never calls an Alaigned server.
