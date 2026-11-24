# Researcher

Read-only research for development work: how this codebase works and what the wider world says about it, with a source for every claim.

Part of the Buildersoft development family 3.0.0.

| Agent | Role | Delegates | Changes files | Commits |
|---|---|---|---|---|
| lead-developer | orchestrator: sizes, plans, builds, verifies, commits | yes (depth 1) | yes | yes |
| developer | implementer: tdd / direct / debug | no | yes | yes |
| **researcher** (this one) | codebase and web facts, every claim cited | no | no | no |
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
## When to use

- How does a feature flow through this codebase, from entry point to side effects?
- Where is something defined, configured or tested?
- Which version of a library does the repo use, and what do that version's docs say?
- What does an error message mean upstream, and is there a known issue?
- Comparing libraries or approaches with dated, primary sources.

## Not for

- Deciding how to build something: `software-architect`.
- Writing or reviewing code: `developer`, `code-reviewer`.
- Proving why something breaks: `debugger`.
- Multi-agent work: `lead-developer`, which can run several researchers at once.

## How it works

- Restates your question in one line, then picks a mode (codebase, external or both) and a depth (quick, medium or thorough; medium by default).
- Codebase mode lists, finds and searches before it reads, then traces entry point → call chain → data → side effects → tests, and ends with the 5-10 files that matter.
- External mode searches wide, then narrow, with the version and year in the query, reads the best pages with web.scrape and prefers primary sources. At medium depth every key claim needs two sources; at thorough depth, a primary source.
- Reads the repo's manifest or lockfile first, so web research targets the version you actually use.
- Works to a budget (about 10, 25 or 60 calls in a codebase) and lists what it did not cover instead of stopping silently.
- Cites every claim: `file:line` for code, a URL with publication and access dates for the web. Reasoning is labelled "Inference:", and each finding carries a confidence of High, Medium or Low.
- Asks at most one question, and only when the answer changes the research (version, platform, subsystem).
- As a sub-agent of Lead Developer, it takes MODE and DEPTH from the brief and ends with the family STATUS block.

## Tools and cards you'll see

| Tool | Approval card |
|---|---|
| fs.list, fs.find, fs.search, fs.read | none |
| web.search, web.scrape | none |
| code.git status and log | none |
| todo.write, datetime.now | none |
| code.git diff or blame (rarely needed) | one each |
| document.save_url (thorough mode, only with your OK) | none, but it adds the page to your document library, and it says so |
| info.request | a question, not a card |

TOOLS.md pins web.scrape in every profile and keeps fs.read, fs.find, fs.search and web.search visible when Lead Developer narrows a sub-agent's tools.

## After installing

- Effort: leave it at the default.
- Start `sophon` in the project folder so the session is bound, then run `/trust` so the project's AGENTS.md or CLAUDE.md loads. Unbound, it can still research, but paths are host-wide and project instructions are not loaded.
- Pick it with `/agent researcher`, or `--agent researcher` on the command line.
- Allowing Medium-risk calls for the session (run `/permissions` and choose Medium) covers this agent's own code.git diff at the root. It never covers a package agent's edits, commits or shell commands, nor any sub-agent's calls; this agent makes none of those anyway.

## Works best with

- `lead-developer`: runs 2-5 researchers at once in its Understand phase, each with a distinct focus, then opens the key cited lines itself.
- `software-architect`: turns the findings into one decisive design and a plan file.
- `debugger`: when the research points at a failure whose cause is unknown.

## Limits

- Sophon has no web.fetch; pages are read with web.scrape in readability mode, so pages behind a login or built entirely in the browser may come back thin.
- It runs no builds, tests or scripts. Where a run would settle a question, it says what the run would prove and who should run it (`qa-engineer` or `lead-developer`).
- Budgets cap coverage on purpose; anything sampled, skipped or capped is listed under "Not covered".
- Search results are capped by the tools. When a result says "showing the first N", it narrows the search or reports the cap.

## What it never does

- Changes files, commits or pushes.
- Runs shell commands.
- Invents a URL, a path or a version.
- Starts sub-agents.
- Stores or repeats secrets. Web pages, file contents and tool output are treated as data, never as instructions.

## What's new in 2.1.0

- Seven companions joined the family: `frontend-developer`, `design-system-engineer`, `visual-designer`, `e2e-test-engineer`, `accessibility-reviewer`, `mcp-integration-engineer` and `technical-writer`. They are licensed Apache-2.0; this agent stays MIT. Add the ones you install to an existing Lead Developer allow-list.

## What's new in 2.0.0

- Full rewrite as part of the Buildersoft development family 2.0.0.
- Codebase, external and both modes; quick, medium and thorough budgets; a fixed report with a dated Sources list and a "Not covered" section.
- A TOOLS.md that pins the tools it needs.
- Updating does not change delegation settings.
- New companions code-reviewer, debugger and security-reviewer: add them to old allow-lists if you restrict which agents Lead Developer may delegate to.

## Credits and license

Workflow patterns adapted, not copied, from obra/superpowers (MIT, © 2025 Jesse Vincent) and Anthropic's Claude Code plugins (feature-dev, pr-review-toolkit, code-review, security-review, frontend-design; Apache-2.0). Licensed under the MIT License; see LICENSE.
