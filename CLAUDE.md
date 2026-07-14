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

## Commands

- Validate: `pwsh -File build/Build-MarketplacePackages.ps1 -ValidateOnly`
- Build:    `pwsh -File build/Build-MarketplacePackages.ps1`  → `dist/<name>-<version>.sophon-skill`
- Publish:  `pwsh -File build/Publish-MarketplacePackages.ps1`  (needs `SOPHON_MARKETPLACE_API_KEY`)

## Package shape

A `.sophon-skill` is a zip of the skill folder's CONTENTS with `manifest.json` at the ROOT (no
wrapping folder); excludes `__pycache__/`, `dist/`, `.DS_Store`, `Thumbs.db`, `*.pyc`. Upload is
`POST /api/v1/publish` (multipart field `package`, Bearer `smk_` key); every version starts
`pendingReview` and needs approval. See [`docs/PUBLISHING.md`](docs/PUBLISHING.md).

## Conventions

- Keep `build/Build-MarketplacePackages.ps1`'s validation rules in sync with the marketplace's
  `Publishing/` validators (`sophon-marketplace` repo) — they are intentionally duplicated.
- `plugins/` is scaffolded for future Sophon plugins (`.sophon-plugin`, a separate compiled path);
  the build script here packages skills only.
- Publishing never happens on merge — it is always a deliberate manual/dispatch action.
