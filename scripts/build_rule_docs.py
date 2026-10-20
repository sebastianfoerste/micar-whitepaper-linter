#!/usr/bin/env python3
# ruff: noqa: E501  (HTML templates keep one element per line)
"""Generate one static page per rule in docs/rules/ from the Rule objects.

Every example on a page is a synthetic draft that is linted while the page is
built; the build stops if a result differs from the status the page states.
tests/test_rule_docs.py regenerates the pages and fails when the committed
copy is stale. Run: uv run python scripts/build_rule_docs.py
"""

from __future__ import annotations

import html
import json
import sys
from dataclasses import dataclass
from pathlib import Path

from micar_linter import __version__, citations
from micar_linter.linter import Linter
from micar_linter.rules import RULESETS
from micar_linter.rules.base import Rule
from micar_linter.whitepaper import Whitepaper, WhitepaperType

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "rules"
REPO = "https://github.com/sebastianfoerste/micar-whitepaper-linter"

REGIME_NAMES = {
    WhitepaperType.OTHER: "Annex I · other crypto-assets",
    WhitepaperType.ART: "Annex II · asset-referenced tokens",
    WhitepaperType.EMT: "Annex III · e-money tokens",
}
SOURCE_MODULES = {
    "COMMON": "common.py",
    "ANNEX_I": "annex_i.py",
    "ANNEX_II": "annex_ii.py",
    "ANNEX_III": "annex_iii.py",
}
# Citations were not re-read against the Official Journal when these pages were generated.
VERIFICATION_NOTE = (
    "Not re-verified when these pages were generated (2026-10-20): EUR-Lex was unreachable from the "
    "build environment. The citation is the rule's own, unchanged."
)
FILLER = "This synthetic sentence only adds length and states no fact about any issuer or token."
NEVER_PASS = {"COMMON.IXBRL_TAGGING", "ANNEX_II.G.DEPOSIT_FLOOR_REVIEW"}
UNTESTED_REGIMES = {
    "ANNEX_II": "The Annex II rules have not yet been run against a real ART white paper.",
    "ANNEX_III": "The Annex III rules have not yet been run against a real EMT white paper.",
}


@dataclass(frozen=True)
class Example:
    title: str
    expected: str
    draft: dict
    note: str


def regimes_by_rule() -> dict[str, list[WhitepaperType]]:
    found: dict[str, list[WhitepaperType]] = {}
    for regime, rules in RULESETS.items():
        for rule in rules:
            found.setdefault(rule.rule_id, []).append(regime)
    return found


def all_rules() -> list[Rule]:
    seen: dict[str, Rule] = {}
    for rules in RULESETS.values():
        for rule in rules:
            seen.setdefault(rule.rule_id, rule)
    return list(seen.values())


def _passing_text(rule: Rule) -> str:
    sentence = (
        "Synthetic example naming " + ", ".join(rule.required_terms) + "." if rule.required_terms else ""
    )
    words = sentence.split()
    while len(words) < rule.min_words:
        words += FILLER.split()
    return " ".join(words)


def _draft(rule: Rule, regime: WhitepaperType, text: str, **metadata: object) -> dict:
    draft: dict = {"title": "Synthetic rule example", "type": regime.value}
    draft.update(metadata)
    draft["sections"] = {rule.section: text}
    return draft


def examples(rule: Rule, regime: WhitepaperType) -> list[Example]:
    if rule.rule_id == "COMMON.IXBRL_TAGGING":
        return [
            Example(
                "Any JSON draft",
                "missing",
                _draft(rule, regime, ""),
                "A JSON, DOCX, PDF or Markdown draft cannot carry Inline XBRL, so the blocker stays open. "
                "An XHTML file is checked for the Inline XBRL 1.1 and ESMA MiCA taxonomy namespaces and "
                "then shows Review, because tag completeness needs a taxonomy validator.",
            )
        ]
    if rule.rule_id == "ANNEX_II.G.DEPOSIT_FLOOR_REVIEW":
        flags = {
            "references_official_currency": True,
            "art_significant": False,
            "article_45_7b_required_by_authority": False,
        }
        return [
            Example(
                "Characterisation not stated",
                "review",
                _draft(rule, regime, "The reserve is held in deposits."),
                "The draft does not state the three characterisation flags, so no candidate floor applies yet.",
            ),
            Example(
                "Flags stated, no percentage",
                "missing",
                _draft(rule, regime, "The reserve is held in deposits.", **flags),
                "The flags point to a candidate floor, but the section states no deposit share.",
            ),
            Example(
                "Flags stated, percentage present",
                "review",
                _draft(rule, regime, "The issuer keeps 40% of the reserve in deposits.", **flags),
                "A percentage is detected and listed for a lawyer. The check never decides whether it meets "
                "a floor.",
            ),
        ]
    result = [
        Example(
            "Section absent",
            "missing",
            {"title": "Synthetic rule example", "type": regime.value, "sections": {}},
            "The section key is missing or empty.",
        ),
    ]
    thin = " ".join(rule.required_terms) or "Short."
    if len(thin.split()) < rule.min_words:
        result.append(
            Example(
                "Thin section",
                "review",
                _draft(rule, regime, thin),
                f"Every listed term appears, but the section is shorter than {rule.min_words} words.",
            )
        )
    result.append(
        Example(
            "Section that matches",
            "pass",
            _draft(rule, regime, _passing_text(rule)),
            "This text passes and shows what the check measures: listed terms and length. It is not "
            "model disclosure wording and does not meet MiCAR.",
        )
    )
    return result


def lint_example(rule: Rule, example: Example) -> str:
    draft = example.draft
    metadata = {k: v for k, v in draft.items() if k not in ("title", "type", "sections")}
    metadata["ixbrl_validated"] = False
    whitepaper = Whitepaper(
        title=draft["title"],
        type=WhitepaperType(draft["type"]),
        sections=dict(draft["sections"]),
        metadata=metadata,
    )
    return Linter((rule,)).lint(whitepaper)[0].status


def _e(text: object) -> str:
    return html.escape(str(text), quote=True)


def _page(title: str, description: str, body: str, *, root: str = "../") -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="{_e(description)}">
<title>{_e(title)}</title>
<link rel="stylesheet" href="{root}assets/site.css">
</head>
<body>
<a class="skip-link" href="#main">Skip to content</a>
<header class="site-header">
  <a class="brand" href="{root}"><span class="brand-mark" aria-hidden="true">M</span><span>MiCAR <strong>Whitepaper Linter</strong></span></a>
  <nav aria-label="Site"><a href="{root}">Overview</a><a href="{root}rules/">Rules</a><a href="{root}playground/">Playground</a><a href="{REPO}">Source</a><button class="theme-toggle" type="button" data-theme-toggle aria-pressed="false">Dark theme</button></nav>
</header>
<main id="main">
{body}
</main>
<footer><span>MiCAR Whitepaper Linter {_e(__version__)} · MIT licence · First-pass screening, not legal advice.</span><span>Generated from the rule set by <code>scripts/build_rule_docs.py</code>.</span></footer>
<script src="{root}assets/theme.js" defer></script>
</body>
</html>
"""


def _status_badge(status: str) -> str:
    return f'<span class="badge {status}">{_e(status.capitalize())}</span>'


def _terms(terms: tuple[str, ...]) -> str:
    return ", ".join(f"<code>{_e(t)}</code>" for t in terms) if terms else "none"


def status_logic(rule: Rule) -> str:
    if rule.rule_id == "COMMON.IXBRL_TAGGING":
        return (
            '<ul class="plain"><li><strong>Missing</strong>: the draft is JSON, DOCX, PDF or Markdown.</li>'
            "<li><strong>Review</strong>: the draft is XHTML. The check reports namespace problems and always adds "
            "that tag completeness was not checked.</li><li><strong>Pass</strong>: never. This is a fail-closed "
            "format gate.</li></ul>"
        )
    if rule.rule_id == "ANNEX_II.G.DEPOSIT_FLOOR_REVIEW":
        return (
            '<ul class="plain"><li><strong>Review</strong>: a characterisation flag '
            "(<code>references_official_currency</code>, <code>art_significant</code>, "
            "<code>article_45_7b_required_by_authority</code>) is missing or not a boolean; the draft states the "
            "token references no official currency; or a percentage is found in the section.</li>"
            "<li><strong>Missing</strong>: the flags determine a candidate floor and the section states no "
            "percentage.</li><li><strong>Pass</strong>: never. Draft flags are assertions pending lawyer "
            "confirmation, not trusted facts.</li></ul>"
        )
    parts = [
        f"<li><strong>Missing</strong>: section <code>{_e(rule.section)}</code> is absent or empty.</li>",
        "<li><strong>Review</strong>: the section has fewer than "
        f"{rule.min_words} words, or a listed term does not appear (case-insensitive substring match).</li>",
    ]
    if rule.required_patterns or rule.prohibited_patterns:
        parts.append(
            "<li>Review also follows when a required pattern is absent or a prohibited pattern matches.</li>"
        )
    parts.append(
        "<li><strong>Pass</strong>: none of the above. A pass means the check matched, nothing more.</li>"
    )
    return '<ul class="plain">' + "".join(parts) + "</ul>"


def rule_page(rule: Rule, regimes: list[WhitepaperType]) -> str:
    family = rule.rule_id.split(".")[0]
    citation_en = citations.to_english(rule.citation)
    sources = "".join(
        f'<li><a href="{_e(url)}">{_e(url)}</a></li>' for url in citations.source_urls(rule.citation)
    )
    limitations = [
        f"Reads one section key, <code>{_e(rule.section)}</code>. Text elsewhere in the draft is not considered.",
        (
            "Reads draft metadata and percentages only. It does not test accuracy or decide whether a floor is met."
            if rule.rule_id == "ANNEX_II.G.DEPOSIT_FLOOR_REVIEW"
            else "Checks the file format and taxonomy namespace only, not tag completeness."
            if rule.rule_id == "COMMON.IXBRL_TAGGING"
            else "Matches words and counts length. It does not test accuracy, consistency with other sections or "
            "the point-level items of the cited Part."
        ),
        "Status and severity are fixed by the rule. A draft cannot waive or downgrade them.",
    ]
    if family in UNTESTED_REGIMES:
        limitations.append(UNTESTED_REGIMES[family])
    if rule.rule_id in NEVER_PASS:
        limitations.append("This rule never reports Pass.")
    example_html = []
    for example in examples(rule, regimes[0]):
        actual = lint_example(rule, example)
        if actual != example.expected:
            raise SystemExit(
                f"{rule.rule_id}: example '{example.title}' gives {actual}, page states {example.expected}"
            )
        example_html.append(
            f'<div class="example"><div class="example-head">{_status_badge(example.expected)}'
            f'<strong>{_e(example.title)}</strong></div><p class="small muted">{_e(example.note)}</p>'
            f"<pre><code>{_e(json.dumps(example.draft, indent=2, ensure_ascii=False))}</code></pre></div>"
        )
    body = f"""<p class="eyebrow">Rule · {_e(rule.severity.label)}</p>
<h1>{_e(rule.rule_id)}</h1>
<p class="lede">{_e(rule.label)}</p>
<div class="panel"><dl class="facts">
<dt>Citation</dt><dd>{_e(citation_en)}</dd>
<dt>Canonical form</dt><dd lang="de">{_e(rule.citation)}</dd>
<dt>Runs for</dt><dd>{_e("; ".join(REGIME_NAMES[r] for r in regimes))}</dd>
<dt>Severity if open</dt><dd>{_e(rule.severity.label)}</dd>
<dt>Section key</dt><dd><code>{_e(rule.section)}</code></dd>
<dt>Minimum words</dt><dd>{rule.min_words}</dd>
<dt>Listed terms (English)</dt><dd>{_terms(rule.required_terms)}</dd>
<dt>Listed terms (German)</dt><dd lang="de">{_terms(rule.required_terms_de)}</dd>
<dt>Present in</dt><dd>Release {_e(__version__)}</dd>
<dt>Source</dt><dd><a href="{REPO}/blob/main/src/micar_linter/rules/{SOURCE_MODULES[family]}">rules/{SOURCE_MODULES[family]}</a></dd>
</dl></div>
<h2>How the status is set</h2>
{status_logic(rule)}
<h2>Legal basis</h2>
<p>{_e(citation_en)}</p>
<ul class="plain">{sources}</ul>
<p class="callout">{_e(VERIFICATION_NOTE)}</p>
<h2>Synthetic examples</h2>
<p class="small muted">Each example is linted when this page is generated. The build fails if a result differs.</p>
{"".join(example_html)}
<h2>Limitations</h2>
<ul class="plain">{"".join(f"<li>{item}</li>" for item in limitations)}</ul>
<p class="small muted">Disagree with this rule, or missing one? <a href="{REPO}/issues/new?template=rule-proposal.yml">Propose a rule change</a>.</p>
"""
    return _page(f"{rule.rule_id}: MiCAR Whitepaper Linter rule", f"{rule.label}. {citation_en}.", body)


def index_page(rules: list[Rule], regimes: dict[str, list[WhitepaperType]]) -> str:
    sections = []
    for regime, name in REGIME_NAMES.items():
        rows = "".join(
            f'<tr><td><a href="{_e(rule.rule_id)}.html"><code>{_e(rule.rule_id)}</code></a></td>'
            f"<td>{_e(rule.label)}</td><td>{_e(rule.severity.label)}</td>"
            f"<td>{_e(citations.to_english(rule.citation))}</td></tr>"
            for rule in RULESETS[regime]
        )
        sections.append(
            f'<h2>{_e(name)} <span class="muted small">({len(RULESETS[regime])} rules)</span></h2>'
            '<div class="table-wrap"><table><thead><tr><th scope="col">Rule</th><th scope="col">Checks for</th>'
            f'<th scope="col">Severity</th><th scope="col">Citation</th></tr></thead><tbody>{rows}</tbody></table></div>'
        )
    body = f"""<p class="eyebrow">Rule reference</p>
<h1>Rules</h1>
<p class="lede">{len(rules)} deterministic checks, generated from the rule set of release {_e(__version__)}. Each page
states the citation, how the status is set, synthetic examples that are tested on every build, and the limits of the
check.</p>
<p class="callout">A pass means a check matched. It is not a compliance opinion. Not legal advice.</p>
{"".join(sections)}
"""
    return _page(
        "Rules: MiCAR Whitepaper Linter", "Reference pages for every MiCAR Whitepaper Linter rule.", body
    )


def build_pages() -> dict[str, str]:
    regimes = regimes_by_rule()
    rules = all_rules()
    pages = {f"{rule.rule_id}.html": rule_page(rule, regimes[rule.rule_id]) for rule in rules}
    pages["index.html"] = index_page(rules, regimes)
    return dict(sorted(pages.items()))


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    pages = build_pages()
    for stale in OUT.glob("*.html"):
        if stale.name not in pages:
            stale.unlink()
    for name, text in pages.items():
        (OUT / name).write_text(text, encoding="utf-8")
    print(f"wrote {len(pages)} pages to {OUT.relative_to(ROOT)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
