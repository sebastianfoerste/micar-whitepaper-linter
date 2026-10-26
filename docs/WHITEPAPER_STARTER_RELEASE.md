# Whitepaper starter release process

The linter repository is the canonical working repository for both the deterministic linter and the starter template. The public `micar-whitepaper-template` repository remains a GitHub template and release surface.

## Release gate

1. Run `make check` from the repository root.
2. Confirm the linter command line interface and GitHub Action inputs are unchanged.
3. Run `make template-export`.
4. Review `release/micar-whitepaper-template` against the public release branch.
5. Push only after human review.

The export script makes no network change: it deletes and recreates the local branch `release/micar-whitepaper-template` from `templates/whitepaper-starter/`. A fresh checkout has only the `origin` remote. To compare with or publish to the public template repository, add it as a remote yourself, and keep its push URL disabled until a human has approved the release.
