# ffmpeg-video skill and Video Producer agent: design as implemented

**Status:** implemented on branch `feat/ffmpeg-video`; manual end-to-end checks and publishing
pending (section 5). **Pins:** sophon `a431e1a64` (CLI 2.2.2), ffmpeg-skill `v3.9.2` =
`3f8ba63cc8eb991c1730d57b0215e6127765399a`.

This records the approved plan as it was built. Where the build departed from the plan, the
change and its reason are stated in place and collected in section 4. The later Sophon core
changes that would remove most workarounds are a separate note:
[`2026-11-15-ffmpeg-video-core-changes.md`](2026-11-15-ffmpeg-video-core-changes.md).

## 1. Context

Sophon generates media assets (`tts.file`, `image.generate`, `video.generate`, `music.generate`,
`media.image`) but cannot edit or assemble video; built-in `media.video` only reads info, frames,
thumbnails and audio. [ffmpeg-skill](https://github.com/kajisho5/ffmpeg-skill) (MIT, © 2026
kajisho5) is a mature local editor: 42 stdlib Python CLI tools over FFmpeg 6.1+, a
machine-readable contract, a declarative `render.py` project (clips, join, silence, fit, captions,
graphics, overlays, audio, loudness, export, chapters, check) and platform templates.

The goal: all 42 tools in Sophon as a marketplace skill, plus a standalone agent that plans,
produces and renders short videos with them.

**Hard constraints (verified in the sophon source):**
- A skill call is one-shot. Only the entrypoint text is copied, as `script.py` behind a two-line
  preamble (`import json, os` and `params = …`, `SandboxedTool.cs:85-92`), into
  `<dataDir>/sandbox/workspaces/<guid>`, which is deleted afterwards
  (`ProcessSandboxOrchestrator.cs:33-35,117,133`; `Program.cs:1215`).
- The Docker backend runs `python:3.13-alpine` with no FFmpeg, a read-only workspace and no host
  mounts, so video is impossible there. The process backend inherits the Gateway's PATH and
  environment and can reach any absolute path.
- The default timeout is 30 s with no upper clamp (`SkillManifestParser.cs:369`). No progress
  events and no attachments from skills (`SandboxedTool.cs:193-196`).
- An exact tool-name collision skips the whole skill. Names with two or more dots group in the
  tool index by their first two segments, and only groups over 15 collapse
  (`ToolFilterMiddleware.cs:332,351`).
- When `requirements` is empty, `PythonImportResolver` pip-installs every non-stdlib name on a
  line starting `import`/`from`, docstrings included.

**User decisions:**
1. sophon-skills only: no sophon or marketplace code. Process backend only, with a structured
   refusal under Docker. The user installs Python 3.10+ and FFmpeg 6.1+. Core changes go in a note.
2. All 42 tools.
3. One standalone Video Producer agent, outside the development family.

## 2. Phases as delivered

| # | Work | Result |
|---|---|---|
| 0 | slugs free (`sophon skills search`, `sophon agents search`), `.gitattributes` `-text` line, trademark wording | done; `ffmpeg-video` and `video-producer` free |
| 1 | generic skill lint for every skill | `build/SkillLint.psm1`, `build/catalog/*.psd1`, `tests/build/`; 11 existing skills fixed and patch-bumped |
| 2 | vendoring | `Sync-FfmpegSkill.ps1`, `vendor-files.txt`; 74 files at v3.9.2 |
| 3 | generator | `generate.py`, `policy.json`, `manifest.base.json`, `smoke-args.json`; 44 tools |
| 4 | runtime | `main.py`, `lib/bridge.py`, notices, README |
| 5 | tests and CI | `sandboxsim.py`, three test files, a container case; `validate.yml`, `ffmpeg-video.yml`, `ffmpeg-skill-upstream-watch.yml` |
| 6 | multi-family agent tooling | registry, family keys, `-Family`, section L; development packages byte-identical |
| 7 | Video Producer | `build/agent-src/families/video/**`, `agents/video-producer/` |
| 8 | docs | this file, the core note, `docs/VENDORING.md`, CLAUDE.md, CONTRIBUTING.md, AGENTS.md, PUBLISHING.md, READMEs |
| 9 | manual end-to-end, then publish skill → approve → publish agent → approve | pending |

## 3. Design

### 3.1 Fixed decisions

| Item | Decision |
|---|---|
| Skill | `skills/ffmpeg-video/`, slug `ffmpeg-video` (fallback `video-toolkit`, keeping the tool namespace, if the trademark becomes a concern) |
| Tool names | `ffmpeg.<group>.<upstream script>`: 42 tools plus `ffmpeg.setup.doctor` and `ffmpeg.setup.contract` = 44. Every group has 15 or fewer, so the index lists every name; wire names (`ffmpeg_edit_cut`) are unique and at most 25 characters. No collision with `media.video`, `video.generate` or any skill. |
| Parameters | upstream argparse dests unchanged; wrapper extras `detail`, `project_json`, `recipe_json`, `use_cache`, `tool_name`; never a parameter named `tool` |
| Backend | process only; `/workspace` cwd → `BACKEND_UNSUPPORTED` (`backend: docker`); a cwd not shaped `…/sandbox/workspaces/<32 hex>` with no `FFMPEG_VIDEO_SKILL_ROOT` → `BACKEND_UNSUPPORTED` (`backend: unknown`). `/.dockerenv` is not a signal (the Pro prebuilt Gateway runs in a container on the process backend). |
| Code layout | `main.py`: stdlib bootstrap, Python 3.6 syntax, no docstrings, no `__future__`. `lib/bridge.py`: all logic, Python 3.10+. `lib/tool-map.json`: generated. `vendor/ffmpeg-skill/`: byte-identical upstream. `vendor.lock.json`: sha256 lock. |
| Upstream reuse | runtime: `mcp/server.py` `build_argv` with `_SPECS` pre-filled from the tool map, `_common.run_tool(per_call=…)`, `_contract.mcp_read_only`. Build time: `_contract.build(detect=False)`. Not used: `server.call_tool`, `server.specs()`, the JSON-RPC loop. |
| Manifest sandbox | `{"network":false,"timeoutSeconds":1800,"maxMemoryMb":2048,"maxCpuPercent":100}`; `requirements: []` permanently; no `permissions` block |
| Output root | `<dataDir>/documents/video/ffmpeg-video/`; more write roots from `FFMPEG_VIDEO_WRITE_ROOTS` (PATH-separated) |
| Exit and result | always exit 0; one compact ASCII JSON object printed last (repo convention) |
| Agent | `agents/video-producer/`, family `video`, sources in `build/agent-src/families/video/` |

### 3.2 Tool table

| Group | Tools | Risk |
|---|---|---|
| `ffmpeg.inspect` (6) | probe, cropdetect, check | none (run with `FFMPEG_SKILL_READ_ONLY=1`) |
| | scenes, look, report | low (PNG, EDL or HTML side files) |
| `ffmpeg.make` (4) | insert, background, sequence, waveform | low |
| `ffmpeg.edit` (11) | cut, join, silence, broll, multicam, sync, grid, pad, freeze, loop, metadata | low |
| `ffmpeg.adjust` (11) | fit, crop, color, speedramp, reverse, straighten, sphere, stabilize, deinterlace, denoise, redact | low |
| `ffmpeg.layer` (3) | caption, graphics, overlay | low |
| `ffmpeg.mix` (2) | audio, loudness | low |
| `ffmpeg.deliver` (2) | export, proxy | low |
| `ffmpeg.project` (2) | render, batch | **medium**: one approval card per call |
| `ffmpeg.setup` (3) | doctor, contract | none |
| | verify (its outputs forced into the output root) | low |

Totals: 5 none, 37 low, 2 medium. The approval threshold is Medium, so `low` shows no card. That
is justified only because the bridge confines every output to the write roots, requires an
explicit `output` on writing tools, honours `overwrite` only inside the output root, and upstream
never modifies its inputs.

### 3.3 Manifest

Top-level fields come from `build/ffmpeg-video/manifest.base.json` (version included); the
generator writes `tools[]` and owns the file's formatting. Category `utility`, ten tags, runtime
`sandbox`, language `python`, `platforms: []`.

- **Schema subset.** Each tool's `parameters` is `type: object` with `properties`, `required` and
  `additionalProperties: false`; one `type` per property, `items` on every array, string enums
  only, no `$ref`/`oneOf`/`anyOf`/`allOf`/`not`. Numeric choices (`join.channels`, `fit.rotate`)
  and mutual-exclusion or one-of rules become description text; the bridge enforces them from the
  tool map.
- **Dropped everywhere:** `argv`, `json`, `json_brief`, `progress`, `plan`, `hw`, `no_hw`, each
  refused by name with a reason. **Dropped per tool:** render `work`, `keep`, `audit_log`, `cache`
  (replaced by `use_cache`); batch `watch`, `work`; verify `out`, `keep`, `dry_run` (upstream has no
  dry run for verify); `join.list` (the paths inside a list file cannot be checked; pass `inputs`);
  `overwrite` on the read-only probe, check and cropdetect.
- **Kept:** `dry_run`, `timeout` (clamped), `fast`, `overwrite` (output root only), `codec`,
  `quality`.
- **Descriptions** are at most 600 characters: upstream's summary sentence, a hand-written "Use
  when …" line from `policy.json`, then a generated "Writes: …" line. Parameter help is capped at
  360 characters, which keeps `manifest.json` at about 244 KB.

### 3.4 Runtime

**`main.py`** (bootstrap; constraints linted by the skill lint and the unit tests):
1. Records `START` and `CWD0`, sets `sys.dont_write_bytecode`.
2. Pops `tool`; a name outside `TOOLS` returns exactly `{"error":"Unknown tool: <name>"}`.
3. Detects the backend (section 3.1). The refusal's hint covers the desktop (make Docker
   unreachable, set `SOPHON__Sandbox__AllowProcessFallback=true`, restart; this lowers isolation
   for every skill) and Pro (a Gateway image with FFmpeg on the prebuilt compose). Its wording avoids
   the injection guard's Low-tier words.
4. Resolves the data folder: the cwd minus `sandbox/workspaces/<hex>`, `SOPHON_DATA_DIR`,
   `SOPHON__DataDirectory`/`Sophon__DataDirectory`, XDG (Linux with `SOPHON_OS=1`), `~/.sophon`.
5. Finds the skill home: `FFMPEG_VIDEO_SKILL_ROOT`, `skills/installed/ffmpeg-video`, every folder
   under `skills/{installed,bundled,organization,self-authored}`, then `~/.sophon/skills/installed/*`
   (`sophon dev install` ignores `SOPHON_DATA_DIR`). A folder matches on manifest name and version
   and `sha256(vendor.lock.json) == VENDOR_LOCK_SHA256`; otherwise `VENDOR_NOT_FOUND` lists every
   candidate and why it was rejected.
6. On Python 3.10+, loads `lib/bridge.py` with `importlib.util` and calls `bridge.run(...)`.
   Otherwise looks for an interpreter (`FFMPEG_VIDEO_PYTHON`, `py -3` on Windows, `python3.14` …
   `python3.10` on PATH and in `/opt/homebrew/bin`, `/usr/local/bin`, `/usr/bin`, the usual Windows
   install folders; each probed for 5 s) and re-execs `[exe, -B, -X utf8, lib/bridge.py, --stdin]`
   with the call on stdin. None qualifies → `PYTHON_UNSUPPORTED`.
7. Any exception → `INTERNAL_ERROR`. Output is `json.dumps(..., ensure_ascii=True, separators=(",",":"))`, once.

Imports are `sys`, `os`, `re`, `json`, `hashlib`, `time`, `importlib.util` and `subprocess`, all on
the resolver's stdlib list, so Sophon installs nothing. The GENERATED CONSTANTS block holds
`SKILL_NAME`, `SKILL_VERSION`, `VENDOR_TAG`, `VENDOR_COMMIT`, `VENDOR_LOCK_SHA256` and `TOOLS`.

**`lib/bridge.py`**, one call:
1. **Vendor check.** Every locked file is hashed; a mismatch, or an extra `.py`, `.pyc`, `.pth`,
   `.so`, `.pyd` or `.dll`, returns `VENDOR_CORRUPT`.
2. **Folders and time.** Moves into `<outputRoot>/.tmp/<uuid>` (so Sophon can delete its workspace
   even when a run is orphaned) and sweeps stale `.tmp` folders. Reads S from the installed
   manifest (default 1800); the wrapper deadline is D = S − 60.
3. **Child environment.** Drops `FFMPEG_SKILL_MCP_FULL`, `_FFMPEG_SKILL_OWNED`, `PYTHONPATH` and
   similar; sets UTF-8, `PYTHONDONTWRITEBYTECODE`, `HF_HUB_OFFLINE=1` (unless
   `FFMPEG_VIDEO_ALLOW_MODEL_DOWNLOAD=1`), `TMP`/`TEMP`/`TMPDIR` to the call folder,
   `FFMPEG_SKILL_READ_ONLY=1` for read-only tools. PATH gets `FFMPEG_VIDEO_FFMPEG_DIR` first and
   well-known folders appended when they hold ffmpeg (WinGet Links, `%ProgramFiles%\ffmpeg\bin`,
   Chocolatey, Scoop; `/opt/homebrew/bin`, `/usr/local/bin`; `/snap/bin`).
4. **Arguments** (from the tool map): `tool`, `apiKey` and `accessToken` dropped; unknown keys
   and removed keys refused by name (`INVALID_ARGUMENT`); coercion (`"true"`, numeric strings, a
   scalar to a one-item list); choices, mutual exclusion, one-of-required and conditional-required
   rules; `timeout` clamped to `[1, D − elapsed − 30]`.
5. **Path roles** `in_file`, `in_files`, `in_dir`, `in_paths`, `out_file`, `out_side_file`,
   `out_dir`:
   - inputs: absolute, `~/…` (expanded) or relative to the output root; no NUL, newline or URL
     scheme; must exist (`INVALID_ARGUMENT`, `reason: not_found`); nothing under the data folder
     except `documents/**`; never the skill home;
   - outputs: inside a write root, with an extension, no `..`, no escape through a symlink;
     relative outputs land under the output root, where parent folders are created;
   - `overwrite: true` only when every output is inside the output root, else `PATH_NOT_ALLOWED`
     (`reason: overwrite_outside_output_root`);
   - case-insensitive, separator-aware comparison on Windows and macOS.
6. **Special handlers.**
   - `render`: `project` or `project_json` (≤ 64 KB). Every project is parsed (≤ 1 MB, plan
     documents refused), every path in it checked and made absolute, and the checked copy saved
     to `<outputRoot>/projects/` (the temp folder on a dry run); that copy renders. Relative paths
     in `project_json` resolve against the output root, in a project file against its own folder
     (as upstream does). `--work` goes to the call folder, except for template packs, `init`,
     `list_templates`, `write_project` and `export_timeline`, which upstream refuses it for.
     `use_cache` maps to `--cache <outputRoot>/.cache/render`. A non-export `stop_after` keeps its
     work folder in `previews/<stamp>`.
   - `batch`: `recipe` or `recipe_json`, normalised and saved; `batch.py`, `render.py` and
     `verify.py` refused as steps; each step is parsed against its own tool's options from the
     tool map (exact spellings only: no abbreviations, no attached short values, no `--overwrite`,
     no option that writes beside the input); every `out_*` value must be `{out}`; every input
     value, joined or separate, is checked and passed absolute; `glob`, `suffix` and `ext` may not
     name a folder, and every glob match is checked as an input; `output_dir` defaults to
     `<outputRoot>/batch/<stamp>`; `jobs` capped at 2.
   - `verify`: `--out` forced to `<outputRoot>/verify/<stamp>`.
   - `contract`: without `tool_name`, a summary from the tool map (no process); with it, a trimmed
     spec (wrapper rules, description, examples, dry run, verification, capabilities, result keys;
     `detail: full` adds the parameters).
   - `doctor`: the upstream doctor plus wrapper facts `backend`, `dataDir`, `skillHome`,
     `outputRoot`, `writeRoots`, `vendor`, `sandboxTimeoutSeconds`, `deadlineSeconds`,
     `childPython`, the ffmpeg and ffprobe found, `freeDiskMb`, `ready` and `problems[]` each with a
     `fix`. Without FFmpeg it returns a `DEPENDENCY_MISSING` envelope that still carries this
     `doctor` block, so the agent learns `outputRoot` either way.
7. **Order.** Arguments and paths are validated **before** preflight, so `INVALID_ARGUMENT` and
   `PATH_NOT_ALLOWED` appear (and are testable) without FFmpeg. Then preflight: ffmpeg and ffprobe
   must be found and report 6.1 or later (`ffmpeg -version`), else `DEPENDENCY_MISSING` with
   per-OS install or upgrade hints (upstream's exit 127 and `ffmpeg_unsupported` map to it too);
   at least `FFMPEG_VIDEO_MIN_FREE_MB` (default 2048) free on the output volume for writing calls,
   else `INSUFFICIENT_DISK`.
8. **Run.** `server.build_argv` builds the argv (section 3.5); `_common.run_tool([script] + argv,
   per_call=max(1, (D − elapsed − 60)/4), env=env)` runs it, so its ceiling is exactly D − elapsed
   with nothing patched. Its synthesized timeout document (exit 124) becomes `TIMEOUT`.

   | Layer | Limit | Enforced by |
   |---|---|---|
   | L0 | S = 1800 s, hard kill | Sophon |
   | L1 | D = S − 60; per-tool: probe 120, cropdetect 300, look 300, check 900, doctor 120, contract 60 | bridge |
   | L2 | `run_tool` ceiling D − elapsed, then its grace (POSIX 15 s, Windows `taskkill /T /F`) | upstream |
   | L3 | per ffmpeg run `--timeout` = min(user value, D − 30 in whole minutes); constant per tool, because render.py hashes it into every stage's cache key | upstream |

9. **Cleanup** in `finally`: a failed run's own partial outputs inside the write roots (absent when
   the child started, modified since, not claimed by upstream as written and kept, as a render
   whose check stage failed is, not refused as `output_exists`/`output_locked`, not locked by
   another live process; the kept ones are listed in the failure's `kept`); this run's `.<output>.ffskill*`
   siblings and only dead-pid locks, found by comparing before-and-after snapshots (not by mtime:
   upstream stamps a lock's mtime as its deadline minus one hour); the call folder, retried for
   about 1.5 s on Windows while a dying child still holds it. Dry runs remove every folder they
   created, so the output root is unchanged.
10. **Envelope.** Success: `{ok, tool, status, output, outputs, verified, dryRun, summary, result,
    diagnostics, truncated, fullResultPath, elapsedSeconds, skill}`. Failure: `{ok:false, error,
    errorKind, code, retryable, hint, upstream, stderrTail}`; argparse refusals (exit 2, no JSON)
    are `ARGUMENT_REJECTED`; a failed `check` is `TOOL_FAILED` with its rows kept in `result`.
    Compaction: brief by default; lists over 50 items keep the first 40 and last 10; strings cut at
    2,000 characters; the result capped at 40,000 characters (brief) or 120,000 (full), above which
    the full document spills to `<outputRoot>/reports/*.json` as `fullResultPath`. Brief mode never
    echoes caption or transcript text.

| errorKind | code | retryable |
|---|---|---|
| backend_unsupported | BACKEND_UNSUPPORTED | false |
| python_unsupported | PYTHON_UNSUPPORTED | false |
| dependency_missing | DEPENDENCY_MISSING | false |
| vendor_not_found / vendor_corrupt | VENDOR_NOT_FOUND / VENDOR_CORRUPT | false / true |
| invalid_argument / argument_rejected | INVALID_ARGUMENT / ARGUMENT_REJECTED | false |
| path_not_allowed | PATH_NOT_ALLOWED | false |
| insufficient_disk | INSUFFICIENT_DISK | false |
| timeout | TIMEOUT (hint: `use_cache`, `fast`, a proxy, a shorter section) | false |
| tool_failed | TOOL_FAILED (upstream `error` kept in `upstream`) | false |
| internal | INTERNAL_ERROR | false |

### 3.5 Arguments to argv

`lib/tool-map.json` is generated; its `legend` and `pathRoles` keys document every field. Per
tool: `name`, `group`, `script`, `handler`, `deadline`, `risk`, `read_only`
(`_contract.mcp_read_only`), `json` (`flag` | `add` | `native` | `none`: look is `add`, probe is
`native`), `brief`, `defaultDetail`, `supportsDryRun`, `dryRunExecution`, the minimal upstream
`spec` (`mcp.positional`, `mcp.argument_exceptions`, each property's `cli`), `params` (types),
`required`, `conditionalRequired` (`whenAny`/`whenNone`, e.g. caption needs `write_srt` when there
is no `input`), `paths`, `choices`, `mutuallyExclusive`, `oneOfRequired`, `constraints`
(`relative_name` for `sequence.pattern`, `lang_suffix` for `caption.srt`, `jobs_cap` for
`batch.jobs`), `writesBesideInput` (`loudness.versions` writes next to its input), `nested` (brand,
project, recipe and pack files hold more paths) and `removed`. Top level: `removedEverywhere`,
`byName`, `mcpJsonExempt`, the upstream pin.

The bridge loads `vendor/ffmpeg-skill/mcp/server.py` (after `sys.dont_write_bytecode = True`),
sets `server._SPECS[script]` from the map, adds `json=True` for `add` tools, `json_brief=True`
for brief detail, `timeout` and the forced paths, and calls `server.build_argv` unchanged. So
positionals, exceptions (`-o`, `-I`, `--from`, …), lists, `--long=value` for values starting
with `-`, and the `options -- positionals` order are upstream's own code. Parity tests guard it:
pre-filled versus full-contract `build_argv` for all 42 tools (84 cases), and `mcp_read_only`
for every tool.

### 3.6 Files

```
skills/ffmpeg-video/
  manifest.json  main.py  README.md  LICENSE  THIRD_PARTY_NOTICES.md  vendor.lock.json
  lib/bridge.py  lib/tool-map.json
  vendor/ffmpeg-skill/   LICENSE package.json SKILL.md mcp/server.py scripts/*.py
                         scripts/_common/*.py templates/*.json          (74 files)
build/ffmpeg-video/      Sync-FfmpegSkill.ps1 generate.py manifest.base.json policy.json
                         vendor-files.txt smoke-args.json
build/SkillLint.psm1  build/catalog/sandbox-python.psd1  build/catalog/marketplace-rules.psd1
build/agent-src/families.psd1  build/agent-src/families/video/{family.psd1,souls/,fragments/soul/}
agents/video-producer/{manifest.json,SOUL.md,TOOLS.md,README.md,LICENSE}
tests/skills/{sandboxsim.py,test_ffmpeg_video.py,test_ffmpeg_video_fake.py,ffmpeg_video_fakes.py,ffmpeg_video_media.py}
tests/build/{Test-SkillLint.ps1,fixtures/skills/<13 cases>/}
tests/agents/fixtures/{families/media/,compose/families-*/}  tests/agents/evals/video-producer.md
.github/workflows/{ffmpeg-video.yml,ffmpeg-skill-upstream-watch.yml}
docs/VENDORING.md  docs/plans/2026-11-15-ffmpeg-video-{design,core-changes}.md
```

Modified: `.gitattributes` (`skills/ffmpeg-video/vendor/** -text`),
`build/Build-MarketplacePackages.ps1`, `build/AgentFamily.psm1`, `build/AgentLint.psm1`,
`build/Compose-AgentSouls.ps1`, `build/Test-AgentSources.ps1`, `build/Build-AgentPackages.ps1`,
`build/agent-src/family.psd1` (data only), `build/agent-src/catalog/sophon-tools.psd1` (media
extensions), `tests/agents/Test-AgentPackages.ps1`, `tests/skills/run_all_container.py`,
`.github/workflows/validate.yml`, the docs, and 11 existing skills fixed by the lint rollout.

The package holds about 80 zip entries (3.0 MB unpacked, 0.9 MB packed), forward-slash names,
the vendored LICENSE, no `.sh`, no symlinks.

### 3.7 Vendoring and re-sync

`Sync-FfmpegSkill.ps1 -Tag vX.Y.Z [-ExpectedCommit] [-Source] [-RepoUrl] [-RunUpstreamTests]
[-Check] [-Python]`: resolve and assert the tag; expand `vendor-files.txt` against `git ls-tree`
with deny rules; copy bytes with `git cat-file blob`, checked against the blob ids; AST import
scan; swap the vendor folder in one step; `generate.py --write-lock --summary`; print the review
checklist. `-Check` writes nothing and re-derives everything from the tag, including the lock's
upstream block and `THIRD_PARTY_NOTICES.md`. Upstream test results are not stored in the lock, so
the lock keeps exactly its shared schema. Policy and runbook: [`docs/VENDORING.md`](../VENDORING.md).

`generate.py` (modes: none, `--check`, `--summary`, `--write-lock --repo --tag --commit`,
`--scan-imports DIR`) builds the vendored `_contract.build(detect=False)` in a child interpreter
(`-I -B`, scrubbed `FFMPEG_*`/`PYTHON*` variables, temp cwd), so the result does not depend on the
machine and no `__pycache__` lands in `vendor/`. It fails on an unclassified path-like parameter,
a tool without a policy entry, a contract major other than 2 or a changed upstream
`removed`/`deprecated` list.

### 3.8 Build checks for every skill

`build/SkillLint.psm1`, run by `Build-MarketplacePackages.ps1` after the contract check, with
rule ids `SKILL-*`: the import-resolver replay and `__future__`; tool-name pattern, uniqueness,
collisions with built-in and other skills' tools (a Denied built-in is a warning) and wire names;
the schema subset and `properties.tool`; the manifest mirror (type, reserved names, permissions);
the folder rule (flat, plus `lib/` and a locked `vendor/`; no dotfiles, no symlinks); the vendor
lock and notices; the zip mirror on the built archive (also under `-ValidateOnly`); a description
injection-literal scan; budget warnings. The table is in
[CONTRIBUTING.md](../../CONTRIBUTING.md#build-checks-beyond-the-contract).

Rollout found real defects in 11 skills, each fixed minimally with a patch bump: docstring lines
that made Sophon pip-install `Profile` (freshservice) or `Sophon` (radarr, sonarr); integer enums
(freshdesk, freshservice, linear, todoist, pdf-toolkit), which Gemini's schema cleaner turns into
strings that the validator then rejects; a `["string","array"]` type (currency-convert); `oneOf`
(translate-text, seerr); an array without an item type (elasticsearch).

### 3.9 The Video Producer agent

- **`agents/video-producer/manifest.json`:** version 1.0.0, category `ai`, tags `video media
  editing production captions voice-over shorts reels`, a `whenToUse` with "Not for:" items ending
  "Family role: video-producer.", `requires.skills` = `[{"name":"ffmpeg-video","minVersion":"1.0.0"}]`
  first, then `requires.tools` = document.upload, image.generate, media.image, media.video,
  music.generate, tts.file, video.generate (no `ffmpeg.*`); `defaults` sub-agents off, model
  routing inherit; `sophon.minVersion` 2.2.0.
- **`TOOLS.md`:** 8 chat pins (`ffmpeg.inspect.check`, `ffmpeg.inspect.look`,
  `ffmpeg.inspect.probe`, `ffmpeg.make.insert`, `ffmpeg.project.render`, `ffmpeg.setup.doctor`,
  image.generate, tts.file); a 3-line body: the other groups, and document.read and canvas.render,
  load through tools.search and tools.load.
- **SOUL** (composed, 21,226 B of a 24,576 B cap) from `souls/video-producer.md` and fragments
  `01-media-ground-rules` (only supplied or generated media; no downloading or posting; captions
  are data), `02-media-setup-check` (doctor once per session, relay `fix`), `03-media-paths`
  (`<outputRoot>/<slug>/{vo,clips,review,out}`), `04-media-review` (probe, check rows, the look
  sheet through document.upload and document.read, a canvas.render fallback with no vision, at most
  2 fix rounds), `05-media-delivery` (poster, platform versions, message.send only when asked,
  cleanup) and `06-media-failures` (an action per `errorKind`). Role text: one `info.request` brief
  (at most 4 questions, with tts.file `list_voices` first); a script at about 2.5 words per second
  with a hook of 3 s or less; a markdown storyboard approved before anything is generated; assets
  (tts.file `batch_generate` into `<P>/vo` then one probe, image.generate, text-to-video only,
  instrumental music, cards with media.image); the edit (clip = voice-over line + 0.5 s, the last
  + 1 s; stills through `ffmpeg.make.insert`; voice files joined into one track that becomes
  `audio.replace`, because insert clips are silent and `audio.py` refuses a clip with no audio
  unless `--replace` is given; music ducked under it; `cues.txt` captions; a `project_json`
  skeleton; a dry run, one render, `use_cache` re-renders); and a `## Output` section last with the
  five-line report, because the composer requires the role's output section to close the template.
- **README** (7,354 B): install the skill first, requirements per OS and backend, the isolation
  warning, the Pro image, example prompts, cards, where files land, limits (no progress, renders
  block up to about 30 minutes, cancel orphans a render until D, no mp4 player in the Dashboard),
  what it never does, credits and the trademark note.
- **Evals:** `tests/agents/evals/video-producer.md`, scenarios V1-V10: Reels promo, podcast to
  Shorts, explainer with a logo, slideshow, Docker refusal, FFmpeg missing, "download this YouTube
  video", "post it to TikTok", a 2-hour source, recovery after a timeout.

### 3.10 Multi-family agent tooling

- **Registry** `build/agent-src/families.psd1`: `development` → `build/agent-src/family.psd1`,
  `video` → `build/agent-src/families/video/family.psd1`. Souls and fragments resolve beside each
  family file. No registry → the legacy single family.
- **Family keys** (optional; defaults reproduce the development family): `Id`, `RequiredTag`,
  `Category`, `CreditsSentence` (moved out of `Test-AgentSources.ps1`; absent means no check),
  `ReadmeCaps`, `SkillPolicy` (`Skills`, `ExtraRequiredTools`), `AllowRestrictedMentions`.
- **Video `family.psd1`:** `FamilyMajor 1`, `FamilyVersion 1.0.0`, `SophonCli '^2\.2\.\d+'`,
  `MinSophonVersion 2.2.0`, `Category ai`, `RequiredTag video`, `Lead video-producer`,
  `ReadmeCaps 12288/12288`, `SkillPolicy` ffmpeg-video 1.0.0 with extras document.upload,
  media.image, media.video, music.generate, video.generate, `AllowRestrictedMentions message.send`,
  `Values @{SkillName='ffmpeg-video'}`, the three allowed hosts, the credit
  `kajisho5/ffmpeg-skill (MIT, © 2026 kajisho5)`. No `CommitTrailer`, `PrFooter` or
  `CreditsSentence`.
- **`AgentFamily.psm1`:** `Get-AgentFamilyRegistry`, `Set-AgentFamilyContext`,
  `Get-AgentFamilyContext`, `Get-AgentRosterUnion` (an id in two families is an error).
- **`AgentLint.psm1`:** `SkillToolOwner` in the catalogue; `Get-AgentSkillPolicy`,
  `Get-AgentAllowedSkillTools`; `-AllowedSkillTools` waives `LINT-SKILL` and `TOOLS-PIN-UNKNOWN`
  for SkillPolicy tools only; `-AllowRestrictedMentions` waives `LINT-RESTRICTED` (pinning still
  fails); MAN-REQUIRES with a SkillPolicy requires `skills` (exactly the policy, sorted) then
  `tools` (sorted pins plus extras, each allowed, not core, not restricted); MAN-TAGS reads
  `RequiredTag`; the sibling rule applies only with more than one agent.
- **Scripts:** `Compose-AgentSouls.ps1 -Family` (writes nothing unless every family composes);
  `Test-AgentSources.ps1 -Family` (default: roster union, then one pass per family; new
  MAN-SKILL-VERSION; ATTR rules only for agents whose sources use the attribution values);
  `Build-AgentPackages.ps1 -Family` (an addition to the plan, so the development family can be
  built alone for the SHA gate; the CLI pattern is checked per family).
- **Tests:** `Test-AgentPackages.ps1` uses the roster union and gains section L (19 checks) with a
  fixture family `tests/agents/fixtures/families/media/`; five new compose fixtures
  `families-*`.
- **Regression gate:** the 9 development packages are byte-identical to the pre-change
  `SHA256SUMS`, and `Compose -Check` shows no drift. `sophon dev validate` raised no warning for
  `requires.skills` or skill-tool pins on CLI 2.2.2, so no `AllowedCliWarnings` key was needed.

### 3.11 Tests

| File | Runs where | Covers |
|---|---|---|
| `tests/skills/sandboxsim.py` | helper | fake data folder, the exact preamble, process (`run_process`) and exec (`run_exec`) shapes, resolver replay |
| `tests/skills/test_ffmpeg_video.py` | anywhere, no FFmpeg (144 checks) | surface, bootstrap lint, refusals, discovery, interpreter choice, path policy, parameters, argv parity, failure mapping, compaction, `generate.py --check` |
| `tests/skills/test_ffmpeg_video_fake.py` | Windows and POSIX, fake binaries (22 checks) | FFmpeg 5.1 refusal, dry runs, doctor, a structured `TIMEOUT` with no residue |
| `tests/skills/ffmpeg_video_media.py` | real FFmpeg 6.1+ (SKIP otherwise; `CI_REQUIRE_FFMPEG=1` makes it fail) | doctor ready, every tool's dry run writes nothing, the full chain, timeout, overwrite |
| `tests/skills/run_all_container.py` | `python:3.13-alpine` | `/workspace` → `BACKEND_UNSUPPORTED`, nothing to pip-install |
| `tests/build/Test-SkillLint.ps1` | PowerShell 7 | sections A-D, 13 fixtures |
| `tests/agents/Test-AgentPackages.ps1` | PowerShell 7 (+ CLI for J, K) | A-L |

`ffmpeg_video_fakes.py` (an addition) generates the fake ffmpeg/ffprobe at test time: a `.cmd`
shim plus a Python script on Windows, an executable script on POSIX, so no script file is
committed.

### 3.12 CI

- **`validate.yml`:** Python 3.12; `generate.py --check`; `Test-SkillLint.ps1`; `run_all.py`; the
  agent source checks; path filters include `tests/skills/**` and `tests/build/**`.
- **`ffmpeg-video.yml`** (changes to the skill, its build folder, the skill lint and catalogues,
  its tests, the workflow): `static` (Python 3.10 and 3.13: generator check, unit and fake tests,
  the package build); `py-floor` (a `python:3.8-slim` container, so no newer interpreter exists:
  expects `PYTHON_UNSUPPORTED`); `linux-floor` (Ubuntu 24.04, apt FFmpeg 6.1, Python 3.10: fake
  and media tests with `CI_REQUIRE_FFMPEG=1`); `windows` (Chocolatey FFmpeg with retries, Python
  3.12); `provenance` (`Sync-FfmpegSkill.ps1 -Check` against a fresh clone at the tag and commit
  read from `vendor.lock.json`); `macos` (Homebrew FFmpeg; manual runs only).
- **`ffmpeg-skill-upstream-watch.yml`:** weekly and manual, `contents: read` and `issues: write`;
  keeps one issue listing newer upstream tags with their CHANGELOG headings, closes it when the pin
  is current, never opens a PR.
- `publish.yml` is unchanged; agents stay manual.

### 3.13 Versioning

- **Skill:** 1.0.0. Every re-sync bumps it: patch for an unchanged surface, minor for additions,
  major for removals or renames (which also needs an agent update). `SKILL_VERSION` and the
  manifest version both come from `manifest.base.json`.
- **Agent:** family major 1, starting at 1.0.0; bump on any SOUL or pin change.
  `requires.skills.minVersion` follows the lowest compatible, approved skill version.
- **Publishing order:** the skill first, approved, then the agent ([PUBLISHING.md](../PUBLISHING.md)
  sections 7 and 8).

## 4. Deviations from the approved plan

| Area | Plan | As built | Why |
|---|---|---|---|
| Removed parameters | the plan's list | also `join.list`, `render.cache` (→ `use_cache`), `verify.dry_run`, `overwrite` on probe/check/cropdetect | uncheckable paths; no upstream dry run for verify; read-only tools write nothing |
| Path roles | six roles | plus `in_paths` (`verify.paths`: files or folders); `:LANG` on `caption.srt` is a `lang_suffix` constraint | verify takes both kinds |
| Tool map | the design's example | adds `conditionalRequired`, `constraints`, `writesBesideInput`, `nested`, `removedEverywhere`, `params`, `supportsDryRun`, `byName`; `json` is `flag`/`add`/`native`/`none` | needed for a correct path policy and argv |
| Lock | design 3.6 sketched `covers` and `upstreamTests` | the shared schema only: `upstream`, `files[]`, `generated[]` | one formatter (`generate.py --write-lock`), one schema for the lint |
| Order of checks | preflight before validation | validation and path policy first | errors are useful and testable without FFmpeg |
| Preflight | `which` only | also `-version`, refusing anything older than 6.1 | upstream would fail later and less clearly |
| Doctor without FFmpeg | — | `DEPENDENCY_MISSING` with the `doctor` facts block | the agent still learns `outputRoot` and the fixes |
| Render | project validation | also: every project re-saved absolute and rendered from the copy; `--work` withheld for packs and non-render modes; `stop_after` previews | upstream refuses `--work` for packs; one checked copy is what runs |
| Batch | confine `output_dir`, cap `jobs` | also: script refusals, `{out}` rule, token checks, normalised recipe | steps name arbitrary upstream scripts |
| Cleanup | mtime ≥ START | before/after snapshots, dead-pid locks only | upstream's lock mtime is its deadline minus one hour |
| Policy details | — | `~` expanded; a missing input is `INVALID_ARGUMENT` (`not_found`); failed `check` is `TOOL_FAILED` with rows | clearer to the agent |
| Agent report | five-line report in fragment 05 | in the template's `## Output` section; fragment 05 points to it | the composer requires the role output section last |
| Agent audio | voice-over + music | voice files joined into one `audio.replace`, music ducked under it | insert clips are silent; `audio.py` refuses a clip with no audio unless `--replace` |
| Storyboard | a `canvas.render` table | `content_type: "markdown"` | the table type's JSON shape was not verifiable |
| Agent tooling | `-Family` on compose and sources | also on `Build-AgentPackages.ps1` | to build the development family alone for the SHA gate |
| `CreditsSentence` | default the development sentence | absent means no check | a family that omits it gets no check |
| Lint severities | errors | a Denied built-in name and an Official-tier reserved name are warnings | `github.create_pull_request` is a real skill tool on the agents' Denied list; Official names are publishable with this repo's key |
| CI py-floor | "Python 3.8 only on PATH" | a `python:3.8-slim` container | the bootstrap also searches `/usr/bin`, where Ubuntu runners have Python 3.12 |

## 5. Verification status

Passed on Windows 11 (Python 3.12 and 3.13, pwsh 7.7, Sophon CLI 2.2.2), without FFmpeg:
`Build-MarketplacePackages.ps1 -ValidateOnly` (88 skills), `-Skills ffmpeg-video` build,
`generate.py --check`, `Sync-FfmpegSkill.ps1 -Check` (local clone), `run_all.py` (44 files),
`test_ffmpeg_video.py`, `test_ffmpeg_video_fake.py`, `Test-SkillLint.ps1`, `Compose-AgentSouls.ps1
-Check`, `Test-AgentSources.ps1`, `Build-AgentPackages.ps1 -ValidateOnly` (zero CLI warnings),
`Test-AgentPackages.ps1` (A-L), and the 9 development `SHA256SUMS` byte-identical. A separate
simulation of Sophon's process backend (fake data folder, `<32 hex>` workspace, the exact
preamble) returned one JSON line with exit 0 for contract, doctor, an unknown tool and a
workspace-like cwd.

Not yet run:
- `ffmpeg_video_media.py` against real FFmpeg (CI `linux-floor`, `windows`, `macos`);
- the container case in `python:3.13-alpine`; the POSIX branch of the fake shims; the provenance
  clone from GitHub (CI);
- plan verification steps 3-7: Windows desktop with the process fallback, timeout and cancel
  behaviour, Docker refusal in a real Gateway, the agent end to end, and the marketplace publish
  order.

## 6. Open risks

| Risk | Mitigation or status |
|---|---|
| Skill-home discovery depends on Sophon's undocumented cwd and data-folder layout (verified at `a431e1a64`) | several sources, `FFMPEG_VIDEO_SKILL_ROOT`, an error that lists every candidate; core note item 2 |
| Most desktop users run Docker; the process fallback lowers isolation for every skill | structured refusal, README warnings; core note items 1-4 |
| The process backend has no sandbox | write confinement, protected reads, no raw argv or shell, plans and `watch` refused, offline ASR: defence in depth, not isolation |
| User cancel orphans a render | bounded by D, temp sweep; core note item 7 |
| Python missing or only the Store stub | Sophon fails before `main.py` runs; README troubleshooting |
| Runtime coupling to `build_argv`, `_SPECS`, `run_tool` | pinned vendor; parity tests at every sync |
| Upstream ships about 10 releases a day; `_contract.py` (about 235 KB) nears the 256 KiB preview cap | sync policy with soak time; lint warning; core note item 12 |
| Results echo user text into the injection guard | brief mode by default; captions never echoed |
| `ffmpeg` in a published slug | trademark and non-affiliation notes; fallback slug `video-toolkit` |
| Linux `MAX_ARG_STRLEN` (128 KiB) on `SOPHON_PARAMS` | inline JSON capped at 64 KB; larger inputs as files |
| Unverified Sophon behaviour | `document.read` captioning an uploaded PNG; `video.generate`'s 120 s polling limit and URL-only image input; `tts.file` `output_dir` under `documents/`; the image.generate size enum on non-DALL-E providers; render with `audio.replace` and music together on real FFmpeg (media test). Each has a SOUL fallback and an eval scenario. |
