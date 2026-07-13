# Legora-inspired programme

The white-paper workspace emits a digest-bound collaboration sidecar, document change set and supervised workflow pack. Review cells support locks, assignment, comments and decisions with expected revisions. Source-digest changes mark the sidecar stale.

Tracked DOCX export copies the source package and writes accepted changes only. Rejected changes are excluded. Workflow runs retain the exact definition snapshot, inputs, source references, decisions and audit events. The CLI supports `--workflow-action validate`, `inspect` and `run`. Review-table timestamps use the reproducible-build `SOURCE_DATE_EPOCH` value, defaulting to Unix epoch zero, so identical inputs produce byte-identical workspace and bundle artifacts.

Run `make check`. External filing, notification and publication remain outside the CLI and require qualified lawyer review.
