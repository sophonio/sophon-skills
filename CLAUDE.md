# CLAUDE.md — sophon-skills

Open-source Skills (and, later, Plugins) that Buildersoft publishes to the **Sophon Marketplace**
(`marketplace.sophon.buildersoft.io`, served by the separate `sophon-marketplace` repo). The Sophon
app itself lives in the separate `sophon` repo.

## What a skill is

A skill is a flat folder `skills/<name>/` containing `manifest.json` + an entrypoint (e.g.
`main.py`) + `README.md` + `LICENSE`. This is **Sophon's** skill format (`manifest.json`), NOT
Claude Code / Anthropic `SKILL.md`. The folder name must equal the manifest `name`.

## The contract (enforced by the build script AND the marketplace)

`name` (== folder name, `^[a-z0-9][a-z0-9-]{1,63}$`), `version` (SemVer, strictly-increasing on
republish), `author`, `license`, `description` (≤2000), `runtime` (`python`|`csharp`|`sandbox`),
`entrypoint` (must exist), `tools[]` (each `name`/`description`/`riskLevel` ∈
none|low|medium|high|critical), optional `tags[]` (≤10, ≤32) and `category` (utility|productivity|
communication|data|development|integration|ai|automation|other). `README.md` (≤64 KiB) and `LICENSE`
must exist at the skill root. Full table: [`CONTRIBUTING.md`](CONTRIBUTING.md).

## Integration skills (`integration` + `credentials`)

Enforced by the build script only — the marketplace stores both blocks verbatim without parsing
them. Declare both or neither; `credentials[].service` must equal `integration.service`;
**`access` must be `"injected"`** (`"proxy"` names a broker that does not exist, so the skill
receives no credentials and reports itself not connected at call time — this silently disabled
every skill in the catalogue until 2026-08-17). Credential fields land **flat in `params` under
their exact manifest key, casing included**; read them at module scope and tool arguments inside
handlers (`skills/todoist/main.py` is the reference). Field keys are permanent — renaming one
orphans every stored credential. Details: [`CONTRIBUTING.md`](CONTRIBUTING.md).

## Commands

- Validate: `pwsh -File build/Build-MarketplacePackages.ps1 -ValidateOnly`
- Build:    `pwsh -File build/Build-MarketplacePackages.ps1`  → `dist/<name>-<version>.sophon-skill`
- Publish:  `pwsh -File build/Publish-MarketplacePackages.ps1`  (needs `SOPHON_MARKETPLACE_API_KEY`)

## Package shape

A `.sophon-skill` is a zip of the skill folder's CONTENTS with `manifest.json` at the ROOT (no
wrapping folder); excludes `__pycache__/`, `dist/`, `.DS_Store`, `Thumbs.db`, `*.pyc`. Upload is
`POST /api/v1/publish` (multipart field `package`, Bearer `smk_` key); every version starts
`pendingReview` and needs approval. See [`docs/PUBLISHING.md`](docs/PUBLISHING.md).

## Agent packages (`agents/`)

Sixteen `.sophon-agent` packages, the Buildersoft development family (roster, ids and fragment order in
`build/agent-src/family.psd1`). Full guide: [`docs/AGENTS.md`](docs/AGENTS.md); design:
`docs/plans/2026-11-15-agents-v2-design.md`.

- **Files.** Only the 7 package files may live in `agents/<id>/` (`manifest.json`, `SOUL.md`,
  `VOICE.md`, `HEARTBEAT.md`, `TOOLS.md`, `README.md`, `LICENSE`); anything else is `not_packaged`
  and fails the build. This family uses exactly 5 (no VOICE, no HEARTBEAT), and `LICENSE` is a
  byte-identical copy of the agent's `LicenseFile`, else of the root `LICENSE`. UTF-8 without BOM,
  LF, no tabs, no trailing whitespace, one final newline.
- **Licenses.** An agent entry in `family.psd1` may set `License` and `LicenseFile` together
  (`License = 'Apache-2.0'`, `LicenseFile = 'build/agent-src/licenses/Apache-2.0.txt'`); without
  them it is MIT with the root `LICENSE`. The nine original agents stay MIT; the seven added in 2.1
  are Apache-2.0 because they adapt anthropics/skills text (Credits key `anthropicSkills`). The
  manifest `license` and the README sentence ("Licensed under the MIT License; see LICENSE." or
  "Licensed under the Apache License, Version 2.0; see LICENSE.") must match it.
- **Never hand-edit `agents/*/SOUL.md`.** It is generated: edit `build/agent-src/` (`souls/<id>.md`
  for role text, `fragments/soul/<NN-id>.md` for shared protocol) and run
  `pwsh -File build/Compose-AgentSouls.ps1`. CI fails on drift. Manifests, TOOLS.md and READMEs
  are hand-written.
- **Commands.**
  - Compose: `pwsh -NoProfile -File build/Compose-AgentSouls.ps1` (`-Check` for drift, `-Explain`
    for line provenance and which agents include each fragment)
  - Source checks, no CLI: `pwsh -NoProfile -File build/Test-AgentSources.ps1`
  - Validate: `pwsh -NoProfile -File build/Build-AgentPackages.ps1 -ValidateOnly` (Sophon CLI
    2.2.x; any CLI warning fails)
  - Build: `pwsh -NoProfile -File build/Build-AgentPackages.ps1` → `dist/agents/<id>-<version>.sophon-agent` + `SHA256SUMS`
  - Tests: `pwsh -NoProfile -File tests/agents/Test-AgentPackages.ps1` (`-SourceOnly` without the CLI)
- **Tool names must be real.** Write them dotted and exact (`fs.read`, `code.git`, `agent.delegate`);
  the lint checks every name against `build/agent-src/catalog/sophon-tools.psd1`. Denied names
  (`web.fetch`, git push or PR tools) and restricted ones (`sessions.yield`, `code.test`, workflow
  tools) may appear only in a negated correction ("There is no web.fetch; use web.scrape"). Never
  provider wire forms (`fs_read`). In SOUL and TOOLS text: no Claude Code tool names in backticks
  and no "Claude Code" (READMEs may mention it).
- **Safe phrasing** (the preflight replays the marketplace and runtime scanners from
  `catalog/scan-rules.psd1`; a hit fails the build):

  | Do not write | Write instead |
  |---|---|
  | "auto-approve" | "allowed Medium-risk calls for the session" |
  | a word ending in pass/token/pwd (or pin, sig, pat, otp) before `:` or `=`, e.g. "first pass:" | "Red first —" |
  | skip, avoid, disable or ignore within 30 characters before approval, permission, consent or confirmation | name the step positively |
  | a secret word (token, password, secret, credential, api key, cookie) within 60 characters of send, post, upload, forward, email or transmit on one line | split the sentence |
  | injection-style phrases (instruction overrides, prompt reveals, personas), `<!--`, role tags, long base64 runs, zero-width or bidi characters, `curl … \| sh` | plain instructions |
  | hosts other than sophon.buildersoft.io, marketplace.sophon.buildersoft.io, github.com | — |
  | headings Sophon appends itself (`## Interaction`, `## Tool Access`, `## Workspace`, `## Memory Knowledge Graph`, `### Available tool index`) | another heading |

- **Attribution strings live only in `family.psd1`** (`Values.CommitTrailer`, `Values.PrFooter`,
  `Values.PlanDir`). Templates and fragments write `{{= CommitTrailer}}`, `{{= PrFooter}}` and
  `{{= PlanDir}}`, never the literal text.
- **Versions.** Major 2 in lockstep across the family; minor and patch per agent. Any content change
  bumps every affected agent (strictly greater SemVer); a shared-fragment change bumps every agent
  that includes it.
- **Publishing is manual:** each `.sophon-agent` is uploaded on its own through the Marketplace
  wizard. `build/Publish-MarketplacePackages.ps1` stays skills-only; never point it at agents.

## Conventions

- Keep `build/Build-MarketplacePackages.ps1`'s validation rules in sync with the marketplace's
  `Publishing/` validators (`sophon-marketplace` repo) — they are intentionally duplicated.
- `plugins/` is scaffolded for future Sophon plugins (`.sophon-plugin`, a separate compiled path);
  the build script here packages skills only.
- Publishing never happens on merge — it is always a deliberate manual/dispatch action.
