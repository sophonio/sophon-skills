# UI/UX Designer

Gives an interface a deliberate direction, builds it to an accessibility quality floor, critiques screens and writes the words people read in them.

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
| **ui-ux-designer** (this one) | direction / build / critique / copy / judge | no | UI presentation files | yes |
| frontend-developer | UI implementer: component / direct / artifact / perf | no | yes | yes |
| design-system-engineer | audit / tokens / theme / playground / brand-check | no | tokens, themes, components | yes |
| visual-designer | concept / art / generative / image / motion | no | asset files | yes |
| e2e-test-engineer | browser end-to-end tests: write / visual / flake | no | e2e tests | yes |
| accessibility-reviewer | WCAG 2.2 AA: audit / review | no | no | no |
| mcp-integration-engineer | MCP servers: design / build / evals | no | yes | yes |
| technical-writer | documentation: draft / edit / reader-test | no | documentation files | yes |
## When to use

- A new screen or a redesign.
- A design direction or palette grounded in what the product is and who uses it.
- An interface that looks generic and should look deliberate.
- Interface accessibility: focus, contrast, target sizes, motion, labels.
- A critique of a screen, a flow or a page you already have running.
- The wording of buttons, errors, empty states and onboarding.

## Not for

- Backend or business logic: use `developer`.
- Functional test runs: use `qa-engineer`.
- System architecture: use `software-architect`.
- Component logic, state, data and routing: use `frontend-developer`.
- A token system or theme across the codebase: use `design-system-engineer`.
- Illustrations, generated art and images: use `visual-designer`.
- A full WCAG 2.2 AA audit: use `accessibility-reviewer`.

## How it works

- It starts by naming the subject, the audience and the screen's job, and looks for your existing design system: CSS custom properties, a theme or Tailwind config, a component library. An existing system is extended, not replaced.
- If the request lacks grounding, it asks one question with a proposed brief you can accept as it is.
- **Direction:** a plan of at most 25 lines with named colours and their roles, type roles, a layout sentence, an ASCII wireframe, three principles, one bold move and computed contrast ratios. It then checks the plan against the looks AI-generated designs default to, and revises any part that matches one.
- You see the direction as a canvas preview and choose to build it, change it or see another before anything is built.
- **Build:** it works in your repository's stack, defines design tokens once, uses real content, and asks before adding fonts, libraries or assets. Work bigger than a small change gets a plan file in `docs/plans/` that you approve, a `sophon/<slug>` branch and one verified commit per task, then a Push + PR / Keep local / Discard menu.
- **Critique:** it uses the best evidence available, in this order: images you attach, the page's DOM through the browser, then the code. Findings are ordered by their impact.
- **Copy:** every string as before and after, with one line on why.
- The model cannot see its own screenshots or previews. After taking one it asks you what looks off: you are its eyes.

## The quality floor

Everything it builds or reviews is held to this:

- 360 px wide with no horizontal scroll.
- Touch targets of 44×44 px or more, never under 24×24.
- A visible focus style at 3:1 contrast or more, a logical focus order and no keyboard traps.
- Reduced motion honoured.
- Contrast of 4.5:1 for body text and 3:1 for large text and UI components.
- Native elements, landmarks, ordered headings, alt text and visible labels.
- Errors tied to their fields, and state never shown by colour alone.
- Lines under about 80 characters.

## Tools and cards you'll see

| Action | Card |
|---|---|
| Reading and searching files, `code.git` status and log, `canvas.render` previews, `browser.screenshot`, `web.scrape`, the todo list | none |
| Each file it creates or edits | one per file |
| Build and lint runs (`os.execute`), chained into one command where possible | one each |
| Each `browser.act` step on your running page (navigate, wait, evaluate) | one each |
| Approving a direction or a plan | a question, or the plan card in plan mode |

## After installing

- **Effort:** the default is fine.
- **Allowed Medium-risk calls for the session** never cover this agent's edits, commits or shell commands, nor any call it makes as a sub-agent: as a Marketplace agent it always asks for those.
- **Bind and trust the folder.** Run `sophon` in the repository so the session is bound, then `/trust` the folder so its AGENTS.md or CLAUDE.md conventions load.
- **Browser checks** need Playwright Chromium on the Gateway host, and `browser.act` opens a localhost page only when `Sophon:Browser:AllowPrivateNetwork` is on. It never starts a dev server: start yours first.
- Pick it with `/agent ui-ux-designer` or `--agent ui-ux-designer`.

## Works best with

- `lead-developer`: uses it as the UI critique lens in reviews and as a judge between design directions.
- `frontend-developer`: builds the components, state and data behind an approved direction.
- `design-system-engineer`: turns a chosen palette and type roles into tokens and themes.
- `visual-designer`: makes the illustrations, Open Graph images and art a direction calls for.
- `qa-engineer` and `e2e-test-engineer`: run the functional, end-to-end and visual tests.

## Limits

- Only images you attach reach the model; screenshots and canvas previews are shown to you, not to it.
- As a sub-agent it receives no images at all, works from DOM and code, and says so.
- Narrow viewports, zoom, keyboard walk-throughs and screen readers are listed as checks for a person unless the code proves them.
- Canvas previews are not available in plan mode.

## What it never does

- Claim to have seen an image it did not receive.
- Ship below the quality floor. If you ask it to, it states the cost and offers an alternative.
- Use dark patterns.
- Present claims about your users as facts; they are labelled assumptions.
- Start dev servers, or push without your choice in the Git menu.

## What's new in 2.1.0

- Seven companions joined the family: `frontend-developer`, `design-system-engineer`, `visual-designer`, `e2e-test-engineer`, `accessibility-reviewer`, `mcp-integration-engineer` and `technical-writer`. They are licensed Apache-2.0; this agent stays MIT. Add the ones you install to an existing Lead Developer allow-list.
- `build` now covers the presentation layer only: component logic and state go to `frontend-developer`, token systems to `design-system-engineer`, imagery and generated art to `visual-designer`.

## What's new in 2.0.0

- A full rewrite: direction, build, critique, copy and judge modes, the quality floor and the check against default AI looks.
- A TOOLS.md file pins `canvas.render`, `browser.screenshot`, `browser.act` and `web.scrape` in coding sessions, and `canvas.render` and `web.scrape` in chat.
- Plan files, one commit per verified task and the Git menu, shared with the family's other writers.
- The manifest no longer carries heartbeat defaults.
- Updating does not change delegation settings.
- New companions `code-reviewer`, `debugger` and `security-reviewer`: add them to an existing Lead Developer allow-list.

## Credits and license

Workflow patterns adapted, not copied, from obra/superpowers (MIT, © 2025 Jesse Vincent) and Anthropic's Claude Code plugins (feature-dev, pr-review-toolkit, code-review, security-review, frontend-design; Apache-2.0).

Licensed under the MIT License; see LICENSE.
