# Development agents: the Buildersoft development family 3.0.0

Twenty-one Sophon Marketplace agents that work on a code repository the way Claude Code does, plus an
optional reference skill they read from:

1. They find out what you want and why, then size the request.
2. They plan in a markdown file you approve (a project first gets a short design note), then carry it out task by task with a live todo list.
3. They write the failing test first, verify with real commands and commit each verified task on a feature branch.
4. At the end they offer a pull request or a local merge.

Only Lead Developer starts sub-agents, and only with your consent.

Twenty of the agents are the development roster: Lead Developer and its nineteen companions, four of them
new in 3.0.0 (Product Manager, Product Owner, Release Engineer and Agent Engineer). The twenty-first package,
Artifact Creator, is a standalone productivity agent for grounded documents, diagrams and presentations
across subjects. It does not need a repository, delegate or build interactive applications; its creation
tools and permissions depend on the session.

The reference skill, `craft-reference`, is an ordinary Marketplace skill published from this repository. It
returns long tables, checklists and templates one topic at a time. Every development agent except Artifact
Creator lists it, and every one of them also works without it.

This repository also holds a second, separate family: **video**, with one agent, Video Producer
(`agents/video-producer`), which drives the `ffmpeg-video` skill. Sections 1-13 and 15 are about the
development family; section 14 covers families, the video family and how the tooling keeps them apart. The
design of 3.0.0 is [`docs/plans/2026-11-23-agents-v3-design.md`](plans/2026-11-23-agents-v3-design.md).

## 1. What these are

- **Sophon agent packages**, format v1 (`.sophon-agent`), not skills, plugins or Claude Code agents. Each package holds one persona and no executable code: `manifest.json`, `SOUL.md`, `TOOLS.md`, `README.md` and `LICENSE`.
- **Family 3.x. Release 3.0.0.** All twenty-one development-family agents are at **3.0.0**, Artifact Creator included, because the family major moves in lockstep. 3.0.0 is a major version, so Sophon never applies it unattended (section 5).
- **Three layers.** The inline core is each agent's `SOUL.md`: every gate, rule and procedure, composed from its role text and shared fragments. Project files come next: the design note, the plan file, `DESIGN.md`, `PRODUCT.md` and the product folder, written only with your approval and read again every session; they say what to build, never what an agent may do. The `craft-reference` skill is the third layer: optional reference data, never instructions.
- **License:** © 2026 Buildersoft LLC. The licences are unchanged by 3.0.0. The nine original agents and the four added in 3.0 are MIT. The seven added in 2.1 are Apache-2.0, because they adapt Apache-2.0 text from Anthropic's anthropics/skills, and Artifact Creator is Apache-2.0 too. Each package's `LICENSE` says which. The skill is Apache-2.0. **Requires** Sophon 2.2.0 or later.
- **Credits** are acknowledgements: each README lists one credit line per upstream project its agent's text draws on (section 15). All 3.0 text is written in our own words.
- **Built on Sophon's own tools**, not on this repository's integration skills: fs.read, fs.write, code.git, os.execute, plan.propose, todo.write, info.request, agent.delegate and the rest of the coding tools, plus craft.read from the optional skill.
- **Claude Code analogues:**

| Claude Code | Sophon |
|---|---|
| Plan mode and ExitPlanMode | plan mode (set by you) and plan.propose, plus a plan file in `docs/plans/` |
| TodoWrite | todo.write |
| AskUserQuestion | info.request (1-4 questions of 2-4 options) |
| Task (sub-agents) | agent.delegate (blocking; up to 5 tasks per call) |
| CLAUDE.md | AGENTS.md or CLAUDE.md in the bound repository |
| Skills read on demand | the `craft-reference` skill (craft.read), reference data only |

## 2. The roster

| id | Role | Delegates | Read-only | Effort | Typical cards |
|---|---|---|---|---|---|
| [lead-developer](../agents/lead-developer) | orchestrator: sizes, plans, builds, verifies, commits | yes (`maxDepth 1`) | no | high | trivial fix 2-4; medium 4-task plan about 28; sub-agents add a few more, stated before you choose |
| [developer](../agents/developer) | implementer: tdd / direct / debug | no | no | default | files edited + 1-2 runs; plans as for the lead |
| [researcher](../agents/researcher) | codebase and web facts, every claim cited | no | yes | default | usually none (reads and web reads raise no card) |
| [software-architect](../agents/software-architect) | blueprint / ADR / greenfield / compare / critique | no | yes, except its plan, ADR or design note | high | one per saved file |
| [code-reviewer](../agents/code-reviewer) | review / refute / re-review / completeness | no | yes | high | 1 for the working tree; a range needs about one command per diff group |
| [qa-engineer](../agents/qa-engineer) | verification gate, regression checks, tests | no | no (tests, when asked) | default | one per chained check; browser checks up to 6 |
| [debugger](../agents/debugger) | root cause first, then a fix when asked | no | no (fix + regression test, when asked) | high | one per reproduction or check run |
| [security-reviewer](../agents/security-reviewer) | exploitable vulnerabilities only | no | yes | high | 1-2 (the diff, a branch range) |
| [ui-ux-designer](../agents/ui-ux-designer) | direction / build / critique / copy / judge | no | no (UI presentation files) | default | direction none until you pick; build as for developer; browser checks one each |
| [frontend-developer](../agents/frontend-developer) | UI implementer: component / direct / artifact / perf | no | no | default | files edited + 1-2 runs; plans as for the lead |
| [design-system-engineer](../agents/design-system-engineer) | audit / tokens / theme / playground / brand-check | no | no (tokens, themes, components) | default | audit none; token or theme changes as for developer |
| [visual-designer](../agents/visual-designer) | concept / art / generative / image / motion (image.generate opt-in) | no | no (asset files) | default | concept none; one per asset file written, plus one per render or check run |
| [e2e-test-engineer](../agents/e2e-test-engineer) | browser end-to-end tests: write / visual / flake | no | no (e2e tests) | default | per test: its edits + a red and a green run; flake: one per repeat or bisection run |
| [accessibility-reviewer](../agents/accessibility-reviewer) | WCAG 2.2 AA: audit / review, VERDICT `CONFORMS` or `GAPS` | no | yes | high | 1 for the working tree (the diff); browser checks one each |
| [mcp-integration-engineer](../agents/mcp-integration-engineer) | MCP servers: design / build / evals | no | no | default | files edited + 1-2 runs; plans as for the lead |
| [technical-writer](../agents/technical-writer) | documentation: draft / edit / reader-test | no | no (documentation files) | default | draft: the skeleton + one per section; edit: one per file; reader-test one per harmless command |
| [product-manager](../agents/product-manager) | discover / analyst / brief / PRD / prioritise / pre-mortem | no | yes, except its product documents | high | none while it interviews or researches; one per saved document |
| [product-owner](../agents/product-owner) | spec / slice / refine / validate / accept / replan / triage | no | yes, except its requirements and story files | high | one per saved file; accept at root: one per check run and per recorded verdict |
| [release-engineer](../agents/release-engineer) | check / ship / deploy / watch / upgrade / rollback | no | no (version, changelog and dependency files) | default | check none; a ship costs the files it edits plus about five; each outward step one more |
| [agent-engineer](../agents/agent-engineer) | agent instructions: design / rule / test / review / diagnose | no | no (agent and skill instruction files) | high | review and diagnose none; plans as for the lead |
| [artifact-creator](../agents/artifact-creator) | grounded reports, explainers, guides, diagrams and presentations | no | no (artifact files) | default | depends on the available creation tools |

The seven readers (researcher, software-architect, code-reviewer, security-reviewer, accessibility-reviewer, product-manager and product-owner) never commit. Software Architect saves only a plan, an ADR or a design note, and Product Manager and Product Owner only their product documents, each after you approve it. The writers (developer, qa-engineer, debugger, ui-ux-designer, frontend-developer, design-system-engineer, visual-designer, e2e-test-engineer, mcp-integration-engineer, technical-writer, release-engineer and agent-engineer) use the same sizing, plan and git rules as the lead when you talk to them directly.

- **Design.** UI/UX Designer owns the direction of a screen and the presentation of screens that exist; new component markup and motion wiring go to frontend-developer, tokens and the token block of `DESIGN.md` to design-system-engineer, and imagery to visual-designer. Visual Designer calls image.generate only when you opt in.
- **Product.** Product Manager decides with you whether something is worth building and for whom, and alone writes `PRODUCT.md`. Product Owner turns an agreed goal into requirements with permanent ids (`R<n>`) and small stories, and accepts or rejects what was built from the evidence. Both write under `docs/product/`.
- **Release.** Release Engineer takes a merged branch to a released, deployed and watched version, and back when it goes wrong. Every step that leaves the machine is asked first, every time.
- **Agent instructions.** Agent Engineer writes and tests the instructions of Sophon agents and skills, and changes an instruction only after it has seen the behaviour the change is meant to fix.
- The lead hands UI implementation tasks to frontend-developer and adds accessibility-reviewer, a ui-ux-designer critique, qa-engineer or a release-engineer check as review lenses where the change needs them. Deciding what to build, writing requirements with you and shipping need you at the root, so the lead names the agent and the sentence to say to it instead of delegating them.

## 3. Where they work

- **Bound and trusted.** Run `sophon` in the repository so the session is bound, then `/trust` the folder. Trusted turns load the project instructions (AGENTS.md or CLAUDE.md) and a "Git state" block, which the agents use instead of a status call.
- **Unbound.** Paths are host-wide, nothing can be rewound and AGENTS.md is not loaded. The agents read, analyse and plan, say once that running `sophon` in the project folder binds the session, and edit or run commands only if you ask again after that.
- **Pick an agent yourself.** The router never picks a package agent on its own. Use `/agent lead-developer` in a chat, or start one with `sophon chat --agent lead-developer`.
- **Shells.** On Windows, os.execute runs cmd (preferred for git and gh) or Windows PowerShell 5.1, never bash. On macOS and Linux it runs bash or sh. Nothing runs in the background, so the agents never start servers or watchers.

## 4. Install order

1. Install the reference skill if you want it: `sophon skills install craft-reference`. It is optional. An agent install lists it as a required skill and completes when you decline it or it is unavailable; the agent then works from what it carries.
2. Install the lead: `sophon agents install lead-developer`.
3. Open Dashboard → Agents → Lead Developer → Delegation, turn on **Restrict to allow list** and save. The list starts empty, and `--allow-delegation-from` adds a companion to it only while this is on, so do this before step 4.
4. Install each companion with permission for the lead to delegate to it:

```
sophon agents install developer --allow-delegation-from lead-developer
sophon agents install researcher --allow-delegation-from lead-developer
sophon agents install software-architect --allow-delegation-from lead-developer
sophon agents install code-reviewer --allow-delegation-from lead-developer
sophon agents install qa-engineer --allow-delegation-from lead-developer
sophon agents install debugger --allow-delegation-from lead-developer
sophon agents install security-reviewer --allow-delegation-from lead-developer
sophon agents install ui-ux-designer --allow-delegation-from lead-developer
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

5. Confirm that **Effective targets** lists every companion you installed.
6. Keep each agent id equal to its package name. The lead finds companions through the `Family role: <id>.` line in each one's when-to-use text, then by id, then by display name. A `-2` suffix still matches, but avoid it. The same line lists the companion's modes and brief keys, which the lead reads instead of carrying a list of its own.

Install Artifact Creator separately when needed: `sophon agents install artifact-creator`. It is a standalone productivity agent, not a lead companion, and it does not use the skill.

A missing companion is not fatal. The lead runs a stand-in (its own rules plus a pasted role checklist), at most 2 per wave, labels the result lower confidence and tells you once which agent to install.

## 5. Settings a package cannot carry

A package can set only `defaults.subAgents` (applied on the first install) and model routing (`inherit` here). It cannot carry a delegation allow list, standing approvals, model pins or effort.

- **Upgraders from 2.x.**
  - 3.0.0 is a major version, so Sophon never applies it unattended. Take it yourself, one agent at a time: `sophon agents update <id>`.
  - Update every family agent you have installed in one sitting. In between, Lead Developer 3.0.0 gives a companion below 3.0.0 the brief that 2.x understands and tells you once which agents to update, and a 3.0.0 companion still accepts a 2.x brief. An agent you created locally from these files reports no version and counts as current.
  - Four agents are new: `product-manager`, `product-owner`, `release-engineer` and `agent-engineer`. Install the ones you want with `--allow-delegation-from lead-developer` (step 4 of section 4). Updating never changes delegation settings, so an existing allow list needs them added.
  - The instructions are longer. Each agent's README states how many more tokens a new session of it, and each sub-agent run of it, reads than in 2.x.
  - 3.0.0 lists the optional `craft-reference` skill. Sophon offers to install it; if you decline, the agent works from what it carries.
  - Your own edits to an installed agent pause its updates. Add `--discard-local-changes` to replace them.
- **Upgraders from 1.0.0: set the lead's delegation depth to 1.** Updating a package never changes its delegation settings, so a 1.0.0 lead keeps `maxDepth 2`. Set it in Dashboard → Agents → Lead Developer → Delegation, or with `PUT /api/agents/lead-developer/subagents`. Depth 1 keeps every consent question and card estimate at the top level, where the lead can ask you.
- **Effort.** Recommended `high` for lead-developer, software-architect, code-reviewer, security-reviewer, debugger, accessibility-reviewer, product-manager, product-owner and agent-engineer; leave the rest at the default:

```
sophon agents models lead-developer --effort high
sophon agents models software-architect --effort high
sophon agents models code-reviewer --effort high
sophon agents models security-reviewer --effort high
sophon agents models debugger --effort high
sophon agents models accessibility-reviewer --effort high
sophon agents models product-manager --effort high
sophon agents models product-owner --effort high
sophon agents models agent-engineer --effort high
```

  A companion's effort reaches its delegated runs only while the lead's chat has no effort of its own (`/effort reset` in that chat).
- **Allowed Medium-risk calls for the session** (the `/permissions` setting, Medium) cover only the root agent's own Medium calls that change nothing in the workspace: agent.delegate, code.git diff and blame, GET http.request, browser.act and memory.forget. They never cover a package agent's edits, commits or shell commands, and never any call a sub-agent makes.

**Cards you should expect.** Marketplace installs are third-party for life: your standing approvals (accept edits, remembered commands, allow all) do not cover them.

| Card on every call | May raise a card | No card |
|---|---|---|
| fs.write, the edit tools, fs.move, fs.copy, fs.delete, fs.create_directory (bound edits always ask) | code.git diff and blame (Medium) | fs.read, fs.list, fs.find, fs.search, fs.info |
| os.execute (Critical; never remembered for a package agent) | agent.delegate (Medium; at the root, covered by allowed Medium-risk calls for the session) | code.git status, log, branch list, remote, stash list |
| every code.git write (Medium) | | web.search, web.scrape, browser.screenshot, canvas.render (Low) |
| http.request, browser.act, memory.forget (Medium) | | todo.write, memory.search, memory.write, tools.search, tools.load, agent.list, session.history, datetime.now, os.info, diff, craft.topics, craft.read |
| plan.propose raises the plan card | | info.request is a question, not a card |

- **Inside a sub-agent,** every Medium-or-higher call raises a card for you, whatever the session allows.
- **Per plan task:** the files it edits + 1 failing-check run + 1 plan tick + 1 verify-and-commit command.
- **Per plan:** about 4 more (the plan file, the branch, the PR body file, push + PR). A design note adds one (its save).
- **Example:** a medium 4-task plan touching about 3 files per task raises about 4 × 6 + 4 = **28 cards**.
- **With sub-agents:** a task built and reviewed by a delegated pair comes to its files edited + 4, plus any card agent.delegate or the reviewer's diff raises, which the estimate does not count. "Build inline, then review" on that medium plan comes to about 29 in all. Each option of the "Agents" question states its cards before you choose. For far fewer cards, see the local-install form (section 10).

## 6. Discovery, the design note and plan files

**Discovery.** At the root, a request to build or change something starts with Discovery in the eight agents that carry it (lead-developer, developer, frontend-developer, ui-ux-designer, design-system-engineer, visual-designer, software-architect and agent-engineer). Questions, reviews, bugs with a known symptom and delegated work skip it.
- Nothing open (the request names the thing and the place, and one approach is clearly right): the agent asks nothing. It puts its understanding and the approach into the plan question or plan card, where you correct them.
- Something open: the agent asks, the reason for the work first, plays its understanding back in at most 200 words with its own fill-ins marked, and offers 2-3 approaches with their trade-offs when more than one is real. You choose.
- **Opt-out:** say "just build it" or "no questions". The agent stops asking discovery questions, writes `Discovery: opted out` on the plan and turns each guess into an `Assumption:` line. Every approval, and every choice of what you will see (such as the "Design" question), is still asked.
- What was agreed goes into the plan's Context, Approach and Global constraints. Plan approval is the gate: nothing is built, scaffolded or installed before it.

**The design note.** A project (Large work, a new subsystem, or work whose shape discovery changed) gets a written design before the plan, from Lead Developer or Software Architect: at most 600 words under `# Design: <title>`, with Why, Goals, Non-goals, Constraints, Approaches and the one chosen, and Left to the builder. Before you see it, the agent reads it as a builder who saw neither the chat nor the code and turns each guess into a cited line, a decision, an assumption or one round of questions. It is saved as `docs/plans/YYYY-MM-DD-<slug>-design.md`, and the plan's `Spec:` line names it. A later change of direction adds a `Decision (YYYY-MM-DD):` line; the approved text is never rewritten.

**The save question.** A document an agent saves with your approval (a design note, an architect's plan or ADR, `DESIGN.md`, a product document, a story) goes through one routine: the whole draft in the reply, then one question with [Save (Recommended)], [Change something] and [Stop]. It is written only on a yes, as one card. "Stop" or no answer saves nothing and leaves the draft in the chat. A draft file is written only when you ask for one. After a new `DESIGN.md` or `PRODUCT.md` at the repository root, the agent offers its AGENTS.md line (section 11) and adds it only on a yes.

**Plan files.**
- Every Medium or Large task gets `docs/plans/YYYY-MM-DD-<slug>.md` in one fixed format: Goal, Context, Approach, Global constraints, Out of scope, Verification, Review focus, Orchestration (lead, when sub-agents run), Tasks, Risks and Progress.
- Each task lists its files, `Depends on:`, `Covers:` (requirement ids, or none), `Interfaces:` (what it uses from earlier tasks and the exact signatures it produces), checkbox steps, the exact `Run:` command, the `Expected:` result and the `Commit:` subject.
- The header carries `Status:` (draft, approved, in-progress, blocked, done, cancelled), the date, agent, size, base and branch, `Approved:`, `Consent:`, `Execution:`, `Spec:` (the design note, a chat date or none), `Discovery:` (full, fast, opted out or none), `Voice:` (plain or terse) and `Request:` (your words verbatim, or the path of the story or requirements it builds).
- Notes in a plan are `Assumption:`, `Open question:` and `Decision (YYYY-MM-DD):` lines; an open question that changes a task is settled before approval.
- Progress lines record each task, repair, block, ruling and cap, one `Review:` line, and one `Parked:` line for each minor point left for later. The word "parked" replaces the 2.x "deferred".
- The file is the durable state. "Continue" after a gap or a compacted conversation makes the agent find the newest open plan (a `-design.md` note is not a plan) and reconcile it with the git log. A task counts as done only when it is ticked and its commit subject is in the log, and a committed task is never redone. Consent and voice come back from the plan's own lines.
- **Another plan folder:** put a line `- Plan directory: <path>` in the project instructions (AGENTS.md), or say which folder in plain words.

**Plan mode off** (the usual case): the agent writes the plan file as a draft (one card that shows it) and asks one "Plan" question, with its understanding and the approach in 2-4 sentences:
- [Approve and start (Recommended)]
- [Change something]
- [Cancel]

The question also carries the "Agents" question when sub-agents would help. No answer means it does not start. An approved file that is more than 7 days old, or whose base commit is gone, gets one more question first: [Run it (Recommended)], [Re-plan] or [Cancel].

**Plan mode on** (bound or not): the agent explores read-only, settles the choices with info.request, then calls plan.propose with at most 4 linear steps, so the card recommends **Inline**. Choose Inline: the agent then writes the plan file, creates the branch and runs the tasks itself. A design note is shown first, and the card's first step saves it. The summary's first three lines are:

```
Plan file (written on approval): <path>
Execution: choose Inline — I run it task by task, verify each task and commit it on sophon/<slug>.
Can't press Approve (Dashboard on Personal, mobile)? Choose Keep planning and type GO.
```

**The GO escape.** The Personal-edition Dashboard (and mobile) cannot approve a plan card:
1. Use the CLI, or choose **Keep planning** and type `GO`.
2. The agent replies "Approved in chat" and asks you to switch the mode to "Ask before edits" (Dashboard: the mode chip or Alt+M; CLI: Shift+Tab or `/permissions default`). Then send any message.
3. On that turn it saves the plan as `Approved: <date> via chat (plan card GO)` and runs it.

**Architect plans.** Software Architect runs Discovery, then sketches two designs under opposing constraints, and you pick before any plan. It drafts the plan in the same format, saves it through the save question, and hands it over with: "To execute: tell Lead Developer 'execute <plan path>'". It never calls plan.propose; in plan mode it returns the draft and the plan.propose JSON in its reply. The lead runs an approved file directly, asking once first if the file is more than 7 days old or its base commit is gone.

**Graph execution** can still be chosen on the plan card. Its steps commit as the plan says, and the agent reconciles the plan with the git log on your next message.

## 7. Consent words, voice and the lead's phases

The lead scans your own messages, newest first; the first match wins.

| You say | Effect |
|---|---|
| "ultracode off", "no ultracode" | back to asking each time |
| "no subagents", "no sub-agents", "without subagents", "don't use agents" | standing no: one thread, zero agent.delegate calls |
| "ultracode" (any case) | standing yes: "Team per task" at Medium and Large, without the Agents question, after a one-line announcement of agents, waves, cards and cost |
| "use agents" (after a standing no) | back to asking |

- The keyword decides consent only. Size still decides the phases: a trivial change stays inline even with ultracode on, and a standing yes still needs plan approval.
- Without a standing answer, the lead asks once per task (header "Agents") and only when delegation clearly helps. The recommended option comes first, Solo is always offered, and each option states agents, waves, cards in all and extra, and "≈N× Solo tokens".
- No answer, or a skipped question, means Solo. The answer is written on the plan's `Consent:` line.
- The other nineteen development agents cannot start sub-agents. Asked for "ultracode", they say that Lead Developer runs multi-agent work, then do the task themselves and run the same checks one after another. Artifact Creator also cannot delegate.

**Other words the agents honour.**
- "just build it" or "no questions": in the eight agents with Discovery, discovery questions stop (section 6). The "Design" question and every approval are still asked.
- "terse" or "caveman": short sentences or labelled fragments (Cause, Fix, Risk), every negation, number and unit kept. "normal" switches back. The default is plain voice: full sentences for a reader who saw none of the tool calls. Questions, options, approvals, warnings, error explanations, ordered steps and everything saved to a file stay in full sentences either way. The plan's `Voice:` line keeps the choice across a gap.

**The options at Medium** (the "Agents" question):
- [Build inline, then review (Recommended)]: the lead builds every task itself, then 3 reviewer lenses, 3 refuters and 1 critic review the branch: about 7 agents in 3 waves, about 29 cards for the 4-task example, ≈3.5× Solo tokens.
- [Team per task]: an implementer and a reviewer for each task, then one review of the whole branch.
- [Solo]: no sub-agents; the lead reviews its own diff lens by lens; about 28 cards; 1×.

At Large, [Team per task (Recommended)] comes first. A standing "ultracode" picks Team per task at both sizes, about 7× Solo tokens on four tasks.

**The phases** (lead, with consent; one wave is one agent.delegate call):
- **Understand** (Large, or Medium surveying more than 15 files or mixing web and code research): 2-5 researchers, one focus each; the lead reads the key files they name itself.
- **Design** (Large): 2-3 architects judged on a written 14-point rubric. The winner is the lead's recommendation; when the top two are close and differ for you, you choose.
- **Builder check** (a design note): one software-architect critiques the draft before you see it.
- **Design direction** (UI work whose look is left to you): the "Design" question (section 12). A direction round shows four options side by side and you pick; never a child, a judge run or the lead.
- **Implement, team per task:** one task at a time, an implementer and a code-reviewer in one call. A finding starts a fix round with a fresh implementer, at most 3 rounds per task, the third fixed by the lead; what stays open gets a ruling. Minor findings are parked and never start a round. Parallel implementers (at most 3) run only on disjoint files.
- **Final review:** after per-task reviews, one cross-task reviewer over the branch; after inline tasks, 3 lenses at Medium and 4-5 at Large, plus security-reviewer, accessibility-reviewer, a ui-ux-designer critique, qa-engineer or a release-engineer check where the change needs them.
- **Refute:** 3 votes on every Critical and Important finding; 2 of 3 must confirm.
- **Fix and re-review:** each confirmed finding gets a test that fails before the fix. After per-task reviews the re-review runs once; after a lens panel it repeats until nothing serious is new, at most 3 rounds.
- **Critic** (Large, or Medium with 4 or more tasks): a completeness check against your request; a plan built from a story adds Product Owner's acceptance.
- **Bug hunt** ("find bugs", "audit"): up to 3 rounds of 3-5 finders, new findings refuted, until a round adds nothing.
- In plan mode only Understand, Design and Design direction run.

**Caps:** Medium at most 20 agents in 10 delegate calls; Large 44 in 22; at most 5 entries per call. A reviewed task or a fix round costs 2 agents and 1 call. The estimate you approved is binding, and anything dropped is logged as a `Cap:` line in the plan and the report.

## 8. Git and pull requests

- **Branch first.** An approved plan runs on `sophon/<slug>` (or the repository's own branch naming), created with one `git checkout -b`. Outside a plan, agents commit only when you ask, on the current branch.
- **One commit per verified task.** The task's check, the staging and the commit run as one command. A failing check means no commit: the agent repairs at most 3 times, then marks the task BLOCKED and asks you. The commit uses a trailing pathspec, so files you staged yourself stay out of it. Task 1 also commits the untracked documents the plan cites, such as its design note or story.
- **Review before the menu.** Before its last plan edit, the agent re-reads every file the plan changed against your request, the global constraints and the review focus, fixes what is wrong with a check that failed first, and parks each minor point.
- **Commit trailer**, the last line of every commit message:

```
Co-Authored-By: Sophon <noreply@buildersoft.io>
```

- **The finish menu** (one info.request with header "Git"):
  - [Push + open PR (Recommended)]: 2 cards, the PR body file then the command.
  - [Merge into `<base>` locally]: 1 card. On a clean tree it merges the branch into the base here, runs the checks on the merged result and commits only if they pass; on a failure it aborts the merge and goes back to the branch. Nothing is pushed, and the branch is kept.
  - [Keep local]: nothing leaves this machine.

  Keep local becomes the recommended first option when something is unverified, there is no remote, or the remote is not GitHub. A non-GitHub remote turns option 1 into "Push branch". No answer means Keep local.
- **Discard is not on the menu.** When you ask for it, the agent lists what would be lost (the branch, its commits, the committed plan file), asks once more, requires a clean tree and only then deletes the branch.
- **Lesson** (lead, at Medium and above, or when you ask): at most one lesson, asked as "Lesson" in the same info.request as "Git", in the cheapest form that stops a repeat: a check the project runs, else one AGENTS.md line, else a memory note for a preference of yours. It is saved only on a yes, as its own commit before any push.
- **PR body.** Summary, Changes, Test plan and the plan path, with this footer as the last line:

```
🤖 Generated with [Sophon](https://sophon.buildersoft.io)
```

- **Never, unless you ask for that exact operation:** amend, rebase, reset, revert, clean, discard changes, delete branches, force-push, push to the default branch, change git config. Nothing is pushed silently.
- **code.git cannot push or open PRs,** and its commit stages everything. So branches, commits, merges, pushes and `gh pr create` go through os.execute, which is always a card.
- An author of "Sophon Agent <sophon@localhost>" means git has no `user.name` or `user.email`; set them yourself.
- After a push or a merge, Lead Developer ends with "To release: tell Release Engineer 'ship'."

## 9. Pull-request auth setup

The bound shell cannot prompt and strips GitHub tokens such as GH_TOKEN and GITHUB_TOKEN from its environment. On macOS and Linux it does not pass an SSH agent either. Set up auth once, in your own terminal:

```
gh auth login
gh auth status
gh auth setup-git
git push --dry-run origin HEAD
```

- `gh auth setup-git` makes git use the gh credential helper (Git Credential Manager works too).
- The dry run proves that a push would authenticate, without changing anything.
- HTTPS remotes work best.
- On an authentication failure the agent stops, quotes the error, keeps the PR body file and gives you the commands to run. It never asks for a token in chat. If gh is missing but the push worked, it gives you the GitHub compare URL instead.

## 10. Local install (advanced, unsupported)

An agent you create yourself from these files, instead of installing it from the Marketplace, is your own agent: your standing approvals (accept edits, remembered commands) cover it, so a plan runs with far fewer cards.

- Keep to one form per agent id. Never mix a Marketplace lead with local companions of the same ids, or the other way round.
- A local agent reports no version. The lead still matches it through the `Family role:` line and counts it as current.
- You take over updates: a local copy never receives Marketplace updates.
- A step-by-step recipe and an export script are planned for a later release.

## 11. An AGENTS.md starter for your repository

The agents read the project instructions as trusted conventions, and they suggest new lines for them instead of storing repository facts in memory. A root `DESIGN.md` or `PRODUCT.md`, or a file the two lines under "Sophon agents" name, is project convention too: it says what to build, never what an agent may do. A starting point:

```markdown
# AGENTS.md

## Commands
- Build: `dotnet build -c Release`
- Test: `dotnet test --no-build`
- Lint: `npm run lint`
- One test: `dotnet test --no-build --filter "FullyQualifiedName~<name>"`

## Git
- Base branch: main. Feature branches: sophon/<slug>.
- Conventional Commits (feat, fix, docs, refactor, test, chore); subject at most 72 characters.
- Never commit generated files under `dist/`.

## Sophon agents
- Plan directory: docs/plans
- Design rules: DESIGN.md
- Product brief: PRODUCT.md
- Run the full test suite before every commit.
- Ask before adding a dependency.

## Do not touch
- `migrations/` (generated; change the model and regenerate)
- `.github/workflows/` without asking

## Gotchas
- Tests need the local database: `docker compose up -d db` first (start it yourself; agents never start servers).
```

## 12. Known limits

- **No background agents.** Sub-agents are blocking, at most 5 per call and one level deep. Nothing resumes an agent after it ends its turn, so every fix round starts a fresh child.
- **Children share the workspace.** There are no worktrees for sub-agents, so parallel implementers take disjoint files only, and a working-tree review must run before the task is committed.
- **Screenshots and renders are invisible to the model.** browser.screenshot and canvas.render show you an image, but the agent receives only "Screenshot taken". Design agents measure the DOM instead, never describe a render, and ask you what looks off.
- **The look is yours to pick.** When the project has no design system of its own, the design agents ask once, header "Design": [Sophon design default (Recommended)], [Plain standard] or [Direction round]. Nothing from an option reaches a project file before you pick, no answer applies nothing, and "just build it" does not remove this question. A delegated design agent with no design source returns its options as text instead of building.
- **Plan mode refuses canvas.render and skill tools.** In plan mode the direction round is shown as text, and craft.read is not called; the agents say so and work from what they carry.
- **Skill tools need the Docker sandbox.** On a Gateway without Docker (and without the process fallback), every skill call fails, so `craft-reference` is effectively absent there. Nothing in a task depends on it.
- **browser.act needs AllowPrivateNetwork for localhost.** It opens `localhost` only when `Sophon:Browser:AllowPrivateNetwork` is on, and it needs Playwright Chromium on the Gateway host. On a blocked navigation the design agents stop browser work, report the setting and continue from the code.
- **code.git has no push,** no PR and no selective commit, so those steps, and the local merge, go through os.execute cards.
- **Cards scale with fan-out:** every sub-agent's edits, commands and diffs raise cards at the top level.
- **Caching:** every new session, including every sub-agent, pays for its own instructions uncached. The cache also misses after any pause over 5 minutes (approval and question waits count) and after each tool load.
- **Questions:** info.request waits 15 minutes, and sub-agents, heartbeat and cron runs cannot ask at all. No answer is never a yes: nothing the question asks about runs.
- **Plan approval on the Personal-edition Dashboard** needs the CLI or the GO escape (section 6).
- **Sophon v3** is a branch, not a release. The packages are checked against it before release (the package format, the scanner phrase lists, no removed memory tool named, the localhost and Docker limits above); v3 is a new install, so you reinstall the same files there.
- **Accepted on plausible but unrun evidence,** each to be checked once in the owner smoke scenarios (D2, L3 and Q1, plus the one push in [the evals README](../tests/agents/evals/README.md), section 3) before release:
  - pathspec commits keeping pre-staged files out;
  - PowerShell 5.1 quote stripping;
  - the cmd stash grouping in QA's red/green check;
  - gh and Git Credential Manager under the bound shell;
  - SSH push on Windows.

## 13. Maintainers: build, test and publish

**Sources.** `agents/<id>/` holds only the 5 package files. Each `SOUL.md` is generated, and so is the `README.md` of every development agent: never edit them by hand. `build/Compose-AgentSouls.ps1` composes the READMEs after the SOULs, from `readmes/<id>.md` and the shared `fragments/readme/<NN-id>.md` blocks (`{{> readme/<NN-id>}}`; a source includes only fragments of its own kind). Besides the family values a README source may use `{{= FamilyVersion}}`, `{{= Id}}`, `{{= DisplayName}}`, `{{= License}}`, `{{= SoulTokens}}` and `{{= SoulTokensDelta}}` (composed SOUL bytes / 3.8, and the growth against the 2.1.0 baseline, each to the nearest hundred); a hand-written figure (a number, optionally with a k suffix, up to three words before "tokens", as in "4,300 tokens", "about 4,300 more tokens" or "8k tokens") is a compose error. A line `{{# roster}}` becomes the roster table (rows from `RosterOrder` and each agent's `Summary`, `Changes` and `Commits`, Delegates from `SubAgents`, the agent's own row in bold) and `{{# credits}}` its credit lines and licence sentence. `-Check` reports README drift like SOUL drift. The video family has no `readmes/` folder, so its README stays hand-written.

Each agent's `LICENSE` must be byte-identical to its canonical source: the root `LICENSE` for MIT,
and `build/licenses/Apache-2.0.txt` for Apache-2.0. The roster can override the family license,
category and required tags per agent; the source checker resolves the canonical license from the
declared license rather than accepting arbitrary paths.

```
build/agent-src/
  families.psd1               the family registry (section 14)
  family.psd1                 development roster, fragment order, SoulCap, RoleCap, SubAgents, Effort,
                              License, Category, RequiredTags, Skills, Credits, Values (commit trailer,
                              PR footer, plan folder), AllowedHosts, SkillPolicy, FragmentCaps, Method,
                              RosterOrder and the roster-table cells
  souls/<id>.md               role text + include lines ({{> soul/<NN-id>}})
  fragments/soul/<NN-id>.md   37 shared fragments, at most 4,096 bytes each
  readmes/<id>.md             README source per development agent ({{> readme/<NN-id>}}, {{# roster}}, {{# credits}})
  fragments/readme/<NN-id>.md shared README blocks
  families/video/             the video family: family.psd1, souls/, fragments/soul/
  catalog/sophon-tools.psd1   real Sophon tool names (pinned to sophon a431e1a64, v2.2.2)
  catalog/scan-rules.psd1     the marketplace and runtime scanner rules the preflight replays
  catalog/soul-baseline.psd1  the composed SOUL sizes at 2.1.0 (budget table, SoulTokensDelta)
  catalog/doc-counts.psd1     DOC-COUNT documents, allowed numbers and history phrases
build/craft-reference/        the reference skill's topic sources, registry (topics.index.json, topics.lock.json),
                              generate.py and Test-CraftSources.ps1
skills/craft-reference/       the generated skill: manifest.json, main.py, README.md, LICENSE, notices
build/licenses/Apache-2.0.txt the LICENSE the Apache-2.0 agents ship
build/AgentFamily.psm1        registry, roster, composer, Method registry, anchors, DOC-COUNT
build/AgentLint.psm1          tool-name lint, scanner preflight, TOOLS.md parser, manifest checks
build/Compose-AgentSouls.ps1  [-RepoRoot] [-Agents] [-Check] [-OutDir] [-Explain] [-Family] [-Omit]
build/Test-AgentSources.ps1   sections A-I and M per family, N once, no Sophon CLI needed (CI runs it) [-Agents] [-Family] [-Release]
build/Build-AgentPackages.ps1 [-RepoRoot] [-OutputDir] [-Agents] [-ValidateOnly] [-Family] [-Release]
tests/agents/                 Test-AgentPackages.ps1 (A-N), Compare-AgentSouls.ps1, fixtures/, evals/
```

**Fragments.** The development family has 37 shared fragments: the worker and care rules (`01` to `06`), sizing, discovery and the design note (`07`, `07b`, `07c`), plan files, running a plan, the plan card and the save routine (`08a` to `08d`), quality, test first, receiving review and high-miss checks (`09` to `09d`), evidence, test integrity and sources (`10a` to `10d`), git (`11`, `12a`, `12b`), data hygiene (`13`), no delegation (`14`), the STATUS and FINDINGS blocks (`15a`, `15b`), reporting and voice (`16`), the prose check (`17`), the reference-topics fragment (`18`, at most 450 bytes through `FragmentCaps`), and the design fragments (`20` design source, `21` Sophon default, `22` design checks, `23` contrast, `25` browser measure). `Compose-AgentSouls.ps1 -Explain` lists which agents include each one.

**Budgets** (`Test-AgentSources.ps1` section E fails over any of them and prints a headroom table):
- Composed SOUL, `SoulCap` in `family.psd1` (the 3.0 tiers, option A of the design's byte ledger): lead-developer 62,464 B; the design writers (ui-ux-designer, frontend-developer, design-system-engineer, visual-designer) 51,200 B; the writers (developer, debugger, qa-engineer, e2e-test-engineer, mcp-integration-engineer, technical-writer, release-engineer, agent-engineer) 44,032 B; the readers (software-architect, code-reviewer, security-reviewer, accessibility-reviewer, product-manager, product-owner) 28,672 B; researcher and artifact-creator 22,528 B. The platform limit is 65,536 B. Caps are data: raising one changes the family file and its header comment, never code.
- Headroom: under 8% of the cap free prints `WARN BUDGET-HEADROOM`; under 5% free is an error only with `-Release` (alias `-StrictHeadroom`, on `Test-AgentSources.ps1` and `Build-AgentPackages.ps1`). Warnings never change the exit code. The table also shows the change against `build/agent-src/catalog/soul-baseline.psd1` (the 2.1.0 sizes). Lead Developer and Software Architect sit only a few bytes above the 5% floor, so any shared-fragment growth that reaches them must be offset in the same change.
- Role text: every development agent has a `RoleCap` (the template without include and comment lines; `BUDGET-ROLE`), from the ledger and rounded up to the next 100; `-Release` requires one for every agent once the family sets any.
- Each fragment at most 4,096 B (or the lower limit `FragmentCaps` sets for its id, `BUDGET-FRAGMENT`), each TOOLS.md at most 2,048 B, each README at most 12 KiB (the lead's 24 KiB).
- Every child pays for its whole SOUL, uncached: keep role text terse and cut before you raise a cap again.

**Other source checks.**
- **Method registry** (section M of `Test-AgentSources.ps1`): the family key `Method` lists the tested rules and the controller/worker split. The development family registers ten rules: five carried by fragments (test-first, receiving-review, test-integrity, run-evidence, discovery-gate) and five carried by role text (root-cause in debugger, premises-first in product-manager, split-never-shrink in product-owner, outward-gate in release-engineer, control-first in agent-engineer). A rule is a whole fragment, or a block from an `Anchor` line to the end of its `| Excuse | Reality |` table. `METHOD-CONTROLLER` keeps controller fragments and terms (agent.delegate, waves, stand-ins, fanning out) out of agents that do not delegate and requires the worker fragments `01-delegated-mode` and `14-no-delegation` (Artifact Creator is exempt); `METHOD-EXCUSES` requires exactly one canonical excuse table (3-6 rows) per rule and none outside a rule; `METHOD-REFERENCE` keeps a skill's tools inside the reference fragment its `SkillPolicy` entry names. The fixtures are `tests/agents/fixtures/method/cases.psd1`.
- **Anchors** (section M, `tests/agents/fixtures/anchors/<family>.psd1`): exact strings each composed SOUL or README must carry (runtime strings, STATUS and FINDINGS keys, verdict words, plan header fields, brief keys and mode words, consent words, the question labels the READMEs promise, the trailer and footer), for a set derived from the roster (`all`, `writers`, `readers`, `lead`, with `Except`) or a list of agent ids. `ANCHOR-MISSING`: a listed agent lacks one; to drop one on purpose, move it to `Removed` with a reason and add the row to the design's "Changed on purpose" table. `ANCHOR-GONE`: a `Gone` string (2.x wording 3.0 replaces) is still present once `FamilyVersion` reaches its `Since`. An entry with `Pending = 'M<n>'` (the milestone that rewrites the text) is counted as pending, and under `-Release` a remaining `Pending` fails, so the key is deleted in the commit that rewrites the text.
- **Lost lines.** `pwsh -NoProfile -File tests/agents/Compare-AgentSouls.ps1 -Base agents-v2.1.0` (read-only; `-Agents`, `-Family`, `-Summary`) composes the base sources of any git ref (`agents-v2.1.0` is the tag of the 2.1.0 baseline, commit `3f052f3`; pass the commit where the tag is missing) in a temporary folder and prints every base SOUL line that no longer occurs in the current SOUL of the same agent, grouped by base source file, with a count per agent. Since M5 most lines are reworded, so the report is reading material and the anchors are the gate.
- **Reference topics** (`LINT-TOPIC`, `LINT-SKILL-FRAGMENT`, `LINT-SKILL-UNUSED`): every "topic `<id>`" pointer must exist in `build/craft-reference/topics.index.json`, the reference fragment must be in exactly the agents that use the skill, and a policy skill no agent uses fails.
- **Document counts** (`DOC-COUNT`, section N, once per repository): a number of 10 or more before "agents", "packages" or "companions" in the documents listed in `build/agent-src/catalog/doc-counts.psd1` must be a roster count derived from the families (all packages, a family roster, the `RosterOrder` table, the lead's companions) or an allowed value; an intended older count goes under `History`. It warns, and fails only with `-Release`.
- **Control arms.** `Compose-AgentSouls.ps1 -Agents <id> -Omit <rule or fragment id> -OutDir <folder>` composes an agent without a registered rule (or a fragment) for a pressure scenario. It is refused without `-OutDir`, with `-Check`, for an `-OutDir` inside `agents/`, and for an agent that does not carry the id; it prints the source, line range, lines and bytes it removed.
- **Instruction tests.** `tests/agents/evals/Invoke-AgentEvals.ps1 -ValidateOnly` lints the scenarios (no CLI, no Gateway; CI runs it) and `-Release` fails while a row is still `Pending`. Run it before a pull request that touches agent text. The tiers, the ship rule, the by-hand steps and the headless runner are in [`tests/agents/evals/README.md`](../tests/agents/evals/README.md).

**The reference skill.** `skills/craft-reference/` is generated: edit the topic sources under `build/craft-reference/` and run `python -B build/craft-reference/generate.py` (`--check` for drift, `--release` for the release rules). `pwsh -NoProfile -File build/craft-reference/Test-CraftSources.ps1` checks the topic sources, and `python tests/skills/run_all.py` runs the skill's offline tests. Its tools are `craft.topics` and `craft.read`, risk `none`, read-only, with no network, credentials or files. The skill carries reference data only: gates, approvals and output formats stay inline in each SOUL, and every agent works without it.

**Release-candidate sequence** (from the repository root; needs PowerShell 7 and Sophon CLI 2.2.x):

```powershell
pwsh --version ; sophon --version                                 # 7.x ; 2.2.x (2.2.2+a431e1a64 known)
pwsh -NoProfile -File build/Compose-AgentSouls.ps1                # regenerate SOUL.md and development README.md
pwsh -NoProfile -File build/Compose-AgentSouls.ps1 -Check         # exit 0, no drift
pwsh -NoProfile -File build/Test-AgentSources.ps1 -Release        # sections A-I, M and N; no release finding
pwsh -NoProfile -File build/Build-AgentPackages.ps1 -ValidateOnly -Release # sophon dev validate: 0 errors, 0 warnings
pwsh -NoProfile -File build/Build-AgentPackages.ps1 -Release      # 22 x <id>-<version>.sophon-agent + SHA256SUMS; run twice, compare
pwsh -NoProfile -File tests/agents/Test-AgentPackages.ps1         # sections A-N
pwsh -NoProfile -File tests/build/Test-SkillLint.ps1
python build/craft-reference/generate.py --check --release ; python tests/skills/run_all.py
pwsh -NoProfile -File build/craft-reference/Test-CraftSources.ps1
pwsh -File build/Build-MarketplacePackages.ps1 -ValidateOnly
pwsh -NoProfile -File tests/agents/evals/Invoke-AgentEvals.ps1 -ValidateOnly -Release
pwsh -NoProfile -File tests/agents/Compare-AgentSouls.ps1 -Base agents-v2.1.0
git status --porcelain                                            # only intended sources + generated files
```

- **The builder** checks the folders against the roster, the CLI version, the composer (`-Check`; drift fails with "SOUL or README drift — run the composer"), `Test-AgentSources.ps1` and `sophon dev validate --json` per agent. Any CLI error **or warning** fails the build. It then writes `dist/agents/<id>-<version>.sophon-agent` and `dist/agents/SHA256SUMS`.
  - It removes stale packages: all of them on a full build, only the selected ids' on a subset build, which prints "SHA256SUMS covers only: …".
  - A failed build leaves no SHA256SUMS. It never installs or publishes.
- **The tests.** `tests/agents/Test-AgentPackages.ps1 -SourceOnly` runs sections A-I, L, M and N without the CLI. See [`tests/README.md`](../tests/README.md).
- **Package shape** (made by `sophon dev build`): a zip with `manifest.json` first, then the other files in ordinal order, at the root, each entry stamped 1980-01-01 00:00:00. Repeat builds are byte-identical.
- **Before the upload,** the release also needs: the instruction-test sweep on a throwaway Gateway (the ship rule, deferred to this sweep by owner decision 9 of the design); the smoke scenarios by hand, with MX1 to MX3 and the card count for one reviewed task; an install preview of each of the 22 packages and of the skill with the injection scan on (a clean verdict, no possible-secret finding, no `expects tool:` line, the pins shown); and the Sophon-default check: every value of fragment `21-sophon-default` found in the Dashboard token file, or each miss explained, with the owner's sign-off recorded.

**Versioning.**
- Major 3 in lockstep across the family (`FamilyMajor`). All 21 development manifests are 3.0.0, Artifact Creator included, because `MAN-VERSION` checks the family major for every roster agent. Minor and patch move per agent.
- A content change bumps every affected agent to a strictly greater SemVer; a shared-fragment change bumps every agent that includes it (`Compose-AgentSouls.ps1 -Explain` lists them).
- The marketplace refuses a version that is not greater than every version ever uploaded, rejected ones included.
- Patch releases in 3.0.x keep TOOLS.md pins and `requires` as they are: a change to either stops auto-update, so `requires.skills` and the `craft.read` pin stay fixed for the whole 3.x line.
- video-producer stays 1.0.0 and byte-identical; craft-reference is 1.0.0. Skill versions follow the skill's own rules: a patch for wording inside existing topics, a minor for an added topic or section, and no removed or renamed topic id.

**Licenses.**
- An agent entry in `family.psd1` may set `License = 'Apache-2.0'`. Without it the agent takes the family default: MIT and the root `LICENSE`.
- AgentLint checks that the manifest `license` equals the agent's License.
- `Test-AgentSources.ps1` requires `agents/<id>/LICENSE` to be byte-identical to the license's canonical text (`build/licenses/Apache-2.0.txt` for Apache-2.0, else the root `LICENSE`), and the README's license sentence to match: "Licensed under the MIT License; see LICENSE." or "Licensed under the Apache-2.0 License; see LICENSE."
- Agents that adapt anthropics/skills text list the `anthropicSkills` key in their `Credits`.

**Publishing (manual, owner only).** Nothing in this repository publishes an agent. The order is fixed, because the Marketplace refuses an agent whose required skill is not approved:
1. Check the five new slugs while signed in: `craft-reference`, `product-owner`, `product-manager`, `release-engineer` and `agent-engineer` (`sophon agents search <slug>`, `sophon skills search <slug>` and `GET https://marketplace.sophon.buildersoft.io/api/v1/packages/<slug>`; skill and agent names share one namespace). Any hit not owned by Buildersoft stops the release.
2. Run the release-candidate sequence above on a clean checkout, and the checks before the upload.
3. Publish `craft-reference` 1.0.0 with `pwsh -File build/Publish-MarketplacePackages.ps1 -Skills craft-reference` and wait until it is approved, not only `pendingReview`.
4. In the Marketplace wizard, upload the four new agents. They are additive: a 2.1.0 lead does not know them, so they can wait in review without affecting anyone.
5. Upload the fifteen existing companions and Artifact Creator.
6. Upload lead-developer last, so that a user who takes the new lead finds every companion at 3.0.0.
7. Every version starts `pendingReview`. Announce only when all 21 agents are approved. Then tag `agents-v3.0.0` and commit its `SHA256SUMS` as the baseline for 3.0.x.

Upload each `.sophon-agent` file from `dist/agents/` on its own; never upload a zip of all of them, and never use `Publish-MarketplacePackages.ps1` for an agent, which stays skills-only. The preview must show no possible-secret finding to acknowledge and a clean moderator flag list. Between steps 5 and 7 a user can hold 3.0.0 companions under a 2.1.0 lead, which works: a 3.0.0 companion still accepts the 2.x brief. The publish rate limit is a deployment setting (the Marketplace source defaults to 500 uploads an hour for one publisher), so confirm the production value before planning the sitting. Video Producer follows section 14. See also [PUBLISHING.md](PUBLISHING.md#7-skills-that-agents-require).

Prerequisite outside the repo: the `noreply@buildersoft.io` mailbox for the commit trailer.

**Deferred to a later release** (not in 3.0.0): a catalogue drift checker, a full port of the runtime's argument-redaction rules (the CLI covers them now), release reproducibility against published hashes, and the local-install export script.

## 14. Families

The repository holds two agent families. A family is one family file: its roster, versions,
values, hosts and credits. Its `souls/` and `fragments/soul/` folders sit beside the family file,
so families never share templates or fragments.

| Family | Family file | Agents | Major | Tag, category |
|---|---|---|---|---|
| development | `build/agent-src/family.psd1` | the twenty-one in section 2 | 3 | `development`, `development` (Artifact Creator: `productivity`, `productivity`) |
| video | `build/agent-src/families/video/family.psd1` | `video-producer` | 1 | `video`, `ai` |

**The registry.** `build/agent-src/families.psd1` lists every family as `@{ Id; Path }`. All
agents still live in `agents/<id>/`; an id belongs to exactly one family, and `agents/` must hold
exactly the union of the rosters. Without a registry (the composer fixtures, for example) the
tooling falls back to the single family in `build/agent-src/family.psd1`.

**Running one family.** Every tool loops over the registry by default. `-Family <id>` limits it:

```powershell
pwsh -NoProfile -File build/Compose-AgentSouls.ps1 -Family video -Check
pwsh -NoProfile -File build/Test-AgentSources.ps1 -Family development
pwsh -NoProfile -File build/Build-AgentPackages.ps1 -Family development -OutputDir <folder>
```

Without `-Family`, `Test-AgentSources.ps1` first checks `agents/` against the roster union, then
re-runs itself once per family; the composer writes nothing unless every family composes cleanly.
A build of fewer families than the registry lists is a subset build.

**Family keys beyond the development set** (all optional; the defaults reproduce the development
family):

| Key | Meaning | video |
|---|---|---|
| `Id` | must equal the registry id | `video` |
| `RequiredTag`, `Category` | MAN-TAGS and MAN-META check them in every manifest | `video`, `ai` |
| `CreditsSentence` | the sentence every README of an agent with Credits must carry, followed by its license sentence; absent means no check (an agent without Credits needs only its license sentence) | none |
| `CreditsSentenceKeys` | the Credits keys `CreditsSentence` speaks for: only an agent carrying one of them must carry the sentence, and any other agent with Credits needs its credits and license sentence; absent means every key (development: `anthropic`, so artifact-creator, with `superpowers` and `humanizer`, has no fixed sentence) | none |
| `ReadmeCaps` | `@{Lead; Other}` README byte caps | 12,288 and 12,288 |
| `SkillPolicy` | `Skills` (name and `MinVersion`) and `ExtraRequiredTools` | `ffmpeg-video` 1.0.0; document.upload, media.image, media.video, music.generate, video.generate |
| `AllowRestrictedMentions` | restricted tools the text may name (never pin) | `message.send` |

**SkillPolicy** is the only way an agent uses a skill's tools:
- `requires.skills` must equal the agent's share of `SkillPolicy.Skills` exactly, sorted by name, and
  comes first in `requires`. `requires.tools` is the sorted union of the built-in pins and
  `ExtraRequiredTools` and never holds a skill tool (the installer would report it missing until the
  skill is installed). Each extra must be an allowed tool, not core and not restricted.
- The tool lint (`LINT-SKILL`) and the pin check (`TOOLS-PIN-UNKNOWN`) are waived only for the
  tools of those skills, read from `skills/<name>/manifest.json`. A restricted pin still fails.
- MAN-SKILL-VERSION checks that `skills/<name>/manifest.json` exists at `MinVersion` or later.
- These rules are evaluated per agent. The optional agent key `Skills` lists the policy skills that
  agent uses: absent means every policy skill (so `video-producer` is unchanged), `@()` means none, and
  any other name is a schema error. `requires.skills`, `LINT-SKILL` and `TOOLS-PIN-UNKNOWN` follow it;
  `ExtraRequiredTools` stays family-wide.
- A policy skill may also name `Fragment = '<NN-id>'`, its reference fragment: `METHOD-REFERENCE`
  then allows that skill's tools only on lines from that fragment, which must carry the sentence
  "If the tool is missing or refused, work from what you carry."
- A policy skill may name `TopicIndex = '<repo path>'`, its JSON id list: `LINT-TOPIC` checks every
  "topic `<id>`" pointer (and ", section `<id>`") against it and the `topics.lock.json` beside it.
  `LINT-SKILL-FRAGMENT` requires the reference fragment exactly in the agents that use the skill, and
  `LINT-SKILL-UNUSED` fails a policy skill no agent uses.
- The development family's SkillPolicy names `craft-reference` (fragment `18-reference-topics`, topic
  index `build/craft-reference/topics.index.json`): every development agent but Artifact Creator
  requires it, pins `craft.read` and includes the fragment. Artifact Creator sets `Skills = @()`, so a
  skill tool name in its text still fails `LINT-SKILL`.

**Derived rules.** The attribution checks apply only to an agent whose sources use
`{{= CommitTrailer}}` or `{{= PrFooter}}`, and the `whenToUse` sibling rule only when the roster
has more than one agent. Video Producer commits nothing and has no sibling, so neither applies.

**The video family.** One agent, Video Producer 1.0.0. It plans and produces short videos with
Sophon's media tools and renders them locally with the `ffmpeg-video` skill. Its SOUL is composed
from `families/video/souls/video-producer.md` and six fragments (`01-media-ground-rules` to
`06-media-failures`); its TOOLS.md pins six `ffmpeg.*` tools plus image.generate and tts.file.
Install order, requirements and limits are in [its README](../agents/video-producer/README.md);
the manual evals are in [`tests/agents/evals/video-producer.md`](../tests/agents/evals/video-producer.md);
the design is [`docs/plans/2026-11-15-ffmpeg-video-design.md`](plans/2026-11-15-ffmpeg-video-design.md).

**Publishing order.** The marketplace refuses an agent whose required skill is not approved, so
publish `ffmpeg-video` and get it approved before uploading `video-producer` (see
[PUBLISHING.md](PUBLISHING.md#7-skills-that-agents-require)).

**Regression gate.** video-producer must stay byte-identical through every development-family
change: its package hash in `dist/agents/SHA256SUMS` equals the 2.1.0 baseline
(`tests/agents/fixtures/baseline/SHA256SUMS-2.1.0`, hash starting `96bcd4d8`). A change to the
multi-family tooling alone must leave every package byte-identical: compare `dist/agents/SHA256SUMS`
before and after, and `Compose-AgentSouls.ps1 -Check` must show no drift. A change to development
text is guarded by the anchors (`ANCHOR-MISSING`, `ANCHOR-GONE`), with the lost-lines report read
against `agents-v2.1.0`.

## 15. Credits

Every README ends with "Credits and license": one credit line for each upstream project its agent's
text draws on, then its licence sentence. The lines come from the family `Credits` table in
`build/agent-src/family.psd1`, which holds one key per upstream, and each agent lists its keys in its
own `Credits`. Section I of `Test-AgentSources.ps1` checks that each README carries the exact string
of every key it lists. The credits are acknowledgements: every idea is re-expressed in our own words,
and no licence changes because of them.

- Every agent but Artifact Creator credits obra/superpowers (MIT, © 2025 Jesse Vincent), Anthropic's Claude Code plugins (Apache-2.0) and JuliusBrussee/caveman (Apache-2.0, © 2026 Julius Brussee), and carries the family's fixed sentence about workflow patterns adapted from obra/superpowers and Anthropic's Claude Code plugins (`CreditsSentence`, required by the `anthropic` key).
- Artifact Creator uses nothing from Anthropic's plugins, so it carries its own credits (obra/superpowers and blader/humanizer) and its licence note instead (`CreditsSentenceKeys`).
- The other upstreams are credited only by the agents that draw on them, among them the product and design method repositories, the engineering skills and Playwright. The security-reviewer exclusion list follows anthropics/claude-code-security-review (MIT, © 2025 Anthropic) in original wording, and its README credits that project.
- BMAD-METHOD is credited by its repository path, bmad-code-org/BMAD-METHOD, which the owner accepted as enough. Two upstream licences name no holder, and their credit lines copy them as they are: `MIT, (c) 2026` for web-design-engineer and `Apache-2.0` for design.md.

Portions of the seven agents added in 2.1 are adapted from Anthropic's agent skills, anthropics/skills (Apache-2.0, © 2026 Anthropic, PBC): frontend-design, web-artifacts-builder, webapp-testing, theme-factory, brand-guidelines (the pattern only), canvas-design, algorithmic-art, slack-gif-creator (the motion vocabulary only) and mcp-builder.

- **Modification notice:** Buildersoft LLC changed that text, rewriting it for Sophon tools and removing its scripts and branding. The README of every agent that uses it carries this notice.
- Technical Writer was written independently. It is inspired by doc-coauthoring, which has no license, and copies none of its text.
- The `craft-reference` skill is Apache-2.0, and its `THIRD_PARTY_NOTICES.md` is generated with it.

The nine original agents and the four added in 3.0 are licensed under the MIT License; see [`LICENSE`](../LICENSE). The seven added in 2.1 and Artifact Creator are licensed under the Apache License, Version 2.0; see [`build/licenses/Apache-2.0.txt`](../build/licenses/Apache-2.0.txt). Every package carries its own `LICENSE`.
