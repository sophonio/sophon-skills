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
| product-manager | discover / analyst / brief / PRD / prioritise / pre-mortem | no | its product documents only | no |
| product-owner | spec / slice / refine / validate / accept / replan / triage | no | its requirements and story files only | no |
| release-engineer | check / ship / deploy / watch / upgrade / rollback | no | version, changelog and dependency files | yes |
| agent-engineer | agent instructions: design / rule / test / review / diagnose | no | agent and skill instruction files | yes |

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

## Upgrading from 2.x

- 3.0.0 is a major version, so Sophon never applies it unattended. Take it yourself, one agent at a time: `sophon agents update <id>`.
- Update every family agent you have installed in one sitting. In between, Lead Developer 3.0.0 gives a companion below 3.0.0 the brief that 2.x understands and tells you once which agents to update, and a 3.0.0 companion still accepts a 2.x brief. An agent you created locally from these files reports no version and counts as current.
- Four agents are new: `product-owner`, `product-manager`, `release-engineer` and `agent-engineer`. Install the ones you want with `--allow-delegation-from lead-developer`. Updating never changes delegation settings, so an existing allow list needs them added.
- The instructions are longer. Each new session of this agent, and each sub-agent run of it, reads about 2,200 more tokens than in 2.x.
- 3.0.0 lists the optional `craft-reference` skill, which returns long reference material on request. Sophon offers to install it; if you decline, the agent works from what it carries.
- Your own edits to an installed agent pause its updates. Add `--discard-local-changes` to replace them.

## Reference skill

This agent can read longer tables, checklists and templates from the optional `craft-reference` skill, which Sophon offers when you install the agent. The skill does not run in plan mode or on a Gateway without the Docker sandbox, and the agent then works from the summary it carries. The skill's own notices credit the sources of its topics.

## Credits and license

Ideas re-expressed in our own words also come from JuliusBrussee/caveman (Apache-2.0, © 2026 Julius Brussee); and mattpocock/skills (MIT, © 2026 Matt Pocock).

Debugging discipline also draws on sheitabrk/backend-design (MIT, © sheitabrk and contributors).

Workflow patterns adapted, not copied, from obra/superpowers (MIT, © 2025 Jesse Vincent) and Anthropic's Claude Code plugins (feature-dev, pr-review-toolkit, code-review, frontend-design; Apache-2.0).

Licensed under the MIT License; see LICENSE.
