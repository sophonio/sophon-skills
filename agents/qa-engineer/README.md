# QA Engineer

Proves a change works by running your project's own commands, and gives a PASS, PASS_WITH_WARNINGS or FAIL verdict you can check line by line.

Part of the Buildersoft development family 2.0.0.

| Agent | Role | Delegates | Changes files | Commits |
|---|---|---|---|---|
| lead-developer | orchestrator: sizes, plans, builds, verifies, commits | yes (depth 1) | yes | yes |
| developer | implementer: tdd / direct / debug | no | yes | yes |
| researcher | codebase and web facts, every claim cited | no | no | no |
| software-architect | blueprint / ADR / greenfield / compare / critique | no | its plan or ADR file only | no |
| code-reviewer | review / refute / re-review / completeness | no | no | no |
| **qa-engineer** (this one) | verification gate, regression checks, tests | no | tests, when asked | yes |
| debugger | root cause first, then a fix when asked | no | fix + regression test, when asked | yes |
| security-reviewer | exploitable vulnerabilities only | no | no | no |
| ui-ux-designer | direction / build / critique / copy / judge | no | UI files | yes |

## When to use

- Run the checks on a branch or a finished plan task before anyone calls it done.
- Prove a bug fix with a test that fails without the fix and passes with it.
- Plan what to test, write or extend tests, or find the missing tests in a diff.
- Check a web page you already have running for structure, names, focus, contrast and overflow.

## Not for

- Finding why something is broken: use **debugger**.
- Fixing production code: use **developer**.
- Judging code by reading it: use **code-reviewer**.
- Security review: use **security-reviewer**.

## How it works

Six modes, picked from your request (or from the brief Lead Developer sends):

- **gate:** lists the claims, writes the proving command for each, runs them fresh and reads the exit code, counts, skips and warnings. Zero tests run, or a test filter that matched nothing, is a FAIL. A flaky test is rerun at most twice and reported.
- **regression:** proves a fix red then green. At the root, when the fix sits in tracked files with nothing else uncommitted, it uses one stash command that runs the test without the fix, restores the fix whatever happens and runs the test again. Otherwise it reverses the fix with an edit and restores it. The red run must fail for the bug's reason.
- **write-tests:** copies the style of neighbouring tests, tests behaviour through public interfaces and mocks only real boundaries. A production bug it finds is reported, not fixed. Medium and Large test work gets a plan file in `docs/plans/`, a `sophon/<slug>` branch and one verified commit per task.
- **strategy:** a risk map (impact and likelihood from 1 to 5, and the cheapest test level that catches each risk), scope, entry and exit criteria, and the commands.
- **gaps:** rates each missing test from 1 to 10 by what it would catch, lists every gap rated 5 or more with the test to add and where it goes, and runs a silent-failure checklist (assertions that cannot fail, empty catch blocks, swallowed errors, ignored exit codes).
- **ui:** checks a page you already have running. It takes a screenshot for you to look at, then runs one in-page check for headings, landmarks, alt text, control names, focus styles, contrast, horizontal overflow and reduced motion. A keyboard walk-through, screen readers and zoom are listed for a person to check.

Every verdict comes with a claim-by-claim table: the claim, the proving command and the result seen in this session.

## Tools and cards you'll see

Sophon shows an approval card for every call at Medium risk or above. For an agent installed from the Marketplace, standing approvals such as accept edits or remembered commands do not apply, so expect these cards:

| A card on every call | No card |
|---|---|
| `os.execute`: every check, the red/green command, branch and commit | `fs.read`, `fs.find`, `fs.search` |
| `browser.act`: navigate, wait and evaluate, at most 6 per page check | `browser.screenshot` |
| `fs.write` and the edit tool: tests and the plan file | `code.git` status, log and stash list |
| `code.git` diff and blame | `todo.write`, `info.request` (a question, not a card) |

- A gate run is usually one or two command cards, because checks are chained into one command where the output stays readable.
- `TOOLS.md` pins `browser.act` and `browser.screenshot` in coding sessions. They need Playwright Chromium on the Gateway host, and `browser.act` opens localhost pages only when `Sophon:Browser:AllowPrivateNetwork` is on. Without it, the agent stops browser work and tells you which setting is missing.

## After installing

- **Effort:** the default suits this agent; no change is needed.
- **Bind and trust the folder:** run `sophon` in the repository, then `/trust`, so your AGENTS.md (test commands, CI rules) and the Git state load.
- **Allowed Medium-risk calls for the session** (the `/permissions` setting) cover only this agent's own non-editing calls at the root, such as `browser.act`, `code.git diff` and GET `http.request`. They never cover a Marketplace agent's edits, commits or shell commands, nor any sub-agent's calls.
- **Tell it your test command** in AGENTS.md under `## Commands`. When it proves a command works, it suggests that line for you.

## Works best with

- **lead-developer** sends it gate, regression and gaps briefs after implementation.
- **developer** fixes the production bugs it reports.
- **debugger** finds the cause when a check fails for a reason nobody understands.
- **ui-ux-designer** judges the visual design it does not.

## Limits

- It never starts servers, watchers or browsers of its own: the ui mode needs a page you already have running.
- The model cannot see screenshots. It receives only "Screenshot taken", so the image is for you, and its own findings come from the page's DOM.
- Tests that hit external services or need secret values are asked about first, or marked "Not verified" with the variable they need.
- On Windows, commands run in cmd or Windows PowerShell 5.1, never bash.
- It runs no sub-agents. Asked for them, or for "ultracode", it says Lead Developer runs multi-agent work and runs the checks itself, one after another.
- In plan mode it proposes the gate as a plan instead of running it.

## What it never does

- Report a result it did not see in this session.
- Weaken a test, loosen an assertion or update snapshots without showing the diff.
- Edit production code unless you ask.
- Push, open a pull request or delete a branch without your answer to the git menu.
- Stash anything except through its one red/green command, which restores the fix itself.

## What's new in 2.0.0

- A full rewrite with six named modes and a strict verdict: zero tests is a FAIL, and every PASS is backed by output from the same session.
- Red/green proof of fixes, rated test gaps, risk-based strategies and page checks through the browser tools.
- It shares one protocol with the rest of the family: sizing, plan files, evidence and one verified commit per task with the trailer `Co-Authored-By: Sophon <noreply@buildersoft.io>`.
- A `TOOLS.md` that pins the browser tools in coding sessions.
- Updating does not change delegation settings.
- New companions in the family: code-reviewer, debugger and security-reviewer. If Lead Developer delegates only to an allow list, add them.

## Credits and license

Workflow patterns adapted, not copied, from obra/superpowers (MIT, © 2025 Jesse Vincent) and Anthropic's Claude Code plugins (feature-dev, pr-review-toolkit, code-review, security-review, frontend-design; Apache-2.0).
Licensed under the MIT License; see LICENSE.
