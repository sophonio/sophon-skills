# Development agents: the Buildersoft development family 2.0.0

Nine Sophon Marketplace agents that work on a code repository the way Claude Code does:

1. They size the request.
2. They plan in a markdown file you approve, then carry it out task by task with a live todo list.
3. They verify with real commands and commit each verified task on a feature branch.
4. At the end they offer a pull request.

Only Lead Developer starts sub-agents, and only with your consent.

This repository also holds a second, separate family: **video**, with one agent, Video Producer
(`agents/video-producer`), which drives the `ffmpeg-video` skill. Sections 1-12 are about the
development family; section 14 covers families, the video family and how the tooling keeps them
apart.

## 1. What these are

- **Sophon agent packages**, format v1 (`.sophon-agent`), not skills, plugins or Claude Code agents. Each package holds one persona and no executable code: `manifest.json`, `SOUL.md`, `TOOLS.md`, `README.md` and `LICENSE`.
- **Family 2.x.** All nine ship at **2.0.0** and are rewritten from scratch. The six 1.0.0 personas are replaced.
- **License:** MIT, © 2026 Buildersoft LLC. **Requires** Sophon 2.2.0 or later.
- **Built on Sophon's own tools**, not on this repository's integration skills: fs.read, fs.write, code.git, os.execute, plan.propose, todo.write, info.request, agent.delegate and the rest of the coding tools.
- **Claude Code analogues:**

| Claude Code | Sophon |
|---|---|
| Plan mode and ExitPlanMode | plan mode (set by you) and plan.propose, plus a plan file in `docs/plans/` |
| TodoWrite | todo.write |
| AskUserQuestion | info.request (1-4 questions of 2-4 options) |
| Task (sub-agents) | agent.delegate (blocking; up to 5 tasks per call) |
| CLAUDE.md | AGENTS.md or CLAUDE.md in the bound repository |

## 2. The roster

| id | Role | Delegates | Read-only | Effort | Typical cards |
|---|---|---|---|---|---|
| [lead-developer](../agents/lead-developer) | orchestrator: sizes, plans, builds, verifies, commits | yes (`maxDepth 1`) | no | high | trivial fix 2-4; medium 4-task plan about 28; sub-agents add a few more, stated before you choose |
| [developer](../agents/developer) | implementer: tdd / direct / debug | no | no | default | files edited + 1-2 runs; plans as for the lead |
| [researcher](../agents/researcher) | codebase and web facts, every claim cited | no | yes | default | usually none (reads and web reads raise no card) |
| [software-architect](../agents/software-architect) | blueprint / adr / greenfield / compare / critique | no | yes, except its plan or ADR file | high | 2 (the plan file, then the approval edit) |
| [code-reviewer](../agents/code-reviewer) | review / refute / re-review / completeness | no | yes | high | 1 for the working tree; a range needs about one command per diff group |
| [qa-engineer](../agents/qa-engineer) | gate / regression / write-tests / strategy / gaps / ui | no | no (tests, when asked) | default | one per chained check; browser checks up to 6 |
| [debugger](../agents/debugger) | investigate / hypothesis / fix | no | no (fix + regression test, when asked) | high | one per reproduction or check run |
| [security-reviewer](../agents/security-reviewer) | review / verify (exploitability 8/10 or higher) | no | yes | high | 1-2 (the diff, a branch range) |
| [ui-ux-designer](../agents/ui-ux-designer) | direction / build / critique / copy / judge | no | no (UI files) | default | direction none; build as for developer; browser checks one each |

The four read-only roles never commit. Software Architect saves only a plan or ADR file, and only after you approve it. The writers (developer, qa-engineer, debugger, ui-ux-designer) use the same sizing, plan and git rules as the lead when you talk to them directly.

## 3. Where they work

- **Bound and trusted.** Run `sophon` in the repository so the session is bound, then `/trust` the folder. Trusted turns load the project instructions (AGENTS.md or CLAUDE.md) and a "Git state" block, which the agents use instead of a status call.
- **Unbound.** Paths are host-wide, nothing can be rewound and AGENTS.md is not loaded. The agents read, analyse and plan, say once that running `sophon` in the project folder binds the session, and edit or run commands only if you ask again after that.
- **Pick an agent yourself.** The router never picks a package agent on its own. Use `/agent lead-developer` in a chat, or start one with `sophon chat --agent lead-developer`.
- **Shells.** On Windows, os.execute runs cmd (preferred for git and gh) or Windows PowerShell 5.1, never bash. On macOS and Linux it runs bash or sh. Nothing runs in the background, so the agents never start servers or watchers.

## 4. Install order

1. Install the lead: `sophon agents install lead-developer`.
2. Open Dashboard → Agents → Lead Developer → Delegation, turn on **Restrict to allow list** and save. The list starts empty, and `--allow-delegation-from` adds a companion to it only while this is on, so do this before step 3.
3. Install each companion with permission for the lead to delegate to it:

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

4. Confirm that **Effective targets** lists every companion you installed.
5. Keep each agent id equal to its package name. The lead finds companions through the `Family role: <id>.` line in each one's when-to-use text, then by id, then by display name. A `-2` suffix still matches, but avoid it.

A missing companion is not fatal. The lead runs a stand-in (its own rules plus a pasted role checklist), at most 2 per wave, labels the result lower confidence and tells you once which agent to install.

## 5. Settings a package cannot carry

A package can set only `defaults.subAgents` (applied on the first install) and model routing (`inherit` here). It cannot carry a delegation allow list, standing approvals, model pins or effort.

- **Upgraders from 1.0.0: set the lead's delegation depth to 1.** Updating a package never changes its delegation settings, so a 1.0.0 lead keeps `maxDepth 2`.
  - Set it in Dashboard → Agents → Lead Developer → Delegation, or with `PUT /api/agents/lead-developer/subagents`.
  - Depth 1 keeps every consent question and card estimate at the top level, where the lead can ask you.
  - Add the new companions (code-reviewer, debugger, security-reviewer) to an existing allow list.
- **Effort.** Recommended `high` for lead-developer, software-architect, code-reviewer, security-reviewer and debugger; leave the rest at the default:

```
sophon agents models lead-developer --effort high
sophon agents models software-architect --effort high
sophon agents models code-reviewer --effort high
sophon agents models security-reviewer --effort high
sophon agents models debugger --effort high
```

  A companion's effort reaches its delegated runs only while the lead's chat has no effort of its own (`/effort reset` in that chat).
- **Allowed Medium-risk calls for the session** (the `/permissions` setting, Medium) cover only the root agent's own Medium calls that change nothing in the workspace: agent.delegate, code.git diff and blame, GET http.request, browser.act and memory.forget. They never cover a package agent's edits, commits or shell commands, and never any call a sub-agent makes.

**Cards you should expect.** Marketplace installs are third-party for life: your standing approvals (accept edits, remembered commands, allow all) do not cover them.

| Card on every call | No card |
|---|---|
| fs.write, the edit tools, fs.move, fs.copy, fs.delete, fs.create_directory (bound edits always ask) | fs.read, fs.list, fs.find, fs.search, fs.info |
| os.execute (Critical; never remembered for a package agent) | code.git status, log, branch list, remote, stash list |
| code.git diff, blame and every code.git write (Medium) | web.search, web.scrape, browser.screenshot, canvas.render (Low) |
| agent.delegate (Medium; at the root, covered by allowed Medium-risk calls for the session) | todo.write, memory.search, memory.write, tools.search, tools.load, agent.list, session.history, datetime.now, os.info, diff |
| http.request, browser.act, memory.forget (Medium); plan.propose raises the plan card | info.request is a question, not a card |

- **Inside a sub-agent,** every Medium-or-higher call raises a card for you, whatever the session allows.
- **Per plan task:** the files it edits + 1 failing-check run + 1 plan tick + 1 verify-and-commit command.
- **Per plan:** about 4 more (the plan file, the branch, the PR body file, push + PR).
- **Example:** a medium 4-task plan touching about 3 files per task raises about 4 × 6 + 4 = **28 cards**. A review panel adds about 4. For far fewer cards, see the local-install form (section 10).

## 6. Plan mode and plan files

**Plan files.**
- Every Medium or Large task gets `docs/plans/YYYY-MM-DD-<slug>.md` in one fixed format: Goal, Context, Approach, Out of scope, Verification, Orchestration (lead, when sub-agents run), Tasks, Risks and Progress.
- Each task lists its files, checkbox steps, the exact `Run:` command, the `Expected:` result and the `Commit:` subject.
- The header carries `Status:` (draft, approved, in-progress, blocked, done, cancelled), `Approved:`, `Consent:` and `Request:` (your words, verbatim).
- The file is the durable state. "Continue" after a gap or a compacted conversation makes the agent find the newest open plan and reconcile it with the git log. A task counts as done only when it is ticked and its commit subject is in the log, and a committed task is never redone.
- **Another plan folder:** put a line `- Plan directory: <path>` in the project instructions (AGENTS.md), or say which folder in plain words.

**Plan mode off** (the usual case): the agent writes the plan file as a draft (one card that shows it) and asks one "Plan" question:
- [Approve and start (Recommended)]
- [Change something]
- [Cancel]

The question also carries the "Agents" question when sub-agents would help. No answer means it does not start.

**Plan mode on** (bound): the agent explores read-only, then calls plan.propose with at most 4 linear steps, so the card recommends **Inline**. Choose Inline: the agent then writes the plan file, creates the branch and runs the tasks itself. The summary's first three lines are:

```
Plan file (written on approval): <path>
Execution: choose Inline — I run it task by task, verify each task and commit it on sophon/<slug>.
Can't press Approve (Dashboard on Personal, mobile)? Choose Keep planning and type GO.
```

**The GO escape.** The Personal-edition Dashboard (and mobile) cannot approve a plan card:
1. Use the CLI, or choose **Keep planning** and type `GO`.
2. The agent replies "Approved in chat" and asks you to switch the mode to "Ask before edits" (Dashboard: the mode chip or Alt+M; CLI: Shift+Tab or `/permissions default`). Then send any message.
3. On that turn it saves the plan as `Approved: <date> via chat (plan card GO)` and runs it.

**Architect plans.** Software Architect drafts a plan in the same format, saves it after you approve it, and hands it over with: "To execute: tell Lead Developer 'execute docs/plans/<file>'". It never calls plan.propose; in plan mode it returns the draft and the plan.propose JSON in its reply. The lead runs an approved file directly. It asks once first if the file is more than 7 days old or its base commit is gone.

**Graph execution** can still be chosen on the plan card. Its steps commit as the plan says, and the agent reconciles the plan with the git log on your next message.

## 7. Consent words

The lead scans your own messages, newest first; the first match wins.

| You say | Effect |
|---|---|
| "ultracode off", "no ultracode" | back to asking each time |
| "no subagents", "no sub-agents", "without subagents", "don't use agents" | standing no: one thread, zero agent.delegate calls |
| "ultracode" (any case) | standing yes: waves run without the Agents question, after a one-line announcement of agents, waves, cards and cost |
| "use agents" (after a standing no) | back to asking |

- The keyword decides consent only. Size still decides the phases: a trivial change stays inline even with ultracode on, and a standing yes still needs plan approval.
- Without a standing answer, the lead asks once per task (header "Agents") and only when delegation clearly helps. The recommended option comes first, Solo is always offered, and each option states agents, waves, cards and "≈N× Solo tokens".
- No answer, or a skipped question, means Solo. The answer is written on the plan's `Consent:` line.
- The other eight agents cannot start sub-agents. Asked for "ultracode", they say that Lead Developer runs multi-agent work, then do the task themselves.

**Ultracode-lite phases** (lead, with consent): Understand (2-5 researchers), Design (2-3 architects judged on a written 14-point rubric), Implement (one developer per task, or up to 3 in parallel on disjoint files), Review (3-5 lenses over one diff file), Refute (3 votes per finding; 2 of 3 must confirm), Fix, Re-review until dry (at most 3 rounds) and a Completeness critic.

**Caps:** Medium 10 agents in 5 calls; Large 25 agents in 14 calls; at most 5 entries per call. The estimate you approved is binding, and anything dropped is logged as a `Cap:` line in the plan and the report.

## 8. Git and pull requests

- **Branch first.** An approved plan runs on `sophon/<slug>` (or the repository's own branch naming), created with one `git checkout -b`. Outside a plan, agents commit only when you ask, on the current branch.
- **One commit per verified task.** The task's check, the staging and the commit run as one command. A failing check means no commit: the agent repairs at most 3 times, then marks the task BLOCKED and asks you. The commit uses a trailing pathspec, so files you staged yourself stay out of it.
- **Commit trailer**, the last line of every commit message:

```
Co-Authored-By: Sophon <noreply@buildersoft.io>
```

- **End-of-task menu** (an info.request with header "Git"):
  - [Push + open PR (Recommended)]: 2 cards, the PR body file then the command.
  - [Keep local]
  - [Discard]: after one more confirmation.

  Keep local becomes the recommended option when something is unverified, there is no remote, or the remote is not GitHub. A non-GitHub remote turns option 1 into "Push branch". No answer means Keep local.
- **PR body.** Summary, Changes, Test plan and the plan path, with this footer as the last line:

```
🤖 Generated with [Sophon](https://sophon.buildersoft.io)
```

- **Never, unless you ask for that exact operation:** amend, rebase, reset, revert, clean, discard changes, delete branches, force-push, push to the default branch, change git config. Nothing is pushed silently.
- **code.git cannot push or open PRs,** and its commit stages everything. So branches, commits, pushes and `gh pr create` go through os.execute, which is always a card.
- An author of "Sophon Agent <sophon@localhost>" means git has no `user.name` or `user.email`; set them yourself.

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
- A local agent reports no version. The lead still matches it through the `Family role:` line.
- You take over updates: a local copy never receives Marketplace updates.
- A step-by-step recipe and an export script are planned for 2.1.

## 11. An AGENTS.md starter for your repository

The agents read the project instructions as trusted conventions, and they suggest new lines for them instead of storing repository facts in memory. A starting point:

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
- Run the full test suite before every commit.
- Ask before adding a dependency.

## Do not touch
- `migrations/` (generated; change the model and regenerate)
- `.github/workflows/` without asking

## Gotchas
- Tests need the local database: `docker compose up -d db` first (start it yourself; agents never start servers).
```

## 12. Known limits

- **No background agents.** Sub-agents are blocking, at most 5 per call and one level deep. Nothing resumes an agent after it ends its turn.
- **Screenshots are invisible to the model.** browser.screenshot and canvas.render show you an image, but the agent receives only "Screenshot taken". You are its eyes, and it asks what looks off.
- **browser.act needs AllowPrivateNetwork for localhost.** It opens `localhost` only when `Sophon:Browser:AllowPrivateNetwork` is on, and it needs Playwright Chromium on the Gateway host.
- **code.git has no push,** no PR and no selective commit, so those steps go through os.execute cards.
- **Cards scale with fan-out:** every sub-agent's edits, commands and diffs raise cards at the top level.
- **Caching:** every new session, including every sub-agent, pays for its own instructions uncached. The cache also misses after any pause over 5 minutes (approval and question waits count) and after each tool load.
- **Questions:** info.request waits 15 minutes, and sub-agents, heartbeat and cron runs cannot ask at all.
- **Plan approval on the Personal-edition Dashboard** needs the CLI or the GO escape (section 6).
- **Accepted on plausible but unrun evidence,** each to be checked once in the owner smoke scenarios (D2, L3 and Q1, plus the one push in the evals README section 4) before release:
  - pathspec commits keeping pre-staged files out;
  - PowerShell 5.1 quote stripping;
  - the cmd stash grouping in QA's red/green check;
  - gh and Git Credential Manager under the bound shell;
  - SSH push on Windows.

## 13. Maintainers: build, test and publish

**Sources.** `agents/<id>/` holds only the 5 package files. Each `SOUL.md` is generated: never edit it by hand.

```
build/agent-src/
  families.psd1               the family registry (section 14)
  family.psd1                 development roster, fragment order, SoulCap, SubAgents, Effort, Credits,
                              Values (commit trailer, PR footer, plan folder), AllowedHosts
  souls/<id>.md               role text + include lines ({{> soul/<NN-id>}})
  fragments/soul/<NN-id>.md   21 shared fragments, at most 4,096 bytes each
  families/video/             the video family: family.psd1, souls/, fragments/soul/
  catalog/sophon-tools.psd1   real Sophon tool names (pinned to sophon a431e1a64, v2.2.2)
  catalog/scan-rules.psd1     the marketplace and runtime scanner rules the preflight replays
build/AgentFamily.psm1        registry, roster and composer
build/AgentLint.psm1          tool-name lint, scanner preflight, TOOLS.md parser, manifest checks
build/Compose-AgentSouls.ps1  [-RepoRoot] [-Agents] [-Check] [-OutDir] [-Explain] [-Family]
build/Test-AgentSources.ps1   sections A-I per family, no Sophon CLI needed (CI runs it) [-Agents] [-Family]
build/Build-AgentPackages.ps1 [-RepoRoot] [-OutputDir] [-Agents] [-ValidateOnly] [-Family]
tests/agents/                 Test-AgentPackages.ps1 (A-L), fixtures/, evals/
```

**Budgets** (`Test-AgentSources.ps1` section E fails over any of them and prints a headroom table):
- Composed SOUL, `SoulCap` in `family.psd1`: lead-developer 43,008 B; developer, qa-engineer, debugger and ui-ux-designer 32,768 B; software-architect, code-reviewer and security-reviewer 22,528 B; researcher 18,432 B.
- Each fragment at most 4,096 B, each TOOLS.md at most 2,048 B, each README at most 12 KiB (the lead's 24 KiB).
- The design planned 36,864 B and 28,672 B for the lead and the writers on an estimate of about 17.5 KB of shared writer text. The fragments it mandates measure about 25 KB, so those two caps were raised rather than cutting runtime workarounds. Every child pays for its whole SOUL, uncached: keep role text terse and cut before you raise a cap again.

**Verification sequence** (from the repository root; needs PowerShell 7 and Sophon CLI 2.2.x):

```powershell
pwsh --version                                                    # 7.x
sophon --version                                                  # 2.2.x (2.2.2+a431e1a64 known)
pwsh -NoProfile -File build/Compose-AgentSouls.ps1                # regenerate agents/*/SOUL.md
pwsh -NoProfile -File build/Compose-AgentSouls.ps1 -Check         # exit 0, no drift
pwsh -NoProfile -File build/Test-AgentSources.ps1                 # lint, preflight, budgets, manifests, TOOLS.md
pwsh -NoProfile -File build/Build-AgentPackages.ps1 -ValidateOnly # sophon dev validate: 0 errors, 0 warnings
pwsh -NoProfile -File build/Build-AgentPackages.ps1               # 9 x <id>-2.0.0 + video-producer-1.0.0 + SHA256SUMS
Get-Content dist/agents/SHA256SUMS
pwsh -NoProfile -File tests/agents/Test-AgentPackages.ps1         # sections A-L
pwsh -File build/Build-MarketplacePackages.ps1 -ValidateOnly      # skills unaffected
git status --porcelain                                            # only intended sources + generated SOULs
```

- **The builder** checks the folders against the roster, the CLI version, the composer (`-Check`; drift fails with "SOUL drift — run the composer"), `Test-AgentSources.ps1` and `sophon dev validate --json` per agent. Any CLI error **or warning** fails the build. It then writes `dist/agents/<id>-<version>.sophon-agent` and `dist/agents/SHA256SUMS`.
  - It removes stale packages: all of them on a full build, only the selected ids' on a subset build, which prints "SHA256SUMS covers only: …".
  - A failed build leaves no SHA256SUMS. It never installs or publishes.
- **The tests.** `tests/agents/Test-AgentPackages.ps1 -SourceOnly` runs sections A-I and L without the CLI. See [`tests/README.md`](../tests/README.md).
- **Package shape** (made by `sophon dev build`): a zip with `manifest.json` first, then the other files in ordinal order, at the root, each entry stamped 1980-01-01 00:00:00. Repeat builds are byte-identical.

**Versioning.**
- Major 2 in lockstep across the family. Minor and patch move per agent.
- A shared-fragment change bumps every agent that includes it (`Compose-AgentSouls.ps1 -Explain` lists them).
- The marketplace refuses a version that is not greater than every version ever uploaded, rejected ones included.
- code-reviewer, debugger and security-reviewer start at 2.0.0 too, so the family has one generation number.

**Publishing (manual, owner only).**
1. Check the slugs, signed in: `sophon agents search <slug>`, `sophon skills search <slug>` and `GET https://marketplace.sophon.buildersoft.io/api/v1/packages/<slug>`. Any hit not owned by Buildersoft stops the release.
2. Run a clean build and the full test suite above.
3. Preview each install on a throwaway Gateway or `SOPHON_DATA_DIR`, with the injection-scan mode not off: `sophon agents install --file dist/agents/<id>-2.0.0.sophon-agent --show-files`, check the verdict and that no `expects tool:` line appears, then answer `n`.
4. Run the smoke scenarios in [`tests/agents/evals/`](../tests/agents/evals/README.md), including the card-count check.
5. In the Marketplace wizard, upload each of the 9 `.sophon-agent` files from `dist/agents/` one at a time. Never upload a zip of all of them, and never use `Publish-MarketplacePackages.ps1`, which stays skills-only. The preview must show no possible-secret finding to acknowledge and a clean moderator flag list.
6. Every version starts `pendingReview`. Announce only after all 9 are approved. Optionally tag `agents-v2.0.0`.
7. Withdraw or reject developer's pending 1.0.0 in My packages, so the old persona is never approved.

Prerequisite outside the repo: the `noreply@buildersoft.io` mailbox for the commit trailer.

**Deferred to 2.1:** a catalogue drift checker, a full port of the runtime's argument-redaction rules (the CLI covers them now), release reproducibility against published hashes, a headless eval runner, the local-install export script, and README composition.

## 14. Families

The repository holds two agent families. A family is one family file: its roster, versions,
values, hosts and credits. Its `souls/` and `fragments/soul/` folders sit beside the family file,
so families never share templates or fragments.

| Family | Family file | Agents | Major | Tag, category |
|---|---|---|---|---|
| development | `build/agent-src/family.psd1` | the nine in section 2 | 2 | `development`, `development` |
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
| `CreditsSentence` | the sentence every README must carry; absent means no check | none |
| `ReadmeCaps` | `@{Lead; Other}` README byte caps | 12,288 and 12,288 |
| `SkillPolicy` | `Skills` (name and `MinVersion`) and `ExtraRequiredTools` | `ffmpeg-video` 1.0.0; document.upload, media.image, media.video, music.generate, video.generate |
| `AllowRestrictedMentions` | restricted tools the text may name (never pin) | `message.send` |

**SkillPolicy** is the only way an agent uses a skill's tools:
- `requires.skills` must equal `SkillPolicy.Skills` exactly, sorted by name, and comes first in
  `requires`. `requires.tools` is the sorted union of the built-in pins and `ExtraRequiredTools`
  and never holds a skill tool (the installer would report it missing until the skill is
  installed). Each extra must be an allowed tool, not core and not restricted.
- The tool lint (`LINT-SKILL`) and the pin check (`TOOLS-PIN-UNKNOWN`) are waived only for the
  tools of those skills, read from `skills/<name>/manifest.json`. A restricted pin still fails.
- MAN-SKILL-VERSION checks that `skills/<name>/manifest.json` exists at `MinVersion` or later.
- The development family has no SkillPolicy, so a skill tool name there still fails `LINT-SKILL`.

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

**Regression gate.** A change to the multi-family tooling must leave the nine development
packages byte-identical: compare `dist/agents/SHA256SUMS` before and after, and
`Compose-AgentSouls.ps1 -Check` must show no drift.

## 15. Credits

Workflow patterns adapted, not copied, from obra/superpowers (MIT, © 2025 Jesse Vincent) and Anthropic's Claude Code plugins (feature-dev, pr-review-toolkit, code-review, security-review, frontend-design; Apache-2.0). Every package README carries this line and its license note.

- The software-architect README also credits backend-design and system-design-skills (both MIT, third party), and the debugger README credits backend-design.
- The security-reviewer exclusion list follows ideas from anthropics/claude-code-security-review in original wording. Its README will credit that project once its license is confirmed, which is an owner item before publishing.

The packages are licensed under the MIT License; see [`LICENSE`](../LICENSE).
