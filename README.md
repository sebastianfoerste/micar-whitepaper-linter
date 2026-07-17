# micar-whitepaper-template

A starter repository for drafting a MiCAR crypto-asset white paper with continuous linting. Click **Use this template**, fill in `whitepaper.json` section by section, and let CI tell you which mandatory disclosures are still open.

Every push runs [micar-whitepaper-linter](https://github.com/sebastianfoerste/micar-whitepaper-linter) in strict mode: the build stays **red until no BLOCKER-severity finding is open**. A green build means the structural Annex checks pass — it does not mean the white paper is lawful, complete, or ready to notify. That judgment stays with your lawyer.

You can also lint drafts [live in the browser](https://sebastianfoerste.github.io/micar-whitepaper-linter/playground/) — nothing you paste leaves the page.

## How to use it

1. **Use this template** → create your repository (private is fine).
2. Edit `whitepaper.json`. Replace every `REPLACE:` placeholder; each one states the disclosure the section must carry and its MiCAR basis.
3. Set `"type"` to `art`, `emt`, or `other` depending on your token. Section requirements follow the type (Anhang I–III MiCAR).
4. Push. The `micar-lint` check lists every open finding with a pinpoint citation (article, paragraph, annex).
5. When CI is green, hand the draft to counsel. The linter checks structure and required disclosure elements, not legal sufficiency.

## What the linter checks

Deterministic rules — no LLM, same input, same findings: mandatory sections present and substantive (summary, risk warning, management-body statement, redemption, reserve of assets, …), the statutory formulas where MiCAR prescribes wording, and annex-specific items per token type. Findings are staged pass / review / missing.

## Scope and honesty

- Not legal advice. A draft can pass every check and still be misleading.
- The template covers the white paper content requirements, not the authorization or notification procedure itself.
- Template text is synthetic guidance; nothing in it describes a real issuer or token.

## License

MIT. The linter behind the CI check is separately MIT-licensed at [sebastianfoerste/micar-whitepaper-linter](https://github.com/sebastianfoerste/micar-whitepaper-linter).
