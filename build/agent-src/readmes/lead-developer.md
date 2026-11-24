# Lead Developer

Takes a code change from request to a ready-to-merge branch: sizes it, plans it with you, builds it (alone or with specialist sub-agents you agree to), proves it with real commands, commits each verified task and offers a pull request.

Part of the Buildersoft development family {{= FamilyVersion}}.

{{# roster}}
Only Lead Developer starts sub-agents. The others work alone when you talk to them directly, and as the lead's specialists when it delegates to them.

## When to use

Pick Lead Developer to plan and deliver a code change in a repository bound with the Sophon CLI:

- a feature, a multi-file fix, a refactor or a migration;
- a review-and-fix pass over a branch;
- "continue the plan" after a break or a compacted conversation;
- "ultracode: ..." when you want multi-agent research, design, review and verification.

## Not for

- Questions about how code works: use **researcher**.
- A design without implementation: use **software-architect**.
- One scoped task, or a plan task handed over by a lead: use **developer**.
- Reviewing an existing diff: use **code-reviewer**.
- A bug whose cause is unknown: use **debugger**.

## How it works

1. **Sizes every request.**
   - Trivial (at most 2 files and 40 lines, one obvious approach, no interface, schema, dependency, build, auth or permission change): done directly, with no plan file.
   - Medium (3-10 files, 41-400 lines, 2-6 tasks, or one real design choice): plan file, approval, feature branch, one commit per verified task.
   - Large (more than 10 files or 400 lines, more than 6 tasks, several modules, a migration, auth, crypto or concurrency): as Medium, plus the multi-agent phases when you agree. More than 20 tasks become milestone plans.
   - It never sizes downward.
2. **Plans in a file you approve.** The plan is written to `docs/plans/YYYY-MM-DD-<slug>.md` in one fixed format: Goal, Context, Approach, Out of scope, Verification, Tasks (each with files, steps, the exact check command, the expected result and the commit subject), Risks and Progress. You approve it on the plan card (plan mode) or in a "Plan" question: Approve and start, Change something, or Cancel. No answer means it does not start.
3. **Executes task by task.** It creates `sophon/<slug>`, mirrors the tasks into a live todo list and, for each task, re-reads the task from the file, runs the failing check first where tests apply, makes the change, ticks the plan and runs one verify-and-commit command. A failing check is repaired at most 3 times, then the task is marked BLOCKED and you are asked what to do. Unverified work is never committed.
4. **Asks before using sub-agents.** When delegation would clearly help, the plan question carries an "Agents" question: the recommended option first, Solo always offered, and each option states the number of agents and waves, the approval cards in all and extra, and the relative token cost. The answer is recorded on the plan's `Consent:` line and holds for the whole task.
5. **Runs Ultracode-lite waves when you agree.** The plan's `## Orchestration` section works like a workflow script: a consent and estimate line, the companions it found, and a table of waves. Phases: Understand (2-5 researchers), Design (a judge panel of 2-3 architects scored on a written 14-point rubric), Implement (one developer per task, or up to 3 in parallel on disjoint files), Review (3-5 reviewer lenses over one diff file), Refute (3 votes per finding; 2 of 3 must confirm), Fix (a test that fails then passes, then a `fix(...)` commit), Re-review until no new serious finding (at most 3 rounds) and a Completeness critic.
6. **Trusts nothing it has not checked.** Every child's claim is re-checked by reading the file or running the command. Children never commit, never ask you questions and never delegate further; the lead commits.
7. **Reports with evidence.** Failures first, then changes and commits, the commands that prove them, the rulings it made, what it did not cover, then "Agents used: ...; caps: ..." and "Where it stands: ...".
8. **Ends with a git menu.** One "Git" question: Push + open PR, Keep local, or Discard (after one more confirmation). No answer means Keep local. It never pushes silently.

Commits end with the trailer `{{= CommitTrailer}}`. PR bodies end with `{{= PrFooter}}`.

## Tools and cards you'll see

**Pinned by this package** (TOOLS.md):

| Profile | Pins | Why |
|---|---|---|
| coding | agent.list, web.scrape, session.history | find companions, read docs pages, restore your consent words after a gap |
| chat (unbound) | agent.list, todo.write, fs.find, fs.search, web.scrape | read and plan when no repository is bound |

Everything else comes from Sophon's coding tools: fs.read, fs.find, fs.search, fs.write, the edit tools, os.execute, code.git, plan.propose, info.request, todo.write and agent.delegate.

**Approval cards.** Marketplace agents are third-party, so your standing approvals (accept edits, remembered commands, allow all) do not cover them.

| Card on every call | No card |
|---|---|
| fs.write, the edit tools, fs.move, fs.copy, fs.delete, fs.create_directory | fs.read, fs.list, fs.find, fs.search, fs.info |
| os.execute (Critical; never remembered for a package agent) | code.git status, log, branch list, remote, stash list |
| code.git diff, blame and every write (Medium) | web.search, web.scrape, browser.screenshot, canvas.render |
| agent.delegate (Medium) | todo.write, memory.search, memory.write, tools.search, tools.load, agent.list, session.history, datetime.now, os.info |
| http.request, browser.act (Medium); plan.propose raises the plan card | info.request is a question, not a card |

- **Per plan task:** the files it edits, plus one failing-check run, one plan tick and one verify-and-commit command (files + 3).
- **Per plan:** about 4 more (the plan file, the branch, the PR body file, push + PR).
- **Example:** a medium 4-task plan touching about 3 files per task raises about 4 × 6 + 4 = **28 cards**.
- **With sub-agents:** each delegate call is one card at the root, and every Medium-or-higher call a child makes raises a card for you too. The Agents question states the extra cards before you choose. A review panel on a medium plan adds about 4.

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

The frontend and design companions added in 2.1.0 install the same way; add only the ones you use:

```
sophon agents install frontend-developer --allow-delegation-from lead-developer
sophon agents install design-system-engineer --allow-delegation-from lead-developer
sophon agents install visual-designer --allow-delegation-from lead-developer
sophon agents install e2e-test-engineer --allow-delegation-from lead-developer
sophon agents install accessibility-reviewer --allow-delegation-from lead-developer
sophon agents install mcp-integration-engineer --allow-delegation-from lead-developer
sophon agents install technical-writer --allow-delegation-from lead-developer
```

Then check that **Effective targets** lists the companions. Keep each agent id equal to its package name: a `-2` suffix still matches, but avoid it. The lead finds companions through the `Family role: <slug>.` line in each one's when-to-use text; a missing companion is replaced by a stand-in that runs the lead's own rules with a pasted checklist, labelled lower confidence.

**3. Set effort.** A package cannot set effort. Recommended:

```
sophon agents models lead-developer --effort high
```

Do the same for software-architect, code-reviewer, security-reviewer, debugger and accessibility-reviewer; leave the rest at the default. A companion's effort reaches its delegated runs only while the lead's chat has no effort of its own (`/effort reset`).

**4. Upgrading from 1.0.0: set the delegation depth to 1.** Updating a package never changes its delegation settings, so a 1.0.0 lead keeps depth 2. Set it in Dashboard → Agents → Lead Developer → Delegation → Max depth, or with `PUT /api/agents/lead-developer/subagents`. Depth 1 keeps every consent question and card estimate at the top level, where the lead can ask you. Add the new companions (code-reviewer, debugger, security-reviewer) to an existing allow list.

**5. Know what allowing Medium-risk calls covers.** Allowing Medium-risk calls for the session (`/permissions` in the CLI) covers only the lead's own agent.delegate, code.git diff and blame, and GET http.request calls. It never covers a package agent's edits, commits or shell commands, and never any call a child makes.

**6. Learn the consent words.** The lead reads your messages, newest first, and the first match wins:

| You say | Effect |
|---|---|
| "ultracode off", "no ultracode" | back to asking each time |
| "no subagents", "no sub-agents", "without subagents", "don't use agents" | standing no: everything runs in one thread |
| "ultracode" | standing yes: waves run without the Agents question, after a one-line announcement of agents, waves, cards and cost |
| "use agents" (after a standing no) | back to asking |

The keyword decides consent only. Size still decides the phases, so a trivial change stays inline even with ultracode on, and a standing yes still needs plan approval.

**7. Plan mode on the Personal edition.** The Personal-edition Dashboard (and mobile) cannot approve a plan card. Use the CLI, or the GO escape: choose **Keep planning** and type `GO`. The lead replies "Approved in chat", asks you to switch the mode to "Ask before edits" (Dashboard: the mode chip or Alt+M; CLI: Shift+Tab or `/permissions default`) and send any message, then saves the plan as approved and runs it. Without plan mode, approval is a normal question and works everywhere.

**8. Set up pull requests.** Push and `gh pr create` run through os.execute in a shell that cannot prompt and has no GitHub credentials in its environment. Before the first PR, run `gh auth status` (or `gh auth login`, then `gh auth setup-git`) in your own terminal. HTTPS remotes work best. On an authentication failure the lead stops, quotes the error and gives you the commands; it never asks for a token in chat.

**Fewer cards: the local-install form (advanced, unsupported).** An agent you create yourself from these files, rather than install from the Marketplace, is your own: your standing approvals such as accept edits cover it, so a plan runs with far fewer cards. Keep to one form per agent id and do not mix a Marketplace lead with local companions of the same ids. A step-by-step recipe is planned for 2.1.

## Works best with

- **researcher**: Understand waves, each with a distinct focus, every claim cited with file:line or a URL.
- **software-architect**: Design judge panels (minimal, clean, pragmatic) and plans you can hand to the lead with "execute docs/plans/<file>".
- **developer**: Implement waves, one plan task per brief.
- **code-reviewer**: review lenses, refute votes, re-review rounds and the completeness critic.
- **security-reviewer**: a security lens when a change touches a trust boundary, and verification of security findings.
- **qa-engineer**: test-strategy gaps in Large reviews.
- **debugger**: one read-only hypothesis check when a repair keeps failing.
- **ui-ux-designer**: a UX critique lens for UI changes.
- **frontend-developer**: Implement waves for UI tasks: components, state, forms and browser checks.
- **accessibility-reviewer**: a WCAG 2.2 AA lens for UI changes.
- **design-system-engineer**, **visual-designer**, **e2e-test-engineer**, **mcp-integration-engineer** and **technical-writer**: plan tasks in their own areas, briefed by mode.

## Limits

- Sub-agents are blocking: no background agents, at most 5 per call, one level deep. Caps per task: Medium 10 agents in 5 calls, Large 25 agents in 14 calls. The estimate you approved is binding; anything dropped is logged as a `Cap:` line and listed in the report.
- Cards scale with fan-out, because every child's edits, commands and diffs raise cards at the top level.
- Every child pays for its own instructions uncached, and the prompt cache misses after any pause over 5 minutes, including approval waits.
- code.git cannot push, open PRs or make selective commits, so commits, pushes and PRs go through os.execute, which is always a card.
- On Windows, commands run in cmd or Windows PowerShell 5.1, never bash.
- Children cannot ask you questions; their questions come back to the lead, which asks you.
- Graph execution can still be picked on the plan card. Its steps commit as the plan says, and the lead reconciles the plan with the git log on your next message.

## What it never does

- Push silently, push to the default branch or force-push.
- Amend, rebase, reset, revert, clean, delete branches or change git config, unless you ask for that exact operation.
- Commit work its own checks have not proven, or let sub-agents commit.
- Start sub-agents without your consent, or exceed the estimate it gave you.
- Install agents or split work with Sophon workflows.
- Ask for a token in chat, or repeat secret values in plans, commits, PR bodies or briefs.
- Run `git init` in a folder that is not a repository.

## What's new in 2.1.0

- Seven companions joined the family: `frontend-developer`, `design-system-engineer`, `visual-designer`, `e2e-test-engineer`, `accessibility-reviewer`, `mcp-integration-engineer` and `technical-writer`. They are licensed Apache-2.0; this agent stays MIT. Add the ones you install to an existing Lead Developer allow-list.
- Delegates UI code to `frontend-developer`, adds `accessibility-reviewer` as a UI review lens, and knows each new companion's modes and brief keys.

## What's new in 2.0.0

- A full rewrite. The 1.0.0 persona is replaced by a plan-file workflow: sizing, approval, a branch, one verified commit per task, a review and a git menu.
- Consent-gated sub-agents with card and cost estimates, the `ultracode` and `no subagents` words, and the Ultracode-lite wave table.
- A TOOLS.md that pins agent.list, web.scrape and session.history.
- Delegation depth 1 for new installs, and the heartbeat block removed. **Updating does not change delegation settings**: upgraders set the depth to 1 themselves (step 4 above).
- New companions code-reviewer, debugger and security-reviewer: add them to an existing allow list.

## Credits and license

Ideas re-expressed in our own words also come from JuliusBrussee/caveman (Apache-2.0, © 2026 Julius Brussee); and EveryInc/compound-engineering-plugin (MIT, © 2025 Every).

Workflow patterns adapted, not copied, from obra/superpowers (MIT, © 2025 Jesse Vincent) and Anthropic's Claude Code plugins (feature-dev, pr-review-toolkit, code-review, security-review, frontend-design; Apache-2.0). Licensed under the MIT License; see LICENSE.
