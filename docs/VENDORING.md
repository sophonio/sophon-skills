# Vendoring third-party code into a skill

A skill may ship another project's code unchanged, under `skills/<name>/vendor/<project>/`. Today
one skill does: `ffmpeg-video` ships [kajisho5/ffmpeg-skill](https://github.com/kajisho5/ffmpeg-skill)
(MIT, © 2026 kajisho5) at tag `v3.9.2`, commit `3f8ba63cc8eb991c1730d57b0215e6127765399a`. This page
is the policy for that tree and for any future one, and the runbook for a re-sync.

Vendored code runs with the Gateway's own rights on Sophon's process backend: the user's files,
the network and the environment. A sync is therefore a code review, not a routine update.

## 1. Policy

- **Tags only.** Vendor a released tag, never a branch or `main`, and assert the commit it resolves
  to (`-ExpectedCommit`). A tag that moved is a stop: find out why before going on.
- **No local patches.** Every file under `vendor/` is a byte-identical copy of the upstream file at
  the pinned commit. A bug in it is reported upstream, and the fix arrives with a later tag.
  Wrapper behaviour belongs in the skill's own code (`main.py`, `lib/`) or in its build inputs
  (`build/ffmpeg-video/policy.json`).
- **When to sync.** For a fix the skill needs or an upstream security advisory, at any time;
  otherwise at most once a month. ffmpeg-skill releases several times a day, so following every tag
  is not a goal.
- **Soak time.** Pick a tag that has had no follow-up patch release for 48 hours. A tag that was
  fixed within a day is skipped in favour of the fix.
- **Every sync is a release.** It bumps the skill's version (section 4); the marketplace refuses a
  version equal to or lower than any version ever uploaded, rejected ones included.
- **Never edit by hand:** anything under `vendor/`, `vendor.lock.json`, `lib/tool-map.json`, the
  manifest `tools[]`, the `main.py` GENERATED CONSTANTS block or the README tools table. The sync
  and `build/ffmpeg-video/generate.py` own them.
- **What may be vendored** (`build/ffmpeg-video/vendor-files.txt`): an explicit allowlist of
  globs, reviewed like code. Never shell, batch or PowerShell scripts, native binaries or compiled
  Python (`.sh .ps1 .psm1 .bat .cmd .exe .dll .so .dylib .pyc .pyo`), dotfiles, symlinks,
  submodules, or files under a folder name the installer or the build drops (`.git`,
  `node_modules`, `__pycache__`, `bin`, `obj`, `dist`, ...). Text only: strict UTF-8, no NUL bytes.
- **Credit.** The upstream `LICENSE` is vendored unchanged, and `THIRD_PARTY_NOTICES.md` at the
  skill root carries its full text, its copyright line, the tag, the commit and the URL.

## 2. What is in the tree

```
skills/ffmpeg-video/
  vendor/ffmpeg-skill/      74 files: LICENSE, package.json, SKILL.md, mcp/server.py,
                            scripts/*.py, scripts/_common/*.py, templates/*.json
  vendor.lock.json          the lock (below)
  THIRD_PARTY_NOTICES.md    the MIT text, © 2026 kajisho5, tag and commit, the FFmpeg trademark note
  lib/tool-map.json         generated from the vendored contract; listed in the lock's generated[]
```

`.gitattributes` marks `skills/ffmpeg-video/vendor/** -text`, so git never rewrites their line
endings and the hashes hold on every platform.

**`vendor.lock.json`** (written only by `generate.py --write-lock`, which the sync calls):

```json
{
  "schemaVersion": 1,
  "upstream": {"repo": "https://github.com/kajisho5/ffmpeg-skill", "tag": "v3.9.2",
               "commit": "3f8ba63cc8eb991c1730d57b0215e6127765399a", "version": "3.9.2"},
  "files": [{"path": "vendor/ffmpeg-skill/<path>", "sha256": "<hex>", "bytes": 1234}],
  "generated": [{"path": "lib/tool-map.json", "sha256": "<hex>"}]
}
```

Paths are relative to the skill root with forward slashes, and `files[]` is sorted by ordinal path.
Every file under `vendor/` is listed, and nothing else may exist there.

**Who checks it:**

| Check | Where | When |
|---|---|---|
| `SKILL-LOCK`, `SKILL-NOTICE`, `SKILL-FOLDER` | `build/SkillLint.psm1` | every `Build-MarketplacePackages.ps1` run, CI included: hashes, sizes, no extra or missing file, sorted lock, denied extensions, strict UTF-8, the vendored LICENSE credited in `THIRD_PARTY_NOTICES.md`; a file over 256 KiB is a warning (the marketplace moderator preview truncates it) |
| `VENDOR_CORRUPT` | `lib/bridge.py` | every tool call: the installed files are hashed against the lock, and an extra `.py`, `.pyc`, `.pth`, `.so`, `.pyd` or `.dll` refuses the call |
| `generate.py --check` | CI (`validate.yml`, `ffmpeg-video.yml`) | the generated files match the vendored contract and the policy |
| `Sync-FfmpegSkill.ps1 -Check` | CI (`ffmpeg-video.yml`, provenance job) | every vendored file, the lock and the notices are re-derived from a fresh clone of the pinned tag |

## 3. Re-syncing ffmpeg-video

Needs PowerShell 7, git, Python 3.10+ and either network access to GitHub or a local clone of the
upstream repository.

```powershell
pwsh -NoProfile -File build/ffmpeg-video/Sync-FfmpegSkill.ps1 -Tag vX.Y.Z -ExpectedCommit <full sha>
pwsh -NoProfile -File build/ffmpeg-video/Sync-FfmpegSkill.ps1 -Tag vX.Y.Z -ExpectedCommit <full sha> -Source <local clone>
```

What it does, in order (the upstream repository is only read, never modified):

1. Opens the repository (`-Source`, or clones `-RepoUrl` into a temporary folder), resolves
   `refs/tags/<tag>^{commit}`, asserts it equals `-ExpectedCommit`, and checks that the tag's
   `package.json` version equals the tag.
2. Expands `vendor-files.txt` against `git ls-tree` at that commit. Every pattern must match a
   file, and the deny rules in section 1 apply on top; case-only duplicates fail.
3. Copies each file's exact bytes with `git cat-file blob` and checks each copy against its git
   blob id, its UTF-8 and the 256 KiB preview cap.
4. Runs an AST import scan (`generate.py --scan-imports`): a non-stdlib, non-local import outside
   a `try` block fails the sync; a network module (`socket`, `urllib`, `http`, `ssl`, ...) or a
   `shell=` subprocess call is a warning to review.
5. With `-RunUpstreamTests`, runs `CI=true python -B tests/test_contract.py` in a throwaway
   checkout of the tag (needs FFmpeg 6.1+); a failure fails the sync.
6. Swaps the vendor folder in one step, writes `vendor.lock.json` and regenerates the tool surface
   (`generate.py --write-lock --summary`). The summary prints tools and parameters added or
   removed, path classifications and risk changes. A path-like parameter that `policy.json` does
   not classify, a tool with no policy entry, a contract major other than 2, or a changed upstream
   `removed`/`deprecated` list fails until a person updates `policy.json`.
7. Prints the review checklist.

**Review checklist** (the sync prints it with the current values):

- [ ] Bump `version` in `build/ffmpeg-video/manifest.base.json` (section 4), then run
      `python -B build/ffmpeg-video/generate.py`.
- [ ] Review every new or changed path classification in the summary (`policy.json` paths and
      literals). An unclassified path is a write or read the bridge cannot confine.
- [ ] Read the upstream CHANGELOG for every release since the old pin, and the import-scan
      warnings.
- [ ] `scripts/_contract.py` is still under 256 KiB (the moderator preview cap).
- [ ] Note a change of `_platforms.UPLOAD_LIMITS_AS_OF` in the release notes.
- [ ] Update the tag and commit in `skills/ffmpeg-video/THIRD_PARTY_NOTICES.md`.
- [ ] On a major bump: update the Video Producer sources and pins
      (`build/agent-src/families/video/`), and its `SkillPolicy.MinVersion` if needed.
- [ ] Run the checks below.

```powershell
pwsh -NoProfile -File build/ffmpeg-video/Sync-FfmpegSkill.ps1 -Tag vX.Y.Z -ExpectedCommit <sha> -Check
python -B build/ffmpeg-video/generate.py --check
python tests/skills/run_all.py                       # includes the argv-parity tests
python tests/skills/ffmpeg_video_media.py            # with FFmpeg 6.1+ installed
pwsh -File build/Build-MarketplacePackages.ps1 -ValidateOnly
pwsh -NoProfile -File build/Test-AgentSources.ps1    # the agent still names real skill tools
```

The argv-parity tests in `tests/skills/test_ffmpeg_video.py` matter most at a sync: the bridge
reuses upstream's `mcp/server.py` `build_argv`, `_common.run_tool` and `_contract.mcp_read_only` at
runtime, so they prove that the pre-filled specs in `lib/tool-map.json` still build the same argv
as the full upstream contract for every tool.

Then release it as any skill ([PUBLISHING.md](PUBLISHING.md) section 8): one PR with the sync, the
version bump and the notices; build, publish, get it approved; then the agent if it changed.

## 4. Versioning

- **Patch** when the tool surface is unchanged (the summary's diff is empty).
- **Minor** when tools, parameters or enum values are added.
- **Major** when any are removed or renamed. This also needs an agent update, because the Video
  Producer names and pins `ffmpeg.*` tools.

`SKILL_VERSION` in `main.py` and the manifest version both come from `manifest.base.json`;
`generate.py --check` fails if they differ from it.

## 5. Watching upstream

`.github/workflows/ffmpeg-skill-upstream-watch.yml` runs weekly (and by hand) with read-only
contents and issue rights. It lists the upstream tags newer than the pin in `vendor.lock.json`,
with their CHANGELOG headings, in one issue that it keeps up to date, and closes the issue once the
pin is current. It never opens a pull request and never syncs: choosing a tag and reviewing it
stays a person's job.

## 6. Vendoring into another skill

The generic rules apply to any skill: a `vendor/<project>/` tree only next to a
`vendor.lock.json` in the schema above, the vendored `LICENSE` credited in
`THIRD_PARTY_NOTICES.md`, the denied extensions, strict UTF-8 and the folder rule. The build checks
enforce them. A new vendored project also needs its own sync tooling under
`build/<skill>/` that copies bytes from a tag the way `Sync-FfmpegSkill.ps1` does, an entry in this
policy, and a provenance check in CI. Prefer not vendoring at all: most skills here are a single
`main.py` on the standard library.
