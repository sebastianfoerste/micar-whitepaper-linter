# Competitive landscape: MiCAR white paper checking (October 2026)

> **Network-limited run.** Research ran on 2026-10-20 from a sandbox whose network allowed GitHub, raw.githubusercontent.com and PyPI only. Every vendor site, eur-lex.europa.eu, esma.europa.eu, review sites and most documentation hosts failed (DNS error or proxy refusal; full list in Part A section 6 and Part B section 0). Facts about commercial products therefore come from search-result snippets and are tagged **Claimed**. Open-source tools were read in source and are **Observed**. No gap was filled from memory.
>
> **Upload log.** No file was uploaded to any checker in this run. No sign-ups, trials, forms or vendor contact.
>
> **Scope note.** Statements about named products are limited to what the cited source shows, on the access date. This document is not a review of any vendor and not legal advice.

Part A covers products in the direct and adjacent rings. Part B covers open-source pattern donors (linters, CI reporters, rule catalogues).

## Part A: MiCA white paper products

Research date and access date for every source: **2026-10-20**. This is read-only research. Nothing was signed up for, uploaded or submitted.

Evidence tags:
- **Observed**: I fetched and read the page, document or code myself.
- **Claimed**: the fact comes only from vendor marketing or a search-result snippet; I could not open the page itself.
- **Inferred**: my own reasoning.

Citation format: `(URL; tag)`. The access date is 2026-10-20 throughout.

> **Main limitation.** The sandbox could not resolve DNS for any vendor site, for eur-lex.europa.eu, for esma.europa.eu, or for the review sites. All of them failed with `getaddrinfo ENOTFOUND`. GitHub, raw.githubusercontent.com and pypi.org worked. As a result:
> - Every fact about a commercial vendor below is **Claimed**, taken from search-result snippets.
> - Only open-source tools are **Observed**.
> - I filled no gaps from memory.

---

### A.1. Preflight log

| Target | Tool | Result |
|---|---|---|
| https://www.witness-compliance.eu/en/mica-whitepaper-validator | WebFetch | error: `getaddrinfo ENOTFOUND www.witness-compliance.eu` |
| https://eur-lex.europa.eu | WebFetch | error: `getaddrinfo ENOTFOUND eur-lex.europa.eu` |
| https://www.esma.europa.eu/document/mica-taxonomy-2025 | WebFetch | error: `getaddrinfo ENOTFOUND www.esma.europa.eu` |
| https://github.com/Arelle/Arelle | WebFetch | ok (Apache-2.0; lists ESEF Reporting Manual validation; no MiCA mention) |
| WebSearch "MiCA white paper validator" | WebSearch (standard) | ok (9 results; no validator product among them) |
| raw.githubusercontent.com, pypi.org (JSON API + simple index), git clone over https from github.com | curl / git | ok |
| GitHub MCP search (repositories, code, issues) | MCP | ok. Reading files from repos outside the session was denied, so I used raw.githubusercontent.com instead |
| `$HTTPS_PROXY/__agentproxy/status` | Bash | blocked by the permission classifier; not retried |

### A.2. Search log

All searches ran on 2026-10-20. The "Useful" column counts results relevant to MiCA white paper tooling.

| # | Query | Lang | Engine | Useful |
|---|---|---|---|---|
| 1 | MiCA white paper validator | EN | WebSearch | 2 (ESMA reporting manual link, Mondaq) |
| 2 | ESMA MiCA taxonomy 2025 assertions filing rules white paper iXBRL | EN | WebSearch | 4 |
| 3 | MiCA whitepaper checker AI score | EN | WebSearch | 2 (Whitepaper Grey agent, Eunice) |
| 4 | Bluprynt MiCA checker | EN | WebSearch | 0 |
| 5 | MiCA whitepaper checker tool | EN | WebSearch | 4 (ToolOracle, TokenEx, Eunice, Whitepaper Grey) |
| 6 | Kryptowerte-Whitepaper Prüfung Software MiCAR | DE | WebSearch | 1 (Finoa × Crypto Risk Metrics) |
| 7 | MiCAR Whitepaper Prüfung Tool iXBRL | DE | WebSearch | 3 (PwC Legal alert, CSSF, OMG SBRM) |
| 8 | livre blanc MiCA validation iXBRL outil | FR | WebSearch | 2 |
| 9 | Auditchain START Pacioli MiCA white paper PwC Legal | EN | WebSearch | 4 |
| 10 | MiCA Crypto Alliance white paper tracker | EN | WebSearch | 1 (CASP tracker only) |
| 11 | Witness Compliance MiCA whitepaper validator | EN | WebSearch | 0 |
| 12 | Solidcheck MiCA XBRL checker free tool | EN | WebSearch | 1 (Capterra listing) |
| 13 | Crypto Risk Metrics MiCA XBRL checker | EN | WebSearch | 2 |
| 14 | Workiva MiCA white paper iXBRL | EN | WebSearch | 0 (no Workiva hit) |
| 15 | MiCA white paper iXBRL tagging software | EN | WebSearch | 3 (CoreFiling, Luca Suite/SBRM, Alliance webinar) |
| 16 | MiCA checker review reddit | EN | WebSearch | 0 |
| 17 | MiCA xbrl validator open source arelle plugin | EN | WebSearch | 1 |
| 18 | Bluprynt MiCA white paper AI compliance score | EN | WebSearch | 3 |
| 19 | livre blanc crypto-actifs MiCA logiciel conformité vérification | FR | WebSearch | 1 (GlobalSuite) |
| 20 | MiCA Whitepaper XBRL Software Anbieter Validierung | DE | WebSearch | 2 (ESMA Excel tool disclaimer) |
| 21 | PwC Legal START platform MiCAR white paper flyer validation report | EN | WebSearch | 3 |
| 22 | bluprynt.com mica-checker free white paper check | EN | WebSearch | 0 |
| 23 | micacryptoalliance.com white-paper-tracker ESMA register white papers | EN | WebSearch | 1 |
| 24 | witness-compliance.eu MiCA | EN | WebSearch | 0 |
| 25 | CoreFiling Seahorse MiCA white paper | EN | WebSearch | 0 |
| 26 | easyESEF easyMiCA white paper iXBRL | EN | WebSearch | 0 |
| 27 | Eunice MiCA whitepaper generator AI | EN | WebSearch | 1 (TokenEx) |
| 28 | micarwhitepapers.eu registry | EN | WebSearch | 0 |
| 29 | BriefCatch Word add-in suggestions explanation rules citations | EN | WebSearch | 4 |
| 30 | Definely Proof Word add-in defined terms cross-reference errors check | EN | WebSearch | 4 |
| 31 | DataTracks MiCA white paper ESMA iXBRL service | EN | WebSearch | 3 |
| G1 | repo search `mica xbrl` | EN | GitHub | 1 (WhitePaperXBRL) |
| G2 | repo search `mica whitepaper` | EN | GitHub | 2 (WhitePaperXBRL, plus our own linter and template) |
| G3 | repo search `micar white paper validator` | EN | GitHub | 0 |
| G4 | code search `"esma.europa.eu/taxonomy" mica` | EN | GitHub | 5 real filed white-paper XHTMLs |
| G5 | code search `mica_entry_table` | EN | GitHub | 5 |
| G6 | repo search `mica ixbrl`, `mica compliance checker crypto`, `mica mcp server crypto` | EN | GitHub | 1 |
| G7 | repo search `tooloracle mica`, code search `validate_whitepaper mica` | EN | GitHub | 2 (MiCAOracle, its OpenAPI) |
| G8 | issue search `MiCA` in Arelle/Arelle; `MiCA white paper taxonomy validation error` | EN | GitHub | 1 (#1898) |
| G9 | awesome-list repo search, then raw README grep for MiCA | EN | GitHub | 0 third-party MiCA checkers |
| P1 | PyPI simple index (918,422 names), regex `mica\|micar\|whitepaper` | EN | PyPI | 1 (mica-crypto-mcp) |

Totals: 31 web searches (25 EN, 3 DE, 3 FR) and 10 GitHub/PyPI searches.

### A.3. Per-product notes

### Ring: direct-checking

#### PwC Legal × Auditchain Labs: START on Pacioli.ai (seed)
- **Status:** the seed press-release URL failed DNS. A search snippet dates the announcement 28 Sep 2026 ([BNC repost](https://bravenewcoin.com/press-release/pwc-and-auditchain-labs-announce-cooperation-for-regulatory-disclosure-automation); Claimed).
- **Job:** prepare, validate and file MiCAR white papers. START stands for Submission, Traceability, Automation, Reporting and Transparency (search snippet of [legal.pwc.de press release](https://legal.pwc.de/en/news/press-releases/pwc-germany-pwc-legal-and-auditchain-labs-announce-cooperation-for-regulatory-disclosure-automation); Claimed).
- **Features:** template-driven workflows for EMT, ART and OTHR. Snippets describe real-time automated validation against "the full MiCAR ITS rulebook". An independent external check runs on the Pacioli.ai Validating Node. Output is exported as iXBRL. Each client gets a dedicated, isolated instance (search snippets of the PwC press release and the [June 2026 flyer](https://legal.pwc.de/content/services/pwc-legal-flyer-micar-start-platform-june-2026.pdf); Claimed).
- **Buyer:** crypto-asset issuers and capital-market participants. PwC Legal provides the legal advice (Claimed, same sources).
- **Agentic:** snippets describe the offering as agent-driven automation of regulatory disclosures (Claimed). An earlier Auditchain Luca Suite is described as built on OMG's SBRM standard ([OMG](https://www.omg.org/insights/how-sbrm-enables-digital-asset-white-paper-compliance-under-the-eu-mica-regulations/); Claimed).
- **Not found:** pricing, the published rule logic, how results are presented, and retention terms.
- **Reviews:** none found. The Reddit-style query (#16) returned nothing relevant.

#### Bluprynt MiCA Checker (seed)
- **Status:** the product page failed DNS. A search for "Bluprynt MiCA checker" returned no relevant result (#4, #22). Whether the checker still exists is unknown.
- **Company:** a search snippet describes Bluprynt as a compliance OS that uses AI and blockchain for issuer disclosures ([Caplight](https://www.caplight.com/company/bluprynt); Claimed). A snippet reports a $4.25M funding round ([Crowdfund Insider](https://www.crowdfundinsider.com/2026/03/264429-digital-asset-os-bluprynt-announces-4-25m-round/); Claimed).
- **Features:** a snippet mentions "assessments based on researched metrics" from document analysis (#18 snippet, startup-seeker; Claimed). With the Avalanche Foundation, Bluprynt records MiCA metadata on-chain, including compliance status, timestamps and completeness ([Crowdfund Insider](https://www.crowdfundinsider.com/?p=235411); Claimed). It has a partnership with Legion for MiCA-compliant token sales ([Decrypt](https://decrypt.co/289825/legion-bluprynt-mica-compliant-ico-eu); Claimed).
- **Not confirmed:** I could not confirm any AI-generated compliance score. One 64/100 score in the results is StartupHub's agent-readiness rating of Bluprynt's website, not a white paper score (Claimed).
- **Reviews:** none found on G2, Capterra or Reddit. All of those hosts were unreachable, and searches surfaced nothing.

#### MiCA Crypto Alliance "White Paper Tracker" (seed)
- **Status:** the seed URL failed DNS. Searches (#10, #23) found only the Alliance's **CASP Tracker**, launched on 5 August, with no year given in the snippet. It is a searchable view of the ESMA interim register with name, LEI, country, regulator, date and service filters, plus side-by-side comparison ([KuCoin flash news](https://www.kucoin.com/news/flash/mica-crypto-alliance-launches-searchable-tracker-for-esma-crypto-authorisations); Claimed).
- **Disclaimer:** coverage says the ESMA register remains the official source (Claimed).
- **Not found:** no evidence of a white-paper tracker. A snippet mentions an Alliance webinar on XHTML/iXBRL white papers ([luma](https://luma.com/b8f7gs0b); Claimed). Whether the white-paper tracker still exists is unknown.

#### Crypto Risk Metrics: MiCA White Paper XBRL Checker (seed)
- **Status:** the page failed DNS. A snippet confirms the company lists a "MiCA White Paper XBRL Checker" among its services ([crypto-risk-metrics.com/products](https://crypto-risk-metrics.com/products/); Claimed).
- **Related services:** XBRL formatting of plain text, including for lawyers (Claimed, same). A partnership with Finoa on MiCAR white papers was reported (#6 snippet, [it-finanzmagazin](https://www.it-finanzmagazin.de/?p=228824); Claimed).
- **Not found:** what the checker validates, its pricing, and its deployment.

#### Solidcheck: MiCA XBRL Checker (seed)
- **Status:** the page failed DNS. Capterra snippets describe Solidcheck as an on-chain monitoring and compliance platform with APIs and AI copilots, aligned with MiCA ([Capterra](https://www.capterra.in/software/1042370/solidcheck); Claimed). No snippet mentions a free MiCA XBRL checker, so the checker's existence is unknown.
- **Reviews:** the Capterra listing exists per the snippet. Its reviews could not be read because the host was unreachable.

#### Witness Compliance: MiCA Whitepaper Validator (seed)
- **Status:** the host failed DNS, and two searches (#11, #24) returned no page from the domain. Whether it still exists is unknown, and nothing about it could be verified.

#### NEW: ToolOracle MiCAOracle / "MiCA Ampel" (MCP server)
- **Sources:** [github.com/ToolOracle/micaoracle](https://github.com/ToolOracle/micaoracle) and its [README](https://raw.githubusercontent.com/ToolOracle/micaoracle/main/README.md) (Observed).
- **Tools:** 20 MCP tools for token-level and entity-level MiCA assessment, including `readiness_check`, `gap_report`, `assess_token` (said to run eighteen checks), `bridge_approve` and `audit_trail` (Observed).
- **Results:** traffic-light statuses GREEN, YELLOW, RED and GREY. `readiness_check` returns an overall readiness score plus a light per article. The README says a human approval through `bridge_approve` moves the light to green. `freshness_check` downgrades a stale GREEN (Observed).
- **Deployment:** remote-only. Clients connect via `mcp-remote` to tooloracle.io (Observed). A third-party OpenAPI mirror lists `validate_whitepaper` among the tools, behind `api.feedoracle.io` ([api-evangelist/tooloracle-io](https://raw.githubusercontent.com/api-evangelist/tooloracle-io/main/openapi/tooloracle-io-mica-ampel-api-openapi.yml); Observed). The 18 checks and the inputs to `validate_whitepaper` are not published (Observed).
- **Pricing:** Free (10 calls/day), Pro €99/month, Enterprise custom (Observed).
- **Missing from the README:** licence, privacy statement and legal disclaimer (Observed).
- **Reviews:** none. The repo has 0 stars and 0 issues (GitHub search; Observed).

#### NEW: mica-crypto-mcp (MEOK AI Labs) on PyPI
- **Sources:** [pypi.org/project/mica-crypto-mcp](https://pypi.org/pypi/mica-crypto-mcp/json) (Observed). I downloaded the sdist v1.0.9 (uploaded 2026-06-27) and read its code.
- **Licence:** MIT.
- **Code:** the `whitepaper_requirements` tool returns `"status": "stub"`, an empty `regulation_refs`, and a note that the checking logic is planned for a later version. It suggests sending the result to a remote service that returns a signed certificate (`server.py` lines 176–204; Observed).
- **README:** shows a badge claiming AI Act compliance and describes the package as ready for production use. It lists paid tiers at £29, £79 and £1,499 per month (Observed).
- **LLM use:** none in the checking path, because there is no checking logic at all (Observed).

#### NEW: Whitepaper Grey (agent listing)
- A search snippet describes a three-layer pipeline (structural analysis, claim extraction, mathematical evaluation) with an "EU MiCA compliance check", priced from $0.25 USDC per verification ([hol.org listing](https://hol.org/registry/agent/uaid:aid:4W6VtCyeeLyRRc2iGVWqugNF1zhwoEo4zUuMXDd4shSNTZB2yMpZ7CkXyrAd8k14Ww); Claimed). The host was not reachable.

### Ring: direct-drafting-filing

#### NEW: WhitePaperXBRL (Loideroi): PDF/DOCX to iXBRL converter with a validator
- **Sources:** [repo](https://github.com/Loideroi/WhitePaperXBRL), [README](https://raw.githubusercontent.com/Loideroi/WhitePaperXBRL/main/README.md), [validation-rules.md](https://raw.githubusercontent.com/Loideroi/WhitePaperXBRL/main/docs/agent_docs/validation-rules.md), [xbrl-taxonomy.md](https://raw.githubusercontent.com/Loideroi/WhitePaperXBRL/main/docs/agent_docs/xbrl-taxonomy.md) and [security-model.md](https://raw.githubusercontent.com/Loideroi/WhitePaperXBRL/main/docs/agent_docs/security-model.md). All Observed.
- **Repo:** TypeScript and Next.js. Last updated 2026-03-18, 0 stars. The README says the licence is proprietary.
- **Workflow:** upload → extract → map fields (table format, then pattern matching, then label matching) → review and edit → validate → generate iXBRL. It covers OTHR, ART and EMT (Table 2, 3 and 4).
- **Validation:** 488 assertions in total: 257 existence, 224 value, 6 LEI and 1 duplicate check. All are hand-coded in TypeScript; there is no formula-linkbase execution. Rule families cover the reporting-manual filing rules (CTX, FCT, IXB, PRH and others) with ERROR and WARNING severities. There are full, quick and per-field validation modes. The LEI check includes mod-97 and an optional GLEIF lookup. Its own docs have count inconsistencies (223 vs 224 value assertions, 487 vs 488 in total).
- **Privacy:** files are processed server-side, in memory, and "never written to disk". Sessions are cleared after 1 hour. No LLM is mentioned.

#### Eunice (seed)
- The page failed DNS. Snippets describe an AI-powered library of more than 1,000 MiCA white papers, with legal opinions from CMS where needed ([Crowdfund Insider](https://www.crowdfundinsider.com/?p=237021); Claimed). It is not a checker.

#### DataTracks: "Rainbow" MiCA for ESMA iXBRL (seed)
- The page failed DNS. A snippet says the cloud tool generates ESMA-compliant XHTML/iXBRL "mapped to the latest MiCA taxonomy" ([datatracks.com](https://datatracks.com/?p=72654); Claimed).

#### CoreFiling MiCA (Seahorse) (seed)
- The page failed DNS. A snippet describes the workflow: create the white paper in Word, InDesign or PDF, convert it, tag it, then validate against the MiCA filing rules before submission ([corefiling.com/mica](https://www.corefiling.com/mica/); Claimed). The search for "Seahorse" returned nothing.

#### easyMiCA / easyESEF (seed)
- The page failed DNS and the search (#26) found nothing. Its existence is unknown.

#### MiCAR Whitepapers registry (seed)
- The page failed DNS and the search (#28) found nothing. Its existence is unknown.

#### Workiva (re-check)
- Search #14 returned no Workiva MiCA page. The host was not reachable. Status: no evidence of a MiCA product.

#### NEW: TokenEx (AI MiCA white paper assistant)
- A snippet says it classifies the token, drafts the white paper, and validates it against requirements, in French and English ([eliteai.tools](https://eliteai.tools/tool/tokenex); Claimed).

#### NEW / reference: ESMA Excel show-case tool
- A snippet describes an Excel-based solution for generating iXBRL white papers. It carries an ESMA disclaimer that the tool is not validated and that output errors stay with the issuer (#20 snippet, [ESMA node 220930](https://www.esma.europa.eu/node/220930); Claimed).

### Ring: adjacent

- **xBRL-Forge** ([repo](https://github.com/antonheitz/xBRL-Forge) and [LICENCE.md](https://raw.githubusercontent.com/antonheitz/xBRL-Forge/main/LICENCE.md); Observed): a generic JSON or DOCX to XBRL/iXBRL generator. It has no MiCA mention and no validation. Its licence is custom and non-commercial (source-available; commercial use needs a separate licence). 8 stars.
- **Arelle** ([repo](https://github.com/Arelle/Arelle); Observed): Apache-2.0 and the de-facto open-source XBRL validator. A sparse clone of master (commit 2ba2e9d, 2026-10-19) shows `arelle/plugin/validate` with CIPC, DBA, EBA, EDINET, ESEF, FERC, IRD, NL, PRH, ROS and UK, and no MiCA plugin. A grep for "mica" in that directory returned nothing (Observed). [Issue #1898 "ESMA MiCA Validation Rules"](https://github.com/Arelle/Arelle/issues/1898), opened 2025-09-09 by a maintainer, asks to add reporting-manual validation. It is open, in Triage, with no PR (Observed).
- **AshishSinghvi18/XBRLValidator** ([AGENT_PLAN.md](https://raw.githubusercontent.com/AshishSinghvi18/XBRLValidator/main/AGENT_PLAN.md); Observed): an agent build plan for a regulator-grade validator (EFM, ESEF and others). The first 100k characters do not mention MiCA. It is a plan, not working software.
- **BriefCatch** (Claimed; [support.briefcatch.com](https://support.briefcatch.com/home/web-app/suggestions)): a Word add-in with suggestion cards, each showing the finding, the proposed change and an explanation, sorted into tabs. "Ignore in all docs" turns a rule off, and a view of ignored rules exists. The AI toggle affects only citations and chat; the rule-based features are unaffected (snippet).
- **Definely Proof / Draft** (Claimed; [definely.com/proof](https://definely.com/proof), [help.definely.com](https://help.definely.com/en/articles/669589-fix-cross-reference-issues)): checks defined terms (undefined, unused, duplicate) and cross-references, with a Manual review-each-fix mode and an Auto bulk-fix mode.
- **Markup AI**: the host failed DNS and I ran no search. Unknown.
- **GlobalSuite** (Claimed, FR snippet): sells versioning, approval and traceability for white papers ([globalsuitesolutions.com](https://www.globalsuitesolutions.com/fr/?p=99865)).
- **OriginStamp** (Claimed): timestamping for white paper integrity ([preview.originstamp.com](https://preview.originstamp.com/en/blog/reader/mica-crypto-white-paper-integrity-timestamping)).

### Awesome-list check (Observed; raw READMEs downloaded and grepped)
- **sebastianfoerste/awesome-eu-fintech-regulation:** its MiCA tools are all by the same owner (micar-register-observatory, micar-whitepaper-linter, eu-reg-mcp), and the author discloses this on the page. It lists no third-party MiCA checkers.
- **Other lists checked:** Vaquill-AI/awesome-legaltech lists only micar-whitepaper-linter. tanko-r/awesome-legal-tech lists only micar-register-observatory and kakunin-core (agent identity, not white papers). chen-friedman/awesome-legaltech, inhouseapac/awesome-in-house-legal, maastrichtlawtech/awesome-legal-nlp and CSHaitao/Awesome-LegalAI-Resources have no MiCA white paper tools.
- **Inferred:** the curated lists contain no third-party open-source MiCA white paper checker.

### A.4. Review mining

| Product | Channels tried | Result |
|---|---|---|
| Bluprynt | G2 (DNS fail), Reddit (DNS fail), web search | no reviews found |
| Solidcheck | Capterra (snippet only; host unreachable) | listing exists (Claimed); no reviews readable |
| START (PwC/Auditchain) | web search, Reddit, HN Algolia (DNS fail) | no reviews found |
| MiCAOracle | GitHub issues and stars | 0 stars, 0 issues (Observed); no reviews |
| WhitePaperXBRL | GitHub issues | 0 issues (Observed) |
| Arelle MiCA | GitHub issues | #1898 open, no comments (Observed) |
| Generic "MiCA checker review reddit" | web search | 0 relevant |

**Q7, user voice on AI scores:** no user reviews or comments on AI scoring were found for any MiCA checker. I can't say what users think.

### A.5. Research questions

### Q1. Assertions and filing rules in the ESMA MiCA taxonomy 2025: who implements them, and is `2025-03-31` correct?

**What ships, from secondary evidence only, because esma.europa.eu was unreachable:**
- **Assertions:** the taxonomy carries Formula 1.0 **existence assertions** (72 for Table 2/OTHR, 103 for Table 3/ART, 82 for Table 4/EMT) and **value assertions** (around 224: 139, 62 and 22 by table). They sit in a formula linkbase (`mica-for-table2.xml` for Table 2) with a companion workbook `mica_taxonomy_formulas_202507.xlsx`. The taxonomy is closed (no extensions). It has entry points `mica_entry_table_2.xsd`, `_3`, `_4`, plus `mica_all.xsd` for software vendors. Source: WhitePaperXBRL docs ([xbrl-taxonomy.md](https://raw.githubusercontent.com/Loideroi/WhitePaperXBRL/main/docs/agent_docs/xbrl-taxonomy.md); Observed as a third-party description, not verified against ESMA).
- **Filing rules:** the **MiCA Reporting Manual v1.0** ([ESMA PDF link from search](https://www.esma.europa.eu/sites/default/files/2025-08/mica_taxonomy_reporting_manual_v1.0.pdf); Claimed) adds technical rules. WhitePaperXBRL implements these as CTX, FCT, IXB, PRH and other families: no `<base>` or `<script>`, `decimals` rather than `precision`, a single entity identifier, xml:lang, hidden-section rules (Observed in its docs).
- **LEI:** snippets say the LEI is checked automatically ([Mondaq](https://www.mondaq.com/fin-tech/1724068/mica-white-papers-re-engineered); Claimed).
- **Timeline:** an ESMA statement of 28 Nov 2025 references taxonomy availability from 5 Aug 2025 and a show case from 8 Oct 2025 ([ESMA75-1303207761-6284](https://www.esma.europa.eu/sites/default/files/2025-11/ESMA75-1303207761-6284_Statement_to_support_the_smooth_implementation_of_MiCA_standards_and_format.pdf); Claimed).

**Who implements them:**
- **Arelle:** no MiCA validation plugin on master as of 2026-10-19. The issue requesting reporting-manual rules (#1898) is still open (Observed). Inferred: Arelle could still run the formula linkbase generically when loading the taxonomy, since it supports Formula 1.0, but it ships no MiCA filing-rule profile.
- **WhitePaperXBRL:** hand-coded TypeScript versions of the assertions and filing rules (Observed).
- **START:** claims validation against the "full MiCAR ITS rulebook" (Claimed).
- **DataTracks and CoreFiling:** claim validation against the MiCA filing rules (Claimed).
- **ESMA's own Excel show-case tool:** reportedly "not validated" per its disclaimer (Claimed).

**Namespace check:**
- **The repo's value matches the published namespace.** The repo uses `https://www.esma.europa.eu/taxonomy/2025-03-31/mica/` (`src/micar_linter/ixbrl.py:21`). This exact namespace is declared in four published white-paper XHTML files in public GitHub repositories (not named here: this research does not quote real white papers). It also matches the "root URI/namespace" in the WhitePaperXBRL docs (Observed via GitHub code search).
- **The entry-point URL puts the path segments in a different order.** One of those published files references `https://www.esma.europa.eu/taxonomy/mica/2025-03-31/mica_entry_table_2.xsd`. The namespace is `…/taxonomy/2025-03-31/mica/`, while the schema location is `…/taxonomy/mica/2025-03-31/…` (Observed). The date matches; only the order differs.
- **Inferred:** the repo correctly checks the namespace, not the schemaRef. If a schemaRef or entry-point check is ever added, it must use the `mica/2025-03-31` order and must not reuse the namespace constant. One of those files also declares `…/2025-03-31/mica/table2` as a separate prefix. Facts tagged under that prefix would not count as taxonomy facts in the current check. This is worth a test fixture (Inferred).
- **Caveat:** I could not check ESMA directly for a newer (2026) taxonomy version.

### Q7. How START, Bluprynt and the Alliance tracker present results

- **START:** all evidence is Claimed. It is described as real-time automated validation against the "full MiCAR ITS rulebook" plus a separate technical validation by an external Pacioli.ai Validating Node, with iXBRL export. I found no screenshot or description of a score versus a status, of per-finding citations, or of uncertainty handling. Calling a check "full rulebook" without published rule logic cannot be checked from outside. I am not tagging it as an anti-pattern because I could not see the product.
- **Bluprynt:** Claimed only. Snippets mention metric-based assessments and on-chain metadata that records a compliance status and completeness. I found no evidence of a numeric AI score, citations or uncertainty display.
- **MiCA Crypto Alliance:** I found no white-paper tracker. The CASP tracker presents register facts and defers to ESMA as the official source (Claimed).
- **Observed comparator (MiCAOracle):** traffic-light statuses plus an overall readiness score. A human `bridge_approve` turns a status GREEN, and a stale GREEN decays to YELLOW. No per-finding legal citation format is documented.
- **User voice on AI scores:** none found.

### A.6. Not reachable (all on 2026-10-20)

| Host / URL | Error |
|---|---|
| www.witness-compliance.eu | getaddrinfo ENOTFOUND |
| eur-lex.europa.eu | getaddrinfo ENOTFOUND |
| www.esma.europa.eu | getaddrinfo ENOTFOUND |
| www.bluprynt.com | getaddrinfo ENOTFOUND |
| www.solidcheck.io | getaddrinfo ENOTFOUND |
| crypto-risk-metrics.com | getaddrinfo ENOTFOUND |
| www.micacryptoalliance.com | getaddrinfo ENOTFOUND |
| legal.pwc.de | getaddrinfo ENOTFOUND |
| eunice.ai | getaddrinfo ENOTFOUND |
| datatracks.com | getaddrinfo ENOTFOUND |
| www.corefiling.com | getaddrinfo ENOTFOUND |
| easyesef.eu | getaddrinfo ENOTFOUND |
| www.micarwhitepapers.eu | getaddrinfo ENOTFOUND |
| www.mfsa.mt (circular PDF) | getaddrinfo ENOTFOUND |
| briefcatch.com | getaddrinfo ENOTFOUND |
| www.definely.com | getaddrinfo ENOTFOUND |
| markup.ai | getaddrinfo ENOTFOUND |
| groups.google.com (Arelle users thread) | getaddrinfo ENOTFOUND |
| policylayer.com | getaddrinfo ENOTFOUND |
| www.xbrl.org | getaddrinfo ENOTFOUND |
| eliteai.tools | getaddrinfo ENOTFOUND |
| www.mondaq.com | getaddrinfo ENOTFOUND |
| hn.algolia.com, www.reddit.com, www.g2.com, www.capterra.com, www.crowdfundinsider.com, decrypt.co, www.elliptic.co, luma.com, www.omg.org, www.cssf.lu, www.workiva.com | curl HTTP 000 (no connection) |
| pypi.org/search (HTML) | page rendered "required part of this site couldn't load"; used JSON/simple API instead |
| api.github.com for repos outside the session (gh) | HTTP 403, session bound to configured repo; used raw.githubusercontent.com and a sparse git clone instead |
| ESEF conformance suite page | not attempted separately (esma.europa.eu DNS failure) |


## Part B: Open-source pattern donors

Accessed: **2026-10-20** for every source below. Tags: **Observed** = read source/docs file in a clone or raw fetch; **Claimed** = snippet/marketing/third-party statement only; **Inferred** = my reasoning from observed facts.
All quotations are ≤10 words; everything else is paraphrase. Repositories were read from shallow clones in a local scratch directory that is not committed; nothing in them was executed.

### B.0. Preflight and "Not reachable" log

Method: `curl -s -o /dev/null -w '%{http_code}' -m 20 <url>` and WebFetch, 2026-10-20.

| Host / URL | Result | Workaround used |
|---|---|---|
| https://docs.astral.sh/ruff/ | 000 (proxy refused) | Read Rust doc comments + `crates/ruff_dev/src/generate_docs.rs` in astral-sh/ruff |
| https://eslint.org/docs/latest/ | 000 | `docs/src/rules/*.md`, `tools/check-rule-examples.js` in eslint/eslint |
| https://docs.github.com/en (curl + WebFetch: ENOTFOUND) | unreachable | github/docs repo (sparse clone, commit 666463860bec) |
| https://groups.google.com/g/arelle-users/c/M_QehLoqJAs (curl 000, WebFetch ENOTFOUND) | unreachable | **Not filled.** Thread content unknown. |
| https://www.esma.europa.eu/ (ESEF Reporting Manual, ESEF conformance suite) | 000 | Only indirect: Arelle test config references the ESMA download URL (see Arelle) |
| https://vale.sh/docs | 000 | errata-ai/vale source |
| https://textlint.org | 000 | textlint/textlint `docs/` |
| https://www.conftest.dev | 000 | open-policy-agent/conftest source |
| https://docs.stoplight.io | 000 | stoplightio/spectral `docs/` |
| https://play.ruff.rs | 000 | playground source |
| https://cdn.jsdelivr.net/pyodide/v0.28.2/full/pyodide-lock.json | proxy connect_rejected | Lockfile from GitHub release `pyodide/pyodide-recipes` `0.28-20250801` (the URL pinned in pyodide 0.28.2 `Makefile.envs`) |
| GitHub REST `search/code` and `repos/reviewdog/...` via `gh api` | 403 (session bound to configured repos) | WebFetch of github.com issue page worked |
| https://github.com/TheAtticusProject/cuad/main/README.md (raw) | 404 (file is `readme.md`) | shallow clone |
| https://raw.githubusercontent.com/HazyResearch/legalbench/main/LICENSE | 404 | licence recorded as per-task (README) |

Reachable: github.com (git + WebFetch of HTML), raw.githubusercontent.com, pypi.org JSON API, registry.npmjs.org.

---

### B.1. Arelle (Apache-2.0) — ring: adjacent

Source: https://github.com/Arelle/Arelle at `2ba2e9d96554554a79c2545219f6e5b941bb4d59` (2026-10-19). Licence Apache-2.0 (`pyproject.toml` `license = "Apache-2.0"`, LICENSE.md, © Workiva) — **Observed**.

### Q2a: Offline formula validation with local taxonomy packages?
- CLI has `--internetConnectivity` with choices `online`/`offline` and `--packages` (repeatable; a directory loads all .zip packages) — **Observed** https://github.com/Arelle/Arelle/blob/2ba2e9d96554554a79c2545219f6e5b941bb4d59/arelle/CntlrCmdLine.py (L279-290, L1214-1220).
- `offline` sets `webCache.workOffline = True` early, before packages load, with a code comment that packages may otherwise trigger web requests — **Observed** same file L1699-1704.
- In offline mode WebCache returns the cached path (falls back to a built-in cache) and never downloads — **Observed** `arelle/WebCache.py` L607-614.
- `--formula validate|run|none` plus `--formulaRunIDs` regex selection of assertions — **Observed** CntlrCmdLine.py L881-897.
- Arelle's own integration test validates an ESEF report with `internetConnectivity="offline"`, `packages=[...]`, `plugins="validate/ESEF"`, `disclosureSystemName="esef-2024"` — **Observed** `tests/integration_tests/scripts/tests/python_api_validate_esef.py` L47-59.
- Conformance configs exist for XBRL Formula 1.0 and assertion severity 2.0 — **Observed** `tests/integration_tests/validation/conformance_suite_configurations/xbrl_formula_1_0*.py`.
- **Answer (Inferred):** yes — formula assertions shipped inside a taxonomy package can be validated/run offline, provided every referenced schema/linkbase resolves through package remappings or the cache; anything outside packages fails to resolve rather than being fetched. Not executed (rule: never run code from clones).

### Q2b: Wheel size and deps
- `arelle-release` 2.46.1, uploaded 2026-10-08; wheel `arelle_release-2.46.1-py3-none-any.whl` **6,146,430 bytes** (~5.9 MiB compressed); sdist 5,717,849 bytes; `requires_python >=3.10`; `license_expression Apache-2.0` — **Observed** https://pypi.org/pypi/arelle-release/json. Installed (unpacked) size not in the JSON — **unknown**.
- Base deps: bottle, certifi, filelock, isodate, jaconv, jsonschema, lxml (`!=6.0.0,<7,>=4`), numpy, openpyxl, pillow, pyparsing, python-dateutil, regex, truststore, typing-extensions. ESEF extra adds tinycss2; EFM extra pulls matplotlib + pythonmonkey — **Observed** same JSON.

### Q2c: Pure-python / Pyodide 0.28.2?
- Wheel tag is `py3-none-any`, so Arelle itself is pure Python — **Observed** (PyPI filename).
- Pyodide 0.28.2's `Makefile.envs` pins prebuilt packages to pyodide-recipes release `0.28-20250801` — **Observed** https://github.com/pyodide/pyodide/blob/0.28.2/Makefile.envs L16-18.
- That lockfile (info: python 3.13.2, emscripten 4.0.9) ships lxml **6.0.0**, numpy 2.2.5, pillow 11.3.0, regex 2024.11.6, jsonschema 4.23.0, pyparsing, python-dateutil, certifi, typing-extensions, rpds-py; it does **not** ship jaconv, truststore, isodate, openpyxl, bottle, filelock, et-xmlfile, tinycss2 — **Observed** https://github.com/pyodide/pyodide-recipes/releases/download/0.28-20250801/pyodide-lock.json.
- The missing ones all have `py3-none-any` wheels on PyPI (jaconv 0.5.0, truststore 0.10.5, isodate 0.7.2, openpyxl 3.1.5, bottle 0.13.4, filelock 4.2.4, et-xmlfile 2.0.0) — **Observed** pypi.org JSON.
- **Blocker:** Arelle excludes `lxml==6.0.0`, the only lxml in the Pyodide 0.28 lock → micropip resolution of `arelle-release` should fail unless deps are bypassed (`deps=False`) — **Inferred** (not executed).
- Further risks — **Inferred**: truststore expects a platform TLS store; WebCache/filelock/socket code assumes a real filesystem and network; numpy+pillow+lxml add several MB of WASM downloads. Recommend: keep Arelle out of the Pyodide playground; offer it as an optional CLI/Action extra.

### Q2d: MiCA-specific code in Arelle?
- `grep -rnI -i -w mica` over the whole clone: **0 hits**; "micar" only matches the substring in `atomicArg` (false positive); no "crypto-asset" hits. Validation plugins present: CIPC, DBA, EBA, EDINET, ESEF, FERC, IRD, NL, PRH, ROS, UK — **Observed** `arelle/plugin/validate/`. So **no MiCA plugin** in Arelle main as of 2026-10-19.
- ESEF conformance suite 2024 is downloaded from an esma.europa.eu URL (mirrored to Arelle's public S3 in CI) — **Observed** `conformance_suite_configurations/esef_ixbrl_2024.py`.
- Arelle users thread M_QehLoqJAs: **unreachable; content unknown**.

---

### B.2. reviewdog (MIT) — ring: pattern-donor

Source: https://github.com/reviewdog/reviewdog/blob/73c79487a087e1696b3e70a0ae5d2a7233343567/README.md (2026-10-19). LICENSE MIT © haya14busa — **Observed**.

- **Inputs:** `errorformat` (Vim-style patterns + predefined list), `rdjson`/`rdjsonl` (Reviewdog Diagnostic Format), `diff`, `checkstyle`, `sarif` (2.1.0) — **Observed** README L163-320.
- RDFormat fields: message, location{path, range{start/end line,column}}, severity, source{name,url}, code{value,url}, suggestions[], original_output, related_locations[] — **Observed** `proto/rdf/reviewdog.proto`.
- SARIF caveat: `artifactLocation.uri` must be a workspace file; URLs there become `../../` paths; findings on unchanged lines need `-filter-mode=file` — **Observed** README L305-319.
- **Reporters:** local, github-check, github-pr-check, github-pr-review, github-annotations, github-pr-annotations, gitlab-mr-discussion/commit, gerrit, bitbucket-code-report, gitea-pr-review — **Observed** README L404-583.
  - github-pr-check: Checks API; level→status mapping info/warning=neutral, error=failure — **Observed**.
  - github-pr-review: PR review comments; only reporter (with gitlab-mr-discussion) supporting code suggestions — **Observed** L332-347.
  - github-annotations/github-pr-annotations: print `::error file=..,line=..,col=..::` to stdout; token used only for the diff — **Observed** L515-529. Their example message embeds a "Raw Output" JSON copy of the finding — **Observed** (anti-pattern for us: duplicates document text into public annotations).
- **Permissions:** reviewdog's own workflow requests `checks: write`, `contents: read`, `pull-requests: write` — **Observed** `.github/workflows/reviewdog.yml` L11-13.
- **Fork PRs:** `GITHUB_TOKEN` from forks has no Check/Review write access, so reviewdog degrades to workflow-command annotations, with a per-run annotation cap; full results remain in the log — **Observed** README L750-766.
- **Filter modes:** `added` (default), `diff_context`, `file`, `nofilter`; github-pr-review only partially supports file/nofilter (falls back to check annotations outside the diff) — **Observed** README L926-975.
- Exit codes: `-fail-level=none` default returns 0; `any|info|warning|error` fail on threshold — **Observed** L916-922.
- Pinned example: `reviewdog/action-setup@d8edfce3...` (v1.4.0) in README — **Observed**; latest tag via ls-remote: v1.5.0 → `d8a7baabd7f3e8544ee4dbde3ee41d0011c3a93f` — **Observed**.

### B.3. GitHub code scanning SARIF + workflow commands (docs, CC-BY-4.0 content / MIT code in github/docs)

Source: github/docs at `666463860bec200da6c8db9cb9334e7335d9b753` (2026-10-19).

SARIF support — https://github.com/github/docs/blob/666463860bec200da6c8db9cb9334e7335d9b753/content/code-security/reference/code-scanning/sarif-files/sarif-support.md — **Observed**:
- Only SARIF `2.1.0`. Required: `$schema`, `version`, `runs[]`; `run.tool.driver` (`name`, `rules[]`); `results[]`; rule `id`, `shortDescription.text`, `fullDescription.text` (each ≤1024 chars), `help.text`; result `message.text`, `locations[]`, `partialFingerprints`; `physicalLocation.artifactLocation.uri`, `region.startLine/startColumn/endLine/endColumn`.
- Recommended optional: `help.markdown` (shown instead of help.text), `properties.precision` (very-high..low), `properties.problem.severity`, `properties.tags[]`, `defaultConfiguration.level` (note/warning/error), rule `name` ≤255 chars.
- `helpUri`: **not mentioned** anywhere under `content/code-security` (grep returned 0) — **Observed absence**; Ruff/Spectral emit it anyway.
- `partialFingerprints`: only `primaryLocationLineHash` is used; `upload-sarif` computes it from source files if absent; API uploads without it may duplicate alerts — **Observed**. Only the first `locations[]` entry is used; max 10 locations listed in the result table text.
- Only first sentence of `message.text` shown when space is tight — **Observed**.
- Limits (`data/reusables/code-scanning/sarif-limits.md`) — **Observed**: runs/file 20; results/run 25,000 (only top 5,000 shown by severity); rules/run 25,000; tool extensions 100; locations/result 1,000 (100 kept); tags/rule 20 (10 kept); alert limit 1,000,000; gzip SARIF ≤10 MB per upload.
- Availability: upload supported for org-owned repos with GitHub Code Security enabled, and public repos on github.com (`upload-sarif-ghas.md`) — **Observed**. ⇒ private personal repos / orgs without Code Security can't use SARIF code scanning — **Inferred**.
- Permissions: `security-events: write` always; `actions: read` + `contents: read` for private repos (`upload-sarif-file.md` L84-88) — **Observed**.
- Fork PRs: write permissions are downgraded to read for `pull_request` from forks unless admin enables write tokens — **Observed** `workflow-syntax.md` L354, L366. ⇒ SARIF upload from fork PRs fails by default — **Inferred**.

Workflow commands — `content/actions/reference/workflows-and-actions/workflow-commands.md` — **Observed**:
- Shapes: `::notice|warning|error file={name},line={line},endLine={endLine},title={title}::{message}` (also `col`, `endColumn`).
- `$GITHUB_STEP_SUMMARY`: GFM; per-step; **max 1 MiB per step** (overflow → upload fails + error annotation, step status unaffected); **max 20 step summaries displayed per job**; summaries auto-mask secrets; deleting requires deleting the whole run.
- Annotation caps (10 errors + 10 warnings per step, 50 per job): **not in github/docs** (`workflow-commands.md`, `limits.md` grep → nothing) — **Observed absence**. Only source: reviewdog issue #411 comment by haya14busa (2020-01-05) citing a GitHub Community post: 10 warning + 10 error per step, 50 per job — **Claimed** https://github.com/reviewdog/reviewdog/issues/411 (via WebFetch). Treat as unverified/possibly stale.
- `limits.md`: check runs per suite 50,000 — **Observed**.

### B.4. Action pins (exact SHAs)

Commands (run 2026-10-20):
```
git ls-remote https://github.com/github/codeql-action 'refs/tags/v3*' 'refs/tags/v4*'
git ls-remote https://github.com/astral-sh/setup-uv 'refs/tags/v*'
git ls-remote https://github.com/reviewdog/action-setup 'refs/tags/v1*'
```
| Action | Tag | Tag object | Commit (`^{}` dereferenced) | Notes |
|---|---|---|---|---|
| github/codeql-action | v4 (floating) | f051dc808ef3645eb0d08647ec751634ec2304ac | **6f2ac81f5cd81fe351a197ba0b00d91d03cd2aee** | = v4.39.0 (tag obj 48870fdd6b42…); upload-sarif runs `node24` |
| github/codeql-action | v4.39.0 | 48870fdd6b42ee6474ec4207209ff87609271a5e | **6f2ac81f5cd81fe351a197ba0b00d91d03cd2aee** | newest v4 |
| github/codeql-action | v3 (floating) | d0bae162f31f17dd92c46ccdc4dfee5710f8dc67 | **ce5e7eeac396d720fe2d802714996c8ce561e311** | = v3.39.0; CHANGELOG says v3 deprecated December 2026 |
| astral-sh/setup-uv | v5 (floating) | e58605a9b6da7c637471fab8847a5e5a6b8df081 | **d4b2f3b6ecc6e67c4457f6d3e41ec42d3d0fcb86** | = v5.4.2 (lightweight); `node20` runtime |
| astral-sh/setup-uv | v6 / v7 floating | d0d8abe6… / 94527f2e… | d0cc045d04ccac9d8b7881df0226f9e82c39688e / 37802adc94f370d6bfd71619e3f0bf239e1f3b78 | |
| astral-sh/setup-uv | v10.3.0 (newest; lightweight, no floating `v8`/`v9`/`v10`) | — | **1c37ad07a6a961277cf70c0d37d6f313000f5884** | `node24`; README pins v10.1.0 `bec219d2…` |
| reviewdog/action-setup | v1.5.0 | 38a8d76742a75eeb6c6ffc616bde64179fd09ebf | **d8a7baabd7f3e8544ee4dbde3ee41d0011c3a93f** | = v1 floating |
The raw `git ls-remote` output was kept locally and is not committed; the SHAs above are copied from it. All **Observed**. v3 deprecation: **Observed** https://raw.githubusercontent.com/github/codeql-action/6f2ac81f5cd81fe351a197ba0b00d91d03cd2aee/CHANGELOG.md L232. setup-uv v5 runs on node20 — **Observed** action.yml at d4b2f3b6; Node 20 runner deprecation not checked here (unknown).

### B.5. Ruff (MIT) — ring: pattern-donor

Source: astral-sh/ruff at `3e3f22dcc47a534d5bb6668817464b02c6e6e133` (2026-10-19); LICENSE MIT © Charles Marsh — **Observed**.

Playground — **Observed** `playground/README.md`, `playground/ruff/src/Editor/settings.ts`, `playground/api/src/index.ts`:
- React + Vite + Monaco SPA; Ruff compiled to WASM; editor state kept in `localStorage` (`source`, plus `theme`).
- Share button POSTs settings + full Python source to a Cloudflare Worker backed by Workers KV; key is `crypto.randomUUID()`; URL becomes `play.ruff.rs/<uuid>`. No expiry/TTL in the `put` call (grep for expiration: none). CORS limited to Ruff/ty origins.
- Legacy share links: lz-string-compressed source in the URL hash (`#…`), still decoded on load.
- "Copy as Markdown" puts source + settings + link onto clipboard.
- **Anti-pattern for us (Inferred):** server-stored, non-expiring share of user content and full document in URL hash/localStorage → would leak unpublished white-paper text. Our playground should keep text in memory only, never auto-persist, and share only rule config/sample IDs.

Rule docs — **Observed** `crates/ruff_linter/src/rules/flake8_bugbear/rules/mutable_argument_default.rs`, `crates/ruff_dev/src/generate_docs.rs`, `scripts/check_docs_formatted.py`:
- Doc comment sections: `## What it does`, `## Why is this bad?`, `## Known problems`, `## Example`, "Use instead:", `## Options`, `## Fix safety`, `## References`.
- Generator prepends: title `name (CODE)`; status line "Added in"/"Preview (since)"/"Deprecated (since)"/"Removed (since)" linking the release tag; "Related issues" search link; "View source" link to file#line; "Derived from" upstream linter; fix availability (Always/Sometimes); preview/deprecation warnings.
- CI script fails if a rule doc lacks "What it does" or "Why is this bad?"; it formats code blocks in examples (style), it does **not** assert that the example triggers the rule — **Observed** (L240-250) / **Inferred** for absence of trigger test.
- Fix safety: `Applicability` enum `DisplayOnly` (show only, may be invalid), `Unsafe` (opt-in, may change behaviour), `Safe` (always applied, meaning preserved) — **Observed** `crates/ruff_diagnostics/src/fix.rs` L14-31.
- `--output-format`: concise, full (default), json, json-lines, junit, grouped, github, gitlab, pylint, rdjson, azure, sarif — **Observed** `crates/ruff_linter/src/settings/types.rs` L555-569.
- `github` line shape: `::error title=<program> (<CODE>),file=<path>,line=..,col=..,endLine=..,endColumn=..::<path>:<row>:<col>: <CODE> <message>%0A  help: …` — **Observed** github.rs + snapshot. Message echoes identifiers from source (fine for code; risk for us).
- SARIF emits `helpUri` from rule URL and `fixes`; no `partialFingerprints` (grep: none) — **Observed** `crates/ruff_linter/src/message/sarif.rs`.

### B.6. ESLint (MIT) — ring: pattern-donor

Source: eslint/eslint at `449724e95bfa013fa32c29375925b4111d3924e4` (2026-10-19); LICENSE MIT (OpenJS Foundation) — **Observed**.
- Rule doc = Markdown with front-matter (`title`, `rule_type`, `related_rules`, `further_reading`; counts across docs: 294/128/77), then intro, `## Rule Details`, examples in `::: incorrect` / `::: correct` containers, `## Options` (one `###` per option), `## When Not To Use It` — **Observed** `docs/src/rules/no-unused-vars.md`.
- **Examples are tested:** `tools/check-rule-examples.js` (npm `lint:docs:rule-examples`, also lint-staged) parses every rule doc, runs `Linter.verify` on each block; an `incorrect` block must yield ≥1 error from that rule, any other error is reported as unexpected (so `correct` blocks must be clean); also flags missing language tags, bad ecmaVersion, duplicate config comments — **Observed** L176-263, `Makefile.js` L934-939, `package.json` L60/116.
- Rule `meta`: `type`, `docs.description`, `docs.recommended`, `docs.url`, `fixable` ("code"/"whitespace", mandatory if fixing), `hasSuggestions` (mandatory if suggesting), `schema`, `defaultOptions`, `deprecated` (+`replacedBy`) — **Observed** `lib/rules/no-unused-vars.js`, `docs/src/extend/custom-rules.md` L59-111.
- Suggestions = manual, standalone fixes (never auto-applied, no multipass), vs `--fix` autofix multipass ≤10 — **Observed** custom-rules.md L330, L401-440. This is ESLint's fix-safety split.
- Core formatters now: stylish (default), json, json-with-metadata, html — **Observed** `lib/cli-engine/formatters/`. (SARIF via external `@microsoft/eslint-formatter-sarif` — **Observed** in reviewdog README example.)

### B.7. Vale (MIT) + vale-action (MIT) — ring: pattern-donor

Source: errata-ai/vale `9f822e9da55aa349e96ea43f01d4724fbd6d6600` (2026-10-16); vale-action `518a9136acc6e6668ce7c00d367051e0941e87ff` (2026-08-03). Both MIT — **Observed**.
- `--output` = `CLI` (default), `line`, `JSON`, or a template file — **Observed** `cmd/vale/flag.go` L25.
- Rules are YAML with `extends:` check types; in testdata: existence 69, substitution 28, metric 10, sequence 9, spelling/occurrence/capitalization 6, script/consistency 3, repetition 2, readability 1, conditional 1 — **Observed** grep of `testdata/styles`.
- Alert JSON fields: Action, Suggestions, Span, Check, Description, Link, Message, Severity (suggestion/warning/error), **Match (the actual matched text)**, Line — **Observed** `internal/core/alert.go` L20-41. Echoing Match is an anti-pattern for confidential drafts.
- Network: `vale sync` downloads packages; optional `NLPEndpoint` external API; otherwise linting is local — **Observed** config.go L246 / **Inferred** offline for linting.
- vale-action: runs Vale `--output=JSON`, converts to rdjsonl itself, pipes to reviewdog; default `reporter: github-pr-annotations`, `filter_mode: added`, `fail_on_error: false`, `token: github.token`, pins reviewdog 0.21.0 — **Observed** `action.yml`, `src/input.ts` L170-173, `src/main.ts` L279.

### B.8. textlint (MIT)
textlint/textlint `dd3d12f13ebe610ec101b21a6f7e85df9f75d0bc` (2026-10-18), MIT — **Observed**.
- Formatters: checkstyle, compact, github, jslint-xml, json, junit, pretty-error, stylish, table, tap, unix — **Observed** `packages/@textlint/linter-formatter/src/formatters/`.
- github formatter wraps each file in `::group::` and escapes data/properties; title `TextLint [ruleId]` — **Observed** github.ts L44-82.
- Filter rules (e.g. `"filters": {"comments": true}`) suppress results; same authoring convention as rules — **Observed** `docs/filter-rule.md`.
- `--mcp` exists: starts textlint as an MCP server over stdio (v14.8.0+; combinable with other flags from v15.2.0) — **Observed** `docs/cli.md` L76, `docs/mcp.md`.

### B.9. Conftest (Apache-2.0)
open-policy-agent/conftest `ca2dfd71a5c673d5f8c207c8788f18c69a6250c7` (2026-10-15), Apache-2.0 — **Observed**.
- Outputs: stdout, json, tap, table, junit, github, azuredevops, sarif — **Observed** `output/output.go` L37-46.
- Location: only when the Rego policy returns a `_loc` object with `file`/`line`; SARIF region = startLine=endLine=line (no columns); github output `::level file=,line=::msg` inside `::group::` — **Observed** `output/result.go` L29-30, L53-80; `output/sarif.go` L92-97; `output/github.go` L54-97. No automatic JSON-path→line mapping — **Inferred**.

### B.10. Spectral (Apache-2.0)
stoplightio/spectral `95ab37eeea1f69ee9ae1a43b88f3ed1df007f190` (2026-10-13), Apache-2.0 — **Observed**.
- Formatters: code-climate, github-actions, html, json, junit, markdown, pretty, sarif, stylish, teamcity, text — **Observed** `packages/formatters/src/`.
- JSON-path → range: `Document.getRangeForJsonPath(path, closest)` calls the parser's `getLocationForJsonPath` on the pointer-preserving parse result; `closest` falls back to the nearest existing ancestor (used for missing keys) — **Observed** `packages/core/src/document.ts` L44-86, `documentInventory.ts` (`getClosestJsonPath`).
- github-actions formatter: relative paths, newlines → `%0A`, appends rule documentation URL — **Observed** github-actions.ts L25-51. SARIF sets `helpUri` from `rule.documentationUrl` — **Observed** sarif.ts L36.
- Ruleset `documentationUrl` + `#rule-name` anchor per finding; absent → no links — **Observed** `docs/guides/4-custom-rulesets.md` L94-110.
- Rule reference entry: rule id heading, one-line requirement, "Why?", **Recommended**, **Default severity**, **Bad Example**, **Good Example** — **Observed** `docs/reference/openapi-rules.md`. Rule tests live separately (`packages/rulesets/src/oas/__tests__`, 59 files); doc examples not auto-checked — **Observed** / **Inferred**.

### B.11. XBRL US DQC rules — custom licence (not OSI; pattern only)
DataQualityCommittee/dqc_us_rules `64abefd357c34ef45f9f4336a1e3171984d76601` (2026-10-19) — **Observed**.
- Licence: copyright AICPA/Calcbench/Toppan Merrill/Workiva/XBRL US; copying allowed but the documents themselves may not be altered — **Observed** `License.md`. Treat as pattern source only.
- Rule doc (`docs/DQC_US_0001/DQC_0001.md`): title; Rule ID; Status; Release date; Effective date; Rule function; Data Quality Guidance; Basis for rule (cites SEC staff observations, FASB guides); Problem solved; Example rule message (with "Rule version: x"); For Developers → Message template with `${ruleVersion}`; Rule element ID index; Appendix of post-implementation edits; companion .xlsx lists — **Observed**.
- Versioning: semver MAJOR.MINOR.FIX; majors open with public comment period + RC tags; each release includes all prior approved rules; messages carry rule version — **Observed** README L23-33.
- Tests: pass/fail XBRL filings per rule; JSON test-case manifest consumed by GitHub Actions — **Observed** `tests/readme.md`.

### B.12. ESEF conformance suite / Reporting Manual
- esma.europa.eu unreachable. Only indirect evidence: Arelle downloads `esef_conformance_suite_2024.zip` from an ESMA URL and runs it with expected-error overrides — **Observed** Arelle config. Reporting manual content: **not read**.

### B.13. Semgrep CE (LGPL-2.1) and LanguageTool (LGPL-2.1) — pattern only
- Semgrep LICENSE is GNU LGPL 2.1 — **Observed** https://raw.githubusercontent.com/semgrep/semgrep/develop/LICENSE. No further reading (time).
- LanguageTool `8ed25c5c3f75160edad6c986626aa6edfedd5f1f`, COPYING = LGPL — **Observed**. JSON matches: `message`, `shortMessage`, `offset`, `length` (to−from), `replacements[{value, shortDescription, type, confidence}]`, `context{text, offset, length}`, `rule`, `contextForSureMatch`, `ignoreForIncompleteSentence`; top-level `incompleteResults` flag — **Observed** `languagetool-core/src/main/java/org/languagetool/tools/RuleMatchesAsJsonSerializer.java`. `context.text` echoes the surrounding document text — anti-pattern for public CI.

### B.14. CUAD / LegalBench (Q8)
- CUAD (`67faa0e6…`, 2021): `evaluate.py` matches spans by Jaccard ≥ `IOU_THRESH = 0.5` (or substring), sweeps confidence thresholds 0.99→0, reports **AUPR** (sklearn auc over monotone-ised precision), **precision at 80% recall** and **at 90% recall**; per-category supported; **no confidence intervals / bootstrap** (grep: none) — **Observed**. Licence not stated in readme — unknown.
- LegalBench (`b46bf4ff…`): 162 tasks / 40 contributors; `evaluation.py` uses exact-match **balanced accuracy** for most tasks, F1 for some (e.g. successor liability, SSLA), task-specific scorers; **no intervals** (grep: none); licences vary per task — **Observed** README + https://raw.githubusercontent.com/HazyResearch/legalbench/main/evaluation.py.
- For us (Inferred): publish per-rule precision/recall on a labelled corpus of white-paper drafts with Wilson/bootstrap intervals — neither donor does intervals, so that's a differentiator rather than a copied pattern.

---

### B.Answers

### Q3. Which output unlocks which PR surface, with which permissions?
| Output | PR surface | Permission | Forks | Private repo | Tag |
|---|---|---|---|---|---|
| Workflow commands `::error file=,line=::` | Inline annotations on "Files changed" + run summary | none beyond default (no token needed) | works | works | Observed (docs); caps Claimed (10/10 per step, 50/job) |
| `$GITHUB_STEP_SUMMARY` Markdown | Run summary page (not in diff) | none | works | works | Observed (1 MiB/step, 20 per job) |
| SARIF via `codeql-action/upload-sarif` | Code scanning alerts + PR check + alert annotations on diff | `security-events: write` (+ `actions: read`, `contents: read` private) | write downgraded → fails by default | needs GitHub Code Security | Observed / Inferred for forks |
| rdjson → reviewdog `github-pr-review` | PR review comments + suggestion blocks | `pull-requests: write` | degrades to annotations | works | Observed |
| rdjson → reviewdog `github-pr-check`/`github-check` | Check run with annotations; status neutral/failure | `checks: write` | degrades to annotations | works | Observed |
| rdjson → `github-pr-annotations` | Same as workflow commands | token for diff only | works | works | Observed |
Recommendation (Inferred): default = workflow-command annotations (rule ID + short message only, no document text) + step summary table; opt-in SARIF (`--format sarif`) for orgs with Code Security; emit rdjson so reviewdog users get review comments.

### Q4. Mapping JSON keys / XHTML elements / numbered fields to SARIF regions
- Spectral: parse with a position-preserving parser, then `getLocationForJsonPath(path, closest=true)`; a missing key maps to the nearest existing ancestor's range — **Observed**. Adopt: keep a JSON-pointer→(line,col,endLine,endCol) map from our JSON loader; missing section → parent object range (fail-closed finding still anchored).
- Conftest: policy must supply `_loc{file,line}`; otherwise no region; line-only (no columns) — **Observed**. Reject as primary approach.
- LanguageTool: character `offset`+`length` on plain text — **Observed**; reviewdog rdjson takes line/column ranges — **Observed**.
- XHTML (Inferred): lxml gives `element.sourceline` (start line); compute end via next sibling or serialise; emit startLine + startColumn=1 when columns unknown (GitHub requires startColumn/endColumn → use 1 and line length). For iXBRL facts, anchor on the `ix:nonFraction`/`ix:nonNumeric` element line and put the concept QName in `logicalLocations` / message.
- Numbered fields (Annex I/II/III item numbers) (Inferred): carry `logicalLocations[{fullyQualifiedName: "AnnexI.PartA.A.3"}]` plus physical location of the heading/field; `partialFingerprints` = hash(ruleId + field id), not line content, so alerts survive edits and don't leak text.
- DOCX (Inferred): no line concept; map to paragraph index (`region.startLine` = paragraph number) and document that convention, or omit SARIF for DOCX and use summary only.

### Q5. What the best rule-doc pages share, and how examples are tested
Shared (Observed across Ruff, ESLint, Spectral, DQC): stable rule ID in title; one-sentence "what it checks"; rationale ("Why is this bad?"/"Why?"/"Problem solved"/"Basis for rule" with citations — DQC cites regulator text, which is our closest analogue to MiCAR Article/Annex citations); bad/good example pair; options; severity/recommended default; lifecycle/version (Ruff "Added in"/preview/deprecated; DQC status + release/effective dates + rule version in message; ESLint `deprecated`/`replacedBy`); fix semantics (Ruff Fix safety; ESLint fixable vs suggestions); links to source/issues (Ruff).
Example testing: ESLint executes every doc example and fails CI if incorrect examples don't trigger or correct ones do (Observed); Ruff checks section presence + example formatting only (Observed); Spectral and DQC keep tests separate from docs (DQC pass/fail filings) (Observed). Adopt ESLint's approach: doc examples are fixtures run by pytest.

### Q8. CUAD and LegalBench accuracy reporting
See B.14: CUAD → AUPR, precision@80%/90% recall, Jaccard≥0.5 span match, no intervals; LegalBench → balanced accuracy (exact match) / F1 per task, no intervals. Both **Observed** in code.
