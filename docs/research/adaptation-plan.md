# Adaptation plan (October 2026)

Mode: `build`. Branch: `feat/competitive-adaptation-2026-10`. Run started 2026-10-20 08:35 UTC.
Sources: [competitive landscape](2026-10-competitive-landscape.md), [design teardown](design-teardown.md), [feature matrix](feature-matrix.csv). Evidence tags: **Observed**, **Claimed**, **Inferred**; access date 2026-10-20 throughout.

This plan adapts patterns; it copies no competitor asset, text or rule. Not legal advice.

## Baseline

Recorded before any change, on commit `ee15693`.

| Item | Result |
|---|---|
| `make install`, `make check` (Python 3.13.16, Node 22.22.0, uv 0.11.32) | Green: ruff clean, 254 passed and 1 skipped, smoke, review bundle, 12 Node tests, starter contract |
| `make demo` (`examples/incomplete.json`, an ART draft) | Exit 0. Pass 0, review 13, missing 5, blockers 15 |
| `micar-lint examples/incomplete.json --json` | Exit 0 |
| `micar-lint examples/numbered-other-draft.xhtml --type other` | Exit 0 |
| Same file without `--type` | Exit 1: refusal asking for the regime (never inferred) |
| `--review-bundle-dir /tmp/micar-bundle` | Exit 0 |
| Action command `uvx --from . micar-lint examples/incomplete.json --strict` | Exit 1 (open blockers) |
| `micar-lint examples/art-stablecoin.json --strict` | Exit 1: the iXBRL format gate and three reserve rules stay open |
| Playground runtime | `cdn.jsdelivr.net` and `*.github.io` refused (proxy 403). Ran under a **local route**: Pyodide 0.28.2 from npm plus `micropip`, `lxml` and `typing_extensions` wheels from the 0.28.2 release tarball, served with Playwright `context.route` |
| Time to ready (local route, 3 cold loads at 1440 px) | 3.0 s, 3.1 s, 3.2 s; median 3.1 s |
| Transfer size | 1.35 MB of page-level responses. Worker fetches (Pyodide core) are not counted by the page listener, so the real cold load is larger; not measured in this run |
| axe-core 4.x, WCAG 2.0/2.1/2.2 A and AA tags, 13 states × 2 widths | 1 **serious** violation in every state: `label-content-name-mismatch` on the brand link (its `aria-label` did not contain the visible text). No critical violations |
| Python 3.14 | `uv python install 3.14` worked; suite green on 3.14.6 after the changes |
| Prior research | `grep -ril "competitor\|landscape" docs studies` found nothing |

States captured at 1440×900 and 390×844 (git-ignored, `research/_captures/baseline/`): empty, example run, each filter, expanded, stale, malformed JSON, XHTML regime prompt, XHTML run, runtime failure (CDN route aborted).

### Briefing corrections

1. `SOURCE_DATE_EPOCH` is read by `review_table.py` and `collaboration_workspace.py`; `workspace.py` has no timestamp code of its own.
2. The text report's closing paragraph cites Art. 8, 16, 17, 18 and 51 in the German form (`Art. 8 Abs. 1 …`) whatever `--citation-style` says (`report.py`, `render_text`). Same class of drift as the German citations in `reports/sample-*.txt`.
3. `.github/ISSUE_TEMPLATE/rule-proposal.yml` already exists; the rule pages link to it rather than adding a second template.
4. `examples/incomplete.json` is an ART draft, so `make demo` shows the 18 ART rules.
5. Pyodide 0.28.2's distribution has no `python-docx` (checked against the release tarball), so H5 needs a vendored wheel, as the hypothesis assumed.
6. The Action's `uvx --from "${GITHUB_ACTION_PATH}"` build is cached by uv on `pyproject.toml`, not on `src/`. Locally, uvx reused a stale build of the same version until `--no-cache` was passed. A moved `v1` tag without a version bump could hit this on a runner with a restored uv cache.
7. The baseline playground already carried one serious axe violation (above).

Everything else in the briefing matched the code: 16/18/14 rules, the two never-pass rules, eight CLI flags missing from `docs/API.md`, `displayCitation` as `TODO(human)`, unpinned `setup-uv@v5` in `action.yml`, no `docs/index.html`, no `docs/adr/`.

## What the research found

1. No reachable MiCA product publishes its check logic. Every vendor site was unreachable; snippets describe START as validating against "the full MiCAR ITS rulebook" (**Claimed**). Our published rules and tested examples are a clear contrast.
2. Arelle has no MiCA plugin, and issue #1898 asking for MiCA reporting-manual rules is open with no PR (**Observed**). Arelle can run formula assertions offline with local packages (**Observed**), but excludes `lxml==6.0.0`, the only lxml in Pyodide 0.28.2 (**Observed**), so it is CLI-only for us.
3. The one reachable open tool that implements the taxonomy assertions, WhitePaperXBRL, hand-codes 488 checks with stable IDs, processes uploads server-side, and treats a failed GLEIF lookup as a valid LEI (**Observed** in its docs).
4. The repo's namespace `https://www.esma.europa.eu/taxonomy/2025-03-31/mica/` matches four published white-paper files on GitHub (**Observed**); the entry-point schema path uses the other order, `taxonomy/mica/2025-03-31/` (**Observed**).
5. SARIF code scanning needs `security-events: write`, is limited to public repositories or GitHub Code Security, and uses only `primaryLocationLineHash` from fingerprints; `helpUri` is not documented by GitHub (**Observed**, github/docs source). Fork PRs cannot upload by default (**Inferred**).
6. Workflow-command annotations need no permissions and work on forks (**Observed**); the 10-per-step caps are **Claimed** (reviewdog issue only). Step summaries are capped at 1 MiB per step (**Observed**).
7. ESLint runs every rule-doc example in CI (**Observed**); Ruff checks doc headings only (**Observed**). Rule pages with executed examples are the strongest pattern for a legal rule set.
8. Ruff's playground autosaves to `localStorage` and stores shared code in a key-value store without expiry (**Observed**): reject for drafts.
9. reviewdog's annotation example copies raw tool output into the annotation (**Observed**); our outputs must not echo draft text.
10. CUAD and LegalBench report point metrics without confidence intervals (**Observed**); publishing Wilson intervals would go further than both.

## Candidates

Rank = Impact × evidence weight (Observed 3, Claimed 2, Inferred 1) ÷ effort (S 1, M 2, L 4). Fit is checked against the non-negotiables.

| ID | Candidate | Impact | Fit | Effort | Evidence | Differentiation | Rank | Decision |
|---|---|---|---|---|---|---|---|---|
| H1 | SARIF, step summary, annotations in the Action | 5 | pass | M | Observed (github/docs, reviewdog, Ruff `github` format) | table stakes for linters, new for MiCA | 7.5 | **Built** |
| H2 | Generated rule pages with executed examples | 5 | pass | M | Observed (ESLint, Ruff, DQC) | differentiator | 7.5 | **Built** |
| H10 | Wilson 95% intervals in `micar-review-summary` | 2 | pass | S | Observed (CUAD, LegalBench lack them) | differentiator once labels exist | 6 | Spec, next |
| H11 | LEI check digits and issuer identity consistency | 4 | pass | M | Observed (WhitePaperXBRL mod-97) | differentiator if fail-closed | 6 | **Built** (swapped in for H7 at the owner's request, 2026-10-21) |
| H8 | Point-level rules | 5 | fail (this run: point citations unverifiable; see Needs owner decision) | L | Observed (WhitePaperXBRL field-level) | table stakes for filing tools | 3.75 | Parked: needs EUR-Lex verification |
| H6 | Landing page | 3 | pass | S | Inferred | table stakes | 3 | **Built** (design) |
| H7 | Dark mode with tokens, no storage | 2 | pass | M | Observed (Ruff playground theme) | table stakes | 3 | Built, then **removed** at the owner's request (2026-10-21) for H11 |
| H3 | Inline section highlight and structural quick-fixes | 4 | pass | L | Observed (Ruff playground, Ruff fix safety) | differentiator | 3 | Spec + Proposed ADR |
| H5 | Browser DOCX import | 3 | pass | M | Inferred | differentiator | 1.5 | Spec; kill test pending |
| H9 | Arelle formula assertions (CLI extra) | 3 | fail (this run: new extra changes `pyproject.toml`/`uv.lock`; see Needs owner decision) | L | Observed | differentiator | 2.25 | Proposed ADR |
| D4 | Load progress and "format gate only" state | 2 | pass | S | Inferred | polish | 2 | Spec |
| H4 | English citations in the browser | 4 | fail (`displayCitation` is `TODO(human)`; see Needs owner decision) | S | Observed (CLI already renders them) | table stakes | — | Owner decision (`TODO(human)`) |

Budget: 4 items built, all Fit = pass, effort S or M. Since 2026-10-21 these are 3 features (H1, H2, H11) and 1 design upgrade (H6): the owner swapped dark mode (H7) for H11, which restores rank order.

**Correction (audit follow-up, 2026-10-21).** The selection departed from rank order. The budget allowed up to 3 features and up to 2 design upgrades within 4 items, so H11 (rank 6) or H10 (rank 6) fitted as a third feature beside one design upgrade, and should have been built ahead of H7 (rank 3). The earlier note here, that the cap "left no slot", misread the budget. H7 was kept because it was finished and tested before the error was found; swapping it for H11 is listed under Needs owner decision. The axe fix on the brand link (D3) was a one-attribute change made inside H7, not a fifth item.

## Anti-patterns

Vendors are named only where the behaviour was **Observed**.

| Anti-pattern | Where seen | Principle it breaks |
|---|---|---|
| A readiness score or status with no published checks | MiCAOracle returns a readiness score and traffic lights; its 18 checks are not published (README, Observed) | Cited, reviewable findings; "report language is load-bearing" |
| A human approval that turns a status green | MiCAOracle: approval upgrades the light to GREEN (README, Observed) | A waiver shows `waived`, never `pass`, and keeps the exit code |
| Failing open on an external lookup | WhitePaperXBRL treats a failed GLEIF lookup as a valid LEI (docs, Observed) | Fail closed |
| Compliance badges and production claims around stub logic | mica-crypto-mcp: README shows a compliance badge and describes the package as production-ready while the white-paper tool returns `"status": "stub"` (code, Observed) | Never call a pass, or a tool, "compliant" |
| Server-side processing of uploaded drafts | WhitePaperXBRL (in memory, Observed); MiCAOracle is remote-only (Observed) | "Nothing you paste leaves the page" |
| Share links and autosaved editor state | Ruff playground: `localStorage` autosave and stored share links without expiry (source, Observed) | No persisted drafts, no share links |
| Raw tool output echoed into CI annotations | reviewdog annotation example (Observed) | CI outputs carry no draft text |
| "Full rulebook" claims without published logic | Seen only as a **Claimed** snippet; no vendor named | Published logic, tested examples |
| Agents rewriting disclosure text | No Observed instance (Markup AI unreachable) | No generated disclosure text; no model in the checking path |

## Positioning

Where this repo should beat everyone: **the only MiCA white-paper checker whose every rule is published, cited, executed against tested examples, and run where the draft already lives** (browser tab, laptop, or the issuer's own CI), with outputs that never carry draft text and statuses that fail closed. The evidence supports this narrowly. No reachable competitor publishes its checks (finding 1), the closest open tool fails open on LEIs and uploads drafts to a server (finding 3), and the open-source MiCA tools found are stubs or remote-only (landscape A.3). The claim does not extend to iXBRL filing validation: commercial filing tools and WhitePaperXBRL implement the taxonomy assertions and we do not. Until the 150 study cells are reviewed, the repo should also not claim accuracy.

## Feature specs

### F1. CI outputs for the Action (H1), built

- **User story.** As an issuer team keeping a draft in Git, I see open findings on the PR and in the run summary without opening the log, and my security team can see them in code scanning.
- **References.** GitHub SARIF support and workflow commands (github/docs source, Observed); reviewdog reporters (Observed); Ruff `github` output format (Observed).
- **Adapted.** Three CLI outputs (`--sarif-output`, `--summary-output`, `--annotations-output`) rendered from the report. Messages carry rule ID, status, severity, English citation, line and rule-page link, never draft text: issue messages of `COMMON.IXBRL_TAGGING` and `ANNEX_II.G.DEPOSIT_FLOOR_REVIEW` can quote draft content (percentages, namespaces, parser errors), so they are replaced by a fixed sentence. The format gate is in SARIF (tag `format-gate`) and the summary, not in annotations. Summary and annotations are on by default; SARIF upload is opt-in. No status, severity or exit code changes. See [ADR 0001](../adr/0001-ci-outputs-sarif-mapping.md).
- **Differs from donors.** reviewdog copies raw output into annotations; Ruff annotates every finding; we cap at 10 and keep the summary as the full list.
- **Acceptance.** Byte-identical outputs on repeated runs; SARIF rules list every rule with `helpUri`; one result per open finding; a draft with a marker string never shows it in any output; `--strict` exit codes unchanged; every `uses:` pinned by SHA.
- **Files.** `src/micar_linter/ci_outputs.py`, `locations.py`, `cli.py`, `action.yml`, `tests/test_ci_outputs.py`.
- **Risk.** SARIF upload fails on forks and on private repos without Code Security: opt-in and documented. Annotation caps are Claimed.

### F2. Rule pages (H2), built

- **User story.** As a reviewing lawyer, I can open any finding's rule and see the citation, how the status is set, what passes and what fails, and the rule's limits.
- **References.** ESLint `check-rule-examples.js` (Observed); Ruff "What it does / Why is this bad" sections and "Added in" (Observed); DQC rule docs citing regulator text (Observed).
- **Adapted.** `scripts/build_rule_docs.py` renders `docs/rules/<RULE_ID>.html` and an index from the `Rule` objects. Each synthetic example is linted at build time and in `tests/test_rule_docs.py`, which also fails on stale pages. The passing example is deliberately filler text that shows the check is lexical; never-pass rules publish no passing example. Citations carry a "not re-verified in this run" note. See [ADR 0002](../adr/0002-generated-rule-pages.md).
- **Differs from donors.** Examples show statuses, not lint errors, and say plainly that a passing example is not model disclosure wording.
- **Acceptance.** One page per rule; every example's stated status equals the linter's; committed pages equal regenerated pages; axe clean at 1440 and 390 px in both themes.
- **Risk.** Readers could reuse the passing filler text. Mitigated by the explicit note and by content that states no facts.

### F3. LEI check digits and identity consistency (H11), built 2026-10-21

- **User story.** As a first-pass reviewer, I learn when an LEI in the draft fails its check digits, or when the issuer's LEI differs between sections.
- **References.** WhitePaperXBRL LEI mod-97 checks (Observed); its GLEIF fail-open is the anti-pattern to avoid.
- **Built as.** Two new rules that run for every regime, both MAJOR, both offline (`src/micar_linter/lei.py`):
  - `COMMON.LEI_CHECK_DIGITS`: Missing when the draft contains no LEI-shaped code (fail closed); Review when a code fails the ISO/IEC 7064 MOD 97-10 check digits; Pass when every code is well formed. A purely numeric 20-digit run counts only right after an LEI label.
  - `COMMON.LEI_CONSISTENCY`: Missing when no party section (`issuer`, `offeror`, `trading_platform_operator`) carries a valid LEI; Review when a valid LEI elsewhere appears in no party section, or the issuer section names more than one; Pass otherwise.
  - No registry (GLEIF) lookup, so a pass never says an LEI exists or belongs to the named entity. CI outputs replace the issue text, which quotes the LEI, with the fixed sentence.
- **Citation.** Part A of each Annex, at Part level, the citation the party rules already use; the repo's study maps the LEI to Annex I, Part A. The point-level basis is not verified (EUR-Lex unreachable) and every rule page says so. See [ADR 0007](../adr/0007-lei-rules.md).
- **Acceptance.** Met: `tests/test_lei.py` (14 tests) covers the check-digit arithmetic, labelled and unlabelled numbers, every status of both rules, German messages, every regime and draft-free CI outputs. Generated rule pages carry tested examples. Fixture LEIs are synthetic, with computed check digits.
- **Effect.** Each regime gains two rules (Annex I 16 → 18, Annex II 18 → 20, Annex III 14 → 16). The synthetic examples carry no LEI, so they now show both rules as Missing. Existing rule IDs are unchanged.

### F4. Wilson intervals in the review summary (H10), next

- **User story.** When study labels exist, readers see precision and recall with 95% intervals, and while labels are pending they see "pending", not a number.
- **Adapt.** Add Wilson 95% bounds to `micar-review-summary` beside the existing precision/recall/F1 and `publication_ready` gate; keep the `model.test.mjs` study-figures test green. No labels entered by the agent or a model.
- **Risk.** None to the non-negotiables; impact is nil until an owner reviews the 150 cells.

### F5. Point-level rules (H8), parked

New IDs under a separate namespace (proposal: `ANNEX_I.A.P<n>`, distinct from `ANNEX_II.G.*` topic IDs and the study's `ANNEX_I_PART_A_02_*` IDs), driven by the numbered fields of Implementing Regulation (EU) 2024/2984. Blocked: every point citation must be verified on EUR-Lex, which was unreachable. See [ADR 0005](../adr/0005-point-level-rule-ids.md).

### F6. Arelle formula assertions (H9), Proposed

An optional CLI-only extra that runs the taxonomy's existence and value assertions with `--internetConnectivity offline` against a taxonomy package the user supplies. Not for the browser (lxml pin conflict). `COMMON.IXBRL_TAGGING` stays never-pass: assertion results become issues under it or under new rule IDs. See [ADR 0004](../adr/0004-arelle-optional-extra.md).

### F7. Browser DOCX import (H5), spec only

Vendor `python_docx-1.2.0-py3-none-any.whl` under `docs/playground/vendor/`, load `lxml` and `typing-extensions` from Pyodide on first DOCX import, then `micropip.install(<same-origin URL>, deps=False)`. Kill if `examples/sample-draft.docx` costs more than 1.5 MB gzip or 5 s extra. Not measured in this run.

### F8. English citations in the browser (H4), owner decision

`displayCitation` in `docs/playground/model.mjs` is reserved for the owner (`TODO(human)`) and was not edited. The engine already emits `citation_en` in the JSON report, so the smallest change is:

```diff
-export function displayCitation(citation) {
-  // TODO(human): render the engine's German-style citation in the English house style.
-  return citation;
-}
+// Display only: exports keep the engine's citation strings unchanged.
+export function displayCitation(finding) {
+  return finding.citation_en ?? finding.citation;
+}
```

with call sites passing the finding instead of `finding.citation`, and a test (to add when the owner accepts) asserting `displayCitation({citation: "Art. 6 Abs. 7 MiCAR", citation_en: "Art. 6(7) MiCAR"}) === "Art. 6(7) MiCAR"`.

## Design upgrades

| ID | Upgrade | Status |
|---|---|---|
| D1 (H7) | Colour tokens for every value in `styles.css`, a dark set via `prefers-color-scheme` and `[data-theme]`, a page-session toggle with no storage | Built (axe: 0 violations in 13 states × 2 widths × 2 themes), then the dark set and toggle were removed at the owner's request on 2026-10-21. The light-only colour tokens stay |
| D2 (H6) | `docs/index.html` landing page sharing tokens with the rule pages | Built. axe clean, no horizontal scroll at 390 px |
| D3 | Accessibility fix: brand link name matches visible text | Built (with D1); kept after D1's dark set was removed |
| D4 | Load progress for the runtime, and a defined state for "only the format gate is open" (no content gaps, explicitly not a compliance opinion) | Spec |
| D5 (H3) | Overlay the `sectionSelection` span on the textarea; CodeMirror 6 only as one vendored same-origin module; structural fixes only (insert a missing key as `""`) labelled with Ruff-style safety | Spec + [ADR 0003](../adr/0003-playground-editor.md) (Proposed) |

## Hypothesis verdicts

| H | Verdict | Evidence | Reason |
|---|---|---|---|
| H1 | modified (built) | https://github.com/github/docs/blob/666463860bec200da6c8db9cb9334e7335d9b753/content/code-security/reference/code-scanning/sarif-files/sarif-support.md; https://github.com/reviewdog/reviewdog/blob/73c79487a087e1696b3e70a0ae5d2a7233343567/README.md | Built with summary and annotations on by default and SARIF opt-in; format gate kept out of annotations; `helpUri` kept for other SARIF consumers although GitHub does not document it |
| H2 | confirmed (built) | https://github.com/eslint/eslint/blob/449724e95bfa013fa32c29375925b4111d3924e4/tools/check-rule-examples.js; https://github.com/astral-sh/ruff/blob/3e3f22dcc47a534d5bb6668817464b02c6e6e133/crates/ruff_dev/src/generate_docs.rs; https://github.com/DataQualityCommittee/dqc_us_rules/blob/64abefd357c34ef45f9f4336a1e3171984d76601/docs/DQC_US_0001/DQC_0001.md | Examples executed in tests, not only rendered |
| H3 | parked | https://github.com/astral-sh/ruff/blob/3e3f22dcc47a534d5bb6668817464b02c6e6e133/playground/ruff/src/Editor/settings.ts | Effort L; needs the editor ADR decision |
| H4 | parked (owner) | https://github.com/sebastianfoerste/micar-whitepaper-linter/blob/ee156930df78b515d5a61397467c24439b61fecd/docs/playground/model.mjs | `displayCitation` is reserved for the owner (`TODO(human)`); diff above |
| H5 | parked | https://github.com/pyodide/pyodide/releases/download/0.28.2/pyodide-0.28.2.tar.bz2 (no python-docx in the distribution) | Size and time kill test not yet run |
| H6 | confirmed (built) | none external (Inferred) | Gives the Pages root a home and states limits |
| H7 | built, then removed | https://github.com/astral-sh/ruff/blob/3e3f22dcc47a534d5bb6668817464b02c6e6e133/playground/ruff/src/Editor/settings.ts (theme setting persisted there; not here) | Removed at the owner's request (2026-10-21) in favour of H11 |
| H8 | parked (owner) | https://github.com/Loideroi/WhitePaperXBRL/blob/f0dc7028e8c13ed8ccd3e322221f03b225f73a10/docs/agent_docs/validation-rules.md | Point citations need EUR-Lex verification |
| H9 | modified, parked | https://github.com/Arelle/Arelle/blob/2ba2e9d96554554a79c2545219f6e5b941bb4d59/arelle/CntlrCmdLine.py; https://github.com/Arelle/Arelle/issues/1898 | CLI-only; killed for the browser (`lxml!=6.0.0`) |
| H10 | confirmed, not built | https://github.com/TheAtticusProject/cuad/blob/67faa0e6023b04fcaae6cc09497ab00e5d63a2a2/evaluate.py; https://github.com/HazyResearch/legalbench/blob/b46bf4ffae90524b2b72aaa30e7745fe9db64481/README.md | Should have been built as a third feature (see the correction above); low impact while 0 of 150 cells are reviewed |
| H11 | modified (built) | https://github.com/Loideroi/WhitePaperXBRL/blob/f0dc7028e8c13ed8ccd3e322221f03b225f73a10/docs/agent_docs/validation-rules.md | Built 2026-10-21 as two fail-closed rules, `COMMON.LEI_CHECK_DIGITS` and `COMMON.LEI_CONSISTENCY`; offline, no registry lookup; see [ADR 0007](../adr/0007-lei-rules.md) |

## Needs owner decision

1. **H4**: accept the `displayCitation` diff above, or keep German citations in the browser.
2. **H9 never-pass**: if Arelle assertions are added, confirm `COMMON.IXBRL_TAGGING` stays never-pass and assertion failures add issues rather than new statuses.
3. **H10 labels**: the 150 study cells need human review before any accuracy figure; nobody else can enter them.
4. **`setup-uv` pin**: the Action now pins `v5.4.2` (newest v5.x, node20). CI uses `v10.3.0` (node24). Moving the Action to v10 needs an ADR and a test run on the starter repo.
5. **Annotations and summary on by default** under `@v1`: additive output with no exit-code change, but visible to every existing consumer on the next `v1` move.
6. **`uvx --no-cache`** in the Action: correctness over a few seconds per run (briefing correction 6).
7. **H8 IDs and citations**: approve the point-level ID scheme and verify each point citation on EUR-Lex.
8. **H7 versus H11**: decided 2026-10-21. The owner swapped dark mode out for H11.
9. **H11 legal basis**: the LEI rules cite Part A of each Annex at Part level (the citation the party rules already use). Verify the point that names the LEI against the Official Journal, and confirm MAJOR as their severity.
10. **Doc drift** proposed in the PR body: `AGENTS.md` (`BaseRule`, database migrations, "compliant"), `docs/FEATURES.md` and `docs/ARCHITECTURE.md` ("regulatory rejection", "compliant"), starter README custody claim (`ANNEX_II.G.CUSTODY` can pass), German citations in `reports/sample-*.txt` and in the text report footer.
