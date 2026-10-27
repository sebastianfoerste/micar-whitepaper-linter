# micar-whitepaper-template

A starter repository for drafting a MiCAR crypto-asset white paper with continuous linting. Click **Use this template**, fill in `whitepaper.json` section by section, and let CI tell you which mandatory disclosures are still open.

Every push to `main` and every pull request runs [micar-whitepaper-linter](https://github.com/sebastianfoerste/micar-whitepaper-linter) and reports each open finding with a pinpoint citation in the **Actions** tab. The default workflow runs in report mode (`strict: 'false'`) so the check stays green while you draft. Flip `strict` to `'true'` in `.github/workflows/micar-lint.yml` when you want the build to **fail on any open BLOCKER** before you notify. The build then always fails: the iXBRL format BLOCKER can never pass for `whitepaper.json`, and for an asset-referenced token (the default `"type": "art"`) neither can the deposit-floor BLOCKER (see below). Read the log for the others.

Two BLOCKER checks never pass for this draft, by design. The iXBRL format check cannot be met by a JSON draft, because the notification format is XHTML with Inline XBRL tagging. For an asset-referenced token, the deposit floor of the reserve of assets (Art. 35(4), 36(4)(d), 45(3) and 45(7)(b) MiCAR) always stays open for a lawyer. A green pipeline never means the white paper is lawful, complete, or ready to notify. That judgment stays with your lawyer.

You can also lint drafts [live in the browser](https://sebastianfoerste.github.io/micar-whitepaper-linter/playground/). Nothing you paste leaves the page.

## How to use it

1. **Use this template** → create your repository (private is fine).
2. Edit `whitepaper.json`. Replace every `REPLACE:` placeholder; each one states the disclosure the section must carry and its MiCAR basis.
3. Set `"type"` to `art`, `emt`, or `other` depending on your token. Section requirements follow the type (Anhang I-III MiCAR).
4. Push. Open the **Actions** tab: the `micar-lint` run lists every open finding with a pinpoint citation (article, paragraph, annex).
5. Work the findings down, then hand the draft to counsel. The linter checks structure and required disclosure elements, not legal sufficiency.

## What the linter checks

Deterministic rules (no LLM, same input, same findings). For each mandatory section (summary, risk warning, management-body statement, redemption, reserve of assets, …) and each annex-specific item for the token type, the linter checks that the section exists, meets a minimum length and contains the expected keywords. It does not compare your text with the wording MiCAR prescribes (the one exception, once a linter release includes it, is the English first-page statement for Title II and e-money token white papers under Art. 6 Abs. 3 and Art. 51 Abs. 3 MiCAR), and it does not judge whether a disclosure is accurate or adequate. Findings are staged pass / review / missing.

The rules, their citations and their tests live in [micar-whitepaper-linter](https://github.com/sebastianfoerste/micar-whitepaper-linter), which is the source of truth; this README only summarises them.

The workflow pins the linter's `@v1` tag, which moves to each linter release. `@v1` runs v1.2.1, which does not yet correct the asset-referenced token redemption checks (Art. 39 Abs. 2 MiCAR) and the reserve citations (Art. 36 MiCAR) or check the first-page statement; they reach `@v1` with the release that includes them.

## Scope and honesty

- Not legal advice. A draft can pass every check that can pass and still be misleading.
- The template covers the white paper content requirements, not the authorization or notification procedure itself.
- Template text is synthetic guidance; nothing in it describes a real issuer or token.

## License

MIT. The linter behind the CI check is separately MIT-licensed at [sebastianfoerste/micar-whitepaper-linter](https://github.com/sebastianfoerste/micar-whitepaper-linter).
