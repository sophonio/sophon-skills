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

**The folder rule.** A skill is flat, with two exceptions:

```
skills/<name>/
├─ lib/                     # optional, flat: first-party .py and .json files only
├─ vendor/<project>/**      # only when vendor.lock.json sits at the skill root
├─ vendor.lock.json         # sha256 of every file under vendor/ (see "Vendored skills")
└─ THIRD_PARTY_NOTICES.md   # required with vendor/: credits each vendored LICENSE's copyright line
```

Any other subfolder, any dotfile or dot-folder, and any symlink is a build error. Sophon copies
only the entrypoint into its sandbox workspace, so code in `lib/` or `vendor/` is reachable only on
the process backend, where the entrypoint can find the installed folder
(`skills/ffmpeg-video/main.py` shows how).

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

## Build checks beyond the contract

After the contract above, `build/Build-MarketplacePackages.ps1` runs `build/SkillLint.psm1` on
every skill. It checks what the package meets after the marketplace: the Sophon runtime, the model
providers, the zip inspector and the installer. Its data lives in `build/catalog/sandbox-python.psd1`
(mirrored from Sophon's `PythonImportResolver.cs`) and `build/catalog/marketplace-rules.psd1`, plus
the agent catalogue `build/agent-src/catalog/sophon-tools.psd1` and `scan-rules.psd1`. Every
message starts with a stable rule id:

| Rule | What fails | Why |
|------|-----------|-----|
| `SKILL-IMPORT` | with `requirements` empty (and no `requirements.txt`), a Python entrypoint line that starts with `import X` or `from X` (after leading whitespace; **docstrings and string literals count**) where `X` is not in the sandbox stdlib list | Sophon regex-scans the script and pip-installs every such `X` before each call. A docstring line like "from Profile Settings…" made it install `Profile`. Reword the line. |
| `SKILL-FUTURE` | a `__future__` import | Sophon prepends `import json, os` to the entrypoint, so the file fails with a SyntaxError |
| `SKILL-TOOLNAME`, `SKILL-TOOLDUP` | a tool name outside `^[a-z][a-z0-9_-]*(\.[a-z0-9_-]+)*$` or over 64 characters; a name declared twice | runtime and provider limits |
| `SKILL-COLLISION` | a name equal to a built-in tool (Allowed or Restricted) or another skill's tool. A Denied built-in name is a warning. | an exact collision makes Sophon skip the whole skill |
| `SKILL-WIRE` | two names that are equal after `.`→`_` | the provider wire form must be unique |
| `SKILL-SCHEMA` | `oneOf`, `anyOf`, `allOf`, `$ref` or `not`; more than one `type`; a non-string enum; an array without `items`; a `required` name that is not a property | providers reject or rewrite them (Gemini turns integer enums into strings, which the validator then refuses). Use `minimum`/`maximum` and list the values in the description. |
| `SKILL-TOOLPARAM` | a parameter named `tool` | the runtime overwrites that key with the tool name |
| `SKILL-TYPE`, `SKILL-RESERVED`, `SKILL-PERMISSIONS` | an explicit `type` other than `skill`; a System-tier reserved name (Official-tier is a warning); a `permissions` block the marketplace would refuse | marketplace rules |
| `SKILL-FOLDER`, `SKILL-DOTFILE`, `SKILL-SYMLINK` | anything outside the folder rule above | the package must hold real, reviewable files |
| `SKILL-LOCK`, `SKILL-NOTICE` | `vendor/` that does not match `vendor.lock.json` byte for byte (missing, extra or changed files, unsorted entries, script or native-binary extensions, non-UTF-8 or NUL bytes); a vendored `LICENSE` whose copyright line is missing from `THIRD_PARTY_NOTICES.md`. A vendored file over 256 KiB is a warning (the moderator preview truncates it). | vendored code is reviewed once, at the pinned tag |
| `SKILL-INJECTION` | a High or Medium injection literal in the skill or tool descriptions | the install preview card is itself a tool result that Sophon's injection guard scans |
| `SKILL-ZIP` | the built archive: more than 5000 entries, over 100 MiB per entry or 500 MiB in total, a compression ratio over 100, a package over 100 MiB, a backslash, `..` or rooted name, case-insensitive duplicates, a symlink entry, `manifest.json` not at the root, or entries that differ from the folder | the marketplace and installer limits |
| `SKILL-BUDGET` (warning) | a tool description over 1024 characters, more than 48 tools | agents reach the rest only through `tools.search` |

`-ValidateOnly` builds every archive in a temporary folder, so the zip checks run in CI too. The
lint has its own tests: `pwsh -NoProfile -File tests/build/Test-SkillLint.ps1` (fixtures in
`tests/build/fixtures/skills/<case>/`). Change `SkillLint.psm1` or a catalogue only together with a
fixture that shows the new rule.

## Vendored skills

A skill may ship a third-party project unchanged under `vendor/<project>/`, as `ffmpeg-video`
does with [kajisho5/ffmpeg-skill](https://github.com/kajisho5/ffmpeg-skill) (MIT). The rules:

- **Never edit vendored files.** They are byte-identical copies of an upstream tag, each pinned by
  sha256 in `vendor.lock.json`; `.gitattributes` marks the tree `-text` so git never rewrites line
  endings. No local patches: a fix goes upstream, then you re-sync to the tag that has it.
- **Never edit generated files.** For `ffmpeg-video` that is the manifest `tools[]`,
  `lib/tool-map.json`, the README tools table, the `main.py` GENERATED CONSTANTS block and
  `vendor.lock.json`. They come from `build/ffmpeg-video/generate.py`, which reads the vendored
  contract, `build/ffmpeg-video/manifest.base.json` (every top-level manifest field, `version`
  included) and `build/ffmpeg-video/policy.json` (per tool: group, risk, the "Use when" line, path
  roles and removed parameters).
- **Commands:**

  ```powershell
  python -B build/ffmpeg-video/generate.py            # regenerate after a policy or base change
  python -B build/ffmpeg-video/generate.py --check    # drift check (CI)
  python -B build/ffmpeg-video/generate.py --summary  # print the tool surface and path classification
  pwsh -NoProfile -File build/ffmpeg-video/Sync-FfmpegSkill.ps1 -Tag vX.Y.Z -ExpectedCommit <sha>   # re-vendor
  pwsh -NoProfile -File build/ffmpeg-video/Sync-FfmpegSkill.ps1 -Tag v3.9.2 -ExpectedCommit 3f8ba63cc8eb991c1730d57b0215e6127765399a -Check
  ```

  `-Source <local clone or URL>` reads the upstream repository from somewhere other than GitHub.
  `-Check` writes nothing.
- **When to re-sync, how to version it and what to review:** [`docs/VENDORING.md`](docs/VENDORING.md).

## Validate before you push

```bash
pwsh -File build/Build-MarketplacePackages.ps1 -ValidateOnly
python tests/skills/run_all.py
```

The first validates **all** skills (contract plus the build checks above) and exits non-zero on any
violation, printing every failing field per skill (it collects all errors, not just the first).
Build real artifacts with the same script without `-ValidateOnly`. The second runs every skill's
offline test file (see [`tests/README.md`](tests/README.md)).

## PR checklist

- [ ] Skill lives in `skills/<name>/` and the folder name equals `manifest.name`.
- [ ] `manifest.json`, entrypoint, `README.md`, and `LICENSE` are all present.
- [ ] `pwsh -File build/Build-MarketplacePackages.ps1 -ValidateOnly` passes locally.
- [ ] `python tests/skills/run_all.py` passes, and the skill has a `tests/skills/test_<skill>.py`.
- [ ] A change to `build/SkillLint.psm1` or `build/catalog/` comes with a fixture, and
      `pwsh -NoProfile -File tests/build/Test-SkillLint.ps1` passes.
- [ ] A vendored skill: nothing under `vendor/` or in a generated file was edited by hand, and
      `python -B build/ffmpeg-video/generate.py --check` passes.
- [ ] If updating an existing skill, `version` is bumped (strictly greater SemVer).
- [ ] Every tool declares an accurate `riskLevel`.
- [ ] `README.md` explains what the skill does, its tools, and any credentials it needs.

## Agents

The agents in `agents/` are Sophon agent packages, not skills, and follow their own rules. They
come in two families, registered in `build/agent-src/families.psd1`: **development** (nine agents,
`build/agent-src/family.psd1`) and **video** (`video-producer`,
`build/agent-src/families/video/family.psd1`).

- Each `agents/<id>/SOUL.md` is generated. Edit the sources of its family (the `souls/` and
  `fragments/soul/` folders beside its family file), then run
  `pwsh -File build/Compose-AgentSouls.ps1`. Never edit a SOUL.md by hand. Families share no
  fragments.
- An agent may use a skill's tools only through its family's `SkillPolicy`: the skill goes in
  `requires.skills`, its tools may be named and pinned, and they never go in `requires.tools`.
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
