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

## Supported Versions

| Line | Supported |
| --- | --- |
| 1.2.x (latest release on PyPI, the `v1` tag of the GitHub Action) | Yes: fixes go into the next release |
| `main` (unreleased) | Yes: fixes land here first |
| 1.1.x and earlier (package 0.2.x and earlier) | No: upgrade to the latest release |

The playground on GitHub Pages runs the wheel built from `main`.

## Reporting

Report suspected vulnerabilities privately; do not open a public issue for them, nor for suspected confidential draft text or credential leaks.

1. If private vulnerability reporting is enabled for this repository, use [Report a vulnerability](https://github.com/sebastianfoerste/micar-whitepaper-linter/security/advisories/new) (enabling it is a repository setting of the owner).
2. Otherwise, use the contact details on the maintainer's [GitHub profile](https://github.com/sebastianfoerste).

Include the affected path, the impact and reproduction steps, with synthetic documents only. You should hear back within 14 days.
