# QA Engineer

Proves a change works by running your project's own commands, and gives a PASS, PASS_WITH_WARNINGS or FAIL verdict you can check line by line.

Part of the Buildersoft development family {{= FamilyVersion}}.

{{# roster}}

## When to use

- Run the checks on a branch or a finished plan task before anyone calls it done.
- Prove a bug fix with a test that fails without the fix and passes with it.
- Plan what to test, write or extend tests, or find the missing tests in a diff.
- Check a web page you already have running for structure, names, focus, contrast and overflow.
- Measure whether something got faster, or probe whether the tests notice a broken line.

## Not for

- Finding why something is broken: **debugger**. Fixing production code: **developer**.
- Judging code by reading it: **code-reviewer**. Security review: **security-reviewer**.
- Browser end-to-end suites: **e2e-test-engineer**. A WCAG audit: **accessibility-reviewer**.
- Acceptance against requirements: **product-owner**. Shipping: **release-engineer**.

## How it works

Eight modes, picked from your request (or from the brief Lead Developer sends). The implementer's report is a claim to test, never evidence.

- **gate:** lists the claims goal-backward: what must be true for you when the work is done, what must exist, and what must be wired (registered, called, reachable). A ticked task or a green unit test shows a part exists, not that the goal is met. It writes the proving command for each claim, runs them fresh and reads the exit code, counts, skips and warnings. Zero tests run, or a filter that matched nothing, is a FAIL. A flaky test is rerun at most twice and reported.
- **regression:** proves a fix red then green. At the root, when the fix sits in tracked files with nothing else uncommitted, one stash command runs the test without the fix, restores the fix whatever happens and runs it again. Otherwise it reverses the fix with an edit and restores it. The red run must fail for the bug's reason.
- **write-tests:** copies the style of neighbouring tests, tests behaviour through public interfaces and mocks only real boundaries. A production bug it finds is reported, not fixed. Medium and Large test work gets a plan file in `docs/plans/`, a `sophon/<slug>` branch and one verified commit per task with the trailer `{{= CommitTrailer}}`, then the finish menu: Push + open PR, Merge into `<base>` locally, or Keep local. Discard runs only when you ask, after a second confirmation.
- **strategy:** a risk map (impact and likelihood from 1 to 5, and the cheapest test level that catches each risk), scope, entry and exit criteria, and the commands.
- **gaps:** rates each missing test from 1 to 10 by what it would catch, lists every gap rated 5 or more with the test to add and where it goes, and runs a silent-failure checklist.
- **ui:** checks a page you already have running: a screenshot for you to look at, then one in-page check for headings, landmarks, alt text, control names, focus styles, contrast, overflow and reduced motion. Keyboard, screen-reader and zoom checks are listed for a person.
- **perf** (only when asked whether something got faster): fixes the operation, input and metric, runs the same command before and after, the median of 5 runs each, and reports both. Without both measurements it says "not verified".
- **probe** (only when you ask for it by name): on committed code, inverts one condition the change added with one edit, runs the tests that should notice, restores the line whatever happened and confirms the file is clean. A run that stays green names the missing test. At most 3 probes, never committed.

Every verdict comes with a claim-by-claim table: the claim, the proving command and the result seen in this session. Replies are plain sentences; say "terse" or "caveman" for short ones and "normal" to switch back.

## Tools and cards you'll see

Sophon shows a card for every call at Medium risk or above. Standing approvals such as accept edits do not apply to a Marketplace agent:

| A card on every call | No card |
|---|---|
| `os.execute`: every check, the red/green command, branch and commit | `fs.read`, `fs.find`, `fs.search` |
| `browser.act`: navigate, wait and evaluate, at most 6 per page check | `browser.screenshot` |
| `fs.write` and the edit tool: tests, the plan file, a probe and its restore | `code.git` status, log and stash list |
| `http.request` | `todo.write`, `info.request` (a question, not a card) |

- `code.git` diff and blame may raise a card; in a trusted workspace on the Gateway we tested they raised none.
- A gate run is usually one or two command cards, because checks are chained into one command where the output stays readable. A probe costs 2 edit cards and 1 command card.
- `TOOLS.md` pins `browser.act` and `browser.screenshot` in coding sessions. They need Playwright Chromium on the Gateway host, and `browser.act` opens localhost pages only when `Sophon:Browser:AllowPrivateNetwork` is on. Without it, the agent stops browser work and names the setting.

## After installing

- **Install:** `sophon agents install qa-engineer`, with `--allow-delegation-from lead-developer` if Lead Developer should brief it. The default effort suits it.
- **Bind and trust the folder:** run `sophon` in the repository, then `/trust`, so your AGENTS.md (test commands, CI rules) and the Git state load.
- **Allowed Medium-risk calls for the session** (`/permissions`) cover only its own non-editing calls at the root, such as `browser.act` and `code.git diff`; never a Marketplace agent's edits, commits or shell commands, nor a sub-agent's calls.
- **Tell it your test command** in AGENTS.md under `## Commands`. When it proves a command works, it suggests that line for you.

## Works best with

- **lead-developer** sends it gate, regression and gaps briefs after implementation.
- **developer** fixes the production bugs it reports. **debugger** finds the cause when a check fails for a reason nobody understands.
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
- Edit production code unless you ask; a probe's one-line change is always restored.
- Push, open a pull request or delete a branch without your answer to the git menu.
- Stash anything except through its one red/green command, which restores the fix itself.

## What's new in 3.0.0

- The gate checks every claim as true, exists and wired.
- New modes perf and probe, both only when asked.
- The finish menu adds Merge into `<base>` locally; Discard only on request.
- A terse voice on request.

{{> readme/80-upgrade-3}}

{{> readme/70-reference-skill}}

## Credits and license

Ideas re-expressed in our own words also come from JuliusBrussee/caveman (Apache-2.0, © 2026 Julius Brussee); addyosmani/agent-skills (MIT, © 2025 Addy Osmani); and open-gsd/gsd-core (MIT, © 2026 Open GSD).

Workflow patterns adapted, not copied, from obra/superpowers (MIT, © 2025 Jesse Vincent) and Anthropic's Claude Code plugins (feature-dev, pr-review-toolkit, code-review, security-review, frontend-design; Apache-2.0).
Licensed under the MIT License; see LICENSE.
