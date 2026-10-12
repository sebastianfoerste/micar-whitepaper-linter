# Whitepaper starter release process

The linter repository is the canonical working repository for both the deterministic linter and the starter template. The public `micar-whitepaper-template` repository remains a GitHub template and release surface.

## Release gate

1. Run `make check` from the repository root.
2. Confirm the linter command line interface and GitHub Action inputs are unchanged.
3. Run `make template-export`.
4. Review `release/micar-whitepaper-template` against the public release branch.
5. Push only after human review.

The export script performs no network mutation. The `template-release` remote has a disabled push URL in this checkout.
