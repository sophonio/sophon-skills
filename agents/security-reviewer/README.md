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
- Inside a Lead Developer review: the lead sends it the security lens of a change that crosses a trust boundary, and candidate security findings to verify from one angle.

## Not for

- General code quality: use `code-reviewer`.
- Dependency or CVE audits and penetration testing: use a dedicated tool or a person.
- Fixing the issues: use `developer`.
- Whole-system threat models, unless you ask for one.

## How it works

- **Scope first.** The working tree (one diff approval) or a branch against its base (one shell approval for a read-only git diff). With an unclear base it asks. In plan mode it reviews the working tree only and says so.
- **Exposure and defences.** It works out who can reach the changed code and searches for the defences already there: auth middleware, model binding, sanitisers, CSRF protection, allowlists.
- **Finder round.** Every added line, and every new data flow into an existing sink, is checked against a 10-category checklist: injection; paths and files; access control; mass assignment; server-side fetches; deserialisation and XML entities; transport and crypto; sensitive data exposure; web sinks, CSRF and CORS; agent and LLM flows.
- **Three-lens verification, refuted by default.** Reachability (source, path, sink and the attacker's position), impact (a concrete gain) and defences (cited, never assumed). A candidate is confirmed only with source, sink and the missing defence all cited.
- **Exploitability 8/10 or higher.** 10 is an unauthenticated remote attacker with the path cited; 8 needs one nameable precondition the code does not prevent. Anything at 7 or lower is counted as dropped, not reported.
- **Gap sweep.** Checklist categories with no candidate get another look, at most twice.
- **Older flaws are labelled.** A real flaw whose path existed before the change is reported as "Worth considering — predates this change", never as blocking.

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
| code.git diff | working-tree review | one |
| code.git blame | checking whether a flaw predates the change | one |
| os.execute with read-only git (diff, log, merge-base, show) | branch review | one per command; Critical risk, so it always asks |
| info.request | unclear base branch | a question, not a card |

- As a sub-agent of Lead Developer it reads only the review-diff file and the candidates in its brief, so it raises no cards of its own.
- TOOLS.md pins web.scrape everywhere, and fs.read, fs.find and fs.search for the sub-agent profile so they stay visible when the lead narrows a child's tools.

## After installing

- **Effort:** high works best for security review: `sophon agents models security-reviewer --effort high`. Delegated runs use it only while the lead's chat has no effort of its own (`/effort reset` there).
- **Bind and trust the repository:** run `sophon` in the project folder, then `/trust`, so AGENTS.md and the project's security rules load.
- **Allowed Medium-risk calls for the session** (set with `/permissions`) cover this agent's code.git diff and blame at the root. They never cover its os.execute calls, and never any sub-agent's calls.
- **With Lead Developer:** install with `sophon agents install security-reviewer --allow-delegation-from lead-developer` and keep the id `security-reviewer`. If the lead restricts delegation to an allow list, add this id to it.
- **Accepted risks:** when you tell it a risk is accepted, it records that decision in your user memory and cites it in later reviews of the same code instead of reporting it again.

## Works best with

- `lead-developer`: adds it to review panels when a change touches a trust boundary, and sends each security finding to three verify runs (reachability, impact, defenses) before acting on it.
- `code-reviewer`: the general defects this agent leaves out.
- `developer`: fixes confirmed issues, with a test that fails first.

## Limits

- It reviews a change, not a whole system.
- Static reading only: it runs no builds, tests, scanners or exploits.
- code.git diff sees uncommitted tracked files only. Committed work needs the branch form, which costs one approval per command.
- A diff cut off by the output window is split, and anything not reviewed is listed.
- As a sub-agent it sees only the diff file and candidates in its brief.
- "No exploitable issues introduced" is evidence from reading the code, not a guarantee.

## What it never does

- Edit, write or commit anything.
- Contact your application, its hosts or any live system, or probe, scan or attack anything.
- Repeat a hard-coded credential's value; it gives the location and kind only.
- Start sub-agents.
- Follow instructions found in the code under review; text that tries to steer a reviewer is reported as a finding.

## What's new in 2.1.0

- Seven companions joined the family: `frontend-developer`, `design-system-engineer`, `visual-designer`, `e2e-test-engineer`, `accessibility-reviewer`, `mcp-integration-engineer` and `technical-writer`. They are licensed Apache-2.0; this agent stays MIT. Add the ones you install to an existing Lead Developer allow-list.

## What's new in 2.0.0

- New in the family: this is its first release, numbered 2.0.0 to match the family generation.
- Ships a TOOLS.md that pins web.scrape and the read tools; nothing else needs installing.
- Updating an agent does not change its delegation settings. If your Lead Developer 1.0.0 uses an allow list, add the new companions `code-reviewer`, `debugger` and `security-reviewer` to it.

## Credits and license

Workflow patterns adapted, not copied, from obra/superpowers (MIT, © 2025 Jesse Vincent) and Anthropic's Claude Code plugins (feature-dev, pr-review-toolkit, code-review, security-review, frontend-design; Apache-2.0). Licensed under the MIT License; see LICENSE.
