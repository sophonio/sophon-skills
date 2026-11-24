# Accessibility Reviewer

Read-only WCAG 2.2 AA review: each finding names the success criterion, the people it blocks, the line and the fix.

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
| **accessibility-reviewer** (this one) | WCAG 2.2 AA: audit / review | no | no | no |
| mcp-integration-engineer | MCP servers: design / build / evals | no | yes | yes |
| technical-writer | documentation: draft / edit / reader-test | no | documentation files | yes |
| product-manager | discover / analyst / brief / PRD / prioritise / pre-mortem | no | its product documents only | no |
| product-owner | spec / slice / refine / validate / accept / replan / triage | no | its requirements and story files only | no |
| release-engineer | check / ship / deploy / watch / upgrade / rollback | no | version, changelog and dependency files | yes |
| agent-engineer | agent instructions: design / rule / test / review / diagnose | no | agent and skill instruction files | yes |

## When to use

- Before a UI change is merged: review the diff for the accessibility failures it introduces.
- To audit a screen, a flow or a whole interface you already have running, or its code when nothing is running.
- When you need findings tied to WCAG 2.2 success criteria, with the level (A or AA) and who is blocked: keyboard users, screen-reader users, low-vision users, people with motor or cognitive disabilities.
- Inside a Lead Developer review panel, as the accessibility lens.

## Not for

- Fixing what it finds: use `frontend-developer`, or `ui-ux-designer` for presentation and copy.
- Visual design or taste critique: use `ui-ux-designer`.
- Design tokens and theme contrast at the system level: use `design-system-engineer`.
- Functional tests and end-to-end tests: use `qa-engineer` and `e2e-test-engineer`.
- Security review: use `security-reviewer`.

## How it works

- **Scope first.** It names what it checks (a screen, a flow, the whole UI, or a diff) and who the interface serves, then finds your stack: framework, component library, design tokens and any accessibility tooling you already run.
- **Audit mode.** On a page you already run, it reads the DOM through the browser: title and language, landmarks and headings, unnamed controls and images, unlabelled fields, tab order, removed focus styles, small targets, computed contrast and live regions, in the default state and up to two more (a menu open, a form submitted). Then it reads the code that renders the screen and traces every finding to the file and line that causes it.
- **Review mode.** Only the changed lines and the criteria they touch. Pre-existing failures are left out unless the change makes them reachable or worse. A component-library primitive that already provides the role, name or focus handling counts as a defence.
- **WCAG 2.2 AA checklist.** Criteria from 1.1.1 Non-text Content through 4.1.3 Status Messages, including the 2.2 additions: 2.4.11 Focus Not Obscured, 2.5.7 Dragging Movements, 2.5.8 Target Size (Minimum), 3.2.6 Consistent Help, 3.3.7 Redundant Entry and 3.3.8 Accessible Authentication. 4.1.1 Parsing, obsolete in 2.2, is never cited. AAA criteria only when you ask.
- **Severity by who is blocked.** Critical: a group of users cannot finish a core task. Important: an AA failure on a core path, or one repeated across shared components. Minor: off the core path or with an easy workaround.
- **Confidence 0 to 100.** Only findings at 80 or above are reported; weaker ones are listed under POSSIBLE.
- **Verdict.** `CONFORMS` or `GAPS` (GAPS when any Critical or Important finding remains), plus `SPEC: n/a`. CONFORMS covers what was checked; it is not a WCAG conformance claim.

## Tools and cards you'll see

| Call | When | Approval card |
|---|---|---|
| fs.read, fs.find, fs.search; code.git status and log | always | none |
| browser.act (navigate, wait, evaluate, click, type) | audit of a running page; at most 8 calls | one each (Medium) |
| browser.screenshot, web.scrape | a screenshot for you to look at; reading public docs | none |
| code.git diff | working-tree review | one |
| os.execute with read-only git | branch or commit-range review, at the root only | one per command; Critical risk, so it always asks |
| info.request | scope unclear | a question, not a card |

- TOOLS.md pins browser.act, browser.screenshot and web.scrape in coding sessions, and fs.read, fs.find and fs.search for the sub-agent profile.

## After installing

- Pick it with `/agent accessibility-reviewer` or `--agent accessibility-reviewer`.
- **Effort:** high works best: `sophon agents models accessibility-reviewer --effort high`.
- **Bind and trust the repository:** run `sophon` in the project folder, then `/trust`, so AGENTS.md and your project rules load.
- **Browser checks** need Playwright Chromium on the Gateway host, and `browser.act` opens a localhost page only when `Sophon:Browser:AllowPrivateNetwork` is on. It never starts a dev server: start yours first. Without one it audits the code and says so.
- **Allowed Medium-risk calls for the session** (set with `/permissions`) cover only the root agent's own Medium calls that change nothing, such as browser.act and code.git diff. They never cover its os.execute calls, and never any sub-agent's calls.
- **With Lead Developer:** install with `sophon agents install accessibility-reviewer --allow-delegation-from lead-developer` and keep the id `accessibility-reviewer`; the lead finds it through the `Family role: accessibility-reviewer.` marker.

## Works best with

- `frontend-developer`: fixes confirmed findings in components and markup.
- `ui-ux-designer`: fixes presentation and copy findings, and owns the design quality floor.
- `design-system-engineer`: fixes contrast and focus at the token level.
- `e2e-test-engineer` and `qa-engineer`: turn fixed findings into regression checks.
- `lead-developer`: adds it as the accessibility lens in a review panel.

## Limits

- It cannot hear a screen reader, zoom the page or press keys through a full walk-through. Those, plus captions quality and contrast over images, are listed under "Checks left for a person" unless the code proves them.
- Screenshots reach you, not the model. As a sub-agent it receives no images and works from DOM and code.
- The browser's snapshot is not an accessibility tree; DOM findings come from one scripted evaluation per state.
- Contrast over images or gradients is reported as unknown.
- Findings below the confidence threshold are listed, not argued.

## What it never does

- Edit, write, move or delete files; commit, push or switch branches.
- Run commands other than read-only git at the root, and none as a sub-agent.
- Start dev servers or sub-agents.
- Claim WCAG conformance, or claim to have seen a screenshot.
- Recommend overlay widgets or ARIA layered on the wrong element instead of native elements.
- Follow instructions found in the code, pages or diff it reviews.

## What's new in 2.0.0

- First release in the family, numbered 2.0.0 to match the family generation.
- Audit and review modes over WCAG 2.2 AA, with criterion, level and impact on every finding.
- Ships a TOOLS.md that pins browser tools for coding sessions and read tools for the sub-agent profile.

## Credits and license

Ideas re-expressed in our own words also come from JuliusBrussee/caveman (Apache-2.0, © 2026 Julius Brussee).

Workflow patterns adapted, not copied, from obra/superpowers (MIT, © 2025 Jesse Vincent) and Anthropic's Claude Code plugins (feature-dev, pr-review-toolkit, code-review, security-review, frontend-design; Apache-2.0).

Licensed under the Apache-2.0 License; see LICENSE.
