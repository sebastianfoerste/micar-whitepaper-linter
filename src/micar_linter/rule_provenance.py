"""Machine-verifiable provenance ledger for every shipped MiCAR rule."""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from micar_linter.rules import RULESETS

SCHEMA = "micar-whitepaper-linter.rule-provenance.v1"
VERIFIED_ON = "2026-07-28"

OFFICIAL_SOURCES = {
    "EU-2023-1114": {
        "identifier": "Regulation (EU) 2023/1114",
        "celex": "32023R1114",
        "title": "Regulation on markets in crypto-assets",
        "official_url": "https://eur-lex.europa.eu/eli/reg/2023/1114/oj?locale=en",
        "role": "MiCAR articles and Annex I, II, and III disclosure requirements",
        "verified_on": VERIFIED_ON,
    },
    "EU-2024-2984": {
        "identifier": "Commission Implementing Regulation (EU) 2024/2984",
        "celex": "32024R2984",
        "title": "Implementing technical standards for crypto-asset white paper formats",
        "official_url": (
            "https://eur-lex.europa.eu/legal-content/EN/TXT/"
            "?uri=CELEX%3A32024R2984"
        ),
        "role": "Forms, formats, templates, and Inline XBRL tagging",
        "verified_on": VERIFIED_ON,
    },
}


def _canonical_sha256(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _source_id(rule_id: str) -> str:
    if rule_id == "COMMON.IXBRL_TAGGING":
        return "EU-2024-2984"
    return "EU-2023-1114"


def build_rule_provenance_manifest() -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    unmapped: list[str] = []
    for whitepaper_type, rules in sorted(RULESETS.items(), key=lambda item: item[0].value):
        for rule in rules:
            source_id = _source_id(rule.rule_id)
            if source_id not in OFFICIAL_SOURCES:
                unmapped.append(f"{whitepaper_type.value}:{rule.rule_id}")
                continue
            rule_payload = {
                **asdict(rule),
                "severity": rule.severity.label,
            }
            entries.append(
                {
                    "ruleset": whitepaper_type.value,
                    "rule_id": rule.rule_id,
                    "citation": rule.citation,
                    "section": rule.section,
                    "label": rule.label,
                    "severity": rule.severity.label,
                    "source_id": source_id,
                    "rule_sha256": _canonical_sha256(rule_payload),
                }
            )
    entries.sort(key=lambda entry: (entry["ruleset"], entry["rule_id"]))
    coverage = {
        "ruleset_entries": len(entries) + len(unmapped),
        "mapped_entries": len(entries),
        "unmapped_entries": len(unmapped),
        "unique_rule_ids": len({entry["rule_id"] for entry in entries}),
        "rulesets": len(RULESETS),
        "official_sources": len(OFFICIAL_SOURCES),
    }
    payload = {
        "schema": SCHEMA,
        "verified_on": VERIFIED_ON,
        "coverage": coverage,
        "unmapped": unmapped,
        "sources": OFFICIAL_SOURCES,
        "entries": entries,
        "review_gate": (
            "The ledger proves code-to-source-family coverage and rule integrity. "
            "A reviewer must still verify the current consolidated legal text and "
            "the substantive interpretation before reliance."
        ),
        "external_actions_allowed": False,
    }
    return {**payload, "overall_digest": _canonical_sha256(payload)}


def render_rule_provenance_manifest(manifest: dict[str, Any]) -> str:
    return json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"


def _validate(manifest: dict[str, Any]) -> None:
    coverage = manifest["coverage"]
    if coverage["ruleset_entries"] == 0:
        raise ValueError("rule provenance ledger contains no rule entries")
    if coverage["unmapped_entries"] != 0 or manifest["unmapped"]:
        raise ValueError("rule provenance ledger contains unmapped rules")
    if coverage["mapped_entries"] != coverage["ruleset_entries"]:
        raise ValueError("rule provenance coverage is incomplete")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="micar-rule-proof")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--output", type=Path, help="Write the deterministic ledger.")
    group.add_argument("--check", type=Path, help="Compare a committed ledger with a rebuild.")
    args = parser.parse_args(argv)

    manifest = build_rule_provenance_manifest()
    _validate(manifest)
    rendered = render_rule_provenance_manifest(manifest)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
        print(
            f"wrote {args.output}: {manifest['coverage']['mapped_entries']} "
            "mapped ruleset entries"
        )
        return 0

    if not args.check.is_file():
        print(f"missing committed rule provenance ledger: {args.check}")
        return 1
    if args.check.read_text(encoding="utf-8") != rendered:
        print("rule provenance drift: run `make rule-proof` and commit the ledger")
        return 1
    print(
        f"rule-provenance check passed: {manifest['coverage']['mapped_entries']} "
        "mapped ruleset entries"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
