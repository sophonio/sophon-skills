# Developer

Implements one scoped code change in a bound repository, test first, and reports exactly what it proved.

Part of the Buildersoft development family {{= FamilyVersion}}.

{{# roster}}

## When to use

- A feature slice, a fix whose cause is known, or a targeted refactor.
- One task from an approved plan. Lead Developer hands these over as sub-agent briefs.
- Small and medium changes you want done directly, with the failing test written first where the project has tests.

## Not for

- An unknown root cause: **debugger**. Choosing between designs: **software-architect**. Reviewing a change: **code-reviewer**.
- UI components checked in a browser: **frontend-developer**. Releases: **release-engineer**. Agent instructions: **agent-engineer**.
- Multi-agent work ("ultracode", parallel agents): **lead-developer**.

## How it works

- **Sizes the request first.** Trivial work (at most 2 files and 40 lines, one obvious approach, no interface, schema, dependency, build, CI or security change) is done directly. Medium and Large work gets a plan file in `docs/plans/` that you approve, a `sophon/<slug>` branch and one verified commit per task.
- **Discovery:** it reads first, and asks only when something is open (why, for whom, what done looks like), one question per message, then plays its understanding back and lets you pick between real approaches. "just build it" skips the questions; its guesses become `Assumption:` lines, and approvals are still asked.
- **Reads before it edits:** every file it will touch and its nearest test. Build and test commands come from your project instructions (AGENTS.md) first, then the README, package scripts and CI files.
- **Plan file:** header lines `Spec:`, `Discovery:` and `Voice:`, sections Global constraints and Review focus. Before the last commit it re-reads the whole change against them; minor points are parked.
- **tdd mode** (the default when the project has tests and behaviour changes): one failing test, run alone to check it fails for the expected reason, then the least code that passes and the task's whole check. Code written before its test is deleted and rewritten from the test.
- **direct mode** for docs, config, renames, generated code or no test setup, named in one line.
- **debug mode** when its own work fails unexpectedly: the smallest reproduction, one hypothesis at a time with its prediction, one state line per round. After three falsified hypotheses it stops and recommends Debugger.
- **Before it adds** a catch, default or retry, it lists the errors it could hide; outside tests no mock or sample value stands in for a failed call. A layer with one implementation becomes direct code.
- **Library facts** come from the version in your manifest or lockfile and a source for that version, cited.
- **Review findings** are checked against the code first; a wrong one is answered with evidence, the rest are fixed one at a time.
- **Halts and asks** before a new dependency, a project, lock, CI, hook or script file nobody named, an ambiguity that changes behaviour, two valid architectures, or anything destructive.
- **Evidence or nothing:** it claims a result only from command output seen in the same turn and quotes the proving line; otherwise "not verified".
- **Git:** inside a plan it commits each verified task with the trailer `{{= CommitTrailer}}`, then asks: Push + open PR, Merge into `<base>` locally, or Keep local. Discard runs only when you ask, after it lists what would be lost and asks again. Outside a plan it commits only when you ask.
- **Voice:** plain sentences; "terse" or "caveman" for short replies, "normal" to switch back.

## Tools and cards you'll see

Sophon shows a card for every call at Medium risk or above. Standing approvals such as accept edits do not apply to a Marketplace agent:

| A card on every call | No card |
|---|---|
| `fs.write`, the edit tool, `fs.move`, `fs.delete` | `fs.read`, `fs.list`, `fs.find`, `fs.search` |
| `os.execute`: every build, test, branch and commit command | `code.git` status, log, branch list and remote |
| `http.request` | `todo.write`, `memory.search`, `memory.write`, `web.search` |
| `plan.propose` (the plan card, in plan mode only) | `info.request` (a question, not a card) |

- `code.git` diff and blame may raise a card; in a trusted workspace on the Gateway we tested they raised none.
- A plan task costs about the files edited plus 3 cards: the red run, the plan edit and one verify-and-commit command. A medium plan of 4 tasks is about 28 cards. Push + open PR adds 2, Merge locally 1.
- `TOOLS.md` pins `fs.move` and `fs.delete` in coding sessions, so renames and deletions show a path-specific card instead of a shell command.

## After installing

- **Install:** `sophon agents install developer`, with `--allow-delegation-from lead-developer` if Lead Developer should brief it. The default effort suits it.
- **Bind and trust the folder:** run `sophon` in the repository, then `/trust`, so your AGENTS.md and the Git state load. Unbound, it reads and plans, and edits only if you ask again.
- **Allowed Medium-risk calls for the session** (`/permissions`) cover only its own non-editing calls at the root, such as `code.git diff`; never a Marketplace agent's edits, commits or shell commands, nor a sub-agent's calls.
- **Git identity:** commits authored "Sophon Agent <sophon@localhost>" mean git has no name or email; it tells you.
- **Pull requests:** sign in once in your own terminal with `gh auth login` (`gh auth setup-git` for HTTPS pushes). The agent never asks for a token.

## Works best with

- **lead-developer** sends it one plan task at a time and verifies and commits the result itself.
- **debugger** takes over when the cause is unknown. **qa-engineer** gives an independent PASS or FAIL. **code-reviewer** reviews the diff before you merge.

## Limits

- Nothing runs in the background: no servers, watchers or REPLs. Long runs time out at 1800 seconds at most.
- On Windows, commands run in cmd or Windows PowerShell 5.1, never bash.
- Push and pull requests run through `os.execute`, which always shows a card.
- It runs no sub-agents: asked for them or for "ultracode", it says Lead Developer runs multi-agent work and does the task itself.
- In plan mode it stays read-only and proposes the plan with `plan.propose`. The Personal-edition Dashboard cannot approve a plan card: use the CLI, or choose Keep planning and type GO.

## What it never does

- Push, open a pull request, merge or delete a branch without your answer.
- Commit work that has not passed its check, or weaken a check to pass it.
- Amend, rebase, reset, clean, force-push, push to the default branch or change git config, unless you ask for that exact operation.
- Change project files through the shell, or edit outside the workspace.
- Store or repeat tokens, keys or other secret values.

## What's new in 3.0.0

- Discovery before a plan; the new plan lines and a whole-change review before the last commit.
- Merge into `<base>` locally joins the finish menu; Discard only on request.
- Checks before adding error handling or a layer; library facts from the version in use; findings checked before fixing.
- A terse voice on request. Not for releases or agent instructions, which have their own agents.

{{> readme/80-upgrade-3}}

{{> readme/70-reference-skill}}

## Credits and license

Ideas re-expressed in our own words also come from JuliusBrussee/caveman (Apache-2.0, © 2026 Julius Brussee); mattpocock/skills (MIT, © 2026 Matt Pocock); and addyosmani/agent-skills (MIT, © 2025 Addy Osmani).

Workflow patterns adapted, not copied, from obra/superpowers (MIT, © 2025 Jesse Vincent) and Anthropic's Claude Code plugins (feature-dev, pr-review-toolkit, code-review, frontend-design; Apache-2.0).
Licensed under the MIT License; see LICENSE.
