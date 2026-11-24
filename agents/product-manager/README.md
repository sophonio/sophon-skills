# Product Manager

Product discovery and definition: whether something is worth building and for whom, written down so that others can specify and build it.

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
| security-reviewer | exploitable vulnerabilities only | no | no | no |
| ui-ux-designer | direction / build / critique / copy / judge | no | UI presentation files | yes |
| frontend-developer | UI implementer: component / direct / artifact / perf | no | yes | yes |
| design-system-engineer | audit / tokens / theme / playground / brand-check | no | tokens, themes, components | yes |
| visual-designer | concept / art / generative / image / motion | no | asset files | yes |
| e2e-test-engineer | browser end-to-end tests: write / visual / flake | no | e2e tests | yes |
| accessibility-reviewer | WCAG 2.2 AA: audit / review | no | no | no |
| mcp-integration-engineer | MCP servers: design / build / evals | no | yes | yes |
| technical-writer | documentation: draft / edit / reader-test | no | documentation files | yes |
| **product-manager** (this one) | discover / analyst / brief / PRD / prioritise / pre-mortem | no | its product documents only | no |
| product-owner | spec / slice / refine / validate / accept / replan / triage | no | its requirements and story files only | no |
| release-engineer | check / ship / deploy / watch / upgrade / rollback | no | version, changelog and dependency files | yes |
| agent-engineer | agent instructions: design / rule / test / review / diagnose | no | agent and skill instruction files | yes |

## When to use

- A discovery interview for a bare idea: who has the problem today, what they do about it, and the premises the idea rests on.
- Sourced evidence on users, a market or how the work is done today (the business-analyst mode).
- A one-page brief, a lean PRD with stable ids, a ranked list of problems, or a pre-mortem.
- `PRODUCT.md`, the short product brief at the repository root that the other agents read.

## Not for

- Requirements with acceptance criteria, stories and acceptance: `product-owner`.
- Solution design: `software-architect`.
- Facts about the code: `researcher`.
- Building: `lead-developer`.

## How it works

- Reads `PRODUCT.md`, `docs/product/` and the project instructions first, and does not ask what they already answer.
- Modes: discover (root only), analyst, brief (root only), prd, prioritise and pre-mortem.
- discover asks one open question and ends its turn, then at most five forcing questions, one per message, each with its own guess. It lists three to seven numbered premises for you to accept, change or reject, and offers two or three approaches, "use what already exists" among them. No document is drafted before the premises are answered; "just write it" turns every open premise into an `Assumption:` line.
- A PRD has nine sections with stable ids (`UJ-n`, `FR-n`, `RULE-n`, `NG-n`, `SM-n`, `OQ-n`), at least one reasoned non-goal and a counter-measure for every measure. A section with nothing known holds one `Unknown:` line; it never invents a number.
- Documents go to `docs/product/<slug>/` unless your project instructions name another folder.
- Every draft is shown in full, then one "Product" question: Save, Change something or Stop. Nothing is written before the yes.
- Hands off: "Next: tell Product Owner 'spec <path>'."

## Tools and cards you'll see

| Tool | Approval card |
|---|---|
| fs.list, fs.find, fs.search, fs.read | none |
| web.search, web.scrape | none |
| fs.write or one edit (a document you approved) | one |
| info.request | a question, not a card |

No card while it interviews or researches; one per saved document, and one more for the AGENTS.md line it offers after a new `PRODUCT.md`.

## After installing

- Effort: set it to high with `sophon agents models product-manager --effort high`.
- Start `sophon` in the project folder so the session is bound, then run `/trust` so the project's instructions load.
- Pick it with `/agent product-manager`, or `--agent product-manager` on the command line.

## Plan mode

It interviews and drafts as usual but cannot save; the draft stays in the chat until you leave plan mode and say "save".

## Limits

- As a sub-agent it cannot interview: discover and brief return NEEDS_CONTEXT with the sentence to say to it at root, and the draft is its final message.
- Its evidence is only the pages and files it opened.
- It does not prove demand: it records what you and the sources say.

## What it never does

- Invents a user, a quote, a number, a competitor, a date or an owner.
- Writes code, configuration, tests or plan files, or runs commands.
- Commits: Lead Developer commits product documents with the first task built from them.
- Decides for you: it recommends, and records what you chose in your own words.

## Credits and license

Ideas re-expressed in our own words also come from JuliusBrussee/caveman (Apache-2.0, © 2026 Julius Brussee); blader/humanizer (MIT, © 2025 Siqi Chen); garrytan/gstack (MIT, © 2026 Garry Tan); bmad-code-org/BMAD-METHOD (MIT, © 2025 BMad Code, LLC); and phuryn/pm-skills (MIT, © 2026 Pawel Huryn).

Workflow patterns adapted, not copied, from obra/superpowers (MIT, © 2025 Jesse Vincent) and Anthropic's Claude Code plugins (feature-dev, pr-review-toolkit, code-review, security-review, frontend-design; Apache-2.0). Licensed under the MIT License; see LICENSE.
