# Review-workspace programme

The white-paper workspace emits a digest-bound collaboration sidecar, document change set and supervised workflow pack. Review cells support locks, assignment, comments and decisions with expected revisions. Source-digest changes mark the sidecar stale.

Tracked DOCX export copies the source package and writes accepted changes only. Rejected changes are excluded. Workflow runs retain the exact definition snapshot, inputs, source references, decisions and audit events. The CLI supports `--workflow-action validate`, `inspect` and `run`. The review tables written by `--review-table-output`, by `--compare-review-table-output` and inside the workspace, and the dates of tracked changes in the DOCX export, use the reproducible-build `SOURCE_DATE_EPOCH` value, defaulting to Unix epoch zero. The workspace vault's own `generated_at` and every file of the review bundle (`--review-bundle-dir`) use the current time, so those outputs differ from run to run.

Run `make check`. External filing, notification and publication remain outside the CLI and require qualified lawyer review.
