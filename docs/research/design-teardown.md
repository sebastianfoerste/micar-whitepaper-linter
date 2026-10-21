# Design teardown (October 2026)

Access date for every source: 2026-10-20. Tags as in the landscape document: **Observed**, **Claimed**, **Inferred**. Patterns are analysed for adaptation; no competitor asset, microcopy, disclaimer or rule text is reused.

Part A tears down MiCA products (most vendor sites were unreachable; see the landscape's Network-limited banner). Part B tears down open-source linters and CI reporters, read in source.

## Part A: MiCA products


All sources were accessed on 2026-10-20.

**Tags:**
- **Observed:** read in fetched pages or code.
- **Claimed:** from search snippets only.
- **Inferred:** my reasoning.

**Our surfaces:** playground, CLI, Action, rule docs.

### Shortfall

None of the four named targets could be reached: Witness Compliance, Solidcheck, START and Bluprynt. Every vendor host failed DNS with `ENOTFOUND`.

I swapped in reachable tools from the same ring:
1. **ToolOracle MiCAOracle.** Direct-checking, Observed.
2. **mica-crypto-mcp.** Direct-checking, Observed.
3. **WhitePaperXBRL.** This is direct-drafting-filing, not direct-checking. I used it because it is the only reachable tool that implements taxonomy validation, and it was Observed.
4. **START.** I kept it as a thin teardown built only from Claimed snippets. It is the only named target with enough snippet text to say anything.

Shortfall: only 2 same-ring substitutes were reachable, so the set has 1 ring substitution and 1 Claimed-only teardown.

Definely and BriefCatch were both unreachable. I chose BriefCatch because its snippets were richer. That teardown is Claimed only.

Anti-patterns are flagged **only** where the evidence is Observed.

---

### 1. ToolOracle MiCAOracle ("MiCA Ampel" MCP server)

**What it is.** A remote MCP server with 20 tools for token-level and entity-level MiCA readiness. The README lists `readiness_check`, `gap_report`, `assess_token` (said to run eighteen checks), `bridge_approve`, `freshness_check` and `audit_trail`. A third-party OpenAPI mirror also lists `validate_whitepaper`. Sources: [README](https://raw.githubusercontent.com/ToolOracle/micaoracle/main/README.md), [OpenAPI mirror](https://raw.githubusercontent.com/api-evangelist/tooloracle-io/main/openapi/tooloracle-io-mica-ampel-api-openapi.yml); Observed.

**Core job UX.**
- The agent calls a tool and gets back an Ampel status per article (GREEN, YELLOW, RED or GREY) plus a readiness score (Observed).
- I could not find documented inputs, outputs or articles for `validate_whitepaper` (Observed absence).

**Trust mechanics.**
- `audit_trail` exists (Observed).
- `freshness_check` downgrades a stale GREEN to YELLOW (Observed). This is a useful idea: a status decays when its evidence ages.
- A human `bridge_approve` call moves the light to green (Observed).
- The README has no licence, no privacy statement and no disclaimer (Observed).

**Pricing and onboarding.** A free tier gives 10 calls per day. Pro costs €99 a month (Observed).

**Anti-patterns (Observed):**
- **Unpublished scoring logic.** The README mentions eighteen checks and an overall readiness score but does not publish the check logic. This breaks the principle that a reviewer must be able to reproduce why a finding fired.
- **Server-side processing with no retention statement.** All calls go to a remote endpoint (tooloracle.io / api.feedoracle.io), and no data-handling policy is given. This breaks data minimisation and transparency for confidential pre-publication drafts.
- **Approval flips status to GREEN.** A manual approval changes the displayed status to GREEN. This blurs "a human accepted the risk" with "the check passed", which breaks the separation of finding from waiver.

| pattern | seen at (URL, date, tag) | adopt / adapt / reject | our surface | reason |
|---|---|---|---|---|
| Per-article traffic-light status | ToolOracle README, 2026-10-20, Observed | adapt | playground | Group findings by Annex part with a status. Avoid green "pass" wording and use "no gaps found by these rules". |
| Single readiness score | ToolOracle README, 2026-10-20, Observed | reject | playground, CLI | A score implies a calibration we don't have. Report counts per severity instead. |
| Freshness decay of a status | ToolOracle README (`freshness_check`), 2026-10-20, Observed | adapt | Action, rule docs | Stamp each report with the rule-set version and date, and have the Action warn when the rule set is older than the latest release. |
| Human approval turns a status green | ToolOracle README (`bridge_approve`), 2026-10-20, Observed | adapt | CLI, Action | Support an explicit, logged waiver per rule ID that stays visible as "waived", never as "pass". |
| Remote-only processing | ToolOracle README (`mcp-remote` to tooloracle.io), 2026-10-20, Observed | reject | playground | Our in-browser, no-upload model is a differentiator. Keep it, and say it on the page. |
| `audit_trail` tool | ToolOracle README, 2026-10-20, Observed | adapt | Action | Emit a machine-readable report (JSON/SARIF) as a CI artifact, giving a per-commit trail. |

---

### 2. mica-crypto-mcp (MEOK AI Labs, PyPI)

**What it is.** An MCP server on PyPI under the MIT licence (v1.0.9, uploaded 2026-06-27). It offers tools for classification, CASP authorisation, `whitepaper_requirements`, market abuse, AML and regulation search. Sources: [PyPI JSON](https://pypi.org/pypi/mica-crypto-mcp/json) and the sdist code; Observed.

**Core job UX.** `whitepaper_requirements(query)` returns JSON with `"status": "stub"`, empty `regulation_refs` and a note that the checking logic is planned for a later version. It suggests sending the result to a remote service that returns a signed certificate (server.py lines 176–204; Observed).

**Trust mechanics.**
- The README shows a badge claiming AI Act compliance and describes the package as ready for production use (Observed).
- Paid tiers include signed certificates of the result (Observed).

**Anti-patterns (Observed):**
- **Compliance language without logic.** The README calls the product compliant and production-ready while the white-paper tool is a stub with no references. This breaks the rule that a claim must match the published logic.
- **Signed certificates for an empty assessment.** The tool offers to "sign" an assessment that has no content. This breaks the rule that a signature must not stand in for substance.

| pattern | seen at (URL, date, tag) | adopt / adapt / reject | our surface | reason |
|---|---|---|---|---|
| Compliance badges in the README | PyPI project description, 2026-10-20, Observed | reject | rule docs | No "compliant" badges. State scope and limits instead. |
| Signed attestation of results | mica-crypto-mcp server.py `next_step`, 2026-10-20, Observed | adapt | Action | Use a report hash plus rule-set version for reproducibility, framed as "this report was produced by these rules", never as a compliance certificate. |
| `pip install` with zero config | PyPI README, 2026-10-20, Observed | adopt | CLI | Already aligned: keep one-command install and a no-key, offline run. |
| Stub tools shipped in a release | server.py L176–204, 2026-10-20, Observed | reject | CLI, rule docs | Each rule must have a test fixture before release. Never ship a placeholder rule as active. |

---

### 3. WhitePaperXBRL (Loideroi): ring substitution, direct-drafting-filing

**What it is.** A Next.js app that converts PDF, DOCX, ODT or RTF white papers into MiCA iXBRL and validates them. It covers OTHR, ART and EMT. The README says it is proprietary, although the repository is public. Sources: [README](https://raw.githubusercontent.com/Loideroi/WhitePaperXBRL/main/README.md), [validation-rules.md](https://raw.githubusercontent.com/Loideroi/WhitePaperXBRL/main/docs/agent_docs/validation-rules.md), [xbrl-taxonomy.md](https://raw.githubusercontent.com/Loideroi/WhitePaperXBRL/main/docs/agent_docs/xbrl-taxonomy.md), [security-model.md](https://raw.githubusercontent.com/Loideroi/WhitePaperXBRL/main/docs/agent_docs/security-model.md); Observed.

**Core job UX.** The flow is Upload → Extract → Map fields → Review/Edit → Validate → Generate.
- Field mapping runs in three passes: table format, then patterns, then labels.
- Validation has three modes: full, quick (LEI plus existence checks, for real-time feedback) and per-field (messages inside the editor).
- Each finding has a rule ID (EXS-…, VAL-…, LEI-…, PRH-…) and a severity of ERROR or WARNING. `formatErrorMessage()` maps IDs to plain text (Observed).

**Rules.**
- 488 assertions in total: 257 existence, 224 value, 6 LEI and 1 duplicate check.
- They are hand-coded in TypeScript. The tool does not evaluate the formula linkbase.
- Filing rules (CTX, FCT, IXB, PRH and others) are taken from the reporting manual.
- The LEI check uses mod-97 plus an optional GLEIF lookup. Network failures are treated as valid (Observed).
- The docs' own counts don't add up: 223 vs 224 value assertions, and 487 vs 488 in total (Observed).

**Trust mechanics.**
- Files are processed in memory on the server and are "never written to disk". Sessions are cleared after 1 hour.
- Logs exclude document content (Observed).
- No LLM is mentioned (Observed).

**Anti-patterns (Observed):**
- **Calling the output compliant.** The repo description says "ESMA MiCA compliant iXBRL format". A generated file can satisfy the format and still fail on legal substance, so this breaks the rule against calling a pass "compliant". This is a mild case, because the claim is about format.
- **Server-side upload of drafts.** Retention is documented and short, but the upload still happens. This breaks the principle of keeping confidential drafts local. The documented retention is a mitigation.
- **Network failure counted as LEI-valid.** This fails open, and breaks the fail-closed principle (Observed in validation-rules.md).

| pattern | seen at (URL, date, tag) | adopt / adapt / reject | our surface | reason |
|---|---|---|---|---|
| Stable rule IDs with ERROR/WARNING severity | validation-rules.md, 2026-10-20, Observed | adopt | CLI, rule docs, Action | Already similar. Keep the IDs stable and map them to SARIF ruleId and level. |
| Quick mode vs full mode | validation-rules.md, 2026-10-20, Observed | adapt | playground | Run a quick structural pass on each edit and the full run on demand. Cheap in Pyodide. |
| Per-field validation inside the editor | validation-rules.md (`validateField`), 2026-10-20, Observed | adapt | playground | Anchor each finding to the section heading or line it concerns. |
| Existence/value assertion counts per token type | xbrl-taxonomy.md, 2026-10-20, Observed | adapt | rule docs | Publish a coverage table: our rules versus Annex items and versus taxonomy existence assertions per table. |
| LEI mod-97 check | validation-rules.md, 2026-10-20, Observed | adopt | CLI, playground | A deterministic, offline check is cheap and high-signal. |
| GLEIF lookup that fails open on network error | validation-rules.md, 2026-10-20, Observed | reject | CLI | Fail closed or report "not verified". Never treat it as valid. |
| Server-side upload, in-memory | security-model.md, 2026-10-20, Observed | reject | playground | We stay client-side. |
| Compliance wording in the repo description | GitHub repo description, 2026-10-20, Observed | reject | rule docs, playground | Use "no gaps found by N rules (version X)" wording. |
| Hand-coded assertions instead of the formula linkbase | validation-rules.md, 2026-10-20, Observed | adapt | rule docs | If we add taxonomy completeness, say whether rules are derived from or checked against the ESMA formula files, and document version drift. |

---

### 4. START (PwC Legal × Auditchain Pacioli.ai): Claimed only

**Evidence base.** Search snippets only. legal.pwc.de failed DNS. Snippets come from the [press release](https://legal.pwc.de/en/news/press-releases/pwc-germany-pwc-legal-and-auditchain-labs-announce-cooperation-for-regulatory-disclosure-automation), the [June 2026 flyer](https://legal.pwc.de/content/services/pwc-legal-flyer-micar-start-platform-june-2026.pdf) and the [BNC repost](https://bravenewcoin.com/press-release/pwc-and-auditchain-labs-announce-cooperation-for-regulatory-disclosure-automation).

**Claimed features.**
- Template-driven workflows for EMT, ART and OTHR.
- Automated validation in real time against the whole MiCAR ITS rule set.
- External technical validation by a Pacioli.ai Validating Node.
- A dedicated, isolated instance per client.
- iXBRL export for filing.
- Bundled with PwC Legal advisory.

**Not visible.** How results are shown (score or status), citations per finding, uncertainty handling, retention, pricing.

**Anti-patterns.** None flagged, because the evidence is not Observed. Inferred note: a whole-rulebook claim with no public rule list can't be checked from outside. Our published rule docs are the contrast.

| pattern | seen at (URL, date, tag) | adopt / adapt / reject | our surface | reason |
|---|---|---|---|---|
| Independent second validation (a second engine) | START press-release snippet, 2026-10-20, Claimed | adapt | Action, rule docs | Document how to run Arelle with the ESMA taxonomy after our linter. Two independent checks instead of one claimed "full" check. |
| Template-driven drafting per token type | START flyer snippet, 2026-10-20, Claimed | adapt | rule docs | Link the micar-whitepaper-template per Annex (I/II/III) from the rule docs. |
| Isolated instance per client | START press-release snippet, 2026-10-20, Claimed | adapt | playground | Our equivalent is stronger: nothing leaves the browser. Say so explicitly. |
| Bundled legal advisory | START press-release snippet, 2026-10-20, Claimed | reject | rule docs | Out of scope for an OSS linter. Keep the "not legal advice" boundary. |

---

### 5. BriefCatch (adjacent): Claimed only

**Evidence base.** Search snippets of [support.briefcatch.com suggestions](https://support.briefcatch.com/home/web-app/suggestions) and related guides. briefcatch.com failed DNS.

**Claimed UX.**
- Each finding is a sidebar card for one passage, carrying a proposed change, an explanation, alternatives and real-world examples.
- Cards are sorted into tabs: All, Style, Clarity, Proofing, Citations.
- "Ignore in all docs" turns off a rule for good, and a separate view of ignored rules lets the user re-enable it.
- An AI toggle affects only citation suggestions and chat. Rule-based checks are unaffected.

| pattern | seen at (URL, date, tag) | adopt / adapt / reject | our surface | reason |
|---|---|---|---|---|
| One card per finding: passage, reason, suggestion | support.briefcatch.com, 2026-10-20, Claimed | adapt | playground | Card = rule ID + pinpoint citation + why it fired + what to add. No auto-rewrite of disclosure text. |
| Tabs by finding category | support.briefcatch.com, 2026-10-20, Claimed | adapt | playground | Tabs or filters by Annex part and severity. |
| Ignore a rule everywhere, with a view of ignored rules | support.briefcatch.com, 2026-10-20, Claimed | adapt | CLI, Action | A config file of waivers per rule ID, always listed in the report summary. |
| AI kept separate from rule-based checks | support.briefcatch.com, 2026-10-20, Claimed | adopt | rule docs | State plainly that the checking path is deterministic, with no LLM. |
| Suggested replacement text | support.briefcatch.com, 2026-10-20, Claimed | reject | playground | For regulated disclosures we suggest what is missing, not wording. Rewriting disclosure text is outside a linter's safe scope. |


## Part B: Open-source pattern donors


Accessed 2026-10-20. Tags: Observed / Claimed / Inferred (full evidence in Part B of the [competitive landscape](2026-10-competitive-landscape.md)). Our principles assumed from the brief: deterministic, offline-capable, fail closed on missing sections, confidential drafts must not leak (no server-side storage, no document text in public CI surfaces).

Surfaces: **playground** (Pyodide), **CLI** (`micar-lint`), **Action** (composite GitHub Action), **rule docs**.

---

### 1. Ruff — playground + rule docs (MIT)

**Playground architecture (Observed, ruff@3e3f22d `playground/`).** Single-page React/Vite app with Monaco; Ruff runs as WASM in the browser, so linting never leaves the tab. State (source, settings, theme) is written to `localStorage` and restored on load. "Share" POSTs source+settings to a Cloudflare Worker that stores them in Workers KV under a random UUID with no TTL in the `put` call; the link is `play.ruff.rs/<uuid>`. Older links compressed the whole source into the URL hash with lz-string and are still decoded. "Copy as Markdown" pastes code + settings + link.

**Anti-patterns for us (Inferred):** (a) permanent server-side copies of shared input — for an unpublished white paper that's a confidentiality breach and a retention obligation; (b) URL-hash payloads leak via history, chat unfurls, and referrers; (c) silent `localStorage` autosave keeps draft text on shared machines. Our playground should keep text in memory, offer an explicit "Download report" instead of share links, and if anything is shareable, share only a sample ID + rule config.

**Rule docs (Observed).** Docs are Rust doc comments on the violation struct with fixed headings: What it does / Why is this bad? / Known problems / Example + "Use instead:" / Options / Fix safety / References. A generator adds title `name (CODE)`, lifecycle ("Added in vX" / Preview / Deprecated / Removed, linking release tags), "Related issues" search link, "View source" file#line link, upstream "Derived from", and fix availability. A CI script fails if "What it does" or "Why is this bad?" is missing and formats the example code; it does not check that the example triggers the rule (Inferred from the script).

**Fix safety (Observed).** Three-level `Applicability`: Safe (always applied, meaning preserved), Unsafe (opt-in), DisplayOnly (shown, never applied). Each rule documents why its fix is unsafe.

**Output (Observed).** 12 formats; `github` lines: `::error title=ruff (CODE),file=…,line=…,col=…,endLine=…,endColumn=…::path:row:col: CODE message%0A  help: …`; SARIF carries `helpUri`, no `partialFingerprints`.

| pattern | seen at (URL, date, tag) | adopt / adapt / reject | our surface | reason |
|---|---|---|---|---|
| Linter compiled to run in-browser (WASM) | github.com/astral-sh/ruff/tree/3e3f22d/playground, 2026-10-20, Observed | adopt (already Pyodide) | playground | keeps drafts client-side |
| Server KV share links, no TTL | …/playground/api/src/index.ts, 2026-10-20, Observed | reject | playground | stores confidential draft text server-side |
| lz-string source in URL hash | …/playground/ruff/src/Editor/settings.ts, 2026-10-20, Observed | reject | playground | leaks via history/unfurls |
| localStorage autosave of source | same file, 2026-10-20, Observed | reject (or opt-in, per-tab only) | playground | persists drafts on shared devices |
| Fixed doc headings enforced in CI | …/scripts/check_docs_formatted.py, 2026-10-20, Observed | adapt: What it checks / Legal basis (MiCAR art./Annex) / Failing example / Passing example / Fix guidance / References | rule docs | consistent, reviewable pages |
| Lifecycle line "Added in vX" / preview / deprecated | …/crates/ruff_dev/src/generate_docs.rs, 2026-10-20, Observed | adopt | rule docs, CLI | regulatory rule changes need dating |
| "View source" + "Related issues" links | same, Observed | adopt | rule docs | auditability of rule logic |
| Safe / Unsafe / DisplayOnly fix applicability | …/crates/ruff_diagnostics/src/fix.rs, Observed | adapt: only DisplayOnly suggestions for legal text | CLI, playground | auto-editing disclosures is unsafe |
| `--output-format` incl. github, sarif, rdjson, junit | …/crates/ruff_linter/src/settings/types.rs, Observed | adopt subset (text, json, github, sarif, rdjson) | CLI, Action | one engine, many surfaces |
| github line echoes rendered message + help | …/render/github.rs snapshot, Observed | adapt: rule ID + generic message, no excerpt | Action | annotations on public PRs must not quote draft text |

---

### 2. ESLint — rule docs (MIT)

**Doc format (Observed, eslint@449724e).** Markdown with front-matter (`title`, `rule_type`, `related_rules`, `further_reading`), intro, `## Rule Details`, `::: incorrect` / `::: correct` example containers, `## Options` with one subsection per option, `## When Not To Use It`.

**Examples are executable tests (Observed).** `tools/check-rule-examples.js` (run in `lint:docs:rule-examples` and lint-staged) lints each example with the real `Linter`: an incorrect block must produce at least one error from that rule; any unexpected error (i.e. any error in a correct block, or other rules) fails; missing language tags, invalid ecmaVersion and duplicated config comments also fail.

**Metadata (Observed).** `meta.type`, `meta.docs.{description, recommended, url}`, `fixable` (mandatory to emit fixes), `hasSuggestions` (mandatory to emit suggestions), `schema`, `defaultOptions`, `deprecated`/`replacedBy`. Suggestions are standalone, never auto-applied; autofix runs multipass up to 10 times.

**Formatters (Observed).** Core keeps stylish, json, json-with-metadata (adds rule meta), html; SARIF is an external package.

| pattern | seen at (URL, date, tag) | adopt / adapt / reject | our surface | reason |
|---|---|---|---|---|
| Correct/incorrect example blocks verified by CI | github.com/eslint/eslint/blob/449724e/tools/check-rule-examples.js, 2026-10-20, Observed | adopt (pytest parametrised over rule-doc fixtures) | rule docs, CLI tests | docs can't drift from behaviour |
| `meta.docs.url` on every rule | …/lib/rules/no-unused-vars.js, Observed | adopt (a doc URL derived from `Rule.rule_id`) | CLI, Action, SARIF helpUri | one click from finding to rationale |
| Mandatory `fixable` / `hasSuggestions` declarations | …/docs/src/extend/custom-rules.md, Observed | adapt: `remediation: none|guidance|template` | rule docs, CLI | explicit about what we never auto-edit |
| Suggestions never auto-applied | same, Observed | adopt | playground | legal text must be author-edited |
| json-with-metadata formatter (results + rule meta) | …/lib/cli-engine/formatters/formatters-meta.json, Observed | adopt | CLI | self-describing JSON report for auditors |
| Front-matter `related_rules`, `further_reading` | docs/src/rules/*.md, Observed | adopt (`related_rules`, `legal_basis`) | rule docs | cross-links Annex items |
| "When Not To Use It" | docs/src/rules/no-unused-vars.md, Observed | adapt: "Not applicable when…" (e.g. ART vs EMT vs other) | rule docs | scope by token type |

---

### 3. reviewdog (MIT)

**What it is (Observed, reviewdog@73c7948 README).** A Go CLI that takes diagnostics in errorformat, rdjson/rdjsonl, diff, checkstyle or SARIF and posts them to GitHub/GitLab/Gerrit/Bitbucket/Gitea surfaces, filtered to the diff.

**Reporters & permissions (Observed).** `github-pr-review` → review comments (+ suggestion blocks), needs `pull-requests: write`; `github-pr-check` / `github-check` → Checks API with annotations, level→status (error = failure, else neutral), needs `checks: write`; `github-[pr-]annotations` → workflow-command lines on stdout (token only for diff). reviewdog's own workflow requests `checks: write`, `contents: read`, `pull-requests: write`.

**Fork PRs (Observed).** Fork tokens can't write Checks/Reviews, so reviewdog falls back to workflow-command annotations, subject to per-run caps; GitHub docs confirm write → read downgrade on fork `pull_request` runs (github/docs workflow-syntax.md, Observed). Cap numbers (10 errors + 10 warnings per step, 50 per job) only appear in a 2020 maintainer comment — Claimed.

**Filter modes (Observed).** added (default), diff_context, file, nofilter; review reporter can't comment outside the diff and falls back to check annotations.

**SARIF caveat (Observed).** `artifactLocation.uri` must be a repo-relative file; findings on unchanged lines need `-filter-mode=file`.

**Anti-pattern (Observed in README example):** the annotations reporter appends a "Raw Output" JSON copy of the diagnostic into the annotation body — duplicates content into a public surface.

| pattern | seen at (URL, date, tag) | adopt / adapt / reject | our surface | reason |
|---|---|---|---|---|
| rdjson as neutral diagnostics format | github.com/reviewdog/reviewdog/blob/73c7948/proto/rdf/reviewdog.proto, 2026-10-20, Observed | adopt (`--format rdjson`) | CLI | lets users pick reviewdog reporters without us shipping them |
| Graceful degradation to annotations on forks | README §Graceful Degradation, Observed | adopt | Action | fork PRs get read-only token |
| Filter mode `file` for whole-document checks | README §Filter mode, Observed | adapt: default `nofilter`/file for missing-section findings | Action | fail-closed findings sit on unchanged lines |
| Level → check conclusion mapping | README §github-pr-check, Observed | adopt (`--fail-level`) | CLI, Action | explicit gating |
| `-fail-level=none` default (exit 0) | README §Exit codes, Observed | reject as default | CLI | fail closed |
| "Raw Output" echoed into annotations | README §github-annotations, Observed | reject | Action | would republish draft excerpts publicly |
| Depend on hosted reviewdog app server | README Option 2, Observed | reject | Action | third-party data flow |

---

### 4. Vale + vale-action (MIT) and Spectral (Apache-2.0)

**Vale (Observed, vale@9f822e9).** Offline prose linter; styles are folders of YAML rules each `extends:` a check type (existence, substitution, occurrence, consistency, capitalization, metric, sequence, conditional, script…). `--output` = CLI | line | JSON | template file. Alert JSON includes Check, Severity, Message, Description, Link, Span, Line, Action/Suggestions and **Match (the literal matched text)**. Network only for `vale sync` packages and an optional NLP endpoint.

**vale-action (Observed, @518a913).** Runs `vale --output=JSON`, converts to rdjsonl itself (to include fix suggestions), pipes to reviewdog; defaults: `reporter: github-pr-annotations`, `filter_mode: added`, `fail_on_error: false`, pinned reviewdog 0.21.0.

**Spectral (Observed, spectral@95ab37e).** Rules are declarative `given` (JSONPath) + `then` (function) in YAML/JS rulesets with `documentationUrl`; each finding links to `documentationUrl#rule-name`. Documents are parsed with position-preserving parsers so `getRangeForJsonPath(path, closest)` maps a JSON path to a line/column range, falling back to the nearest existing ancestor for missing keys. Formatters include sarif (helpUri from documentationUrl) and github-actions (relative paths, `%0A` newlines, appended doc URL). Rule reference entries: id, requirement sentence, "Why?", Recommended, Default severity, Bad Example, Good Example; tests live separately.

| pattern | seen at (URL, date, tag) | adopt / adapt / reject | our surface | reason |
|---|---|---|---|---|
| Declarative YAML rule types (existence, consistency, conditional) | github.com/errata-ai/vale/tree/9f822e9/internal/check, 2026-10-20, Observed | adapt (keep the Python `Rule` dataclass, add declarative "required field present" config) | CLI, rule docs | many Annex items are presence checks |
| `--output` template file | …/cmd/vale/flag.go, Observed | reject for now | CLI | fixed formats easier to keep deterministic |
| JSON alert carries `Match` text | …/internal/core/alert.go, Observed | reject for public outputs; allow in local `--format json --include-excerpts` | CLI, Action | confidentiality |
| Action converts own JSON → rdjsonl → reviewdog | github.com/errata-ai/vale-action/blob/518a913/src/main.ts, Observed | adapt (emit rdjson directly) | Action | avoids second converter |
| Action default `fail_on_error: false` | …/action.yml, Observed | reject | Action | fail closed |
| JSON path → range with closest-ancestor fallback | github.com/stoplightio/spectral/blob/95ab37e/packages/core/src/document.ts, Observed | adopt | CLI, Action (SARIF) | anchors missing-section findings to parent |
| `documentationUrl#rule-id` per finding | …/docs/guides/4-custom-rulesets.md, Observed | adopt | CLI, Action, playground | consistent deep links |
| github-actions formatter appends doc URL | …/packages/formatters/src/github-actions.ts, Observed | adopt | Action | annotation is actionable without excerpt |
| Rule reference: Why? / Recommended / Default severity / Bad / Good | …/docs/reference/openapi-rules.md, Observed | adopt + add "Legal basis" | rule docs | compact page shape |
| Doc examples not executed | Spectral docs vs `__tests__`, Inferred | reject (use ESLint approach) | rule docs | drift risk |

---

### 5. Cross-cutting anti-patterns to avoid (summary)

1. **Share links / browser-stored state** — Ruff KV shares with no TTL, URL-hash payloads, localStorage autosave (Observed). Reject for playground; drafts are confidential before publication.
2. **Echoing document text into public annotations** — reviewdog "Raw Output", Vale `Match`, LanguageTool `context.text`, Ruff help lines (Observed). Our Action messages should carry rule ID, Annex reference, field path and doc URL only; excerpts stay in local CLI output behind a flag.
3. **Non-failing defaults** — reviewdog `-fail-level=none`, vale-action `fail_on_error: false` (Observed). Conflicts with fail-closed.
4. **SARIF-only CI** — unavailable on private repos without GitHub Code Security and on fork PRs (Observed/Inferred). Keep workflow-command annotations + step summary (≤1 MiB/step, Observed) as baseline.
