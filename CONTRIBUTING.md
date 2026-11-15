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

Stored verbatim and not column-projected by the Marketplace, but **`integration` and `credentials`
are a real contract enforced by the build script** — see below: `permissions` (`network[]` bare
hostnames, `filesystem[]` relative paths, `maxMemoryMb` ≤ 4096), `integration`, `credentials`,
`sandbox`, `requirements`.

### Integration & credentials contract

A skill that talks to an external service declares **both** an `integration` block (the connection
form Sophon renders) and a `credentials` entry (what the runtime looks up at call time). The
Marketplace does not parse either block, so these rules are enforced locally and in CI by
`build/Build-MarketplacePackages.ps1`.

| Rule | Detail |
|------|--------|
| both or neither | `integration` and a non-empty `credentials[]` must appear together |
| `credentials[].service` | must equal `integration.service` exactly — the runtime looks the stored credential up by this string |
| `credentials[].access` | **must be `"injected"`** for any skill that reads credentials from `params`. See below. |
| `integration.authType` | `custom`, `oauth2`, or `static_token`; `oauth2` also needs `authorizeUrl` + `tokenUrl` |
| `integration.category` | `cloud`, `developer`, `integration`, or `messaging` — this is the **connections-page grouping**, a different field from the top-level marketplace `category` above |
| `integration.fields[].type` | `text`, `secret`, `url`, `email`, `number`, or `select` (`select` needs `options[]`) |
| `integration.fields[].key` | a valid identifier, unique within the skill, never `tool` (the runtime overwrites that key) |
| field keys vs. code | every credential key the entrypoint reads at module scope must be declared in `integration.fields[]`; a declared field never read anywhere is warned about |

**`access` is not cosmetic.** Sophon merges the stored credential's fields **flat, verbatim, at the
top level** of the `SOPHON_PARAMS` JSON, so `main.py` reads `params.get("<fieldKey>")` using the
exact manifest key — **casing included**. Only `"injected"` delivers them. `"proxy"` names a broker
(the executor makes the outbound call so the sandbox never sees the secret) that **is not
implemented**; a skill declaring it receives no credentials at all and fails at call time claiming
it is not connected. Every skill in this repo declared `"proxy"` until 2026-08-17, which is exactly
why the rule above is now enforced.

**Where to read what.** Read credentials at **module scope** and tool arguments **inside handler
functions** — `skills/todoist/main.py` is the reference. The validator relies on this split to tell
credentials from tool arguments.

**Tool arguments win.** A tool argument with the same name as a non-secret credential field
overrides the stored value, which is the "pass it per call, or fall back to the connection default"
idiom (`clickhouse` `database`, `snowflake` `role`, `tmdb` `region`). A field with a tool-argument
twin should therefore be `required: false`. Secret-typed fields are never overridable.

**Field keys are permanent.** They key the stored credential, so renaming one silently orphans every
existing connection: the badge stays green and the tool breaks. New skills use camelCase; the
existing snake_case skills (`jellyfin`, `lastfm`, `plex`, `radarr`, `seerr`, `sonarr`, `steam`,
`tmdb`, `twitch`) stay snake_case. Never mix conventions within one skill.

**Shared services.** Several skills may share one `integration.service` (`microsoft-graph`,
`github`). Sophon registers one connection form per service and unions the declared fields, so a
field only some of the sharing skills need must be `required: false`.

**Versioning.** Patch-bump a skill's `version` if and only if a file inside its `skills/<name>/`
folder changed. Bumping an unchanged skill republishes an identical artifact.

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

## Agents

The development agents in `agents/` are Sophon agent packages, not skills, and follow their own
rules:

- Each `agents/<id>/SOUL.md` is generated. Edit the sources in `build/agent-src/`, then run
  `pwsh -File build/Compose-AgentSouls.ps1`. Never edit a SOUL.md by hand.
- Before a PR, run `pwsh -NoProfile -File build/Test-AgentSources.ps1` (CI runs it together with
  `Compose-AgentSouls.ps1 -Check`). With Sophon CLI 2.2.x installed, also run
  `pwsh -NoProfile -File tests/agents/Test-AgentPackages.ps1`.
- Agents are published by hand through the Marketplace wizard, never with
  `Publish-MarketplacePackages.ps1`.

The full rules (allowed files, real tool names, safe phrasing, versioning) are in
[`CLAUDE.md`](CLAUDE.md) and [`docs/AGENTS.md`](docs/AGENTS.md).

## Publishing

Merging does **not** publish. Publishing to the Marketplace is a deliberate manual step — see
[`docs/PUBLISHING.md`](docs/PUBLISHING.md).
