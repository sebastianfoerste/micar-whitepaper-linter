# 0009. Marketing communications under Art. 7 MiCAR

Status: Accepted (2026-11-25). The owner chose the feature on 2026-11-25 (rank 1 of the [competitive update](../research/2026-11-competitive-update.md)). The rule IDs, the severities and the CLI shape below are the build's choices; until the owner releases them, they can still change, and after a release the IDs are stable.

## Context

Every Title II notification travels with marketing communications: the FMA's upload list names them next to the white paper and the Art. 8(4) explanation, and Art. 8(2) MiCAR has them notified on request. Art. 143(2)(a) applies Art. 7 to the marketing communications of crypto-assets admitted to trading before 30 December 2024 as well. ESMA's response to the MiCA review (30 September 2026, section 3.5) reports "extensive and disputable marketing activities". The research found no checker that compares a marketing communication with its white paper.

Art. 7(1) MiCAR sets five requirements for a marketing communication about a crypto-asset other than an ART or EMT, read in the Official Journal text in English and German on 2026-11-25: (a) clearly identifiable as such; (b) fair, clear and not misleading; (c) consistent with the white paper; (d) a clear statement that a white paper has been published, with the website of the offeror, the person seeking admission to trading or the operator of the trading platform, a telephone number and an e-mail address; (e) a prescribed statement, whose second subparagraph puts the person seeking admission or the operator in place of the offeror. Art. 7(2) bars dissemination before the white paper is published. Art. 29 (ARTs) and Art. 53 (EMTs) set requirements of their own; the fixed statement of Art. 7(1)(e) appears only in Art. 7.

## Options

1. **A second kind of document in the same engine.** The communication is parsed into one section of the existing `Whitepaper` model, and the rules run through `Linter`, so the report, JSON, SARIF, summary, annotations, `--strict` and the rule pages work unchanged.
2. **A separate model and engine.** Cleaner names, but every output and the rule-page generator would need a second path.
3. **Checks inside the white paper rule set.** A white paper draft does not contain its marketing communications, so this does not fit.

## Decision

Option 1.

- **Input.** `micar-lint FILE --marketing [--whitepaper WP]`. `load_marketing_communication` (`whitepaper.py`) reads JSON (`title`, `text`, optional `type`, which must be `other`), Markdown, text, HTML, XHTML, DOCX or PDF, and keeps the text a reader sees (`shown_text` where the loaders tell hidden text apart), so hidden text cannot satisfy a check. The text goes into the section `marketing_communication`. The reserved metadata keys `document_kind` and `reference_text` (the white paper's title, sections and file text) are set only by that loader; a JSON communication cannot set them.
- **Rules** (`rules/marketing.py`, logic in `linter.py`, text helpers in `marketing_checks.py`), in the order of Art. 7(1):

  | Rule | Point | Severity | Checks |
  |---|---|---|---|
  | `MARKETING.IDENTIFIABLE` | (a) | MAJOR | a marketing label in the title or the first 40 words |
  | `MARKETING.MISLEADING_CLAIMS` | (b) | MAJOR | listed claims (guaranteed return, no risk, rising price, approval), English and German, named by pattern, never by the matched text |
  | `MARKETING.CONSISTENCY` | (c) | MAJOR | every LEI, nine-character code, e-mail address, web host, international telephone number, date, percentage and amount of the communication is found in the white paper |
  | `MARKETING.WHITE_PAPER_AND_CONTACT` | (d) | BLOCKER | the published-white-paper statement, a website, a telephone number and an e-mail address |
  | `MARKETING.NOT_REVIEWED_STATEMENT` | (e) | BLOCKER | the statement word for word, in English or German by the draft's language, with one of the three persons |

  BLOCKER here means that an open finding should keep the communication from being disseminated until it is cured; (d) and (e) are fixed requirements that the text either meets or not. The other three are judgments the check can only prompt, so they are MAJOR.
- **Not run.** Without `--whitepaper`, `MARKETING.CONSISTENCY` gives no finding (`runs_on`), the report adds one note and the `--json`, SARIF and summary outputs name it under `not_run`, as for the field-level rules of ADR 0005.
- **Outputs.** The text report names the document and Art. 7 MiCAR in its header and footer; the JSON report and the SARIF run properties add `document_kind` for a marketing report only, so white paper reports keep their keys. `MARKETING.CONSISTENCY` quotes draft values, so it joins `DRAFT_ECHO_RULES` and CI outputs show a fixed sentence (ADR 0001). The review table, bundle, coverage, audit log, manifest, remediation, workspace, collaboration and batch modes refuse `--marketing` with exit 2 until they are built for it.
- **No never-pass gate.** A communication that meets all five checks passes, and `--strict` exits 0 on it.

## Consequences

- Five new rule IDs under `MARKETING.*`, which collides with no other namespace, with generated rule pages (`scripts/build_rule_docs.py`, `SOURCE_MODULES["MARKETING"]`) and a "not yet run against a real marketing communication" note (`UNTESTED_REGIMES`).
- Art. 7(2) (no dissemination before the white paper is published) is not checked: a communication carries no dissemination date the linter could compare with the white paper's publication date (Table 2 field F.10). A later flag could supply one.
- Art. 29 and Art. 53 are not covered; `--type art|emt` with `--marketing` exits 2. A later variant would add rule sets for those regimes under the same IDs where the requirement is the same.
- The playground does not offer marketing checks yet. The GitHub Action has no input of its own for them: with the communication as its `whitepaper` input and `extra-args: --marketing --whitepaper <path>`, it runs them and writes its SARIF log, summary and annotations.

## Non-negotiables check

- No model and no network call: the checks are regular expressions and comparisons on local text.
- Fail closed: an empty or placeholder text is Missing for every rule; consistency does not pass without a white paper, it does not run.
- Outputs without draft text: CI outputs replace the consistency issue with a fixed sentence; claims are reported by name.
- A pass is never described as compliance: the report says "All checked items present. Lawyer review still required."
