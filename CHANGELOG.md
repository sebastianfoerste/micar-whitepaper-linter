# Changelog

## Unreleased

### Fixed

- The audit log (`--audit-log`) and the review bundle's `compliance-checklist.md` no longer say "All automated checks passed" while a MAJOR or MINOR finding is open. When findings are open but none is a BLOCKER, the log shows a warning that gives the number of open findings by severity, for example "1 finding is still open (1 MAJOR) and no BLOCKER finding is open", and says that the draft still needs them resolved or reviewed and that substantive lawyer review is still required. The "All automated checks passed" note now appears only when every finding passes, the condition under which the text report says all required disclosures are present. The BLOCKER warning is unchanged. The playground wheel is rebuilt from the fixed source.
