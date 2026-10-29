# micar-whitepaper-template

A starter repository for drafting a MiCAR crypto-asset white paper with continuous linting. Click **Use this template**, fill in `whitepaper.json` section by section, and let CI tell you which mandatory disclosures are still open.

Every push to `main` and every pull request runs [micar-whitepaper-linter](https://github.com/sebastianfoerste/micar-whitepaper-linter) and reports each open finding with a pinpoint citation in the **Actions** tab. The default workflow runs in report mode (`strict: 'false'`), so open findings do not fail the check while you draft (a `whitepaper.json` the linter cannot load, such as invalid JSON or an unknown `"type"`, still does). Flip `strict` to `'true'` in `.github/workflows/micar-lint.yml` when you want the build to **fail on any open BLOCKER** before you notify the white paper or submit it for approval. The build then always fails: the iXBRL format BLOCKER can never pass for `whitepaper.json`, and for an asset-referenced token (the default `"type": "art"`) neither can the deposit-floor BLOCKER (see below). Read the log for the others.

Two BLOCKER checks never pass for this draft, by design. The iXBRL format check cannot be met by a JSON draft, because the notification format is XHTML with Inline XBRL tagging. For an asset-referenced token, the deposit floor of the reserve of assets (Art. 35(4), 36(4)(d), 45(3) and 45(7)(b) MiCAR) always stays open for a lawyer. A green pipeline never means the white paper is lawful, complete, or ready to notify or submit for approval. That judgment stays with your lawyer.

You can also lint drafts [live in the browser](https://sebastianfoerste.github.io/micar-whitepaper-linter/playground/). Nothing you paste leaves the page.

## How to use it

1. **Use this template** → create your repository (private is fine).
2. Edit `whitepaper.json`. Replace every `REPLACE:` placeholder; each section's placeholder states the disclosure the section must carry, and some cite a MiCAR provision (check each citation against your token type). The linter does not treat `REPLACE:` text as a placeholder. It reads an untouched section as written text, so it does not report that section Missing: most checks report Review on it, and in some releases a few even pass (in 1.2.1 the notification-date and language checks do). Search for any `REPLACE:` left over yourself.
3. Set `"type"` to `art`, `emt`, or `other` depending on your token. Section requirements follow the type (Anhang I-III MiCAR), but `whitepaper.json` holds the sections of an asset-referenced token (`art`), and its placeholders describe Anhang II. For `emt` or `other`, the linter warns about the keys that type does not read (`art`, `reserve_of_assets`, `redemption`). It reports as Missing each section that type's rules read and the template lacks: `emt` and `safeguarding` for `emt`; `offeror`, `trading_platform_operator`, `project` and `crypto_asset` for `other`. Add those sections and rewrite the placeholders for your type.
4. Push to `main` or open a pull request. Open the **Actions** tab: the `micar-lint` run lists every open finding with a pinpoint citation (article, paragraph, annex).
5. Work the findings down, then hand the draft to counsel. The linter checks structure and required disclosure elements, not legal sufficiency.

## What the linter checks

Deterministic rules (no LLM, same input, same findings): mandatory sections present and substantive (summary, risk warning, management-body statement, redemption, reserve of assets, …), listed terms for the risk warning and the management-body statement (the exact wording is not checked), and annex-specific items per token type. Findings are staged pass / review / missing.

## Scope and honesty

- Not legal advice. A draft can pass every check that can pass and still be misleading.
- The template covers the white paper content requirements, not the authorization or notification procedure itself.
- Template text is synthetic guidance; nothing in it describes a real issuer or token.

## License

MIT. The linter behind the CI check is separately MIT-licensed at [sebastianfoerste/micar-whitepaper-linter](https://github.com/sebastianfoerste/micar-whitepaper-linter).
