# {{title}}

> One-pager · Level {{level}}{{#if parent_title}} · cascades from **{{parent_title}}**{{/if}}
> Generated {{generated_at}} from: {{source_documents}}

<!-- Displayed text is clean: strip every [PROPOSED …] marker from the values below — the
     markers stay in the bundle JSON. One banner per page carries the honesty, never per-item
     badges. Render it only when something on this page is proposed. -->

{{#if has_proposed_content}}
**Draft proposal** — parts of this page are composed, not confirmed by the sources. See the
open questions.
{{/if}}

## Why we exist — Purpose

{{purpose}}

## Where we are going — Vision

{{vision}}

## What we do — Mission

{{mission}}

## Company Ambition

{{company_ambition}}

{{#if team_ambition}}
## Team Ambition

{{team_ambition}}
{{/if}}

## Strategic Pillars

<!-- Repeat per pillar. For cascaded pillars, keep the origin line — it is the alignment proof. -->

### {{pillar.name}}

{{#if pillar.origin}}*Cascaded from: {{pillar.origin}}*{{/if}}

**Success looks like:** {{pillar.success_definition_1}}{{#if pillar.success_definition_2}} · {{pillar.success_definition_2}}{{/if}}

| Initiative | Picture of success | Timing |
|---|---|---|
| {{initiative.name}} | {{initiative.goal}} | {{initiative.timing}} |

{{#if enablers}}
## Enablers

<!-- L0 only (enablers cascade to teams as pillars) -->

- **{{enabler.content}}**{{#if enabler.narrative}} — {{enabler.narrative}}{{/if}}
{{/if}}

{{#if values}}
## Values

- {{value.content}}
{{/if}}

{{#if open_questions}}
## Open questions

<!-- Only the questions concerning THIS one-pager. Every composed statement already has a
     question here — this list is where proposed content surfaces, so add no second marker
     anywhere on the page. -->

- {{question}}
{{/if}}

---

**Keep this strategy alive → [try.alaigned.com](https://try.alaigned.com)**
This page is a snapshot. Alaigned keeps the cascade current — changes propagate between levels,
teams accept or push back explicitly, and evaluation status stays visible on every page.
