# System Architecture: MiCAR Whitepaper Linter

This document explains the internal modules, parsing pipeline, and rules-as-code structure of the MiCAR Whitepaper Linter.

## System Pipeline

The linter acts as a deterministic parser and check engine:

```mermaid
graph TD
    Input[Input Document: JSON, XHTML, DOCX] -->|Parse| DocObj[src/micar_linter/document.py Document Object]
    DocObj -->|Convert| WP[src/micar_linter/whitepaper.py Whitepaper Structure]
    WP -->|Execute| Linter[src/micar_linter/linter.py Linter Engine]

    subgraph Rule Engine
        Linter -->|Match Annex| Rules[src/micar_linter/rules/ base.py]
        Rules --> Common[common.py common rules]
        Rules --> Annex1[annex_i.py Other regime]
        Rules --> Annex2[annex_ii.py ART regime]
        Rules --> Annex3[annex_iii.py EMT regime]
    end

    Linter -->|Compile Findings| Report[src/micar_linter/report.py Report Compiler]
    Report --> Output[Output: Markdown Report or JSON payload]
```

---

## Technical Components

### 1. Document Parsing Layer
Normalizes inputs into structural sections:
- **`document.py`**: Base document model tracking raw text, headings, and tables.
- **`xhtml_parser.py`** & **`ixbrl.py`**: Parse Inline XBRL XHTML files, extracting tagged compliance attributes.

### 2. Regulatory Regimes (`rules/`)
All validation rules inherit from `rules.base.BaseRule`:
- **`common.py`**: Validates basic information required for all whitepapers (e.g. issuer identity details, default warning clauses).
- **`annex_i.py`**: Specific to Other Crypto-Assets.
- **`annex_ii.py`**: Specific to Asset-Referenced Tokens (verify reserve assets disclosures, redemption rights).
- **`annex_iii.py`**: Specific to E-Money Tokens (verify issuer licensing, redeemability details).

### 3. Report Compiler (`report.py`)
Collects and groups rule findings, prioritizing blocker flags (conditions that would cause regulatory rejection) over recommendations.