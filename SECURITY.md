# Security Policy

## Scope

This repository is a deterministic local linter for draft MiCAR crypto-asset white paper materials. Public demos should use synthetic fixture documents only.

## Sensitive Data Surfaces

The tool can process draft white paper text, issuer details, token economics, source files, audit logs, remediation outputs, coverage matrices, batch packs and manifest hashes.

## Required Controls

1. Do not commit client white papers, token launch plans, authority correspondence or privileged comments.
2. Use synthetic examples for portfolio demos.
3. Keep audit logs and remediation outputs from real documents outside source control.
4. Treat blocker status as review workflow readiness, not a legal conclusion.
5. Do not add regulator claims, authorization statements or filing dates to examples unless they are clearly synthetic fixtures.

## Reporting

Report suspected vulnerabilities privately through the maintainer's GitHub profile contact details. Include the affected path, impact and reproduction steps. Do not open public issues for suspected confidential draft text or credential leaks.
