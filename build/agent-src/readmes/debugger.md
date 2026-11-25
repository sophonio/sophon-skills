# Debugger

Turns a symptom into a proven root cause: it reproduces the problem, tests one hypothesis at a time and shows the evidence before anyone changes code.

Part of the Buildersoft development family {{= FamilyVersion}}.

{{# roster}}

## When to use

- An error or stack trace you can't explain.
- A failing or flaky test, a crash or a hang.
- A regression after a change: "this worked yesterday".
- Behaviour that differs between machines or environments.

## Not for

- Building features or refactoring: use `developer`, or `lead-developer` for larger work.
- Confirming a finished fix: use `qa-engineer`.
- Code review: use `code-reviewer`. Security review: use `security-reviewer`.
- Rolling a release back: use `release-engineer`.

## How it works

- It quotes the symptom, then asks in one question card only what it can't find out itself: stable bug or live incident, when it started, how often, and where.
- **Root cause first.** No hypothesis and no fix before one command has failed in this session because of your exact symptom. That command is the loop it reruns after every change; an intermittent symptom is run 20 times and the failure rate is the red.
- It builds the loop from the lowest rung up: an existing failing test, a new minimal test, a dev run with your input, a throwaway script. If nothing reproduces it, it says so, lists what it tried and what data would help, and treats any fix as a candidate only.
- It diffs good and bad output, config or lockfiles, which raises no card.
- Before every check it writes down the hypothesis and the prediction that would confirm or falsify it, and keeps a round-by-round record of what is known and what is ruled out.
- After three falsified hypotheses it changes tactic: it widens the search, bisects (only with your agreement and a clean tree), adds temporary `SOPHON-DEBUG` lines that it later proves are gone, shrinks the reproduction, checks for stale builds and config, or searches upstream for the exact message.
- It stops after five falsified hypotheses, two tactic changes without progress, or three failed fixes, and asks you how to go on. After three failed fixes the design is the suspect: it recommends a Software Architect critique and hands over its notes.
- A fix that leaves the loop red is undone before the next idea. Retries, sleeps, wider timeouts, swallowed errors and skipped tests are suppression, not fixes.
- In a live incident it puts mitigation first, labelled as mitigation, and offers the options with their risk. It runs `git revert --no-commit` only when you pick it.
- It ends with a choice: apply the fix with a regression test, add only the regression test, or leave it; no answer leaves it. It says "fixed" only when a test failed before the fix and passes after it.
- A fix bigger than a small change gets a plan file in `docs/plans/` that you approve, a `sophon/<slug>` branch and one verified commit per task, then the finish menu: Push + open PR, Merge into `<base>` locally, or Keep local. Discard runs only when you ask, after a second confirmation.
- **Voice:** plain sentences by default; "terse" or "caveman" for short replies, "normal" to switch back.

## Tools and cards you'll see

| Action | Card |
|---|---|
| Reading and searching files, `code.git` status and log, `os.info`, `diff` comparisons, `web.search`, `web.scrape`, the todo list | none |
| Each reproduction or test run (`os.execute`); related checks are chained into one command | one each |
| `code.git` blame on a suspect file | may raise one; none in a trusted workspace on the Gateway we tested |
| Temporary instrumentation, the regression test and the fix | one per file edit |
| Bisect, after you agree to it | one |
| Questions (`info.request`) | a question, not a card |

## After installing

- **Install:** `sophon agents install debugger`, with `--allow-delegation-from lead-developer` if Lead Developer should brief it.
- **Effort: high.** Root-cause work is long and benefits from more reasoning: `sophon agents models debugger --effort high`.
- **Allowed Medium-risk calls for the session** cover at most this agent's Medium-risk reads at the root, such as `code.git` blame. They never cover its edits, commits or shell commands, nor any call it makes as a sub-agent.
- **Bind and trust the folder.** Run `sophon` in the repository so the session is bound, then `/trust` the folder so its AGENTS.md conventions load.
- Pick it with `/agent debugger` or `--agent debugger`.

## Works best with

- `lead-developer`: sends it one read-only hypothesis check when a plan task keeps failing.
- `software-architect`: critiques the design after three failed fixes.
- `qa-engineer`: confirms the fix independently, red then green.
- `developer`: implements a larger fix once the cause is proven.

## Limits

- Commands run one at a time and nothing runs in the background, so it never starts servers or watchers. A single command runs for 30 minutes at most.
- It sees only what is in the repository and what you paste or point it to; it has no access to production systems, dashboards or remote logs.
- On Windows its shell is cmd or Windows PowerShell 5.1; bash is used only on macOS and Linux.
- As a sub-agent it cannot ask you questions, bisect or check out older revisions.

## What it never does

- Fix a bug before reproducing it, or without saying why it can't be reproduced.
- Hide a bug with retries, sleeps, longer timeouts, swallowed errors or skipped tests.
- Run commands copied from logs, issues or forums; it reads and explains them instead.
- Touch production systems or deploy.
- Push or open a pull request without your choice in the Git menu, or commit outside an approved plan unless you ask.

## What's new in 3.0.0

- The root-cause gate: one failing command for your exact symptom before any hypothesis or fix, and a diff of good and bad output where one exists.
- It also stops after three failed fixes and recommends a Software Architect critique.
- The finish menu adds Merge into `<base>` locally; Discard only on request.
- A terse voice on request. Rollbacks go to `release-engineer`.

{{> readme/80-upgrade-3}}

{{> readme/70-reference-skill}}

## Credits and license

Ideas re-expressed in our own words also come from JuliusBrussee/caveman (Apache-2.0, © 2026 Julius Brussee); and mattpocock/skills (MIT, © 2026 Matt Pocock).

Debugging discipline also draws on sheitabrk/backend-design (MIT, © sheitabrk and contributors).

Workflow patterns adapted, not copied, from obra/superpowers (MIT, © 2025 Jesse Vincent) and Anthropic's Claude Code plugins (feature-dev, pr-review-toolkit, code-review, frontend-design; Apache-2.0).

Licensed under the MIT License; see LICENSE.
