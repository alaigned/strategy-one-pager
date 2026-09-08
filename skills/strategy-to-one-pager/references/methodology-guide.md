# Methodology Guide — Element Definitions and Quality Bar

> Derived from **Alaigned Strategy Methodology 2026.1**. This guide condenses what the skill needs for
> the Definition phase; the methodology also covers horizontal alignment, evaluation, adoption and
> facilitation, which are out of scope for skill output. Where the shipped schema (v1) and the
> methodology text diverge, the schema wins for output validity and the divergence is noted.

## The one-pager idea

Most strategies fail because they never leave the room they were made in. The **Strategy
One-Pager (SOP)** is a single page holding the whole of a team's strategy — from purpose down to
the measurable result of each initiative. A strategy is aligned when it cascades **down** (every
team knows how its work serves the level above), aligns **across** (dependent teams plan against
the same commitments), and travels back **up** through evaluation. This skill executes the
**Definition** phase and the vertical-cascade part of **Alignment** for L0 + L1.

One discipline governs the page: it tracks **changing the business, not running the business**.
Quality levels and service commitments that keep the operation going are not strategy — this
single test removes most of what does not belong.

## Elements and how they map to the schema

> The numeric rule values below (ceilings, critical-team cap) are encoded machine-readably in
> the methodology itself (`hierarchy[].limits` in `schemas/methodology.inlined.json`) — the
> validator reads them from there, so this table is documentation, not the source of truth.

| Methodology name | Schema field | Required | Rules |
|---|---|---|---|
| Purpose / Vision / Mission | `purpose`, `vision`, `mission` | ≥ 1 filled at L0 | The "why" — impact beyond profit. Short, often one line. Communication fields. Fill the one(s) the sources support; leave the rest `textValue: null` (no open question needed — using one, two or all three is a legitimate choice) |
| Strategic Ambition | `companyAmbition` | L0, always | One fundamental goal in concrete business parameters, medium/long term. One parameter, at most two. The strongest form is a single sharp line carrying a number or position: "By 2028: five countries, fifty cities, 500 million in net revenue." Copied read-only to lower levels |
| Team Strategic Ambition | `teamAmbition` | L1+ | Not a copy — the team's role within the company ambition. Narrow it to the team's domain ("become the core competence centre for X"), don't restate it |
| Strategic Pillars | `pillars` | all levels | Authored pillars: **short noun phrase, 2–4 words** ("Grid", "Core assortment everywhere") — never a sentence with a verb. Optimum 3–4, ceiling 5. Cascaded pillars carry the parent initiative's sentence verbatim — that's correct, they are continuations |
| Definition of Success (DEOS) | `successDefinition1`, `successDefinition2` | 1–2 per pillar | How you know the pillar is won — high-level, as measurable as possible. Enterprise default pairing: medium-term ambition (`successDefinition1`) + this-year goal (`successDefinition2`) |
| Key Initiatives | `initiatives` per pillar | all levels | The activities that deliver the pillar. Belongs to exactly one pillar. Optimum 2–3 per L0 pillar (1–3 under a cascaded pillar), ceiling 5; ~10–12 initiatives per page total |
| Goal | initiative `goal` | 1 per initiative | The specific, measurable result of the initiative — the engine of the cascade (becomes the child pillar's DEOS). The methodology's earlier name *Picture of Success* (PICOS) is retired |
| Enablers | `enablers` | L0 only | Foundations performance rests on — "how we organise ourselves", not "what we want to achieve". Optimum 3–4, ceiling 5. Name = **short noun phrase for the condition** ("Modern ERP backbone"), never a verb exhortation — the name cascades verbatim into child pillar names |
| Culture / Values / Behaviours | `values` | optional, L0 | Attitudes and behaviours, **first person**, short ("We are in it together"). Ceiling 8. Never invent them |
| DNA (decision cross-roads) | — *(no schema field in v1)* | optional | A few defining either/or choices. Rarely used. If the sources contain genuine DNA, put it in the L0 `narrative` element and add an open question |
| Critical Teams | — *(expressed via cascade `links`)* | optional | Which teams deliver an initiative — this drives the cascade (below) |

## Writing rules (these carry most of the weight)

1. **An initiative is a sentence with a verb, not an attitude.** "Launch the new platform in Q3",
   "Cut onboarding from fourteen days to five". Noun phrases ("Brand development", "Process
   automation") quietly avoid concreteness — rewrite them. Attitudes ("growth mindset",
   "customer centricity") belong in Values, never in Initiatives.
2. **An initiative must stand on its own for a distant reader.** An accountant should understand
   a trading initiative. Spell out domain acronyms on first use. If a colleague from the
   furthest-away function would have to ask, rewrite.
3. **A goal measures output, not input, and carries a number.** Not "improve visibility"
   but "+20% organic traffic". Reserve input goals ("the system is live") for cases where nothing
   else is honestly possible (regulatory milestone, governance approval). The test: could you
   say mid-year "we are green, yellow or red" against it? If not, it's written wrong.
4. **Keep it to the ten or twelve things that matter.** A one-pager is a strategic document, not
   a task list. When the sources offer fourteen initiatives, perhaps five are the core — propose
   the cut and put the rest in open questions.
5. **Design pillars around content, not the org chart.** Both are legitimate — areas of
   responsibility (Grid / Customer / Growth) or cross-functional topics (New fulfilment model /
   International expansion) — but choose on content. If the resulting one-pager doesn't fit the
   existing structure, that is a finding, not a flaw; note it as an open question.
6. **Nothing is analysed or drafted from unconfirmed sources.** Ask for sources and wait — a gap
   is never filled from your own knowledge. (Unlike rules 1–5, this one governs how the skill
   behaves rather than how a one-pager is written, so it has no counterpart in the upstream
   methodology — keep it when re-deriving this guide.)

## Initiatives versus Enablers (mandatory distinction)

| Initiatives | Enablers |
|---|---|
| Top line (revenue) | Bottom line (cost) |
| Business drivers | Business conditions |
| Building the business | Running the business |
| Right to win (unique) | Right to play (hygiene) |
| External: customers, product, delivery | Internal: people, processes |
| Output / impact | Input |

Enabler categories: tools (ERP, CRM), processes (efficiency, agile adoption), people (capability,
talent), mindset/culture, legal framework, governance. **A shared resource is not an enabler**:
"CAPEX budget" or "CRM technology" as an enabler is an anti-pattern — an enabler is an
organisational or human condition, not a cost line.

An enabler may be *promoted* to an initiative in exactly three cases: it's a genuine game-changer
for the business, a source of unique differentiation, or core DNA. Otherwise keep the line clean:
a new ERP is an enabler; market expansion is an initiative.

## The vertical cascade

The mechanism is precise:

- A Key Initiative names its **Critical Teams** (max 3, direct reports of the one-pager's owner
  only). For each critical team, the initiative becomes a **Strategic Pillar on that team's
  one-pager**, carrying its Goal as the new pillar's Definition of Success. The
  receiving team then writes its own Key Initiatives under that pillar.
- **The dead-end rule:** if the owning team itself does the work, the initiative does not cascade
  — it terminates at that level. Not every initiative produces a child pillar.
- Enablers sit on L0 and may also carry critical teams — cascade each enabler to the teams that
  must build or adopt it (often all of them, but that is a content decision, not a rule).
- The Strategic Ambition is copied read-only into every child; the child adds its own Team
  Strategic Ambition above its pillars.
- Propagated values are **verbatim copies** — alignment is only checkable when the words match.
- **Sparse sources and the team page:** the initiatives the receiving team writes are real
  content in its own domain language, distinct from every sibling team's. Thin sources → propose
  them (`[PROPOSED]`) with an open question naming what that team must confirm; nothing known
  about the team → leave the goals `null` and raise a targeted open question.

> Schema note: the shipped v1 propagation rules also carry Purpose/Vision/Mission down to
> children (read-only company context), although the methodology text marks them "not cascaded".
> Follow the schema: include the links for whichever of the three are filled at L0.

## Maturity honesty

Sources rarely contain a complete strategy; the output must make maturity visible:

- Solid, sourced statements → normal text.
- Reasonable proposals from strong hints → prefix `textValue` with `[PROPOSED] `.
- Composed numbers and dates (a figure or year derived, not quoted) → `[PROPOSED]` as well.
- True gaps → `textValue: null` plus an open question.
- The marker belongs on composed **content `textValue`s** only. A one-pager's `title` and
  `company.name` are printed straight into the page heading, where a marker would render
  verbatim *and* escape the draft banner and the Gap Report's proposed-content section — the
  validators reject it there. Raise the naming or team-split question in `openQuestions`
  instead (prose that *mentions* the marker is fine).

An **attributed fact** is a statement traceable to a named source — a source document, or a
fetched public source (annual report, investor materials, press, a published strategy
statement, a leadership post). Interpretation of a website or inference from search-result
titles is not attribution. The ladder does not care where a source lives, only that it is
named: a public source grounds a statement exactly like a document does. Published values,
missions, and named priorities are quoted verbatim with attribution even when they break the
writing rules — the rules govern what the skill composes; the deviation becomes an open
question, never a rewrite. Fact counting governs pillars authored at L0 — cascaded pillar
names and success definitions remain verbatim copies regardless of the count.

The markers are **bundle data, not page decoration**: rendered pages carry one document-level
draft banner and the Gap Report lists what is proposed — per-item badges are not rendered.

**A published one-pager carries no placeholders** — "Type something", "[x]", or a facilitation
question written into an initiative field are anti-patterns from real engagements. An honest
half-empty one-pager that a leadership team can finish in a workshop beats a fluent fake.

## Anti-patterns seen in real one-pagers (avoid and flag)

1. Unmeasurable goal — "A satisfied customer who shops regularly" fails the green/yellow/red test.
2. Initiative as a noun phrase — "Brand development", "Vertical integration".
3. Initiative unreadable outside the team — "Off APS and EqB infra".
4. A shared resource dressed as an enabler — "Marketing budget".
5. Placeholder content — "[x]", "Type something".
6. A question or internal note in an initiative field.
7. Fifteen-plus initiatives on one page — a bucket list, not a priority set.
8. A facilitation instruction standing in for content — "Break this pillar into the team's key
   initiatives" written as an initiative, "define measurable goals" written as a goal.
9. The same initiative or goal repeated across sibling team pages — interchangeable pages mean
   no team actually planned.
