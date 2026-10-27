# Rule terms against the wording of MiCAR

Stand: 27 October 2026. Rules as on `main` at `0e0939d`, with the changes that #49 makes to `ANNEX_II.D` and `ANNEX_II.I`. This document changes no code; each fix it proposes goes up as its own pull request.

## What was checked

A rule on the generic checks lists terms. A section that lacks one of them, by a case-insensitive substring match, goes to review. For every rule variant in `RULESETS` this review asks two questions:

1. Does the wording of the provision the rule cites contain each term, in English and in German?
2. Where it does not, will a complete section still contain the term, or does the term ask for something the provision does not require?

This review checked the common rules and the risk parts against the paragraph or Part for each white paper type separately, because one pooled check hides a term that only one of them uses. It also checked the proposed terms against the field labels and filling instructions of the templates in Implementing Regulation (EU) 2024/2984 and against the committed examples (see "Effect on the examples"). The templates apply from 23 December 2025 (Art. 4). White papers notified before that date were drawn up on the Annexes alone, so the template points below do not apply to them.

A reviewer who had not seen the drafting then checked every legal proposition in this review against the Official Journal. This version includes the reviewer's corrections.

### Sources

All texts were read on 27 October 2026 in the Official Journal versions served by the EU Publications Office (Cellar), in English and German. The EUR-Lex website was unreachable from the build environment.

| Instrument | Read | Currency |
|---|---|---|
| Regulation (EU) 2023/1114 (MiCAR), OJ L 150, 9.6.2023 | Recitals 66 and 70; Art. 3(1)(6) and (7), 6, 8, 19, 36, 37, 39, 46 to 51, 54; Annexes I to III | The articles and Annexes read have the same wording, apart from footnote numbers, in the consolidated version of 9 January 2024, which carries no recitals. The only amending act on record is Regulation (EU) 2023/2869. The English and German corrigenda (2024/90275, 2024/90658) do not touch these provisions. |
| Implementing Regulation (EU) 2024/2984 | Recitals 2 and 9, Art. 2 and 4; Annex, Tables 2 to 4 | Applies from 23 December 2025. No amendment or corrigendum on record. |
| Delegated Regulation (EU) 2025/422 | Recital 9, Art. 4 and the Annex | No amendment or corrigendum on record. |
| Directive 2009/110/EC (EMD2) | Art. 1, 7 and 9 | Same wording in the consolidated version of 13 January 2018. |
| Directive (EU) 2015/2366 (PSD2) | Art. 10, Art. 114, correlation table | Consolidated version of 17 January 2025; Art. 10 as amended by Regulation (EU) 2024/886. |

## Findings

Four kinds of defect turned up. A rule can show more than one.

### 1. Terms or citations that misstate the law

| Rule | Defect | Statutory basis |
|---|---|---|
| `ANNEX_III.A` | Requires both "credit institution" and "e-money institution". An issuer is authorised as one or the other, and an exempt issuer needs neither authorisation, so a complete issuer section need not name both. MiCAR's term is "electronic money institution" (28 occurrences), which never matches "e-money institution" (no occurrence). | Art. 48(1)(a): "authorised as a credit institution or as an electronic money institution". Art. 48(4) disapplies paragraph 1 for issuers exempted under Art. 9(1) EMD2, which are registered and treated as electronic money institutions (Art. 9(3) EMD2). Art. 48(5) disapplies Title IV, except Art. 48(7) and Art. 51, for e-money tokens exempt under Art. 1(4) and (5) EMD2, whose issuer need be neither. Both still draw up a white paper (Art. 48(7)); Annex III Part A No. 13 and template field A.24 ("Exemption from authorisation") provide for them. Annex III Part A names no institution type. |
| `ANNEX_I.A`, `ANNEX_I.B`, `ANNEX_II.A`, `ANNEX_III.A` | Require "registered" and, except `ANNEX_I.B` and `ANNEX_III.A`, "legal form" (German "eingetragen", "rechtsform"). A white paper that gives an LEI need not state the legal form or the registered address, so a complete section that gives an LEI and leaves them out goes to review. | Recital 2 of Implementing Regulation 2024/2984: where a valid LEI is provided, the white paper need not contain the information retrievable from it, namely "legal form, registered address and head office (where different) and identity of the parent company". The templates say to fill these fields only where no LEI is provided: Table 2 A.2 to A.4 and A.11, B.3 to B.5 and B.9, C.2 to C.4 and C.8; Table 3 A.3 to A.5 and A.9; Table 4 A.3 to A.5 and A.12. The Annexes list both items without condition (No. 2 and No. 3 of each party Part). "address" stays a fair term, because every party Part asks for the business addresses of the members of the management body. |
| `ANNEX_III.C` | Requires "issuance", "subscription" and "target market" (German "emission", "zeichnung", "zielmarkt"). The EMT part has none of these items. | Annex III Part C has four items: offer or admission to trading, number of units, trading platforms, applicable law and competent court. |
| `ANNEX_II.B` | Requires "basket". An asset-referenced token may reference a single value. | Art. 3(1)(6): "another value or right or a combination thereof". |
| `ANNEX_I.F` (German) | Requires "kryptowertpapier", which does not occur in MiCAR. | German MiCAR builds its terms on "Kryptowert" (more than 1,900 occurrences of the stem) and never uses "Kryptowertpapier". |
| `ANNEX_II.G.VALUATION_AUDIT` | Cites Art. 36(3), and its label repeats "(Art. 36(3) MiCAR)". Art. 36(3) concerns the operational segregation of the reserve. Class 3 covers its terms. | Valuation: Art. 36(7), (11) and (12). Independent audit every six months: Art. 36(9); notification and publication of its results: Art. 36(10). |

### 2. The Regulation's own wording fails the check

| Rule | Term | What the Official Journal says |
|---|---|---|
| `COMMON.MANAGEMENT_STATEMENT` (German) | "entspricht" | Only Art. 19(5) says "diesem Titel entspricht". Art. 6(6) says "diesem Titel Rechnung trägt", and Art. 51(5) says "die Anforderungen des vorliegenden Titels erfüllt". The templates' predefined German statement says "Dieses Kryptowerte-Whitepaper erfüllt Titel II", and "Titel III" and "Titel IV" for the two token types (Table 2 field 03; Tables 3 and 4 field I.03), so a statement in the template's words goes to review whatever the type. All of these say "Titel". |
| `ANNEX_II.B` (German) | "vermögenswertreferenziert" | Annex II Part B uses both spellings. No. 2 has "vermögenswertreferenzierten", while the heading, Nos. 1, 3 and 5 and all eight mentions in Part B of the German template (Table 3) have "vermögenswertereferenzierten". The Official Journal as a whole has 758 against 59. A section in the predominant spelling goes to review. |
| `ANNEX_III.B` (German) | "offizielle währung" | Does not occur in MiCAR, which says "amtliche Währung" throughout. |
| `ANNEX_III.D` (German) | "rückzahlung", "zu par" | Annex III Part D No. 1: "Rücktausch zum Nennwert"; Art. 49(4): "jederzeit und zum Nennwert". MiCAR's word for redemption is "Rücktausch" (102 occurrences, against 2 for "Rückzahlung"); "zu par" does not occur. |
| `ANNEX_II.F`, `ANNEX_III.F` (German) | "rücknahme" | MiCAR never uses "Rücknahme" as a word of its own; its one match is inside "Zurücknahme eines Gebots" (Art. 89). The word for redemption is "Rücktausch" (102 occurrences). |
| `ANNEX_III.SAFEGUARDING` | "safeguarding", "segregated" (German "absicherung", "getrennt") | Art. 54 says the funds are "safeguarded in accordance with Article 7(1) of Directive 2009/110/EC" ("besichert"), and Art. 54(a) requires deposits "in separate accounts in credit institutions" ("auf gesonderten Konten bei Kreditinstituten"). "safeguarding" occurs only in the headings of EMD2 Art. 7 and PSD2 Art. 10 ("Safeguarding requirements"), so a section in the words of Art. 54 goes to review. "segregated" occurs in neither Art. 54 nor EMD2 Art. 7; PSD2 Art. 10 uses it once, for the insurance method in point (b), and describes the account method in point (a) as funds that "shall not be commingled" and are deposited "in a separate account". In German, "Absicherung" occurs in none of the three (EMD2 Art. 7 is headed "Sicherungsanforderungen"), and "getrennt" only in PSD2 Art. 10(1)(b) ("getrennt gehalten"). Class 3 covers the rule as a whole. |
| `ANNEX_I.J`, `ANNEX_II.H`, `ANNEX_III.G` | "environmental" | Delegated Regulation 2025/422 and the template headings say "environment-related" (17 times in the Delegated Regulation). "environmental" occurs there only inside "environmentally friendly" in recital 9; Art. 4, its Annex and the English templates never use it. The German terms are found. |

### 3. Terms the cited provision does not ask for

These terms send a complete section to review when its author follows the Annex and the template. They are proxies the rule's author chose, mostly risk categories or concepts from another Part or from an article outside the Annexes.

| Rule | Terms | What the provision and the template ask for |
|---|---|---|
| `ANNEX_I.D` | "purpose", "business model"; German "zweck", "geschäftsmodell", "team" | Annex I Part D: project name, description, the persons involved ("development team"; German "Entwickler"), past and future milestones (German "Projekt-Etappen"), resources, use of funds. Template D.8: "Plans for the token". |
| `ANNEX_I.E`, `ANNEX_II.C` | "jurisdictions" | Annex I Part E No. 19 and Annex II Part C No. 15: "the law applicable to the offer ..., as well as the competent court". |
| `ANNEX_II.C` | "issuance", "target market" | Annex II Part C No. 4: "prospective holders targeted by the offer"; template C.8: "Targeted holders". |
| `ANNEX_I.F` | "supply", "transfer"; German "übertragung", "funktionsweise" | These belong to Annex I Part G Nos. 7 and 8. Part F asks for the type, the characteristics and the functionality ("Funktionen"); template F.6: "Crypto-asset characteristics". The German "angebot" is matched by any "öffentlich angeboten". |
| `ANNEX_I.G` | "holder", "enforce"; German "inhaber", "durchsetzen" | Annex I Part G speaks of the "purchaser" and of "the procedure and conditions for the exercise of those rights" (German "Ausübung"), and No. 10 asks for the applicable law and the competent court. Template G.2: "Exercise of rights and obligations"; G.19: "Competent court". |
| `ANNEX_I.H` | "smart contract" | Annex I Part H No. 1: "distributed ledger technology, protocols and technical standards". A token that runs without smart contracts fails. |
| `ANNEX_II.E`, `ANNEX_III.E` | "custody", "key management" | Annex II and III Part E cover the technology, the consensus mechanism, incentives and fees, a ledger operated by the issuer, and the audit outcome; Annex III Part E also the technical requirements a purchaser must meet to gain control over the token (No. 2). Custody of keys appears in neither. |
| `ANNEX_I.I` | "market", "regulatory", "liquidity", "operational" | Annex I Part I groups risks by source: the offer, the issuer, the crypto-assets, project implementation, and the technology with mitigation measures. Template I.1 to I.6: "Offer-related risks", "Issuer-related risks", "Crypto-assets-related risks", "Project implementation-related risks", "Technology-related risks", "Mitigation measures". |
| `ANNEX_II.F` | "market", "credit", "liquidity", "de-peg", "redemption"; German also "operativ" | Annex II Part F has the sources of Annex I, with operationalisation in place of project implementation (No. 5), and adds the reserve of assets (No. 1); template F.1 to F.7. The English "operational" matches "operationalisation"; the German "Operationalisierung" does not contain "operativ". Credit, market, concentration and liquidity risk appear in Art. 36(8)(c), the stabilisation policy, and not in Part F. |
| `ANNEX_III.F` | "market", "credit", "liquidity", "operational", "redemption", "safeguarding" | Annex III Part F has three items: the issuer, the e-money token, and the technology with mitigation measures. Template F.1 to F.4: "Issuer-related risks", "Token-related risks", "Technology-related risks", "Mitigation measures". |
| `ANNEX_II.B` | "reference assets", "stabilisation" | Annex II Part B asks for the name, characteristics, persons involved, third-party roles and plans. The referenced assets belong to Part D No. 10, the alignment of the reserve with the claim to Part G No. 1, and the stabilisation policy to Art. 36(8). "asset-referenced" is matched by any section about the token. |
| `ANNEX_II.G.COMPOSITION_DISCLOSURE` | "deposit", "concentration" (German "einlagen", "konzentration") | Annex II Part G No. 2 asks for "the reserve of assets and their composition" (template G.2: "Asset reserve description"). In Art. 36, "deposit" occurs only in paragraph 4, second subparagraph, point (d), the mandate for regulatory technical standards on the minimum deposits in each referenced official currency, and "concentration" only in Art. 36(8)(c), the stabilisation policy. No item of Part G asks for either. |
| `ANNEX_II.G.VALUATION_AUDIT` | "valuation", "audit" | Neither Annex II Part G nor template Part G (G.1 to G.8) has a valuation or audit item. The white paper item on valuation is Annex II Part D No. 10(c), how "a fair and transparent valuation of components of the claim is undertaken" (template D.21: "Transparent claim valuation"), which belongs to the rights section. No Annex II item asks for the six-monthly reserve audit of Art. 36(9); its results are notified and published under Art. 36(10). |
| `ANNEX_III.B` | "referenced", "official currency", "denomination"; German also "stückelung" | Annex III Part B asks for the name, characteristics and persons involved; template B.6: "Crypto-asset characteristics". "referencing ... one official currency" is the definition in Art. 3(1)(7); "denomination" and "Stückelung" occur in neither Part B nor the template. |
| `ANNEX_III.D` | "no interest" | Art. 50(1) prohibits granting interest ("shall not grant interest"). Annex III Part D does not ask the white paper to state it, and the statutory words do not contain "no interest". Part D No. 6 asks for complaints handling, which the rule does not check. |
| `ANNEX_III.SAFEGUARDING` | the whole rule | No Annex III item and no field of template Table 4 asks for the safeguarding arrangements. The rule's words come from Art. 54, which governs the investment of the funds received, and from EMD2 Art. 7 and PSD2 Art. 10. Art. 54 covers funds "safeguarded in accordance with Article 7(1) of Directive 2009/110/EC", a provision addressed to electronic money institutions. On that wording it does not reach funds received by a credit institution, or by an institution whose Member State waived Art. 7 under Art. 9(1) EMD2; Art. 48(3), which applies Titles II and III of EMD2 "with respect to e-money tokens", and recital 66 leave room for the opposite reading. The nearest white paper items are Annex III Part D No. 3, the rights of holders when the issuer cannot fulfil its obligations, "including in insolvency" (template D.3), and No. 7, protection schemes, where applicable. |

### 4. Citations and labels

| Rule | Finding | Proposal |
|---|---|---|
| `ANNEX_II.G.VALUATION_AUDIT` | See classes 1 and 3. Art. 36(3) is wrong whatever the rule ends up checking. | Depends on the owner's decision on the rule (see "Proposed terms"). In the reserve section it cites "Anhang II Teil G i.V.m. Art. 36 Abs. 7 und 9 bis 12 MiCAR"; as a check of the valuation item it cites "Anhang II Teil D Nr. 10 Buchst. c MiCAR". The label drops "(Art. 36(3) MiCAR)" either way. |
| `ANNEX_II.G.CUSTODY` | The label says "(Art. 36(2) MiCAR)". Art. 36(2) is the legal segregation of the reserve; the custody policy is Art. 37. The citation names both. | Label "(Art. 36(2), Art. 37 MiCAR)". |
| `ANNEX_II.I` | Looks for "suspension", which comes from Art. 46. The recovery plan "shall include" a wide range of recovery options, including "suspension of redemptions" (Art. 46(1), third subparagraph, point (c)), and the competent authority may "temporarily suspend the redemption" (Art. 46(4)). The white paper item is Annex II Part D No. 14, the rights "in the context of the implementation of the recovery plan" (template D.29). The citation names neither. | Add "Teil D Nr. 14" and "Art. 46 Abs. 1 UAbs. 3 Buchst. c und Abs. 4" to the citation. |
| `ANNEX_III.SAFEGUARDING` | Within the safeguarding provisions, "insolvency" occurs only in PSD2 Art. 10(1)(a) ("in particular in the event of insolvency"). EMD2 Art. 7(1) refers to Art. 9(1) and (2) of Directive 2007/64/EC, which PSD2 Art. 114 and its correlation table turn into a reference to PSD2 Art. 10(1) and (2). The citation stops at EMD2 Art. 7. Inside MiCAR, Annex III Part D No. 3 ("including in insolvency", template D.3) is the closer basis. | If the rule stays (see "Proposed terms"), cite Annex III Part D No. 3 for "insolvency", or add "Art. 10 Richtlinie (EU) 2015/2366", for which `citations.py` needs an `ACT_URLS` entry and an English name. |
| `COMMON.LEI_CHECK_DIGITS`, `COMMON.LEI_CONSISTENCY` | The citation names Part A of each Annex. In Annex I, Part A is the offeror; the issuer's LEI is Part B No. 5 and the platform operator's Part C No. 5, and both rules read all three party sections (`PARTY_SECTIONS` in `lei.py`). In Annexes II and III, Part A No. 5 is the issuer's. Each No. 5 allows "another identifier required pursuant to applicable national law" in place of the LEI (German "Unternehmenskennung"), and Art. 2(1)(b) and (c) of Implementing Regulation 2024/2984 require the LEI "where available". Both rules report a draft without an LEI as missing, which these provisions do not support where the draft gives another identifier. The rule pages still call the pinpoint unverified. | Cite "Anhang I Teil A, B und C jeweils Nr. 5, Anhang II Teil A Nr. 5, Anhang III Teil A Nr. 5 MiCAR" and replace the pending-review note on the two rule pages. The status for a draft that gives another identifier is an owner decision. |
| `COMMON.IXBRL_TAGGING` | Confirmed. Art. 2(1) of Implementing Regulation 2024/2984 requires the white paper in XHTML with the fields marked up in Inline XBRL 1.1. | None. |

### Rules confirmed without change

`COMMON.SUMMARY`, `COMMON.RISK_WARNING` (both variants, since #46 and #47), `COMMON.NOTIFICATION_DATE` and `COMMON.LANGUAGE` find every term in each type's paragraph in both languages. So do `ANNEX_I.C`, `ANNEX_II.D` (with #49) and the terms of `ANNEX_II.G.CUSTODY` and `ANNEX_II.I` (with #49). `ANNEX_II.G.DEPOSIT_FLOOR_REVIEW` has its own logic and no terms.

## Proposed terms

Each proposal takes its words from the Annex item and the template field the rule covers. Where no Annex item exists, the words come from the provisions the rule cites: "titel" from Art. 6(6), 19(5) and 51(5), and the safeguarding terms from Art. 54 MiCAR, PSD2 Art. 10(1)(a) and Annex III Part D No. 3. Stems cover the German inflections and compounds.

| Rule | English | German |
|---|---|---|
| `COMMON.MANAGEMENT_STATEMENT` | unchanged | "titel" in place of "entspricht" |
| `ANNEX_I.A` | name, address | name, anschrift |
| `ANNEX_I.B` | issuer, address | emittent, anschrift |
| `ANNEX_I.D` | project, milestones | projekt, etappen |
| `ANNEX_I.E` | court in place of jurisdictions | gericht in place of jurisdiktionen |
| `ANNEX_I.F` | characteristics, functionality | merkmale, funktion |
| `ANNEX_I.G` | rights, obligations, exercise, court | rechte, pflichten, ausübung, gericht |
| `ANNEX_I.H` | ledger in place of smart contract | ledger in place of smart contract |
| `ANNEX_I.I` | offer, project, technology, mitigation | angebot, projekt, technologie, minderung |
| `ANNEX_I.J`, `ANNEX_II.H`, `ANNEX_III.G` | environment in place of environmental | unchanged |
| `ANNEX_II.A` | issuer, address, management body | emittent, anschrift, leitungsorgan |
| `ANNEX_II.B` | characteristics, milestones | merkmale, etappen |
| `ANNEX_II.C` | offer, holders, court | angebot, inhaber, gericht |
| `ANNEX_II.E`, `ANNEX_III.E` | ledger, protocol, consensus, audit | ledger, protokoll, konsens, prüfung |
| `ANNEX_II.F` | reserve, issuer, offer, technology, mitigation | reserve, emittent, angebot, technologie, minderung |
| `ANNEX_II.G.COMPOSITION_DISCLOSURE` | reserve, composition | reserve, zusammensetzung |
| `ANNEX_II.G.VALUATION_AUDIT` | owner decision, see below | owner decision, see below |
| `ANNEX_III.A` | issuer, address, management body | emittent, anschrift, leitungsorgan |
| `ANNEX_III.B` | e-money token, characteristics | e-geld-token, merkmale |
| `ANNEX_III.C` | offer, court | angebot, gericht |
| `ANNEX_III.D` | rights, redemption, at par, complaints, holder | rechte, rücktausch, nennwert, beschwerden, inhaber |
| `ANNEX_III.F` | issuer, technology, mitigation | emittent, technologie, minderung |
| `ANNEX_III.SAFEGUARDING` | if the rule stays: safeguard, separate, credit institution, insolvency | if the rule stays: sicher, gesondert, kreditinstitut, insolvenz |

These choices need a decision from the owner:

1. `ANNEX_II.B` loses its check of the referenced assets and the stabilisation mechanism unless a rule that cites Annex II Part D No. 10, Part G No. 1 and Art. 36(8) takes them over.
2. `ANNEX_I.D` and `ANNEX_II.B` could use "plan" (template "Plans for the token") in place of "milestones" (the Annex wording); "plan" also matches "explanation".
3. The generic checks cannot ask for the legal form and the registered address only when no LEI is given. The proposals drop both terms; the alternative is logic of its own in the four party rules that looks for an LEI first.
4. `ANNEX_II.G.VALUATION_AUDIT` has no white paper item in the reserve section. Its valuation check can move to Annex II Part D No. 10(c) and drop "audit", or the rule can stay in the reserve section as a prompt for the lawyer with the corrected citation; as a prompt, it would stay a blocker although no white paper item requires its content.
5. `ANNEX_III.SAFEGUARDING` has no white paper item, and on its wording Art. 54 may not reach credit-institution issuers. It can stay as a prompt, lose its blocker severity, or be retired; retiring it removes a rule page and a SARIF rule ID that users may refer to. If it stays, the German "sicher" also matches "sichere Aktiva" in Art. 54(b), so it can pass a section that describes the investment of the funds and says nothing on how they are safeguarded.
6. `COMMON.LEI_CHECK_DIGITS` and `COMMON.LEI_CONSISTENCY`: whether a draft that gives another identifier, as No. 5 allows, gets review in place of missing.

The owner decided choices 3 to 6 on 27 October 2026. The legal form and registered address terms go (3). The valuation check moves to Annex II Part D No. 10(c) and drops "audit" (4). `ANNEX_III.SAFEGUARDING` stays as a prompt for review with the proposed terms and MAJOR severity (5). A party section without an LEI goes to review (6). Choices 1 and 2 remain open and belong to the class 3 fix.

## Effect on the examples

The results below come from linting every committed example and the starter template with the proposed terms in place of the current ones (`ANNEX_II.G.VALUATION_AUDIT` keeps its terms; `ANNEX_III.SAFEGUARDING` runs with the proposed ones). The rules and examples are those on `main` at `0e0939d`; #49's version of `art-stablecoin.json` gives the same result.

- `examples/art-stablecoin.json`: `ANNEX_II.B`, `ANNEX_II.C`, `ANNEX_II.E` and `ANNEX_II.F` go from Pass to Review, and `ANNEX_II.G.COMPOSITION_DISCLOSURE` from Review to Pass. The example's texts were written to the current terms; a fix PR rewrites them to the Annex items.
- `examples/other-crypto-asset.json`: `ANNEX_I.E`, `ANNEX_I.F`, `ANNEX_I.G` and `ANNEX_I.H` go from Pass to Review, for the same reason. `ANNEX_I.D` and `ANNEX_I.I` stay at Review with other missing terms.
- `examples/numbered-other-draft.xhtml` and `docs/playground/sample-numbered.xhtml`: `ANNEX_I.F` and `ANNEX_I.I` go from Pass to Review. Both follow the template but leave out the fields F.6, I.4 and I.6, which a complete white paper carries. `ANNEX_I.A`, `ANNEX_I.D`, `ANNEX_I.E` and `ANNEX_I.G` stay at Review with other missing terms.
- `examples/emt-token.json`: `ANNEX_III.A`, `ANNEX_III.B`, `ANNEX_III.C`, `ANNEX_III.D`, `ANNEX_III.F` and `ANNEX_III.SAFEGUARDING` stay at Review and report other missing terms.
- `examples/sample-draft.xhtml`: `ANNEX_III.A` and `ANNEX_III.B` stay at Review and report other missing terms. `ANNEX_III.C` to `ANNEX_III.G` and `ANNEX_III.SAFEGUARDING` stay at Missing.
- `examples/incomplete.json`: `ANNEX_II.A`, `ANNEX_II.B`, `ANNEX_II.E`, `ANNEX_II.F` and `ANNEX_II.G.COMPOSITION_DISCLOSURE` stay at Review and report other missing terms. This changes `reports/sample-incomplete-blockers.txt`, `docs/demo.txt` and `docs/demo.png`, which needs Chrome to regenerate. The output blocks in `README.md` and `docs/DETAILS.md` show only the first three common rules and stay as they are.
- `examples/sample-draft.docx`: `ANNEX_I.F` stays at Review with other missing terms.
- `templates/whitepaper-starter/whitepaper.json`: `ANNEX_II.B`, `ANNEX_II.C`, `ANNEX_II.E`, `ANNEX_II.F`, `ANNEX_II.G.COMPOSITION_DISCLOSURE` and `ANNEX_II.H` stay at Review with other missing terms.

Every example change, and every change to a citation or label, feeds the generated outputs listed in `AGENTS.md` section 6, so each fix PR regenerates them.

## German Official Journal text

Two points affect the choice of German terms. The adjective appears as "vermögenswertereferenziert" and as "vermögenswertreferenziert" (see class 2). Annex III Part B No. 2 of the German text reads "Beschreibung der Merkmale des vermögenswertreferenzierten Token", in the annex on e-money tokens, where the English text says "the characteristics of the e-money token".

## Proposed order of the fix pull requests

1. Classes 1 and 2, without the risk parts: `ANNEX_III.A`, the legal form and registered address terms of `ANNEX_I.A`, `ANNEX_I.B` and `ANNEX_II.A`, `ANNEX_III.C`, `ANNEX_I.F` (German), `ANNEX_II.B` ("basket" and the German spelling), `COMMON.MANAGEMENT_STATEMENT` (German), `ANNEX_III.B` (German), `ANNEX_III.D` and the three environmental rules.
2. Class 4: the citations and labels of `ANNEX_II.G.CUSTODY`, `ANNEX_II.I` and the LEI rules.
3. Class 3: the remaining terms, `ANNEX_II.G.COMPOSITION_DISCLOSURE` included, with the examples rewritten to the Annex items and the generated outputs refreshed.
4. `ANNEX_II.G.VALUATION_AUDIT` and `ANNEX_III.SAFEGUARDING`, once the owner has decided what each rule checks.

Fixes 1, 2 and 4 went up on 27 October 2026 as #51, #52 and #53. The `ANNEX_II.I` citation of fix 2 went into #49, which already rewrites that rule. Fix 3 waits for choices 1 and 2.

## Limits

The check is a substring test, so every proposed term is a heuristic too: it catches a section that leaves the item out and can miss a paraphrase. Where the review calls a term a defect, it relies on the provision's wording; whether a complete section in practice contains a proxy term is a judgement, marked as class 3.

Whether complete sections in practice carry the proxy terms, and how often the stems "plan", "sicher" and "titel" match unrelated words, can only be settled on a corpus of notified white papers, such as the ESMA register the study under `studies/` draws on. The terms of #49 are taken as at its head `4eee45c` and need a second look if it changes before merging. The reading of Art. 54 for credit-institution issuers rests on its wording alone; no EBA statement on the point was checked.
