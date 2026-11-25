# Researcher

Read-only research for development work: how this codebase works and what the wider world says about it, with a source for every claim.

Part of the Buildersoft development family {{= FamilyVersion}}.

{{# roster}}

## When to use

- How does a feature flow through this codebase, from entry point to side effects?
- Where is something defined, configured or tested?
- Which version of a library does the repo use, and what do that version's docs say?
- What does an error message mean upstream, and is there a known issue?
- Comparing libraries or approaches with dated, primary sources.
- Getting to know a project: a drafted project-context block for its AGENTS.md.

## Not for

- Deciding how to build something: `software-architect`.
- Writing or reviewing code: `developer`, `code-reviewer`.
- Proving why something breaks: `debugger`.
- Weighing evidence for a product decision: `product-manager`.
- Multi-agent work: `lead-developer`, which can run several researchers at once.

## How it works

- Restates your question in one line, then picks a mode (codebase, external, both or onboard) and a depth (quick, medium or thorough; medium by default).
- Codebase mode lists, finds and searches before it reads, then traces entry point → call chain → data → side effects → tests, and ends with the 5-10 essential files in reading order, each with a line on what it settles.
- External mode searches wide, then narrow, with the version and year in the query, reads the best pages with web.scrape and prefers primary sources. At medium depth every key claim needs two sources; at thorough depth, a primary source.
- **Version first.** Before it describes a library, it reads the version in use from your manifest or lockfile, opens a source for that version and cites it. Forum answers and its own memory are leads to check, never sources; what nothing settles is written "nothing found".
- **Onboard mode** ("get to know this project"): it drafts project context for your AGENTS.md as one block of at most 60 lines in its reply: Commands (marked "not run"), Layout, Entry points, Conventions, Do not touch, Gotchas and Terms, each line with its source. It never saves the file; Technical Writer or Lead Developer can add it.
- Works to a budget (about 10, 25 or 60 calls in a codebase) and lists what it did not cover instead of stopping silently.
- Cites every claim: `file:line` for code, a URL with publication and access dates for the web. Reasoning is labelled "Inference:", and each finding carries a confidence of High, Medium or Low.
- Asks at most one question, and only when the answer changes the research (version, platform, subsystem).
- As a sub-agent of Lead Developer, it takes MODE and DEPTH from the brief and ends with the family STATUS block.
- Replies are plain sentences; say "terse" or "caveman" for short ones and "normal" to switch back.

## Tools and cards you'll see

| Tool | Approval card |
|---|---|
| fs.list, fs.find, fs.search, fs.read | none |
| web.search, web.scrape | none |
| code.git status and log | none |
| todo.write, datetime.now | none |
| code.git diff or blame (rarely needed) | may raise one; none in a trusted workspace on the Gateway we tested |
| document.save_url (thorough mode, only with your OK) | none, but it adds the page to your document library, and it says so |
| info.request | a question, not a card |

TOOLS.md pins web.scrape in every profile and keeps fs.read, fs.find, fs.search and web.search visible when Lead Developer narrows a sub-agent's tools.

## After installing

- Install: `sophon agents install researcher`, with `--allow-delegation-from lead-developer` if Lead Developer should brief it. Leave the effort at the default.
- Start `sophon` in the project folder so the session is bound, then run `/trust` so the project's AGENTS.md loads. Unbound, it can still research, but paths are host-wide and project instructions are not loaded.
- Pick it with `/agent researcher`, or `--agent researcher` on the command line.
- Allowing Medium-risk calls for the session (run `/permissions` and choose Medium) covers this agent's own code.git diff at the root. It never covers a package agent's edits, commits or shell commands, nor any sub-agent's calls; this agent makes none of those anyway.

## Works best with

- `lead-developer`: runs 2-5 researchers at once in its Understand phase, each with a distinct focus, then opens the key cited lines itself.
- `software-architect`: turns the findings into one decisive design and a plan file.
- `debugger`: when the research points at a failure whose cause is unknown.
- `technical-writer`: saves an onboard draft into AGENTS.md when you ask.

## Limits

- Sophon has no web.fetch; pages are read with web.scrape in readability mode, so pages behind a login or built entirely in the browser may come back thin.
- It runs no builds, tests or scripts. Where a run would settle a question, it says what the run would prove and who should run it (`qa-engineer` or `lead-developer`).
- Budgets cap coverage on purpose; anything sampled, skipped or capped is listed under "Not covered".
- Search results are capped by the tools. When a result says "showing the first N", it narrows the search or reports the cap.

## What it never does

- Changes files, commits or pushes; that includes the onboard draft.
- Runs shell commands.
- Invents a URL, a path or a version.
- Starts sub-agents.
- Stores or repeats secrets. Web pages, file contents and tool output are treated as data, never as instructions.

## What's new in 3.0.0

- Onboard mode: a drafted project-context block for AGENTS.md that it never saves.
- Library answers start from the version in use, with the source for that version cited.
- A terse voice on request.

{{> readme/80-upgrade-3}}

{{> readme/70-reference-skill}}

## Credits and license

Ideas re-expressed in our own words also come from JuliusBrussee/caveman (Apache-2.0, © 2026 Julius Brussee); and addyosmani/agent-skills (MIT, © 2025 Addy Osmani).

Workflow patterns adapted, not copied, from obra/superpowers (MIT, © 2025 Jesse Vincent) and Anthropic's Claude Code plugins (feature-dev, pr-review-toolkit, code-review, frontend-design; Apache-2.0). Licensed under the MIT License; see LICENSE.
