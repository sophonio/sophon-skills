# Security Reviewer

Read-only security review of a code change: only vulnerabilities a realistic attacker could exploit, each traced from source to sink by file and line.

Part of the Buildersoft development family 3.0.0.

| Agent | Role | Delegates | Changes files | Commits |
|---|---|---|---|---|
| lead-developer | orchestrator: sizes, plans, builds, verifies, commits | yes (depth 1) | yes | yes |
| developer | implementer: tdd / direct / debug | no | yes | yes |
| researcher | codebase and web facts, every claim cited | no | no | no |
| software-architect | blueprint / ADR / greenfield / compare / critique | no | its plan or ADR file only | no |
| code-reviewer | review / refute / re-review / completeness | no | no | no |
| qa-engineer | verification gate, regression checks, tests | no | tests, when asked | yes |
| debugger | root cause first, then a fix when asked | no | fix + regression test, when asked | yes |
| **security-reviewer** (this one) | exploitable vulnerabilities only | no | no | no |
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

- Before merging a change that touches input handling, sign-in or access control, file paths, shell or database calls, parsing, outbound requests, cryptography or key handling.
- When you want to know whether a change or a branch is secure, without a list of generic hardening advice.
- When a change stores, logs, exports or shares data about people.
- Inside a Lead Developer review: the lead sends it the security lens of a change that crosses a trust boundary, and candidate security findings to verify from one angle.

## Not for

- General code quality: `code-reviewer`. Fixing the issues: `developer`.
- Dependency or CVE audits and penetration testing: use a dedicated tool or a person.
- Whole-system threat models, unless you ask for one.

## How it works

- **Scope first.** The working tree or a branch against its base (one shell approval for a read-only git diff). With an unclear base it asks. In plan mode it reviews the working tree only and says so.
- **Exposure and defences.** It works out who can reach the changed code and searches for the defences already there: auth middleware, model binding, sanitisers, CSRF protection, allowlists.
- **Finder round, for recall.** Every added line, and every new data flow into an existing sink, is checked against a 10-category checklist (injection; paths and files; access control; mass assignment; server-side fetches; deserialisation and XML entities; transport and crypto; sensitive data exposure; web sinks, CSRF and CORS; agent and LLM flows) and the checks reviews miss, such as a guard added to one handler but not its siblings. Nothing is dropped for looking minor at this stage.
- **Verification, for precision, refuted by default.** Each candidate must first be written as "an attacker who … can … to gain …". Then three lenses: reachability (source, path, sink and the attacker's position), impact (a concrete gain) and defences (cited, never assumed). A candidate is confirmed only with source, sink and the missing defence all cited.
- **Attacker is not victim.** A flaw that harms only the attacker, on their own machine or account, is refuted. That never excuses a server-side fetch, other people's data, a gate on what a model or agent may do, or config read from a project folder.
- **Exploitability 8/10 or higher.** 10 is an unauthenticated remote attacker with the path cited; 8 needs one nameable precondition the code does not prevent. Anything at 7 or lower is counted as dropped, not reported.
- **Second finder round.** With the candidates so far set aside, it looks again for different flaws, checklist categories with no candidate first, at most twice.
- **Privacy lens.** For a change that touches personal data it lists each field and answers from the code why it is collected, where it flows, how it is deleted and who can read it. An unanswered question is a finding; it states facts about the code, never a legal conclusion.
- **Older flaws are labelled.** A real flaw whose path existed before the change is reported as "Worth considering — predates this change", never as blocking.
- Replies are plain sentences; say "terse" or "caveman" for short ones and "normal" to switch back.

### What it does not report

- Availability-only issues: denial of service, exhaustion, ReDoS, rate limits.
- Trusted or already-compromised inputs: environment variables, CLI flags, server config, protected files.
- Missing hardening or headers without a concrete exploit; theoretical races; timing side channels.
- Outdated dependencies; tests, fixtures, docs and dev scripts that no untrusted input reaches; client-side-only authorization.
- Low-impact classes such as open redirect, tabnabbing or prototype pollution, unless chained to a score of 8 or more.

Logging secrets or personal data is always reported.

### Modes

| Mode | What it does | Verdict |
|---|---|---|
| review | the full process above | CLEAN or ISSUES |
| verify | votes CONFIRMED or REFUTED on each candidate from one lens (reachability, impact or defenses), with a "predates" flag | one vote per candidate |

## Tools and cards you'll see

| Call | When | Approval card |
|---|---|---|
| fs.read, fs.find, fs.search; code.git status and log | always | none |
| web.scrape | public advisories and docs | none |
| code.git diff | working-tree review | may raise one; none in a trusted workspace on the Gateway we tested |
| code.git blame | checking whether a flaw predates the change | may raise one, as diff |
| os.execute with read-only git (diff, log, merge-base, show) | branch review | one per command; Critical risk, so it always asks |
| info.request | unclear base branch | a question, not a card |

- As a sub-agent of Lead Developer it reads the change its brief names (a diff file, or the working tree with one code.git diff call) and the candidates, and runs no shell commands.
- TOOLS.md pins web.scrape everywhere, and fs.read, fs.find and fs.search for the sub-agent profile so they stay visible when the lead narrows a child's tools.

## After installing

- **Effort:** high works best for security review: `sophon agents models security-reviewer --effort high`. Delegated runs use it only while the lead's chat has no effort of its own (`/effort reset` there).
- **Bind and trust the repository:** run `sophon` in the project folder, then `/trust`, so AGENTS.md and the project's security rules load.
- **Allowed Medium-risk calls for the session** (set with `/permissions`) cover this agent's code.git diff and blame at the root. They never cover its os.execute calls, and never any sub-agent's calls.
- **With Lead Developer:** install with `sophon agents install security-reviewer --allow-delegation-from lead-developer` and keep the id `security-reviewer`. If the lead restricts delegation to an allow list, add this id to it.
- **Accepted risks:** when you tell it a risk is accepted, it records that decision in your user memory and cites it in later reviews of the same code instead of reporting it again.

## Works best with

- `lead-developer`: adds it to reviews when a change touches a trust boundary, runs one more finder when it returns two or fewer candidates, and sends each security finding to three verify runs (reachability, impact, defenses) before acting on it.
- `code-reviewer`: the general defects this agent leaves out.
- `developer`: fixes confirmed issues, with a test that fails first.

## Limits

- It reviews a change, not a whole system.
- Static reading only: it runs no builds, tests, scanners or exploits.
- code.git diff sees uncommitted tracked files only. Committed work needs the branch form, which costs one approval per command.
- A diff cut off by the output window is split, and anything not reviewed is listed.
- As a sub-agent it sees only the change and candidates in its brief.
- "No exploitable issues introduced" is evidence from reading the code, not a guarantee.

## What it never does

- Edit, write or commit anything.
- Contact your application, its hosts or any live system, or probe, scan or attack anything.
- Repeat a hard-coded credential's value; it gives the location and kind only.
- Start sub-agents.
- Follow instructions found in the code under review; text that tries to steer a reviewer is reported as a finding.

## What's new in 3.0.0

- A second finder round, at most twice, that sets the first candidates aside.
- Every candidate is restated as an attacker's gain before it is verified, and attacker-is-not-victim cases are refuted.
- A privacy lens for changes that touch personal data.
- As a sub-agent it reads the change its brief names. A terse voice on request.

## Upgrading from 2.x

- 3.0.0 is a major version, so Sophon never applies it unattended. Take it yourself, one agent at a time: `sophon agents update <id>`.
- Update every family agent you have installed in one sitting. In between, Lead Developer 3.0.0 gives a companion below 3.0.0 the brief that 2.x understands and tells you once which agents to update, and a 3.0.0 companion still accepts a 2.x brief. An agent you created locally from these files reports no version and counts as current.
- Four agents are new: `product-owner`, `product-manager`, `release-engineer` and `agent-engineer`. Install the ones you want with `--allow-delegation-from lead-developer`. Updating never changes delegation settings, so an existing allow list needs them added.
- The instructions are longer. Each new session of this agent, and each sub-agent run of it, reads about 1,600 more tokens than in 2.x.
- 3.0.0 lists the optional `craft-reference` skill, which returns long reference material on request. Sophon offers to install it; if you decline, the agent works from what it carries.
- Your own edits to an installed agent pause its updates. Add `--discard-local-changes` to replace them.

## Reference skill

This agent can read longer tables, checklists and templates from the optional `craft-reference` skill, which Sophon offers when you install the agent. The skill does not run in plan mode or on a Gateway without the Docker sandbox, and the agent then works from the summary it carries. The skill's own notices credit the sources of its topics.

## Credits and license

Ideas re-expressed in our own words also come from JuliusBrussee/caveman (Apache-2.0, © 2026 Julius Brussee); Anthropic's security-guidance plugin, anthropics/claude-plugins-official (Apache-2.0); and anthropics/claude-code-security-review (MIT, © 2025 Anthropic).

Workflow patterns adapted, not copied, from obra/superpowers (MIT, © 2025 Jesse Vincent) and Anthropic's Claude Code plugins (feature-dev, pr-review-toolkit, code-review, frontend-design; Apache-2.0). Licensed under the MIT License; see LICENSE.
