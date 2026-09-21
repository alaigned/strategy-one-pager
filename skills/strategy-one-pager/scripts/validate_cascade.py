#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["jsonschema"]
# ///
# (jsonschema is preferred, not required — plain `python3` runs the same
# check set on the built-in stdlib engine; uv/pipx users get the exact one.)
"""Validate a strategy cascade bundle against the packaged Alaigned methodology.

Runs anywhere Python does: schema checks use the `jsonschema` package when it
is importable and a built-in stdlib checker otherwise — the same checks either
way, so no environment needs pip or network to validate.

Usage:
    python3 validate_cascade.py <bundle.json> [--skill-dir <path>]

Checks, in order:
  1. envelope shape (cascade-bundle.schema.json)
  2. methodology fingerprint matches the packaged schemas/fingerprint.json
  3. every one-pager's content against schemas/methodology.inlined.json
     hierarchy[level].onePagerSchema
  4. structural rules: single L0, resolvable parent refs, level = parent+1,
     unique refs, unique + well-formed entity UUIDs
  5. links: each (parentRef, childRef, parentPath, childPath) appears once,
     rule pair belongs to the parent level's propagationRules, paths match
     rules, paths resolve, values are verbatim-equal
  6. cascade completeness: a core-field link per core field the parent fills,
     every child pillar derives from a parent initiative or enabler, and a
     cascading initiative reaches at most 3 children (its critical teams);
     dead-end initiatives reach none, and enablers cascade only to the
     children that adopt them (a content decision, not a rule)
  7. methodology ceilings as warnings — values read from the packaged
     artifact's hierarchy[].limits
  8. generator.skillVersion against the version in the sibling SKILL.md, as a
     warning — a bundle stamped with a version the installed skill never shipped
     means the run did not read the skill's own frontmatter

Exit code 0 = valid; 1 = validation errors; 2 = usage/environment problem.
"""

import argparse
import json
import re
import sys
from pathlib import Path

try:
    import jsonschema
except ImportError:  # the built-in checker below takes over — never a stop
    jsonschema = None

UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I
)


# --- schema-check engines -----------------------------------------------------
#
# The `jsonschema` package is the preferred engine (exact draft-07 semantics)
# and always wins when importable. The built-in checker is the stdlib fallback
# for environments where pip cannot install anything (no-network chat
# sandboxes): the packaged schemas are fully inlined at package time
# ($ref/allOf resolved), so the draft-07 subset below covers every keyword
# they use, and the full check set runs either way. The subset is guarded by
# name and by form: a schema carrying any other keyword — or a supported
# keyword written in a form the checker does not implement, e.g. tuple `items`
# — is a hard exit 2, so the built-in engine never silently under-validates.

BUILTIN_KEYWORDS = {
    "type", "properties", "required", "items", "enum", "const", "pattern",
    "additionalProperties", "minItems", "maxItems", "minLength", "maxLength",
    "minimum", "maximum", "uniqueItems",
}
# Keywords that annotate without constraining, so ignoring them is parity with
# the preferred engine rather than laxity: `format` and the content* pair only
# constrain when a Draft7Validator is given a format_checker, and we construct
# it without one (verified against jsonschema 4.26 — no error on a violating
# instance). Any "x-" key is a vendor extension, likewise annotation-only.
# `maxItemsRecommended` is the methodology's own advisory element ceiling: it
# rides on the collection array beside the `maxItems` that does the
# constraining, and the preferred engine ignores it as an unknown keyword.
BUILTIN_ANNOTATIONS = {
    "$schema", "$id", "$comment", "title", "description", "default",
    "examples", "format", "readOnly", "writeOnly", "contentEncoding",
    "contentMediaType", "deprecated", "maxItemsRecommended",
}


def builtin_is_annotation(key):
    return key in BUILTIN_ANNOTATIONS or key.startswith("x-")


def builtin_form_name(value):
    """The JSON form of a schema value, for the unsupported-form message."""
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, dict):
        return "object"
    if isinstance(value, list):
        return "array"
    if isinstance(value, str):
        return "string"
    if value is None:
        return "null"
    return "number"


def builtin_assert_supported(schema, where):
    """Refuse whatever the checker below cannot fully evaluate — by keyword
    name AND by form. The whitelist covers `items` as a single schema (not the
    tuple form) and `additionalProperties` as a boolean (not a subschema), and
    every schema position must be an object: draft-07 boolean subschemas
    (`{"properties": {"x": false}}`) are not implemented either."""
    unsupported = set()

    def walk(node):
        if not isinstance(node, dict):
            unsupported.add(f"{builtin_form_name(node)} subschema")
            return
        for key, value in node.items():
            if key in ("enum", "const") or builtin_is_annotation(key):
                continue  # data / annotations, not schemas
            if key not in BUILTIN_KEYWORDS:
                unsupported.add(key)
                continue
            if key == "properties":
                if not isinstance(value, dict):
                    unsupported.add(f"properties({builtin_form_name(value)} form)")
                    continue
                for sub in value.values():
                    walk(sub)
            elif key == "items":
                if not isinstance(value, dict):
                    unsupported.add(f"items({builtin_form_name(value)} form)")
                    continue
                walk(value)
            elif key == "additionalProperties" and not isinstance(value, bool):
                unsupported.add(
                    f"additionalProperties({builtin_form_name(value)} form)"
                )
            # every other supported keyword carries data, never a subschema

    walk(schema)
    if unsupported:
        sys.stderr.write(
            f"The packaged {where} schema uses JSON Schema keyword(s)/form(s) "
            f"{sorted(unsupported)} the built-in checker does not implement — "
            "install the jsonschema package or repackage the skill.\n"
        )
        sys.exit(2)


def builtin_type_ok(instance, expected):
    if expected == "null":
        return instance is None
    if expected == "boolean":
        return isinstance(instance, bool)
    if expected == "integer":
        # draft-07: a float with zero fractional part IS an integer (1.0),
        # matching the jsonschema package's verdict
        if isinstance(instance, bool):
            return False
        return isinstance(instance, int) or (
            isinstance(instance, float) and instance.is_integer()
        )
    if expected == "number":
        return isinstance(instance, (int, float)) and not isinstance(instance, bool)
    if expected == "string":
        return isinstance(instance, str)
    if expected == "array":
        return isinstance(instance, list)
    if expected == "object":
        return isinstance(instance, dict)
    return False


def builtin_equal(a, b):
    """JSON equality — bool is its own type at every depth, never equal to
    0/1 (mirrors the jsonschema package's deep comparison)."""
    if isinstance(a, bool) != isinstance(b, bool):
        return False
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(builtin_equal(x, y) for x, y in zip(a, b))
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(builtin_equal(v, b[k]) for k, v in a.items())
    return a == b


def builtin_min_phrase(bound):
    """jsonschema words a minLength/minItems failure as emptiness when the
    bound is 1 — the envelope's most common bound — and as shortness above."""
    return "should be non-empty" if bound == 1 else "is too short"


def builtin_max_phrase(bound):
    """...and a maxLength/maxItems failure as emptiness when the bound is 0."""
    return "is expected to be empty" if bound == 0 else "is too long"


def builtin_schema_errors(schema, instance, path=()):
    """(path, message) pairs, draft-07 semantics for the supported subset.
    Keyword checks apply only to instances of their type, exactly as
    jsonschema evaluates them — a type mismatch does not short-circuit."""
    errors = []
    declared = schema.get("type")
    if declared is not None:
        types = declared if isinstance(declared, list) else [declared]
        if not any(builtin_type_ok(instance, t) for t in types):
            expected = ", ".join(f"'{t}'" for t in types)
            errors.append((path, f"{instance!r} is not of type {expected}"))
    if "enum" in schema and not any(builtin_equal(instance, v) for v in schema["enum"]):
        errors.append((path, f"{instance!r} is not one of {schema['enum']!r}"))
    if "const" in schema and not builtin_equal(instance, schema["const"]):
        errors.append((path, f"{schema['const']!r} was expected"))
    if isinstance(instance, str):
        if "pattern" in schema and not re.search(schema["pattern"], instance):
            errors.append((path, f"{instance!r} does not match {schema['pattern']!r}"))
        if "minLength" in schema and len(instance) < schema["minLength"]:
            errors.append(
                (path, f"{instance!r} {builtin_min_phrase(schema['minLength'])}")
            )
        if "maxLength" in schema and len(instance) > schema["maxLength"]:
            errors.append(
                (path, f"{instance!r} {builtin_max_phrase(schema['maxLength'])}")
            )
    if isinstance(instance, (int, float)) and not isinstance(instance, bool):
        if "minimum" in schema and instance < schema["minimum"]:
            errors.append(
                (path, f"{instance!r} is less than the minimum of {schema['minimum']!r}")
            )
        if "maximum" in schema and instance > schema["maximum"]:
            errors.append(
                (path, f"{instance!r} is greater than the maximum of {schema['maximum']!r}")
            )
    if isinstance(instance, list):
        if "minItems" in schema and len(instance) < schema["minItems"]:
            errors.append(
                (path, f"{instance!r} {builtin_min_phrase(schema['minItems'])}")
            )
        if "maxItems" in schema and len(instance) > schema["maxItems"]:
            errors.append(
                (path, f"{instance!r} {builtin_max_phrase(schema['maxItems'])}")
            )
        if schema.get("uniqueItems") and any(
            builtin_equal(a, b)
            for i, a in enumerate(instance)
            for b in instance[i + 1 :]
        ):
            errors.append((path, f"{instance!r} has non-unique elements"))
        if isinstance(schema.get("items"), dict):
            for index, item in enumerate(instance):
                errors.extend(
                    builtin_schema_errors(schema["items"], item, path + (index,))
                )
    if isinstance(instance, dict):
        properties = schema.get("properties", {})
        for name in schema.get("required", []):
            if name not in instance:
                errors.append((path, f"{name!r} is a required property"))
        for name, sub in properties.items():
            if name in instance:
                errors.extend(builtin_schema_errors(sub, instance[name], path + (name,)))
        if schema.get("additionalProperties") is False:
            extras = sorted(set(instance) - set(properties))
            if extras:
                names = ", ".join(repr(e) for e in extras)
                verb = "was" if len(extras) == 1 else "were"
                errors.append(
                    (path, f"Additional properties are not allowed ({names} {verb} unexpected)")
                )
    return errors


def resolve_schema_engine(choice):
    if choice == "jsonschema" and jsonschema is None:
        sys.stderr.write(
            "--schema-engine jsonschema requested but the package is not importable\n"
        )
        sys.exit(2)
    if choice == "auto":
        return "jsonschema" if jsonschema is not None else "builtin"
    return choice


def schema_errors(schema, instance, engine):
    """(path, message) pairs from the selected engine. The jsonschema path is
    byte-identical to the historical output (same messages, same ordering).
    Accepted divergence: when ten or more sibling errors share one message the
    two engines print them in a different order — jsonschema sorts by
    str(error), which embeds the instance path (so '[10]' precedes '[2]'), the
    built-in checker by message text alone — the findings themselves match."""
    if engine == "jsonschema":
        validator = jsonschema.Draft7Validator(schema)
        return [
            (tuple(error.path), error.message)
            for error in sorted(validator.iter_errors(instance), key=str)
        ]
    return sorted(builtin_schema_errors(schema, instance), key=lambda e: e[1])

# Methodology rule values (element ceilings, critical-team cap) and the rule
# classifications are NOT hardcoded here — they are read/derived from the
# packaged methodology artifact: the element ceilings from each collection's
# maxItemsRecommended annotation, the critical-team cap from
# hierarchy[].limits, and the rule classifications from propagationRules.


def level_entry(methodology, level):
    for entry in methodology.get("hierarchy", []):
        if entry.get("level") == level:
            return entry
    return None


# Where each element ceiling lives in the level's onePagerSchema: every name is
# a "properties" hop, "items" steps into an array's elements.
COLLECTION_PATHS = {
    "pillars": ["pillars", "properties", "content"],
    "enablers": ["enablers", "properties", "content"],
    "values": ["values", "properties", "content"],
    "initiativesPerPillar": [
        "pillars", "properties", "content", "items",
        "properties", "initiatives", "properties", "content",
    ],
}


def dig(node, path):
    for key in path:
        if not isinstance(node, dict):
            return None
        node = node.get(key)
    return node


def level_limits(methodology, level):
    """Element ceilings from each collection's maxItemsRecommended annotation,
    plus the critical-teams cap, which has no array to hang off and stays in
    hierarchy[].limits."""
    entry = level_entry(methodology, level) or {}
    properties = dig(entry, ["onePagerSchema", "properties"]) or {}

    limits = {}
    for key, path in COLLECTION_PATHS.items():
        limits[key] = dig(properties, path + ["maxItemsRecommended"])

    limits["criticalTeamsPerInitiative"] = dig(entry, ["limits", "criticalTeamsPerInitiative"])

    if any(value is None for value in limits.values()):
        missing = sorted(key for key, value in limits.items() if value is None)
        sys.stderr.write(
            f"Methodology artifact is missing limits {missing} for level {level} — "
            "the schemas/ directory is out of date or incomplete. Regenerate it if "
            "you maintain this skill, otherwise download the skill again.\n"
        )
        sys.exit(2)
    return limits


def static_rules(rules):
    """Core-field rules: propagation pairs without wildcards."""
    return [parent for parent in rules if "*" not in parent]


def initiative_name_rule(rules):
    """The wildcard rule cascading an initiative's name into a child pillar name."""
    matches = [
        parent
        for parent in rules
        if ".initiatives." in parent and parent.endswith(".name.textValue")
    ]
    if len(matches) != 1:
        sys.stderr.write(f"Expected exactly one initiative-name rule, got {matches}\n")
        sys.exit(2)
    return matches[0]


class Findings:
    def __init__(self):
        self.errors = []
        self.warnings = []

    def error(self, check, message):
        self.errors.append((check, message))

    def warning(self, check, message):
        self.warnings.append((check, message))

    def report(self):
        for check, message in self.errors:
            print(f"ERROR   [{check}] {message}")
        for check, message in self.warnings:
            print(f"WARNING [{check}] {message}")
        print(
            f"\n{len(self.errors)} error(s), {len(self.warnings)} warning(s)"
        )


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def resolve_path(content, path):
    """Resolve a dot path; 'content' array steps are addressed by metadata.id."""
    node = content
    for segment in path.split("."):
        if isinstance(node, list):
            node = next(
                (
                    item
                    for item in node
                    if isinstance(item, dict)
                    and item.get("metadata", {}).get("id") == segment
                ),
                None,
            )
        elif isinstance(node, dict):
            node = node.get(segment)
        else:
            return None, False
        if node is None:
            return None, False
    return node, True


def path_matches_rule(path, rule):
    path_segments = path.split(".")
    rule_segments = rule.split(".")
    if len(path_segments) != len(rule_segments):
        return False
    return all(
        r == "*" or r == p for p, r in zip(path_segments, rule_segments)
    )


def numeric_level(op):
    """A one-pager's level when it is a number, else None. Levels arrive
    straight from the bundle, so any JSON type can turn up (`level: null` is a
    plausible model emission) — comparing or incrementing a non-numeric one
    raises a TypeError that kills the run before the report prints, and
    check_envelope has already collected the real defect ("None is not of type
    'integer'"). bool counts as numeric on purpose: True is an int in Python
    and already read as a child level."""
    level = op.get("level", 0)
    return level if isinstance(level, (int, float)) else None


def is_child_level(op):
    """True for a one-pager below the root — the structural walks skip a page
    whose level is missing, zero, or not a number (see numeric_level)."""
    level = numeric_level(op)
    return level is not None and level > 0


def collect_entity_ids(node, acc):
    if isinstance(node, dict):
        metadata = node.get("metadata")
        if isinstance(metadata, dict) and "id" in metadata:
            acc.append(metadata["id"])
        for value in node.values():
            collect_entity_ids(value, acc)
    elif isinstance(node, list):
        for item in node:
            collect_entity_ids(item, acc)


def check_envelope(bundle, envelope_schema, findings, engine):
    for path, message in schema_errors(envelope_schema, bundle, engine):
        findings.error("envelope", f"{'/'.join(map(str, path))}: {message}")


def check_fingerprint(bundle, skill_dir, findings):
    packaged = load_json(skill_dir / "schemas" / "fingerprint.json")
    declared = bundle.get("methodology", {}).get("fingerprint")
    if declared != packaged["fingerprint"]:
        findings.error(
            "fingerprint",
            f"bundle declares {declared!r} but the packaged methodology is "
            f"{packaged['fingerprint']!r} — regenerate the bundle from the "
            "packaged schemas",
        )


# `[PROPOSED …]` marks composed content so the renderer can strip it from the
# page and account for it in the draft banner and the Gap Report. That walk
# only reaches `onePagers[].content`, while `company.name` and a one-pager's
# `title` are printed into the page header verbatim — a marker there would
# ship inside the heading AND escape the honesty accounting. Open questions
# are prose about the draft, so a marker *mentioned* there is legitimate; only
# the two rendered identity fields are policed.
PROPOSED_MARKER_RE = re.compile(r"\[PROPOSED(?:\s*[—-]\s*[^\]]*)?\]")


def check_proposed_markers(bundle, findings):
    company_name = (bundle.get("company") or {}).get("name")
    if isinstance(company_name, str) and PROPOSED_MARKER_RE.search(company_name):
        findings.error(
            "markers",
            "company.name carries a [PROPOSED] marker — it renders verbatim in "
            "the page header; keep the marker on composed content textValues "
            "and raise the naming question in openQuestions",
        )

    for op in bundle.get("onePagers", []):
        title = op.get("title")
        if isinstance(title, str) and PROPOSED_MARKER_RE.search(title):
            findings.error(
                "markers",
                f"{op.get('ref', '?')}: title carries a [PROPOSED] marker — it "
                "renders verbatim in the page header; keep the marker on composed "
                "content textValues and raise the question in openQuestions",
            )


def level_schema(methodology, level):
    for entry in methodology.get("hierarchy", []):
        if entry.get("level") == level:
            return entry.get("onePagerSchema")
    return None


def propagation_rules(methodology, level):
    for entry in methodology.get("hierarchy", []):
        if entry.get("level") == level:
            return entry.get("propagationRules", {})
    return {}


def check_content_schemas(bundle, methodology, findings, engine):
    for op in bundle.get("onePagers", []):
        ref = op.get("ref", "?")
        schema = level_schema(methodology, op.get("level"))
        if schema is None:
            findings.error("schema", f"{ref}: no methodology level {op.get('level')}")
            continue
        for path, message in schema_errors(schema, op.get("content", {}), engine):
            where = "/".join(map(str, path)) or "(root)"
            findings.error("schema", f"{ref}: {where}: {message}")


def check_structure(bundle, findings):
    one_pagers = bundle.get("onePagers", [])
    by_ref = {}
    for op in one_pagers:
        ref = op.get("ref")
        if ref in by_ref:
            findings.error("structure", f"duplicate ref {ref!r}")
        by_ref[ref] = op

    roots = [op for op in one_pagers if op.get("level") == 0]
    if len(roots) != 1:
        findings.error("structure", f"expected exactly 1 level-0 one-pager, got {len(roots)}")
    for op in roots:
        if op.get("parentRef") is not None:
            findings.error("structure", f"{op.get('ref')}: level-0 must have parentRef null")

    for op in one_pagers:
        if is_child_level(op):
            parent = by_ref.get(op.get("parentRef"))
            if parent is None:
                findings.error(
                    "structure",
                    f"{op.get('ref')}: parentRef {op.get('parentRef')!r} does not resolve",
                )
                continue
            # A non-numeric parent level is check_envelope's finding, not this
            # walk's: the arithmetic would raise instead of reporting anything
            parent_level = numeric_level(parent)
            if parent_level is not None and op.get("level") != parent_level + 1:
                findings.error(
                    "structure",
                    f"{op.get('ref')}: level {op.get('level')} is not parent level + 1",
                )

    ids = []
    for op in one_pagers:
        collect_entity_ids(op.get("content", {}), ids)
    seen = set()
    for entity_id in ids:
        if not isinstance(entity_id, str) or not UUID_RE.match(entity_id):
            findings.error("structure", f"entity id {entity_id!r} is not a UUID")
        elif entity_id in seen:
            findings.error("structure", f"entity id {entity_id} is not unique")
        seen.add(entity_id)

    return by_ref


def check_links(bundle, methodology, by_ref, findings):
    links = bundle.get("links", [])

    # (parentRef, childRef, parentPath, childPath) identifies one propagation
    # row; a repeat would ask the product to insert the same accepted link
    # twice. Checked before the per-link rules — both copies are individually
    # well-formed, so nothing else would notice.
    seen = {}
    for i, link in enumerate(links):
        key = (
            link.get("parentRef"),
            link.get("childRef"),
            link.get("parentPath"),
            link.get("childPath"),
        )
        if key in seen:
            findings.error("links", f"links[{i}]: duplicate of links[{seen[key]}]")
        else:
            seen[key] = i

    for i, link in enumerate(links):
        label = f"links[{i}]"
        parent = by_ref.get(link.get("parentRef"))
        child = by_ref.get(link.get("childRef"))
        if parent is None or child is None:
            findings.error("links", f"{label}: parentRef/childRef does not resolve")
            continue
        if child.get("parentRef") != parent.get("ref"):
            findings.error(
                "links",
                f"{label}: {child.get('ref')} is not a child of {parent.get('ref')}",
            )
            continue

        rules = propagation_rules(methodology, parent.get("level"))
        parent_rule, child_rule = link.get("parentRule"), link.get("childRule")
        if rules.get(parent_rule) != child_rule:
            findings.error(
                "links",
                f"{label}: rule pair ({parent_rule!r} -> {child_rule!r}) is not "
                f"in the methodology's propagationRules for level {parent.get('level')}",
            )
            continue

        ok = True
        for role, rule, path, op in (
            ("parentPath", parent_rule, link.get("parentPath"), parent),
            ("childPath", child_rule, link.get("childPath"), child),
        ):
            if not path_matches_rule(path, rule):
                findings.error("links", f"{label}: {role} {path!r} does not match rule {rule!r}")
                ok = False
                continue
            _, found = resolve_path(op.get("content", {}), path)
            if not found:
                findings.error(
                    "links", f"{label}: {role} {path!r} does not resolve in {op.get('ref')}"
                )
                ok = False
        if not ok:
            continue

        parent_value, _ = resolve_path(parent.get("content", {}), link["parentPath"])
        child_value, _ = resolve_path(child.get("content", {}), link["childPath"])
        if parent_value != child_value:
            findings.error(
                "links",
                f"{label}: values differ — cascade must be a verbatim copy "
                f"({parent_value!r} vs {child_value!r})",
            )


def check_completeness(bundle, methodology, by_ref, findings):
    """Methodology-artifact-driven: core links for the static rules the parent
    fills, every child pillar derives from a parent initiative/enabler, and a
    cascading initiative reaches at most limits.criticalTeamsPerInitiative
    children. Dead-end initiatives reach none; enablers cascade only where
    adopted."""
    links = bundle.get("links", [])
    children = [op for op in bundle.get("onePagers", []) if is_child_level(op)]

    for child in children:
        ref = child.get("ref")
        parent = by_ref.get(child.get("parentRef"), {})
        parent_rules = propagation_rules(methodology, parent.get("level"))
        child_links = [l for l in links if l.get("childRef") == ref]

        for rule in static_rules(parent_rules):
            _, filled = resolve_path(parent.get("content", {}), rule)
            if filled and not any(l.get("parentRule") == rule for l in child_links):
                findings.error(
                    "completeness",
                    f"{ref}: missing core-field link {rule!r} "
                    f"(filled on {parent.get('ref')})",
                )

        pillars = (
            child.get("content", {}).get("pillars", {}).get("content", [])
        )
        targeted = {
            l["childPath"].split(".")[2]
            for l in child_links
            if l.get("childPath", "").startswith("pillars.content.")
        }
        for pillar in pillars:
            pillar_id = pillar.get("metadata", {}).get("id")
            if pillar_id not in targeted:
                findings.error(
                    "completeness",
                    f"{ref}: pillar {pillar_id} has no parent origin link — every "
                    "L1 pillar must derive from a parent initiative or enabler",
                )

    # Critical-team cap, per parent level (rule + cap from the methodology)
    by_parent_level = {}
    for link in links:
        parent = by_ref.get(link.get("parentRef"), {})
        by_parent_level.setdefault(parent.get("level"), []).append(link)

    for parent_level, level_links in by_parent_level.items():
        if level_entry(methodology, parent_level) is None:
            # Parent level the methodology does not define — including None,
            # from a link whose parentRef resolves to nothing. check_links
            # already reported it; without this skip the empty rule set would
            # send initiative_name_rule/level_limits into their exit 2 and the
            # reader would never see that report.
            continue
        rules = propagation_rules(methodology, parent_level)
        if not rules:
            # The deepest level cascades nothing downward, so it legitimately
            # carries no propagationRules (the packaged level 3 has limits and
            # zero rules) — there is no critical-team rule to count against.
            # A link parented on such a page is check_links' defect to report;
            # initiative_name_rule({}) would exit 2 and swallow that report.
            continue
        name_rule = initiative_name_rule(rules)
        cap = level_limits(methodology, parent_level)["criticalTeamsPerInitiative"]

        initiative_targets = {}
        for link in level_links:
            if link.get("parentRule") == name_rule:
                segments = link["parentPath"].split(".")
                if len(segments) < 6:
                    # Too short to carry an initiative id, so it cannot name a
                    # critical-team cascade — check_links already reported the
                    # path defect, and indexing here would raise instead
                    continue
                initiative_id = segments[5]
                initiative_targets.setdefault(initiative_id, set()).add(link["childRef"])
        for initiative_id, targets in initiative_targets.items():
            if len(targets) > cap:
                findings.error(
                    "completeness",
                    f"initiative {initiative_id} cascades to {len(targets)} children — "
                    f"critical teams are capped at {cap} per initiative (methodology limits)",
                )


def check_limits(bundle, methodology, findings):
    """Methodology element ceilings from hierarchy[].limits — warnings, not errors."""

    def entries(container, key):
        # Schema-invalid shapes (a scalar where a collection belongs) yield []
        # instead of crashing — check_content_schemas owns those defects, and
        # the ceiling warnings must never swallow the report.
        node = container.get(key) if isinstance(container, dict) else None
        content = node.get("content") if isinstance(node, dict) else None
        return content if isinstance(content, list) else []

    for op in bundle.get("onePagers", []):
        if level_entry(methodology, op.get("level")) is None:
            # A level the methodology does not define is a bundle defect that
            # check_content_schemas already reports ("no methodology level N").
            # Exiting 2 here would swallow the whole report and leave the
            # reader nothing to fix; the exit-2 below stays for the packaging
            # defect it names — a level that exists but carries no limits.
            continue
        ref = op.get("ref")
        content = op.get("content", {})
        limits = level_limits(methodology, op.get("level"))
        pillars = entries(content, "pillars")

        checks = [
            ("pillars", len(pillars), limits["pillars"]),
            ("enablers", len(entries(content, "enablers")), limits["enablers"]),
            ("values", len(entries(content, "values")), limits["values"]),
        ] + [
            (
                f"initiatives in pillar {p.get('name', {}).get('textValue')!r}",
                len(entries(p, "initiatives")),
                limits["initiativesPerPillar"],
            )
            for p in pillars
            if isinstance(p, dict) and isinstance(p.get("name"), dict)
        ]
        for label, count, maximum in checks:
            if count > maximum:
                findings.warning(
                    "limits",
                    f"{ref}: {count} {label} — methodology ceiling is {maximum}, prioritise",
                )


SKILL_VERSION_RE = re.compile(r"^version:\s*([^\s#]+)", re.M)


def skill_version(skill_dir):
    """The `version:` in the skill's own SKILL.md frontmatter, or None when the
    file is not beside the script — the connector packaging serves the scripts
    flat, without SKILL.md, and a missing file is not a bundle defect."""
    path = Path(skill_dir) / "SKILL.md"
    if not path.exists():
        return None
    match = SKILL_VERSION_RE.search(path.read_text(encoding="utf-8")[:2000])
    return match.group(1).strip().strip("\"'") if match else None


def check_skill_version(bundle, skill_dir, findings):
    """A bundle records the skill version that produced it. When it disagrees
    with the installed SKILL.md, the run worked from something other than this
    skill's frontmatter — typically by copying the version out of the
    output-contract reference's envelope example, which shows the version that
    contract shipped with. A warning, never an error: the bundle itself is
    still valid, and the version is metadata the import does not depend on."""
    stamped = (bundle.get("generator") or {}).get("skillVersion")
    installed = skill_version(skill_dir)
    if not installed or not stamped or stamped == installed:
        return
    findings.warning(
        "generator",
        f"generator.skillVersion is {stamped!r} but the installed skill is "
        f"{installed!r} — re-read SKILL.md and stamp the version it declares",
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    parser.add_argument(
        "--skill-dir",
        type=Path,
        default=Path(__file__).resolve().parent.parent,
        help="skill root containing cascade-bundle.schema.json and schemas/",
    )
    parser.add_argument(
        "--schema-engine",
        choices=("auto", "jsonschema", "builtin"),
        default="auto",
        help="schema-check engine (testing/debugging) — 'auto' uses the "
        "jsonschema package when importable, else the built-in checker; "
        "the full check set runs either way",
    )
    args = parser.parse_args()
    engine = resolve_schema_engine(args.schema_engine)

    methodology_path = args.skill_dir / "schemas" / "methodology.inlined.json"
    if not methodology_path.exists():
        sys.stderr.write(
            f"Missing {methodology_path} — the skill package is incomplete "
            "(schemas are generated at package time).\n"
        )
        return 2

    bundle = load_json(args.bundle)
    methodology = load_json(methodology_path)
    envelope_schema = load_json(args.skill_dir / "cascade-bundle.schema.json")

    if engine == "builtin":
        # Guard before any partial report: the built-in engine refuses to run
        # against a schema it cannot fully check.
        builtin_assert_supported(envelope_schema, "envelope")
        for entry in methodology.get("hierarchy", []):
            builtin_assert_supported(
                entry.get("onePagerSchema", {}), f"level-{entry.get('level')}"
            )

    findings = Findings()
    check_envelope(bundle, envelope_schema, findings, engine)
    check_fingerprint(bundle, args.skill_dir, findings)
    check_proposed_markers(bundle, findings)
    check_content_schemas(bundle, methodology, findings, engine)
    check_limits(bundle, methodology, findings)
    check_skill_version(bundle, args.skill_dir, findings)
    by_ref = check_structure(bundle, findings)
    if not findings.errors:
        check_links(bundle, methodology, by_ref, findings)
        check_completeness(bundle, methodology, by_ref, findings)

    findings.report()
    if engine == "builtin":
        print("schema engine: built-in (stdlib) — full check set ran")
    if findings.errors:
        return 1
    print("✅ bundle is valid")
    return 0


if __name__ == "__main__":
    sys.exit(main())
