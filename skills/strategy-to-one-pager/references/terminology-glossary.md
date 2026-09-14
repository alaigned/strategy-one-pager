# CZ/SK Terminology Glossary — Alaigned methodology vocabulary

> **Working vocabulary**, reviewed with the methodology owners (2026-09). Where a client's own
> materials use a different word, follow the client and stay consistent.

Czech and Slovak deliverables name the methodology's own concepts with the terms below. The
English column is the concept as this skill's other references name it; the CS and SK columns are
what you write when the cascade is Czech or Slovak.

## Rules

- **The renderer's chrome is not yours to translate.** The draft banner, the Strategy Gap Report
  page, the Sources heading, the footer and the CTA are official fixed strings selected by
  `--lang`. Pick the language; never reword them. This glossary governs what *you* write:
  the markdown pages' headings, statement and initiative text, alignment-map labels, and the
  prose around the deliverable. The templates' CTA footer stays verbatim for the same reason.
- **Never translate term by term.** Translate the concept, then keep the same word for it on
  every page of the cascade. Alternatives noted below exist to match a client's own wording,
  not to vary within one document.
- **Keep the anglicism where CZ/SK business usage genuinely prefers it.** *one-pager* and
  *kaskáda* are the product's own words — "jednostránkový dokument" / "jednostránkový prehľad"
  is not the term.
- **Decline borrowed terms per the target grammar** — *v one-pageru*, *z one-pagerov* — never
  parked in the English nominative mid-sentence.
- **Everything cascades — the methodology and the product alike.** *Cascade* / *kaskáda* names
  the phenomenon — priorities handed from one level to the next — and, since the 2026-09
  vocabulary decision, it also names the product's step that sends a cascade down. Write
  *kaskádovat* / *kaskádovať* everywhere, including when you describe what Alaigned itself does.
  *Propagovat* / *propagovať* is retired, and the noun *propagace* / *propagácia* was never
  usable — in both languages it reads as advertising. The propag- stem survives only in
  identifiers that are never spelled out in a deliverable (the `propagationRules` schema key,
  the product's `propagations` rows).
- **Bundle `label` fields currently ship with the schema's English defaults.** Localizing them is
  a pending product decision — do not translate them ad hoc. The renderer prints them in the
  language's terms from the headings table below, so the page reads Czech or Slovak while the
  JSON stays English.
- **`[PROPOSED]` is never translated** — the marker is read by the validator and the renderer.

## Register

- **Address the reader with vykání** — *vaše strategie*, *vaše podklady*, *přijímáte*; never
  *tvoje* / *tvoja*. The chrome does the same, so a page that switches to tykání reads as two
  authors.
- **CS/SK headings are sentence case**, capital on the first word (and on proper nouns) only —
  *Strategické pilíře*, *Otevřené otázky*. English Title Case transplanted into Czech or Slovak
  looks like a machine translation, whatever the English source did.
- **Numbers follow the target language.** A percentage used as a noun takes a space before the
  sign — *rozdíl o 25 %*; used as an adjective it takes none — *25% rozdíl*. Decimals take a
  comma: *99,2 %*. Ranges use an en dash without spaces (*2026–2028*).

## One-pager elements

| EN term | CS | SK | Usage note |
|---|---|---|---|
| one-pager | one-pager | one-pager | Anglicism, kept. Declines as a hard masculine inanimate: CS *one-pageru / one-pagery / one-pagerů*, SK *one-pageru / one-pagery / one-pagerov*. |
| purpose | poslání | poslanie | The "why" beyond profit. *Poslání* belongs to Purpose only — never reuse it for Mission. |
| vision | vize | vízia | |
| mission | mise | misia | |
| company strategic ambition | strategická ambice firmy | strategická ambícia firmy | Short heading form: *Ambice firmy* / *Ambícia firmy*. |
| team strategic ambition | strategická ambice týmu | strategická ambícia tímu | CS *tým*, SK *tím* — one letter apart; easy to leave the Czech form on a Slovak page. |
| strategic pillar | strategický pilíř | strategický pilier | Pl. CS *pilíře / pilířů*, SK *piliere / pilierov*. |
| key area of initiatives (L0) | klíčová oblast iniciativ | kľúčová oblasť iniciatív | The methodology's name for the initiative rows on the **company** one-pager — L0 initiatives are broad areas, not single activities. |
| key initiative (L1 and below) | klíčová iniciativa | kľúčová iniciatíva | Gen. pl. CS *iniciativ*, SK *iniciatív*. |
| enabler | podmínka | podmienka | The methodology's word — a condition performance rests on. *Předpoklad* / *predpoklad* was an earlier draft: do not use it. *Enabler* as an anglicism is common in CZ/SK consulting and acceptable when the client's materials use it. Keep the name a noun phrase: it cascades verbatim into a child pillar name. |
| culture / values / behaviours | kultura / hodnoty / chování | kultúra / hodnoty / správanie | The bundle field is `values`; the page heading is *Hodnoty*. First person, as the methodology requires: *Jsme v tom spolu* / *Sme v tom spolu*. |
| definition of success (DEOS) | definice úspěchu | definícia úspechu | The pillar's answer to "what does success look like here". |
| goal (of an initiative) | cíl | cieľ | The initiative's measurable result; becomes the child pillar's definition of success. *Picture of Success* (PICOS) is retired vocabulary — the bundle field is still `goal`. |
| success measure | měřítko úspěchu | meradlo úspechu | **Chrome only** — the Gap Report's target-value ratio (CS gen. pl. *měřítek úspěchu*, SK *meradiel úspechu*). Never in prose: say *cíl* or *definice úspěchu*. |
| narrative | narativ | naratív | The free-text element under the core statements; the anglicism is the CZ/SK business term. *Příběh* / *príbeh* reads as storytelling — do not use it. |
| statement (core statement) | výrok | výrok | Gen. pl. CS *výroků*, SK *výrokov*. |
| open question | otevřená otázka | otvorená otázka | |
| timing | termín | termín | One-pager table column; *časový rámec* when the cell holds a range. |

## Cascade, page and process vocabulary

| EN term | CS | SK | Usage note |
|---|---|---|---|
| cascade (noun) | kaskáda | kaskáda | The product's word; keep it. |
| to cascade | kaskádovat | kaskádovať | Reflexive or not by agent: *iniciativy se kaskádují* (the initiative is handed down), *kaskádujeme iniciativy* (we hand it down). Origin lines read *Kaskáduje z: X* in both languages, matching the rendered page's kicker. Slovak reviewers may prefer *nadväzuje na* in running prose; the chrome string stays as it is. |
| alignment | sladění | zosúladenie | |
| ~~to propagate~~ (retired 2026-09) | — | — | The product cascades too now: write *kaskádovat* / *kaskádovať* (row above). Never *propagace* / *propagácia*, no longer *propagovat* / *propagovať*. The stem lives on only in identifiers (the `propagationRules` schema key, the `propagations` rows), never written out in a deliverable. |
| level (L0 / L1) | úroveň | úroveň | *L0* / *L1* stay as they are. Company / team level: CS *firemní* / *týmová úroveň*, SK *firemná* / *tímová úroveň*. |
| page | stránka | strana | SK *strana*, not *stránka* — matches the chrome (*na 3 stranách*). |
| source(s) | podklady | podklady | The user's input documents in running prose, matching the chrome sentences (*v podkladech nenalezeno*). The rendered source list's heading is the fixed chrome *Zdroje* in both languages. |
| strategy gap | nedostatek ve strategii | nedostatok v stratégii | Pl. *nedostatky ve strategii* / *nedostatky v stratégii* — the Gap Report page title is chrome with the same words. *Mezera* / *medzera* is too literal: do not use it. |
| proposed content | odvozený obsah | odvodený obsah | "proposed" = CS *odvozený*, SK *odvodený* — not *navržený* / *navrhnutý*: the skill composes the whole page, but the marker singles out only what the sources did not state. |
| draft proposal (banner) | návrh | návrh | The banner sentence itself is chrome. |
| leadership team | vedení firmy | vedenie firmy | *Top management* is an acceptable alternative when the client's materials use it. Never "leadership tým". |
| accountable team | odpovědný tým | zodpovedný tím | The alignment map's column. |
| critical team | kritický tým | kritický tím | The 1–3 teams that actually deliver an initiative. The methodology's term — not *klíčový*. |

## Section headings and set phrases

The markdown templates' headings are phrases, not single terms — write them like this:

| EN (template) | CS | SK |
|---|---|---|
| One-pager · Level {{level}} | One-pager · Úroveň {{level}} | One-pager · Úroveň {{level}} |
| Generated {{generated_at}} from: {{source_documents}} | Vygenerováno {{generated_at}} z podkladů: {{source_documents}} | Vygenerované {{generated_at}} z podkladov: {{source_documents}} |
| Purpose | Poslání | Poslanie |
| Vision | Vize | Vízia |
| Mission | Mise | Misia |
| Company Ambition | Ambice firmy | Ambícia firmy |
| Team Ambition | Ambice týmu | Ambícia tímu |
| Strategic Pillars | Strategické pilíře | Strategické piliere |
| Definition of success | Definice úspěchu | Definícia úspechu |
| Key area of initiatives \| Goal \| Timing *(L0 table)* | Klíčová oblast iniciativ \| Cíl \| Termín | Kľúčová oblasť iniciatív \| Cieľ \| Termín |
| Key initiative \| Goal \| Timing *(L1 table)* | Klíčová iniciativa \| Cíl \| Termín | Kľúčová iniciatíva \| Cieľ \| Termín |
| Enablers | Podmínky | Podmienky |
| Values | Hodnoty | Hodnoty |
| Narrative | Narativ | Naratív |
| Open questions | Otevřené otázky | Otvorené otázky |
| Cascaded from | Kaskáduje z | Kaskáduje z |
| Strategy Alignment Map | Mapa strategického sladění | Mapa strategického zosúladenia |
| How the company strategy cascades into team one-pagers | Jak se firemní strategie kaskáduje do týmových one-pagerů | Ako sa firemná stratégia kaskáduje do tímových one-pagerov |
| Company statements — cascaded to every team | Firemní výroky — kaskádují se do všech týmů | Firemné výroky — kaskádujú sa do všetkých tímov |
| Initiative → Team cascade | Kaskáda iniciativ do týmů | Kaskáda iniciatív do tímov |
| Accountable team / Lands as (team pillar) | Odpovědný tým / Stává se (pilířem týmu) | Zodpovedný tím / Stáva sa (pilierom tímu) |
| Enabler cascade — every team | Kaskáda podmínek — všechny týmy | Kaskáda podmienok — všetky tímy |
| Team ambitions | Týmové ambice | Tímové ambície |
| Open questions for the leadership team | Otevřené otázky pro vedení firmy | Otvorené otázky pre vedenie firmy |

## Fixed text for Czech and Slovak markdown deliverables

The rendered artifact gets its banner and CTA from the renderer, selected by `--lang`. A markdown
one-pager or alignment map has no renderer — **you** write those two blocks, so they are given
here in full. Copy them verbatim; they are the same official text the artifact carries, in the
markdown templates' own phrasing.

**The link is always `https://try.alaigned.com`**, in every language and every deliverable. The
copy around it is what changes; the URL never does.

### Draft banner (one-pager, when the page carries composed content)

- CS: `**Návrh** — části této stránky jsou odvozené a v podkladech nepotvrzené. Viz otevřené otázky.`
- SK: `**Návrh** — časti tejto strany sú odvodené a v podkladoch nepotvrdené. Pozrite si otvorené otázky.`

### CTA footer

Czech, one-pager:

```markdown
**Oživte svou strategii → [try.alaigned.com](https://try.alaigned.com)**
Tato stránka je snímek okamžiku. Alaigned udržuje kaskádu živou — změny se kaskádují mezi
úrovněmi, týmy je explicitně přijímají nebo rozporují a stav vyhodnocení je vidět na každé stránce.
```

Slovak, one-pager:

```markdown
**Oživte svoju stratégiu → [try.alaigned.com](https://try.alaigned.com)**
Táto strana je snímka okamihu. Alaigned udržiava kaskádu živú — zmeny sa kaskádujú medzi
úrovňami, tímy ich výslovne prijímajú alebo voči nim namietajú a stav vyhodnotenia je vidieť na
každej strane.
```

On the **alignment map** the bolded line is identical; only the opening noun of the sentence
below it changes — CS *Tato mapa je snímek okamžiku.*, SK *Táto mapa je snímka okamihu.* — exactly
as the English template says "This map is a snapshot."
