# Software Architect

Repo-grounded, read-only design with quantified quality attributes, trade-offs, security boundaries, API contracts, migration plans and ADR drafts.

## When to use

Pick this agent for repository-grounded software design, trade-offs, security boundaries, API contracts, migration plans, and ADR drafts.

## Package and setup

- Version: **1.0.0**. Author: **Buildersoft LLC**. License: **MIT** (see `LICENSE`).
- Requires **Sophon 2.2.0 or newer** with repository reading and research tools enabled as needed.
- This is a persona package, not executable code. It installs no tools, integrations, or credentials.
- Read-only by default through persona instructions, not a sandbox permission restriction.
- Delegation is disabled. Heartbeat, auto-approval, and autonomous planning are off on install.
- Models are inherited from the host. `SOUL.md` is the unmodified existing local agent persona.

Install through Sophon's agent package import, or `sophon agents install <package-file>`.
Choose a free ID if `software-architect` already exists. Packaged agents are third-party under
Sophon's trust rules: select or delegate explicitly; standing auto-approvals do not apply.
