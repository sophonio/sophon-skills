# Frontend Developer

Builds and changes UI code in your repository's own stack, test-first through the public UI, held to an accessibility quality floor.

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
| **frontend-developer** (this one) | UI implementer: component / direct / artifact / perf | no | yes | yes |
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

- A new or changed component, page or form in a web frontend.
- Client state, routing, data fetching, and their loading, empty and error states.
- Turning an approved design into working code that follows your design spec and tokens.
- A self-contained HTML prototype you can open or share as one file.
- Measuring and reducing bundle or route size, one change at a time.

## Not for

- Choosing the look or writing interface copy: use `ui-ux-designer`.
- Token systems and light or dark themes: use `design-system-engineer`.
- Imagery and generated art: use `visual-designer`.
- Backend or API code: use `developer`.
- Verification gates and unit or integration suites: use `qa-engineer`.
- Browser end-to-end specs: use `e2e-test-engineer`.
- WCAG audits or accessibility reviews: use `accessibility-reviewer`.

## How it works

- **First move:** it detects the stack (framework and its installed version, router, styling, component library, design tokens, test runner) and reads your design spec, such as `DESIGN.md` or the theme files, before changing anything.
- **Component** (the default): one failing test that drives the public UI, querying by role or label, run red first; then the minimal code to make it green. Each loading, empty, error and success state gets its own failing test the same way, then the relevant suite runs.
- **Direct:** wiring, config and styles no test can drive, proved by build, type check and lint runs.
- **Artifact:** one self-contained HTML prototype. When a framework is needed it scaffolds with your project's tool or the framework's official CLI, asks you first because that installs packages, builds, and inlines everything into one file. You see it as a canvas preview before any testing.
- **Perf:** measure, change one thing, measure again, with numbers only from build output or tools you already have installed.
- **Code rules:** explicit prop types, discriminated-union variant props, no nested ternaries in JSX, design tokens instead of hard-coded values, fetch errors shown to the user rather than swallowed, and a written justification for any HTML or script-injection sink such as `dangerouslySetInnerHTML` or `innerHTML`.
- It never guesses a library API: it reads the installed version and its types or official docs first.
- Work bigger than a small change gets a plan file in `docs/plans/` that you approve, a `sophon/<slug>` branch and one verified commit per task, then a Push + PR / Keep local / Discard menu.

## The quality floor

The same floor as `ui-ux-designer`:

- 360 px wide with no horizontal scroll.
- Touch targets of 44×44 px or more, never under 24×24.
- A visible focus style at 3:1 contrast or more, a logical focus order and no keyboard traps.
- Reduced motion honoured.
- Contrast of 4.5:1 for body text and 3:1 for large text and UI components.
- Native elements, landmarks, ordered headings, alt text and visible labels; errors tied to their fields; state never shown by colour alone.
- Lines under about 80 characters.

## Tools and cards you'll see

| Action | Card |
|---|---|
| Reading and searching files, `code.git` status and log, `canvas.render` previews, `browser.screenshot`, `web.scrape`, the todo list | none |
| Each file it creates or edits | one per file |
| Test, build, type check and lint runs (`os.execute`), chained into one command where possible | one each |
| Scaffolding an artifact project | a question first, then one command card |
| Each `browser.act` step on your running page (navigate, wait, evaluate, click, type) | one each |
| Approving a plan | a question, or the plan card in plan mode |

## After installing

- Pick it with `/agent frontend-developer` or `--agent frontend-developer`.
- **Effort:** the default is fine.
- **Allowed Medium-risk calls for the session** never cover this agent's edits, commits or shell commands, nor any call it makes as a sub-agent: as a Marketplace agent it always asks for those.
- **Bind and trust the folder.** Run `sophon` in the repository so the session is bound, then `/trust` the folder so its AGENTS.md or CLAUDE.md conventions load.
- **Browser checks** need Playwright Chromium on the Gateway host, and `browser.act` opens a localhost page only when `Sophon:Browser:AllowPrivateNetwork` is on. It never starts a dev server: start yours first.

## Works best with

- `lead-developer`: delegates UI tasks to it inside a plan.
- `ui-ux-designer`: sets the direction it builds to.
- `design-system-engineer`: owns the tokens and themes it uses.
- `qa-engineer` and `e2e-test-engineer`: run the gate and the browser end-to-end tests.

## Limits

- Screenshots and canvas previews are shown to you, not to the model; after taking one it asks you what looks off.
- As a sub-agent it receives no images at all, works from DOM and code, and says so.
- Performance numbers come only from build output or tools already installed; anything else is listed as a check for a person.
- Narrow viewports, zoom, keyboard walk-throughs and screen readers are listed as checks for a person unless the code proves them.

## What it never does

- Start dev servers or watchers.
- Add a dependency, font or asset without asking; as a sub-agent, only when the brief names it.
- Ship below the quality floor. If you ask it to, it states the cost and offers an alternative.
- Claim to have seen a screenshot or preview.
- Push without your choice in the Git menu.

## What's new in 2.0.0

- First release in the family, numbered 2.0.0 to match the family generation: component, direct, artifact and perf modes, the quality floor and the code rules.
- A TOOLS.md file pins `browser.act`, `browser.screenshot`, `canvas.render` and `web.scrape` in coding sessions, and `canvas.render` and `web.scrape` in chat.
- If your Lead Developer uses a delegation allow list, add `frontend-developer` to it.

## Credits and license

Ideas re-expressed in our own words also come from JuliusBrussee/caveman (Apache-2.0, © 2026 Julius Brussee); Dammyjay93/interface-design (MIT, © 2026 Damola Akinleye); emilkowalski/skills (MIT, © 2026 Emil Kowalski); web-design-engineer from ConardLi/garden-skills (MIT, © 2026); Leonxlnx/taste-skill (MIT, © 2026 Leonxlnx); and vercel-labs/web-interface-guidelines (MIT, © 2025 Vercel Labs).

Portions adapted from Anthropic's agent skills, anthropics/skills (Apache-2.0, © 2026 Anthropic, PBC), changed by Buildersoft LLC: rewritten for Sophon tools, with scripts and branding removed (frontend-design, web-artifacts-builder, webapp-testing).

Workflow patterns adapted, not copied, from obra/superpowers (MIT, © 2025 Jesse Vincent) and Anthropic's Claude Code plugins (feature-dev, pr-review-toolkit, code-review, security-review, frontend-design; Apache-2.0).

Licensed under the Apache-2.0 License; see LICENSE.
