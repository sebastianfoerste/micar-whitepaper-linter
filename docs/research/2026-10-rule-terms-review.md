# Rule terms against the wording of MiCAR

Stand: 27 October 2026. Rules as on `main` at `0e0939d`, with the changes that #49 makes to `ANNEX_II.D` and `ANNEX_II.I`. This document changes no code; each fix it proposes goes up as its own pull request.

## What was checked

A rule on the generic checks lists terms. A section that lacks one of them, by a case-insensitive substring match, goes to review. For every rule variant in `RULESETS` this review asks two questions:

1. Does the wording of the provision the rule cites contain each term, in English and in German?
2. Where it does not, will a complete section still contain the term, or does the term ask for something the provision does not require?

The common rules were checked against the paragraph for each white paper type separately, because one pooled check hides a term that only one of the three paragraphs uses. Proposed terms were also checked against the field labels of the templates in Implementing Regulation (EU) 2024/2984, which every white paper must follow, and against the committed examples (see "Effect on the examples").

### Sources

All texts were read on 27 October 2026 in the Official Journal versions served by the EU Publications Office (Cellar), in English and German. The EUR-Lex website was unreachable from the build environment.

| Instrument | Read | Currency |
|---|---|---|
| Regulation (EU) 2023/1114 (MiCAR), OJ L 150, 9.6.2023 | Art. 3(1)(6) and (7), 6, 8, 19, 36, 37, 39, 46 to 51, 54; Annexes I to III | Same wording, apart from footnote numbers, in the consolidated version of 9 January 2024. The only amending act on record is Regulation (EU) 2023/2869. The English and German corrigenda (2024/90275, 2024/90658) do not touch these provisions. |
| Implementing Regulation (EU) 2024/2984 | Art. 2; Annex, Tables 2 to 4 | No amendment or corrigendum on record. |
| Delegated Regulation (EU) 2025/422 | Art. 4 and the Annex | No amendment or corrigendum on record. |
| Directive 2009/110/EC (EMD2) | Art. 7 | Same wording in the consolidated version of 13 January 2018. |
| Directive (EU) 2015/2366 (PSD2) | Art. 10, Art. 114, correlation table | Consolidated version of 17 January 2025; Art. 10 as amended by Regulation (EU) 2024/886. |

## Findings

Four kinds of defect turned up. A rule can show more than one.

### 1. Terms or citations that misstate the law

| Rule | Defect | Statutory basis |
|---|---|---|
| `ANNEX_III.A` | Requires both "credit institution" and "e-money institution". An issuer of an e-money token is one or the other, and MiCAR's term is "electronic money institution". A complete issuer section fails at least one of the two. | Art. 48(1)(a): "authorised as a credit institution or as an electronic money institution". Annex III Part A asks for the legal form (No. 2), registered address (No. 3), members of the management body (No. 8) and the authorisation (No. 13), and names no institution type. |
| `ANNEX_III.C` | Requires "subscription" and "target market". The EMT part has no subscription items and no target market. | Annex III Part C has four items: offer or admission to trading, number of units, trading platforms, applicable law and competent court. |
| `ANNEX_II.B` | Requires "basket". An asset-referenced token may reference a single value. | Art. 3(1)(6): "another value or right or a combination thereof". |
| `ANNEX_I.F` (German) | Requires "kryptowertpapier", which does not occur in MiCAR. | German MiCAR builds its terms on "Kryptowert" (1,912 occurrences of the stem) and never uses "Kryptowertpapier". |
| `ANNEX_II.G.VALUATION_AUDIT` | Cites Art. 36(3), and its label repeats "(Art. 36(3) MiCAR)". Art. 36(3) concerns the operational segregation of the reserve. | Valuation: Art. 36(7), (11) and (12). Independent audit every six months: Art. 36(9), notification of its results: Art. 36(10). |

### 2. The Regulation's own wording fails the check

| Rule | Term | What the Official Journal says |
|---|---|---|
| `COMMON.MANAGEMENT_STATEMENT` (German) | "entspricht" | Only Art. 19(5) says "diesem Titel entspricht". Art. 6(6) says "diesem Titel Rechnung trägt", and Art. 51(5) says "die Anforderungen des vorliegenden Titels erfüllt". A statement in the words of Art. 6(6) or Art. 51(5) goes to review. All three say "Titel". |
| `ANNEX_II.B` (German) | "vermögenswertreferenziert" | The Official Journal spells it "vermögenswertereferenziert" 758 times and "vermögenswertreferenziert" 59 times. A section in the more common spelling goes to review. |
| `ANNEX_III.B` (German) | "offizielle währung" | Does not occur in MiCAR, which says "amtliche Währung" throughout. |
| `ANNEX_III.D` (German) | "rückzahlung", "zu par" | Annex III Part D No. 1: "Rücktausch zum Nennwert"; Art. 49(4): "jederzeit und zum Nennwert". MiCAR's word for redemption is "Rücktausch" (102 occurrences, against 2 for "Rückzahlung"); "zu par" does not occur. |
| `ANNEX_II.F`, `ANNEX_III.F` (German) | "rücknahme" | MiCAR uses "Rücknahme" once and "Rücktausch" 102 times. |
| `ANNEX_III.SAFEGUARDING` | "safeguarding", "segregated" (German "absicherung", "getrennt") | Art. 54 says the funds are "safeguarded in accordance with Article 7(1) of Directive 2009/110/EC" ("besichert"), and Art. 54(a) requires deposits "in separate accounts in credit institutions" ("auf gesonderten Konten bei Kreditinstituten"). "safeguarded" does not contain "safeguarding". "segregated" occurs in neither Art. 54 nor EMD2 Art. 7; PSD2 Art. 10 uses it once, for the insurance method in point (b), and describes the account method in point (a) as funds that "shall not be commingled" and are deposited "in a separate account". |
| `ANNEX_I.J`, `ANNEX_II.H`, `ANNEX_III.G` | "environmental" | Delegated Regulation 2025/422 and the template headings say "environment-related" (17 times in the Delegated Regulation); "environmental" occurs there once. The German terms are found. |

### 3. Terms the cited provision does not ask for

These terms send a complete section to review when its author follows the Annex and the template. They are proxies the rule's author chose, mostly risk categories or concepts from another Part.

| Rule | Terms | What the provision and the template ask for |
|---|---|---|
| `ANNEX_I.D` | "purpose", "business model"; German "zweck", "geschäftsmodell", "team" | Annex I Part D: project name, description, the persons involved ("development team"; German "Entwickler"), past and future milestones (German "Projekt-Etappen"), resources, use of funds. Template D.8: "Plans for the token". |
| `ANNEX_I.E`, `ANNEX_II.C` | "jurisdictions" | Annex I Part E No. 19 and Annex II Part C No. 15: "the law applicable to the offer ..., as well as the competent court". |
| `ANNEX_II.C` | "issuance", "target market" | Annex II Part C No. 4: "prospective holders targeted by the offer"; template C.8: "Targeted holders". |
| `ANNEX_I.F` | "supply", "transfer"; German "übertragung", "funktionsweise" | These belong to Annex I Part G Nos. 7 and 8. Part F asks for the type, the characteristics and the functionality ("Funktionen"); template F.6: "Crypto-asset characteristics". The German "angebot" is matched by any "öffentlich angeboten". |
| `ANNEX_I.G` | "holder", "enforce"; German "inhaber", "durchsetzen" | Annex I Part G speaks of the "purchaser" and of "the procedure and conditions for the exercise of those rights" (German "Ausübung"), and No. 10 asks for the applicable law and the competent court. Template G.2: "Exercise of rights and obligations"; G.19: "Competent court". |
| `ANNEX_I.H` | "smart contract" | Annex I Part H No. 1: "distributed ledger technology, protocols and technical standards". A token that runs without smart contracts fails. |
| `ANNEX_II.E`, `ANNEX_III.E` | "custody", "key management" | Annex II and III Part E cover the technology, the consensus mechanism, incentives and fees, a ledger operated by the issuer, and the audit outcome. Custody of keys appears in neither. |
| `ANNEX_I.I`, `ANNEX_II.F`, `ANNEX_III.F` | "market", "credit", "liquidity", "operational", "regulatory", "de-peg", "redemption", "safeguarding" | The risk parts group risks by source: the offer, the issuer, the crypto-asset or token, project implementation (ART: operationalisation), the technology, and mitigation measures; for ARTs also the reserve of assets (Annex II Part F No. 1). The templates label the fields "Offer-related risks", "Issuer-related risks", "Technology-related risks", "Mitigation measures". For ARTs, credit, market, concentration and liquidity risk appear in Art. 36(8)(c), the stabilisation policy, and not in Part F. |
| `ANNEX_II.B` | "reference assets", "stabilisation" | Annex II Part B asks for the name, characteristics, persons involved, third-party roles and plans. The referenced assets belong to Part D No. 10, the alignment of the reserve with the claim to Part G No. 1, and the stabilisation policy to Art. 36(8). "asset-referenced" is matched by any section about the token. |
| `ANNEX_III.B` | "referenced", "official currency", "denomination" | Annex III Part B asks for the name, characteristics and persons involved; template B.6: "Crypto-asset characteristics". "referencing ... one official currency" is the definition in Art. 3(1)(7); "denomination" occurs in neither. |
| `ANNEX_III.D` | "no interest" | Art. 50(1) prohibits granting interest ("shall not grant interest"). Annex III Part D does not ask the white paper to state it, and the statutory words do not contain "no interest". Part D No. 6 asks for complaints handling, which the rule does not check. |

### 4. Citations and labels

| Rule | Finding | Proposal |
|---|---|---|
| `ANNEX_II.G.VALUATION_AUDIT` | See class 1. | Cite "Anhang II Teil G i.V.m. Art. 36 Abs. 7, 9 und 11 MiCAR" and say so in the label. |
| `ANNEX_II.G.CUSTODY` | The label says "(Art. 36(2) MiCAR)". Art. 36(2) is the legal segregation of the reserve; the custody policy is Art. 37. The citation names both. | Label "(Art. 36(2), Art. 37 MiCAR)". |
| `ANNEX_II.I` | Looks for "suspension", which comes from Art. 46: the recovery plan may provide for "suspension of redemptions" (Art. 46(1)(c)), and the competent authority may "temporarily suspend the redemption" (Art. 46(4)). The citation does not name Art. 46. | Add Art. 46 to the citation. |
| `ANNEX_III.SAFEGUARDING` | "insolvency" occurs only in PSD2 Art. 10(1)(a) ("in particular in the event of insolvency"). EMD2 Art. 7(1) refers to Art. 9(1) and (2) of Directive 2007/64/EC, which PSD2 Art. 114 and its correlation table turn into a reference to PSD2 Art. 10(1) and (2). The citation stops at EMD2 Art. 7. | Add "Art. 10 Richtlinie (EU) 2015/2366"; `citations.py` needs an `ACT_URLS` entry and an English name for it. |
| `COMMON.LEI_CHECK_DIGITS`, `COMMON.LEI_CONSISTENCY` | Confirmed. Annex I, II and III Part A each name the legal entity identifier in No. 5 (German "Unternehmenskennung"). Art. 2(1)(b) and (c) of Implementing Regulation 2024/2984 also require the persons concerned to be identified in the Inline XBRL document by their ISO 17442 legal entity identifier, where available. The rule pages still call this point unverified. | Cite "Teil A Nr. 5" and replace the pending-review note on the two rule pages. |
| `COMMON.IXBRL_TAGGING` | Confirmed. Art. 2(1) of Implementing Regulation 2024/2984 requires the white paper in XHTML with the fields marked up in Inline XBRL 1.1. | None. |

### Rules confirmed without change

`COMMON.SUMMARY`, `COMMON.RISK_WARNING` (both variants, since #46 and #47), `COMMON.NOTIFICATION_DATE` and `COMMON.LANGUAGE` find every term in each type's paragraph in both languages. So do `ANNEX_I.A`, `ANNEX_I.B`, `ANNEX_I.C`, `ANNEX_II.A`, `ANNEX_II.D` (with #49), `ANNEX_II.G.COMPOSITION_DISCLOSURE` (whose "deposit" and "concentration" come from Art. 36(8)) and the terms of `ANNEX_II.G.CUSTODY` and `ANNEX_II.I` (with #49). `ANNEX_II.G.DEPOSIT_FLOOR_REVIEW` has its own logic and no terms.

## Proposed terms

Each proposal takes its words from the Annex item and the template field the rule covers. Stems cover the German inflections and both spellings.

| Rule | English | German |
|---|---|---|
| `COMMON.MANAGEMENT_STATEMENT` | unchanged | "titel" in place of "entspricht" |
| `ANNEX_I.D` | project, milestones | projekt, etappen |
| `ANNEX_I.E` | court in place of jurisdictions | gericht in place of jurisdiktionen |
| `ANNEX_I.F` | characteristics, functionality | merkmale, funktion |
| `ANNEX_I.G` | rights, obligations, exercise, court | rechte, pflichten, ausübung, gericht |
| `ANNEX_I.H` | ledger in place of smart contract | ledger in place of smart contract |
| `ANNEX_I.I` | offer, project, technology, mitigation | angebot, projekt, technologie, minderung |
| `ANNEX_I.J`, `ANNEX_II.H`, `ANNEX_III.G` | environment in place of environmental | unchanged |
| `ANNEX_II.B` | characteristics, milestones | merkmale, etappen |
| `ANNEX_II.C` | offer, holders, court | angebot, inhaber, gericht |
| `ANNEX_II.E`, `ANNEX_III.E` | ledger, protocol, consensus, audit | ledger, protokoll, konsens, prüfung |
| `ANNEX_II.F` | reserve, issuer, offer, technology, mitigation | reserve, emittent, angebot, technologie, minderung |
| `ANNEX_III.A` | issuer, legal form, registered, address, management body | emittent, rechtsform, eingetragen, anschrift, leitungsorgan |
| `ANNEX_III.B` | e-money token, characteristics | e-geld-token, merkmale |
| `ANNEX_III.C` | offer, court | angebot, gericht |
| `ANNEX_III.D` | rights, redemption, at par, complaints, holder | rechte, rücktausch, nennwert, beschwerden, inhaber |
| `ANNEX_III.F` | issuer, technology, mitigation | emittent, technologie, minderung |
| `ANNEX_III.SAFEGUARDING` | safeguard, separate, credit institution, insolvency | sicher, gesondert, kreditinstitut, insolvenz |

Three choices in this table need a decision from the owner. `ANNEX_II.B` loses its check of the referenced assets and the stabilisation mechanism unless a rule that cites Annex II Part D No. 10, Part G No. 1 and Art. 36(8) takes them over. `ANNEX_I.D` and `ANNEX_II.B` could use "plan" (template "Plans for the token") in place of "milestones" (the Annex wording); "plan" also matches "explanation". The German "sicher" also matches "sichere Aktiva", which every safeguarding section contains.

## Effect on the examples

Measured on the committed examples with the proposed terms in place of the current ones:

- `examples/art-stablecoin.json`: `ANNEX_II.B`, `ANNEX_II.C`, `ANNEX_II.E` and `ANNEX_II.F` go from Pass to Review. The example's texts were written to the current terms; a fix PR rewrites them to the Annex items.
- `examples/other-crypto-asset.json`: `ANNEX_I.E`, `ANNEX_I.F`, `ANNEX_I.G` and `ANNEX_I.H` go from Pass to Review, for the same reason.
- `examples/numbered-other-draft.xhtml` and `docs/playground/sample-numbered.xhtml`: `ANNEX_I.F` and `ANNEX_I.I` go from Pass to Review. Both follow the template but leave out the fields F.6, I.4 and I.6, which a complete white paper carries.
- `examples/emt-token.json` and `examples/sample-draft.xhtml`: the EMT rules that change are already at Review; the missing terms they report change.

Every example change feeds the generated outputs listed in `AGENTS.md` section 6, so each fix PR regenerates them.

## German Official Journal text

Two points affect the choice of German terms. The adjective appears as "vermögenswertereferenziert" and as "vermögenswertreferenziert" (see class 2). Annex III Part B No. 2 of the German text reads "Beschreibung der Merkmale des vermögenswertreferenzierten Token", in the annex on e-money tokens, where the English text says "the characteristics of the e-money token".

## Proposed order of the fix pull requests

1. Classes 1 and 2, without the risk parts: `ANNEX_III.A`, `ANNEX_III.C`, `ANNEX_I.F` (German), `ANNEX_II.B` ("basket" and the German spelling), `COMMON.MANAGEMENT_STATEMENT` (German), `ANNEX_III.B` (German), `ANNEX_III.D`, `ANNEX_III.SAFEGUARDING` and the three environmental rules.
2. Class 4: the citations and labels of `ANNEX_II.G.VALUATION_AUDIT`, `ANNEX_II.G.CUSTODY`, `ANNEX_II.I`, `ANNEX_III.SAFEGUARDING` and the LEI rules.
3. Class 3: the remaining terms, with the examples rewritten to the Annex items and the generated outputs refreshed.

## Limits

The check is a substring test, so every proposed term is a heuristic too: it catches a section that leaves the item out and can miss a paraphrase. Where the review calls a term a defect, it relies on the provision's wording; whether a complete section in practice contains a proxy term is a judgement, marked as class 3.
