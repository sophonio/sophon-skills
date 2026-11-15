# Developer

Implements one scoped coding task or bug fix with tests, root-cause debugging and build/lint/test evidence.

## When to use

Pick this agent for a scoped coding task or bug fix requiring tests, root-cause debugging, and build evidence.

## Package and setup

- Version: **1.0.0**. Author: **Buildersoft LLC**. License: **MIT** (see `LICENSE`).
- Requires **Sophon 2.2.0 or newer** with the appropriate workspace and coding tools enabled.
- This is a persona package, not a coding tool or executable. It does not install tools,
  credentials, or third-party integrations. Models are inherited from the host configuration.
- Delegation is disabled. Heartbeat, auto-approval, and autonomous planning are off on install.
- Exported from the existing local Sophon agent. `SOUL.md` is preserved without edits.

Install through Sophon's agent package import, or `sophon agents install <package-file>`.
Choose a free agent ID if `developer` already exists; importing is not a way to overwrite it.
Packaged agents remain third-party under Sophon's trust rules, including first-party-authored
packages: select or delegate to them explicitly; standing auto-approvals do not apply.
