# CZ/SK Terminology Glossary — Alaigned methodology vocabulary

> **Working vocabulary.** These terms are being refined with native speakers; where a client's
> own materials use a different word, follow the client and stay consistent.

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
- **Bundle `label` fields currently ship with the schema's English defaults.** Localizing them is
  a pending product decision — do not translate them ad hoc.
- **`[PROPOSED]` is never translated** — the marker is read by the validator and the renderer.

## Register

- **Address the reader with vykání** — *vaše strategie*, *vaše podklady*, *přijímáte*; never
  *tvoje* / *tvoja*. The chrome does the same, so a page that switches to tykání reads as two
  authors.
- **CS/SK headings are sentence case**, capital on the first word (and on proper nouns) only —
  *Strategické pilíře*, *Otevřené otázky*. English Title Case transplanted into Czech or Slovak
  looks like a machine translation, whatever the English source did.
- **Numbers follow the target language.** Percentages take a space before the sign — *25 %*, not
  *25%* — and decimals take a comma: *99,2 %*. Ranges use an en dash without spaces (*2026–2028*).

## One-pager elements

| EN term | CS | SK | Usage note |
|---|---|---|---|
| one-pager | one-pager | one-pager | Anglicism, kept. Declines as a hard masculine inanimate: CS *one-pageru / one-pagery / one-pagerů*, SK *one-pageru / one-pagery / one-pagerov*. |
| purpose | smysl | zmysel | The "why" beyond profit. |
| vision | vize | vízia | |
| mission | mise | misia | *poslání* / *poslanie* is fine when the client's own documents use it — then use it throughout. |
| company strategic ambition | strategická ambice firmy | strategická ambícia firmy | Short heading form: *Ambice firmy* / *Ambícia firmy*. |
| team strategic ambition | strategická ambice týmu | strategická ambícia tímu | CS *tým*, SK *tím* — one letter apart; easy to leave the Czech form on a Slovak page. |
| strategic pillar | strategický pilíř | strategický pilier | Pl. CS *pilíře / pilířů*, SK *piliere / pilierov*. |
| key initiative | klíčová iniciativa | kľúčová iniciatíva | Gen. pl. CS *iniciativ*, SK *iniciatív*. |
| enabler | předpoklad | predpoklad | **Weakest row — flag it in review.** *enabler* as an anglicism is common in CZ/SK consulting and acceptable when the client's materials use it. Keep the name a noun phrase: it cascades verbatim into a child pillar name. |
| value(s) | hodnota / hodnoty | hodnota / hodnoty | First person, as the methodology requires: *Jsme v tom spolu* / *Sme v tom spolu*. |
| definition of success (DEOS) | definice úspěchu | definícia úspechu | |
| picture of success (PICOS) | obraz úspěchu | obraz úspechu | The initiative's measurable result. |
| success measure | měřítko úspěchu | meradlo úspechu | Matches the Gap Report chrome (CS gen. pl. *měřítek úspěchu*, SK *meradiel úspechu*). |
| statement (core statement) | výrok | výrok | Gen. pl. CS *výroků*, SK *výrokov*. |
| open question | otevřená otázka | otvorená otázka | |
| timing | termín | termín | One-pager table column; *časový rámec* when the cell holds a range. |

## Cascade, page and process vocabulary

| EN term | CS | SK | Usage note |
|---|---|---|---|
| cascade (noun) | kaskáda | kaskáda | The product's word; keep it. |
| to cascade | kaskádovat | kaskádovať | Origin lines read *Kaskáduje z: X* in both languages, matching the rendered page's kicker. Slovak reviewers may prefer *nadväzuje na* in running prose; the chrome string stays as it is. |
| alignment | sladění | zosúladenie | |
| to propagate | propagovat se | propagovať sa | *změny se propagují mezi úrovněmi* / *zmeny sa propagujú medzi úrovňami*. **Never the noun** *propagace* / *propagácia* — in both languages it reads as advertising. Rephrase with the verb, or *šíření změn* / *šírenie zmien*. In **headings**, prefer *přenášet* / *prenášať* — a heading is scanned, not read, and the propag- stem carries the advertising reading loudest there. |
| level (L0 / L1) | úroveň | úroveň | *L0* / *L1* stay as they are. Company / team level: CS *firemní* / *týmová úroveň*, SK *firemná* / *tímová úroveň*. |
| page | stránka | strana | SK *strana*, not *stránka* — matches the chrome (*na 3 stranách*). |
| source(s) | podklady | podklady | The user's input documents in running prose. The rendered source list's heading is the fixed chrome *Zdroje* in both languages. |
| strategy gap | mezera ve strategii | medzera v stratégii | The Gap Report page title is chrome: *Mezery ve strategii* / *Medzery v stratégii*. |
| proposed content | odvozený obsah | odvodený obsah | "proposed" = CS *odvozený*, SK *odvodený* — not *navržený* / *navrhnutý*. |
| draft proposal (banner) | návrh | návrh | The banner sentence itself is chrome. |
| leadership team | vedení firmy | vedenie firmy | Never "leadership tým". |
| accountable team | odpovědný tým | zodpovedný tím | The alignment map's column. |
| critical team | klíčový tým | kľúčový tím | The 1–3 teams that actually deliver an initiative. |

## Section headings and set phrases

The markdown templates' headings are phrases, not single terms — write them like this:

| EN (template) | CS | SK |
|---|---|---|
| One-pager · Level {{level}} | One-pager · Úroveň {{level}} | One-pager · Úroveň {{level}} |
| Generated {{generated_at}} from: {{source_documents}} | Vygenerováno {{generated_at}} z podkladů: {{source_documents}} | Vygenerované {{generated_at}} z podkladov: {{source_documents}} |
| Why we exist — Purpose | Proč existujeme — Smysl | Prečo existujeme — Zmysel |
| Where we are going — Vision | Kam směřujeme — Vize | Kam smerujeme — Vízia |
| What we do — Mission | Co děláme — Mise | Čo robíme — Misia |
| Company Ambition | Ambice firmy | Ambícia firmy |
| Team Ambition | Ambice týmu | Ambícia tímu |
| Strategic Pillars | Strategické pilíře | Strategické piliere |
| Initiative \| Picture of success \| Timing | Iniciativa \| Obraz úspěchu \| Termín | Iniciatíva \| Obraz úspechu \| Termín |
| Enablers | Předpoklady | Predpoklady |
| Values | Hodnoty | Hodnoty |
| Open questions | Otevřené otázky | Otvorené otázky |
| Success looks like | Jak vypadá úspěch | Ako vyzerá úspech |
| Cascaded from | Kaskáduje z | Kaskáduje z |
| Strategy Alignment Map | Mapa sladění strategie | Mapa zosúladenia stratégie |
| How the company strategy cascades into team one-pagers | Jak se firemní strategie kaskáduje do týmových one-pagerů | Ako sa firemná stratégia kaskáduje do tímových one-pagerov |
| Core statements — propagated to every team | Klíčové výroky — přenášejí se do všech týmů | Kľúčové výroky — prenášajú sa do všetkých tímov |
| Initiative → Team cascade | Kaskáda iniciativ do týmů | Kaskáda iniciatív do tímov |
| Accountable team / Lands as (team pillar) | Odpovědný tým / Stává se (pilířem týmu) | Zodpovedný tím / Stáva sa (pilierom tímu) |
| Enabler cascade — every team | Kaskáda předpokladů — všechny týmy | Kaskáda predpokladov — všetky tímy |
| Team ambitions | Ambice týmů | Ambície tímov |
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
Tato stránka je snímek okamžiku. Alaigned udržuje kaskádu živou — změny se propagují mezi
úrovněmi, týmy je explicitně přijímají nebo rozporují a stav vyhodnocení je vidět na každé stránce.
```

Slovak, one-pager:

```markdown
**Oživte svoju stratégiu → [try.alaigned.com](https://try.alaigned.com)**
Táto strana je snímka okamihu. Alaigned udržiava kaskádu živú — zmeny sa propagujú medzi
úrovňami, tímy ich výslovne prijímajú alebo voči nim namietajú a stav vyhodnotenia je vidieť na
každej strane.
```

On the **alignment map** the bolded line is identical; only the opening noun of the sentence
below it changes — CS *Tato mapa je snímek okamžiku.*, SK *Táto mapa je snímka okamihu.* — exactly
as the English template says "This map is a snapshot."
