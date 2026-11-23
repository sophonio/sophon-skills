# Developer

Implements one scoped code change in a bound repository, test first, and reports exactly what it proved.

Part of the Buildersoft development family 2.1.0.

| Agent | Role | Delegates | Changes files | Commits |
|---|---|---|---|---|
| lead-developer | orchestrator: sizes, plans, builds, verifies, commits | yes (depth 1) | yes | yes |
| **developer** (this one) | implementer: tdd / direct / debug | no | yes | yes |
| researcher | codebase and web facts, every claim cited | no | no | no |
| software-architect | blueprint / ADR / greenfield / compare / critique | no | its plan or ADR file only | no |
| code-reviewer | review / refute / re-review / completeness | no | no | no |
| qa-engineer | verification gate, regression checks, tests | no | tests, when asked | yes |
| debugger | root cause first, then a fix when asked | no | fix + regression test, when asked | yes |
| security-reviewer | exploitable vulnerabilities only | no | no | no |
| ui-ux-designer | direction / build / critique / copy / judge | no | UI presentation files | yes |
| frontend-developer | UI implementer: component / direct / artifact / perf | no | yes | yes |
| design-system-engineer | audit / tokens / theme / playground / brand-check | no | tokens, themes, components | yes |
| visual-designer | concept / art / generative / image / motion | no | asset files | yes |
| e2e-test-engineer | browser end-to-end tests: write / visual / flake | no | e2e tests | yes |
| accessibility-reviewer | WCAG 2.2 AA: audit / review | no | no | no |
| mcp-integration-engineer | MCP servers: design / build / evals | no | yes | yes |
| technical-writer | documentation: draft / edit / reader-test | no | documentation files | yes |
## When to use

- A feature slice, a fix whose cause is known, or a targeted refactor.
- One task from an approved plan. Lead Developer hands these over as sub-agent briefs.
- Small and medium changes you want done directly, with the failing test written first where the project has tests.

## Not for

- An unknown root cause: use **debugger**.
- Choosing between designs: use **software-architect**.
- Reviewing a change: use **code-reviewer**.
- Multi-agent work ("ultracode", parallel agents): use **lead-developer**.

## How it works

- **Sizes the request first.** Trivial work (at most 2 files and 40 lines, one obvious approach, no interface, schema, dependency, build, CI or security change) is done directly, without a plan. Medium and Large work gets a plan file in `docs/plans/` that you approve, a `sophon/<slug>` branch and one verified commit per task.
- **Reads before it edits:** every file it will touch and its nearest test. It takes build and test commands from your project instructions (AGENTS.md) first, then the README, package scripts and CI files.
- **tdd mode** (the default when the project has tests and behaviour changes): one failing test, run alone to check it fails for the expected reason, then the minimal code, green, a tidy-up inside the change and the relevant suite.
- **direct mode** for docs, config, renames and generated code. It names the exception rather than claim a test covers it.
- **debug mode** when its own work fails unexpectedly: the full error, the smallest reproduction, one hypothesis at a time with its prediction written down, and one state line per round. After three falsified hypotheses it stops and recommends Debugger.
- **Halts and asks** before a new dependency, an unnamed project, lock, CI, hook or script file, an ambiguity that changes behaviour, a choice between two valid architectures, or anything destructive.
- **Evidence or nothing:** it claims a result only from command output it saw in the same turn and quotes the proving line; otherwise it says "not verified".
- **Git:** inside a plan it commits each verified task with the trailer `Co-Authored-By: Sophon <noreply@buildersoft.io>`, then asks Push + open PR, Keep local or Discard. Outside a plan it commits only when you ask.

## Tools and cards you'll see

Sophon shows an approval card for every call at Medium risk or above. For an agent installed from the Marketplace, standing approvals such as accept edits or remembered commands do not apply, so expect these cards:

| A card on every call | No card |
|---|---|
| `fs.write`, the edit tool, `fs.move`, `fs.delete` | `fs.read`, `fs.list`, `fs.find`, `fs.search` |
| `os.execute`: every build, test, branch and commit command | `code.git` status, log, branch list and remote |
| `code.git` diff and blame | `todo.write`, `memory.search`, `memory.write`, `web.search` |
| `plan.propose` (the plan card, in plan mode only) | `info.request` (a question, not a card) |

- A plan task costs about the number of files edited plus 3 cards: the red test run, the plan tick and one verify-and-commit command. A medium plan of 4 tasks is about 28 cards.
- `TOOLS.md` pins `fs.move` and `fs.delete` in coding sessions, so renames and deletions show a path-specific card instead of a shell command.

## After installing

- **Effort:** the default suits this agent; no change is needed.
- **Bind and trust the folder:** run `sophon` in the repository, then `/trust`, so your AGENTS.md and the Git state load. In an unbound chat it reads and plans, and edits only if you ask again after it explains binding.
- **Allowed Medium-risk calls for the session** (the `/permissions` setting) cover only this agent's own non-editing calls at the root, such as `code.git diff` and GET `http.request`. They never cover a Marketplace agent's edits, commits or shell commands, nor any sub-agent's calls.
- **Git identity:** configure your name and email in git. Commits authored "Sophon Agent <sophon@localhost>" mean git has neither, and the agent tells you so.
- **Pull requests:** sign in once in your own terminal with `gh auth login` (check with `gh auth status`; run `gh auth setup-git` for HTTPS pushes). The agent never asks for a token.

## Works best with

- **lead-developer** sends it one plan task at a time and verifies and commits the result itself.
- **debugger** takes over when the cause is unknown, or after debug mode stops at three falsified hypotheses.
- **qa-engineer** gives an independent PASS or FAIL on the branch.
- **code-reviewer** reviews the diff before you merge.

## Limits

- Nothing runs in the background: it never starts servers, watchers or REPLs. Long runs use a timeout of up to 1800 seconds.
- On Windows, commands run in cmd or Windows PowerShell 5.1, never bash.
- `code.git` cannot push, stage selectively or open pull requests, so those steps run through `os.execute`, which always shows a card.
- It runs no sub-agents. Asked for them, or for "ultracode", it says Lead Developer runs multi-agent work and does the task itself. At Large size it says so once, then continues if you want.
- In plan mode it stays read-only and proposes the plan with `plan.propose`. The Personal-edition Dashboard cannot approve a plan card: use the CLI, or choose Keep planning and type GO.

## What it never does

- Push, open a pull request or delete a branch without your answer to the git menu.
- Commit work that has not passed its check.
- Amend, rebase, reset, clean, force-push, push to the default branch or change git config, unless you ask for that exact operation.
- Create or change project files through the shell, or edit outside the workspace.
- Store or repeat tokens, keys or other secret values.

## What's new in 2.1.0

- Seven companions joined the family: `frontend-developer`, `design-system-engineer`, `visual-designer`, `e2e-test-engineer`, `accessibility-reviewer`, `mcp-integration-engineer` and `technical-writer`. They are licensed Apache-2.0; this agent stays MIT. Add the ones you install to an existing Lead Developer allow-list.
- Hands UI components that need checking in a browser to `frontend-developer`.

## What's new in 2.0.0

- A full rewrite. It now shares one protocol with the rest of the family: sizing, plan files in `docs/plans/`, evidence from real commands, one verified commit per task and the end-of-task git menu.
- Three named modes: tdd, direct and debug, with a hard stop after three falsified hypotheses.
- A `TOOLS.md` that pins `fs.move` and `fs.delete` in coding sessions.
- Updating does not change delegation settings.
- New companions in the family: code-reviewer, debugger and security-reviewer. If Lead Developer delegates only to an allow list, add them.

## Credits and license

Workflow patterns adapted, not copied, from obra/superpowers (MIT, © 2025 Jesse Vincent) and Anthropic's Claude Code plugins (feature-dev, pr-review-toolkit, code-review, security-review, frontend-design; Apache-2.0).
Licensed under the MIT License; see LICENSE.
