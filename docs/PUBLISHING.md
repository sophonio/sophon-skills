# Publishing Guide

How to build, validate, and publish the skills in this repo to the
[Sophon Marketplace](https://marketplace.sophon.buildersoft.io), under the **Buildersoft LLC**
publisher account. Artifacts are built locally and uploaded manually — there is no CI job that
publishes on merge.

## TL;DR — release in five commands

```powershell
# from the repo root, PowerShell 7+
python tests/skills/run_all.py                                   # offline skill tests (all must PASS)
pwsh -File build/Build-MarketplacePackages.ps1 -ValidateOnly     # contract check (exit 0 = clean)
pwsh -File build/Build-MarketplacePackages.ps1                   # writes dist/<name>-<version>.sophon-skill
$env:SOPHON_MARKETPLACE_API_KEY = 'smk_...'                       # your publisher key (see §2)
pwsh -File build/Publish-MarketplacePackages.ps1 -DryRun         # preview, then re-run without -DryRun
```

Bash/zsh equivalent for the key: `export SOPHON_MARKETPLACE_API_KEY='smk_...'`.

## 0. Prerequisites & configuration

**Tools**

| Need | Why | Check |
|------|-----|-------|
| PowerShell **7+** (`pwsh`) | both build scripts `#Requires -Version 7.0`; Windows PowerShell 5.1 will not run them | `pwsh --version` |
| Python **3.10+** (runtime target is 3.13) | runs the offline skill tests in `tests/skills/` and the `ffmpeg-video` generator (stdlib only, no `pip install`) | `python --version` |
| git | `Sync-FfmpegSkill.ps1` reads the upstream repository (only when re-vendoring `ffmpeg-video`) | `git --version` |
| FFmpeg **6.1+** *(optional)* | the real-media tests of `ffmpeg-video` (`tests/skills/ffmpeg_video_media.py`); without it they print SKIP | `ffmpeg -version` |
| Docker *(optional)* | container parity smoke on `python:3.13-alpine` (`tests/skills/run_all_container.py`) | `docker --version` |

**Configuration** — nothing is needed to build or validate; publishing needs:

| Setting | Where | Required | Default / notes |
|---------|-------|----------|-----------------|
| `SOPHON_MARKETPLACE_API_KEY` | env var, or `-ApiKey` | **yes** (not for `-DryRun`) | `smk_…` publisher key for the Buildersoft LLC account — see §2. Never commit it. |
| `SOPHON_MARKETPLACE_URL` | env var, or `-MarketplaceUrl` | no | `https://marketplace.sophon.buildersoft.io`; set e.g. `http://localhost:5100` for a local marketplace. The script appends `/api/v1/publish`. |

For the GitHub Actions publish workflow, the same two values are configured on the repo — see
[§5](#5-publishing-from-github-actions).

**Script options at a glance**

| Script | Option | Effect |
|--------|--------|--------|
| `Build-MarketplacePackages.ps1` | `-ValidateOnly` | validate every skill, write nothing |
| | `-Skills a,b` | only these skill folders |
| | `-OutputDir <path>` | write artifacts somewhere other than `dist/` |
| `Publish-MarketplacePackages.ps1` | `-DryRun` | list what would upload; no key needed |
| | `-Skills a,b` | only artifacts matching `<name>-*.sophon-skill` |
| | `-ArtifactDir <path>` | read artifacts from somewhere other than `dist/` |
| | `-MarketplaceUrl <url>` / `-ApiKey <key>` | override the env vars above |

> `dist/` is not cleaned between builds. If it holds an old version of a skill, the publish
> script uploads that too (and gets `409` for it). Clear `dist/` or use `-Skills` to stay
> targeted.

## 1. Build artifacts

```bash
# Validate only (what CI runs) — no output written, exits non-zero on any violation
pwsh -File build/Build-MarketplacePackages.ps1 -ValidateOnly

# Build .sophon-skill zips into dist/
pwsh -File build/Build-MarketplacePackages.ps1
```

For each skill under `skills/`, the script validates `manifest.json` against the
[manifest contract](../CONTRIBUTING.md#manifest-contract) and the
[build checks](../CONTRIBUTING.md#build-checks-beyond-the-contract) (`build/SkillLint.psm1`) —
collecting **all** errors per skill rather than stopping at the first — and, for skills that
validate clean, writes
`dist/<name>-<version>.sophon-skill`: a zip of the skill folder's **contents** (`manifest.json` at
the zip root, no wrapping folder), excluding `__pycache__/`, `dist/`, `.DS_Store`, `Thumbs.db`, and
`*.pyc`. Entries are written in ordinal path order with forward slashes, and each archive is
re-checked against the zip rules (`SKILL-ZIP`); a failing archive is deleted. The run exits `1` if
any skill failed validation (packages that did validate are still written). Each artifact's SHA256 is printed — use it to verify the upload against the registry's
recorded hash and the download endpoint's `X-Checksum-Sha256` header.

`dist/` is git-ignored — artifacts are build output, not checked in.

Options: `-Skills jira,confluence` (build only the named skills); `-OutputDir <path>` (write
artifacts elsewhere).

## 2. Get a publisher API key

Publishing uses an `smk_`-prefixed API key tied to the **Buildersoft LLC** account with a verified
email. Mint one **once** from an interactive JWT session (API keys can't mint other API keys):

```bash
ACCESS_TOKEN=$(curl -sS -X POST https://marketplace.sophon.buildersoft.io/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"you@buildersoft.io","password":"..."}' | jq -r .accessToken)

curl -sS -X POST https://marketplace.sophon.buildersoft.io/api/v1/me/api-keys \
  -H "Authorization: Bearer $ACCESS_TOKEN" -H 'Content-Type: application/json' \
  -d '{"name":"ci-publish-key"}'
```

The response's `key` (`smk_...`) is shown **exactly once** — save it as a secret. API keys are
publish-scoped only.

## 3. Publish

```bash
export SOPHON_MARKETPLACE_API_KEY='smk_...'
pwsh -File build/Publish-MarketplacePackages.ps1            # all of dist/
pwsh -File build/Publish-MarketplacePackages.ps1 -DryRun    # preview, no upload
pwsh -File build/Publish-MarketplacePackages.ps1 -Skills jira
```

The script POSTs each artifact to `<MarketplaceUrl>/api/v1/publish` as multipart field `package`
with the Bearer key. `-MarketplaceUrl` (or `$env:SOPHON_MARKETPLACE_URL`) overrides the target
(e.g. a local `http://localhost:5100`). Equivalent raw call:

```bash
curl -X POST https://marketplace.sophon.buildersoft.io/api/v1/publish \
  -H "Authorization: Bearer $SOPHON_MARKETPLACE_API_KEY" \
  -F "package=@dist/jira-1.0.0.sophon-skill;type=application/zip"
```

A successful publish returns `201 Created` with `{ name, version, status: "pendingReview", sha256 }`.

## 4. Review & versioning

- Every new version — including the first for a new name — starts in **`pendingReview`** and is
  invisible to browse/search/download until a super-admin approves it. Publishing a new, strictly
  greater version on an already-approved skill keeps the previous approved version live while the
  new one waits.
- **Versions must be strictly increasing SemVer.** Bump `manifest.version` before re-publishing any
  change. Re-uploading byte-identical content returns `409 duplicate-content`.
- There is no separate "edit metadata" endpoint — description, tags, category, etc. all come from
  whatever `manifest.json` you publish next.

## 5. Publishing from GitHub Actions

Two workflows live in `.github/workflows/`:

- **`validate.yml`** runs automatically on PRs and pushes to `main` that touch `skills/`, `build/`,
  `agents/`, `tests/skills/`, `tests/build/`, `tests/agents/` or `templates/`: `-ValidateOnly`,
  `generate.py --check`, `Test-SkillLint.ps1`, `run_all.py`, then the agent source checks. It needs
  no configuration.
- **`ffmpeg-video.yml`** runs on changes to the `ffmpeg-video` skill, its build folder, the skill
  lint or its tests: unit tests on Python 3.10 and 3.13, the Python-floor refusal, real-FFmpeg
  tests on Ubuntu 24.04 (FFmpeg 6.1) and Windows, and the provenance check (`Sync-FfmpegSkill.ps1
  -Check` against a fresh clone of the pinned upstream tag). The macOS job runs only when the
  workflow is started by hand.
- **`ffmpeg-skill-upstream-watch.yml`** runs weekly (and by hand). It keeps one open issue listing
  the upstream ffmpeg-skill tags newer than the vendored pin, and closes it when the pin is
  current. It never opens a pull request; re-syncing stays a deliberate step (§8).
- **`publish.yml`** is **manual only** (Actions → *publish* → *Run workflow*). It builds every
  skill and then runs the publish script. Inputs are `skills` (comma-separated, blank = all) and
  `dry_run` (**defaults to `true`**, so untick it to really upload).

One-time repo setup for `publish.yml` (Settings → Environments):

1. Create an environment named **`marketplace`**. The job targets it, so you can add required
   reviewers there as an approval gate.
2. Add the **secret** `SOPHON_MARKETPLACE_API_KEY` = your `smk_…` key, either on that environment
   or as a repo secret.
3. *(Optional)* Add the **variable** `SOPHON_MARKETPLACE_URL` to target a non-production
   marketplace. If it's empty, the script uses production.

## 6. Release checklist

0. For a **new** skill, check the slug is free while signed in: `sophon skills search <slug>`,
   `sophon agents search <slug>` (names are shared across package types) and
   `GET https://marketplace.sophon.buildersoft.io/api/v1/packages/<slug>`. A hit not owned by
   Buildersoft stops the release.
1. Bump `version` in every changed skill's `manifest.json`. It must be strictly greater than the
   last published version.
2. `python tests/skills/run_all.py` shows every file as PASS.
3. `pwsh -File build/Build-MarketplacePackages.ps1 -ValidateOnly` exits `0`.
4. Build with `-Skills <changed skills>`, then publish with `-DryRun` and check the list.
5. Publish for real. Confirm every response is `201` / `pendingReview`, then ask a super-admin to
   approve.

## 7. Skills that agents require

An agent package can name marketplace skills in `requires.skills`; Sophon offers to install them
with the agent. The marketplace refuses an agent whose required skill is not approved, so the
order is fixed:

1. Publish the skill (`pwsh -File build/Publish-MarketplacePackages.ps1 -Skills ffmpeg-video`).
2. Wait until a super-admin has **approved** that version (not just `pendingReview`).
3. Only then upload the agent (`dist/agents/video-producer-<version>.sophon-agent`) in the
   Marketplace wizard, as described in [AGENTS.md](AGENTS.md) section 13. Agents are never
   uploaded with `Publish-MarketplacePackages.ps1`.

The agent's `requires.skills[].minVersion` must be a version that is approved and live. Raise it
only after the newer skill version is approved, and bump the agent version when you do.

## 8. Releasing a vendored skill (ffmpeg-video)

`ffmpeg-video` ships [kajisho5/ffmpeg-skill](https://github.com/kajisho5/ffmpeg-skill) unchanged
under `vendor/ffmpeg-skill/`. A re-sync is a release of its own; the policy (when to sync, which
tag, how to review) is in [VENDORING.md](VENDORING.md). The steps:

1. Pick the tag and its full commit sha (the upstream watch issue lists newer tags).
2. Re-vendor and regenerate (needs git, Python 3.10+ and network access to GitHub, or a local
   clone passed as `-Source`):

   ```powershell
   pwsh -NoProfile -File build/ffmpeg-video/Sync-FfmpegSkill.ps1 -Tag vX.Y.Z -ExpectedCommit <sha>
   ```

   It prints the tool-surface diff and a review checklist, and fails on anything that needs a
   person (an unclassified path parameter, a tool with no policy entry, a contract change).
3. Work through the checklist. Bump `version` in `build/ffmpeg-video/manifest.base.json` (patch
   when the surface diff is empty, minor for added tools, parameters or values, major for removed
   or renamed ones), update the tag and commit in `skills/ffmpeg-video/THIRD_PARTY_NOTICES.md`,
   then run `python -B build/ffmpeg-video/generate.py`.
4. Verify:

   ```powershell
   pwsh -NoProfile -File build/ffmpeg-video/Sync-FfmpegSkill.ps1 -Tag vX.Y.Z -ExpectedCommit <sha> -Check
   python -B build/ffmpeg-video/generate.py --check
   python tests/skills/run_all.py
   python tests/skills/ffmpeg_video_media.py            # with FFmpeg 6.1+ installed
   pwsh -File build/Build-MarketplacePackages.ps1 -ValidateOnly
   ```

5. On a major bump, update the Video Producer sources and pins (and `SkillPolicy.MinVersion` if the
   old skill no longer works with it), then rebuild the agent packages.
6. Build with `-Skills ffmpeg-video`, publish, and get it approved. Then publish the agent if it
   changed (§7).

The archive holds about 80 entries (the 74 vendored files plus the skill's own), all forward-slash
names, with the vendored `LICENSE` and no `.sh` file, so the marketplace raises no scripts flag.

## Common failures

| HTTP | Cause |
|------|-------|
| `413` | package exceeds 100 MB |
| `403` | you don't own an existing skill with this name |
| `409` | name used by a different package type; version not strictly greater than your highest; or identical content already published |
| `422` | zip-safety violation (zip-slip / bomb / entry-count) or manifest schema failure — the response lists every failing field |

Rate limit: 10 uploads/hour per publisher.
