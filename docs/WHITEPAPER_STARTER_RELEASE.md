# Whitepaper starter release process

The linter repository is the canonical working repository for both the deterministic linter and the starter template. The public `micar-whitepaper-template` repository remains a GitHub template and release surface.

## Release gate

1. Run `make check` from the repository root.
2. Confirm the linter command line interface and GitHub Action inputs are unchanged. Then run the untouched `whitepaper.json` with the release `v1` points to (for example from `git archive v1`) and with HEAD. Confirm that the template README, the workflow comments and the placeholders describe what each reports, because template users run `@v1`, not HEAD.
3. Run `make template-export`.
4. Review `release/micar-whitepaper-template` against the public repository's `main`.
5. After human review, push it to a new branch of the public repository and open a pull request into `main`, and merge it with a merge commit. The public `main` holds the merge commits of earlier releases, which the export does not, so the export never fast-forwards onto it.

The export script makes no network change. It needs a clean working tree: with any change `git status --porcelain` lists (staged, modified or untracked; ignored files do not count), it exits 1 and leaves the branch as it was. Otherwise it deletes and recreates the local branch `release/micar-whitepaper-template` with `git subtree split`, from the committed history of `templates/whitepaper-starter/` at the current HEAD. A fresh checkout has only the `origin` remote. To compare with or publish to the public template repository, add it as a remote yourself. `git remote add` gives it a working push URL, so disable that (for example `git remote set-url --push <name> no_push`) until a human has approved the release.

Change the template only under `templates/whitepaper-starter/` in this repository, because the export carries that folder's history alone: a change made directly in the public repository is not in the next export, and its release pull request keeps it only where the export does not touch the same lines. The public repository's pull request #2 (read-only permissions, a commit-pinned checkout, Dependabot) was copied here for that reason.
