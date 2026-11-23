# Technical Writer

Writes and tightens the documentation people follow, checks every command and path against the code, and reads a doc the way a newcomer would.

Part of the Buildersoft development family 2.1.0.

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
| **technical-writer** (this one) | documentation: draft / edit / reader-test | no | documentation files | yes |

## When to use

- A new README, docs page, guide, ADR write-up or changelog entry.
- Existing documentation that is long, vague or written for the wrong reader.
- Checking that the commands, paths, flags and defaults in a doc still match the code.
- Finding out what a newcomer would get stuck on before you publish a doc.

## Not for

- Code changes: use `developer`.
- Architecture decisions: use `software-architect`. This agent writes up a decision already made; it does not make one.
- Interface microcopy such as buttons, errors and empty states: use `ui-ux-designer`.
- Test suites: use `qa-engineer`.

## How it works

- It starts by reading the doc, your project instructions and the code the doc describes, and finds the house style: the docs layout, heading style, front matter, link style and changelog format. Your existing style wins over its own.
- **Draft:** for a short doc it offers one pass (an outline, then a full draft) or section by section; you can switch to one pass at any point. It asks a few questions about the doc type, the reader and what the reader should be able to do afterwards, invites you to share context in any shape, then asks numbered follow-up questions in chat that you can answer in shorthand. Once you agree an outline it writes a skeleton with every heading, then fills one section at a time: questions, a numbered list of candidate points you keep or drop, a draft, and your feedback. It ends with a read-through of the whole doc for flow, repetition and contradictions. As a sub-agent it derives the outline from the brief, chooses the points itself and records each non-obvious choice.
- **Edit:** it tightens an existing doc for one reader, puts the task first (the shortest path to a first result, then reference and rationale), and checks every command, path, flag, default and version against the repository. It asks before moving or removing a section.
- **Reader test:** read-only. It lists the questions a newcomer would arrive with and marks each answered, partly answered or not answered, quoting the line. It follows every step literally, checking each command against the repository and running only harmless forms such as `--help`, `--version` or a dry run; a run that installs or writes needs your answer first. You get the unanswered questions, the steps that fail and what the doc assumes the reader already knows.
- A command goes into a doc only after it has found its definition (a package script, build target, CLI option or CI step) or run a harmless form of it. What it cannot confirm is left out or marked, and listed as not verified.
- One doc drafted with you section by section needs no plan file: the agreed outline is the plan. Edits over 40 changed lines, or work across three or more doc files, get a plan file in `docs/plans/` that you approve, a `sophon/<slug>` branch and one verified commit per task, then a Push + PR / Keep local / Discard menu.

## Tools and cards you'll see

| Action | Card |
|---|---|
| Reading and searching files, `code.git` status and log, `web.scrape`, the todo list | none |
| Each doc file it creates or edits | one per file |
| Harmless command checks (`os.execute`), chained into one command where possible | one each |
| Approving an outline, a structural change or a plan | a question, or the plan card in plan mode |

## After installing

- **Effort:** the default is fine.
- **Allowed Medium-risk calls for the session** never cover this agent's edits, commits or shell commands, nor any call it makes as a sub-agent: as a Marketplace agent it always asks for those.
- **Bind and trust the folder.** Run `sophon` in the repository so the session is bound, then `/trust` the folder so its AGENTS.md or CLAUDE.md conventions load.
- Pick it with `/agent technical-writer` or `--agent technical-writer`.

## Works best with

- `lead-developer`: hands it the documentation step of a larger change.
- `developer`: makes the code changes a doc fix turns out to need.
- `software-architect`: makes the decision this agent writes up as ADR prose.
- `researcher`: gathers cited facts for a doc about unfamiliar code.

## Limits

- It changes documentation files only, including docs navigation and front-matter files such as a section `meta.json`, the `mkdocs.yml` nav or `sidebars.js`. A doc fix that needs a code or other config change is reported, not made.
- As a sub-agent there is no one to interview: it works from the brief and the code and lists its open questions.
- It runs only harmless forms of documented commands. Commands that install, build into the tree or change state are checked by reading their definitions, unless you allow the run when it asks (or, as a sub-agent, the brief allows it).
- Generated docs are changed at their source; it names the generator instead of editing the output.

## What it never does

- Document behaviour it has not confirmed in the code or by a run.
- Invent decisions, owners, dates or numbers.
- Edit source code, configuration (other than docs navigation), scripts or tests.
- Push without your choice in the Git menu.

## What's new in 2.0.0

- First release in the family: draft, edit and reader-test modes, with every documented command and path checked against the repository.
- A TOOLS.md file pins `web.scrape`, and keeps `fs.read`, `fs.find` and `fs.search` visible when it runs as a sub-agent.
- Plan files, one commit per verified task and the Git menu, shared with the family's other writers.

## Credits and license

The section-by-section drafting method is inspired by Anthropic's doc-coauthoring skill and written independently.

Workflow patterns adapted, not copied, from obra/superpowers (MIT, © 2025 Jesse Vincent) and Anthropic's Claude Code plugins (feature-dev, pr-review-toolkit, code-review, security-review, frontend-design; Apache-2.0).

Licensed under the Apache License, Version 2.0; see LICENSE.
