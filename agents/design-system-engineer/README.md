# Design System Engineer

Turns a chosen visual direction into design tokens and themes, defined once with light and dark values, and keeps the codebase consistent with them.

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
| **design-system-engineer** (this one) | audit / tokens / theme / playground / brand-check | no | tokens, themes, components | yes |
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

- Defining design tokens for the first time, or migrating hard-coded values to CSS custom properties or a Tailwind theme.
- Adding a dark mode that stays in step with the light one.
- Finding token drift: hard-coded colours, radii, spacing, font sizes or shadows that bypass the system.
- Checking contrast with computed WCAG ratios instead of guesses.
- Turning an approved direction (from `ui-ux-designer`, your spec or your colours) into a theme, or swapping the palette and type of an existing layout from three named options.
- Building a single-file HTML playground to tune a component's look and hand a developer a ready prompt.
- Checking the code against your repository's own brand spec, such as a DESIGN.md.

## Not for

- Choosing a product's design direction or a screen's layout: use `ui-ux-designer`.
- Component logic, state, data fetching and routing: use `frontend-developer`.
- Imagery, illustrations and generated art: use `visual-designer`.
- Full WCAG audits beyond contrast: use `accessibility-reviewer`.
- Backend code: use `developer`.

## How it works

- It starts by finding your existing system: CSS custom properties, the Tailwind theme, theme files, the component library and any brand spec. It reads the spec before changing anything, and extends an existing system instead of replacing it.
- **Audit** (read-only): searches styles, markup and components for colour literals outside the token file, values off the scale, unused or undefined tokens and missing dark values. Each hit comes with its file and line and the nearest token. With a page you already run, it can read the computed colours through the browser.
- **Tokens:** one source of truth, semantic names mapped to a raw scale, dark values in the same file, one scale per kind (spacing, radius per hierarchy level, type, shadows, motion). Migrations replace exact matches only; a value with no matching token is a question for you, never a silent rounding.
- **Theme:** given a direction, it encodes that. With none, for a palette and type swap on an existing layout, it drafts three named options, each with 4-6 colours, heading and body faces and a line on fit, shown together as swatches in a canvas preview. You choose one; nothing is applied before that. It then applies the theme as tokens with web fonts and checks every text pair in light and dark.
- **Playground:** one self-contained HTML file with grouped controls, 3-5 named presets, light and dark previews and a generated prompt written as a direction to a developer, with a Copy button.
- **Brand check:** enforces your spec, never one it brings: accent meanings, font roles and fallbacks, banned patterns and the contrast of every brand pair.
- Contrast ratios are computed with the WCAG formula, to two decimals.
- Work bigger than a small change gets a plan file in `docs/plans/` that you approve, a `sophon/<slug>` branch and one verified commit per task, then a Push + PR / Keep local / Discard menu.
- The model cannot see its own previews or screenshots. After showing one it asks you what looks off.

## Tools and cards you'll see

| Action | Card |
|---|---|
| Reading and searching files, `code.git` status and log, `canvas.render` previews, `browser.screenshot`, `web.scrape`, `calculator.evaluate`, the todo list | none |
| Each file it creates, edits or renames (`fs.move`) | one per file |
| Build runs (`os.execute`), chained into one command where possible | one each |
| Each `browser.act` step on your running page (navigate, wait, evaluate) | one each |
| Choosing a theme or approving a plan | a question, or the plan card in plan mode |

## After installing

- **Effort:** the default is fine.
- **Allowed Medium-risk calls for the session** never cover this agent's edits, commits or shell commands, nor any call it makes as a sub-agent: as a Marketplace agent it always asks for those.
- **Bind and trust the folder.** Run `sophon` in the repository so the session is bound, then `/trust` the folder so its AGENTS.md or CLAUDE.md conventions load.
- **Browser checks** need Playwright Chromium on the Gateway host, and `browser.act` opens a localhost page only when `Sophon:Browser:AllowPrivateNetwork` is on. It never starts a dev server: start yours first.
- Pick it with `/agent design-system-engineer` or `--agent design-system-engineer`.

## Works best with

- `ui-ux-designer`: decides the direction that this agent encodes as tokens.
- `frontend-developer`: builds the component logic on top of the tokens.
- `accessibility-reviewer`: audits everything beyond contrast.
- `lead-developer`: can hand it token and theme tasks inside a larger plan.

## Limits

- Swatches, playground previews and screenshots are shown to you, not to the model.
- As a sub-agent it receives no images, renders no previews and returns theme options as text.
- Canvas previews are not available in plan mode.
- Contrast over images or gradients is reported as unknown.

## What it never does

- Apply a direction you have not chosen: palette, type and mood come from the brief, your spec or your choice.
- Set a new product's direction, mood or layout: that is `ui-ux-designer`'s job.
- Invent brand values or reuse another company's palette or typefaces.
- Round a value to a nearby token without asking.
- Start dev servers, or push without your choice in the Git menu.

## What's new in 2.0.0

- First release in the family: audit, tokens, theme, playground and brand-check modes, computed contrast and a quality floor for light and dark.
- A TOOLS.md file pins `canvas.render`, `browser.act`, `browser.screenshot`, `web.scrape`, `fs.move` and `calculator.evaluate` in coding sessions, `calculator.evaluate` as a coding sub-agent, and `canvas.render` and `web.scrape` in chat.
- Plan files, one commit per verified task and the Git menu, shared with the family's other writers.

## Credits and license

Ideas re-expressed in our own words also come from JuliusBrussee/caveman (Apache-2.0, © 2026 Julius Brussee); google-labs-code/design.md (Apache-2.0); Dammyjay93/interface-design (MIT, © 2026 Damola Akinleye); emilkowalski/skills (MIT, © 2026 Emil Kowalski); web-design-engineer from ConardLi/garden-skills (MIT, © 2026); and Leonxlnx/taste-skill (MIT, © 2026 Leonxlnx).

Portions adapted from Anthropic's agent skills, anthropics/skills (Apache-2.0, © 2026 Anthropic, PBC), changed by Buildersoft LLC: rewritten for Sophon tools, with scripts and branding removed (theme-factory, brand-guidelines, frontend-design). The playground mode adapts the design-playground template of the playground plugin in anthropics/claude-plugins-official (Apache-2.0), changed by Buildersoft LLC in the same way.

Workflow patterns adapted, not copied, from obra/superpowers (MIT, © 2025 Jesse Vincent) and Anthropic's Claude Code plugins (feature-dev, pr-review-toolkit, code-review, security-review, frontend-design; Apache-2.0).

Licensed under the Apache-2.0 License; see LICENSE.
