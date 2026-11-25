# Lead Developer

Takes a code change from request to a ready-to-merge branch: works out with you what is wanted, sizes it, plans it, builds it (alone or with specialist sub-agents you agree to), proves it with real commands, commits each verified task and offers a pull request.

Part of the Buildersoft development family 3.0.0.

| Agent | Role | Delegates | Changes files | Commits |
|---|---|---|---|---|
| **lead-developer** (this one) | orchestrator: sizes, plans, builds, verifies, commits | yes (depth 1) | yes | yes |
| developer | implementer: tdd / direct / debug | no | yes | yes |
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
| product-manager | discover / analyst / brief / PRD / prioritise / pre-mortem | no | its product documents only | no |
| product-owner | spec / slice / refine / validate / accept / replan / triage | no | its requirements and story files only | no |
| release-engineer | check / ship / deploy / watch / upgrade / rollback | no | version, changelog and dependency files | yes |
| agent-engineer | agent instructions: design / rule / test / review / diagnose | no | agent and skill instruction files | yes |

Only Lead Developer starts sub-agents. The others work alone when you talk to them directly, and as the lead's specialists when it delegates to them.

## When to use

Pick Lead Developer to plan and deliver a code change in a repository bound with the Sophon CLI:

- a feature, a multi-file fix, a refactor or a migration;
- a review-and-fix pass over a branch;
- a story or requirements file to build: "execute docs/product/<slug>/01-<story>.md";
- "continue the plan" after a break or a compacted conversation;
- "ultracode: ..." when you want multi-agent research, design, review and verification.

## Not for

- Questions about how code works: use **researcher**.
- A design without implementation: use **software-architect**.
- One scoped task, or a plan task handed over by a lead: use **developer**.
- Reviewing an existing diff: use **code-reviewer**.
- A bug whose cause is unknown: use **debugger**.
- Whether to build something and for whom: use **product-manager**. Requirements and stories written with you: use **product-owner**. Shipping a merged branch: use **release-engineer**. The lead does not brief these on its own; it names the agent and the sentence to say to it.

## How it works

1. **Sizes every request.**
   - Trivial (at most 2 files and 40 lines, one obvious approach, no interface, schema, dependency, build, auth or permission change): done directly, with no plan file.
   - Medium (3-10 files, 41-400 lines, 2-6 tasks, or one real design choice): plan file, approval, feature branch, one commit per verified task.
   - Large (more than 10 files or 400 lines, more than 6 tasks, several modules, a migration, auth, crypto or concurrency): as Medium, plus the multi-agent phases when you agree. More than 20 tasks become milestone plans.
   - It never sizes downward.
2. **Asks before it plans, only what is open.** With nothing open it asks nothing and puts its understanding into the plan question. Otherwise it asks the reason for the work first, one open question per message, ending the first with: Or say "just build it" and I will plan from my assumptions. It plays its understanding back in at most 200 words, and with more than one real approach it describes 2-3 and you choose. Nothing is built, scaffolded or installed before plan approval. "just build it" or "no questions" stops discovery questions (`Discovery: opted out`, each guess an `Assumption:` line); approvals are still asked.
3. **Writes a design note for a project.** Large work, a new subsystem, or work whose shape discovery changed gets a note of at most 600 words, first read as a builder who saw neither the chat nor the code would read it. It is shown in chat and saved as `docs/plans/YYYY-MM-DD-<slug>-design.md` only on your yes in a "Design note" question (Save, Change something or Stop): one card. Later changes add dated `Decision` lines.
4. **Plans in a file you approve.** The plan is written to `docs/plans/YYYY-MM-DD-<slug>.md` in one fixed format: header lines (among them `Request:`, `Spec:`, `Discovery:`, `Voice:` and `Consent:`), then Goal, Context, Approach, Global constraints, Out of scope, Verification, Review focus, Tasks (each with files, steps, the exact check command, the expected result and the commit subject), Risks and Progress. You approve it on the plan card (plan mode) or in a "Plan" question: Approve and start, Change something, or Cancel. No answer means it does not start.
5. **Executes task by task.** It creates `sophon/<slug>`, mirrors the tasks into a live todo list and, for each task, re-reads the task from the file, runs the failing check first where tests apply, makes the change, ticks the plan and runs one verify-and-commit command. A failing check is repaired at most 3 times, then the task is marked BLOCKED and you are asked what to do. Unverified work is never committed. Minor review points it does not fix are recorded as `Parked:` lines in the plan.
6. **Asks before using sub-agents.** When delegation would clearly help, the plan question carries an "Agents" question: the recommended option first, Solo always offered, and each option states the agents and waves, the approval cards in all and extra, and the relative token cost. On a Medium plan the options are **Build inline, then review** (Recommended), **Team per task** and **Solo**; on a Large plan Team per task comes first. The answer is recorded on the plan's `Consent:` line and holds for the whole task.
7. **Runs the waves you agreed to.** The plan's `## Orchestration` section works like a workflow script: a consent and estimate line, the companions it found, and a table of waves.
   - Understand (2-5 researchers) and Design (2-3 architects scored on a written 14-point rubric) run before the plan when needed.
   - **Team per task:** an implementer and a reviewer per task in one delegate call; changes asked for start a fix round, at most 3 per task, the third fixed by the lead. Then one cross-task reviewer reads the branch and one re-review follows; what stays open gets a Ruling.
   - **Build inline, then review:** the lead builds every task, then reviewer lenses read one diff of the branch (Medium 3, Large 4-5), 3 refuters vote on each serious finding (2 of 3 confirm), each confirmed one gets a failing-then-passing test and a `fix(...)` commit, and re-review repeats at most 3 rounds.
   - A Completeness critic runs on Large plans and Medium plans of 4 or more tasks, joined by Product Owner's acceptance check for a story. Up to 3 implementers run in parallel only on disjoint files.
8. **Settles the look before UI work.** When neither you nor the project's own system (`DESIGN.md`, tokens, a component library) decides it, it asks once, header "Design": Sophon design default (Recommended), Plain standard, or Direction round (UI/UX Designer shows four directions and you pick). Nothing reaches a project file before your pick, "just build it" does not remove this question, and it never styles from memory.
9. **Trusts nothing it has not checked.** Every child's claim is re-checked by reading the file or running the command, and a child's outcome is read from its STATUS line. Children never commit, never ask you questions and never delegate further; the lead commits.
10. **Reports with evidence.** Failures first, then changes and commits, the commands that prove them, the rulings it made, what it did not cover, then "Agents used: ...; caps: ..." and "Where it stands: ...". After a push or a merge it ends with "To release: tell Release Engineer 'ship'."
11. **Offers one lesson.** At Medium and above it may offer, with the git menu, the one lesson that would have saved the most work (a check, an AGENTS.md line or a memory note), as exact text in a "Lesson" question: Save it, or Not now. It is saved only on a yes, as its own commit.
12. **Ends with a git menu.** One "Git" question: Push + open PR, Merge into `<base>` locally (checks run on the merged result; nothing is pushed), or Keep local. No answer means Keep local. Discard runs only when you ask, after it lists what would be lost and asks once more. It never pushes silently.
13. **Answers in the voice you choose.** Plain by default; "terse" or "caveman" switches to short sentences that keep every number and negation, "normal" switches back. Questions, warnings and saved files stay in full sentences.

Commits end with the trailer `Co-Authored-By: Sophon <noreply@buildersoft.io>`. PR bodies end with `🤖 Generated with [Sophon](https://sophon.buildersoft.io)`.

## Tools and cards you'll see

**Pinned by this package** (TOOLS.md):

| Profile | Pins | Why |
|---|---|---|
| all | craft.read | long reference topics from the optional craft-reference skill |
| coding | agent.list, canvas.render, web.scrape, session.history | find companions, show design options, read docs pages, restore your consent and voice words after a gap |
| chat (unbound) | agent.list, canvas.render, todo.write, fs.find, fs.search, web.scrape | read and plan when no repository is bound |

Everything else comes from Sophon's coding tools: fs.read, fs.find, fs.search, fs.write, the edit tools, os.execute, code.git, plan.propose, info.request, todo.write and agent.delegate.

**Approval cards.** Marketplace agents are third-party, so your standing approvals (accept edits, remembered commands, allow all) do not cover them.

| Card on every call | May raise a card | No card |
|---|---|---|
| fs.write, the edit tools, fs.move, fs.copy, fs.delete, fs.create_directory | agent.delegate (Medium) | fs.read, fs.list, fs.find, fs.search, fs.info |
| os.execute (Critical; never remembered for a package agent) | code.git diff and blame (Medium) | code.git status, log, branch list, remote, stash list |
| every code.git write (Medium) | | web.search, web.scrape, browser.screenshot, canvas.render |
| http.request, browser.act (Medium); plan.propose raises the plan card | | todo.write, memory.search, memory.write, tools.search, tools.load, agent.list, session.history, datetime.now, os.info; info.request is a question, not a card |

- **Per plan task:** the files it edits, plus one failing-check run, one plan tick and one verify-and-commit command (files edited + 3).
- **Per plan:** about 4 more (the plan file, the branch, the PR body file, push + PR). A saved design note adds one.
- **Example:** a medium 4-task plan touching about 3 files per task raises about 4 × 6 + 4 = **28 cards** Solo.
- **With sub-agents:** every Medium-or-higher call a child makes raises a card for you at the top level. Under Team per task a reviewed task comes to files edited + 4, so the same plan is about 33 cards; Build inline, then review is about 29. The Agents question states the extra cards first. agent.delegate and a reviewer's code.git diff may add one each; the estimate leaves them out, and in a trusted workspace neither raised one in our tests.

## After installing

**1. Bind and trust the repository.** Run `sophon` in the project folder, then `/trust` so the project instructions (AGENTS.md or CLAUDE.md) and the git state load. Pick the agent with `/agent lead-developer`, or `--agent lead-developer` when you start the CLI. Unbound, it reads and plans, and edits only if you ask again after it suggests binding.

**2. Install the companions.** With the lead installed, first open Dashboard → Agents → Lead Developer → Delegation, turn on **Restrict to allow list** and save: the list starts empty, and `--allow-delegation-from` adds to it only while this is on. Then install each companion with permission for the lead to delegate to it:

```
sophon agents install developer --allow-delegation-from lead-developer
sophon agents install researcher --allow-delegation-from lead-developer
sophon agents install software-architect --allow-delegation-from lead-developer
sophon agents install code-reviewer --allow-delegation-from lead-developer
sophon agents install qa-engineer --allow-delegation-from lead-developer
sophon agents install debugger --allow-delegation-from lead-developer
sophon agents install security-reviewer --allow-delegation-from lead-developer
sophon agents install ui-ux-designer --allow-delegation-from lead-developer
```

The frontend, design and other companions install the same way; add only the ones you use:

```
sophon agents install frontend-developer --allow-delegation-from lead-developer
sophon agents install design-system-engineer --allow-delegation-from lead-developer
sophon agents install visual-designer --allow-delegation-from lead-developer
sophon agents install e2e-test-engineer --allow-delegation-from lead-developer
sophon agents install accessibility-reviewer --allow-delegation-from lead-developer
sophon agents install mcp-integration-engineer --allow-delegation-from lead-developer
sophon agents install technical-writer --allow-delegation-from lead-developer
sophon agents install product-manager --allow-delegation-from lead-developer
sophon agents install product-owner --allow-delegation-from lead-developer
sophon agents install release-engineer --allow-delegation-from lead-developer
sophon agents install agent-engineer --allow-delegation-from lead-developer
```

Then check that **Effective targets** lists the companions. Keep each agent id equal to its package name (a `-2` suffix still matches). The lead finds companions through the `Family role: <slug>.` line in their when-to-use text, which also lists their modes and brief keys; a missing one is replaced by a stand-in running the lead's rules with a pasted checklist, labelled lower confidence. A companion below 3.0.0 gets the 2.x brief, and the lead tells you once to update it.

**3. Set effort.** A package cannot set effort. Recommended:

```
sophon agents models lead-developer --effort high
```

Do the same for software-architect, code-reviewer, security-reviewer, debugger, accessibility-reviewer, product-manager, product-owner and agent-engineer; leave the rest at the default. A companion's effort reaches its delegated runs only while the lead's chat has no effort of its own (`/effort reset`).

**4. Upgrading from 1.0.0: set the delegation depth to 1.** Updating never changes delegation settings, so a 1.0.0 lead keeps depth 2. Set it in Dashboard → Agents → Lead Developer → Delegation → Max depth, or with `PUT /api/agents/lead-developer/subagents`, so every consent question and card estimate stays at the top level.

**5. Know what allowing Medium-risk calls covers.** Allowing Medium-risk calls for the session (`/permissions` in the CLI) covers only the lead's own agent.delegate, code.git diff and blame, and GET http.request calls. It never covers a package agent's edits, commits or shell commands, and never any call a child makes.

**6. Learn the consent words.** The lead reads your messages, newest first, and the first match wins:

| You say | Effect |
|---|---|
| "ultracode off", "no ultracode" | back to asking each time |
| "no subagents", "no sub-agents", "without subagents", "don't use agents" | standing no: everything runs in one thread |
| "ultracode" | standing yes: waves run without the Agents question, after a one-line announcement of agents, waves, cards and cost, and it selects Team per task at Medium and at Large (about 7× Solo tokens on a four-task plan, against about 3.5× for Build inline, then review) |
| "use agents" (after a standing no) | back to asking |

The keyword decides consent only. Size still decides the phases, so a trivial change stays inline even with ultracode on, and a standing yes still needs plan approval.

**7. Plan mode on the Personal edition.** The Personal-edition Dashboard (and mobile) cannot approve a plan card. Use the CLI, or the GO escape: choose **Keep planning** and type `GO`. The lead replies "Approved in chat", asks you to switch the mode to "Ask before edits" (Dashboard: the mode chip or Alt+M; CLI: Shift+Tab or `/permissions default`) and send any message, then saves the plan as approved and runs it. Without plan mode, approval is a normal question and works everywhere.

**8. Set up pull requests.** Push and `gh pr create` run through os.execute in a shell that cannot prompt and has no GitHub credentials in its environment. Before the first PR, run `gh auth status` (or `gh auth login`, then `gh auth setup-git`) in your own terminal. HTTPS remotes work best. On an authentication failure the lead stops, quotes the error and gives you the commands; it never asks for a token in chat.

**Fewer cards: the local-install form (advanced, unsupported).** An agent you create yourself from these files is your own: your standing approvals such as accept edits cover it, so a plan raises far fewer cards. Keep one form per agent id; do not mix a Marketplace lead with local companions of the same ids.

## Works best with

- **researcher**: Understand waves, each with a distinct focus, every claim cited with file:line or a URL.
- **software-architect**: Design judge panels, the builder check of a design note, and plans you hand over with "execute docs/plans/<file>".
- **developer**: the implementer of a task no other companion covers.
- **code-reviewer**: per-task and cross-task reviews, lenses, refute votes, re-reviews and the completeness critic.
- **security-reviewer**: a security lens when a change touches a trust boundary, and verification of security findings.
- **qa-engineer**: test-strategy gaps in Large reviews; a probe or perf run when you ask for one by name.
- **debugger**: one read-only hypothesis check when a repair keeps failing.
- **ui-ux-designer**: the direction round, `DESIGN.md` prose and a UX critique lens for UI changes.
- **frontend-developer**: the implementer for UI tasks: components, state, forms and browser checks.
- **accessibility-reviewer**: a WCAG 2.2 AA lens for UI changes.
- **product-owner**: the acceptance check of a plan built from a story.
- **release-engineer**: a release check lens for version, changelog, dependency, migration or CI changes.
- **design-system-engineer**, **visual-designer**, **e2e-test-engineer**, **mcp-integration-engineer**, **technical-writer** and **agent-engineer**: plan tasks in their own areas, briefed by mode.

## Limits

- Sub-agents are blocking: no background agents, at most 5 per call, one level deep. Caps per request: Medium 20 agents in 10 delegate calls, Large 44 agents in 22 delegate calls; a reviewed task or a fix round counts 2 agents. The estimate you approved is binding; anything dropped is logged as a `Cap:` line and listed in the report.
- Cards scale with fan-out, because every child's edits and commands raise cards at the top level.
- Every child pays for its own instructions uncached, and the prompt cache misses after any pause over 5 minutes, including approval waits.
- Children share your workspace: there are no separate worktrees, so parallel implementers get disjoint files only.
- code.git cannot push, open PRs or make selective commits, so commits, pushes and PRs go through os.execute, which is always a card.
- On Windows, commands run in cmd or Windows PowerShell 5.1, never bash.
- Children cannot ask you questions; their questions come back to the lead, which asks you.
- In plan mode only Understand, Design and the direction round run, and canvas previews and skill tools are refused: design options then come as text.
- Graph execution can still be picked on the plan card. Its steps commit as the plan says, and the lead reconciles the plan with the git log on your next message.

## What it never does

- Push silently, push to the default branch or force-push.
- Amend, rebase, reset, revert, clean, delete branches or change git config, unless you ask for that exact operation.
- Commit work its own checks have not proven, or let sub-agents commit.
- Start sub-agents without your consent, or exceed the estimate it gave you.
- Pick an approach, a design direction or a scope cut for you: it recommends, you choose.
- Build, scaffold or install anything before the plan is approved.
- Install agents or split work with Sophon workflows.
- Ask for a token in chat, or repeat secret values in plans, commits, PR bodies or briefs.
- Run `git init` in a folder that is not a repository.

## What's new in 3.0.0

- Discovery, the design note, the wider plan format, the Lesson step, the terse voice and the "Design" question.
- Sub-agent options Build inline, then review; Team per task ("ultracode" selects it); Solo. Caps 20 agents in 10 calls (Medium) and 44 in 22 (Large).
- The finish menu gains Merge into `<base>` locally; open minor points are "parked" in the plan.
- New companions `product-manager`, `product-owner`, `release-engineer` and `agent-engineer`: add them to an existing allow list.

## Upgrading from 2.x

- 3.0.0 is a major version, so Sophon never applies it unattended. Take it yourself, one agent at a time: `sophon agents update <id>`.
- Update every family agent you have installed in one sitting. In between, Lead Developer 3.0.0 gives a companion below 3.0.0 the brief that 2.x understands and tells you once which agents to update, and a 3.0.0 companion still accepts a 2.x brief. An agent you created locally from these files reports no version and counts as current.
- Four agents are new: `product-owner`, `product-manager`, `release-engineer` and `agent-engineer`. Install the ones you want with `--allow-delegation-from lead-developer`. Updating never changes delegation settings, so an existing allow list needs them added.
- The instructions are longer. Each new session of this agent, and each sub-agent run of it, reads about 4,400 more tokens than in 2.x.
- 3.0.0 lists the optional `craft-reference` skill, which returns long reference material on request. Sophon offers to install it; if you decline, the agent works from what it carries.
- Your own edits to an installed agent pause its updates. Add `--discard-local-changes` to replace them.

## Reference skill

This agent can read longer tables, checklists and templates from the optional `craft-reference` skill, which Sophon offers when you install the agent. The skill does not run in plan mode or on a Gateway without the Docker sandbox, and the agent then works from the summary it carries. The skill's own notices credit the sources of its topics.

## Credits and license

Ideas re-expressed in our own words also come from JuliusBrussee/caveman (Apache-2.0, © 2026 Julius Brussee); and EveryInc/compound-engineering-plugin (MIT, © 2025 Every).

Workflow patterns adapted, not copied, from obra/superpowers (MIT, © 2025 Jesse Vincent) and Anthropic's Claude Code plugins (feature-dev, pr-review-toolkit, code-review, frontend-design; Apache-2.0). Licensed under the MIT License; see LICENSE.
