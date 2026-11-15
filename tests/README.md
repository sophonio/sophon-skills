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
uses per tool call:

```bash
docker run --rm --memory=256m -v "<repo>:/repo:ro" \
  python:3.13-alpine python /repo/tests/skills/run_all_container.py
```

## Agent package tests (`tests/agents/`)

`Test-AgentPackages.ps1` checks the nine development-agent packages in `agents/` end to end. It
needs PowerShell 7; sections J and K also need Sophon CLI 2.2.x on PATH.

```powershell
# sections A-K (about 1-2 minutes: it builds the packages several times into a temp folder)
pwsh -NoProfile -File tests/agents/Test-AgentPackages.ps1

# sections A-I only, no Sophon CLI; prints "CLI CHECKS NOT RUN (-SourceOnly)" in red
pwsh -NoProfile -File tests/agents/Test-AgentPackages.ps1 -SourceOnly

# the A-I source checks on their own (what CI runs, with Compose-AgentSouls.ps1 -Check)
pwsh -NoProfile -File build/Test-AgentSources.ps1
```

| Section | What it checks |
|---|---|
| A | roster and layout: `agents/` folders equal the roster, 5 files each, strict UTF-8, LF, size limits, LICENSE equals the root LICENSE |
| B | composer: `-Check` on the real tree, every composer fixture against its EXPECT, two byte-identical `-OutDir` composes |
| C | tool-name lint on the packages, plus the lint fixtures |
| D | scanner preflight (P1-P6) on the packages, plus the scan fixtures; fragment rules (at most 4,096 B, one `## ` heading on line 1), plus a planted-heading case |
| E | byte budgets (SOUL cap, TOOLS.md 2,048 B, README 12 KiB, lead 24 KiB) and the headroom table |
| F | manifests against the family contract, plus the manifest fixtures |
| G | TOOLS.md grammar, the runtime-parser port and pin rules, plus the toolsmd fixtures |
| H | attribution: exact commit trailer and PR footer bytes in every committing agent, none in the read-only ones |
| I | README credits |
| J | `sophon --version` matches; `sophon dev validate --json` per agent: ok, projectType agent, no errors, no warnings |
| K | `build/Build-AgentPackages.ps1` into a temp folder: a decoy package removed; 9 `<id>-<version>.sophon-agent` (each version from its manifest); SHA256SUMS (9 lines, ordinal file-name order, LF, hashes recomputed); zip entries `manifest.json` first then ordinal, equal to the sources byte for byte, stamped 1980-01-01 00:00:00; identical repeat build; a subset build; failure cases (unknown agent, roster mismatch, name mismatch, SOUL drift, a lint error) |

Each section prints PASS, FAIL or SKIP, and the script exits 1 on any failure. Temporary folders
live under the system temp folder and are removed at the end; nothing in the repository is written.

**Fixtures** (`tests/agents/fixtures/`):

- `compose/<case>/` is a miniature repository (`build/agent-src/` and, where a SOUL composes
  cleanly, `agents/<id>/SOUL.md`) plus an `EXPECT` file. `OK` means `Compose-AgentSouls.ps1
  -RepoRoot <case> -Check` must exit 0; any other text must appear in its output, with exit 1.
  The `trailing-whitespace` case keeps two trailing spaces on purpose: do not let an editor strip them.
- `lint/`, `scan/`, `toolsmd/` and `manifest/` each hold a `cases.psd1` run by
  `Invoke-AgentLintFixtures` in `build/AgentLint.psm1`. A case has a `Name`, `Expect` (`pass` or
  `fail`), the expected `Rule` id for a failure, and its text. `{U+XXXX}` and `{REPEAT:<text>:<n>}`
  expand at run time, so no hidden character, long blob or secret-shaped string is committed.
  Manifest cases are `Replace` pairs applied to a valid `Base` manifest.

**Manual evals** (`tests/agents/evals/`): smoke scenarios the owner runs in an interactive, bound
and trusted Sophon CLI before publishing. See [`evals/README.md`](agents/evals/README.md) and
[`evals/scenarios.md`](agents/evals/scenarios.md).
