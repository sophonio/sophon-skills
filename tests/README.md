# Tests

## Skill integration tests (`tests/skills/`)

Offline mock-HTTP integration tests for the skills in `skills/`. No network and no credentials:
`skills/mockhttp.py` patches `urllib` so every HTTP call a skill makes is served from a scripted
response queue while the full request (method, URL, headers, body) is recorded for byte-exact
assertions — auth header composition, token flows, pagination, error surfacing, and
security probes (path-injection quoting, no secret leakage in output).

```bash
# run everything
python tests/skills/run_all.py

# run one skill's tests
python tests/skills/test_okta.py
```

Each `test_<skill>.py` is a plain script (no pytest dependency) that prints `ok/FAIL` lines via
`mockhttp.check()` and exits non-zero on any failure. When adding a skill, add a matching test
file covering: auth exactness, happy-path response shaping, one write-tool body, 401/429 error
paths, and the skill's quirks (see existing files for the pattern).

The sandbox parity smoke (`run_all_container.py`) exercises the unknown-tool and
missing-credential paths inside `python:3.13-alpine` — the image the Sophon runtime actually
uses per tool call. It also checks that `ffmpeg-video`, run from the Docker backend's
`/workspace`, refuses with `BACKEND_UNSUPPORTED` and gives Sophon nothing to pip-install. The three
Sophon Science skills run from `/workspace` too: `science-statistics` answers one `scistat.describe`,
`science-evidence` one `scievidence.canonical_hash` and `science-literature` refuses an empty query
before any request; each answers an unknown tool with `UNKNOWN_TOOL` and gives Sophon nothing to
pip-install:

```bash
docker run --rm --memory=256m -v "<repo>:/repo:ro" \
  python:3.13-alpine python /repo/tests/skills/run_all_container.py
```

### ffmpeg-video (`test_ffmpeg_video*.py`, `ffmpeg_video_media.py`)

`ffmpeg-video` cannot be tested in-process like the HTTP skills: it runs only on Sophon's process
backend and finds its installed folder from the call's working directory. `sandboxsim.py`
reproduces that shape: a throwaway data folder (`skills/installed/...`, `sandbox/workspaces/<32
hex>`, `documents/`), the skill copied in as an installer would, and the exact two-line preamble
Sophon puts in front of `main.py` before running it as `script.py`. Its `resolver_packages()`
replays `PythonImportResolver` (what Sophon would pip-install).

| File | Needs | Covers |
|---|---|---|
| `test_ffmpeg_video.py` | nothing (no FFmpeg) | the 44-tool surface and risk table; bootstrap lint (resolver replay, Python 3.6 syntax, no docstrings or `__future__`); the exact `Unknown tool:` text; the Docker and unknown-backend refusals with no subprocess started; skill-home discovery (data-folder sources, renamed folders, version decoys, a tampered or extra file, a wrong lock); interpreter selection and `PYTHON_UNSUPPORTED`; the path policy (a symlink escape where symlinks can be created, case folding on Windows and macOS, `FFMPEG_VIDEO_WRITE_ROOTS`); parameter coercion and refusals; argv parity of the pre-filled specs against the full upstream contract for all 42 tools; failure mapping, compaction and spill files; one ASCII JSON line on every error path; `generate.py --check` |
| `test_ffmpeg_video_fake.py` | nothing (fake `ffmpeg`/`ffprobe` generated at test time by `ffmpeg_video_fakes.py`) | FFmpeg 5.1 gives `DEPENDENCY_MISSING`; dry runs of cut, fit and export on a fake 7.1 leave the output root unchanged; doctor's wrapper facts; a hanging fake under a 75 s manifest gives a structured `TIMEOUT` with no partial output, lock, temp folder or process left |
| `ffmpeg_video_media.py` | FFmpeg 6.1+ on PATH | doctor ready; a dry run of every tool from `build/ffmpeg-video/smoke-args.json` writes nothing; the chain probe, insert, background, cut, join, caption, audio, render (9:16 `project_json`), check, look, export, verify on lavfi fixtures; a clean timeout; overwrite rules |

`run_all.py` runs the two `test_*` files. The media script is not a `test_*` file, so run it
directly; it prints SKIP and exits 0 without FFmpeg, unless `CI_REQUIRE_FFMPEG=1` is set:

```bash
python tests/skills/test_ffmpeg_video.py
python tests/skills/test_ffmpeg_video_fake.py
CI_REQUIRE_FFMPEG=1 python tests/skills/ffmpeg_video_media.py
```

CI (`.github/workflows/ffmpeg-video.yml`) runs the media script on Ubuntu 24.04 with FFmpeg 6.1
and on Windows, and checks the Python-floor refusal under Python 3.8.

## Skill build-check tests (`tests/build/`)

`Test-SkillLint.ps1` tests `build/SkillLint.psm1` and its wiring into
`build/Build-MarketplacePackages.ps1`. PowerShell 7 only (no Python, no Sophon CLI).

```powershell
pwsh -NoProfile -File tests/build/Test-SkillLint.ps1
```

| Section | What it checks |
|---|---|
| A | every fixture in `tests/build/fixtures/skills/<case>/`, linted on its own, gives exactly its expected errors and warnings |
| B | variants: temporary copies of the fixtures with one change each (declared requirements, a dotfile, a symlink, injection literals, permissions, type, budgets, reserved-name tiers, ignored build output, a collision with another skill) |
| C | the zip mirror on a built fixture archive, then on crafted archives (symlink entry, backslash name, `..`, case-only duplicate, missing manifest, zip-bomb ratio, entry mismatch) |
| D | the build script against a temporary repository of fixture skills, with `-ValidateOnly` and a real build |

The fixtures are `good` (with `lib/` and a locked `vendor/`), `import-hazard`, `docstring-from`,
`future-import`, `name-collision`, `dot-underscore-collision`, `oneOf` (manifest name `one-of`),
`int-enum`, `tool-param`, `bad-lock` (a `.sh` file and a non-UTF-8 file on purpose),
`extra-subfolder`, `reserved-name` and `symlink-zip`. The filesystem-symlink case in B needs
permission to create symlinks (on Windows: Developer Mode or an elevated shell) and reports SKIP
otherwise.

## Agent package tests (`tests/agents/`)

`Test-AgentPackages.ps1` checks the twenty-two agent packages in `agents/` end to end: the development
family 3.0.0, with its twenty development agents (thirteen MIT, seven Apache-2.0) and the Apache-2.0
productivity agent `artifact-creator`, and the video family's `video-producer`. It needs PowerShell 7 and
git; sections J and K also need Sophon CLI 2.2.x on PATH.

```powershell
# sections A-N (several minutes: it builds the packages several times into a temp folder)
pwsh -NoProfile -File tests/agents/Test-AgentPackages.ps1

# sections A-I, L, M and N, no Sophon CLI; prints "CLI CHECKS NOT RUN (-SourceOnly)" in red
pwsh -NoProfile -File tests/agents/Test-AgentPackages.ps1 -SourceOnly

# the source checks on their own (CI runs the -Release line, with Compose-AgentSouls.ps1 -Check): A-I and M per family, N once
pwsh -NoProfile -File build/Test-AgentSources.ps1
pwsh -NoProfile -File build/Test-AgentSources.ps1 -Release   # the release gate: headroom, RoleCap, anchors Pending, DOC-COUNT

# the instruction-test scenario lint (CI runs it with -Release)
pwsh -NoProfile -File tests/agents/evals/Invoke-AgentEvals.ps1 -ValidateOnly

# the Sophon-default digest check (maintainer only, at every family release; needs the sibling sophon repository)
pwsh -NoProfile -File tests/agents/Compare-SophonDigest.ps1 -Require   # -Require: a missing repository fails, not SKIP
```

| Section | What it checks |
|---|---|
| A | roster and layout: `agents/` folders equal the roster union of all families, 5 files each, strict UTF-8, LF, size limits, LICENSE equals the agent's canonical license (root `LICENSE` for MIT, `build/licenses/Apache-2.0.txt` for Apache-2.0); per-agent License/Category/RequiredTags schema cases |
| B | composer: `-Check` on the real tree (SOULs and the development READMEs), every composer fixture against its EXPECT, two byte-identical `-OutDir` composes |
| C | tool-name lint on the packages, plus the lint fixtures; `LINT-SKILL-FRAGMENT` and `LINT-SKILL-UNUSED` |
| D | scanner preflight (P1-P6) on the packages, plus the scan fixtures; fragment rules (at most 4,096 B or its `FragmentCaps` limit, one `## ` heading on line 1), plus a planted-heading case |
| E | byte budgets (SOUL cap per tier, role text against `RoleCap`, TOOLS.md 2,048 B, README 12 KiB, lead 24 KiB) and the headroom table; the 5% and 8% boundaries and `-Release` on a copy with a lowered cap |
| F | manifests against the family contract, plus the manifest fixtures; `MAN-SKILL-VERSION` |
| G | TOOLS.md grammar, the runtime-parser port and pin rules, plus the toolsmd fixtures |
| H | attribution: exact commit trailer and PR footer bytes in every committing agent, none in the read-only ones |
| I | README credits: every Credits key's string, the family sentence where `CreditsSentenceKeys` asks for it, the license sentence |
| J | `sophon --version` matches each family's `SophonCli`; `sophon dev validate --json` per agent: ok, projectType agent, no errors, no warnings |
| K | `build/Build-AgentPackages.ps1` into a temp folder: a decoy package removed; 22 `<id>-<version>.sophon-agent` (each version from its manifest); SHA256SUMS (22 lines, ordinal file-name order, LF, hashes recomputed); zip entries `manifest.json` first then ordinal, equal to the sources byte for byte, stamped 1980-01-01 00:00:00; identical repeat build; a subset build; failure cases (unknown agent, roster mismatch, name mismatch, SOUL drift, a lint error) |
| L | families: a temporary copy with the fixture family `tests/agents/fixtures/families/media/` installed composes, lints and checks on its own (`-Family`); the roster union, and an id in two families fails; the legacy single family without a registry; `SkillPolicy` and the per-agent `Skills` key (absent, all, none, schema); `message.send` named only where `AllowRestrictedMentions` allows it and never pinned; `requires.skills` and `requires.tools` variants against `MAN-REQUIRES`; a skill below `MinVersion` fails `MAN-SKILL-VERSION` |
| M | the Method registry and the instruction tests: the method fixtures (`METHOD-CONTROLLER`, `METHOD-EXCUSES`, `METHOD-REFERENCE`), the skill-use fixtures (`LINT-SKILL-FRAGMENT`, `LINT-SKILL-UNUSED`, `LINT-TOPIC`), the development family's own `Method` key; anchor cases (`ANCHOR-MISSING`, `ANCHOR-GONE`); a smoke run of `Compare-AgentSouls.ps1`; `Compare-SophonDigest.ps1` on the digest fixtures (all found, two planted wrong values, two wrong values inside longer fallback words, SKIP without the sibling repository); the scenario lint's own cases, the transcript scorer, the runner's exec line, package choice, SOUL hash and run-error rule, `Invoke-AgentEvals.ps1 -ValidateOnly` on the real scenario files (and `-Release` failing while a row is `Pending`), every eval fixture and patch as a git workspace, and `-Prepare` on two scenarios |
| N | documents: `DOC-COUNT` from the repository pass of `Test-AgentSources.ps1`, plus a temporary copy with planted counts (number words and digits, qualifiers, a History phrase, and `-Release` turning the warning into an error) |

Each section prints PASS, FAIL or SKIP, and the script exits 1 on any failure. Temporary folders
live under the system temp folder and are removed at the end; nothing in the repository is written.

**Fixtures** (`tests/agents/fixtures/`):

- `families/media/` is a second, fixture family (one agent, a `SkillPolicy` on a fixture
  `media-kit` skill) that section L installs into a temporary copy; it is not in the real registry.
- `compose/<case>/` is a miniature repository (`build/agent-src/` and, where a SOUL composes
  cleanly, `agents/<id>/SOUL.md`) plus an `EXPECT` file. `OK` means `Compose-AgentSouls.ps1
  -RepoRoot <case> -Check` must exit 0; any other text must appear in its output, with exit 1. An
  optional `ARGS` file passes other arguments (the `omit-*` cases of `-Omit`). The `readme-*` cases
  cover README composition: the roster block, credits, drift and hand-written token figures.
  The `trailing-whitespace` case keeps two trailing spaces on purpose: do not let an editor strip them.
- `lint/`, `scan/`, `toolsmd/` and `manifest/` each hold a `cases.psd1` run by
  `Invoke-AgentLintFixtures` in `build/AgentLint.psm1`. A case has a `Name`, `Expect` (`pass` or
  `fail`), the expected `Rule` id for a failure, and its text. `{U+XXXX}` and `{REPEAT:<text>:<n>}`
  expand at run time, so no hidden character, long blob or secret-shaped string is committed.
  Manifest cases are `Replace` pairs applied to a valid `Base` manifest. The scan cases include the
  excuse-row phrase bank: a failing row per "Do not write" form of the CLAUDE.md safe-phrasing table
  (each key name and secret word it lists),
  a passing row per "Write instead" form, and a copy of every shipped `| Excuse | Reality |` table.
- `method/cases.psd1` and `skills/cases.psd1` hold the Method-registry and skill-use cases of section M.
- `anchors/development.psd1` lists the strings the composed SOULs and READMEs must carry, the 2.x
  wording that must be gone, and the anchors removed on purpose.
- `baseline/SHA256SUMS-2.1.0` holds the package hashes of the 2.1.0 baseline; video-producer must still
  match it.
- `evals/` holds the scenario lint's own cases and two recorded stream-json transcripts for the scorer.
- `digest/` holds made-up token files (`tokens/`: `index.css`, `tokens.css`, `motion.css`), a fallback
  `DESIGN.md`, a small fragment and topic whose values all resolve, and `fragment-wrong.md` with two planted
  wrong values (a light text colour and a radius) that `Compare-SophonDigest.ps1 -TokenDir` must report, and
  `fragment-substring.md` with `fallback-whole/DESIGN.md`, where `Inter` and `20 ms` occur only inside
  `pointer` and `120ms` and must still be misses.

**Instruction tests** (`tests/agents/evals/`): the scenarios that show whether the agent text changes what
an agent does, in four automated tiers (acceptance, pressure, design and voice) and the smoke scenarios
the owner runs by hand in an interactive, bound and trusted Sophon CLI before publishing. Their own
fixture projects are in `evals/fixtures/` (`repo-basic`, `repo-bug`, `repo-ui-bare`, `repo-ui-system`,
`repo-agent`) with the delegated briefs in `evals/fixtures/briefs/`. The lint runs offline; a sweep runs
on a throwaway Gateway only, by hand or with the headless runner. See
[`evals/README.md`](agents/evals/README.md) and [`evals/scenarios.md`](agents/evals/scenarios.md). The
video family's ten scenarios (V1-V10) are in [`evals/video-producer.md`](agents/evals/video-producer.md);
they need FFmpeg and the process sandbox.
