# Demo Asset Plan

## Screenshots Needed

1. Terminal run of `make check`.
2. CLI text output for `examples/incomplete.json`.
3. JSON output for one synthetic complete example.
4. Audit log or remediation output excerpt showing review-gated language.

## Synthetic Input

Use the existing fictional examples under `examples/`: Synthetic EuroStable, Synthetic PayEUR and Synthetic MeshCompute.

## Output To Show

Show cited findings, blocker counts, remediation output, coverage matrix and manifest digest. Show the not-legal-advice and lawyer-review language.

## Material To Exclude

Do not show real white papers, issuer names, token launch plans, authority correspondence, filing dates, wallet addresses, investor terms or privileged comments.

## 60 Second Demo

1. Run `make check`.
2. Run the linter on `examples/incomplete.json`.
3. Show blocker language and cited missing sections.
4. Generate remediation and manifest outputs into `/tmp`.
5. Show that strict mode fails when blockers remain.

## Buyer Or Recruiter Takeaway

The app demonstrates regulation-as-code: stable rule IDs, typed outputs, deterministic blockers, review artifacts and conservative legal framing.

## Hosting Readiness

GitHub and local CLI demo ready. Hosted demo is optional and should accept only synthetic examples unless a separate privacy review is completed.
