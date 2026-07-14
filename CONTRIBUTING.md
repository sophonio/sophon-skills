# Contributing to Sophon Skills

Thanks for helping build the Sophon skill catalog. This guide covers the skill format, the manifest
contract, and the checklist your PR must pass.

## Anatomy of a skill

Each skill is a flat folder under `skills/<name>/`:

```
skills/<name>/
├─ manifest.json     # required — metadata + tool declarations (contract below)
├─ main.py           # required — the entrypoint named by manifest.entrypoint
├─ README.md         # required — becomes the Marketplace listing page (≤ 64 KiB)
└─ LICENSE           # required — MIT © Buildersoft LLC (or the skill's own license)
```

The folder name **must** equal the manifest `name`. Start from a scaffold:
`templates/skill-python/` or `templates/skill-csharp/` — copy it to `skills/<name>/` and drop the
`.template` suffixes.

## Manifest contract

Every `manifest.json` must satisfy these rules before it can be packaged or accepted by the
Marketplace. The build script (`build/Build-MarketplacePackages.ps1`) enforces them locally and in
CI; the Marketplace re-validates on upload.

| Field | Rule |
|-------|------|
| `name` | required; matches `^[a-z0-9][a-z0-9-]{1,63}$`; **must equal the folder name**; globally unique on the Marketplace and immutable once owned |
| `version` | required; SemVer (`1.0.0`, `1.2.0-beta.1`); **strictly greater** than every version ever published for this skill (rejected versions still count — numbers are never reused) |
| `author` | required, non-empty (`"Buildersoft LLC"` for first-party) |
| `license` | required, non-empty (SPDX id, e.g. `MIT`) |
| `description` | required; ≤ 2000 characters |
| `runtime` | one of `python`, `csharp`, `sandbox` |
| `entrypoint` | required; must name a file that exists in the folder |
| `tools[]` | non-empty; each tool needs `name`, `description`, and `riskLevel` ∈ `none`/`low`/`medium`/`high`/`critical` |
| `tags` | optional; ≤ 10 tags, each ≤ 32 chars (missing → no search tags) |
| `category` | optional; one of `utility`, `productivity`, `communication`, `data`, `development`, `integration`, `ai`, `automation`, `other` (missing/unknown → `other`) |
| `README.md` | must exist at the skill root, ≤ 64 KiB |
| `LICENSE` | must exist at the skill root |

Optional, free-form (stored verbatim, not column-projected by the Marketplace): `permissions`
(`network[]` bare hostnames, `filesystem[]` relative paths, `maxMemoryMb` ≤ 4096), `integration`,
`credentials`, `sandbox`, `requirements`.

### Conventions for first-party skills

- `"author": "Buildersoft LLC"`, `"license": "MIT"`, with an MIT © Buildersoft LLC `LICENSE` file.
- READMEs wrapping a third-party brand (Jira/Confluence → Atlassian, google-gmail → Google) include
  a **Trademarks** note, and a **Third-Party Software** note when bundling/depending on external
  libraries.

## Validate before you push

```bash
pwsh -File build/Build-MarketplacePackages.ps1 -ValidateOnly
```

This validates **all** skills and exits non-zero on any violation, printing every failing field per
skill (it collects all errors, not just the first). Build real artifacts with the same script
without `-ValidateOnly`.

## PR checklist

- [ ] Skill lives in `skills/<name>/` and the folder name equals `manifest.name`.
- [ ] `manifest.json`, entrypoint, `README.md`, and `LICENSE` are all present.
- [ ] `pwsh -File build/Build-MarketplacePackages.ps1 -ValidateOnly` passes locally.
- [ ] If updating an existing skill, `version` is bumped (strictly greater SemVer).
- [ ] Every tool declares an accurate `riskLevel`.
- [ ] `README.md` explains what the skill does, its tools, and any credentials it needs.

## Publishing

Merging does **not** publish. Publishing to the Marketplace is a deliberate manual step — see
[`docs/PUBLISHING.md`](docs/PUBLISHING.md).
