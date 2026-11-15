# Lead Developer

Scopes software work, delegates dependency-aware briefs to specialist agents, integrates and reviews results, and delivers final evidence.

## When to use

Pick this agent to scope software work, coordinate development specialists, integrate changes, and deliver reviewed verification evidence.

## Package and setup

- Version: **1.0.0**. Author: **Buildersoft LLC**. License: **MIT** (see `LICENSE`).
- Requires **Sophon 2.2.0 or newer** with the appropriate workspace and development tools enabled.
- This is a persona package, not executable code. It installs no tools, integrations, or credentials.
- Delegation is enabled with maximum depth **2**; models are inherited from the host.
- Heartbeat, auto-approval, and autonomous planning are off on install.
- Exported from the existing local Sophon agent. `SOUL.md` is preserved without edits.

### Required companion agents

Install or provide these agents under their exact IDs before asking the lead to coordinate work:

- `developer`
- `qa-engineer`
- `researcher`
- `software-architect`
- `ui-ux-designer`

**Manual policy setup required:** package format v1 cannot include an enforced delegation
allow-list or agent dependencies. After import, enable **Restrict to allow-list** in the lead's
delegation settings and allow only the five IDs above. The persona states the same boundary,
but prompt instructions are not an enforced runtime policy. Until that manual step, the host
policy is unrestricted. This repository does not change any live agent settings.

Install through Sophon's agent package import, or `sophon agents install <package-file>`.
An existing `lead-developer` ID is not overwritten. If a companion gets a different ID on
import, reconcile the lead's persona references and its enforced allow-list before using it.
Packaged agents are third-party under Sophon's trust rules: explicit selection or delegation
is required, standing auto-approvals do not apply, and the lead cannot install companions itself.
