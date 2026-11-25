# Technical Writer

Writes and tightens the documentation people follow, checks every command and path against the code, and reads a doc the way a newcomer would.

Part of the Buildersoft development family 3.0.0.

| Agent | Role | Delegates | Changes files | Commits |
|---|---|---|---|---|
| lead-developer | orchestrator: sizes, plans, builds, verifies, commits | yes (depth 1) | yes | yes |
| developer | implementer: tdd / direct / debug | no | yes | yes |
| researcher | codebase and web facts, every claim cited | no | no | no |
| software-architect | blueprint / ADR / greenfield / compare / critique | no | its plan, ADR or design note only | no |
| code-reviewer | review / refute / re-review / completeness | no | no | no |
| qa-engineer | verification gate, regression checks, tests | no | tests, when asked | yes |
| debugger | root cause first, then a fix when asked | no | fix + regression test, when asked | yes |
| security-reviewer | exploitable vulnerabilities only | no | no | no |
| ui-ux-designer | discover / direction / refine / build / critique / copy / judge | no | UI presentation files | yes |
| frontend-developer | UI implementer: component / direct / artifact / perf / variant | no | yes | yes |
| design-system-engineer | audit / tokens / theme / playground / brand-check / guards | no | tokens, themes, components, token guards | yes |
| visual-designer | concept / art / generative / image / motion | no | asset files | yes |
| e2e-test-engineer | browser end-to-end tests: write / visual / flake | no | e2e tests | yes |
| accessibility-reviewer | WCAG 2.2 AA: audit / review | no | no | no |
| mcp-integration-engineer | MCP servers: design / build / evals | no | yes | yes |
| **technical-writer** (this one) | documentation: draft / edit / reader-test | no | documentation files | yes |
| product-manager | discover / analyst / brief / PRD / prioritise / pre-mortem | no | its product documents only | no |
| product-owner | spec / slice / refine / validate / accept / replan / triage | no | its requirements and story files only | no |
| release-engineer | check / ship / deploy / watch / upgrade / rollback | no | version, changelog and dependency files | yes |
| agent-engineer | agent instructions: design / rule / test / review / diagnose | no | agent and skill instruction files | yes |

## When to use

- A new README, docs page, guide, ADR write-up or changelog entry.
- Existing documentation that is long, vague or written for the wrong reader.
- Checking that the commands, paths, flags and defaults in a doc still match the code.
- Finding out what a newcomer would get stuck on before you publish a doc.

## Not for

- Code changes: `developer`. Test suites: `qa-engineer`.
- Architecture decisions: `software-architect`. This agent writes up a decision already made; it does not make one.
- Interface microcopy such as buttons, errors and empty states: `ui-ux-designer`.
- Requirements and stories: `product-owner`. Agent instructions: `agent-engineer`. Cutting a release: `release-engineer`.

## How it works

- It starts by reading the doc, your project instructions and the code the doc describes, and finds the house style: the docs layout, heading style, front matter, link style and changelog format. Your existing style wins over its own.
- **Draft:** for a short doc it offers one pass (an outline, then a full draft) or section by section; you can switch to one pass at any point. It asks a few questions about the doc type, the reader and what the reader should be able to do afterwards, invites you to share context in any shape, then asks numbered follow-up questions in chat that you can answer in shorthand. Once you agree an outline it writes a skeleton with every heading, then fills one section at a time: questions, a numbered list of candidate points you keep or drop, a draft, and your feedback. It ends with a read-through of the whole doc for flow, repetition and contradictions. As a sub-agent it derives the outline from the brief, chooses the points itself and records each non-obvious choice.
- **Edit:** it tightens an existing doc for one reader, puts the task first (the shortest path to a first result, then reference and rationale), and checks every command, path, flag, default and version against the repository. It asks before moving or removing a section.
- **Reader test:** read-only. It lists the questions a newcomer would arrive with and marks each answered, partly answered or not answered, quoting the line. It follows every step literally, checking each command against the repository and running only harmless forms such as `--help`, `--version` or a dry run; a run that installs or writes needs your answer first. You get the unanswered questions, the steps that fail and what the doc assumes the reader already knows.
- **Drift check:** every backticked path, command, flag, route and symbol is looked up in the repository. Where doc and code disagree the code is right: it fixes the doc and lists the drift. Behaviour the code lacks is reported, never made true by rewording.
- A command goes into a doc only after it has found its definition (a package script, build target, CLI option or CI step) or run a harmless form of it. What it cannot confirm is left out or marked, and listed as not verified.
- **Terms and prose:** one name per concept, as your project glossary decides it, with aliases flagged. Before saving it scans the text for filler, weight words and sentences about the document instead of its subject.
- One doc drafted with you section by section needs no plan file: the agreed outline is the plan. Edits over 40 changed lines, or work across three or more doc files, get a plan file in `docs/plans/` that you approve, a `sophon/<slug>` branch and one verified commit per task, then the finish menu: Push + open PR, Merge into `<base>` locally, or Keep local. Discard runs only when you ask, after a second confirmation.
- Replies are plain sentences; say "terse" or "caveman" for short ones and "normal" to switch back. The docs themselves are always in full sentences.

## Tools and cards you'll see

| Action | Card |
|---|---|
| Reading and searching files, `code.git` status and log, `web.scrape`, the todo list | none |
| Each doc file it creates or edits | one per file |
| Harmless command checks (`os.execute`), chained into one command where possible | one each |
| `code.git` diff | may raise one; none in a trusted workspace on the Gateway we tested |
| Approving an outline, a structural change or a plan | a question, or the plan card in plan mode |

## After installing

- **Install:** `sophon agents install technical-writer`, with `--allow-delegation-from lead-developer` if Lead Developer should brief it. The default effort is fine.
- **Allowed Medium-risk calls for the session** never cover this agent's edits, commits or shell commands, nor any call it makes as a sub-agent.
- **Bind and trust the folder.** Run `sophon` in the repository so the session is bound, then `/trust` the folder so its AGENTS.md conventions load.

## Works best with

- `lead-developer`: hands it the documentation step of a larger change.
- `developer`: makes the code changes a doc fix turns out to need.
- `software-architect`: makes the decision this agent writes up as ADR prose.
- `researcher`: gathers cited facts for a doc about unfamiliar code, and drafts project context for AGENTS.md that this agent can save.

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

## What's new in 3.0.0

- A drift check of every backticked name against the code, glossary discipline and a prose scan before saving.
- The finish menu adds Merge into `<base>` locally; Discard only on request.
- A terse voice for replies on request.

## Upgrading from 2.x

- 3.0.0 is a major version, so Sophon never applies it unattended. Take it yourself, one agent at a time: `sophon agents update <id>`.
- Update every family agent you have installed in one sitting. In between, Lead Developer 3.0.0 gives a companion below 3.0.0 the brief that 2.x understands and tells you once which agents to update, and a 3.0.0 companion still accepts a 2.x brief. An agent you created locally from these files reports no version and counts as current.
- Four agents are new: `product-owner`, `product-manager`, `release-engineer` and `agent-engineer`. Install the ones you want with `--allow-delegation-from lead-developer`. Updating never changes delegation settings, so an existing allow list needs them added.
- The instructions are longer. Each new session of this agent, and each sub-agent run of it, reads about 1,800 more tokens than in 2.x.
- 3.0.0 lists the optional `craft-reference` skill, which returns long reference material on request. Sophon offers to install it; if you decline, the agent works from what it carries.
- Your own edits to an installed agent pause its updates. Add `--discard-local-changes` to replace them.

## Reference skill

This agent can read longer tables, checklists and templates from the optional `craft-reference` skill, which Sophon offers when you install the agent. The skill does not run in plan mode or on a Gateway without the Docker sandbox, and the agent then works from the summary it carries. The skill's own notices credit the sources of its topics.

## Credits and license

Ideas re-expressed in our own words also come from JuliusBrussee/caveman (Apache-2.0, © 2026 Julius Brussee); blader/humanizer (MIT, © 2025 Siqi Chen); and mattpocock/skills (MIT, © 2026 Matt Pocock).

The section-by-section drafting method is inspired by Anthropic's doc-coauthoring skill and written independently.

Workflow patterns adapted, not copied, from obra/superpowers (MIT, © 2025 Jesse Vincent) and Anthropic's Claude Code plugins (feature-dev, pr-review-toolkit, code-review, frontend-design; Apache-2.0).

Licensed under the Apache-2.0 License; see LICENSE.
