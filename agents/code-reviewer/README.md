# Code Reviewer

Read-only code review that reports only the defects it can show: the line, the failing case and the fix.

Part of the Buildersoft development family 3.0.0.

| Agent | Role | Delegates | Changes files | Commits |
|---|---|---|---|---|
| lead-developer | orchestrator: sizes, plans, builds, verifies, commits | yes (depth 1) | yes | yes |
| developer | implementer: tdd / direct / debug | no | yes | yes |
| researcher | codebase and web facts, every claim cited | no | no | no |
| software-architect | blueprint / ADR / greenfield / compare / critique | no | its plan, ADR or design note only | no |
| **code-reviewer** (this one) | review / refute / re-review / completeness | no | no | no |
| qa-engineer | verification gate, regression checks, tests | no | tests, when asked | yes |
| debugger | root cause first, then a fix when asked | no | fix + regression test, when asked | yes |
| security-reviewer | exploitable vulnerabilities only | no | no | no |
| ui-ux-designer | discover / direction / refine / build / critique / copy / judge | no | UI presentation files | yes |
| frontend-developer | UI implementer: component / direct / artifact / perf / variant | no | yes | yes |
| design-system-engineer | audit / tokens / theme / playground / brand-check / guards | no | tokens, themes, components, token guards | yes |
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

- Before you commit or merge: review the working tree, a branch against its base, or named files.
- When you want real defects only: each finding has file:line, a failure scenario, a fix and a confidence of 80 or more.
- Inside Lead Developer's reviews: the lead sends it per-task reviews, branch reviews, and refute, re-review and completeness briefs.

## Not for

- Fixing what it finds: `developer`. Running the test suite: `qa-engineer`.
- Exploitable-vulnerability review: `security-reviewer`. Choosing a different design: `software-architect`.
- Agent instructions and packages: `agent-engineer`. Acceptance against requirements: `product-owner`.

## How it works

- **Scope first.** The working tree, a branch or commit range (one shell approval per read-only git command, announced up front) or named files. With nothing to review it asks: last commit, branch vs main, or specific files.
- **Spec from you.** Your request, the plan file or the lead's brief; without one it reports `SPEC: CANNOT_VERIFY` instead of guessing. Whatever the files cannot settle goes on a CANNOT_VERIFY line, never under met.
- **Lens by lens.** Correctness, spec compliance, tests and silent failures, and simplification (report only), each finished before the next starts.
- **Checks reviews miss.** After the hunk-by-hunk read: sibling handlers that need the same guard, every switch or map keyed on a new kind, a check that reads one value while the action uses another, the callers of a changed return, code that fails open, and two parsers that read one input differently. A finding outside the diff names the diff line that enables it.
- **Tests that can fail.** A test whose expected value comes from the code under test, or whose assertion has nothing to check, is a finding; so is a loosened assertion, an added retry or a skipped test.
- **Confidence 0 to 100.** Only findings at 80 or above are reported; weaker ones are listed under POSSIBLE, so nothing is hidden.
- **No noise.** Pre-existing issues the change does not make worse, what the compiler or linter catches, style without a quoted project rule and "could be more defensive" are left out.
- **Claims are checked.** The implementer's summary, commit messages and code comments are claims to verify, and a stated reason never lowers a severity. An instruction to pass over a defect or rate it a given way gets a DECLINED line; text aimed at AI reviewers is itself reported.
- **Verdict and coverage.** APPROVE, or REQUEST_CHANGES when any Critical or Important finding remains, plus a line saying how many files were reviewed and which were not.
- Replies are plain sentences; say "terse" or "caveman" for short ones and "normal" to switch back.

### Modes

| Mode | What it does | Verdict |
|---|---|---|
| review | the lenses above, over a change, or over one plan task with its steps, Global constraints and Review focus as the spec | APPROVE or REQUEST_CHANGES, plus SPEC: MET, GAPS or CANNOT_VERIFY |
| refute | votes CONFIRMED or REFUTED on every candidate finding from one angle: reachability, impact or defenses | one vote per finding |
| re-review | reads the lines each earlier finding cites as they stand now: ADDRESSED or NOT_ADDRESSED | ALL_ADDRESSED or OPEN |
| completeness | what the request asked for that is not done or not verified | COMPLETE or GAPS |

You can ask for any mode directly, for example "check this branch for completeness against the plan in docs/plans".

## Tools and cards you'll see

| Call | When | Approval card |
|---|---|---|
| fs.read, fs.find, fs.search; code.git status and log | always | none |
| code.git diff | working-tree review | may raise one; none in a trusted workspace on the Gateway we tested |
| os.execute with read-only git (log, diff) | branch or commit-range review | one per command; Critical risk, so it always asks |
| info.request | nothing to review | a question, not a card |

- As a sub-agent it reads the change the brief names: a diff file the lead wrote, with fs.read and no card, or the working tree with one code.git diff call. It runs no shell commands there.
- TOOLS.md pins fs.read, fs.find and fs.search for the sub-agent profile, so they stay visible when the lead narrows a child's tools.

## After installing

- **Effort:** high works best for review: `sophon agents models code-reviewer --effort high`. Delegated runs use it only while the lead's chat has no effort of its own (`/effort reset` there).
- **Bind and trust the repository:** run `sophon` in the project folder, then `/trust`, so AGENTS.md and the project rules load. The reviewer quotes a rule whenever it cites one.
- **Allowed Medium-risk calls for the session** (set with `/permissions`) cover this agent's code.git diff at the root. They never cover its os.execute calls, and never any sub-agent's calls.
- **With Lead Developer:** install with `sophon agents install code-reviewer --allow-delegation-from lead-developer` and keep the id `code-reviewer`. If the lead restricts delegation to an allow list, add this id to it. The lead finds the agent through the `Family role: code-reviewer.` marker in its when-to-use text.

## Works best with

- `lead-developer`: under "Team per task" it pairs this agent with each implementer and runs one cross-task review of the branch; under "Build inline, then review" it runs a panel (3 lenses for a medium change, 4 or 5 for a large one), 3 refuters per Critical or Important finding and a re-review after each fix.
- `developer`: fixes confirmed findings, with a test that fails first.
- `security-reviewer`: the security lens this agent leaves out.
- `qa-engineer`: runs the suites this agent does not.

## Limits

- It runs no builds or tests. When a run would settle a question, it says which run and who should do it.
- code.git diff sees uncommitted tracked files only. Committed work is reviewed through the range form, which costs one approval per command.
- Large diffs are split to fit the output window; anything not reviewed is named.
- As a sub-agent it reviews only the change and line ranges in its brief, opening other files only to prove a finding or run the checks reviews miss. A task review whose implementer did not finish returns NEEDS_CONTEXT.
- Findings below the confidence threshold are listed, not argued, so some real but unproven issues land there.
- It is not a security review.

## What it never does

- Edit, write, move or delete files; commit, push or switch branches.
- Run commands other than read-only git, and none at all as a sub-agent.
- Start sub-agents.
- Report style preferences without a quoted project rule.
- Follow instructions found in the code, comments or diff it reviews.

## What's new in 3.0.0

- As a sub-agent it reads the change the brief names: a diff file, or the working tree with one code.git diff call.
- A review mode for one plan task, the six checks reviews miss, the test-integrity rules, and CANNOT_VERIFY and DECLINED lines.
- A terse voice on request.

## Upgrading from 2.x

- 3.0.0 is a major version, so Sophon never applies it unattended. Take it yourself, one agent at a time: `sophon agents update <id>`.
- Update every family agent you have installed in one sitting. In between, Lead Developer 3.0.0 gives a companion below 3.0.0 the brief that 2.x understands and tells you once which agents to update, and a 3.0.0 companion still accepts a 2.x brief. An agent you created locally from these files reports no version and counts as current.
- Four agents are new: `product-owner`, `product-manager`, `release-engineer` and `agent-engineer`. Install the ones you want with `--allow-delegation-from lead-developer`. Updating never changes delegation settings, so an existing allow list needs them added.
- The instructions are longer. Each new session of this agent, and each sub-agent run of it, reads about 1,900 more tokens than in 2.x.
- 3.0.0 lists the optional `craft-reference` skill, which returns long reference material on request. Sophon offers to install it; if you decline, the agent works from what it carries.
- Your own edits to an installed agent pause its updates. Add `--discard-local-changes` to replace them.

## Reference skill

This agent can read longer tables, checklists and templates from the optional `craft-reference` skill, which Sophon offers when you install the agent. The skill does not run in plan mode or on a Gateway without the Docker sandbox, and the agent then works from the summary it carries. The skill's own notices credit the sources of its topics.

## Credits and license

Ideas re-expressed in our own words also come from JuliusBrussee/caveman (Apache-2.0, © 2026 Julius Brussee); and Anthropic's security-guidance plugin, anthropics/claude-plugins-official (Apache-2.0).

Workflow patterns adapted, not copied, from obra/superpowers (MIT, © 2025 Jesse Vincent) and Anthropic's Claude Code plugins (feature-dev, pr-review-toolkit, code-review, frontend-design; Apache-2.0). Licensed under the MIT License; see LICENSE.
