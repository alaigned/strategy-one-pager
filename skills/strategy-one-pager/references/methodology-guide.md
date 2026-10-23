# Methodology Guide — Element Definitions and Quality Bar

> Derived from **Alaigned Strategy Methodology 2026.2**. This guide condenses what the skill needs
> for the Definition phase; the methodology also covers horizontal alignment, evaluation, adoption
> and facilitation, which are out of scope for skill output. Where the shipped schema (v1) and the
> methodology text diverge, the schema wins for output validity and the divergence is noted.

## The one-pager idea

Most strategies fail because they never leave the room they were made in. The **Strategy
One-Pager (SOP)** is a single page holding the whole of a team's strategy — from purpose down to
the measurable result of each initiative. A strategy is aligned when it cascades **down** (every
team knows how its work serves the level above), aligns **across** (dependent teams plan against
the same commitments), and travels back **up** through evaluation. The methodology rests on three
**foundations** that produce these three directions — Definition, Alignment and Evaluation. This
skill executes the **Definition** foundation and the vertical-cascade part of **Alignment** for
L0 + L1.

One discipline governs the page: its pillars and initiatives track **changing the business,
not running the business**. The test is a single question about any candidate initiative: *if
this succeeds, what about the business will be different?* If the honest answer is "nothing, it
keeps the operation running at its current level", it is not an initiative. A foundation the
strategy needs *built or improved* goes into Enablers, named for that change; the routine of
running the operation — service levels, routine quality targets, steady-state obligations —
stays off the page. Applied consistently, this one question removes most of what does not
belong among the initiatives.

## Elements and how they map to the schema

> The numeric rule values below (ceilings, critical-team cap) are encoded machine-readably in
> the methodology itself (`hierarchy[].limits` in `schemas/methodology.inlined.json`) — the
> validator reads them from there, so this table is documentation, not the source of truth.

| Methodology name | Schema field | Required | Rules |
|---|---|---|---|
| Purpose / Vision / Mission | `purpose`, `vision`, `mission` | none mandatory (L0) | The "why" — impact beyond profit. Short, often one line. Communication fields; where defined, copied read-only into lower-level one-pagers. None of the three is mandatory: fill the ones the sources support; the element objects still exist, with `textValue: null` for the rest (no open question needed — using none, one, two or all three is a legitimate choice) |
| Strategic Ambition | `companyAmbition` | L0, always | One fundamental goal in concrete business parameters, medium/long term. One parameter is the strongest form; a small set of interlinked parameters (typically to hold both revenue and profitability) is workable, up to three or four. Either way, write it as a single sharp line carrying a number or position: "By 2028: five countries, fifty cities, 500 million in net revenue." Copied read-only to lower levels |
| Team Strategic Ambition | `teamAmbition` | L1+ | Not a copy — the team's role within the company ambition. Narrow it to the team's domain ("become the core competence centre for X"), don't restate it; same horizon as the Strategic Ambition it narrows, typically three to five years. The methodology lets a company run without it; schema v1 requires it at L1, so the skill always writes one |
| Strategic Pillars | `pillars` | all levels | Authored pillars: **short noun phrase, 2–4 words** ("Grid", "Core assortment everywhere") — never a sentence with a verb. The methodology calls the noun phrase (and the initiative's verb sentence) recommended syntax rather than an obligation; the skill applies both to everything it composes. Optimum 3–4, ceiling 5. Cascaded pillars carry the parent initiative's sentence verbatim — that's correct, they are continuations. A source pillar named for an organisational condition (People / Our People, Foundations, Finance, IT / Systems, Culture, Governance) is an **enabler** unless its content states a customer- or market-facing outcome — move it and record the move as an open question ("the sources list X as a pillar; this cascade keeps it as an enabler — does the leadership team accept that cut?") |
| Definition of Success (DEOS) | `successDefinition1`, `successDefinition2` | 1–2 per pillar | How you know the pillar is won — high-level, as measurable as possible. Enterprise default pairing: medium-term ambition (`successDefinition1`) + this-year goal (`successDefinition2`). The limit of two is a limit on fields, not on ambition — a small set of related measures goes inside the text of one Definition of Success, not into further fields. Horizons follow the level's strategy cycle (for an annual strategy, "medium term" may be the half-year) |
| Key Initiatives | `initiatives` per pillar | all levels | The activities that deliver the pillar. Belongs to exactly one pillar. Optimum 2–3, recommended max 3 per pillar (1–3 under a cascaded pillar); ceiling 5 (validator). Carries its own time frame — a start and an end date (`timing`) — the window its Goal is assessed in; ~8 initiatives per printed page — print capacity, not a ceiling: the landscape A4 sheet is as tall as its fullest pillar column, and the renderer continues an overflowing page onto a second sheet rather than dropping anything |
| Goal | initiative `goal` | 1 per initiative (schema default; optional in the methodology) | The initiative's Definition of Success: the specific, measurable result of the initiative, in one or two measures — the engine of the cascade (becomes the child pillar's DEOS). It carries no dates — the initiative's `timing` is the window. The methodology's earlier name *Picture of Success* (PICOS) is retired |
| Enablers | `enablers` | L0 only | Conditions performance rests on — "how we organise ourselves", not "what we want to achieve". Even an enabler is defined from the perspective of change: what must be built, improved or elevated. The routine of running the operation (service levels, routine quality targets, steady-state obligations) is not an enabler — it stays off the page. Optimum 3–4, ceiling 5. Name = **short noun phrase that names the change** ("Upgraded CRM platform", "Modern ERP backbone"), never a verb exhortation and never a bare tool noun ("CRM technology") — the name cascades verbatim into child pillar names. A source pillar named for an organisational condition (People / Our People, Foundations, Finance, IT / Systems, Culture, Governance) belongs here unless its content states a customer- or market-facing outcome; moving it is a cut the leadership team must accept, so it gets an open question ("the sources list X as a pillar; this cascade keeps it as an enabler — does the leadership team accept that cut?") |
| Culture / Values / Behaviours | `values` | optional, L0 | Attitudes and behaviours, **first person**, short ("We are in it together"). Ceiling 5 — never an error: keep every value the sources state, and above five add an open question naming the actual count, e.g. "you list seven values; the methodology recommends five — which five do you run by?". The validator's ceiling warning on values is answered by that open question, never by cutting a value. Never invent them |
| Critical Teams | — *(expressed via cascade `links`)* | optional | Which teams deliver an initiative — this drives the cascade (below). A team is critical only when a distinct part of the initiative — a sub-task it owns, with its own goal — lands on its own page as a pillar. Being needed is not the test: a function that only provides service or capacity (IT, Finance) belongs in Enablers or horizontal alignment |

## Writing rules (these carry most of the weight)

1. **An initiative is a sentence with a verb, not an attitude.** "Launch the new client
   platform", "Redesign the client onboarding process". The target does not sit in the
   initiative, it sits in the goal: "live in Q3", "onboarding cut from fourteen days to five" —
   the initiative says what you will do, the goal what you will have to show for it. Noun
   phrases ("Brand development", "Process automation") quietly avoid concreteness — rewrite
   them. Attitudes ("growth mindset",
   "customer centricity") belong in Values, never in Initiatives.
2. **An initiative must stand on its own for a distant reader.** An accountant should understand
   a trading initiative. Spell out domain acronyms on first use. If a colleague from the
   furthest-away function would have to ask, rewrite.
3. **A goal measures output, not input, and carries a number or a clearly assessable state.**
   Not "improve visibility" but "+20% organic traffic". Reserve input goals ("the system is
   live") for cases where nothing else is honestly possible (regulatory milestone, governance
   approval). The test: could you say mid-year "we are green, yellow or red" against it? If not,
   it's written wrong.
4. **Keep it to the ten or twelve things that matter.** A one-pager is a strategic document, not
   a task list; within a pillar, up to three. When the sources offer far more, propose the cut
   and put the rest in open questions. When a pillar has more than three candidate initiatives,
   move one to the pillar it serves better or report it as a gap — never merge two initiatives
   into one sentence. Four or five initiatives in one pillar still validate, but add an open
   question naming the count ("this pillar carries five initiatives; the methodology recommends
   three — which can move or wait?"), so the Gap Report shows it.
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
| "What we want to do" | "How we organise ourselves" |
| Output / impact | Input |

Enabler categories: tools (ERP, CRM), processes (efficiency, agile adoption), people (capability,
talent), mindset/culture, legal framework, business context, governance. **A shared resource is not
an enabler**: "CAPEX budget" as an enabler is an anti-pattern — an enabler is an organisational or
human condition, not a cost line. A tool named as a bare noun ("CRM technology") is a different
case: not wrong in kind, only missing the change — "Upgraded CRM platform" is a legitimate enabler.

An enabler may be *promoted* to an initiative in exactly three cases: it's a genuine game-changer
for the business (AI adoption in a sector being reshaped by it), a source of unique
differentiation (an agile capability that becomes a signature advantage), or core DNA (a
genuinely exceptional culture). Otherwise keep the line clean: a new ERP is an enabler; market
expansion is an initiative.

## The vertical cascade

The mechanism is precise:

- A Key Initiative names its **Critical Teams** (max 3 in schema v1 — the methodology sets no
  cap; direct reports of the one-pager's owner only). For each critical team, the initiative
  becomes a **Strategic Pillar on that team's one-pager**, carrying its Goal as the new pillar's
  Definition of Success. The receiving team then writes its own Key Initiatives under that
  pillar.
- **Shared initiatives:** where several teams share an initiative, each team's pillar keeps the
  parent goal verbatim in `successDefinition1` and states the team's own part in
  `successDefinition2`. When the sources do not say how the work divides, leave
  `successDefinition2` null and raise the split as an open question.
- Keep any one team to about five cascades from the same one-pager — more means its page
  carries too many pillars; flag it as an open question.
- **The dead-end rule:** if the owning team itself does the work, the initiative does not cascade
  — it terminates at that level. Not every initiative produces a child pillar.
- Enablers sit on L0 and cascade like initiatives — to the teams that will carry a distinct part
  of building them, not to every team that will use the result. When the sources don't say,
  cascade to the teams they name and raise the rest as an open question.
- The Strategic Ambition is copied read-only into every child; the child adds its own Team
  Strategic Ambition above its pillars.
- Cascaded values are **verbatim copies** — alignment is only checkable when the words match.
- **Sparse sources and the team page:** the initiatives the receiving team writes are real
  content in its own domain language, distinct from every sibling team's. Thin sources → propose
  them (`[PROPOSED]`) with an open question naming what that team must confirm; nothing known
  about the team → leave the goals `null` and raise a targeted open question.

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
4. A shared resource dressed as an enabler — "Marketing budget". (A bare tool noun such as
   "CRM technology" is a different case: name the change instead — "Upgraded CRM platform".)
5. Placeholder content — "[x]", "Type something".
6. A question or internal note in an initiative field.
7. More than five pillars, or fifteen or more initiatives, on a single L0 one-pager —
   acceptable at the edge for a large enterprise, but a signal to prioritise.
8. A facilitation instruction standing in for content — "Break this pillar into the team's key
   initiatives" written as an initiative, "define measurable goals" written as a goal.
9. The same initiative or goal repeated across sibling team pages — interchangeable pages mean
   no team actually planned.
