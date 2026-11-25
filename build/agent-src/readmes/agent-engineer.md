# Agent Engineer

Designs, writes, tests and reviews the instructions of Sophon agents and skills: SOUL text, TOOLS pins and manifests. It changes an instruction only after it has seen the behaviour the change is meant to fix.

Part of the Buildersoft development family {{= FamilyVersion}}.

{{# roster}}

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
- rule writes the scenario first, outside every package folder, and needs a control arm that fails without the new text. A control that already behaves means nothing is written. You can say "untested is fine": the scenario is still written first, and the text is labelled `Untested:` in the report and the commit.
- review is read-only: the project's lint first, then the platform's rules. Each finding has a line and a rewrite; the verdict is PASSES or FAILS.
- diagnose reads a finished session with session.history and looks at cost, repeats, plan drift, instructions not acted on and stops. Every finding cites its sequence numbers. It ends with the one change that would have saved the most.
- Work bigger than a small change gets a plan file in `docs/plans/` that you approve, a `sophon/<slug>` branch and one verified commit per task, then the Git menu: Push + open PR, Merge into `<base>` locally, or Keep local. Discard runs only when you ask, after one more confirmation.
- Say "terse" or "caveman" for short replies and "normal" to switch back.

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

- Install: `sophon agents install agent-engineer --allow-delegation-from lead-developer` (drop the flag if you do not use Lead Developer, which can hand it instruction tasks inside a plan).
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

{{> readme/70-reference-skill}}

## Credits and license

Ideas re-expressed in our own words also come from JuliusBrussee/caveman (Apache-2.0, © 2026 Julius Brussee).

Workflow patterns adapted, not copied, from obra/superpowers (MIT, © 2025 Jesse Vincent) and Anthropic's Claude Code plugins (feature-dev, pr-review-toolkit, code-review, frontend-design; Apache-2.0). Licensed under the MIT License; see LICENSE.
