# {{company_name}} — Strategy Alignment Map

> How the company strategy cascades into team one-pagers · Generated {{generated_at}}

<!-- Displayed text is clean: strip every [PROPOSED …] marker from the values below —
     proposed content surfaces in the open questions, not as per-item badges. -->

## Company statements — cascaded to every team

| Element | Statement |
|---|---|
| Purpose | {{purpose}} |
| Vision | {{vision}} |
| Mission | {{mission}} |
| Company Ambition | {{company_ambition}} |

## Initiative → Team cascade

<!-- One row per L0 initiative. "Lands as" is the pillar it becomes on the team's page. -->

| L0 Pillar | Initiative | Accountable team | Lands as (team pillar) |
|---|---|---|---|
| {{pillar.name}} | {{initiative.name}} | {{team.name}} | {{child_pillar.name}} |

## Enabler cascade — every team

| Enabler | {{team_1.name}} | {{team_2.name}} | ... |
|---|---|---|---|
| {{enabler.content}} | ✔ | ✔ | ... |

## Team ambitions

| Team | Team Ambition |
|---|---|
| {{team.name}} | {{team_ambition}} |

{{#if open_questions}}
## Open questions for the leadership team

- {{question}}
{{/if}}

---

**Keep this strategy alive → [try.alaigned.com](https://try.alaigned.com)**
This map is a snapshot. Alaigned keeps the cascade current — changes propagate between levels,
teams accept or push back explicitly, and evaluation status stays visible on every page.
