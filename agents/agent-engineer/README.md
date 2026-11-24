# Agent Engineer

Designs, writes, tests and reviews the instructions of Sophon agents and skills: SOUL text, TOOLS pins and manifests. It changes an instruction only after it has seen the behaviour the change is meant to fix.

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
| product-manager | discover / analyst / brief / PRD / prioritise / pre-mortem | no | its product documents only | no |
| product-owner | spec / slice / refine / validate / accept / replan / triage | no | its requirements and story files only | no |
| release-engineer | check / ship / deploy / watch / upgrade / rollback | no | version, changelog and dependency files | yes |
| **agent-engineer** (this one) | agent instructions: design / rule / test / review / diagnose | no | agent and skill instruction files | yes |

## When to use

- Designing a new agent, skill or mode, starting from the cheapest form that works.
- Adding or changing one rule in an agent's instructions.
- Writing a scenario that tests one behaviour.
- Reviewing a package against the platform's size, pin and scanner rules before you publish it.
- Explaining a finished session: its cost, repeated work, or a plan that was not followed.

## Not for

- MCP servers: `mcp-integration-engineer`.
- Application code, including skill entrypoint code: `developer`.
- User documentation: `technical-writer`.
- Code review: `code-reviewer`.

## How it works

- Finds the layout, any composer or generator, and the project's own lint and validation commands first; they outrank its checklist. A generated file changes at its source.
- Modes: design, rule, test, review and diagnose.
- design chooses the cheapest carrier and says why: nothing, a line in AGENTS.md, a mode in an existing agent, a skill, or a new agent. A new agent, skill or mode starts with discovery and a plan, as in every writer of the family.
- rule writes the scenario first, outside every package folder, and needs a control arm that fails without the new text. A control that already behaves means nothing is written. You can say "untested is fine": the text is then labelled `Untested:` in the report and the commit.
- review is read-only: the project's lint first, then the platform's rules. Each finding has a line and a rewrite; the verdict is PASSES or FAILS.
- diagnose reads a finished session with session.history and looks at cost, repeats, plan drift, instructions not acted on and stops. Every finding cites its sequence numbers. It ends with the one change that would have saved the most.

## Tools and cards you'll see

| Tool | Approval card |
|---|---|
| fs.list, fs.find, fs.search, fs.read, fs.info | none |
| agent.list, session.history, web.scrape | none |
| fs.write, fs.edit (scenario and instruction sources) | one each |
| os.execute (the project's lint or eval command, the commit) | one each |
| info.request | a question, not a card |

rule costs the scenario file, the edited sources and each run; review none, or one for the project's lint; diagnose none.

## After installing

- Effort: set it to high with `sophon agents models agent-engineer --effort high`.
- Start `sophon` in the project folder so the session is bound, then run `/trust` so the project's instructions load.
- Pick it with `/agent agent-engineer`, or `--agent agent-engineer` on the command line.

## Plan mode

Plans work as in every writer of the family; review and diagnose work read-only.

## Limits

- It cannot open a fresh session, so the test arms are run by you in a new chat, or by the project's eval command.
- A session list shows your top-level sessions only; a sub-agent's session is read by the id its parent's result names.
- The platform limits it reviews against are those of Sophon 2.2.2.

## What it never does

- Changes an instruction without a recorded failing control or the `Untested:` label.
- Loosens a gate to make a scenario pass, or writes text that lowers what needs your approval.
- Installs or publishes a package.
- Writes skill entrypoint code.
- Ships a scenario inside a package.

## Credits and license

Ideas re-expressed in our own words also come from JuliusBrussee/caveman (Apache-2.0, © 2026 Julius Brussee).

Workflow patterns adapted, not copied, from obra/superpowers (MIT, © 2025 Jesse Vincent) and Anthropic's Claude Code plugins (feature-dev, pr-review-toolkit, code-review, security-review, frontend-design; Apache-2.0). Licensed under the MIT License; see LICENSE.
