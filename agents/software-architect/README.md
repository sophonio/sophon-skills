# Software Architect

Read-only software design: one decisive blueprint grounded in your code, and a plan file Lead Developer can run.

Part of the Buildersoft development family 3.0.0.

| Agent | Role | Delegates | Changes files | Commits |
|---|---|---|---|---|
| lead-developer | orchestrator: sizes, plans, builds, verifies, commits | yes (depth 1) | yes | yes |
| developer | implementer: tdd / direct / debug | no | yes | yes |
| researcher | codebase and web facts, every claim cited | no | no | no |
| **software-architect** (this one) | blueprint / ADR / greenfield / compare / critique | no | its plan or ADR file only | no |
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
## When to use

- A blueprint for a feature or subsystem, before any code is written.
- An architecture decision record (ADR).
- A comparison of two or three competing designs against a written rubric.
- A gap check on an existing plan: missing tasks, weak verification, ordering, unsafe steps.
- A greenfield system: requirements with numbers, estimates, a data model, an API sketch, failure modes and an evolution path.

## Not for

- Implementing the plan: `lead-developer`, `developer`.
- Open fact-finding: `researcher`.
- Reviewing a finished diff: `code-reviewer`.

## How it works

- Asks one round of at most four questions before designing, and only when the answers change the design.
- Reads one to three analogous features in your code first and cites them with `file:line`. It writes down constraints, invariants and non-goals, and never invents a requirement.
- Commits to one approach and names the strongest alternative and why it lost. Perspectives: minimal, clean, or pragmatic (the default). With none given, it opens with a three-row comparison.
- Blueprints carry a trade-off table (choice, solves, worsens, revisit when) and, for backend work, a failure-mode table (failure, detect, surface, recover). New infrastructure must first answer four questions: what the current stack cannot do, who runs it, what leaving it costs, and the simplest version for the next year.
- Modes: blueprint, adr, greenfield, compare (scores 2-3 blueprints 1-5 on fit, size, risk, testability and reversibility) and critique (verdict READY or NEEDS_DECISION).
- Ends with an implementation map, a build sequence, an end-to-end check, a plan file in the family format, and a ready plan.propose input of at most four linear steps, so the plan card recommends Inline.
- Saves the plan or ADR as a draft (you see it on the write card), then asks: Mark it approved, Change something, or Keep as draft.
- Hands off: "To execute: tell Lead Developer 'execute docs/plans/<file>'."

## Tools and cards you'll see

| Tool | Approval card |
|---|---|
| fs.list, fs.find, fs.search, fs.read | none |
| web.search, web.scrape | none |
| code.git status and log | none |
| fs.write (the plan or ADR draft) | one |
| the edit that marks the file approved | one |
| info.request | a question, not a card |

A typical design costs two cards: the draft and the approval edit. TOOLS.md pins web.scrape in every profile and keeps fs.read, fs.find and fs.search visible when Lead Developer narrows a sub-agent's tools.

## After installing

- Effort: set it to high with `sophon agents models software-architect --effort high`. When Lead Developer delegates to it, that setting reaches the delegated run only while the lead's chat has no effort of its own (`/effort reset`).
- Start `sophon` in the project folder so the session is bound, then run `/trust` so the project's AGENTS.md or CLAUDE.md loads. Unbound, it can read and design, but paths are host-wide and project instructions are not loaded.
- Pick it with `/agent software-architect`, or `--agent software-architect` on the command line.
- Allowing Medium-risk calls for the session (run `/permissions` and choose Medium) never covers this agent's plan or ADR write: a package agent's edits always raise a card, and so does every sub-agent's call.

## Plan mode

In plan mode the architect cannot save files. It returns the plan draft and the plan.propose input in its reply, then tells you to leave plan mode and say "save", or to give the plan to Lead Developer. It never calls plan.propose itself: the agent that executes the plan proposes it, because graph steps would otherwise run as the architect.

## Works best with

- `lead-developer`: executes the plan file task by task, with a verified commit per task; in large work it runs two or three architects as a judge panel.
- `researcher`: gathers the facts first, with sources.
- `code-reviewer`: reviews the finished change against the plan.

## Limits

- It designs only from what it read; open fact-finding belongs to `researcher`.
- It runs no builds, tests or commands, so the plan's Run and Expected lines are proposals until `lead-developer` or `qa-engineer` runs them.
- In plan mode it cannot save its file. On the Personal edition the Dashboard cannot approve plan cards; Lead Developer then offers the chat route ("Choose Keep planning and type GO").
- One decisive design per run; ask again for an alternative.

## What it never does

- Edits source code, runs shell commands, commits or pushes.
- Calls plan.propose.
- Starts sub-agents.
- Writes any file other than its own plan or ADR, and that only after you see the write card.

## What's new in 2.1.0

- Seven companions joined the family: `frontend-developer`, `design-system-engineer`, `visual-designer`, `e2e-test-engineer`, `accessibility-reviewer`, `mcp-integration-engineer` and `technical-writer`. They are licensed Apache-2.0; this agent stays MIT. Add the ones you install to an existing Lead Developer allow-list.

## What's new in 2.0.0

- Full rewrite as part of the Buildersoft development family 2.0.0.
- Five modes, three perspectives, and plan files in the family format with a ready plan.propose input.
- Saves only the plan or ADR you approve; it never edits code.
- A TOOLS.md that pins the tools it needs.
- Updating does not change delegation settings.
- New companions code-reviewer, debugger and security-reviewer: add them to old allow-lists if you restrict which agents Lead Developer may delegate to.

## Credits and license

Design patterns also draw on backend-design (sheitabrk/backend-design; MIT, © sheitabrk and contributors) and system-design-skills (proyecto26/system-design-skills; MIT, © 2026 Proyecto 26), adapted in original wording.

Workflow patterns adapted, not copied, from obra/superpowers (MIT, © 2025 Jesse Vincent) and Anthropic's Claude Code plugins (feature-dev, pr-review-toolkit, code-review, security-review, frontend-design; Apache-2.0). Licensed under the MIT License; see LICENSE.
