# Development agent packages

These are native **Sophon agent package format v1** projects, not skills, plugins, or
Claude Code agents. Each bundle contains one persona, no executable code.

## Approved release metadata

| Field | Value |
|-------|-------|
| Agents | `developer`, `lead-developer`, `qa-engineer`, `researcher`, `software-architect`, `ui-ux-designer` |
| Version | `1.0.0` |
| Author | `Buildersoft LLC` |
| License | `MIT`, full notice included in each bundle |
| Category | `development` |
| Minimum Sophon | `2.2.0` |

Display names and descriptions come from the existing local agents. When-to-use text and tags
are derived from their roles with the owner's approval. Each `SOUL.md` is preserved verbatim
from Sophon's native export. No live agents or their policies were modified.

## Build and verify

Prerequisites: PowerShell 7+ and `sophon` CLI 2.2.0+ on PATH. A Gateway is needed to export a
live agent, but not to validate or rebuild these checked-in projects. No credentials are needed
to build. The helper calls **`sophon dev validate`** and **`sophon dev build`**; it does not
implement a second package validator or writer.

```powershell
# Without -AllowWarnings, the helper fails closed on any CLI warning.
pwsh -File build/Build-AgentPackages.ps1 -ValidateOnly

# After reviewing the QA warning below:
pwsh -File build/Build-AgentPackages.ps1 -ValidateOnly -AllowWarnings
pwsh -File build/Build-AgentPackages.ps1 -AllowWarnings
pwsh -File tests/agents/Test-AgentPackages.ps1
```

The first command currently exits nonzero because of the reviewed QA warning; that is intentional.
`-AllowWarnings` prints all warnings and never bypasses validation errors. CLI 2.2.0 JSON combines
advisory warnings with publish-blocking issues, so this switch is **not** a publish-readiness verdict.
The tests pin the one reviewed warning and reject every other warning for this release. Review
all new warnings rather than reusing this exception blindly.

The helper writes the following upload-ready files and their hashes to **`dist/agents/`**:

```text
developer-1.0.0.sophon-agent
lead-developer-1.0.0.sophon-agent
qa-engineer-1.0.0.sophon-agent
researcher-1.0.0.sophon-agent
software-architect-1.0.0.sophon-agent
ui-ux-designer-1.0.0.sophon-agent
SHA256SUMS
```

Each zip holds `manifest.json` first, then `LICENSE`, `README.md`, and `SOUL.md` at its root,
with deterministic timestamps and no enclosing folder. Original raw exports are retained locally
in `dist/agent-exports/`; they predate the added license notices and detailed READMEs and are
**not the final upload artifacts**. One-off export tooling and isolated test outputs are also
retained under `dist/`; the whole directory is git-ignored. Preserve source in `agents/`.
Repeated builds replace the selected artifacts. A failed build leaves no success hash index;
older artifacts can remain on disk, so upload only after a successful complete build.

## Reviewed QA warning

Sophon 2.2.0 reports `possible_secret` at **`qa-engineer/SOUL.md:30`**. The complete line is:

> 6. Accessibility: automated scan (e.g. axe) at each key state PLUS manual pass: keyboard-only, visible focus, focus not obscured, 200% and 400% zoom, target size, contrast, screen reader where available. Automation alone is not a pass.

This is accessibility guidance, not a credential. The owner explicitly chose to preserve the
original and retain the warning. Do not remove the line or silently suppress the scanner.
Publishing from Sophon can require acknowledging the specific finding `SOUL.md:30`; that
acknowledgement has not been sent. Inspect any publication/moderation preview before proceeding.

## Install behavior and manual policy setup

- Import through Sophon's agent package UI or `sophon agents install <package-file>`.
- All installs start with heartbeat, auto-approval, and autonomous planning **off**. No provider,
  model pin, credentials, tool implementations, workspace path, or live `agent.json` is bundled.
- The five specialists have delegation disabled; Lead Developer has delegation enabled at
  maximum depth **2**. Models are inherited from the host.
- Package format v1 cannot carry enforced delegation allow-lists or agent dependencies.
  **After import, restrict Lead Developer's delegation to exactly** `developer`, `qa-engineer`,
  `researcher`, `software-architect`, and `ui-ux-designer`. Until the user configures that policy,
  the host policy is unrestricted; the preserved persona's instructions are not enforcement.
- Install companions with those exact IDs. An existing ID is not overwritten. If imports use
  different IDs, reconcile the lead's persona references and enforced allow-list before use.
- All packaged agents, even these first-party-authored ones, are third-party under Sophon's
  package trust rules: no automatic router selection, no standing auto-approvals, and no agent
  installs initiated by them. The lead cannot install companions itself.
- No skill dependency or exact tool pin has been invented. Configure the host's appropriate
  development, research, and design tools and permissions for the work you want to perform.

## Manual Marketplace upload

1. Build and run the tests above. Inspect the six final files and `SHA256SUMS`.
2. Sign in to the intended Marketplace publisher account and open the publish wizard.
3. Upload each final **`.sophon-agent`** file individually from `dist/agents/`; do not upload
   a zip of all six and do not use this repository's skill-only publishing script.
4. Review persona text, metadata, and the QA finding. Submit only after your own approval.
5. A submitted version starts in `pendingReview` and still needs moderation approval.

Nothing in this task uploads, installs, publishes, commits, or pushes. Live Marketplace name
ownership and prior versions were not checked. These IDs are not reserved by the documented v1
name tiers, but an existing owner or a previously published version can still prevent submission.
If needed, choose new slugs or bump versions deliberately; do not silently rename companion IDs.

## Contract references

The implementation was checked against the sibling Sophon repository:

- `docs/AGENT-PACKAGE-FORMAT.md` (author guide)
- `docs/AGENT-PACKAGE-CONTRACT.md` (frozen format, publishing issues, install policy, deterministic zips)
- `src/Sophon.Skills/Marketplace/Agents/AgentPackageExporter.cs` (native export)
- `src/Sophon.CLI/Commands/DevCommand.Agents.cs` (canonical project validation/build)

The Sophon app and Marketplace server remain separate repositories; no changes there are required
or made by this packaging task. Runtime installs, model behavior, and live publication remain untested.
