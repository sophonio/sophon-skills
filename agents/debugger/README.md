# Debugger

Turns a symptom into a proven root cause: it reproduces the problem, tests one hypothesis at a time and shows the evidence before anyone changes code.

Part of the Buildersoft development family 3.0.0.

| Agent | Role | Delegates | Changes files | Commits |
|---|---|---|---|---|
| lead-developer | orchestrator: sizes, plans, builds, verifies, commits | yes (depth 1) | yes | yes |
| developer | implementer: tdd / direct / debug | no | yes | yes |
| researcher | codebase and web facts, every claim cited | no | no | no |
| software-architect | blueprint / ADR / greenfield / compare / critique | no | its plan or ADR file only | no |
| code-reviewer | review / refute / re-review / completeness | no | no | no |
| qa-engineer | verification gate, regression checks, tests | no | tests, when asked | yes |
| **debugger** (this one) | root cause first, then a fix when asked | no | fix + regression test, when asked | yes |
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

- An error or stack trace you can't explain.
- A failing or flaky test, a crash or a hang.
- A regression after a change: "this worked yesterday".
- Behaviour that differs between machines or environments.

## Not for

- Building features or refactoring: use `developer`, or `lead-developer` for larger work.
- Confirming a finished fix: use `qa-engineer`.
- Code review: use `code-reviewer`. Security review: use `security-reviewer`.

## How it works

- It quotes the symptom, then asks in one question card only what it can't find out itself: live incident or stable bug, when it started, how often, and where.
- It reproduces the problem from the lowest rung up: an existing failing test, a new minimal test, a dev run with your input, a throwaway script. If nothing reproduces it, it says so, lists what it tried and what data would help, and treats any fix as a candidate only.
- Before every check it writes down the hypothesis and the prediction that would confirm or falsify it, and it keeps a round-by-round record of what is known and what is ruled out.
- After three falsified hypotheses it changes tactic: it widens the search, bisects (only with your agreement and a clean tree), adds temporary `SOPHON-DEBUG` lines that it later proves are gone, shrinks the reproduction, checks for stale builds and config, or searches upstream for the exact message.
- It stops after five falsified hypotheses and asks you how to proceed instead of guessing.
- In a live incident it puts mitigation first and offers the options with their risk.
- It ends with a choice: apply the fix with a regression test, add only the regression test, or leave it. It says "fixed" only when a test failed before the fix and passes after it.
- A fix bigger than a small change gets a plan file in `docs/plans/` that you approve, a `sophon/<slug>` branch and one verified commit per task, then a Push + PR / Keep local / Discard menu.

## Tools and cards you'll see

| Action | Card |
|---|---|
| Reading and searching files, `code.git` status and log, `os.info`, `diff` comparisons, `web.search`, `web.scrape`, the todo list | none |
| Each reproduction or test run (`os.execute`); related checks are chained into one command | one each |
| `code.git` blame on a suspect file | one each |
| Temporary instrumentation, the regression test and the fix | one per file edit |
| Bisect, after you agree to it | one |
| Questions (`info.request`) | a question, not a card |

## After installing

- **Effort: high.** Root-cause work is long and benefits from more reasoning: `sophon agents models debugger --effort high`.
- **Allowed Medium-risk calls for the session** cover at most this agent's Medium-risk reads at the root, such as `code.git` blame. They never cover its edits, commits or shell commands, nor any call it makes as a sub-agent: as a Marketplace agent it always asks for those.
- **Bind and trust the folder.** Run `sophon` in the repository so the session is bound, then `/trust` the folder so its AGENTS.md or CLAUDE.md conventions load.
- Pick it with `/agent debugger` or `--agent debugger`.

## Works best with

- `lead-developer`: sends it one read-only hypothesis check when a plan task keeps failing.
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

## What's new in 2.1.0

- Seven companions joined the family: `frontend-developer`, `design-system-engineer`, `visual-designer`, `e2e-test-engineer`, `accessibility-reviewer`, `mcp-integration-engineer` and `technical-writer`. They are licensed Apache-2.0; this agent stays MIT. Add the ones you install to an existing Lead Developer allow-list.

## What's new in 2.0.0

- A new agent, released at 2.0.0 together with the rest of the family.
- A TOOLS.md file pins `os.info`, `diff` and `web.scrape` in coding sessions.
- Updating does not change delegation settings.
- If your Lead Developer delegates through an allow-list, add `debugger` to it, together with the other new companions `code-reviewer` and `security-reviewer`.

## Credits and license

Debugging discipline also draws on backend-design by sheitabrk (MIT, github.com/sheitabrk/backend-design).

Workflow patterns adapted, not copied, from obra/superpowers (MIT, © 2025 Jesse Vincent) and Anthropic's Claude Code plugins (feature-dev, pr-review-toolkit, code-review, security-review, frontend-design; Apache-2.0).

Licensed under the MIT License; see LICENSE.
