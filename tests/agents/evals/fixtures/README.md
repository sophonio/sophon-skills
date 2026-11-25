# Eval fixtures

Small projects the instruction tests run in. None of them is a package, and none mentions these tests
or an agent of the development family; the scenario lint checks the second rule.

Each fixture is a folder:

- `fixture.psd1`: a description, the project's test command, an optional `Base` (another fixture whose files
  are copied first) and `Patches`, each with its reason. A patch with `Commit` (and optionally `Branch`) is
  applied as a commit on that branch; any other patch is applied and left uncommitted. A patch with `Remote`
  first pushes the current branch, with upstream tracking, to a new bare repository beside the workspace
  (`<workspace>-<Remote>.git`), so its own commit is one ahead of that remote.
- `files/`: the project as plain files. A run copies them to a temporary folder and makes a git repository
  with one commit.
- `patches/<name>.patch`: a `git apply` patch against `files/` (after `Base`).

| Fixture | What it is |
|---|---|
| `repo-basic` | A Python CLI and reports page over CSV files; the slugify defect, the "Helo" typo, the empty-file crash, the version in two files, a lockfile; a 1.4.0 release commit ahead of a local bare origin |
| `repo-bug` | Python weekly totals that move a late-Sunday entry into the next week, two calls from the report; patches for review, a sibling guard, security handlers, a server-side fetch and a finished branch |
| `repo-ui-bare` | A Node web app with unstyled markup and no design system; a landing page with accessibility defects; a failing Playwright assertion |
| `repo-ui-system` | `repo-ui-bare` plus `DESIGN.md`, a token file (a serif face, an orange primary) and the AGENTS.md design-rules line |
| `repo-agent` | One made-up agent package (`agents/helper/`) and an `evals/` folder beside it |

`briefs/` holds delegated first messages. Each starts with the runtime's own sub-agent opening, copied
from `BuildDelegatedPrompt` in `src/Sophon.Core/Agents/SubAgentOrchestrator.cs` of the Sophon source at
commit a431e1a64 (CLI 2.2.2), followed by a brief in the 2.1.0 Lead Developer format.
