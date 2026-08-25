# Cascade Bundle — Output Contract (v0.1)

The primary artifact is one JSON file (the **bundle**). Its envelope is specified by
`../cascade-bundle.schema.json`; each one-pager's `content` is additionally validated against the
per-level schema inside `../schemas/methodology.inlined.json` (`hierarchy[level].onePagerSchema`).
`scripts/validate_cascade.py` checks both plus the structural rules below.

## Envelope

```json
{
  "bundleVersion": "0.1",
  "generator": {
    "skill": "strategy-to-one-pager",
    "skillVersion": "0.1.0",
    "generatedAt": "2026-07-06"
  },
  "methodology": {
    "methodologyID": "methodology-v1",
    "fingerprint": "sha256:<64 hex chars>",
    "fingerprintGeneratedAt": "2026-07-06"
  },
  "attribution": {
    "ref": "3f6f2b1e-6c9d-4b6e-9c57-2a8b6d1f4e0a"
  },
  "company": {
    "name": "Meridian Logistics",
    "sourceDocuments": ["strategy-brief.md"]
  },
  "onePagers": [ ... ],
  "links": [ ... ],
  "openQuestions": ["Who owns initiative X — Operations or Commercial?"]
}
```

- `methodology.*` is copied from `../schemas/fingerprint.json` (`methodologyID`, `fingerprint`,
  `generatedAt` → `fingerprintGeneratedAt`). Never fabricate it.
- `attribution.ref` (optional, strongly recommended) is one fresh UUIDv4 generated when the
  bundle is first assembled. The printable artifact's CTA links inherit it and a later import
  ties the bundle back to this run — keep it stable across edits and re-renders.
- `company.sourceDocuments` lists every source the cascade draws on — documents by filename,
  public web sources as `"https://… (accessed YYYY-MM-DD)"` (the access date makes a fetched
  page citable). Free text either way; the renderer's Gap Report lists them as Sources.
- `openQuestions` collects every gap found during extraction.
- `[PROPOSED …]` markers are valid only inside `onePagers[].content` `textValue`s. The
  validator rejects one in `company.name` or a one-pager `title` — both render verbatim into
  the page heading and are invisible to the renderer's proposed-content walk. A marker
  mentioned in `openQuestions` prose is not policed.

## One-pagers

```json
{
  "ref": "l1-operations",
  "level": 1,
  "title": "Meridian Logistics — Operations",
  "parentRef": "l0",
  "content": { ... }
}
```

- `ref` is a bundle-local slug, unique across `onePagers`. The L0 uses `"l0"`; L1s use
  `"l1-<team-slug>"`.
- Exactly **one** level-0 one-pager with `parentRef: null`; every other one-pager's `parentRef`
  must resolve, with `level` = parent's level + 1. This skill produces L0 + L1 only.

### `content` — the one-pager body

`content` must validate against `hierarchy[level].onePagerSchema` from
`../schemas/methodology.inlined.json`. Key facts of that schema (v1):

- **Elements are objects, not strings.** A text element looks like:

  ```json
  { "label": "Purpose", "textValue": "Why we exist beyond profit.", "mandatory": true }
  ```

  `label` and `textValue` are **required** on every text element (labels come from the schema's
  defaults: "Purpose", "Vision", "Mission", "Company Strategic Ambition", "Team Strategic
  Ambition", "Name", "Goal (picture of success)", "Success 1", "Success 2", "Narrative", "Text",
  "Pillar", "Initiative", "Enabler", "Value", "Pillars", "Initiatives", "Enablers", "Values").
  `textValue` may be `null` for honest gaps — pair that with an open question.

- **Collections wrap their items in `content` arrays** (max 100 items):

  ```json
  "pillars": { "label": "Pillars", "content": [ { ...pillar... }, ... ] }
  ```

- **Every collection item carries `metadata.id`** — a fresh UUIDv4, unique across the whole
  bundle:

  ```json
  { "label": "Pillar", "metadata": { "id": "0b6f0e9e-..." }, "name": { ... }, ... }
  ```

- **Top-level `metadata`** of each one-pager: `{ "schemaVersion": "v1" }`.

- **Required at L0**: `purpose`, `vision`, `mission`, `companyAmbition`, `pillars`, `enablers`.
  **Required at L1**: `teamAmbition`, `pillars`. (Include the propagated core fields on L1 too —
  they're how alignment shows.)

- **Required per entity**: pillar → `label`, `metadata`, `name`, `initiatives`; initiative →
  `label`, `metadata`, `name` (plus `goal` in practice); enabler → `label`, `metadata`, `content`;
  value → `label`, `metadata`, `content`.

- Initiative `timing` (optional): `{ "startDate": "2026-01", "endDate": "2026-12" }` — `YYYY-MM`
  strings, no other keys allowed.

## Path grammar

Paths address values inside a one-pager's `content`, dot-separated. Array steps go **through
`content` and then the entity's `metadata.id`**:

```
purpose.textValue
pillars.content.<pillarId>.name.textValue
pillars.content.<pillarId>.initiatives.content.<initiativeId>.goal.textValue
enablers.content.<enablerId>.content.textValue
```

This matches the Alaigned product's propagation paths, which is what makes the bundle
import-ready.

## Links — the alignment model

One `links[]` entry per propagated field. A link mirrors an *accepted* propagation in the product:
the bundle is an **interchange format for import**, so it deliberately follows the product's
*current* storage model (Propagation rows), not a hypothetical future one. If the product moves
propagations into one-pager content (a refactor the team has discussed), the bundle follows in a
new `bundleVersion` — the envelope pins the version precisely so this migration is explicit
rather than silent.

```json
{
  "parentRef": "l0",
  "childRef": "l1-operations",
  "parentRule": "pillars.content.*.initiatives.content.*.name.textValue",
  "childRule": "pillars.content.*.name.textValue",
  "parentPath": "pillars.content.<pillarId>.initiatives.content.<initiativeId>.name.textValue",
  "childPath": "pillars.content.<childPillarId>.name.textValue"
}
```

Rules (validator-enforced):

- (`parentRule` → `childRule`) must be one of the parent level's `propagationRules` pairs from the
  methodology. For L0→L1 (v1) these are exactly:

  | parentRule | childRule |
  |---|---|
  | `purpose.textValue` | `purpose.textValue` |
  | `vision.textValue` | `vision.textValue` |
  | `mission.textValue` | `mission.textValue` |
  | `companyAmbition.textValue` | `companyAmbition.textValue` |
  | `pillars.content.*.initiatives.content.*.name.textValue` | `pillars.content.*.name.textValue` |
  | `pillars.content.*.initiatives.content.*.goal.textValue` | `pillars.content.*.successDefinition1.textValue` |
  | `enablers.content.*.content.textValue` | `pillars.content.*.name.textValue` |

- `parentPath` must match `parentRule` and `childPath` must match `childRule` (same segments,
  with each `*` replaced by a concrete entity id).
- Both paths must resolve, and **the values at both ends must be equal** — propagation is a
  verbatim copy.
- `parentRef`/`childRef` must be an actual parent→child edge (`child.parentRef == parentRef`).

Cascade completeness (validator-enforced):

- Every L1 has a core-field link for **each core field whose L0 `textValue` is non-null**
  (the Strategic Ambition is always filled; Purpose/Vision/Mission — whichever of them are).
- Every L1 pillar is the **target of at least one link** — i.e. it demonstrably derives from a
  parent initiative (name + goal→successDefinition1 links) or a parent enabler (content→name
  link). Team-local pillars with no parent origin are not allowed at L1 in this skill's output;
  if a team insists on one, record it as an open question instead.
- A cascading L0 initiative links to **1–3 children** — its critical teams (dead-end initiatives,
  delivered by the L0 owner's own team, link to none). Enablers link to the children that must
  build or adopt them.
- Element-count ceilings and the critical-team cap are read from the methodology artifact
  (`hierarchy[].limits` in `schemas/methodology.inlined.json`): ceilings report as validator
  **warnings**, the critical-team cap as an error.

## Worked micro-example

L0 pillar "Network Excellence" has initiative "Hub automation rollout" (goal: "All three hubs run
automated sortation by end of 2027") assigned to team Operations. The bundle then contains:

- L0 `content.pillars.content[]` → pillar `p1` with `initiatives.content[]` → initiative `i1`
  (`name.textValue` = "Hub automation rollout", `goal.textValue` = "All three hubs run...").
- L1-operations `content.pillars.content[]` → pillar `cp1` with `name.textValue` =
  "Hub automation rollout" (verbatim) and `successDefinition1.textValue` = "All three hubs run..."
  (verbatim), plus that team's own `initiatives.content[]` breaking the pillar down.
- Two links: (`...initiatives.content.*.name.textValue` → `pillars.content.*.name.textValue`,
  paths through `p1`/`i1`/`cp1`) and (`...goal.textValue` → `...successDefinition1.textValue`,
  same entities).

A complete valid bundle lives in the eval golden set:
`plg/evals/golden/synthetic/meridian/expected/cascade.json` (monorepo only, not packaged with the
public skill).
