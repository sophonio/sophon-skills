# QA Engineer

Independent risk-based verification with requirement traceability, reproducible defects, security/accessibility checks and explicit release risks.

## When to use

Pick this agent for independent software verification, requirement traceability, reproducible defect reports, and explicit release risks.

## Package and setup

- Version: **1.0.0**. Author: **Buildersoft LLC**. License: **MIT** (see `LICENSE`).
- Requires **Sophon 2.2.0 or newer** with the project's test tools and workspace access enabled.
- This is a persona package, not executable code. It installs no tools, integrations, or credentials.
- Delegation is disabled. Heartbeat, auto-approval, and autonomous planning are off on install.
- Models are inherited from the host. `SOUL.md` is the unmodified existing local agent persona.

Install through Sophon's agent package import, or `sophon agents install <package-file>`.
Choose a free ID if `qa-engineer` already exists. Packaged agents are third-party under
Sophon's trust rules: select or delegate explicitly; standing auto-approvals do not apply.

## Reviewed validation warning

Sophon 2.2.0 reports `possible_secret` for `SOUL.md:30`. That line is accessibility guidance
about automated scans, keyboard-only use, visible focus, zoom, target size, and screen readers;
it contains no credential. The owner chose to preserve the original wording and retain this
false-positive warning. Review it in any publish or moderation preview; do not automatically
acknowledge any other finding. Publishing from Sophon may require explicitly acknowledging
this specific finding. The warning does not prevent building the package.
