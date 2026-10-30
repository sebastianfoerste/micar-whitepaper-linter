# MiCAR Whitepaper Compliance Review Log

- **Document Title**: Synthetic EuroStable ART White Paper
- **Regime/Type**: ART
- **Source File**: examples/art-stablecoin.json
- **SHA-256 Checksum**: `e8969fa1d2b061343085e85b22eec491f0b7adde670f9abfa937f2737fbb46ff`
- **Review Timestamp**: 2026-10-29 06:57:48

## Rule Compliance Checklist

| Rule ID | Citation | Description | Severity | Status | Reviewer Checked |
|---|---|---|---|---|---|
| `COMMON.SUMMARY` | Art. 6 Abs. 7, Art. 19 Abs. 6, Art. 51 Abs. 6 MiCAR | Plain-language summary | BLOCKER | **PASS** | [x] |
| `COMMON.RISK_WARNING` | Art. 6 Abs. 5, Art. 19 Abs. 4, Art. 51 Abs. 4 MiCAR | Mandatory risk warning statement | BLOCKER | **PASS** | [x] |
| `COMMON.MANAGEMENT_STATEMENT` | Art. 6 Abs. 6, Art. 19 Abs. 5, Art. 51 Abs. 5 MiCAR | Statement by the management body on completeness, fairness, and clarity | BLOCKER | **PASS** | [x] |
| `COMMON.NOTIFICATION_DATE` | Art. 6 Abs. 8, Art. 19 Abs. 7, Art. 51 Abs. 7 MiCAR | Date of notification to the competent authority | MAJOR | **PASS** | [x] |
| `COMMON.LANGUAGE` | Art. 6 Abs. 9, Art. 19 Abs. 8, Art. 51 Abs. 8 MiCAR | Language of the white paper (home Member State official language or customary in international finance) | MAJOR | **PASS** | [x] |
| `COMMON.IXBRL_TAGGING` | Art. 2 VO (EU) 2024/2984 | Inline XBRL (iXBRL) compliance and ESMA metadata tagging | BLOCKER | **MISSING** | [ ] |
| `COMMON.LEI_CHECK_DIGITS` | Anhang I Teil A Nr. 5, Teil B Nr. 5, Teil C Nr. 5, Anhang II Teil A Nr. 5, Anhang III Teil A Nr. 5 MiCAR | Legal Entity Identifier format and check digits (ISO 17442, ISO/IEC 7064 MOD 97-10) | MAJOR | **PASS** | [x] |
| `COMMON.LEI_CONSISTENCY` | Anhang I Teil A Nr. 5, Teil B Nr. 5, Teil C Nr. 5, Anhang II Teil A Nr. 5, Anhang III Teil A Nr. 5 MiCAR | Legal Entity Identifiers agree across the party sections and the rest of the draft | MAJOR | **PASS** | [x] |
| `ANNEX_II.A` | Anhang II Teil A MiCAR | Information about the issuer of the ART (identity, management body, governance arrangements) | BLOCKER | **PASS** | [x] |
| `ANNEX_II.B` | Anhang II Teil B MiCAR | Information about the asset-referenced token (characteristics, plans and milestones) | BLOCKER | **PASS** | [x] |
| `ANNEX_II.C` | Anhang II Teil C MiCAR | Information about the offer to the public of the ART or its admission to trading | BLOCKER | **PASS** | [x] |
| `ANNEX_II.D` | Anhang II Teil D i.V.m. Art. 39 MiCAR | Rights and obligations of holders (permanent right of redemption, complaints handling) | BLOCKER | **PASS** | [x] |
| `ANNEX_II.E` | Anhang II Teil E MiCAR | Information on the underlying technology (DLT, protocols, consensus mechanism, audit outcome) | BLOCKER | **PASS** | [x] |
| `ANNEX_II.F` | Anhang II Teil F MiCAR | Risk factors specific to ARTs (reserve of assets, issuer, offer or admission to trading, token, operationalisation, technology and any mitigation measures) | BLOCKER | **PASS** | [x] |
| `ANNEX_II.G.COMPOSITION_DISCLOSURE` | Anhang II Teil G Nr. 1 und 2 MiCAR | Reserve composition and value alignment mechanism (Annex II Part G Nos. 1 and 2 MiCAR) | BLOCKER | **PASS** | [x] |
| `ANNEX_II.G.DEPOSIT_FLOOR_REVIEW` | Anhang II Teil G i.V.m. Art. 35 Abs. 4, Art. 36 Abs. 4 Buchst. d, Art. 45 Abs. 3 und Art. 45 Abs. 7 Buchst. b MiCAR | Candidate deposit floor for the reserve (30 % under Art. 36(4)(d); 60 % under Art. 45(7)(b) for significant ARTs, or for non-significant ARTs via Arts. 35(4) and 45(3) MiCAR) - lawyer review required | BLOCKER | **REVIEW** | [ ] |
| `ANNEX_II.G.CUSTODY` | Anhang II Teil G i.V.m. Art. 36 Abs. 2, Art. 37 MiCAR | Custody of the reserve assets (Art. 37 MiCAR) and their legal segregation (Art. 36(2) MiCAR) | BLOCKER | **REVIEW** | [ ] |
| `ANNEX_II.G.VALUATION_AUDIT` | Anhang II Teil D Nr. 10 MiCAR | Referenced assets and valuation of the components of the claim (Annex II Part D No. 10 MiCAR) | BLOCKER | **PASS** | [x] |
| `ANNEX_II.H` | Art. 19 Abs. 1 UAbs. 1 Buchst. h MiCAR i.V.m. Art. 4 VO (EU) 2025/422; Anhang Tabelle 3 Teil H VO (EU) 2024/2984 | Principal adverse environmental and climate-related impact of the consensus mechanism | MAJOR | **PASS** | [x] |
| `ANNEX_II.I` | Anhang II Teil D Nr. 9, 14, 15 und 16, Teil G Nr. 3 i.V.m. Art. 39, Art. 46 Abs. 1 UAbs. 3 Buchst. c und Art. 46 Abs. 4 MiCAR | Redemption rights and procedure (timing, fees, suspension conditions) | BLOCKER | **PASS** | [x] |

## Summary of Findings

- **Passed Checks**: 17
- **Under Review**: 2
- **Missing Sections**: 1
- **BLOCKER Issues**: 3

> [!WARNING]
> **BLOCKER issues are currently open.** The draft is not package-ready for an external review or filing workflow until the gaps are cured and a lawyer has signed off.

## Lawyer Sign-off

This document is an automated disclosure checklist. The reviewing lawyer must sign below only after reviewing the automated findings, the source draft and any filing decision independently.

```
Reviewer Name:  __________________________________
Date of Review: __________________________________
Signature:      __________________________________
```