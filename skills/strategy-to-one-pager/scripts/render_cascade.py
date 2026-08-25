#!/usr/bin/env python3
"""Render a validated cascade bundle into a single self-contained, printable
HTML artifact: the root one-pager, then a "Strategy Gap Report" page built
from the bundle's open questions, then the team one-pagers — one A4
landscape page each.

Stdlib only at its core, mirroring validate_cascade.py — the skill runs
anywhere Python does, no packages, no network, no external assets. `--pdf`
produces a real PDF with the best engine this environment actually offers,
probed at run time: headless Chromium (faithful to the print CSS — always
wins when present), then WeasyPrint, then a built-in stdlib PDF writer
(simplified layout, zero dependencies) so no environment ships without a
PDF. The HTML additionally prints to PDF from any browser (Cmd/Ctrl+P) —
the full-design companion whenever the built-in tier rendered the PDF.
`--docx` writes the editable twin: the same design as a hand-authored OOXML
package (stdlib `zipfile`, one engine, no converters), which Google Drive
turns into a native Google Doc on convert-on-upload.

The layout replicates Alaigned's product PDF export as closely as the
bundle allows — same landscape A4 geometry, brand stripe, header band, 36mm
label column, side-by-side pillar cells with an accent top border,
enabler/value chip band, three-column footer — deliberately: the artifact
doubles as a preview of the product, and Alaigned workspaces re-brand it
with the customer's own logo and colors (whitelabel). Where the two diverge,
the artifact adds (page kicker, per-initiative goal sub-lines, the gap
page); it never restyles what the product already renders.

Usage:
    python3 scripts/render_cascade.py bundle.json [-o strategy.html]
        [--pdf [strategy.pdf]] [--docx [strategy.docx]]

Design notes:
  * @page margin is 0 and each page carries its own padding — browsers apply
    print-dialog margins inconsistently (and users set "None"), so the layout
    must own its margins to guarantee them.
  * Walks the one-pager content generically in template (JSON) order — any
    node carrying a textValue renders, so schema additions (narrative, timing)
    appear without code changes.
  * [PROPOSED — note] markers never render as per-item badges: displayed text
    is clean everywhere. The honesty is document-level — one draft banner on
    every one-pager page whenever the bundle carries composed content, plus
    the Gap Report's "Proposed content" section listing each marked statement
    with its note. Per-item badges saturate into visual noise (40 of them
    across three pages in one real run); the markers themselves stay in
    the bundle JSON as provenance and are never stripped there.
  * The Gap Report closes with a "Sources" block — the bundle's
    company.sourceDocuments, documents and fetched public sources alike,
    capped with a "+N more" line. Its chrome speaks of "sources", not
    "documents": a cascade may legitimately be built from public web sources.
  * Mandatory-but-null fields render as explicit "not found in your
    sources" gaps and are counted on the gap page, never as empty headings.
  * The CTA footer text is verbatim from templates/ — never reworded.
"""

from __future__ import annotations

import argparse
import base64
import html
import json
import os
import re
import shutil
import subprocess
import sys
import unicodedata
import urllib.parse
import uuid
import zipfile
import zlib
from pathlib import Path

PROPOSED_RE = re.compile(r"\s*\[PROPOSED(?:\s*[—-]\s*([^\]]*))?\]")
YEAR_RE = re.compile(r"\b(19|20)\d\d\b")
QUARTER_RE = re.compile(r"\b[QH][1-4]\b")

# Fallbacks only — the bundle's own label wins (statement labels are
# methodology-defined and client-translatable, like every other label in the
# artifact); this map covers bundles whose statements carry no label.
STATEMENT_HEADINGS = {
    "purpose": "Purpose",
    "vision": "Vision",
    "mission": "Mission",
    "teamAmbition": "Team Ambition",
}

# Plural-form selection per language. A counted phrase ships as a tuple of
# official forms and the language's rule picks one — the renderer selects a
# written form, it never inflects a word itself. Defined above STRINGS because
# each language's table names its own rule.


def _plural_en(count):
    return 0 if count == 1 else 1


def _plural_cs(count):
    # Czech counts in three forms: 1, the 2–4 "few", and the 5+ genitive
    # plural ("1 výrok", "3 výroky", "5 výroků").
    if count == 1:
        return 0
    return 1 if 2 <= count <= 4 else 2


def _plural_sk(count):
    # Slovak splits the same three ways as Czech — 1, the 2–4 "few", and the
    # 5+ genitive plural ("1 výrok", "3 výroky", "5 výrokov"). Same shape, own
    # rule: the two languages' forms differ, so they never share a table.
    if count == 1:
        return 0
    return 1 if 2 <= count <= 4 else 2


# The artifact chrome (draft banner, gap page, CTA, footer) ships as an
# official fixed string set per language, selected via --lang. The
# CTA-verbatim rule operates per language: models pick a language, they never
# translate or reword these strings themselves.
STRINGS = {
    "en": {
        # The BCP-47 tag the HTML artifact declares in <html lang>. Chrome and
        # body travel in one language, so the tag belongs with the strings —
        # screen readers and Drive's convert-on-upload both read it.
        "lang": "en",
        "banner": (
            "Draft proposal — parts of this cascade are composed, not confirmed by the "
            "sources. See the Strategy Gap Report."
        ),
        # --split sheets travel without the Gap Report page, so their banner
        # cannot point at it. A separate string, not a runtime slice: these
        # are official translations, not text to cut up.
        "banner_split": (
            "Draft proposal — parts of this cascade are composed, not confirmed by the sources."
        ),
        "proposed_heading": "Proposed content",
        "plural_rule": _plural_en,
        "proposed_count": "%s across %s",
        "proposed_count_stmt": ("%d proposed statement", "%d proposed statements"),
        "proposed_count_pages": ("%d page", "%d pages"),
        # "sources", not "documents": a cascade may be built from fetched
        # public sources as well as files, and the page must stay truthful
        # either way
        "gap_missing": "Not found in your sources",
        "gap_entry": "%s: %s — not stated in the sources",
        "generated": "Generated %s",
        "kicker": "One-pager · Level %s",
        "cascades_from": " · cascades from <strong>%s</strong>",
        "gap_kicker": "Strategy Gap Report",
        # counted headline — the item total is written into the phrase, so it
        # ships as forms like every other counted string
        "gap_title": (
            "The %d thing your strategy hasn&rsquo;t nailed down yet",
            "The %d things your strategy hasn&rsquo;t nailed down yet",
        ),
        "gap_subtitle": "%s — what a strategy consultant would flag first, extracted from your sources.",
        "gap_continued": "continued",
        "sources_heading": "Sources",
        # the Sources block's overflow line — counted, so it ships as forms
        "sources_more": ("+%d more", "+%d more"),
        # A ratio label ("3/7 …"), not a counted phrase — it has no singular
        # reading to select, so it stays one string.
        "stat_targets": "success measures carrying a target value",
        # The stat strip typesets its number separately, so these labels carry
        # no %d — the count only selects the form (plural_form()).
        "stat_questions": (
            "open question your sources could not answer",
            "open questions your sources could not answer",
        ),
        "stat_missing": (
            "core statement not found in the sources",
            "core statements not found in the sources",
        ),
        # pure copy: the growth host is appended by the renderer (CTA_HOST), so
        # the domain lives in exactly one constant
        "cta_title": "Keep this strategy alive",
        "cta_body": (
            "This page is a snapshot. Alaigned keeps the cascade current — changes propagate "
            "between levels, teams accept or push back explicitly, and evaluation status stays "
            "visible on every page."
        ),
        "cta_close": "Every question above becomes an owned, trackable decision the moment this cascade goes live.",
        "cta_whitelabel": (
            "In Alaigned, this document carries your logo and your brand colors — the preview "
            "above wears ours."
        ),
        "doc_title": "%s — Strategy One-Pager Cascade",
    },
    "cs": {
        "lang": "cs",
        "banner": (
            "Návrh — části této kaskády jsou odvozené a v podkladech nepotvrzené. "
            "Viz stránku Mezery ve strategii."
        ),
        "banner_split": (
            "Návrh — části této kaskády jsou odvozené a v podkladech nepotvrzené."
        ),
        "proposed_heading": "Odvozený obsah",
        "plural_rule": _plural_cs,
        # the pages phrase carries its own preposition ("na" + locative), so
        # the joiner is a plain space where English needs "across"
        "proposed_count": "%s %s",
        "proposed_count_stmt": (
            "%d odvozený výrok",
            "%d odvozené výroky",
            "%d odvozených výroků",
        ),
        # "na 1 stránce" / "na 3 stránkách" — few and many coincide here, so
        # this noun ships two forms and the 5+ index clamps onto the second
        "proposed_count_pages": ("na %d stránce", "na %d stránkách"),
        "gap_missing": "V podkladech nenalezeno",
        "gap_entry": "%s: %s — v podkladech neuvedeno",
        "generated": "Vygenerováno %s",
        "kicker": "One-pager · Úroveň %s",
        "cascades_from": " · kaskáduje z <strong>%s</strong>",
        "gap_kicker": "Mezery ve strategii",
        # "věc" is feminine: 1 takes the singular with its relative pronoun in
        # the accusative ("kterou"), 2–4 the nominative plural, 5+ the genitive
        "gap_title": (
            "%d věc, kterou vaše strategie ještě nemá dořešenou",
            "%d věci, které vaše strategie ještě nemá dořešené",
            "%d věcí, které vaše strategie ještě nemá dořešené",
        ),
        "gap_subtitle": "%s — co by strategický konzultant označil jako první, vytaženo z vašich podkladů.",
        "gap_continued": "pokračování",
        "sources_heading": "Zdroje",
        "sources_more": ("+%d další", "+%d další", "+%d dalších"),
        # a ratio label, not a counted phrase — the genitive stays fixed
        "stat_targets": "měřítek úspěchu nese konkrétní cílovou hodnotu",
        "stat_questions": (
            "otevřená otázka, na kterou podklady neodpovídají",
            "otevřené otázky, na které podklady neodpovídají",
            "otevřených otázek, na které podklady neodpovídají",
        ),
        "stat_missing": (
            "klíčový výrok v podkladech chybí",
            "klíčové výroky v podkladech chybí",
            "klíčových výroků v podkladech chybí",
        ),
        "cta_title": "Oživte svou strategii",
        "cta_body": (
            "Tato stránka je snímek okamžiku. Alaigned udržuje kaskádu živou — změny se "
            "propagují mezi úrovněmi, týmy je explicitně přijímají nebo rozporují a stav "
            "vyhodnocení je vidět na každé stránce."
        ),
        "cta_close": (
            "Každá otázka výše dostane svého vlastníka a stane se sledovatelným rozhodnutím ve "
            "chvíli, kdy kaskáda ožije."
        ),
        "cta_whitelabel": (
            "V Alaigned nese tento dokument vaše logo a vaše barvy — tento náhled nese naše."
        ),
        "doc_title": "%s — Kaskáda strategických one-pagerů",
    },
    "sk": {
        "lang": "sk",
        "banner": (
            "Návrh — časti tejto kaskády sú odvodené a v podkladoch nepotvrdené. "
            "Pozrite si stranu Medzery v stratégii."
        ),
        "banner_split": (
            "Návrh — časti tejto kaskády sú odvodené a v podkladoch nepotvrdené."
        ),
        "proposed_heading": "Odvodený obsah",
        "plural_rule": _plural_sk,
        # like Czech, the pages phrase carries its own preposition ("na" +
        # locative), so the joiner is a plain space
        "proposed_count": "%s %s",
        "proposed_count_stmt": (
            "%d odvodený výrok",
            "%d odvodené výroky",
            "%d odvodených výrokov",
        ),
        # "na 1 strane" / "na 3 stranách" — few and many coincide, so this noun
        # ships two forms and the 5+ index clamps onto the second
        "proposed_count_pages": ("na %d strane", "na %d stranách"),
        "gap_missing": "Nenájdené v podkladoch",
        "gap_entry": "%s: %s — v podkladoch neuvedené",
        "generated": "Vygenerované %s",
        "kicker": "One-pager · Úroveň %s",
        "cascades_from": " · kaskáduje z <strong>%s</strong>",
        "gap_kicker": "Medzery v stratégii",
        # "vec" is feminine, like the Czech row: 1 singular with the accusative
        # relative pronoun ("ktorú"), 2–4 nominative plural, 5+ genitive
        "gap_title": (
            "%d vec, ktorú vaša stratégia ešte nemá doriešenú",
            "%d veci, ktoré vaša stratégia ešte nemá doriešené",
            "%d vecí, ktoré vaša stratégia ešte nemá doriešené",
        ),
        "gap_subtitle": "%s — čo by strategický konzultant označil ako prvé, vytiahnuté z vašich podkladov.",
        "gap_continued": "pokračovanie",
        "sources_heading": "Zdroje",
        # "zdroj" is masculine inanimate: 1 takes the singular "ďalší", 2–4 the
        # nominative plural "ďalšie" (the animate "ďalší" would be wrong here),
        # 5+ the genitive "ďalších"
        "sources_more": ("+%d ďalší", "+%d ďalšie", "+%d ďalších"),
        # a ratio label, not a counted phrase — the genitive stays fixed
        "stat_targets": "meradiel úspechu nesie konkrétnu cieľovú hodnotu",
        "stat_questions": (
            "otvorená otázka, na ktorú podklady neodpovedajú",
            "otvorené otázky, na ktoré podklady neodpovedajú",
            "otvorených otázok, na ktoré podklady neodpovedajú",
        ),
        "stat_missing": (
            "kľúčový výrok v podkladoch chýba",
            "kľúčové výroky v podkladoch chýbajú",
            "kľúčových výrokov v podkladoch chýba",
        ),
        "cta_title": "Oživte svoju stratégiu",
        "cta_body": (
            "Táto strana je snímka okamihu. Alaigned udržiava kaskádu živú — zmeny sa "
            "propagujú medzi úrovňami, tímy ich výslovne prijímajú alebo voči nim namietajú "
            "a stav vyhodnotenia je vidieť na každej strane."
        ),
        "cta_close": (
            "Každá otázka vyššie dostane svojho vlastníka a stane sa sledovateľným "
            "rozhodnutím vo chvíli, keď kaskáda ožije."
        ),
        "cta_whitelabel": (
            "V Alaigned nesie tento dokument vaše logo a vaše farby — tento náhľad nesie naše."
        ),
        "doc_title": "%s — Kaskáda strategických one-pagerov",
    },
}
S = STRINGS["en"]
# The growth host, not the marketing site: every CTA in every engine
# resolves here. CTA_HOST is the display half — chrome strings carry copy only,
# so this constant is the single place the domain is written down.
CTA_URL = "https://try.alaigned.com"
CTA_HOST = CTA_URL.split("://", 1)[1]
# One UUID per strategy run, stamped into every CTA link. The bundle's
# attribution.ref wins when present (per-run identity: the JSON, every render
# and a later import carry the same ref); this generated one is the fallback
# for bundles without the block. The registration page stores it with the
# lead (nullable, non-unique), so N registrations sharing one ref = one
# artifact traveling — deliberately the only attribution this funnel has.
CTA_REF = str(uuid.uuid4())
CTA_HREF = "%s/?ref=%s" % (CTA_URL, CTA_REF)


def cta_label(title):
    """The CTA as displayed — copy plus the host it points at. Every engine
    composes it here instead of baking the domain into the strings table, so a
    host change is one edit in one constant."""
    return "%s → %s" % (title, CTA_HOST)


# Alaigned wordmark, embedded so the artifact stays self-contained. Whitelabel note: product exports swap this for
# the customer's uploaded logo.
LOGO_B64 = "PHN2ZyB3aWR0aD0iMTc4IiBoZWlnaHQ9IjU0IiB2aWV3Qm94PSIwIDAgMTc4IDU0IiBmaWxsPSJub25lIiB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciPgo8cGF0aCBkPSJNNDEuMDQzMSA4LjY0Nzg1QzM3LjM3MDMgNC45NzgwMyAyOS4zMjA5IDMuNjcwMTcgMjMuMDExNyAzLjY3MDE3QzE2LjcwMjUgMy42NzAxNyA4LjY1Mjk4IDQuOTc4MDMgNC45ODA3OSA4LjY0Nzg1Qy0xLjY2MDI2IDE1LjI4NDIgLTEuNjYwMjYgMzguMDQ5NiA0Ljk4MDc5IDQ0LjY4NjVDOC4yNjY3MSA0Ny45NzA3IDE1LjYzODMgNDkuNjEyNyAyMy4wMTE3IDQ5LjYxMjdDMzAuMzg1IDQ5LjYxMjcgMzcuNzU3OCA0Ny45NzAxIDQxLjA0MzEgNDQuNjg2NUM0Ny42MTQ0IDM4LjExODIgNDcuNjE0NCAxNS4yMTUgNDEuMDQzMSA4LjY0Nzg1Wk0xNS44NDUzIDE2LjgyNTFDMTUuODQ1MyAxNC40MjA1IDE3Ljc5NTYgMTIuNDcxNSAyMC4yMDE5IDEyLjQ3MTVIMjYuMDEwN0MyOC40MTY0IDEyLjQ3MTUgMzAuMzY3MyAxNC40MjA1IDMwLjM2NzMgMTYuODI1MVYxNy45MTM1SDE1Ljg0NTlWMTYuODI1MUgxNS44NDUzWk0xMi4yMTUxIDI2Ljk4MzRDMTIuMjE1MSAyNC41Nzg4IDE0LjE2NTQgMjIuNjI5NyAxNi41NzE3IDIyLjYyOTdIMjkuNjQwOUMzMi4wNDY2IDIyLjYyOTcgMzMuOTk3NSAyNC41Nzg4IDMzLjk5NzUgMjYuOTgzNFYyOC4wNzE4SDEyLjIxNTFWMjYuOTgzNFpNMzcuNjI3NyAzOC4yMzA2SDguNTg0MzZWMzcuMTQyMkM4LjU4NDM2IDM0LjczNzcgMTAuNTM0NiAzMi43ODg2IDEyLjk0MDkgMzIuNzg4NkgzMy4yNzExQzM1LjY3NjggMzIuNzg4NiAzNy42Mjc3IDM0LjczNzcgMzcuNjI3NyAzNy4xNDIyVjM4LjIzMDZaIiBmaWxsPSIjMTE4RTY0Ii8+CjxwYXRoIGQ9Ik03Mi44OTI3IDE3LjY5NTJDNzIuNTkyMiAxNi41NDM1IDcxLjk5NzIgMTUuNjEwNyA3MS4xMTM0IDE0LjkwMzJDNzAuMjMwMyAxNC4xOTU3IDY5LjIwMjggMTMuODQ1IDY4LjAzMTYgMTMuODQ1SDY1LjgwMTVDNjQuNjI5NyAxMy44NDUgNjMuNTg5OCAxNC4yMDE3IDYyLjY5NDIgMTQuOTI4MUM2MS44MDQ2IDE1LjYyOSA2MS4yMjE5IDE2LjU2MTggNjAuOTMzOSAxNy43MjY2TDU2LjU5MjcgMzUuNDg3MUM1Ni41ODAyIDM1LjUyNSA1Ni41NzM3IDM1LjU2MjIgNTYuNTczNyAzNS41OTM2QzU2LjU3MzcgMzUuNjkzNSA1Ni42MTc1IDM1Ljc4NzYgNTYuNjkyNiAzNS44ODE3QzU2Ljc2NzggMzUuOTc1NyA1Ni44ODA3IDM2LjAxOTUgNTcuMDE4NiAzNi4wMTk1SDU5LjUxMThDNTkuOTE4OCAzNi4wMTk1IDYwLjIwMSAzNS43OTQxIDYwLjM1NzcgMzUuMzQ5OUw2MS41NzkyIDMwLjM5ODJINzIuMjY2M0w3My40NzU0IDM1LjM0OTlDNzMuNjM4NiAzNS43OTQxIDczLjkyNjcgMzYuMDE5NSA3NC4zMzM3IDM2LjAxOTVINzYuODM5NEM3Ni45NzcyIDM2LjAxOTUgNzcuMDgzNyAzNS45NjMzIDc3LjE3NzcgMzUuODUwM0M3Ny4yNDA0IDM1Ljc4MTcgNzcuMjcxOCAzNS42OTQxIDc3LjI3MTggMzUuNTkzNkM3Ny4yNzE4IDM1LjU2MjIgNzcuMjY1MyAzNS41MjUgNzcuMjUyOSAzNS40ODcxTDcyLjg5MjcgMTcuNjk1MlpNNjIuNDYyNCAyNi43NjAzTDY0LjQ4NiAxOC41MjE2QzY0LjcxNzggMTcuODI2NSA2NS4xNTYyIDE3LjQ4MjMgNjUuODAxNSAxNy40ODIzSDY4LjAzMTZDNjguNjk1MyAxNy40ODIzIDY5LjE0MDEgMTcuODM4OSA2OS4zNjU1IDE4LjU2NTNMNzEuMzYzNiAyNi43NjAzSDYyLjQ2MThINjIuNDYyNFpNODEuODI1OSAxMy44NDU2SDc5LjA1N0M3OC45MzgxIDEzLjg0NTYgNzguODMxNiAxMy44ODkzIDc4Ljc0NDEgMTMuOTcxQzc4LjY2MjUgMTQuMDU4NSA3OC42MTg3IDE0LjE2NSA3OC42MTg3IDE0LjI4MzlWMzUuNTk0MkM3OC42MTg3IDM1LjcwNjYgNzguNjYyNSAzNS44MDcxIDc4Ljc0NDEgMzUuODg4MkM3OC44MzE2IDM1Ljk3NTcgNzguOTM4MSAzNi4wMTk1IDc5LjA1NyAzNi4wMTk1SDgxLjgyNTlDODEuOTUxMyAzNi4wMTk1IDgyLjA1MTMgMzUuOTc1NyA4Mi4xMzg5IDM1Ljg4ODJDODIuMjI2NCAzNS44MDY1IDgyLjI3MDIgMzUuNzA2NiA4Mi4yNzAyIDM1LjU5NDJWMTQuMjgzM0M4Mi4yNzAyIDE0LjE2NDQgODIuMjI2NCAxNC4wNTc5IDgyLjEzODkgMTMuOTcwNEM4Mi4wNTEzIDEzLjg4ODcgODEuOTUwOCAxMy44NDUgODEuODI1OSAxMy44NDVWMTMuODQ1NlpNOTYuMDA4MyAyMC4zNjgzSDg1LjQyNzdDODUuMzAyMyAyMC4zNjgzIDg1LjIwMjQgMjAuNDEyMSA4NS4xMjA3IDIwLjQ5OTZDODUuMDM5MSAyMC41ODcyIDg0Ljk5NTMgMjAuNjg3NyA4NC45OTUzIDIwLjgxMjVWMjMuNTc5N0M4NC45OTUzIDIzLjY5ODYgODUuMDM5MSAyMy44MDUxIDg1LjEyMDcgMjMuODkyNkM4NS4yMDI0IDIzLjk4MDIgODUuMzAyMyAyNC4wMjM5IDg1LjQyNzcgMjQuMDIzOUg5Ni4wMDgzQzk2LjAyNzMgMjQuMDIzOSA5Ni4wNTIxIDI0LjAyMzkgOTYuMDcxIDI0LjAzNjRDOTYuMDkgMjQuMDU1MyA5Ni4xMDI0IDI0LjA4MDEgOTYuMTAyNCAyNC4wOTkxVjI2LjM3NzZIODcuODA4Qzg2Ljc4MDYgMjYuMzc3NiA4NS45MDM5IDI2Ljc0MDggODUuMTgzNCAyNy40NzMxQzg0LjQ0NCAyOC4xOTk1IDg0LjA4MDggMjkuMDc1NiA4NC4wODA4IDMwLjEwMjVWMzIuMjg3NUM4NC4wODA4IDMzLjMyMDMgODQuNDQ0IDM0LjIwMjkgODUuMTgzNCAzNC45MzU4Qzg1LjkwMzkgMzUuNjU1NyA4Ni43ODA2IDM2LjAxODkgODcuODA4IDM2LjAxODlIOTYuMDA4M0M5Ny4wMzU4IDM2LjAxODkgOTcuOTEyNSAzNS42NTU3IDk4LjYzOTUgMzQuOTM1OEM5OS4zNzI0IDM0LjIwMzUgOTkuNzQyMSAzMy4zMjAzIDk5Ljc0MjEgMzIuMjg3NVYyNC4wOTkxQzk5Ljc0MjEgMjMuMDc4NyA5OS4zNzI0IDIyLjIwMiA5OC42Mzk1IDIxLjQ2OTdDOTcuOTEzMSAyMC43Mzc0IDk3LjAzNTggMjAuMzY3NyA5Ni4wMDgzIDIwLjM2NzdWMjAuMzY4M1pNOTYuMTAyNCAzMi4yODgxQzk2LjEwMjQgMzIuMzEzIDk2LjA5IDMyLjMzMTkgOTYuMDcxIDMyLjM1MDhDOTYuMDUyMSAzMi4zNjk4IDk2LjAyNzMgMzIuMzgyMiA5Ni4wMDgzIDMyLjM4MjJIODcuODA4Qzg3Ljc4OTEgMzIuMzgyMiA4Ny43NzA4IDMyLjM2OTggODcuNzUxOCAzMi4zNTA4Qzg3LjcyNyAzMi4zMzE5IDg3LjcyMDUgMzIuMzEzIDg3LjcyMDUgMzIuMjg4MVYzMC4xMDNDODcuNzIwNSAzMC4wODQxIDg3LjcyNjQgMzAuMDY1MiA4Ny43NTE4IDMwLjA0MDNDODcuNzcwOCAzMC4wMjE0IDg3Ljc4OTcgMzAuMDE1NSA4Ny44MDggMzAuMDE1NUg5Ni4xMDI0VjMyLjI4ODFaTTEwNC43NjQgMTMuODQ1NkgxMDEuOTgzQzEwMS44NyAxMy44NDU2IDEwMS43NyAxMy44ODkzIDEwMS42ODIgMTMuOTcxQzEwMS42MDEgMTQuMDU4NSAxMDEuNTU3IDE0LjE2NSAxMDEuNTU3IDE0LjI4MzlWMTcuMDUxQzEwMS41NTcgMTcuMTc2NCAxMDEuNjAxIDE3LjI4MjkgMTAxLjY4MiAxNy4zNjRDMTAxLjc3IDE3LjQ1MTUgMTAxLjg3IDE3LjQ5NTMgMTAxLjk4MyAxNy40OTUzSDEwNC43NjRDMTA0Ljg3NyAxNy40OTUzIDEwNC45NzcgMTcuNDUxNSAxMDUuMDY1IDE3LjM2NEMxMDUuMTUyIDE3LjI4MjMgMTA1LjE5NiAxNy4xNzY0IDEwNS4xOTYgMTcuMDUxVjE0LjI4MzlDMTA1LjE5NiAxNC4xNjUgMTA1LjE1MiAxNC4wNTg1IDEwNS4wNjUgMTMuOTcxQzEwNC45NzcgMTMuODg5MyAxMDQuODc2IDEzLjg0NTYgMTA0Ljc2NCAxMy44NDU2Wk0xMDQuNzY0IDIwLjM2ODNIMTAxLjk4M0MxMDEuODcgMjAuMzY4MyAxMDEuNzcgMjAuNDEyMSAxMDEuNjgyIDIwLjQ5OTZDMTAxLjYwMSAyMC41ODcyIDEwMS41NTcgMjAuNjg3NyAxMDEuNTU3IDIwLjgxMjVWMzUuNTkzQzEwMS41NTcgMzUuNzA1NCAxMDEuNjAxIDM1LjgwNTkgMTAxLjY4MiAzNS44ODdDMTAxLjc3IDM1Ljk3NDUgMTAxLjg3IDM2LjAxODMgMTAxLjk4MyAzNi4wMTgzSDEwNC43NjRDMTA0Ljg3NyAzNi4wMTgzIDEwNC45NzcgMzUuOTc0NSAxMDUuMDY1IDM1Ljg4N0MxMDUuMTUyIDM1LjgwNTMgMTA1LjE5NiAzNS43MDU0IDEwNS4xOTYgMzUuNTkzVjIwLjgxMjVDMTA1LjE5NiAyMC42ODcxIDEwNS4xNTIgMjAuNTg3MiAxMDUuMDY1IDIwLjQ5OTZDMTA0Ljk3NyAyMC40MTIxIDEwNC44NzYgMjAuMzY4MyAxMDQuNzY0IDIwLjM2ODNaTTExOC43NDggMjAuMzY4M0gxMTAuNTY3QzEwOS41MzkgMjAuMzY4MyAxMDguNjU2IDIwLjczMTUgMTA3LjkyMyAyMS40NjM4QzEwNy4xOTEgMjIuMTkwMiAxMDYuODIxIDIzLjA2NjMgMTA2LjgyMSAyNC4wOTk3VjMyLjI4ODFDMTA2LjgyMSAzMy4zMjA5IDEwNy4xOTEgMzQuMTk3NiAxMDcuOTIzIDM0LjkyOTlDMTA4LjY1NiAzNS42NTYzIDEwOS41MzkgMzYuMDE4OSAxMTAuNTY3IDM2LjAxODlIMTE4Ljg0MlYzOC44MTc0QzExOC44NDIgMzguODM2MyAxMTguODM2IDM4Ljg1NTIgMTE4LjgxOCAzOC44ODAxQzExOC44MDUgMzguODk5IDExOC43OCAzOC45MDQ5IDExOC43NDggMzguOTA0OUgxMDguMThDMTA4LjA2MSAzOC45MDQ5IDEwNy45NTUgMzguOTQ4NyAxMDcuODY3IDM5LjAzMDNDMTA3Ljc4NiAzOS4xMTIgMTA3Ljc0MiAzOS4yMTE5IDEwNy43NDIgMzkuMzM3M1Y0Mi4xMDQ1QzEwNy43NDIgNDIuMjIzNCAxMDcuNzg2IDQyLjMyOTkgMTA3Ljg2NyA0Mi40MTc0QzEwNy45NTUgNDIuNTA1IDEwOC4wNjEgNDIuNTQ4NyAxMDguMTggNDIuNTQ4N0gxMTguNzQ4QzExOS43ODIgNDIuNTQ4NyAxMjAuNjY1IDQyLjE3OTYgMTIxLjM5OCA0MS40NTMyQzEyMi4xMzEgNDAuNzI2OCAxMjIuNTAxIDM5Ljg0NDMgMTIyLjUwMSAzOC44MTc0VjI0LjA5OTdDMTIyLjUwMSAyMy4wNjY4IDEyMi4xMzEgMjIuMTkwMiAxMjEuMzk4IDIxLjQ2MzhDMTIwLjY2NSAyMC43MzE1IDExOS43ODIgMjAuMzY4MyAxMTguNzQ4IDIwLjM2ODNaTTExOC44NDIgMzIuMzgyMkgxMTAuNTY3QzExMC41MzYgMzIuMzgyMiAxMTAuNTE3IDMyLjM2OTggMTEwLjQ5OCAzMi4zNTA4QzExMC40ODUgMzIuMzMxOSAxMTAuNDc5IDMyLjMxMyAxMTAuNDc5IDMyLjI4ODFWMjQuMDk5N0MxMTAuNDc5IDI0LjA4MDcgMTEwLjQ4NSAyNC4wNTU5IDExMC40OTggMjQuMDM2OUMxMTAuNTE3IDI0LjAxOCAxMTAuNTM2IDI0LjAwNTYgMTEwLjU2NyAyNC4wMDU2SDExOC43NDhDMTE4Ljc4IDI0LjAwNTYgMTE4LjgwNSAyNC4wMTggMTE4LjgxOCAyNC4wMzY5QzExOC44MzYgMjQuMDU1OSAxMTguODQyIDI0LjA4MDcgMTE4Ljg0MiAyNC4wOTk3VjMyLjM4MjJaTTEzNi4zODkgMjAuMzY4M0gxMjguMTg4QzEyNy4xNjEgMjAuMzY4MyAxMjYuMjc4IDIwLjczNzQgMTI1LjU0NSAyMS40NzAzQzEyNC44MTkgMjIuMTkwMiAxMjQuNDYxIDIzLjA2NjggMTI0LjQ2MSAyNC4wOTk3VjM1LjU5MzZDMTI0LjQ2MSAzNS43MTI1IDEyNC40OTkgMzUuODE5IDEyNC41OCAzNS45MDA2QzEyNC42NjIgMzUuOTgyMiAxMjQuNzYyIDM2LjAxOTUgMTI0Ljg4NyAzNi4wMTk1SDEyNy42NTZDMTI3Ljc3NSAzNi4wMTk1IDEyNy44ODEgMzUuOTgyMiAxMjcuOTY5IDM1LjkwMDZDMTI4LjA1NyAzNS44MTkgMTI4LjEgMzUuNzEyNSAxMjguMSAzNS41OTM2VjI0LjA5OTdDMTI4LjEgMjQuMDgwNyAxMjguMTA3IDI0LjA1NTkgMTI4LjEzMiAyNC4wMzY5QzEyOC4xMzggMjQuMDI0NSAxMjguMTU3IDI0LjAyNDUgMTI4LjE4OCAyNC4wMjQ1SDEzNi4zODhDMTM2LjQwNyAyNC4wMjQ1IDEzNi40MjYgMjQuMDI0NSAxMzYuNDUxIDI0LjAzNjlDMTM2LjQ1NyAyNC4wNTU5IDEzNi40NjMgMjQuMDgwNyAxMzYuNDYzIDI0LjA5OTdWMzUuNTkzNkMxMzYuNDYzIDM1LjcxMjUgMTM2LjUwNyAzNS44MTkgMTM2LjU5NSAzNS45MDA2QzEzNi42ODIgMzUuOTgyMiAxMzYuNzgzIDM2LjAxOTUgMTM2LjkwOCAzNi4wMTk1SDEzOS42NzdDMTM5Ljc5NSAzNi4wMTk1IDEzOS45MDIgMzUuOTgyMiAxMzkuOTg5IDM1LjkwMDZDMTQwLjA3NyAzNS44MTkgMTQwLjEyMSAzNS43MTI1IDE0MC4xMjEgMzUuNTkzNlYyNC4wOTk3QzE0MC4xMjEgMjMuMDc5MyAxMzkuNzUxIDIyLjIwMjYgMTM5LjAxOCAyMS40NzAzQzEzOC4yODUgMjAuNzM4IDEzNy40MDggMjAuMzY4MyAxMzYuMzg3IDIwLjM2ODNIMTM2LjM4OVpNMTU0LjE2MSAyMC4zNjgzSDE0NS45NjFDMTQ0LjkzMyAyMC4zNjgzIDE0NC4wNTcgMjAuNzM3NCAxNDMuMzMgMjEuNDcwM0MxNDIuNTk3IDIyLjIwMjYgMTQyLjIzNCAyMy4wNzkzIDE0Mi4yMzQgMjQuMDk5N1YzMi4yODgxQzE0Mi4yMzQgMzMuMzIwOSAxNDIuNTk3IDM0LjIwMzUgMTQzLjMzIDM0LjkzNjRDMTQ0LjA1NiAzNS42NTYzIDE0NC45MzMgMzYuMDE5NSAxNDUuOTYxIDM2LjAxOTVIMTU2LjU0OEMxNTYuNjY3IDM2LjAxOTUgMTU2Ljc3MyAzNS45ODIyIDE1Ni44NjEgMzUuOTAwNkMxNTYuOTQ5IDM1LjgxOSAxNTYuOTkzIDM1LjcxMjUgMTU2Ljk5MyAzNS41OTM2VjMyLjgyNjRDMTU2Ljk5MyAzMi43MDEgMTU2Ljk0OSAzMi42MDEgMTU2Ljg2MSAzMi41MTM1QzE1Ni43NzQgMzIuNDI2IDE1Ni42NjcgMzIuMzgyMiAxNTYuNTQ4IDMyLjM4MjJIMTQ1Ljk2MUMxNDUuOTQyIDMyLjM4MjIgMTQ1LjkyMyAzMi4zNjk4IDE0NS45MDUgMzIuMzUwOEMxNDUuODkyIDMyLjMzMTkgMTQ1Ljg4NiAzMi4zMTMgMTQ1Ljg4NiAzMi4yODgxVjMwLjAxNTVIMTU0LjE2MUMxNTUuMTg5IDMwLjAxNTUgMTU2LjA3MiAyOS42NTIzIDE1Ni44MDUgMjguOTI2NUMxNTcuNTMxIDI4LjE5NDIgMTU3Ljg5NSAyNy4zMTE2IDE1Ny44OTUgMjYuMjg0N1YyNC4xMDAyQzE1Ny44OTUgMjMuMDc5OSAxNTcuNTMyIDIyLjIwMzIgMTU2LjgwNSAyMS40NzA5QzE1Ni4wNzIgMjAuNzM4NiAxNTUuMTg5IDIwLjM2ODkgMTU0LjE2MSAyMC4zNjg5VjIwLjM2ODNaTTE1NC4yNTUgMjYuMjg0N0MxNTQuMjU1IDI2LjMxNjEgMTU0LjI0MyAyNi4zMzUgMTU0LjIyNCAyNi4zNDc0QzE1NC4xOTkgMjYuMzY2NCAxNTQuMTggMjYuMzc4OCAxNTQuMTYxIDI2LjM3ODhIMTQ1Ljg4NlYyNC4xMDAyQzE0NS44ODYgMjQuMDgxMyAxNDUuODkyIDI0LjA1NjUgMTQ1LjkwNSAyNC4wMzc1QzE0NS45MjQgMjQuMDI1MSAxNDUuOTQzIDI0LjAyNTEgMTQ1Ljk2MSAyNC4wMjUxSDE1NC4xNjFDMTU0LjE4IDI0LjAyNTEgMTU0LjE5OSAyNC4wMjUxIDE1NC4yMjQgMjQuMDM3NUMxNTQuMjQzIDI0LjA1NjUgMTU0LjI1NSAyNC4wODEzIDE1NC4yNTUgMjQuMTAwMlYyNi4yODQ3Wk0xNzUuMjI4IDEzLjk3MDRDMTc1LjE0MSAxMy44ODg3IDE3NS4wMzQgMTMuODQ1IDE3NC45MTUgMTMuODQ1SDE3Mi4xNDZDMTcyLjAyMSAxMy44NDUgMTcxLjkyMSAxMy44ODg3IDE3MS44MzMgMTMuOTcwNEMxNzEuNzQ1IDE0LjA1NzkgMTcxLjcwMiAxNC4xNjQ0IDE3MS43MDIgMTQuMjgzM1YyMC4zNjgzSDE2My40MjZDMTYyLjM5OSAyMC4zNjgzIDE2MS41MjIgMjAuNzMxNSAxNjAuNzg5IDIxLjQ2MzhDMTYwLjA2MyAyMi4xOTAyIDE1OS42OTkgMjMuMDY2MyAxNTkuNjk5IDI0LjA5OTdWMzIuMjg4MUMxNTkuNjk5IDMzLjMyMDkgMTYwLjA2MiAzNC4xOTc2IDE2MC43ODkgMzQuOTI5OUMxNjEuNTIyIDM1LjY1NjMgMTYyLjM5OSAzNi4wMTg5IDE2My40MjYgMzYuMDE4OUgxNzEuNjA4QzE3Mi42NDEgMzYuMDE4OSAxNzMuNTI1IDM1LjY1NTcgMTc0LjI1OCAzNC45Mjk5QzE3NC45OTEgMzQuMTk3NiAxNzUuMzYgMzMuMzIwOSAxNzUuMzYgMzIuMjg4MVYxNC4yODMzQzE3NS4zNiAxNC4xNjQ0IDE3NS4zMTYgMTQuMDU3OSAxNzUuMjI5IDEzLjk3MDRIMTc1LjIyOFpNMTcxLjcwMiAzMi4yODgxQzE3MS43MDIgMzIuMzEzIDE3MS42OTUgMzIuMzMxOSAxNzEuNjc3IDMyLjM1MDhDMTcxLjY2NCAzMi4zNjk4IDE3MS42MzkgMzIuMzgyMiAxNzEuNjA4IDMyLjM4MjJIMTYzLjQyNkMxNjMuMzk1IDMyLjM4MjIgMTYzLjM3NiAzMi4zNjk4IDE2My4zNTcgMzIuMzUwOEMxNjMuMzQ1IDMyLjMzMTkgMTYzLjMzOCAzMi4zMTMgMTYzLjMzOCAzMi4yODgxVjI0LjA5OTdDMTYzLjMzOCAyNC4wODA3IDE2My4zNDUgMjQuMDU1OSAxNjMuMzU3IDI0LjAzNjlDMTYzLjM3NiAyNC4wMTggMTYzLjM5NSAyNC4wMDU2IDE2My40MjYgMjQuMDA1NkgxNzEuNzAyVjMyLjI4ODFaIiBmaWxsPSJibGFjayIvPgo8L3N2Zz4K"


# --- content helpers ---------------------------------------------------------


def esc(text):
    return html.escape(text, quote=True)


def trim_label(label):
    """Schema labels can carry a parenthetical ("Goal (picture of success)")
    — too long for narrow label columns; keep the term."""
    return re.sub(r"\s*\(.*\)$", "", label)


def split_proposed(text):
    """Return (clean_text, [notes]) with [PROPOSED …] markers removed."""
    notes = [m.group(1).strip() if m.group(1) else "" for m in PROPOSED_RE.finditer(text)]
    return PROPOSED_RE.sub("", text).strip(), notes


def carries_target(text):
    clean, _ = split_proposed(text)
    clean = YEAR_RE.sub("", clean)
    clean = QUARTER_RE.sub("", clean)
    return bool(re.search(r"\d", clean))


def plural_form(key, count):
    """The official form this count selects — selection only, no number.

    Two shapes of counted string exist. Phrases that print the number inside
    themselves ("3 pages") carry a %d and go through plural(); labels that sit
    beside a separately typeset number — the Gap Report's stat strip, where the
    figure is its own 24pt line — carry no %d and take the form as it stands.
    Both pick the form the same way, which is what this holds."""
    forms = S[key]
    return forms[min(S["plural_rule"](count), len(forms) - 1)]


def plural(key, count):
    """One counted phrase in the artifact's language, e.g. "3 pages".

    The forms are official strings; this only picks between them. A noun whose
    form list is shorter than the rule's index clamps onto the last form —
    Czech and Slovak nouns whose few and many forms coincide ship two, not
    three."""
    return plural_form(key, count) % count


def proposed_count_line(entries):
    """The Proposed-content section's one-line summary — both output paths
    render this exact text, correctly pluralized. Both counts are derived from
    the entries here, so the two surfaces cannot count differently.

    Pages are counted by the entry's page key (the one-pager's `ref`, its
    index when a bundle omits one) — two one-pagers may legitimately share a
    title, only the ref is unique."""
    pages = len({page_key for page_key, _title, _label, _text, _note in entries})
    return S["proposed_count"] % (
        plural("proposed_count_stmt", len(entries)),
        plural("proposed_count_pages", pages),
    )


def truncate(text, limit=120):
    """One scannable line for the Gap Report's proposed list — the full text
    is on the page it came from, so the entry only has to identify it. The
    marker's note is capped the same way, for the same reason."""
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def proposed_entries(bundle):
    """Every [PROPOSED]-marked value in the bundle, in template order, as
    (page_key, page_title, label, clean_text, note) — one entry per marked
    element.

    ONE scan feeds both surfaces that carry the honesty now: the
    document-level draft banner (shown when this list is non-empty) and the
    Gap Report's Proposed-content section. Deriving both from the same walk
    is what stops them disagreeing — a banner promising a section that has
    nothing in it would be worse than no banner at all.

    The page key rides along so the section can group its entries under one
    subheading per one-pager (the title is written once, not once per line)
    and count pages by identity rather than by title."""
    entries = []
    for index, one_pager in enumerate(bundle.get("onePagers") or []):
        _walk_proposed(
            one_pager.get("content") or {},
            one_pager.get("ref") or index,
            one_pager.get("title", ""),
            "",
            entries,
        )
    return entries


def _walk_proposed(node, page_key, page_title, entity_label, entries):
    if isinstance(node, list):
        # every item of a collection is an entity (a pillar, an initiative, an
        # enabler, a value) and names the fields below it until the next one
        for item in node:
            own = item.get("label") if isinstance(item, dict) else None
            _walk_proposed(item, page_key, page_title, own or entity_label, entries)
        return
    if not isinstance(node, dict):
        return
    for key, value in node.items():
        if is_text_node(value) and isinstance(value.get("textValue"), str):
            clean, notes = split_proposed(value["textValue"])
            if notes:
                note = " ".join(n for n in notes if n)
                entries.append(
                    (page_key, page_title, _entry_label(entity_label, key, value), clean, note)
                )
        _walk_proposed(value, page_key, page_title, entity_label, entries)


# Field labels that describe the slot but not the thing in it: on their own,
# "Name" and "Text" identify nothing a reader can act on.
GENERIC_FIELDS = ("name", "content", "narrative")


def _entry_label(entity_label, key, node):
    """The entry's element label, prefixed with the enclosing entity's own
    label where the field label alone is generic — "Pillar name", "Enabler
    text", while "Purpose" or "Goal" already name themselves."""
    element = trim_label(node.get("label") or "") or key
    if key in GENERIC_FIELDS and entity_label:
        return "%s %s" % (entity_label, element.lower())
    return element


def proposed_groups(entries):
    """The entries as [(page_title, [entry])] — one group per one-pager. The
    walk emits entries in page order, so the runs are already contiguous;
    grouping keys on the page key, never the title."""
    groups = []
    for entry in entries:
        page_key, page_title = entry[0], entry[1]
        if not groups or groups[-1][0] != page_key:
            groups.append((page_key, page_title, []))
        groups[-1][2].append(entry)
    return [(title, group) for _key, title, group in groups]


def draft_banner_text(entries, standalone):
    """The one honesty line a one-pager page carries, or "" when nothing in
    the bundle is composed (`entries` is the proposed_entries scan). It is
    bundle-scoped on purpose — the pages travel together and a reader cannot
    tell which sheet the composed statement sat on, so the wording speaks of
    the cascade, not the page."""
    if not entries:
        return ""
    return S["banner_split"] if standalone else S["banner"]


def value_html(node, gaps, page_title, css="value"):
    """Render one textValue node with its [PROPOSED …] marker stripped, or an
    explicit gap. No per-item badge: the page's draft banner and the Gap
    Report's Proposed-content section carry that."""
    text = node.get("textValue")
    label = node.get("label", "")

    if text is None:
        if node.get("mandatory"):
            gaps.append(S["gap_entry"] % (page_title, label))
            return '<p class="gap">%s</p>' % S["gap_missing"]
        return ""

    clean, _notes = split_proposed(text)
    return '<p class="%s">%s</p>' % (css, esc(clean))


def is_text_node(node):
    return isinstance(node, dict) and "textValue" in node


def is_collection(node):
    return isinstance(node, dict) and isinstance(node.get("content"), list)


def gap_stats(bundle):
    """The Gap Report's headline pair — (goals carrying a target, goals in
    total) — walked once here for all three surfaces that print it (HTML, the
    built-in PDF, the DOCX). Three copies of this walk could disagree about
    what a measurable goal is; one cannot."""
    goals = []

    def walk(node):
        if isinstance(node, dict):
            goal = node.get("goal")
            if is_text_node(goal) and isinstance(goal.get("textValue"), str):
                goals.append(goal["textValue"])
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    for one_pager in bundle["onePagers"]:
        walk(one_pager["content"])

    return sum(1 for goal in goals if carries_target(goal)), len(goals)


# --- page sections -----------------------------------------------------------


def core_rows_html(content, gaps, page_title):
    """The strategy-context strip: uppercase accent labels in a fixed column,
    values beside — companyAmbition is excluded (it lives in the header)."""
    rows = []
    for key, node in content.items():
        if key in ("metadata", "companyAmbition") or not is_text_node(node):
            continue
        body = value_html(node, gaps, page_title, css="core-value")
        if not body:
            # a null optional statement renders as nothing, never a hollow row
            continue
        label = node.get("label") or STATEMENT_HEADINGS.get(key, key)
        heading = trim_label(label)
        rows.append(
            '<div class="core-label">%s</div><div class="core-cell">%s</div>'
            % (esc(heading.upper()), body)
        )
    if not rows:
        return ""
    return '<section class="core">%s</section>' % "".join(rows)


def est_lines_n(nchars, chars_per_line):
    return max(1, -(-nchars // chars_per_line))


def entity_text_len(entity):
    """Total visible characters of an entity's own labeled rows — the basis
    for its height estimate. A null value may still render (the mandatory-
    field gap line), so it counts as a short line rather than zero."""
    total = 0
    for key, node in entity.items():
        if key in ("label", "metadata", "name"):
            continue
        if is_text_node(node):
            value_chars = len(node.get("textValue") or "") or NULL_VALUE_CHARS
            total += len(node.get("label") or key) + value_chars
        elif is_collection(node):
            for item in node["content"]:
                name = item.get("name") or {}
                total += len(name.get("textValue") or "") + entity_text_len(item)
    return total


def entity_body_parts(entity, gaps, page_title, chars_per_line):
    """The entity's body as (kind, group, html, mm) blocks in template order —
    the unit the pillar paginator cuts at. Built exactly once per render so
    the gap collection sees each missing value once."""
    parts = []
    for index, (key, node) in enumerate(entity.items()):
        if key in ("label", "metadata", "name"):
            continue
        if is_text_node(node):
            body = value_html(node, gaps, page_title)
            if body:
                label = trim_label(node.get("label", key))
                nchars = len(label) + len(node.get("textValue") or "")
                parts.append(
                    (
                        "row",
                        index,
                        '<div class="row"><span class="row-label">%s</span><span class="row-value">%s</span></div>'
                        % (esc(label.upper()), body),
                        1 + PILLAR_LINE_MM * est_lines_n(nchars, chars_per_line),
                    )
                )
        elif is_collection(node):
            for item in node["content"]:
                name = item.get("name")
                title = (
                    esc(split_proposed(name["textValue"])[0])
                    if is_text_node(name) and name.get("textValue")
                    else ""
                )
                nchars = len(title) + entity_text_len(item)
                parts.append(
                    (
                        "init",
                        index,
                        '<li><span class="init-name">%s</span>%s</li>'
                        % (title, entity_body_html(item, gaps, page_title)),
                        1 + PILLAR_LINE_MM * est_lines_n(nchars, chars_per_line),
                    )
                )
    return parts


def assemble_parts(parts):
    """Blocks back into markup: consecutive initiative items of one collection
    share a single <ul>, exactly as the unpaginated body renders."""
    html, run, run_group = [], [], None
    for kind, group, block, _mm in parts:
        if kind == "init":
            if run and run_group != group:
                html.append('<ul class="initiatives">%s</ul>' % "".join(run))
                run = []
            run_group = group
            run.append(block)
        else:
            if run:
                html.append('<ul class="initiatives">%s</ul>' % "".join(run))
                run = []
            html.append(block)
    if run:
        html.append('<ul class="initiatives">%s</ul>' % "".join(run))
    return "".join(html)


def entity_body_html(entity, gaps, page_title):
    """Everything inside a pillar/initiative except its name: labeled rows +
    nested collections, in template order."""
    return assemble_parts(entity_body_parts(entity, gaps, page_title, 999))


# Column count mirroring the product template's grid_columns/1: up to six
# pillars sit on one row; beyond that they wrap into balanced rows
# (8 -> 4+4, 11 -> 6+5) instead of a lopsided 6 + remainder.
MAX_COLUMNS = 6


def grid_columns(count):
    if count <= MAX_COLUMNS:
        return max(count, 1)
    rows = -(-count // MAX_COLUMNS)
    return -(-count // rows)


# A pillar column's width shrinks with the column count, so its line budget
# does too; heights are conservative mm estimates in the same spirit as the
# gap-report budgets. The paginator engages only when a page's estimate
# clearly exceeds one sheet — ordinary bundles render exactly as before.
PILLAR_LINE_MM = 4.4
# Estimates deliberately run ~15-20% above real heights (they must err tall),
# so the engage threshold lives in estimate-space: est 220 ≈ a real ~185mm
# page, right at the sheet boundary. Ordinary pages stay on the single-sheet
# path and render exactly as before.
OP_ENGAGE_MM = 220
OP_HEADER_MM = 34
OP_BANNER_MM = 10  # the draft banner box (6.5mm) plus its margin, when shown
OP_CHIP_ROW_MM = 9
NULL_VALUE_CHARS = 30  # a rendered "Not found in your sources" gap line


def pillar_chars_per_line(cols):
    # 234mm grid minus gaps, cell padding, list indent and bullet markers;
    # ~1.7mm per character at the 9pt body size
    cell_mm = (234 - 3 * (cols - 1)) / cols - 13
    return max(12, int(cell_mm / 1.7))


def pillar_name_chars(cols):
    # the name bar is bold 11pt — noticeably fewer characters per line
    cell_mm = (234 - 3 * (cols - 1)) / cols - 5
    return max(10, int(cell_mm / 2.3))


def pillar_cells(pillars, gaps, page_title):
    """Each pillar as (name_bar_html, [body blocks], name_bar_mm)."""
    cols = grid_columns(len(pillars["content"]))
    chars = pillar_chars_per_line(cols)
    cells = []
    for pillar in pillars["content"]:
        name = pillar.get("name", {})
        title = esc(split_proposed(name.get("textValue") or "")[0])
        parts = entity_body_parts(pillar, gaps, page_title, chars)
        name_mm = 4 + 5.5 * est_lines_n(max(len(title), 1), pillar_name_chars(cols))
        cells.append((title, parts, name_mm))
    return cols, cells


def cell_est_mm(cell):
    _title, parts, name_mm = cell
    return name_mm + sum(p[3] for p in parts)


def pillar_band_html(pillars, cols, cells_html):
    return (
        '<section class="pillars"><div class="band-label">%s</div>'
        '<div class="pillar-cells cols-%d">%s</div></section>'
        % (esc(pillars.get("label", "Pillars").upper()), cols, "".join(cells_html))
    )


def pillar_cell_html(title, parts):
    return (
        '<article class="pillar"><div class="pillar-name">%s</div><div class="pillar-body">%s</div></article>'
        % (title, assemble_parts(parts))
    )


def band_est_mm(cols, cells):
    """A grid row is as tall as its tallest cell; rows of `cols` cells stack."""
    total = 8
    for row_start in range(0, len(cells), cols):
        total += max(cell_est_mm(c) for c in cells[row_start : row_start + cols])
    return total


def pillar_band_chunks(pillars, cols, cells, budgets):
    """The pillar band cut into whole sheets, one grid row-group at a time —
    a sheet never stacks two row groups, so its height is one group's tallest
    column, not their sum. Within a group all columns advance in parallel
    against the same mm budget (grid geometry identical on every sheet);
    spent columns keep an empty cell to hold their grid track, and each
    column reserves its own repeated name bar's estimated height. Yields one
    band-HTML per sheet; `budgets` yields each sheet's body budget."""
    label = pillars.get("label", "Pillars")
    first = True
    for row_start in range(0, len(cells), cols):
        group = [
            (title, list(parts), name_mm)
            for title, parts, name_mm in cells[row_start : row_start + cols]
        ]
        while any(parts for _title, parts, _nm in group):
            budget = next(budgets)
            sheet_cells = []
            for title, parts, name_mm in group:
                if not parts:
                    sheet_cells.append('<article class="pillar"></article>')
                    continue
                used = name_mm
                take = []
                while parts and (not take or used + parts[0][3] <= budget):
                    used += parts[0][3]
                    take.append(parts.pop(0))
                sheet_cells.append(pillar_cell_html(title, take))
            band = dict(pillars)
            if not first:
                band["label"] = "%s — %s" % (label, S["gap_continued"])
            yield pillar_band_html(band, cols, sheet_cells)
            first = False


def chip_band_html(collections, gaps, page_title):
    """Enablers / values as chip rows — chips only, like the product export
    (narratives stay in the bundle and the markdown pages; the print band
    keeps a single clear owner per row)."""
    rows = []
    for collection in collections:
        chips = []
        for item in collection["content"]:
            primary = item.get("content")
            if is_text_node(primary) and isinstance(primary.get("textValue"), str):
                clean, _marks = split_proposed(primary["textValue"])
                chips.append('<span class="chip">%s</span>' % esc(clean))
        if chips:
            rows.append(
                '<div class="chip-row"><div class="band-label">%s</div><div class="chips">%s</div></div>'
                % (esc(collection.get("label", "").upper()), "".join(chips))
            )
    if not rows:
        return ""
    return '<section class="chip-band">%s</section>' % "".join(rows)


def footer_html(generated_at):
    # One slim footnote line, not a banner: the CTA as a brand pill on the left
    # and the generation date, quiet, on the right. It stays on every page — the
    # link carries the attribution ref, and on --split sheets it is the only CTA
    # at all, which is why it earns button energy rather than a grey footnote.
    return (
        '<footer><span class="footer-cta"><a href="%s">%s</a></span>'
        '<span class="footer-date">%s</span></footer>'
        % (CTA_HREF, esc(cta_label(S["cta_title"])), S["generated"] % esc(generated_at))
    )


OP_SHEET_TEMPLATE = """
<section class="page">
  <div class="stripe"></div>
  <div class="page-body">
    <header>
      <div class="header-text">
        <div class="kicker">%s%s</div>
        <h1>%s</h1>
        %s
      </div>
      <img class="logo" src="data:image/svg+xml;base64,%s" alt="Alaigned" />
    </header>
    %s
    %s
  </div>
  %s
</section>"""


def core_est_mm(content):
    total = 8
    for key, node in content.items():
        if key in ("metadata", "companyAmbition") or not is_text_node(node):
            continue
        value_chars = len(node.get("textValue") or "") or NULL_VALUE_CHARS
        nchars = len(node.get("label") or key) + value_chars
        total += 2 + PILLAR_LINE_MM * est_lines_n(nchars, 100)
    return total


def one_pager_html(one_pager, by_ref, bundle, gaps, banner_text):
    content = one_pager["content"]
    title = one_pager.get("title", "")
    level = one_pager.get("level")
    generated_at = bundle.get("generator", {}).get("generatedAt", "")
    parent = by_ref.get(one_pager.get("parentRef"))
    cascade_line = S["cascades_from"] % esc(parent["title"]) if parent else ""

    ambition = content.get("companyAmbition")
    ambition_html = (
        value_html(ambition, gaps, title, css="ambition") if is_text_node(ambition) else ""
    )
    ambition_text = ambition.get("textValue") or "" if is_text_node(ambition) else ""

    collections = [v for v in content.values() if is_collection(v)]
    pillar_like = [c for c in collections if c["content"] and "name" in c["content"][0]]
    chip_like = [c for c in collections if c["content"] and "name" not in c["content"][0]]

    # Build every fragment exactly once (the gap collection records each
    # missing value as a side effect), then decide the page shape from the
    # height estimate: one sheet as always, or parallel-paginated pillars.
    core = core_rows_html(content, gaps, title)
    bands = [(c,) + pillar_cells(c, gaps, title) for c in pillar_like]
    chips = chip_band_html(chip_like, gaps, title)
    footer = footer_html(generated_at)
    banner = '<p class="draft-banner">%s</p>' % esc(banner_text) if banner_text else ""

    header_mm = (
        OP_HEADER_MM
        + 9 * (est_lines_n(len(title), 38) - 1)
        + PILLAR_LINE_MM * est_lines_n(len(ambition_text), 95)
        + (OP_BANNER_MM if banner_text else 0)
    )
    core_mm = core_est_mm(content)
    est_total = (
        header_mm
        + core_mm
        + sum(band_est_mm(cols, cells) for _c, cols, cells in bands)
        + (chips.count("chip-row") * OP_CHIP_ROW_MM + 4 if chips else 0)
    )

    def sheet(body, continued):
        heading = esc(title) + (" — %s" % S["gap_continued"] if continued else "")
        # the banner repeats on continuation sheets with the header: sheets
        # print and travel separately, so each one states its own honesty
        return OP_SHEET_TEMPLATE % (
            S["kicker"] % level,
            cascade_line,
            heading,
            ambition_html,
            LOGO_B64,
            banner,
            body,
            footer,
        )

    band_html = lambda c, cols, cells: pillar_band_html(  # noqa: E731
        c, cols, [pillar_cell_html(t, p) for t, p, _mm in cells]
    )

    if est_total <= OP_ENGAGE_MM:
        body = "%s\n    %s\n    %s" % (
            core,
            "".join(band_html(c, cols, cells) for c, cols, cells in bands),
            chips,
        )
        return sheet(body, False)

    def budget_gen():
        # 185, not the sheet's 190: a few mm of slack per sheet so a small
        # estimation miss spills nothing (the footer would go first)
        yield max(50, 185 - header_mm - core_mm)
        while True:
            yield max(70, 185 - header_mm)

    budgets = budget_gen()
    chunks = [
        chunk
        for c, cols, cells in bands
        for chunk in pillar_band_chunks(c, cols, cells, budgets)
    ]
    if not chunks:
        return sheet(core + chips, False)
    sheets = [sheet(core + chunks[0], False)]
    sheets += [sheet(chunk, True) for chunk in chunks[1:]]
    if chips:
        sheets.append(sheet(chips, True))
    return "".join(sheets)


# The Gap Report is the one page designed to grow with the input, so the
# renderer chunks its list into whole sheets itself instead of letting the
# browser fragment an overlong page: a fragment starts at the sheet edge with
# no vertical padding, because the padding lives on the .page-body box and
# @page margin must stay 0 for the full-bleed stripe. Budgets are conservative
# mm estimates and must err TALL: when one misses, the break-inside rules only
# keep the split between items — the continuation sheet is back to losing its
# vertical padding.
#
# The constants below are measured in the browser against the rendered page,
# not guessed: a sheet packed to the estimated brim must still print as ONE
# sheet. Until the Proposed-content section arrived no sheet ever filled its
# budget, which hid ~13mm of accumulated optimism here and the first full
# sheet promptly spilled onto a second page. What the measurements say: the
# body is 183mm, budgeted 176 once the list's own 6mm bottom margin is
# reserved; the stats strip is 32mm, budgeted 33 to err tall.
GAP_SHEET_MM = 176
GAP_HEADER_MM = 30  # header box + its 4mm margin
GAP_STATS_MM = 33  # stats strip + its 6mm margin
GAP_CTA_MM = 46
GAP_LINE_MM = 5.4  # a 10.5pt line at line-height 1.45
GAP_ITEM_SPACING_MM = 3
# the 220mm .gap-list column fits 121 characters of representative prose at
# 10.5pt; budgeted at 95 so a line of wide glyphs still estimates tall
GAP_CHARS_PER_LINE = 95
# The Proposed-content section sets one size smaller than the numbered list,
# so it gets its own line budget instead of borrowing the 10.5pt one — with 29
# entries on a real cascade, rounding every line up by 10% costs whole sheets.
# The same 220mm column fits 132 characters at 9.5pt, 127 when the whole line
# is the semibold element-label prefix; budgeted at 105 for the same ~20%
# safety margin the numbered list carries.
GAP_PROPOSED_LINE_MM = 4.9  # a 9.5pt line at line-height 1.45
GAP_PROPOSED_SPACING_MM = 2
GAP_PROPOSED_CHARS = 105
# One per-one-pager subheading: its own 10pt line plus the margins that
# separate it from the group above (3mm) and its own list below (1.5mm), and
# the 2mm bottom margin of the preceding <ul>. Budgeted tall, like the rest.
GAP_PROPOSED_PAGE_MM = 11
# heading + count line + the <ul>'s own 6mm margin, which lands on whichever
# sheet the section starts (GAP_SHEET_MM reserves one list margin, not two)
GAP_SECTION_MM = 22
# The Sources block's heading: its 4mm lead-in, its own 12pt line, the 2mm
# below it and the <ul>'s 6mm bottom margin. No count line, so it budgets
# shorter than GAP_SECTION_MM — rounded up, like every constant here.
GAP_SOURCES_HEADING_MM = 18
# The Gap Report cites provenance, it does not reproduce a bibliography: past
# this many entries the block says how many more there are and stops.
SOURCES_MAX = 8


def gap_item_mm(text):
    return GAP_ITEM_SPACING_MM + GAP_LINE_MM * (1 + len(text) // GAP_CHARS_PER_LINE)


def gap_proposed_mm(text):
    """Height of one Proposed-content line. `text` must be the line the markup
    actually produces, separators included — its semibold prefix is why
    GAP_PROPOSED_CHARS is measured on a semibold sample."""
    return GAP_PROPOSED_SPACING_MM + GAP_PROPOSED_LINE_MM * (
        1 + len(text) // GAP_PROPOSED_CHARS
    )


def gap_chunks(items):
    """Pack (kind, html, mm) items into sheets: [(start_number, [(kind, html)])].
    Only "item" entries are numbered, so start_number continues the gap list's
    numbering across sheets while the Proposed-content block flows through the
    same packing. The first sheet also carries the stats strip; the last must
    leave room for the CTA hero, which otherwise gets a closing sheet of its
    own."""
    chunks = []
    budget = GAP_SHEET_MM - GAP_HEADER_MM - GAP_STATS_MM
    current, used, start = [], 0, 1
    for kind, block, mm in items:
        if current and used + mm > budget:
            chunks.append((start, current))
            start += _numbered_count(current)
            current, used = [], 0
            budget = GAP_SHEET_MM - GAP_HEADER_MM
        current.append((kind, block))
        used += mm
    chunks.append((start, current))
    if current and used + GAP_CTA_MM > budget:
        chunks.append((start + _numbered_count(current), []))
    return chunks


def _numbered_count(chunk):
    """How many of a sheet's entries carry a list number."""
    return sum(1 for kind, _block in chunk if kind == "item")


# The unnumbered gap-chunk kinds and the list each one's run is wrapped in. A
# kind missing here raises rather than falling into some other section's
# markup — a new block must name its own list.
GAP_LIST_CLASS = {"proposed": "gap-proposed", "source": "gap-sources"}


def gap_chunk_html(start, chunk):
    """One sheet's items back into markup: consecutive numbered entries share
    an <ol> that continues the document-wide numbering, consecutive entries of
    an unnumbered kind share that kind's <ul>, headings and page subheadings
    stand alone (so each one-pager's entries land in their own list under their
    own title)."""
    out, run, run_kind, number = [], [], None, start

    def flush():
        nonlocal run, run_kind, number
        if not run:
            return
        if run_kind == "item":
            out.append('<ol class="gap-list" start="%d">%s</ol>' % (number, "".join(run)))
            number += len(run)
        else:
            out.append('<ul class="%s">%s</ul>' % (GAP_LIST_CLASS[run_kind], "".join(run)))
        run, run_kind = [], None

    for kind, block in chunk:
        if kind in ("heading", "subheading"):
            flush()
            out.append(block)
            continue
        if run and kind != run_kind:
            flush()
        run_kind = kind
        run.append(block)
    flush()
    return "".join(out)


def proposed_item(entry):
    """One marked element as a gap-chunk item. The line names the element,
    not the page — the page is the subheading this entry sits under, written
    once for the whole group instead of repeated down the left edge."""
    _page_key, _page_title, label, clean, note = entry
    text = truncate(clean)
    note = truncate(note)
    # the plain-text twin of the markup below, separators included — the
    # height estimate must measure the line the reader actually gets
    line = "%s: %s" % (label, text) + (" (%s)" % note if note else "")
    why = ' <span class="gap-proposed-why">(%s)</span>' % esc(note) if note else ""
    return (
        "proposed",
        '<li class="gap-proposed-item">'
        '<span class="gap-proposed-src">%s:</span> %s%s</li>' % (esc(label), esc(text), why),
        gap_proposed_mm(line),
    )


def proposed_section_items(entries):
    """The Proposed-content section as gap-chunk items: one heading block
    carrying the count summary, then per one-pager a subheading and one line
    per marked element. They ride the same packing as the questions, so the
    section flows onto a continuation sheet instead of running off this one."""
    if not entries:
        return []
    heading = (
        '<div class="gap-proposed-heading">%s</div><div class="gap-proposed-count">%s</div>'
        % (esc(S["proposed_heading"]), esc(proposed_count_line(entries)))
    )
    items = []
    for page_title, group in proposed_groups(entries):
        group_items = [proposed_item(entry) for entry in group]
        # A subheading claims its first entry's height on top of its own, so
        # it can only land on a sheet that also holds one of its entries — a
        # page title alone at the foot of a sheet reads as a group with
        # nothing in it. The heading above does the same for the first
        # subheading. The claimed height is then counted twice, which only
        # ever leaves the sheet slack.
        items.append(
            (
                "subheading",
                '<div class="gap-proposed-page">%s</div>' % esc(page_title),
                GAP_PROPOSED_PAGE_MM + group_items[0][2],
            )
        )
        items.extend(group_items)
    return [("heading", heading, GAP_SECTION_MM + items[0][2])] + items


def source_lines(bundle):
    """The Sources block's plain text as (shown, more): the bundle's
    `company.sourceDocuments` up to SOURCES_MAX, one scannable line each, and
    the "+N more" line ("" when nothing overflows). Documents arrive as
    filenames and fetched public sources as "https://… (accessed
    YYYY-MM-DD)" — free text either way, so every line is truncated like a
    Proposed-content entry and escaped by its caller. ONE derivation feeds
    both surfaces, so the HTML artifact and the built-in PDF cannot cite
    differently."""
    sources = (bundle.get("company") or {}).get("sourceDocuments") or []
    shown = [truncate(text) for text in sources[:SOURCES_MAX]]
    overflow = len(sources) - len(shown)
    return shown, plural("sources_more", overflow) if overflow else ""


def sources_section_items(bundle):
    """The Sources block as gap-chunk items: one heading, then one line per
    cited source. It closes the Gap Report — provenance for everything above
    it — and rides the same packing, so a long list flows onto a continuation
    sheet instead of running off this one. A bundle naming no sources renders
    no block at all."""
    shown, more = source_lines(bundle)
    if not shown:
        return []
    items = [
        ("source", '<li class="gap-sources-item">%s</li>' % esc(line), gap_proposed_mm(line))
        for line in shown
    ]
    if more:
        items.append(
            (
                "source",
                '<li class="gap-sources-item gap-sources-more">%s</li>' % esc(more),
                gap_proposed_mm(more),
            )
        )
    heading = '<div class="gap-sources-heading">%s</div>' % esc(S["sources_heading"])
    # the heading claims its first entry's height, like the Proposed-content
    # section above: a "Sources" title alone at the foot of a sheet cites
    # nothing
    return [("heading", heading, GAP_SOURCES_HEADING_MM + items[0][2])] + items


def gap_report_html(bundle, gaps, proposed):
    questions = bundle.get("openQuestions") or []
    company = bundle.get("company", {}).get("name", "")
    generated_at = bundle.get("generator", {}).get("generatedAt", "")

    with_target, total_goals = gap_stats(bundle)
    total_items = len(questions) + len(gaps)

    stats = """
  <div class="stats">
    <div class="stat"><div class="stat-number">%d/%d</div><div class="stat-label">%s</div></div>
    <div class="stat"><div class="stat-number">%d</div><div class="stat-label">%s</div></div>
    <div class="stat"><div class="stat-number">%d</div><div class="stat-label">%s</div></div>
  </div>""" % (
        with_target,
        total_goals,
        S["stat_targets"],
        len(questions),
        # the number above each label is typeset on its own, so the count only
        # selects the label's form — it is not written into it
        plural_form("stat_questions", len(questions)),
        len(gaps),
        plural_form("stat_missing", len(gaps)),
    )

    items = [("item", "<li>%s</li>" % esc(q), gap_item_mm(q)) for q in questions]
    items += [
        ("item", '<li class="statement-gap">%s</li>' % esc(g), gap_item_mm(g)) for g in gaps
    ]
    items += proposed_section_items(proposed)
    items += sources_section_items(bundle)
    chunks = gap_chunks(items)

    # The hero heading is the CTA copy alone: the footer pill on this very
    # sheet already spells the host out, and printing it twice reads as a
    # repeated ad rather than one invitation. The heading stays the link.
    cta_hero = """
    <div class="cta-hero">
      <h3><a href="%s">%s</a></h3>
      <p>%s</p>
      <p class="cta-close">%s</p>
      <p class="cta-whitelabel">%s</p>
    </div>""" % (
        CTA_HREF,
        esc(S["cta_title"]),
        esc(S["cta_body"]),
        S["cta_close"],
        esc(S["cta_whitelabel"]),
    )

    sections = []
    for index, (start, chunk) in enumerate(chunks):
        title = plural("gap_title", total_items)
        if index:
            title += " — %s" % S["gap_continued"]
        sections.append(
            """
<section class="page gap-page">
  <div class="stripe"></div>
  <div class="page-body">
    <header>
      <div class="header-text">
        <div class="kicker kicker-gap">%s</div>
        <h1>%s</h1>
        <p class="ambition">%s</p>
      </div>
      <img class="logo" src="data:image/svg+xml;base64,%s" alt="Alaigned" />
    </header>
    %s
    %s
    %s
  </div>
  %s
</section>"""
            % (
                S["gap_kicker"],
                title,
                S["gap_subtitle"] % esc(company),
                LOGO_B64,
                stats if index == 0 else "",
                gap_chunk_html(start, chunk),
                cta_hero if index == len(chunks) - 1 else "",
                footer_html(generated_at),
            )
        )
    return "".join(sections)


# --- document ----------------------------------------------------------------

# Geometry and palette copied from the product's PDF template
# (one_pager_pdf/template.ex): landscape A4 (297x210mm), 4mm brand stripe,
# 8/12/4mm page padding, 36mm label column, pillar cells side by side.
# Palette mirrors the design tokens (assets/css/tokens.css): brand accent
# #118E64 (600) with #0A6447 (800) for labels; ink/line/text greys from the
# same sheet; status amber #E48A1B for gaps (status colors deliberately do
# not follow tenant brand). Kept as hex because this file renders outside any
# CSS-variable pipeline — same reasoning as the product's PDF template.
CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: 'Host Grotesk', ui-sans-serif, system-ui, -apple-system, 'Segoe UI', sans-serif;
  color: #232426; background: #eef1f4; line-height: 1.45;
  -webkit-print-color-adjust: exact; print-color-adjust: exact;
}
a { color: #118E64; }
.page {
  background: #ffffff; width: 297mm; min-height: 210mm; margin: 24px auto;
  box-shadow: 0 2px 4px 0 rgba(0,0,0,0.08), 0 4px 8px 0 rgba(0,0,0,0.04);
  display: flex; flex-direction: column;
}
.stripe { width: 100%; height: 4mm; background: #118E64; flex-shrink: 0; }
.page-body { flex: 1; padding: 8mm 12mm 4mm 12mm; display: flex; flex-direction: column; }
header {
  display: flex; align-items: flex-start; justify-content: space-between; gap: 10mm;
  border-bottom: 0.4mm solid #E7EBEF; padding-bottom: 5mm; margin-bottom: 4mm;
}
.kicker { font-size: 8pt; letter-spacing: 0.08em; text-transform: uppercase; color: #0A6447; font-weight: 600; margin-bottom: 1mm; }
.kicker strong { color: #232426; }
.kicker-gap { color: #E48A1B; }
h1 { font-size: 22pt; font-weight: 700; line-height: 1.1; margin: 0 0 2mm 0; letter-spacing: -0.01em; }
.ambition { font-size: 10pt; color: #4B5563; margin: 0; max-width: 200mm; }
.logo { height: 9mm; max-width: 40mm; object-fit: contain; flex-shrink: 0; margin-top: 1mm; }
.core {
  display: grid; grid-template-columns: 36mm 1fr; gap: 1.5mm 4mm;
  padding: 2mm 0 4mm 0; border-bottom: 0.2mm solid #E7EBEF; margin-bottom: 4mm;
}
.core-label, .band-label, .row-label {
  font-size: 8pt; font-weight: 600; letter-spacing: 0.08em; color: #0A6447;
}
.core-label { padding-top: 0.5mm; }
.core-value { font-size: 9.5pt; line-height: 1.35; }
.pillars {
  display: grid; grid-template-columns: 36mm 1fr; gap: 3mm; margin-bottom: 4mm;
}
.band-label { padding-top: 1mm; }
.pillar-cells { display: grid; gap: 3mm; align-items: start; }
.pillar-cells.cols-1 { grid-template-columns: 1fr; }
.pillar-cells.cols-2 { grid-template-columns: repeat(2, 1fr); }
.pillar-cells.cols-3 { grid-template-columns: repeat(3, 1fr); }
.pillar-cells.cols-4 { grid-template-columns: repeat(4, 1fr); }
.pillar-cells.cols-5 { grid-template-columns: repeat(5, 1fr); }
.pillar-cells.cols-6 { grid-template-columns: repeat(6, 1fr); }
.pillar { break-inside: avoid; min-width: 0; overflow-wrap: break-word; }
.pillar-name {
  font-size: 11pt; font-weight: 700; color: #232426; padding: 2mm 2.5mm;
  background: rgba(0, 0, 0, 0.04); border-top: 0.8mm solid #118E64;
  border-radius: 1mm 1mm 0 0; overflow-wrap: break-word; min-width: 0;
}
.pillar-body { padding: 1.5mm 2.5mm 0 2.5mm; min-width: 0; }
.row { font-size: 8.5pt; line-height: 1.35; margin: 0.6mm 0; }
.row-label { margin-right: 1.5mm; }
.row-value p { display: inline; }
/* The product template's list rhythm, verbatim (.pdf-pillar-initiatives): 9pt
   at 1.4, 1mm between items, and the 4mm indent as *padding* rather than
   margin — with the global `* { padding: 0 }` reset an outside marker drawn
   against a margin-only indent lands in the pillar cell's own padding, flush
   under the SUCCESS label above it, and the list stops reading as a list. The
   marker colour is the one deliberate departure from the master: brand green,
   matched by the built-in PDF's bullet and the DOCX numbering, so an
   initiative bullet is the same mark in all three engines. */
.initiatives { margin: 1mm 0 0 0; padding-left: 4mm; font-size: 9pt; line-height: 1.4; }
.initiatives li { margin-bottom: 1mm; }
.initiatives li::marker { color: #118E64; }
.init-name { display: inline; }
.chip-band { padding-top: 3mm; border-top: 0.2mm solid #E7EBEF; }
.chip-row { display: grid; grid-template-columns: 36mm 1fr; gap: 3mm; align-items: start; margin-bottom: 2mm; }
.chip-row .band-label { padding-top: 1.2mm; }
.chips { display: flex; gap: 2mm; flex-wrap: wrap; align-items: center; }
.chip {
  font-size: 9pt; padding: 1.2mm 3mm; border-radius: 999px;
  background: rgba(0, 0, 0, 0.04); border: 0.2mm solid #E7EBEF;
}
/* The document-level honesty line, in the amber the per-item badges used
   (#9A6700 ink on a lighter tint of their #FFF3D6 ground — a full-width band
   carries far more color than a 7pt chip did): one quiet line under the
   header band, deliberately too small to compete with the strategy. It states
   a fact about the whole cascade; it does not decorate the page. */
.draft-banner {
  font-size: 8pt; color: #9A6700; background: #FFF8E7;
  border-left: 0.8mm solid #E8D49A; border-radius: 0 1mm 1mm 0;
  padding: 1.2mm 3mm; margin-bottom: 3mm;
}
.gap { font-size: 9pt; font-style: italic; color: #E48A1B; }
/* The footer's two halves are deliberately unequal: the CTA is a brand pill
   (the only call to action a --split sheet carries), the date stays a grey
   footnote. `center` alignment, not `baseline` — a padded pill and a bare
   date share no baseline worth aligning on. The body already sets
   print-color-adjust: exact, so the fill survives every print path. */
footer {
  display: flex; justify-content: space-between; align-items: center; gap: 4mm;
  margin: 1.5mm 12mm 4mm 12mm; padding-top: 1.5mm;
  border-top: 0.2mm solid #E7EBEF; font-size: 7.5pt; color: #9CA3AF;
}
/* line-height 1.15, not the body's 1.45: the tightened lead pays for the
   pill's padding, so the whole footer block stays within half a millimetre of
   the grey line it replaced and the sheet budgets above still hold. */
.footer-cta a {
  display: inline-block; background: #118E64; color: #ffffff; font-weight: 700;
  font-size: 8.5pt; line-height: 1.15; padding: 1.2mm 3.5mm; border-radius: 999px;
  text-decoration: none;
}
.gap-page .stats { display: flex; gap: 4mm; margin-bottom: 6mm; }
.gap-page .stat { flex: 1; border: 0.2mm solid #E7EBEF; border-radius: 2mm; padding: 4mm; }
.gap-page .stat-number { font-size: 26pt; font-weight: 800; letter-spacing: -0.02em; color: #E48A1B; }
.gap-page .stat-label { font-size: 8.5pt; color: #6B7280; }
.gap-list { margin: 0 0 6mm 6mm; max-width: 220mm; }
.gap-list li { font-size: 10.5pt; margin-bottom: 3mm; padding-left: 1.5mm; }
.gap-list li::marker { font-weight: 800; color: #E48A1B; }
.gap-list .statement-gap { color: #6B7280; }
.gap-proposed-heading { font-size: 12pt; font-weight: 700; color: #9A6700; margin-bottom: 1mm; }
.gap-proposed-count { font-size: 9pt; color: #6B7280; margin-bottom: 3mm; }
/* One subheading per one-pager: the page title is written once and the
   entries below it name only their element, so a 30-character title stops
   being the first thing on every line. */
.gap-proposed-page { font-size: 10pt; font-weight: 700; color: #232426; margin: 3mm 0 1.5mm 0; }
.gap-proposed { list-style: none; margin: 0 0 2mm 0; max-width: 220mm; }
.gap-proposed-item { font-size: 9.5pt; color: #4B5563; margin-bottom: 2mm; }
.gap-proposed-src { font-weight: 600; color: #9A6700; }
.gap-proposed-why { font-style: italic; color: #9A6700; }
/* Provenance, not a warning: the Sources block matches the Proposed-content
   section's rhythm but keeps the neutral ink of body text — the amber on this
   page marks what is missing or composed, and a cited source is neither. */
.gap-sources-heading { font-size: 12pt; font-weight: 700; color: #232426; margin: 4mm 0 2mm 0; }
.gap-sources { list-style: none; margin: 0 0 2mm 0; max-width: 220mm; }
.gap-sources-item {
  font-size: 9.5pt; color: #4B5563; margin-bottom: 1.5mm;
  overflow-wrap: anywhere;
}
.gap-sources-more { color: #6B7280; font-style: italic; }
.cta-hero {
  margin-top: auto; background: #E8F7F1; border: 0.5mm solid #118E64;
  border-radius: 3mm; padding: 6mm 8mm;
}
.cta-hero h3 { font-size: 17pt; margin-bottom: 2.5mm; letter-spacing: -0.01em; }
.cta-hero a { color: #0A6447; text-decoration: none; }
.cta-hero p { font-size: 9.5pt; }
.cta-hero .cta-close { margin-top: 2.5mm; font-weight: 600; }
.cta-hero .cta-whitelabel { margin-top: 2.5mm; font-size: 8.5pt; color: #0A6447; }
/* Sheet-overflow damage control, not a guarantee: when a page still exceeds
   one sheet despite the renderer's own pagination, these keep the split
   between logical units — the continuation sheet still starts at the paper
   edge without padding, which is why the height estimates must err tall.
   WEASYPRINT_CSS mirrors these with the legacy page-break-* names. */
header, .core, .stats, .chip-band, .cta-hero, .draft-banner { break-inside: avoid; }
.gap-list li, .gap-proposed-item, .gap-sources-item { break-inside: avoid; }
@media print {
  body { background: none; }
  .page {
    /* Full sheet height so the flex column pins the footer to the bottom
       of every printed page; the -0.5mm slack keeps an exact-fit box from
       spilling a phantom blank sheet on rounding. */
    width: auto; min-height: 209.5mm; margin: 0; box-shadow: none;
    page-break-after: always;
  }
  .page:last-child { page-break-after: auto; }
}
@page { size: A4 landscape; margin: 0; }
"""


def render(bundle):
    by_ref = {op["ref"]: op for op in bundle["onePagers"]}
    company = bundle.get("company", {}).get("name", "Strategy")

    gaps = []
    proposed = proposed_entries(bundle)
    banner = draft_banner_text(proposed, standalone=False)
    rendered = [
        one_pager_html(op, by_ref, bundle, gaps, banner) for op in bundle["onePagers"]
    ]

    # Page order: the root one-pager first (their strategy, laid out), the Gap
    # Report second (the punch lands after the credibility), team pages as the
    # cascade appendix. onePagers[0] is the root per the bundle contract.
    pages = rendered[:1] + [gap_report_html(bundle, gaps, proposed)] + rendered[1:]

    return document(S["doc_title"] % esc(company), pages)


def document(title, pages):
    # The lang tag follows --lang: chrome and body travel in one language, and
    # a page that lies about it degrades screen readers and Drive's
    # convert-on-upload alike.
    return """<!DOCTYPE html>
<html lang="%s">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>%s</title>
<style>%s</style>
</head>
<body>
%s
</body>
</html>
""" % (S["lang"], title, CSS, "".join(pages))


def slugify(text):
    """Filename-safe ASCII slug (Czech/Slovak diacritics fold to plain letters)."""
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_text.lower()).strip("-")
    return slug or "one-pager"


# --- built-in PDF fallback engine --------------------------------------------
#
# A minimal, stdlib-only PDF writer + layout: the tier-3 engine behind --pdf.
# It exists so the printable artifact is ALWAYS a real PDF — code-exec
# sandboxes without Chromium (ChatGPT/Codex, plain claude.ai chat) previously
# delivered only HTML plus "print it yourself", which fails the use case
# The layout is a simplified sibling of the HTML artifact (same page
# order, stripe, label column, pillar grid, gap report, CTA) — deliberately
# plainer: whenever Chromium or WeasyPrint exists, those engines win and this
# code never runs. Base-14 Helvetica only; Czech/Slovak diacritics ride a
# dynamically built font encoding (cp1252 base + /Differences slots), so no
# font files are embedded and the writer stays dependency-free.

PT_PER_MM = 72 / 25.4
PDF_PAGE_W = 297 * PT_PER_MM
PDF_PAGE_H = 210 * PT_PER_MM
PDF_MARGIN_X = 12 * PT_PER_MM
PDF_BODY_TOP = 4 * PT_PER_MM + 8 * PT_PER_MM  # stripe + top padding
PDF_BODY_BOTTOM = PDF_PAGE_H - 14 * PT_PER_MM  # keeps clear of the footer line
# The header's ceiling: the ambition may fill at most half the body here —
# past that the header stops being a header and the rest flows into the body
# as ordinary budgeted lines. (Nothing else rides the header any more: the
# per-item [PROPOSED] notes that used to hang under the ambition are gone,
# and the draft banner is drawn as the body's first line.)
PDF_HEADER_BOTTOM = PDF_BODY_TOP + (PDF_BODY_BOTTOM - PDF_BODY_TOP) / 2
# The footer CTA pill (the HTML `.footer-cta a` button, drawn as a rect). The
# text keeps the footer baseline; RISE is how far the pill's top edge sits
# above it and H its total height, so the pill spans baseline-8.5 .. baseline+4
# — inside the 14mm the body already stays clear of, and clear of the divider
# line at baseline-12. Nothing here moves PDF_BODY_BOTTOM.
PDF_FOOTER_CTA_SIZE = 8
PDF_FOOTER_PILL_PAD_X = 8
PDF_FOOTER_PILL_RISE = 8.5
PDF_FOOTER_PILL_H = 12.5

# The pillar bullet, mirroring the master's list rhythm (.pdf-pillar-initiatives
# in one_pager_pdf/template.ex): the initiative text sits 4mm right of the row
# label and the marker is drawn back at the cell's own text edge, exactly where
# Chromium places the HTML artifact's disc (measured: marker 0.07mm left of the
# cell edge, text 4.00mm right of it). The size is not the initiative's 8.5pt:
# Helvetica's bullet is a far thinner disc than Host Grotesk's (0.21em against
# 0.32em), so at 8.5pt it draws a 0.6mm dot beside the HTML's 1.0mm one. 11pt
# matches that weight, and the 0.7pt drop puts the enlarged glyph's optical
# centre back on the HTML marker's — Helvetica centres • 0.30em above the
# baseline, so a bigger glyph would otherwise float above the line.
PDF_LIST_INDENT = 4 * PT_PER_MM
PDF_BULLET_SIZE = 11
PDF_BULLET_DROP = 0.7

BRAND = (0.067, 0.557, 0.392)  # #118E64
BRAND_DARK = (0.039, 0.392, 0.278)  # #0A6447
INK = (0.137, 0.141, 0.149)  # #232426
GRAY = (0.294, 0.333, 0.388)  # #4B5563
GRAY_MID = (0.42, 0.447, 0.502)  # #6B7280
GRAY_LIGHT = (0.612, 0.639, 0.686)  # #9CA3AF
LINE = (0.906, 0.922, 0.937)  # #E7EBEF
AMBER = (0.894, 0.541, 0.106)  # #E48A1B
AMBER_DARK = (0.604, 0.404, 0.0)  # #9A6700
BAR_BG = (0.955, 0.955, 0.955)
CTA_BG = (0.91, 0.969, 0.945)  # #E8F7F1
WHITE = (1.0, 1.0, 1.0)  # #FFFFFF — ink on the brand-filled CTA pill

# PostScript glyph names for the Latin Extended-A set the cascade languages
# (EN/CS/SK) need beyond cp1252, plus common typography. Anything else folds
# to its ASCII base via NFKD.
GLYPH_NAMES = {
    "č": "ccaron", "Č": "Ccaron", "ď": "dcaron", "Ď": "Dcaron",
    "ě": "ecaron", "Ě": "Ecaron", "ľ": "lcaron", "Ľ": "Lcaron",
    "ĺ": "lacute", "Ĺ": "Lacute", "ň": "ncaron", "Ň": "Ncaron",
    "ř": "rcaron", "Ř": "Rcaron", "ŕ": "racute", "Ŕ": "Racute",
    "ť": "tcaron", "Ť": "Tcaron", "ů": "uring", "Ů": "Uring",
    "ę": "eogonek", "Ę": "Eogonek", "ą": "aogonek", "Ą": "Aogonek",
    "ł": "lslash", "Ł": "Lslash", "ś": "sacute", "Ś": "Sacute",
    "ż": "zdotaccent", "Ż": "Zdotaccent", "ź": "zacute", "Ź": "Zacute",
    "ő": "ohungarumlaut", "Ő": "Ohungarumlaut",
    "ű": "uhungarumlaut", "Ű": "Uhungarumlaut",
    "•": "bullet",
}

# Characters the base-14 fonts have no glyph for at all, folded to the nearest
# character they do carry. A /Differences slot cannot rescue them: Helvetica
# has no `arrowright` outline, so the slot renders as a blank gap. The HTML
# artifact is unaffected — it draws the real arrow.
CHAR_FALLBACK = {"→": "»"}

# Helvetica / Helvetica-Bold advance widths (per-mille) for ASCII 32–126 —
# the wrap math only; the PDF itself carries no width arrays (base-14 fonts
# bring their own metrics in every viewer).
_HELV_W = (
    "278,278,355,556,556,889,667,191,333,333,389,584,278,333,278,278,"
    "556,556,556,556,556,556,556,556,556,556,278,278,584,584,584,556,"
    "1015,667,667,722,722,667,611,778,722,278,500,667,556,833,722,778,"
    "667,778,722,667,611,722,667,944,667,667,611,278,278,278,469,556,"
    "333,556,556,500,556,556,278,556,556,222,222,500,222,833,556,556,"
    "556,556,333,500,278,556,500,722,500,500,500,334,260,334,584"
)
_HELV_BOLD_W = (
    "278,333,474,556,556,889,722,238,333,333,389,584,278,333,278,278,"
    "556,556,556,556,556,556,556,556,556,556,333,333,584,584,584,611,"
    "975,722,722,722,722,667,611,778,722,278,556,722,611,833,722,778,"
    "667,778,722,667,611,722,667,944,667,667,611,333,278,333,584,556,"
    "333,556,611,556,611,556,333,611,611,278,278,556,278,889,611,611,"
    "611,611,389,556,333,611,556,778,556,556,500,389,280,389,584"
)
HELV_WIDTHS = {chr(32 + i): int(w) for i, w in enumerate(_HELV_W.split(","))}
HELV_BOLD_WIDTHS = {chr(32 + i): int(w) for i, w in enumerate(_HELV_BOLD_W.split(","))}
_EXTRA_W = {"–": 556, "—": 1000, "…": 1000, "•": 350, "’": 222, "‘": 222,
            "“": 333, "”": 333, "„": 333, "€": 556, "°": 400, "×": 584, "»": 556}


def _char_width(ch, bold):
    # measure the character that actually gets drawn, folding included
    ch = CHAR_FALLBACK.get(ch, ch)
    table = HELV_BOLD_WIDTHS if bold else HELV_WIDTHS
    if ch in table:
        return table[ch]
    if ch in _EXTRA_W:
        return _EXTRA_W[ch]
    base = unicodedata.normalize("NFKD", ch)[:1]
    return table.get(base, 556)


def text_width(text, size, bold=False):
    return sum(_char_width(ch, bold) for ch in text) * size / 1000.0


class PdfWriter:
    """Buffered PDF builder: layout emits unicode draw ops, save() builds the
    font encoding from the document's actual charset (cp1252 base, spare byte
    slots re-pointed at Latin-Ext glyphs via /Differences) and serializes."""

    STYLE_FONT = {"": "F1", "b": "F2", "i": "F3", "bi": "F4"}
    BASE_FONTS = {"F1": "Helvetica", "F2": "Helvetica-Bold",
                  "F3": "Helvetica-Oblique", "F4": "Helvetica-BoldOblique"}

    def __init__(self, title):
        self.title = title
        self.pages = []

    def new_page(self):
        self.pages.append({"ops": [], "annots": []})

    def rect(self, x, y, w, h, fill=None, stroke=None, line_w=0.6):
        self.pages[-1]["ops"].append(("rect", x, y, w, h, fill, stroke, line_w))

    def raw(self, stream_bytes):
        """Pre-serialized content-stream fragment (the vector logo)."""
        self.pages[-1]["ops"].append(("raw", stream_bytes))

    def line(self, x1, y1, x2, y2, color, width=0.5):
        self.pages[-1]["ops"].append(("line", x1, y1, x2, y2, color, width))

    def text(self, x, y_baseline, segments):
        """segments: [(text, size, style, rgb)] drawn left to right from x.
        y_baseline is measured from the TOP of the page."""
        self.pages[-1]["ops"].append(("text", x, y_baseline, segments))

    def link(self, x, y_top, w, h, uri):
        # link annotations are written as plain ASCII, and the CTA carries the
        # bundle's attribution ref verbatim — percent-encode so any ref (a
        # Czech slug, a stray space) survives instead of killing the render
        uri = urllib.parse.quote(uri, safe=":/?=&#%")
        self.pages[-1]["annots"].append((x, PDF_PAGE_H - y_top - h, w, h, uri))

    # -- encoding ------------------------------------------------------------

    def _build_encoding(self):
        used = set()
        for page in self.pages:
            for op in page["ops"]:
                if op[0] == "text":
                    for txt, _s, _st, _c in op[3]:
                        # folded first: a slot must never shadow the cp1252
                        # char a fallback resolves to
                        used.update(CHAR_FALLBACK.get(ch, ch) for ch in txt)
        need_slots = sorted(
            ch for ch in used
            if ord(ch) >= 128 and not _cp1252_ok(ch) and ch in GLYPH_NAMES
        )
        # Undefined cp1252 bytes first, then bytes whose cp1252 char this
        # document never uses — a slot never shadows a char the doc needs.
        free = [b for b in (0x7F, 0x81, 0x8D, 0x8F, 0x90, 0x9D)]
        free += [
            b for b in range(0x80, 0x100)
            if b not in free
            and (_cp1252_char(b) is None or _cp1252_char(b) not in used)
        ]
        self.slot_of = {}
        differences = []
        for ch, slot in zip(need_slots, free):
            self.slot_of[ch] = slot
            differences.append((slot, GLYPH_NAMES[ch]))
        return differences

    def _encode(self, text):
        out = bytearray()
        for ch in text:
            ch = CHAR_FALLBACK.get(ch, ch)
            if ch in self.slot_of:
                out.append(self.slot_of[ch])
                continue
            try:
                out += ch.encode("cp1252")
            except UnicodeEncodeError:
                folded = unicodedata.normalize("NFKD", ch).encode("ascii", "ignore")
                out += folded or b"?"
        return bytes(out)

    @staticmethod
    def _esc(raw):
        return raw.replace(b"\\", b"\\\\").replace(b"(", b"\\(").replace(b")", b"\\)")

    # -- serialization -------------------------------------------------------

    def _content_stream(self, page):
        chunks = []
        for op in page["ops"]:
            if op[0] == "raw":
                chunks.append(op[1])
            elif op[0] == "rect":
                _kind, x, y, w, h, fill, stroke, line_w = op
                ops = []
                if fill:
                    ops.append(b"%.3f %.3f %.3f rg" % fill)
                if stroke:
                    ops.append(b"%.3f %.3f %.3f RG %.2f w" % (stroke + (line_w,)))
                paint = b"B" if (fill and stroke) else (b"f" if fill else b"S")
                chunks.append(
                    b"q %s %.2f %.2f %.2f %.2f re %s Q"
                    % (b" ".join(ops), x, PDF_PAGE_H - y - h, w, h, paint)
                )
            elif op[0] == "line":
                _kind, x1, y1, x2, y2, color, width = op
                chunks.append(
                    b"q %.3f %.3f %.3f RG %.2f w %.2f %.2f m %.2f %.2f l S Q"
                    % (color + (width, x1, PDF_PAGE_H - y1, x2, PDF_PAGE_H - y2))
                )
            elif op[0] == "text":
                _kind, x, y, segments = op
                parts = [b"BT"]
                cursor = x
                for txt, size, style, rgb in segments:
                    if not txt:
                        continue
                    font = self.STYLE_FONT[style].encode()
                    parts.append(b"/%s %.2f Tf" % (font, size))
                    parts.append(b"%.3f %.3f %.3f rg" % rgb)
                    parts.append(b"1 0 0 1 %.2f %.2f Tm" % (cursor, PDF_PAGE_H - y))
                    parts.append(b"(%s) Tj" % self._esc(self._encode(txt)))
                    cursor += text_width(txt, size, "b" in style)
                parts.append(b"ET")
                chunks.append(b" ".join(parts))
        return zlib.compress(b"\n".join(chunks))

    def save(self, path):
        differences = self._build_encoding()
        objects = []  # 1-based bodies, object 1 = catalog, 2 = pages tree

        def add(body):
            objects.append(body)
            return len(objects)

        add(b"")  # 1: catalog placeholder
        add(b"")  # 2: pages placeholder

        diff_parts = b" ".join(b"%d /%s" % (slot, name.encode()) for slot, name in differences)
        enc_ref = add(
            b"<< /Type /Encoding /BaseEncoding /WinAnsiEncoding /Differences [ %s ] >>"
            % diff_parts
            if differences
            else b"<< /Type /Encoding /BaseEncoding /WinAnsiEncoding >>"
        )
        font_refs = {}
        for res_name, base in self.BASE_FONTS.items():
            font_refs[res_name] = add(
                b"<< /Type /Font /Subtype /Type1 /BaseFont /%s /Encoding %d 0 R >>"
                % (base.encode(), enc_ref)
            )
        font_dict = b" ".join(
            b"/%s %d 0 R" % (name.encode(), ref) for name, ref in font_refs.items()
        )

        page_refs = []
        for page in self.pages:
            stream = self._content_stream(page)
            content_ref = add(
                b"<< /Length %d /Filter /FlateDecode >>\nstream\n%s\nendstream"
                % (len(stream), stream)
            )
            annot_refs = []
            for x, y, w, h, uri in page["annots"]:
                annot_refs.append(
                    add(
                        b"<< /Type /Annot /Subtype /Link /Rect [ %.2f %.2f %.2f %.2f ] "
                        b"/Border [ 0 0 0 ] /A << /Type /Action /S /URI /URI (%s) >> >>"
                        % (x, y, x + w, y + h, self._esc(uri.encode("ascii")))
                    )
                )
            annots = (
                b"/Annots [ %s ]" % b" ".join(b"%d 0 R" % r for r in annot_refs)
                if annot_refs
                else b""
            )
            page_refs.append(
                add(
                    b"<< /Type /Page /Parent 2 0 R /MediaBox [ 0 0 %.2f %.2f ] "
                    b"/Resources << /Font << %s >> >> /Contents %d 0 R %s >>"
                    % (PDF_PAGE_W, PDF_PAGE_H, font_dict, content_ref, annots)
                )
            )

        objects[0] = b"<< /Type /Catalog /Pages 2 0 R >>"
        objects[1] = b"<< /Type /Pages /Kids [ %s ] /Count %d >>" % (
            b" ".join(b"%d 0 R" % r for r in page_refs),
            len(page_refs),
        )
        title_utf16 = b"\xfe\xff" + self.title.encode("utf-16-be")
        info_ref = add(b"<< /Title (%s) /Producer (render_cascade.py) >>" % self._esc(title_utf16))

        out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        offsets = []
        for index, body in enumerate(objects, start=1):
            offsets.append(len(out))
            out += b"%d 0 obj\n%s\nendobj\n" % (index, body)
        xref_at = len(out)
        out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1)
        for offset in offsets:
            out += b"%010d 00000 n \n" % offset
        out += (
            b"trailer\n<< /Size %d /Root 1 0 R /Info %d 0 R >>\nstartxref\n%d\n%%%%EOF\n"
            % (len(objects) + 1, info_ref, xref_at)
        )
        Path(path).write_bytes(bytes(out))


def _cp1252_ok(ch):
    try:
        ch.encode("cp1252")
        return True
    except UnicodeEncodeError:
        return False


def _cp1252_char(byte):
    try:
        return bytes([byte]).decode("cp1252")
    except UnicodeDecodeError:
        return None


# -- rich-text wrapping --------------------------------------------------------


def _hard_break(word, size, bold, width):
    """Cut a token with no break opportunity into width-sized pieces. Only
    tokens WIDER than the whole wrap width get here, so ordinary text wraps
    byte for byte as before; without this a space-less 400-char goal (a pasted
    URL, a concatenated identifier) would draw straight past the right
    margin. No hyphen: the break point is arbitrary, so implying a syllable
    would be a lie."""
    pieces, current, used = [], "", 0.0
    for ch in word:
        w = _char_width(ch, bold) * size / 1000.0
        if current and used + w > width:
            pieces.append(current)
            current, used = "", 0.0
        current += ch
        used += w
    if current:
        pieces.append(current)
    return pieces


def wrap_segments(segments, width):
    """Greedy word-wrap of [(text, size, style, rgb)] into lines of the same
    shape. A word longer than the width is hard-broken into pieces, each of
    which takes a line of its own."""
    words = []
    for txt, size, style, rgb in segments:
        bold = "b" in style
        for word in txt.split(" "):
            if text_width(word, size, bold) > width:
                for piece in _hard_break(word, size, bold, width):
                    words.append((piece, size, style, rgb))
                continue
            words.append((word, size, style, rgb))
    lines, current, used = [], [], 0.0
    for word, size, style, rgb in words:
        space_w = text_width(" ", size, "b" in style)
        word_w = text_width(word, size, "b" in style)
        extra = word_w + (space_w if current else 0)
        if current and used + extra > width:
            lines.append(current)
            current, used = [], 0.0
            extra = word_w
        prefix = " " if current else ""
        current.append((prefix + word, size, style, rgb))
        used += extra
    if current:
        lines.append(current)
    return lines


def _strip_markup(value):
    return html.unescape(re.sub(r"<[^>]+>", "", value))


def _plain(s_key, *fmt):
    """Chrome strings are HTML-authored — unescape entities and strip tags
    for the PDF surface."""
    value = S[s_key] % fmt if fmt else S[s_key]
    return _strip_markup(value)


def _plain_plural(s_key, count):
    """_plain() for a counted chrome string: the language picks its form
    first, the markup comes off second. Both non-HTML engines go through here,
    so the PDF and the DOCX can never select differently from the HTML."""
    return _strip_markup(plural(s_key, count))


# -- bundle extraction (mirror of the HTML walkers, producing plain text) ------


def _pdf_val(node):
    """None (skip) | ('gap',) | ('text', clean). The [PROPOSED …] marker is
    stripped and dropped here: the note it carried is listed once on the Gap
    Report page, not beside every value."""
    text = node.get("textValue")
    if text is None:
        return ("gap",) if node.get("mandatory") else None
    return ("text", split_proposed(text)[0])


def _pdf_entity_parts(entity, gaps, page_title):
    parts = []
    for key, node in entity.items():
        if key in ("label", "metadata", "name"):
            continue
        if is_text_node(node):
            value = _pdf_val(node)
            if value is None:
                continue
            if value[0] == "gap":
                # gap entries carry the raw label with the HTML walkers' ""
                # fallback — the two artifacts must count identical gaps
                gaps.append(S["gap_entry"] % (page_title, node.get("label", "")))
            parts.append(("row", trim_label(node.get("label", key)), value))
        elif is_collection(node):
            for item in node["content"]:
                name = item.get("name")
                title = (
                    split_proposed(name["textValue"])[0]
                    if is_text_node(name) and name.get("textValue")
                    else ""
                )
                parts.append(("init", title, _pdf_entity_parts(item, gaps, page_title)))
    return parts


def _pdf_extract_op(one_pager, by_ref, gaps):
    content = one_pager["content"]
    title = one_pager.get("title", "")
    parent = by_ref.get(one_pager.get("parentRef"))

    ambition = content.get("companyAmbition")
    ambition_val = _pdf_val(ambition) if is_text_node(ambition) else None
    if ambition_val == ("gap",):
        gaps.append(S["gap_entry"] % (title, ambition.get("label", "")))

    core = []
    for key, node in content.items():
        if key in ("metadata", "companyAmbition") or not is_text_node(node):
            continue
        value = _pdf_val(node)
        if value is None:
            continue
        if value[0] == "gap":
            gaps.append(S["gap_entry"] % (title, node.get("label", "")))
        label = node.get("label") or STATEMENT_HEADINGS.get(key, key)
        core.append((trim_label(label), value))

    collections = [v for v in content.values() if is_collection(v)]
    pillar_bands, chip_bands = [], []
    for coll in collections:
        if coll["content"] and "name" in coll["content"][0]:
            pillars = []
            for pillar in coll["content"]:
                name = pillar.get("name", {})
                pillar_title = split_proposed(name.get("textValue") or "")[0]
                pillars.append((pillar_title, _pdf_entity_parts(pillar, gaps, title)))
            pillar_bands.append((coll.get("label", "Pillars"), pillars))
        else:
            chips = []
            for item in coll["content"]:
                primary = item.get("content")
                if is_text_node(primary) and isinstance(primary.get("textValue"), str):
                    chips.append(split_proposed(primary["textValue"])[0])
            if chips:
                chip_bands.append((coll.get("label", ""), chips))

    return {
        "title": title,
        "level": one_pager.get("level"),
        "parent_title": parent["title"] if parent else None,
        "ambition": ambition_val,
        "core": core,
        "pillar_bands": pillar_bands,
        "chip_bands": chip_bands,
    }


# -- built-in layout -----------------------------------------------------------

LABEL_COL = 36 * PT_PER_MM
COL_GAP = 11
CELL_GAP = 8.5
# the value/grid column right of the label column — shared by the core strip,
# the pillar grid and the chip band
VALUE_X = PDF_MARGIN_X + LABEL_COL + COL_GAP
VALUE_W = PDF_PAGE_W - PDF_MARGIN_X - VALUE_X


class BuiltinLayout:
    def __init__(self, writer, generated_at):
        self.pdf = writer
        self.generated_at = generated_at
        self.y = 0.0

    # every sheet: brand stripe + footer with the linked CTA
    def _sheet_chrome(self):
        self.pdf.new_page()
        self.pdf.rect(0, 0, PDF_PAGE_W, 4 * PT_PER_MM, fill=BRAND)
        footer_y = PDF_PAGE_H - 8 * PT_PER_MM
        # 12, not the old 9: the divider clears the pill's top edge. It still
        # sits below PDF_BODY_BOTTOM, so no body line moves.
        self.pdf.line(PDF_MARGIN_X, footer_y - 12, PDF_PAGE_W - PDF_MARGIN_X, footer_y - 12, LINE)
        # The CTA as a brand-filled pill, the HTML footer's button in the
        # writer's own vocabulary (plain rect — the writer draws no curves, and
        # the DOCX run shading is square too). Both footer strings keep the
        # single baseline the sheet-clipping guard pins them to; the pill is a
        # rect around it, so nothing new lands below the body floor.
        cta = cta_label(_plain("cta_title"))
        pill_w = text_width(cta, PDF_FOOTER_CTA_SIZE, True) + 2 * PDF_FOOTER_PILL_PAD_X
        self.pdf.rect(
            PDF_MARGIN_X,
            footer_y - PDF_FOOTER_PILL_RISE,
            pill_w,
            PDF_FOOTER_PILL_H,
            fill=BRAND,
        )
        self.pdf.text(
            PDF_MARGIN_X + PDF_FOOTER_PILL_PAD_X,
            footer_y,
            [(cta, PDF_FOOTER_CTA_SIZE, "b", WHITE)],
        )
        self.pdf.link(
            PDF_MARGIN_X,
            footer_y - PDF_FOOTER_PILL_RISE,
            pill_w,
            PDF_FOOTER_PILL_H,
            CTA_HREF,
        )
        generated = _plain("generated", self.generated_at)
        self.pdf.text(
            PDF_PAGE_W - PDF_MARGIN_X - text_width(generated, 7.5),
            footer_y,
            [(generated, 7.5, "", GRAY_LIGHT)],
        )
        self.y = PDF_BODY_TOP

    def _wordmark(self):
        logo = logo_vector()
        if logo:
            vb_w, vb_h, paths = logo
            height = 9 * PT_PER_MM  # mirrors the HTML header's 9mm logo
            scale = height / vb_h
            x = PDF_PAGE_W - PDF_MARGIN_X - vb_w * scale
            y_top = self.y + 2
            chunks = [
                b"q",
                b"%.4f 0 0 %.4f %.3f %.3f cm" % (scale, -scale, x, PDF_PAGE_H - y_top),
            ]
            for pdf_ops, rgb in paths:
                chunks.append(b"%.3f %.3f %.3f rg" % rgb)
                chunks.append(pdf_ops.encode())
                chunks.append(b"f")
            chunks.append(b"Q")
            self.pdf.raw(b"\n".join(chunks))
            return
        word = "Alaigned"
        self.pdf.text(
            PDF_PAGE_W - PDF_MARGIN_X - text_width(word, 13, True),
            self.y + 10,
            [(word, 13, "b", BRAND)],
        )

    def _draw_lines(self, x, lines, leading, y=None):
        y = self.y if y is None else y
        for line in lines:
            y += leading
            self.pdf.text(x, y, line)
        return y

    def content_width(self):
        return PDF_PAGE_W - 2 * PDF_MARGIN_X

    def sheet_header(self, kicker_segs, title, subtitle_segs):
        """Draw the sheet's header; return the [(x, lines, leading)] fragments
        of the subtitle that did not fit above PDF_HEADER_BOTTOM, for the
        caller to flow into the body — the ambition is strategy content, so it
        is budgeted and never disappears under the footer.

        The TITLE stays unbudgeted by choice: it is the sheet's heading, and a
        heading that continues in the body is no longer a heading. Nothing
        bounds its length either — the packaged methodology schema carries no
        maxLength anywhere — so a title taller than a sheet draws past the
        bottom and repeats on every continuation sheet. That is an accepted
        risk for a name, not a covered case."""
        self._sheet_chrome()
        self._wordmark()
        self.y += 8
        self.pdf.text(PDF_MARGIN_X, self.y, kicker_segs)
        self.y += 4
        title_lines = wrap_segments(
            [(title, 20, "b", INK)], self.content_width() - 110
        )
        self.y = self._draw_lines(PDF_MARGIN_X, title_lines, 24)
        deferred = []
        if subtitle_segs:
            sub_lines = wrap_segments(subtitle_segs, self.content_width() - 110)
            fits = max(0, int((PDF_HEADER_BOTTOM - self.y) // 13))
            self.y = self._draw_lines(PDF_MARGIN_X, sub_lines[:fits], 13) + 2
            if sub_lines[fits:]:
                deferred.append((PDF_MARGIN_X, sub_lines[fits:], 13))
        self.y += 8
        self.pdf.line(PDF_MARGIN_X, self.y, PDF_PAGE_W - PDF_MARGIN_X, self.y, LINE)
        self.y += 6
        return deferred

    def ensure(self, needed, continued_header):
        """Start a continued sheet when `needed` points don't fit."""
        if self.y + needed > PDF_BODY_BOTTOM:
            continued_header()

    def flow_lines(self, x, lines, leading, continued_header, offset=0.0, gutter=None):
        """Draw wrapped lines from the current y, cutting to a continued sheet
        at a line boundary whenever the body bottom is reached — the budgeted
        counterpart of _draw_lines, so a long value spills instead of running
        past the footer. `gutter(y)` draws the row's label or number beside
        the FIRST fragment only and returns its own bottom. Returns the bottom
        of the last fragment; self.y is left at that bottom."""
        rest, bottom = list(lines), self.y + offset
        while rest:
            if PDF_BODY_BOTTOM - (self.y + offset) < leading:
                continued_header()
            fits = max(1, int((PDF_BODY_BOTTOM - (self.y + offset)) // leading))
            start = self.y
            bottom = self._draw_lines(x, rest[:fits], leading, y=start + offset)
            if gutter is not None:
                bottom = max(bottom, gutter(start))
                gutter = None
            rest = rest[fits:]
            self.y = bottom
        return bottom


# -- vector logo ---------------------------------------------------------------
#
# The artifact's logo is an SVG (LOGO_B64, two filled paths). PDF cannot embed
# SVG, but its content streams speak the same vector primitives, so the path
# data is translated 1:1 into PDF operators — the built-in engine renders the
# real wordmark, not a text stand-in, still with zero dependencies. Any path
# command outside the supported set (a future logo swap with arcs, say) makes
# the parser bail and the header falls back to the text wordmark.


def _svg_path_to_pdf_ops(d):
    """SVG path data → PDF path operators, or None on unsupported commands."""
    tokens = re.findall(r"[A-Za-z]|-?\d*\.?\d+(?:[eE][-+]?\d+)?", d)
    ops = []
    index = 0
    cmd = None
    cx = cy = sx = sy = 0.0

    def num():
        nonlocal index
        value = float(tokens[index])
        index += 1
        return value

    while index < len(tokens):
        token = tokens[index]
        if token.isalpha():
            cmd = token
            index += 1
            if cmd in "Zz":
                ops.append("h")
                cx, cy = sx, sy
                cmd = None
            continue
        if cmd is None:
            return None
        relative = cmd.islower()
        base_x, base_y = (cx, cy) if relative else (0.0, 0.0)
        letter = cmd.upper()
        if letter == "M":
            cx, cy = base_x + num(), base_y + num()
            sx, sy = cx, cy
            ops.append(f"{cx:.3f} {cy:.3f} m")
            cmd = "l" if relative else "L"  # implicit lineto after moveto
        elif letter == "L":
            cx, cy = base_x + num(), base_y + num()
            ops.append(f"{cx:.3f} {cy:.3f} l")
        elif letter == "H":
            cx = base_x + num()
            ops.append(f"{cx:.3f} {cy:.3f} l")
        elif letter == "V":
            cy = base_y + num()
            ops.append(f"{cx:.3f} {cy:.3f} l")
        elif letter == "C":
            x1, y1 = base_x + num(), base_y + num()
            x2, y2 = base_x + num(), base_y + num()
            cx, cy = base_x + num(), base_y + num()
            ops.append(f"{x1:.3f} {y1:.3f} {x2:.3f} {y2:.3f} {cx:.3f} {cy:.3f} c")
        else:  # arcs, quadratics, smooth curves — not needed by our logo
            return None
    return " ".join(ops)


def _css_fill_rgb(fill):
    named = {"black": (0.0, 0.0, 0.0), "white": (1.0, 1.0, 1.0)}
    if fill in named:
        return named[fill]
    match = re.fullmatch(r"#([0-9a-fA-F]{6})", fill)
    if match:
        raw = match.group(1)
        return tuple(int(raw[i : i + 2], 16) / 255.0 for i in (0, 2, 4))
    return INK


_LOGO_VECTOR = None  # lazy cache: (viewbox_w, viewbox_h, [(ops, rgb)]) | False


def _svg_attr(tag, name):
    """One attribute of an SVG start tag. Attribute order and quote style are
    an exporter's choice, never a contract — assuming either would half-draw a
    reordered logo instead of falling back."""
    match = re.search(r'\b%s\s*=\s*(["\'])(.*?)\1' % name, tag, re.S)
    return match.group(2) if match else None


def logo_vector():
    global _LOGO_VECTOR
    if _LOGO_VECTOR is None:
        try:
            svg = base64.b64decode(LOGO_B64).decode("utf-8", "replace")
            _x0, _y0, vb_w, vb_h = (
                float(v) for v in _svg_attr(svg, "viewBox").split()
            )
            paths = []
            for tag in re.findall(r"<path\b[^>]*>", svg, re.S):
                pdf_ops = _svg_path_to_pdf_ops(_svg_attr(tag, "d") or "")
                if not pdf_ops:
                    raise ValueError("unsupported SVG path command")
                paths.append((pdf_ops, _css_fill_rgb(_svg_attr(tag, "fill") or "black")))
            # all or nothing: a partially understood logo would draw as a
            # mutilated wordmark, which is worse than the text stand-in
            if not paths or len(paths) != svg.count("<path"):
                raise ValueError("logo SVG only partially parsed")
            _LOGO_VECTOR = (vb_w, vb_h, paths)
        except Exception:
            _LOGO_VECTOR = False  # header falls back to the text wordmark
    return _LOGO_VECTOR or None


def _label_col_lines(text):
    """A band/row label wrapped inside the 36mm label column — long
    methodology labels (e.g. "Team Strategic Ambition") must never run into
    the value column."""
    return wrap_segments([(text.upper(), 8, "b", BRAND_DARK)], LABEL_COL - 4)


def _op_kicker_segs(op):
    segs = [(_plain("kicker", op["level"]), 8, "b", BRAND_DARK)]
    if op["parent_title"]:
        segs.append((_plain("cascades_from", op["parent_title"]), 8, "b", BRAND_DARK))
    return segs


def _proposed_entry_segs(entry):
    """One Proposed-content line as rich segments — the built-in mirror of the
    HTML <li>: the semibold element label, the truncated statement, then the
    marker's note, parenthesised, in italics. The page title is the group's
    subheading here too, never part of the line."""
    _page_key, _page_title, label, clean, note = entry
    # GRAY, not GRAY_MID: the HTML sets .gap-proposed-item to #4B5563 and keeps
    # #6B7280 for the quieter count and overflow lines — the two print surfaces
    # had drifted onto the lighter grey for the statement itself.
    segs = [("%s: " % label, 9, "b", AMBER_DARK), (truncate(clean), 9, "", GRAY)]
    note = truncate(note)
    if note:
        segs.append((" (%s)" % note, 8.5, "i", AMBER_DARK))
    return segs


def _value_segs(value, size, color):
    """('text', clean) | ('gap',) into rich segments."""
    if value[0] == "gap":
        return [(_plain("gap_missing"), size, "i", AMBER)]
    return [(value[1], size, "", color)]


def _text_block(lines, leading, indent=0, spacing=2.5, bullet=None):
    """A wrapped text block as (height, draw, split) — the pillar paginator's
    unit. `split(budget)` cuts the block at a line boundary into (head, tail),
    at least one line each, so a block taller than the remaining column budget
    spills onto the next sheet instead of being drawn past the page bottom;
    None when the block cannot be cut (a single line)."""
    h = len(lines) * leading + spacing

    def draw(pdf, x, y):
        line_y = y
        for index, line in enumerate(lines):
            line_y += leading
            if bullet and index == 0:
                pdf.text(
                    x + indent - PDF_LIST_INDENT,
                    line_y + PDF_BULLET_DROP,
                    [(bullet, PDF_BULLET_SIZE, "", BRAND)],
                )
            pdf.text(x + indent, line_y, line)

    def split(budget):
        take = max(1, int((budget - spacing) // leading))
        if take >= len(lines):
            return None
        # the bullet marks the item, so it belongs to the first fragment only
        return (
            _text_block(lines[:take], leading, indent, spacing, bullet),
            _text_block(lines[take:], leading, indent, spacing, None),
        )

    return (h, draw, split)


def _block_min_h(block):
    """The height that makes progress on a block: one line of a splittable
    text block, the whole block for the unsplittable name bar."""
    h, _draw, split = block
    fragment = split(0.0) if split else None
    return fragment[0][0] if fragment else h


def _pillar_blocks(pillar_title, parts, cell_w):
    """A pillar as (height, draw(x, y), split) blocks — the pagination unit.
    The first block is the name bar; it repeats on continued sheets and never
    splits."""
    blocks = []
    name_lines = wrap_segments([(pillar_title, 10.5, "b", INK)], cell_w - 12)
    bar_h = 8 + len(name_lines) * 13 + 5

    def draw_bar(pdf, x, y, h=bar_h, lines=name_lines):
        pdf.rect(x, y, cell_w, 2.2, fill=BRAND)
        pdf.rect(x, y + 2.2, cell_w, h - 2.2, fill=BAR_BG)
        line_y = y + 4
        for line in lines:
            line_y += 13
            pdf.text(x + 6, line_y, line)

    blocks.append((bar_h + 4, draw_bar, None))

    def add_text_block(lines, leading, indent=0, spacing=2.5, bullet=None):
        blocks.append(_text_block(lines, leading, indent, spacing, bullet))

    def walk(parts, depth):
        indent = 6 + depth * 9
        for kind, label, payload in parts:
            if kind == "row":
                rich = [(label.upper() + "  ", 7.5, "b", BRAND_DARK)] + _value_segs(
                    payload, 8.5, INK
                )
                add_text_block(wrap_segments(rich, cell_w - indent - 6), 11.2, indent)
            else:  # initiative
                name_rich = [(label, 8.5, "b", INK)] if label else []
                if name_rich:
                    add_text_block(
                        wrap_segments(name_rich, cell_w - indent - PDF_LIST_INDENT - 6),
                        11.2,
                        indent + PDF_LIST_INDENT,
                        spacing=1.5,
                        bullet="•",
                    )
                walk(payload, depth + 2)
    walk(parts, 0)
    return blocks


def _render_pillar_band(layout, band_label, pillars, continued_header):
    pdf = layout.pdf
    cols = grid_columns(len(pillars))
    cell_w = (VALUE_W - CELL_GAP * (cols - 1)) / cols

    band_chunk = 0
    labeled_pages = set()
    for row_start in range(0, len(pillars), cols):
        group = []
        for pillar_title, parts in pillars[row_start : row_start + cols]:
            blocks = _pillar_blocks(pillar_title, parts, cell_w)
            # blocks[0] is the name bar — keep it aside so continuation
            # sheets can repeat the bar and advance by its true height
            bar_h, bar_draw, _split = blocks[0]
            group.append({"blocks": blocks, "bar": bar_draw, "bar_h": bar_h, "started": False})

        while any(g["blocks"] for g in group):
            # a sheet must fit the smallest fragment that makes progress — a
            # repeated name bar plus one line — not whole blocks: taking the
            # max of whole blocks broke the row group onto a fresh sheet
            # whenever ONE column's next block was tall, leaving the rest of
            # the sheet blank.
            min_h = max(
                (g["bar_h"] if g["started"] else 0.0) + _block_min_h(g["blocks"][0])
                for g in group
                if g["blocks"]
            )
            layout.ensure(min_h + 16, continued_header)
            page_index = len(pdf.pages)
            label_h = 0.0
            if page_index not in labeled_pages:
                label = band_label if band_chunk == 0 else "%s — %s" % (band_label, _plain("gap_continued"))
                label_lines = _label_col_lines(label)
                layout._draw_lines(PDF_MARGIN_X, label_lines, 10, y=layout.y - 2)
                labeled_pages.add(page_index)
                label_h = len(label_lines) * 10
            budget = PDF_BODY_BOTTOM - layout.y
            tallest = 0.0
            taken = 0
            for index, g in enumerate(group):
                if not g["blocks"]:
                    continue
                # measure the sheet's worth of blocks before drawing any: a
                # column that contributes nothing here must not emit a
                # repeated name bar with no content under it
                #
                # A repeated bar that cannot fit beside even one line of prose
                # is dropped for this sheet instead: repeating it would make
                # `budget - used` negative, and then every block — splittable
                # prose included — would fail to split and fall through to the
                # unsplit backstop below. The pillar keeps the bar it started
                # with, oversized, where it started.
                repeat_bar = (
                    g["started"]
                    and g["bar_h"] + _block_min_h(g["blocks"][0]) <= budget
                )
                used = g["bar_h"] if repeat_bar else 0.0
                take = []
                while g["blocks"]:
                    h, draw, split = g["blocks"][0]
                    if h <= budget - used:
                        g["blocks"].pop(0)
                    else:
                        fragment = split(budget - used) if split else None
                        if fragment is None or fragment[0][0] > budget - used:
                            break  # the block continues on the next sheet
                        head, tail = fragment
                        g["blocks"][0] = tail
                        h, draw, _split = head
                    take.append((h, draw))
                    used += h
                if not take:
                    continue
                x = VALUE_X + index * (cell_w + CELL_GAP)
                y = layout.y
                if repeat_bar:
                    g["bar"](pdf, x, y)  # repeated name bar above the rest
                    y += g["bar_h"]
                for h, draw in take:
                    draw(pdf, x, y)
                    y += h
                g["started"] = True
                taken += len(take)
                tallest = max(tallest, used)
            if not taken:
                # Nothing fit an otherwise empty sheet: only an unsplittable
                # name bar taller than a whole page reaches here. Draw it
                # anyway rather than loop forever on a sheet it can never fit.
                for index, g in enumerate(group):
                    if g["blocks"]:
                        h, draw, _split = g["blocks"].pop(0)
                        draw(pdf, VALUE_X + index * (cell_w + CELL_GAP), layout.y)
                        g["started"] = True
                        tallest = max(tallest, h)
            layout.y += max(tallest, label_h) + 8
            band_chunk += 1


def _render_one_pager_pdf(layout, op, banner):
    ambition_segs = _value_segs(op["ambition"], 10, GRAY) if op["ambition"] else None
    bannered = set()

    def draw_banner():
        # the body's first line on every sheet of this page — sheets print and
        # travel separately, so each states the cascade's draft status itself.
        # Guarded per sheet: a deferred ambition can route through
        # continued_header, which already banners the sheet it opens.
        if not banner or len(layout.pdf.pages) in bannered:
            return
        bannered.add(len(layout.pdf.pages))
        lines = wrap_segments([(banner, 7.5, "", AMBER_DARK)], layout.content_width())
        layout.y = layout._draw_lines(PDF_MARGIN_X, lines, 10) + 6

    def continued_header():
        # the compact header: a continuation sheet repeats the title only, so
        # it always leaves the body room to make progress
        layout.sheet_header(
            _op_kicker_segs(op),
            "%s — %s" % (op["title"], _plain("gap_continued")),
            None,
        )
        draw_banner()

    def full_header():
        deferred = layout.sheet_header(_op_kicker_segs(op), op["title"], ambition_segs)
        draw_banner()
        # an ambition too long for the header continues in the body, through
        # the same budgeted flow the core strip uses
        for x, lines, leading in deferred:
            layout.y = layout.flow_lines(x, lines, leading, continued_header) + 2

    full_header()

    # Core statement strip. The value flows line by line onto continued
    # sheets — a long mission is common enough that a single ensure() would
    # simply have drawn it off the bottom of the page.
    for label, value in op["core"]:
        segs = _value_segs(value, 9.5, INK)
        label_lines = _label_col_lines(label)
        layout.ensure(max(12.4, len(label_lines) * 10) + 4, continued_header)
        layout.y = (
            layout.flow_lines(
                VALUE_X,
                wrap_segments(segs, VALUE_W),
                12.4,
                continued_header,
                offset=-2,
                gutter=lambda y, lines=label_lines: layout._draw_lines(
                    PDF_MARGIN_X, lines, 10, y=y
                ),
            )
            + 2
        )
        layout.y += 4
    if op["core"]:
        layout.y += 2
        layout.pdf.line(PDF_MARGIN_X, layout.y, PDF_PAGE_W - PDF_MARGIN_X, layout.y, LINE)
        layout.y += 8

    for band_label, pillars in op["pillar_bands"]:
        _render_pillar_band(layout, band_label, pillars, continued_header)

    # chip bands (enablers / values)
    for band_label, chips in op["chip_bands"]:
        chip_h = 15
        rows = [[]]
        used = 0.0
        for clean in chips:
            # measure exactly the text drawn below, so the chip box fits
            w = text_width(clean, 8.5) + 14
            if rows[-1] and used + w + 5 > VALUE_W:
                rows.append([])
                used = 0.0
            rows[-1].append((clean, w))
            used += w + 5
        # Chip ROWS flow against the page budget, like the pillar band's
        # blocks: `maxItems: 100` on enablers/values is enough for a band
        # taller than the whole sheet, and a band drawn in one go would run
        # every row past that point under the footer. A single row is 19pt, so
        # row granularity is enough — nothing has to split inside a row.
        row_h = chip_h + 4
        rest, chunk = rows, 0
        while rest:
            label = (
                band_label if chunk == 0
                else "%s — %s" % (band_label, _plain("gap_continued"))
            )
            label_lines = _label_col_lines(label)
            label_h = 2 + len(label_lines) * 10
            # the whole remainder still asks for a fresh sheet first (a band
            # that fits stays whole, as before); what a sheet cannot hold
            # continues under the repeated label
            layout.ensure(max(len(rest) * row_h, label_h) + 8, continued_header)
            fits = max(1, int((PDF_BODY_BOTTOM - layout.y) // row_h))
            layout._draw_lines(PDF_MARGIN_X, label_lines, 10, y=layout.y + 2)
            band_top = layout.y
            for row in rest[:fits]:
                x = VALUE_X
                for clean, w in row:
                    layout.pdf.rect(x, layout.y + 2, w, chip_h, fill=BAR_BG, stroke=LINE, line_w=0.5)
                    layout.pdf.text(x + 7, layout.y + 12.5, [(clean, 8.5, "", INK)])
                    x += w + 5
                layout.y += row_h
            rest = rest[fits:]
            # a two-line band label outruns a single chip row — advance by
            # whichever side is taller, as the core strip does
            layout.y = max(layout.y, band_top + label_h) + 6
            chunk += 1


def _render_gap_report_pdf(layout, bundle, gaps, proposed):
    questions = bundle.get("openQuestions") or []
    company = bundle.get("company", {}).get("name", "")

    with_target, total_goals = gap_stats(bundle)
    total_items = len(questions) + len(gaps)

    def header(continued):
        title = _plain_plural("gap_title", total_items)
        if continued:
            title += " — %s" % _plain("gap_continued")
        # the subtitle rides the first sheet only, like the one-pager's
        # ambition — a continued sheet keeps its whole body for the list
        deferred = layout.sheet_header(
            [(_plain("gap_kicker").upper(), 8, "b", AMBER)],
            title,
            None if continued else [(_plain("gap_subtitle", company), 9.5, "", GRAY)],
        )
        for x, lines, leading in deferred:
            layout.y = layout.flow_lines(x, lines, leading, continued_header) + 2

    def continued_header():
        header(True)

    header(False)

    # stats strip
    stat_w = (layout.content_width() - 2 * COL_GAP) / 3
    # The two counted labels carry no markup and no %d — the figure is drawn
    # above them at 24pt — so the count only selects the form.
    stats = [
        ("%d/%d" % (with_target, total_goals), _plain("stat_targets")),
        (str(len(questions)), plural_form("stat_questions", len(questions))),
        (str(len(gaps)), plural_form("stat_missing", len(gaps))),
    ]
    stat_h = 58
    for index, (number, label) in enumerate(stats):
        x = PDF_MARGIN_X + index * (stat_w + COL_GAP)
        layout.pdf.rect(x, layout.y, stat_w, stat_h, stroke=LINE, line_w=0.8)
        layout.pdf.text(x + 12, layout.y + 30, [(number, 24, "b", AMBER)])
        label_lines = wrap_segments([(label, 8.5, "", GRAY_MID)], stat_w - 24)
        layout._draw_lines(x + 12, label_lines, 10, y=layout.y + 34)
    layout.y += stat_h + 14

    # Numbered list, then the CTA hero on (or after) the last sheet. Items
    # flow line by line: an open question long enough to outgrow the sheet
    # must continue overleaf, never disappear under the footer.
    list_x = PDF_MARGIN_X + 26
    list_w = layout.content_width() - 60
    # The number's gutter, not an arbitrary offset: the HTML artifact sets a
    # `1.` 5.7mm left of its question, and 22pt (7.8mm) stranded the marker far
    # enough from its text that the two stopped reading as one item. Only the
    # number moves — list_x is untouched, so no wrap width and no sheet budget
    # on this page changes. The marker is right-aligned to end 4pt short of the
    # text column and grows leftward into the margin, so a hundredth item
    # ("100." is 19.5pt at 10pt bold, wider than any fixed gutter worth having)
    # still cannot overprint its question.
    number_gutter_end_x = list_x - 4
    for number, (text, is_statement_gap) in enumerate(
        [(q, False) for q in questions] + [(g, True) for g in gaps], start=1
    ):
        color = GRAY_MID if is_statement_gap else INK
        lines = wrap_segments([(text, 10, "", color)], list_w)
        layout.ensure(20, continued_header)  # the number stays with line one

        def number_gutter(y, number=number):
            marker = "%d." % number
            layout.pdf.text(
                number_gutter_end_x - text_width(marker, 10, True),
                y + 13,
                [(marker, 10, "b", AMBER)],
            )
            return y + 13

        layout.y = (
            layout.flow_lines(list_x, lines, 13, continued_header, gutter=number_gutter) + 7
        )

    # Proposed content: every [PROPOSED]-marked statement, once, on the page
    # the draft banner points at — the HTML artifact's section, same grouping,
    # same order and same wording, flowing against the same sheet budget.
    if proposed:
        count_lines = wrap_segments(
            # the counted phrases carry no markup, so the HTML-stripping
            # _plain() detour the other chrome strings need does not apply
            [(proposed_count_line(proposed), 9, "", GRAY_MID)],
            layout.content_width(),
        )
        groups = [
            (
                wrap_segments([(page_title, 10, "b", INK)], layout.content_width()),
                [
                    wrap_segments(_proposed_entry_segs(entry), layout.content_width())
                    for entry in group
                ],
            )
            for page_title, group in proposed_groups(proposed)
        ]

        # A block reserves the first thing that must follow it — a heading or
        # a page subheading alone at the foot of a sheet reads as a section
        # with nothing in it (the HTML side reserves the same thing in mm).
        # The arithmetic is exactly what the drawing code below spends: 13pt
        # per subheading line, +4pt after; 11.5pt per entry line, +3pt after.
        def group_head_h(sub_lines, entry_lines):
            return 13 * len(sub_lines) + 4 + 11.5 * len(entry_lines[0]) + 3

        # 6pt lead-in + 17pt heading line + the count block (11pt per line,
        # +5pt after), then the first group's own reservation.
        head_h = 6 + 17 + 11 * len(count_lines) + 5
        layout.ensure(head_h + group_head_h(*groups[0]), continued_header)
        layout.y += 6
        layout.pdf.text(
            PDF_MARGIN_X, layout.y + 13, [(_plain("proposed_heading"), 12, "b", AMBER_DARK)]
        )
        layout.y += 17
        layout.y = layout._draw_lines(PDF_MARGIN_X, count_lines, 11) + 5
        for sub_lines, entry_lines in groups:
            layout.ensure(group_head_h(sub_lines, entry_lines), continued_header)
            layout.y = layout._draw_lines(PDF_MARGIN_X, sub_lines, 13) + 4
            for lines in entry_lines:
                layout.ensure(14, continued_header)
                layout.y = layout.flow_lines(PDF_MARGIN_X, lines, 11.5, continued_header) + 3

    # Sources: what the cascade was built from — the HTML artifact's closing
    # block, same list, same cap and same overflow line, against this surface's
    # own budget. The counted overflow phrase carries no markup, so it needs no
    # _plain() detour; the heading, being a chrome string, does.
    shown, more = source_lines(bundle)
    if shown:
        # .gap-sources-item is #4B5563 (GRAY); only the "+N more" overflow line
        # drops to the quieter #6B7280 italic, exactly as the HTML and the DOCX
        # writer have it.
        source_entries = [
            wrap_segments([(line, 9.5, "", GRAY)], layout.content_width())
            for line in shown
        ]
        if more:
            source_entries.append(
                wrap_segments([(more, 9.5, "i", GRAY_MID)], layout.content_width())
            )
        # 6pt lead-in + 17pt heading line, then the first entry the heading
        # reserves (11.5pt per line, +3pt after) — the same arithmetic the
        # Proposed-content block above spends, and exactly what is drawn below.
        layout.ensure(6 + 17 + 11.5 * len(source_entries[0]) + 3, continued_header)
        layout.y += 6
        layout.pdf.text(PDF_MARGIN_X, layout.y + 13, [(_plain("sources_heading"), 12, "b", INK)])
        layout.y += 17
        for lines in source_entries:
            layout.ensure(14, continued_header)
            layout.y = layout.flow_lines(PDF_MARGIN_X, lines, 11.5, continued_header) + 3

    # Copy only, no host: the footer pill on this same sheet already carries
    # `title → try.alaigned.com`, and the hero repeating it turns one
    # invitation into two ads. The heading stays the link.
    cta_title = _plain("cta_title")
    body_lines = wrap_segments([(_plain("cta_body"), 9.5, "", INK)], layout.content_width() - 90)
    close_lines = wrap_segments([(_plain("cta_close"), 9.5, "b", INK)], layout.content_width() - 90)
    wl_lines = wrap_segments([(_plain("cta_whitelabel"), 8.5, "", BRAND_DARK)], layout.content_width() - 90)
    hero_h = 30 + (len(body_lines) + len(close_lines)) * 12.5 + len(wl_lines) * 11 + 26
    layout.ensure(hero_h + 6, continued_header)
    hero_y = layout.y + 4
    layout.pdf.rect(PDF_MARGIN_X, hero_y, layout.content_width(), hero_h, fill=CTA_BG, stroke=BRAND, line_w=1.2)
    tx = PDF_MARGIN_X + 22
    ty = hero_y + 26
    layout.pdf.text(tx, ty, [(cta_title, 15, "b", BRAND_DARK)])
    layout.pdf.link(tx, ty - 14, text_width(cta_title, 15, True), 18, CTA_HREF)
    ty += 8
    ty = layout._draw_lines(tx, body_lines, 12.5, y=ty)
    ty += 3
    ty = layout._draw_lines(tx, close_lines, 12.5, y=ty)
    ty += 3
    layout._draw_lines(tx, wl_lines, 11, y=ty)
    layout.y = hero_y + hero_h


def render_builtin_pdf(bundle, pdf_path, only_op=None):
    """Tier-3 --pdf engine: bundle → real PDF, no external tools. Page order
    mirrors the HTML artifact (root, gap report, teams); with only_op set it
    renders that single one-pager (--split sheets, no gap page)."""
    if not bundle.get("onePagers"):
        # a clean signal for the caller's fallback message — the layout below
        # assumes a root one-pager and would die on an index instead
        raise ValueError("bundle has no onePagers")
    company = bundle.get("company", {}).get("name", "Strategy")
    generated_at = bundle.get("generator", {}).get("generatedAt", "")
    by_ref = {op["ref"]: op for op in bundle["onePagers"]}

    gaps = []
    source_ops = [only_op] if only_op is not None else bundle["onePagers"]
    extracted = [_pdf_extract_op(op, by_ref, gaps) for op in source_ops]

    # Bundle-scoped like the HTML artifact's, so a --split sheet carries the
    # cascade's draft status too — with the shortened wording, since the Gap
    # Report page it would otherwise point at does not travel with it.
    proposed = proposed_entries(bundle)
    banner = draft_banner_text(proposed, standalone=only_op is not None)

    writer = PdfWriter(html.unescape(S["doc_title"] % company))
    layout = BuiltinLayout(writer, generated_at)

    _render_one_pager_pdf(layout, extracted[0], banner)
    if only_op is None:
        # the HTML collects statement gaps from every page before the gap
        # report renders — extraction above already walked all of them
        _render_gap_report_pdf(layout, bundle, gaps, proposed)
    for op in extracted[1:]:
        _render_one_pager_pdf(layout, op, banner)

    writer.save(pdf_path)
    return "builtin"


# --- built-in DOCX writer -----------------------------------------------------
#
# The editable twin of the printable artifact: one hand-authored OOXML package
# (stdlib `zipfile` + string-assembled XML, no packages, no converters) built
# from the same validated bundle and the same extraction layer the built-in PDF
# engine uses. There is no engine ladder here and no `--docx-engine` flag —
# pandoc/LibreOffice would degrade this design rather than improve it, and
# neither is dependably present. Google Docs has no format of its own, so this
# file is also the Google Doc: uploading it to Drive with convert-on-upload
# opens it as a native Doc.
#
# What it deliberately does NOT do: pagination. Word owns page breaking, so the
# writer emits one A4-landscape SECTION per one-pager plus one for the Gap
# Report (same order as the HTML/PDF: root, Gap Report, teams) and lets long
# content flow. None of the PDF engine's mm-estimation machinery is ported.
#
# Everything is direct run/paragraph formatting over a minimal styles.xml —
# no named-style system to keep in sync with the print design. UTF-8 native:
# the arrow in the CTA stays a real arrow and diacritics need no glyph table,
# which is the one place this surface is simpler than the PDF writer.

# A4 landscape in twips (1/1440 inch), mirroring the print geometry: 297x210mm,
# 12mm side padding, the 36mm label column.
DOCX_PAGE_W = 16838
DOCX_PAGE_H = 11906
DOCX_MARGIN_X = 680  # 12mm
DOCX_MARGIN_TOP = 680  # 12mm — clears the 4mm brand stripe drawn as a page border
DOCX_MARGIN_BOTTOM = 851  # 15mm, so the footer line never crowds the body
DOCX_CONTENT_W = DOCX_PAGE_W - 2 * DOCX_MARGIN_X
DOCX_LABEL_COL = 2041  # 36mm
DOCX_VALUE_COL = DOCX_CONTENT_W - DOCX_LABEL_COL
DOCX_LOGO_COL = 2600  # the 40mm wordmark plus its breathing room
DOCX_GUTTER = 227  # 4mm, the stats strip's inter-cell gap
DOCX_CELL_PAD = 142  # 2.5mm, the pillar cell's own padding
DOCX_TAB_RIGHT = DOCX_CONTENT_W  # the footer's right-aligned date tab stop
# List geometry, in twips. Word left-aligns a marker at `left - hanging` and
# tabs the text to `left`, so `hanging` is literally the marker-to-text
# distance the HTML artifact shows: 4mm under a pillar bullet, 5mm under a Gap
# Report number (measured off the Chromium render). Only the whole-list offset
# differs from the print surfaces — 1mm for the bullet, so the list stops
# sitting flush under the label above it and reads as a list in Word, which
# has neither the print sheet's density nor its column rules to make that
# obvious. The 2.5mm the numbered list carries is the HTML marker's own
# position; its 8mm predecessor left the number stranded a centimetre from its
# question.
DOCX_BULLET_INDENT = 283  # 5mm to the initiative text
DOCX_BULLET_HANGING = 227  # 4mm back to the bullet
DOCX_NUMBER_INDENT = 425  # 7.5mm to the question text
DOCX_NUMBER_HANGING = 283  # 5mm back to the number
DOCX_LIST_ITEM_GAP = 57  # 1mm — .initiatives li { margin-bottom: 1mm }
DOCX_ROW_GAP = 34  # 0.6mm — .row { margin: 0.6mm 0 }
DOCX_GAP_ITEM_GAP = 170  # 3mm — .gap-list li { margin-bottom: 3mm }
EMU_PER_MM = 36000
DOCX_LOGO_MM = 40

# Relationship ids of word/document.xml (word/_rels/document.xml.rels). Fixed,
# not generated: the package has exactly these six parts to point at (styles
# rId1, numbering rId2, the font table rId6 — those three are referenced by the
# rels alone, so only the ids the body cites need constants).
DOCX_REL_FOOTER = "rId3"
DOCX_REL_LOGO = "rId4"
DOCX_REL_CTA = "rId5"
# The footer part has one relationship of its own — the same CTA href.
DOCX_FOOTER_REL_CTA = "rId1"

# The print palette as OOXML hex. Mapped rather than converted: the PDF
# constants store rounded floats, so converting them back drifts — BAR_BG's
# 0.955 lands on F4F4F4, a shade darker than the tint the HTML paints there
# (rgba(0,0,0,0.04) over white, i.e. ~#F5F5F5). The map pins each colour once
# and is the only place a DOCX colour may come from.
DOCX_HEX = {
    BRAND: "118E64",
    BRAND_DARK: "0A6447",
    INK: "232426",
    GRAY: "4B5563",
    GRAY_MID: "6B7280",
    GRAY_LIGHT: "9CA3AF",
    LINE: "E7EBEF",
    AMBER: "E48A1B",
    AMBER_DARK: "9A6700",
    BAR_BG: "F5F5F6",
    CTA_BG: "E8F7F1",
    WHITE: "FFFFFF",
}
DOCX_BANNER_BG = "FFF8E7"
DOCX_BANNER_BORDER = "E8D49A"

# Rasterized once at dev time from LOGO_B64 (the SVG the HTML artifact
# embeds) — DrawingML has no SVG part that Word and Google Docs both honor,
# and hand-built custom geometry risks a corrupt-document dialog, so the DOCX
# carries a transparent PNG image part instead. 712x216 px = the SVG's 178x54
# viewBox at 4x, placed 40mm wide. To regenerate:
#
#   python3 - <<'PY'
#   import base64, pathlib, subprocess, sys
#   sys.path.insert(0, "scripts")
#   import render_cascade as rc
#   svg = base64.b64decode(rc.LOGO_B64).decode()
#   svg = svg.replace('width="178" height="54"', 'width="712" height="216"', 1)
#   page = pathlib.Path("logo.html")
#   page.write_text('<!DOCTYPE html><meta charset="utf-8">'
#                   '<style>html,body{margin:0;background:transparent}svg{display:block}</style>' + svg)
#   subprocess.run([rc.find_chromium(), "--headless", "--screenshot=logo.png",
#                   "--window-size=712,216", "--default-background-color=00000000",
#                   "--hide-scrollbars", "--disable-gpu", page.resolve().as_uri()], check=True)
#   print(base64.b64encode(pathlib.Path("logo.png").read_bytes()).decode())
#   PY
#
# Empty it and the header falls back to a text wordmark, exactly as the PDF
# engine's vector parser does when it cannot read the SVG.
LOGO_PNG_B64 = "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"


# -- OOXML primitives ----------------------------------------------------------

# Control characters are legal inside a JSON string and illegal in XML 1.0 —
# a stray one in bundle prose would make Word reject the whole package.
_XML_CTRL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def _dx_esc(text):
    """Bundle text into XML character data."""
    return (
        _XML_CTRL.sub("", str(text))
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _dx_attr(value):
    """The same, for an attribute value (the CTA href, the document title)."""
    return _dx_esc(value).replace('"', "&quot;")


def _dx_hex(rgb):
    """A print-palette tuple as an OOXML RRGGBB. Map lookup only: a colour the
    map does not carry is a design that has drifted, and a silently converted
    float would ship it as a shade nobody chose — KeyError says it out loud."""
    return DOCX_HEX[rgb]


def _dx_run(text, size, style, rgb, caps=False, shade=None, border=None, spacing=None):
    """One `(text, size, style, rgb)` segment as a run. The rPr children are
    emitted in schema order (b, i, caps, color, spacing, sz, bdr, shd) — Word
    rejects a reordered property block. `caps` renders uppercase without
    uppercasing the text itself, so the document stays searchable in its own
    language (the print surfaces have to fold the text instead)."""
    props = []
    if "b" in style:
        props.append("<w:b/>")
    if "i" in style:
        props.append("<w:i/>")
    if caps:
        props.append("<w:caps/>")
    props.append('<w:color w:val="%s"/>' % _dx_hex(rgb))
    if spacing:
        props.append('<w:spacing w:val="%d"/>' % spacing)
    half = int(round(size * 2))
    props.append('<w:sz w:val="%d"/><w:szCs w:val="%d"/>' % (half, half))
    if border:
        props.append('<w:bdr w:val="single" w:sz="4" w:space="0" w:color="%s"/>' % border)
    if shade:
        props.append('<w:shd w:val="clear" w:color="auto" w:fill="%s"/>' % shade)
    return '<w:r><w:rPr>%s</w:rPr><w:t xml:space="preserve">%s</w:t></w:r>' % (
        "".join(props),
        _dx_esc(text),
    )


def _dx_runs(segments, **run_opts):
    """A whole segment list as runs — the same `(text, size, style, rgb)` model
    the PDF writer draws, which is why both surfaces share the extraction
    layer above."""
    return "".join(
        _dx_run(text, size, style, rgb, **run_opts)
        for text, size, style, rgb in segments
        if text
    )


def _dx_para(
    runs,
    indent=0,
    hanging=0,
    before=0,
    after=80,
    line=None,
    num_id=None,
    shade=None,
    border_left=None,
    align=None,
    keep_next=False,
):
    """One paragraph. pPr children are emitted in schema order (keepNext,
    numPr, pBdr, shd, spacing, ind, jc). `keep_next` is this surface's answer
    to the print engines' height reservations: Word does the arithmetic, it
    only has to be told that a heading belongs with what follows it."""
    props = []
    if keep_next:
        props.append("<w:keepNext/>")
    if num_id:
        props.append('<w:numPr><w:ilvl w:val="0"/><w:numId w:val="%d"/></w:numPr>' % num_id)
    if border_left:
        props.append(
            '<w:pBdr><w:left w:val="single" w:sz="12" w:space="6" w:color="%s"/></w:pBdr>'
            % border_left
        )
    if shade:
        props.append('<w:shd w:val="clear" w:color="auto" w:fill="%s"/>' % shade)
    spacing = '<w:spacing w:before="%d" w:after="%d"' % (before, after)
    spacing += (' w:line="%d" w:lineRule="auto"/>' % line) if line else "/>"
    props.append(spacing)
    if indent or hanging:
        props.append('<w:ind w:left="%d" w:hanging="%d"/>' % (indent, hanging))
    if align:
        props.append('<w:jc w:val="%s"/>' % align)
    return "<w:p><w:pPr>%s</w:pPr>%s</w:p>" % ("".join(props), runs)


def _dx_spacer():
    """The paragraph that has to follow every table: Word treats two adjacent
    tables as one and a table ending a section as a defect. Sized to a hairline
    so it reads as the gap the print design has there anyway."""
    return (
        '<w:p><w:pPr><w:spacing w:after="0" w:line="120" w:lineRule="exact"/>'
        '<w:rPr><w:sz w:val="10"/></w:rPr></w:pPr></w:p>'
    )


def _dx_margins(left=0, right=0, top=0, bottom=0):
    return (
        '<w:tcMar><w:top w:w="%d" w:type="dxa"/><w:left w:w="%d" w:type="dxa"/>'
        '<w:bottom w:w="%d" w:type="dxa"/><w:right w:w="%d" w:type="dxa"/></w:tcMar>'
        % (top, left, bottom, right)
    )


# CT_TcBorders fixes the order of its children; a caller listing the sides in
# any other order would emit a block Word rejects, so the emitter sorts them.
DOCX_BORDER_SIDES = ("top", "left", "bottom", "right")


def _dx_borders(sides, color, sz=4):
    return "<w:tcBorders>%s</w:tcBorders>" % "".join(
        '<w:%s w:val="single" w:sz="%d" w:space="0" w:color="%s"/>' % (side, sz, color)
        for side in DOCX_BORDER_SIDES
        if side in sides
    )


def _dx_cell(width, blocks, shade=None, borders="", margins=""):
    """One table cell. tcPr children in schema order (tcW, tcBorders, shd,
    tcMar); an empty cell still needs a paragraph."""
    props = ['<w:tcW w:w="%d" w:type="dxa"/>' % width]
    if borders:
        props.append(borders)
    if shade:
        props.append('<w:shd w:val="clear" w:color="auto" w:fill="%s"/>' % shade)
    if margins:
        props.append(margins)
    return "<w:tc><w:tcPr>%s</w:tcPr>%s</w:tc>" % ("".join(props), blocks or "<w:p/>")


def _dx_table(widths, rows):
    """A fixed-layout table — every band in this document is a grid whose
    column widths are the design, so autofit is never wanted."""
    return (
        "<w:tbl><w:tblPr>"
        '<w:tblW w:w="%d" w:type="dxa"/>'
        '<w:tblLayout w:type="fixed"/>'
        '<w:tblCellMar><w:top w:w="0" w:type="dxa"/><w:left w:w="0" w:type="dxa"/>'
        '<w:bottom w:w="0" w:type="dxa"/><w:right w:w="113" w:type="dxa"/></w:tblCellMar>'
        "</w:tblPr><w:tblGrid>%s</w:tblGrid>%s</w:tbl>%s"
        % (
            sum(widths),
            "".join('<w:gridCol w:w="%d"/>' % w for w in widths),
            "".join("<w:tr>%s</w:tr>" % row for row in rows),
            _dx_spacer(),
        )
    )


def _dx_hyperlink(runs, rel_id):
    return '<w:hyperlink r:id="%s">%s</w:hyperlink>' % (rel_id, runs)


def _dx_label_run(text):
    """A band / row / core-statement label in the 36mm column: 8pt caps in the
    dark brand green, the print design's accent label."""
    return _dx_run(text, 8, "b", BRAND_DARK, caps=True, spacing=12)


def _dx_logo(drawing_id):
    """The wordmark as an inline image part, 40mm wide at the SVG's aspect
    ratio. An empty LOGO_PNG_B64 falls back to a text wordmark, mirroring the
    PDF engine's own fallback."""
    if not LOGO_PNG_B64:
        return _dx_run("Alaigned", 13, "b", BRAND)
    cx = DOCX_LOGO_MM * EMU_PER_MM
    cy = int(round(cx * 54 / 178.0))
    return (
        "<w:r><w:drawing>"
        '<wp:inline distT="0" distB="0" distL="0" distR="0">'
        '<wp:extent cx="%d" cy="%d"/>'
        '<wp:effectExtent l="0" t="0" r="0" b="0"/>'
        '<wp:docPr id="%d" name="Alaigned logo %d" descr="Alaigned"/>'
        '<wp:cNvGraphicFramePr><a:graphicFrameLocks noChangeAspect="1"/></wp:cNvGraphicFramePr>'
        "<a:graphic><a:graphicData "
        'uri="http://schemas.openxmlformats.org/drawingml/2006/picture">'
        "<pic:pic><pic:nvPicPr>"
        '<pic:cNvPr id="%d" name="logo.png"/><pic:cNvPicPr/></pic:nvPicPr>'
        '<pic:blipFill><a:blip r:embed="%s"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill>'
        '<pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="%d" cy="%d"/></a:xfrm>'
        '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr>'
        "</pic:pic></a:graphicData></a:graphic></wp:inline></w:drawing></w:r>"
        % (cx, cy, drawing_id, drawing_id, drawing_id, DOCX_REL_LOGO, cx, cy)
    )


# -- sheet sections ------------------------------------------------------------


def _dx_sectpr():
    """One A4-landscape section, identical on every sheet. The 4mm brand
    stripe is a page border: `sz` counts eighths of a point, so 90 = 11.25pt =
    ~4mm, and `offsetFrom="page"` pins it to the paper edge the way the HTML
    stripe sits above the page padding."""
    return (
        "<w:sectPr>"
        '<w:footerReference w:type="default" r:id="%s"/>'
        '<w:type w:val="nextPage"/>'
        '<w:pgSz w:w="%d" w:h="%d" w:orient="landscape"/>'
        '<w:pgMar w:top="%d" w:right="%d" w:bottom="%d" w:left="%d" '
        'w:header="340" w:footer="397" w:gutter="0"/>'
        '<w:pgBorders w:offsetFrom="page">'
        '<w:top w:val="single" w:sz="90" w:space="0" w:color="%s"/>'
        "</w:pgBorders>"
        '<w:cols w:space="708"/><w:docGrid w:linePitch="360"/>'
        "</w:sectPr>"
        % (
            DOCX_REL_FOOTER,
            DOCX_PAGE_W,
            DOCX_PAGE_H,
            DOCX_MARGIN_TOP,
            DOCX_MARGIN_X,
            DOCX_MARGIN_BOTTOM,
            DOCX_MARGIN_X,
            _dx_hex(BRAND),
        )
    )


def _dx_header(kicker_segs, title, subtitle_segs, drawing_id):
    """The sheet header band: kicker, title and (one-pager) ambition or (gap
    report) subtitle on the left, the wordmark on the right, over the hairline
    the print design rules under it."""
    border = _dx_borders(("bottom",), _dx_hex(LINE))
    text = [_dx_para(_dx_runs(kicker_segs, caps=True, spacing=12), after=40)]
    text.append(_dx_para(_dx_run(title, 22, "b", INK), after=60, line=252))
    if subtitle_segs:
        text.append(_dx_para(_dx_runs(subtitle_segs), after=0))
    return _dx_table(
        [DOCX_CONTENT_W - DOCX_LOGO_COL, DOCX_LOGO_COL],
        [
            _dx_cell(
                DOCX_CONTENT_W - DOCX_LOGO_COL,
                "".join(text),
                borders=border,
                # the 10mm the print header keeps between the title and the
                # wordmark, so a long title never runs into the logo column
                margins=_dx_margins(right=567, bottom=113),
            )
            + _dx_cell(
                DOCX_LOGO_COL,
                _dx_para(_dx_logo(drawing_id), after=0, align="right"),
                borders=border,
                margins=_dx_margins(bottom=113),
            )
        ],
    )


def _dx_banner(text):
    """The one honesty line the cascade's one-pager sheets carry — the print
    artifact's shaded amber strip, same wording, same restraint."""
    return _dx_para(
        _dx_run(text, 8, "", AMBER_DARK),
        indent=113,
        before=40,
        after=160,
        shade=DOCX_BANNER_BG,
        border_left=DOCX_BANNER_BORDER,
    )


def _dx_core(core):
    """The strategy-context strip: accent labels in the 36mm column, values
    beside them."""
    rows = []
    for label, value in core:
        rows.append(
            _dx_cell(DOCX_LABEL_COL, _dx_para(_dx_label_run(label), after=60))
            + _dx_cell(
                DOCX_VALUE_COL, _dx_para(_dx_runs(_value_segs(value, 9.5, INK)), after=60)
            )
        )
    return _dx_table([DOCX_LABEL_COL, DOCX_VALUE_COL], rows) if rows else ""


def _dx_pillar_parts(parts, depth):
    """A pillar's body in template order: labeled rows as indented paragraphs,
    initiatives as real bullet-list items (numbering.xml's bullet abstract), so
    the reader can edit the list as a list instead of retyping a glyph.

    Word sums a paragraph's `before` with the previous one's `after` instead of
    collapsing them, which is what lets this reproduce the HTML's spacing
    exactly: 0.6mm between an initiative and its own GOAL row (`.row`'s margin)
    and 1.6mm before the next initiative (that margin plus the list item's
    own). The bullets used to carry 0.35mm of `after` and nothing else, so
    every item in a pillar ran into the next one."""
    blocks = []
    for kind, label, payload in parts:
        if kind == "row":
            runs = _dx_run(label + "  ", 7.5, "b", BRAND_DARK, caps=True, spacing=10)
            runs += _dx_runs(_value_segs(payload, 8.5, INK))
            blocks.append(_dx_para(runs, indent=depth * 397, after=DOCX_ROW_GAP))
        else:
            if label:
                blocks.append(
                    _dx_para(
                        _dx_run(label, 8.5, "b", INK),
                        indent=depth * 397 + DOCX_BULLET_INDENT,
                        hanging=DOCX_BULLET_HANGING,
                        before=DOCX_LIST_ITEM_GAP,
                        after=DOCX_ROW_GAP,
                        num_id=1,
                    )
                )
            blocks.extend(_dx_pillar_parts(payload, depth + 1))
    return blocks


def _dx_pillar_band(band_label, pillars):
    """One pillar band as a fixed grid: the label column, then `grid_columns(n)`
    pillar columns. Each row group is two table rows — the shaded name bar with
    its green top border, then the bodies — because a single cell cannot shade
    its heading without shading everything under it."""
    cols = grid_columns(len(pillars))
    cell_w = DOCX_VALUE_COL // cols
    widths = [DOCX_LABEL_COL] + [cell_w] * cols
    name_borders = _dx_borders(("top",), _dx_hex(BRAND), sz=24)
    pad = _dx_margins(left=DOCX_CELL_PAD, right=DOCX_CELL_PAD + 57, top=57, bottom=57)
    body_pad = _dx_margins(left=DOCX_CELL_PAD, right=DOCX_CELL_PAD + 57, top=57, bottom=113)

    rows = []
    for start in range(0, len(pillars), cols):
        group = pillars[start : start + cols]
        label = (
            band_label
            if start == 0
            else "%s — %s" % (band_label, _plain("gap_continued"))
        )
        names = [_dx_cell(DOCX_LABEL_COL, _dx_para(_dx_label_run(label), after=60))]
        bodies = [_dx_cell(DOCX_LABEL_COL, "")]
        for index in range(cols):
            if index < len(group):
                pillar_title, parts = group[index]
                names.append(
                    _dx_cell(
                        cell_w,
                        _dx_para(_dx_run(pillar_title, 11, "b", INK), after=0),
                        shade=_dx_hex(BAR_BG),
                        borders=name_borders,
                        margins=pad,
                    )
                )
                bodies.append(
                    _dx_cell(cell_w, "".join(_dx_pillar_parts(parts, 0)), margins=body_pad)
                )
            else:
                # the grid track still has to exist so the columns stay aligned
                names.append(_dx_cell(cell_w, ""))
                bodies.append(_dx_cell(cell_w, ""))
        # the shaded name bar is one line of design, never two half-sheets
        rows.append("<w:trPr><w:cantSplit/></w:trPr>" + "".join(names))
        rows.append("".join(bodies))
    return _dx_table(widths, rows)


def _dx_chip_band(band_label, chips):
    """Enablers / values as chips — shaded, bordered runs on one flowing line,
    the print artifact's chip row without a layout engine to place it."""
    runs = []
    for chip in chips:
        # non-breaking spaces are the chip's padding: a run border hugs its
        # glyphs, and OOXML has no per-run box padding
        runs.append(
            _dx_run(
                "\u00a0%s\u00a0" % chip,
                9,
                "",
                INK,
                shade=_dx_hex(BAR_BG),
                border=_dx_hex(LINE),
            )
        )
        runs.append(_dx_run("  ", 9, "", INK))
    return _dx_table(
        [DOCX_LABEL_COL, DOCX_VALUE_COL],
        [
            _dx_cell(DOCX_LABEL_COL, _dx_para(_dx_label_run(band_label), after=60))
            + _dx_cell(DOCX_VALUE_COL, _dx_para("".join(runs), after=60, line=312))
        ],
    )


def _dx_one_pager(op, banner, drawing_id):
    """One one-pager sheet as a section body."""
    blocks = [
        _dx_header(
            _op_kicker_segs(op),
            op["title"],
            _value_segs(op["ambition"], 10, GRAY) if op["ambition"] else None,
            drawing_id,
        )
    ]
    if banner:
        blocks.append(_dx_banner(banner))
    blocks.append(_dx_core(op["core"]))
    for band_label, pillars in op["pillar_bands"]:
        blocks.append(_dx_pillar_band(band_label, pillars))
    for band_label, chips in op["chip_bands"]:
        blocks.append(_dx_chip_band(band_label, chips))
    return "".join(blocks)


def _dx_stats(stats):
    """The Gap Report's three-number strip. Gutter columns, not cell margins:
    the stat boxes are bordered, and adjacent bordered cells would share an
    edge instead of standing apart."""
    stat_w = (DOCX_CONTENT_W - 2 * DOCX_GUTTER) // 3
    widths = [stat_w, DOCX_GUTTER, stat_w, DOCX_GUTTER, stat_w]
    widths[-1] = DOCX_CONTENT_W - sum(widths[:-1])
    borders = _dx_borders(("top", "left", "bottom", "right"), _dx_hex(LINE))
    pad = _dx_margins(left=227, right=227, top=170, bottom=170)
    cells = []
    for index, (number, label) in enumerate(stats):
        if index:
            cells.append(_dx_cell(DOCX_GUTTER, ""))
        cells.append(
            _dx_cell(
                widths[index * 2],
                _dx_para(_dx_run(number, 26, "b", AMBER), after=40, line=252)
                + _dx_para(_dx_run(label, 8.5, "", GRAY_MID), after=0),
                borders=borders,
                margins=pad,
            )
        )
    return _dx_table(widths, ["".join(cells)])


def _dx_cta_hero():
    """The Gap Report's closing hero — the CTA text verbatim from STRINGS, in
    the print design's tinted, brand-bordered box, its title the same link the
    footer carries.

    The heading is the copy alone: the footer of this very sheet spells the
    host out, so the hero repeating it would print the domain twice."""
    title = _plain("cta_title")
    body = (
        _dx_para(
            _dx_hyperlink(_dx_run(title, 17, "b", BRAND_DARK), DOCX_REL_CTA),
            after=120,
            line=252,
        )
        + _dx_para(_dx_run(_plain("cta_body"), 9.5, "", INK), after=120)
        + _dx_para(_dx_run(_plain("cta_close"), 9.5, "b", INK), after=120)
        + _dx_para(_dx_run(_plain("cta_whitelabel"), 8.5, "", BRAND_DARK), after=0)
    )
    return _dx_table(
        [DOCX_CONTENT_W],
        [
            _dx_cell(
                DOCX_CONTENT_W,
                body,
                shade=_dx_hex(CTA_BG),
                borders=_dx_borders(("top", "left", "bottom", "right"), _dx_hex(BRAND), sz=12),
                margins=_dx_margins(left=340, right=340, top=340, bottom=340),
            )
        ],
    )


def _dx_gap_report(bundle, gaps, proposed, drawing_id):
    """The Strategy Gap Report sheet: the same stats, the same numbered list,
    the same Proposed-content and Sources blocks the other two surfaces carry —
    derived from the same helpers, so the three cannot disagree."""
    questions = bundle.get("openQuestions") or []
    # The subtitle's fallback is the empty string, exactly as `gap_report_html`
    # and the PDF's gap sheet have it — a nameless bundle opens the line with a
    # dash rather than with a stand-in name. `render_docx` names the *document*
    # (a different field) and takes the HTML <title>'s "Strategy" fallback.
    company = bundle.get("company", {}).get("name", "")

    with_target, total_goals = gap_stats(bundle)
    total_items = len(questions) + len(gaps)

    blocks = [
        _dx_header(
            [(_plain("gap_kicker"), 8, "b", AMBER)],
            _plain_plural("gap_title", total_items),
            [(_plain("gap_subtitle", company), 10, "", GRAY)],
            drawing_id,
        ),
        # the two counted labels carry no %d — the figure is its own run above
        # them — so the count selects the form and nothing is interpolated
        _dx_stats(
            [
                ("%d/%d" % (with_target, total_goals), _plain("stat_targets")),
                (str(len(questions)), plural_form("stat_questions", len(questions))),
                (str(len(gaps)), plural_form("stat_missing", len(gaps))),
            ]
        ),
    ]

    for text, is_statement_gap in [(q, False) for q in questions] + [(g, True) for g in gaps]:
        blocks.append(
            _dx_para(
                _dx_run(text, 10.5, "", GRAY_MID if is_statement_gap else INK),
                indent=DOCX_NUMBER_INDENT,
                hanging=DOCX_NUMBER_HANGING,
                after=DOCX_GAP_ITEM_GAP,
                num_id=2,
            )
        )

    if proposed:
        blocks.append(
            _dx_para(
                _dx_run(_plain("proposed_heading"), 12, "b", AMBER_DARK),
                before=160,
                after=40,
                keep_next=True,
            )
        )
        # the counted phrases carry no markup, so they skip the _plain() detour
        blocks.append(
            _dx_para(
                _dx_run(proposed_count_line(proposed), 9, "", GRAY_MID), after=120, keep_next=True
            )
        )
        for page_title, group in proposed_groups(proposed):
            blocks.append(
                _dx_para(_dx_run(page_title, 10, "b", INK), before=120, after=60, keep_next=True)
            )
            for entry in group:
                blocks.append(_dx_para(_dx_runs(_proposed_entry_segs(entry)), after=80))

    shown, more = source_lines(bundle)
    if shown:
        blocks.append(
            _dx_para(
                _dx_run(_plain("sources_heading"), 12, "b", INK),
                before=160,
                after=60,
                keep_next=True,
            )
        )
        for line in shown:
            blocks.append(_dx_para(_dx_run(line, 9.5, "", GRAY), after=60))
        if more:
            blocks.append(_dx_para(_dx_run(more, 9.5, "i", GRAY_MID), after=60))

    blocks.append(_dx_cta_hero())
    return "".join(blocks)


# -- package assembly ----------------------------------------------------------

DOCX_XML_HEAD = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'

DOCX_W_NS = (
    'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
    'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"'
)
DOCX_DRAWING_NS = (
    ' xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"'
    ' xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"'
    ' xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture"'
)


def _dx_content_types():
    override = (
        '<Override PartName="/%s" ContentType="application/vnd.openxmlformats-%s"/>'
    )
    return DOCX_XML_HEAD + (
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" '
        'ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Default Extension="png" ContentType="image/png"/>'
        + override % ("word/document.xml", "officedocument.wordprocessingml.document.main+xml")
        + override % ("word/styles.xml", "officedocument.wordprocessingml.styles+xml")
        + override % ("word/numbering.xml", "officedocument.wordprocessingml.numbering+xml")
        + override % ("word/fontTable.xml", "officedocument.wordprocessingml.fontTable+xml")
        + override % ("word/footer1.xml", "officedocument.wordprocessingml.footer+xml")
        + override % ("docProps/core.xml", "package.core-properties+xml")
        + override % ("docProps/app.xml", "officedocument.extended-properties+xml")
        + "</Types>"
    )


def _dx_rels(entries):
    body = "".join(
        '<Relationship Id="%s" Type="http://schemas.openxmlformats.org/%s" '
        'Target="%s"%s/>' % (rel_id, rel_type, target, mode)
        for rel_id, rel_type, target, mode in entries
    )
    return DOCX_XML_HEAD + (
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        "%s</Relationships>" % body
    )


def _dx_styles():
    """One default style, everything else direct formatting: the print design
    has no named-style system to mirror, and a half-built one would only drift.
    Word substitutes for 'Host Grotesk' where the brand font is not installed —
    `word/fontTable.xml` tells it what to substitute with."""
    return DOCX_XML_HEAD + (
        "<w:styles %s>"
        "<w:docDefaults><w:rPrDefault><w:rPr>"
        '<w:rFonts w:ascii="Host Grotesk" w:hAnsi="Host Grotesk" w:cs="Host Grotesk"/>'
        '<w:color w:val="%s"/><w:sz w:val="19"/><w:szCs w:val="19"/>'
        "</w:rPr></w:rPrDefault>"
        "<w:pPrDefault><w:pPr>"
        '<w:spacing w:after="80" w:line="288" w:lineRule="auto"/>'
        "</w:pPr></w:pPrDefault></w:docDefaults>"
        '<w:style w:type="paragraph" w:default="1" w:styleId="Normal">'
        '<w:name w:val="Normal"/><w:qFormat/></w:style>'
        "</w:styles>" % (DOCX_W_NS, _dx_hex(INK))
    )


def _dx_font_table():
    """The substitution hint for the brand face. `rFonts` alone only names
    'Host Grotesk'; on a machine without it — nearly every machine — Word picks
    the substitute on its own and can land on a serif, which reads as a
    different document. The font table says what to fall back to: a variable-
    pitch swiss (grotesque) face, Arial where nothing better is installed.
    CT_Font orders its children altName, family, pitch."""
    return DOCX_XML_HEAD + (
        "<w:fonts %s>"
        '<w:font w:name="Host Grotesk">'
        '<w:altName w:val="Arial"/>'
        '<w:family w:val="swiss"/>'
        '<w:pitch w:val="variable"/>'
        "</w:font>"
        "</w:fonts>" % DOCX_W_NS
    )


def _dx_numbering():
    """Two abstract lists: the pillar initiatives' bullet and the Gap Report's
    numbered questions — real Word lists, so the reader can extend them.

    Marker size is pinned rather than inherited. Without a `w:sz` a marker
    takes the document default (9.5pt), which drew the Gap Report's bold amber
    number a size *smaller* than the 10.5pt question beside it — it now matches
    its item. The bullet keeps 9.5pt, deliberately: Arial's • is a thinner disc
    than Host Grotesk's, so the print surfaces size their bullet up to reach the
    HTML marker's weight, but Word folds the marker's size into the line height
    of the item it marks, and a bullet enlarged the same way would loosen every
    initiative's first line. Pinned, not inherited, so a change to the document
    default can never silently resize a marker.

    The indents here are what a reader inherits when they extend the list; the
    list paragraphs restate them (direct formatting wins in Word).
    """
    return DOCX_XML_HEAD + (
        "<w:numbering %s>"
        '<w:abstractNum w:abstractNumId="0"><w:multiLevelType w:val="hybridMultilevel"/>'
        '<w:lvl w:ilvl="0"><w:start w:val="1"/><w:numFmt w:val="bullet"/>'
        '<w:lvlText w:val="•"/><w:lvlJc w:val="left"/>'
        '<w:pPr><w:ind w:left="%d" w:hanging="%d"/></w:pPr>'
        '<w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial" w:hint="default"/>'
        '<w:color w:val="%s"/><w:sz w:val="19"/><w:szCs w:val="19"/></w:rPr>'
        "</w:lvl></w:abstractNum>"
        '<w:abstractNum w:abstractNumId="1"><w:multiLevelType w:val="hybridMultilevel"/>'
        '<w:lvl w:ilvl="0"><w:start w:val="1"/><w:numFmt w:val="decimal"/>'
        '<w:lvlText w:val="%%1."/><w:lvlJc w:val="left"/>'
        '<w:pPr><w:ind w:left="%d" w:hanging="%d"/></w:pPr>'
        '<w:rPr><w:b/><w:color w:val="%s"/><w:sz w:val="21"/><w:szCs w:val="21"/></w:rPr>'
        "</w:lvl></w:abstractNum>"
        '<w:num w:numId="1"><w:abstractNumId w:val="0"/></w:num>'
        '<w:num w:numId="2"><w:abstractNumId w:val="1"/></w:num>'
        "</w:numbering>"
        % (
            DOCX_W_NS,
            DOCX_BULLET_INDENT,
            DOCX_BULLET_HANGING,
            _dx_hex(BRAND),
            DOCX_NUMBER_INDENT,
            DOCX_NUMBER_HANGING,
            _dx_hex(AMBER),
        )
    )


def _dx_footer(generated_at):
    """The slim footnote every sheet carries: the CTA, linked, and the
    generation date on a right tab — the HTML footer, part-shared instead of
    repeated per page. The CTA is a brand-shaded, white, bold run: OOXML run
    shading is the closest Word gets to the HTML pill (square, no radius —
    the built-in PDF draws its pill square for the same reason), and a leading
    and trailing space inside the shaded run keeps the fill off the glyphs."""
    runs = _dx_hyperlink(
        _dx_run(
            " %s " % cta_label(_plain("cta_title")),
            8.5,
            "b",
            WHITE,
            shade=_dx_hex(BRAND),
        ),
        DOCX_FOOTER_REL_CTA,
    )
    date = _plain("generated", generated_at)
    runs += (
        '<w:r><w:rPr><w:color w:val="%s"/><w:sz w:val="15"/><w:szCs w:val="15"/></w:rPr>'
        '<w:tab/><w:t xml:space="preserve">%s</w:t></w:r>'
        % (_dx_hex(GRAY_LIGHT), _dx_esc(date))
    )
    return DOCX_XML_HEAD + (
        "<w:ftr %s><w:p><w:pPr>"
        '<w:pBdr><w:top w:val="single" w:sz="4" w:space="4" w:color="%s"/></w:pBdr>'
        '<w:tabs><w:tab w:val="right" w:pos="%d"/></w:tabs>'
        '<w:spacing w:before="80" w:after="0"/>'
        "</w:pPr>%s</w:p></w:ftr>" % (DOCX_W_NS, _dx_hex(LINE), DOCX_TAB_RIGHT, runs)
    )


def _dx_core_props(title):
    return DOCX_XML_HEAD + (
        "<cp:coreProperties "
        'xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
        'xmlns:dc="http://purl.org/dc/elements/1.1/">'
        "<dc:title>%s</dc:title><dc:creator>render_cascade.py</dc:creator>"
        "<cp:lastModifiedBy>render_cascade.py</cp:lastModifiedBy>"
        "</cp:coreProperties>" % _dx_esc(title)
    )


def _dx_app_props():
    return DOCX_XML_HEAD + (
        "<Properties "
        'xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties">'
        "<Application>render_cascade.py</Application>"
        "</Properties>"
    )


def _dx_document(sections):
    """Section bodies into word/document.xml: every section but the last ends
    with a hairline paragraph carrying its sectPr (that is how OOXML terminates
    a section); the last one's rides the body itself."""
    sectpr = _dx_sectpr()
    body = []
    for index, blocks in enumerate(sections):
        body.append(blocks)
        if index < len(sections) - 1:
            body.append(
                '<w:p><w:pPr><w:spacing w:after="0" w:line="20" w:lineRule="exact"/>'
                '<w:rPr><w:sz w:val="2"/></w:rPr>%s</w:pPr></w:p>' % sectpr
            )
    return DOCX_XML_HEAD + (
        "<w:document %s%s><w:body>%s%s</w:body></w:document>"
        % (DOCX_W_NS, DOCX_DRAWING_NS, "".join(body), sectpr)
    )


def render_docx(bundle, docx_path, only_op=None):
    """The `--docx` writer: bundle → a Word document inheriting the printable
    artifact's design. One landscape section per one-pager plus the Gap Report
    (root, gap report, teams); with only_op set it writes that single sheet
    (--split, no gap page), exactly like the built-in PDF engine."""
    if not bundle.get("onePagers"):
        # a clean signal for the caller's fallback message
        raise ValueError("bundle has no onePagers")
    # Names the document, so it takes the fallback the HTML artifact's <title>
    # takes (`render`) — a nameless bundle still opens as a titled file.
    company = bundle.get("company", {}).get("name", "Strategy")
    generated_at = bundle.get("generator", {}).get("generatedAt", "")
    by_ref = {op["ref"]: op for op in bundle["onePagers"]}

    gaps = []
    source_ops = [only_op] if only_op is not None else bundle["onePagers"]
    extracted = [_pdf_extract_op(op, by_ref, gaps) for op in source_ops]

    proposed = proposed_entries(bundle)
    banner = draft_banner_text(proposed, standalone=only_op is not None)

    sections = [_dx_one_pager(extracted[0], banner, 1)]
    if only_op is None:
        # the extraction above already walked every page, so the gap list the
        # report renders is complete before its section is built
        sections.append(_dx_gap_report(bundle, gaps, proposed, 2))
    for index, op in enumerate(extracted[1:], start=3):
        sections.append(_dx_one_pager(op, banner, index))

    rels = [
        ("rId1", "officeDocument/2006/relationships/styles", "styles.xml", ""),
        ("rId2", "officeDocument/2006/relationships/numbering", "numbering.xml", ""),
        (DOCX_REL_FOOTER, "officeDocument/2006/relationships/footer", "footer1.xml", ""),
    ]
    if LOGO_PNG_B64:
        rels.append(
            (DOCX_REL_LOGO, "officeDocument/2006/relationships/image", "media/logo.png", "")
        )
    rels.append(
        (
            DOCX_REL_CTA,
            "officeDocument/2006/relationships/hyperlink",
            _dx_attr(CTA_HREF),
            ' TargetMode="External"',
        )
    )
    rels.append(("rId6", "officeDocument/2006/relationships/fontTable", "fontTable.xml", ""))

    parts = [
        ("[Content_Types].xml", _dx_content_types().encode("utf-8")),
        (
            "_rels/.rels",
            _dx_rels(
                [
                    ("rId1", "officeDocument/2006/relationships/officeDocument", "word/document.xml", ""),
                    ("rId2", "package/2006/relationships/metadata/core-properties", "docProps/core.xml", ""),
                    ("rId3", "officeDocument/2006/relationships/extended-properties", "docProps/app.xml", ""),
                ]
            ).encode("utf-8"),
        ),
        ("word/document.xml", _dx_document(sections).encode("utf-8")),
        ("word/_rels/document.xml.rels", _dx_rels(rels).encode("utf-8")),
        ("word/styles.xml", _dx_styles().encode("utf-8")),
        ("word/fontTable.xml", _dx_font_table().encode("utf-8")),
        ("word/numbering.xml", _dx_numbering().encode("utf-8")),
        ("word/footer1.xml", _dx_footer(generated_at).encode("utf-8")),
        (
            "word/_rels/footer1.xml.rels",
            _dx_rels(
                [
                    (
                        DOCX_FOOTER_REL_CTA,
                        "officeDocument/2006/relationships/hyperlink",
                        _dx_attr(CTA_HREF),
                        ' TargetMode="External"',
                    )
                ]
            ).encode("utf-8"),
        ),
        ("docProps/core.xml", _dx_core_props(_plain("doc_title", company)).encode("utf-8")),
        ("docProps/app.xml", _dx_app_props().encode("utf-8")),
    ]
    if LOGO_PNG_B64:
        parts.append(("word/media/logo.png", base64.b64decode(LOGO_PNG_B64)))

    with zipfile.ZipFile(str(docx_path), "w", zipfile.ZIP_DEFLATED) as package:
        for name, payload in parts:
            package.writestr(name, payload)
    return "builtin"


# --- pdf conversion ----------------------------------------------------------


_CHROMIUM_PROBE = ["unset"]


def find_chromium():
    """A headless-capable Chromium/Chrome/Edge binary, or None. Probed once
    per process — --split converts one PDF per one-pager."""
    if _CHROMIUM_PROBE == ["unset"]:
        _CHROMIUM_PROBE[0] = _probe_chromium()
    return _CHROMIUM_PROBE[0]


def _probe_chromium():
    for name in (
        "chromium",
        "chromium-browser",
        "google-chrome",
        "google-chrome-stable",
        "chrome",
        "msedge",
    ):
        path = shutil.which(name)
        if path:
            return path
    for path in (
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
        "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    ):
        if os.path.exists(path):
            return path
    return None


def _has_pdf_magic(path):
    """Proof the file is a PDF this run produced — an external engine that
    writes an error page (or nothing) under the PDF name must not count as
    success."""
    try:
        with open(path, "rb") as handle:
            return handle.read(5) == b"%PDF-"
    except OSError:
        return False


def _last_line(raw):
    """The tail of a subprocess' stderr — chromium's own diagnosis, one line."""
    lines = [line for line in raw.decode("utf-8", "replace").splitlines() if line.strip()]
    return lines[-1].strip() if lines else ""


# WeasyPrint cannot fragment flex containers cleanly: a page taller than A4
# splits with overlapping content and phantom blank pages (observed live on
# claude.ai, 2026-07-31). Blockify the page containers so content flows and
# keep logical units unbroken. Chromium gets no override — it honors the
# print CSS as designed, one page per one-pager.
WEASYPRINT_CSS = """
.page, .page-body { display: block !important; }
.page { min-height: auto !important; }
header, .core, .pillar, .chip-band, .stats, .cta-hero, .draft-banner { page-break-inside: avoid !important; }
.gap-list li, .gap-proposed-item, .gap-sources-item { page-break-inside: avoid !important; }
footer { margin-top: 6mm !important; }
"""
# The !important is load-bearing: write_pdf(stylesheets=…) injects these at
# USER origin, and a normal user declaration loses to the artifact's own
# author-origin <style> at equal specificity (WeasyPrint declaration
# precedence: user-normal 2 < author-normal 3). Without it the overlay is
# silently inert and the flex pages fragment corruptly again.


def convert_to_pdf(html_path, pdf_path, bundle, only_op=None, engine="auto"):
    """PDF production ladder. Returns the engine used, or None only when even
    the built-in writer failed (the HTML then still prints from any browser).

    The ladder is strictly best-output-first and probes THIS environment's
    actual capabilities at run time (never a hardcoded platform assumption):

      1. headless Chromium — renders the print CSS faithfully; always wins
         when any Chromium/Chrome/Edge binary exists here.
      2. WeasyPrint — near-faithful; used when importable. It gets
         WEASYPRINT_CSS layered on top so its flex-fragmentation limits do
         not corrupt the pages; check the output against the HTML.
      3. the built-in stdlib writer — a real PDF, simplified layout. Never
         preempts 1 or 2; it exists so no environment ships without a PDF.

    `engine` forces a single tier (testing / debugging); "auto" is the
    contract. A prettier engine appearing in the environment on the next run
    automatically wins again.
    """
    if engine in ("auto", "chromium"):
        chromium = find_chromium()
        failure = "no chromium/chrome/edge binary in this environment"
        if chromium:
            # Chrome's sandbox stays on wherever it works — desktop users are
            # the ones rendering alongside untrusted content. Root or
            # containerized environments (code-exec sandboxes) cannot
            # initialize the sandbox and exit nonzero, so --no-sandbox is a
            # retry, never the default.
            for extra in ([], ["--no-sandbox"]):
                # An earlier run's PDF sitting at the target must never pass
                # as this run's output: chromium can exit 0 having written
                # nothing at all, and a stale artifact is worse than none.
                pdf_path.unlink(missing_ok=True)
                try:
                    result = subprocess.run(
                        [
                            chromium,
                            "--headless",
                            "--disable-gpu",
                            *extra,
                            "--no-pdf-header-footer",
                            "--print-to-pdf=%s" % pdf_path,
                            html_path.resolve().as_uri(),
                        ],
                        capture_output=True,
                        timeout=120,
                    )
                except (subprocess.TimeoutExpired, OSError) as error:
                    failure = "%s: %s" % (type(error).__name__, error)
                    continue
                if result.returncode == 0 and _has_pdf_magic(pdf_path):
                    return "chromium"
                failure = _last_line(result.stderr) or "exit %d, no PDF written" % result.returncode
        if engine == "chromium":
            # auto keeps falling down the ladder silently; a forced tier owes
            # the caller the reason it produced nothing
            print("chromium PDF failed — %s" % failure, file=sys.stderr)
            return None
    if engine in ("auto", "weasyprint"):
        try:
            from weasyprint import CSS, HTML  # optional, never a hard dependency

            HTML(filename=str(html_path)).write_pdf(
                str(pdf_path), stylesheets=[CSS(string=WEASYPRINT_CSS)]
            )
            return "weasyprint"
        except ImportError:
            if engine == "weasyprint":
                return None
        except Exception as error:  # noqa: BLE001 — a broken install raises
            # OSError at import (missing pango/cairo); any weasyprint failure
            # must fall through to the built-in tier, never kill PDF delivery
            print(
                "weasyprint failed (%s: %s) — using the built-in writer"
                % (type(error).__name__, error),
                file=sys.stderr,
            )
            if engine == "weasyprint":
                return None
    try:
        return render_builtin_pdf(bundle, pdf_path, only_op=only_op)
    except Exception as error:  # noqa: BLE001 — the HTML delivery must survive a writer bug
        print("built-in PDF writer failed (%s: %s)" % (type(error).__name__, error), file=sys.stderr)
        return None


def _emit_docx(bundle, docx_path, only_op=None, pdf_produced=False):
    """Write one DOCX and report it, or report that none was written. Wrapped
    like the built-in PDF tier: the Word document is an extra, so a writer bug
    must cost the run its DOCX and nothing else — the PDF and the HTML have
    already been delivered by the time this runs, and the exit code stays 0.

    The fallback line names what this run actually produced: a `--docx` run
    without `--pdf` has no PDF to fall back on, and pointing at one would send
    the caller looking for a file that was never written."""
    try:
        render_docx(bundle, docx_path, only_op=only_op)
    except Exception as error:  # noqa: BLE001 — PDF delivery must survive a writer bug
        print(
            "built-in DOCX writer failed (%s: %s)" % (type(error).__name__, error),
            file=sys.stderr,
        )
        print("no DOCX produced — deliver the %s" % ("PDF" if pdf_produced else "HTML"))
        return False
    print(f"docx {docx_path} (built-in OOXML writer)")
    return True


def main():
    global S, CTA_REF, CTA_HREF

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path, help="validated cascade bundle JSON")
    parser.add_argument(
        "-o", "--output", type=Path, help="output HTML path (default: <bundle>.html)"
    )
    parser.add_argument(
        "--split",
        action="store_true",
        help="additionally write one artifact per one-pager (<output>-NN-<title>.html) so "
        "each unit gets its own sheet; the combined cascade stays the shareable story",
    )
    parser.add_argument(
        "--lang",
        choices=sorted(STRINGS),
        default="en",
        help="language of the artifact chrome (draft banner, Gap Report page, CTA) — "
        "match the cascade's language",
    )
    parser.add_argument(
        "--pdf",
        nargs="?",
        const=True,
        default=None,
        metavar="PDF",
        help="also produce a PDF (default: <output>.pdf) — best engine this "
        "environment offers: headless Chromium, then WeasyPrint, then the "
        "built-in writer (simplified layout, always available)",
    )
    parser.add_argument(
        "--pdf-engine",
        choices=("auto", "chromium", "weasyprint", "builtin"),
        default="auto",
        help="force one PDF engine (testing/debugging) — 'auto' picks the best "
        "available and is the correct choice everywhere",
    )
    parser.add_argument(
        "--docx",
        nargs="?",
        const=True,
        default=None,
        metavar="DOCX",
        help="also produce an editable Word document (default: <output>.docx) — the "
        "same design, written by the built-in OOXML writer; upload it to Google "
        "Drive with convert-on-upload and it opens as a Google Doc",
    )
    args = parser.parse_args()

    S = STRINGS[args.lang]

    bundle = json.loads(args.bundle.read_text(encoding="utf-8"))

    attribution_ref = (bundle.get("attribution") or {}).get("ref")
    if attribution_ref:
        CTA_REF = attribution_ref
        CTA_HREF = "%s/?ref=%s" % (CTA_URL, CTA_REF)
    output = args.output or args.bundle.with_suffix(".html")
    output.write_text(render(bundle), encoding="utf-8")
    print(f"rendered {output} ({len(bundle['onePagers'])} one-pager(s) + gap report)")

    pdf_produced = False
    if args.pdf is not None:
        pdf_path = output.with_suffix(".pdf") if args.pdf is True else Path(args.pdf)
        engine = convert_to_pdf(output, pdf_path, bundle, engine=args.pdf_engine)
        pdf_produced = engine is not None
        if engine == "chromium":
            print(f"pdf {pdf_path} (headless chromium — faithful to the print CSS)")
        elif engine == "weasyprint":
            print(f"pdf {pdf_path} (weasyprint — verify the layout against the HTML before sharing)")
        elif engine == "builtin":
            print(f"pdf {pdf_path} (built-in writer — simplified layout; the HTML carries the full design)")
        else:
            print("no PDF produced — deliver the HTML; it prints to PDF from any browser")

    if args.docx is not None:
        _emit_docx(
            bundle,
            output.with_suffix(".docx") if args.docx is True else Path(args.docx),
            pdf_produced=pdf_produced,
        )

    if args.split:
        by_ref = {op["ref"]: op for op in bundle["onePagers"]}
        # Bundle-scoped, like the combined artifact's: a team sheet says the
        # cascade carries composed content even when this team's page does not
        banner = draft_banner_text(proposed_entries(bundle), standalone=True)
        for index, one_pager in enumerate(bundle["onePagers"]):
            # Per-sheet gap collection is discarded — statement gaps feed the
            # combined artifact's Gap Report page, which splits do not carry.
            page = one_pager_html(one_pager, by_ref, bundle, [], banner)
            title = one_pager.get("title", "")
            split_path = output.with_name(
                "%s-%02d-%s.html" % (output.stem, index, slugify(title))
            )
            split_path.write_text(document(esc(title), [page]), encoding="utf-8")
            print(f"split {split_path}")
            split_pdf = False
            if args.pdf is not None:
                engine = convert_to_pdf(
                    split_path,
                    split_path.with_suffix(".pdf"),
                    bundle,
                    only_op=one_pager,
                    engine=args.pdf_engine,
                )
                split_pdf = engine is not None
                if engine:
                    print(f"pdf {split_path.with_suffix('.pdf')} ({engine})")
            if args.docx is not None:
                _emit_docx(
                    bundle,
                    split_path.with_suffix(".docx"),
                    only_op=one_pager,
                    pdf_produced=split_pdf,
                )
    return 0


if __name__ == "__main__":
    sys.exit(main())
