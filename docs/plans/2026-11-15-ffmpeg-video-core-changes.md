# Design note: Sophon core changes that would make media skills first-class

**Status:** proposal only. Nothing here is implemented, and this repository contains no Sophon
code. The `ffmpeg-video` skill (design:
[`2026-11-15-ffmpeg-video-design.md`](2026-11-15-ffmpeg-video-design.md)) works around every gap
below from inside the skill. Each item names the gap in Sophon today (checked at `a431e1a64`), the
proposed change, and the hook already present in the skill, so that adopting the change is a small
edit in `skills/ffmpeg-video/` rather than a redesign.

## Summary

| # | Change | Unblocks | Hook in the skill |
|---|---|---|---|
| 1 | Media sandbox image | the Docker backend | `detect_backend()` in `main.py`; preflight in `lib/bridge.py` |
| 2 | Stage the whole skill folder, set `SOPHON_SKILL_DIR` | no cwd inference | `home_candidates()` / `find_home()`, `FFMPEG_VIDEO_SKILL_ROOT` |
| 3 | Read-only input mounts from a schema annotation | Docker inputs | generated path roles in `lib/tool-map.json` |
| 4 | Persistent `/out` mount, `SOPHON_OUTPUT_DIR` | Docker outputs | one output root, `FFMPEG_VIDEO_WRITE_ROOTS` |
| 5 | `_sophon` attachments and model images; a Dashboard video viewer | showing results | `output`/`outputs` paths; the `look` contact sheet |
| 6 | `SOPHON_PROGRESS` stderr protocol | progress during renders | upstream `--progress`, removed by name |
| 7 | Kill the process tree on user cancel | orphaned renders | deadline D, self-cleaning call folder |
| 8 | Per-tool timeouts and a job mode | long renders | per-tool `deadline`, S read from the manifest, `use_cache` |
| 9 | Process-backend Python: `py -3`, a version floor, macOS PATH | interpreter selection | `find_python()` re-exec, `PYTHON_UNSUPPORTED` |
| 10 | Import resolver: honour `requirements: []`, skip docstrings | accidental pip installs | `SKILL-IMPORT` lint, docstring-free bootstrap |
| 11 | `SOPHON_SANDBOX_BACKEND`, `SOPHON_SANDBOX_CAPS`, `sandbox.backends` | backend detection, install warnings | `backend` in every refusal and in doctor |
| 12 | Marketplace review assist for vendored code; a larger preview cap | reviewing the package | `vendor.lock.json`, `THIRD_PARTY_NOTICES.md`, `SKILL-LOCK` warning |
| 13 | Skill v2, gated by `sophon.minVersion` | dropping the workarounds | generated constants, `manifest.base.json` |

Items 1-4 belong together: only with all four can a media skill run under Docker. Items 7 and 10
are small bug fixes worth doing on their own.

## 1. A media sandbox image

**Today.** The Docker backend runs every Python skill on `python:3.13-alpine`
(`DockerSandboxOrchestrator.cs:221`), which has no FFmpeg, with `PidsLimit = 128` (`:128`). The
skill therefore refuses Docker outright (`BACKEND_UNSUPPORTED`).

**Proposal.** An allowlisted `sandbox.image: "media"` in the manifest, mapped by the Gateway to an
image pinned by digest: glibc Python 3.12 or 3.13, FFmpeg 7.x with libass, freetype, fribidi,
harfbuzz, zimg and vidstab, fontconfig, DejaVu and Noto CJK fonts. Raise `PidsLimit` for it (x264
and its filters start many threads, and threads count toward the limit). Skills cannot name
arbitrary images.

**Hook.** Backend detection is one function, `detect_backend()` in `main.py`; the refusal is one
message. The bridge already preflights ffmpeg and ffprobe on PATH (version 6.1 or later) and
honours `FFMPEG_VIDEO_FFMPEG_DIR`, so inside such an image it needs no change beyond accepting the
backend, once items 2-4 give it its files.

## 2. Stage the whole skill folder and set `SOPHON_SKILL_DIR`

**Today.** Only the entrypoint text is written, as `script.py` behind a preamble
(`SandboxedTool.cs:85-92`), into a throwaway `<dataDir>/sandbox/workspaces/<guid>`
(`ProcessSandboxOrchestrator.cs:33-35`; `Program.cs:1215`). A skill with `lib/` or `vendor/` has
to infer its installed folder from the cwd, which works only on the process backend and depends on
an undocumented layout.

**Proposal.** Mount (Docker: read-only at `/skill`) or point to (process: the installed folder) the
whole skill, and set `SOPHON_SKILL_DIR` on both backends.

**Hook.** Discovery is `home_candidates()` and `find_home()` in `main.py`. The first candidate is
already an explicit variable (`FFMPEG_VIDEO_SKILL_ROOT`), and every candidate is verified by
manifest name, version and the sha256 of `vendor.lock.json`. Reading `SOPHON_SKILL_DIR` is one more
line ahead of it; the cwd inference and the five data-folder sources then become a fallback for
older Sophon versions.

## 3. Read-only input mounts from a schema annotation

**Today.** No host path is mounted into the container; `request.FileSystemPaths` is set
(`SandboxedTool.cs:182`) but never read by either orchestrator. User media cannot reach a
Docker-run skill.

**Proposal.** A parameter annotation `x-sophon-path: "in" | "in-dir"`. The Gateway checks the value
with its `PathValidator` (the same rules as the fs tools), mounts it read-only at `/in/<n>`, and
rewrites the parameter to the mounted path.

**Hook.** Every path parameter already has a generated role in `lib/tool-map.json` (`in_file`,
`in_files`, `in_dir`, `in_paths`), derived from `build/ffmpeg-video/policy.json`. The generator can
emit the annotation into `tools[]` from the same data. Paths nested in render projects and batch
recipes (the `nested` rules) still need the bridge's own checks, or a project-file mount.

## 4. A persistent output mount and `SOPHON_OUTPUT_DIR`

**Today.** The Docker workspace is read-only for Python and deleted after the call
(`DockerSandboxOrchestrator.cs:104,112,224`); on the process backend it is deleted in `finally`
(`ProcessSandboxOrchestrator.cs:117`). Nothing a Docker-run skill writes survives.

**Proposal.** `sandbox.outputs` mounts `<dataDir>/documents/video/<skill>` read-write at `/out`,
sets `SOPHON_OUTPUT_DIR`, and maps paths in the result back to host paths.

**Hook.** The skill already writes only under one output root, `<dataDir>/documents/video/ffmpeg-video`
(`OUTPUT_PARTS` in `lib/bridge.py`), plus the operator's `FFMPEG_VIDEO_WRITE_ROOTS`. Every output
parameter has an `out_file`, `out_side_file` or `out_dir` role. Taking the root from
`SOPHON_OUTPUT_DIR` when it is set is a one-place change.

## 5. Attachments and model images from skills; a video viewer

**Today.** A skill returns stdout text only, never `Attachments` (`SandboxedTool.cs:193-196`). The
Dashboard viewer has no video format (`viewer/format.ts:20-69`, `types.ts:1-3`), so an mp4 renders
as a download card. The agent reviews a contact sheet by passing it through `document.upload` and
`document.read`.

**Proposal.** A reserved `_sophon` key in the skill's JSON result: `attachments` and `modelImages`
(file paths, restricted to the output mount or root) become `ToolResult.Attachments` and model
image parts. Add a Dashboard `video` format with `<video>` playback, and an mp4 extractor for the
documents library.

**Hook.** Every success envelope carries the absolute `output` and `outputs`; `ffmpeg.inspect.look`
writes a PNG contact sheet. The bridge can add `_sophon.attachments` from `outputs` and
`_sophon.modelImages` from look's sheet, and the agent can then drop its document.upload step.

## 6. Progress events

**Today.** No progress channel exists for skills; a render blocks for up to 30 minutes with no
sign of life.

**Proposal.** A line protocol on stderr, `SOPHON_PROGRESS {json}`, streamed to the client as
`tool.output` events while the call runs.

**Hook.** Upstream already has `--progress` (JSON progress lines from the encoder). The wrapper
removes it by name ("progress events are not supported by Sophon skills" in `policy.json`
`dropEverywhere`). With the protocol, the bridge passes `--progress` and translates each line.

## 7. Kill the process tree on user cancel

**Today.** On timeout the process tree is killed, but the catch filter
`when (!ct.IsCancellationRequested)` (`ProcessSandboxOrchestrator.cs:98`) lets a user cancel
through without `KillProcessSafe`, so the render keeps running, orphaned. Docker needs the same
fix.

**Proposal.** Kill the tree on any cancellation, not only on timeout.

**Hook.** The skill bounds an orphan anyway: everything stops by the wrapper deadline D = S − 60;
the call works in `<outputRoot>/.tmp/<uuid>` rather than Sophon's workspace, and stale `.tmp`
folders are swept by the next call. Nothing changes in the skill when this lands; the README's
"cancel does not stop a render" limit goes away.

## 8. Per-tool timeouts and a job mode

**Today.** One `sandbox.timeoutSeconds` covers every tool of a skill (default 30 s, no upper
clamp, `SkillManifestParser.cs:369`). The skill sets 1800 s, so a 1 s probe and a 25-minute render
share a limit, and a render longer than that cannot run at all.

**Proposal.** A per-tool `timeoutSeconds`, and for long work a start/poll job mode (or TaskLedger
entries skills can open and update), so a render can outlive one call.

**Hook.** The tool map already carries a per-tool `deadline` (probe 120, cropdetect 300, look 300,
check 900, doctor 120, contract 60), and the bridge reads S from the installed manifest at run
time. Renders are already restartable: `use_cache` reuses finished stages, which is what a job
mode's retry would rely on.

## 9. Python on the process backend

**Today.** The process backend runs whatever `python` the Gateway's PATH finds. On Windows that may
be the Store alias; on macOS a launchd Gateway sees a minimal PATH and Apple's Python 3.9.

**Proposal.** Prefer the `py -3` launcher on Windows, probe the version, honour a manifest
`python` floor (`"python": ">=3.10"`), and give the macOS service plist a PATH that includes
`/opt/homebrew/bin` and `/usr/local/bin`.

**Hook.** `main.py` parses as Python 3.6 and finds a 3.10+ interpreter itself (`find_python()`:
`FFMPEG_VIDEO_PYTHON`, `py -3`, `python3.14` … `python3.10` on PATH and in the well-known folders),
re-executing `lib/bridge.py --stdin`; with none it returns `PYTHON_UNSUPPORTED` listing what it
tried. With a floor in core, the re-exec becomes dead code for new Sophon versions.

## 10. The import resolver

**Today.** With `requirements` empty, `PythonImportResolver` regex-scans every line with
`^(?:import|from)\s+(\w+)` after trimming (`PythonImportResolver.cs:10,21-33`), docstrings and
string literals included, and pip-installs every non-stdlib name. A docstring line "from Profile
Settings" in one of this repository's skills made Sophon install a package called `Profile`.

**Proposal.** Treat an explicit `"requirements": []` as "install nothing", and skip docstrings and
string literals (or parse with a tokenizer).

**Hook.** The repository lints for it (`SKILL-IMPORT` in `build/SkillLint.psm1`, replaying the
resolver against `build/catalog/sandbox-python.psd1`); the skill's bootstrap has no docstrings and
imports only resolver-stdlib modules, and its manifest says `requirements: []`. Nothing changes
in the skill; the lint can relax for Sophon versions with the fix.

## 11. Backend and capability variables

**Today.** A skill cannot ask which backend runs it. The skill infers it from the cwd: `/workspace`
is Docker, `…/sandbox/workspaces/<32 hex>` is the process backend, anything else is unknown.
`/.dockerenv` is useless, because the Pro prebuilt Gateway runs in a container on the process
backend.

**Proposal.** Set `SOPHON_SANDBOX_BACKEND` (`process` | `docker`) and `SOPHON_SANDBOX_CAPS` (for
example `ffmpeg,host-paths`) for every call, and accept a manifest `sandbox.backends: ["process"]`
so the installer can warn before install rather than at the first call.

**Hook.** Every refusal and the doctor report already carry a `backend` field. `detect_backend()`
reads the variable first when present and keeps the cwd rule as a fallback.

## 12. Marketplace review of vendored code

**Today.** The marketplace runs no content scanner on skill packages, and the moderator preview
truncates files over 256 KiB. The vendored `scripts/_contract.py` is about 235 KB, close to that
cap; every re-sync puts a few thousand lines of third-party code in front of a reviewer.

**Proposal.** A review assist that reads a `vendor.lock.json`: show the upstream repository, tag
and commit, verify the hashes, and show the diff against the previous approved version, so a
reviewer reads what changed upstream and the first-party wrapper in full. Raise the preview cap
above 256 KiB for text files.

**Hook.** The lock already records `upstream.{repo, tag, commit, version}` and a sha256 and size per
file, and `THIRD_PARTY_NOTICES.md` names the tag and commit. The repository warns on any vendored
file over 256 KiB (`SKILL-LOCK`) and re-derives the tree from the tag in CI (`Sync-FfmpegSkill.ps1
-Check`). The policy is in [`docs/VENDORING.md`](../VENDORING.md).

## 13. Migration to skill v2

**Proposal.** Once items 1-4, 9 and 11 ship, publish an `ffmpeg-video` 2.0.0 that requires them
through `sophon.minVersion`: it reads `SOPHON_SKILL_DIR`, `SOPHON_OUTPUT_DIR` and
`SOPHON_SANDBOX_BACKEND`, runs under Docker on the media image, and drops the cwd inference, the
data-folder search, the interpreter re-exec and the Docker refusal. Version 1.x stays on the
marketplace for older Sophon versions.

**Hook.** The version and the generated constants come from `build/ffmpeg-video/manifest.base.json`
through `generate.py`; the tool names, parameters and path roles do not change, so the Video
Producer agent keeps working with a raised `SkillPolicy.MinVersion` and no SOUL change.
