# UI/UX Designer

Works out with you what an interface should be, offers directions you pick from, builds the presentation or reviews it to an accessibility quality floor, and writes the words people read in it.

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
| product-manager | discover / analyst / brief / PRD / prioritise / pre-mortem | no | its product documents only | no |
| product-owner | spec / slice / refine / validate / accept / replan / triage | no | its requirements and story files only | no |
| release-engineer | check / ship / deploy / watch / upgrade / rollback | no | version, changelog and dependency files | yes |
| agent-engineer | agent instructions: design / rule / test / review / diagnose | no | agent and skill instruction files | yes |

## When to use

- The direction and layout of a new screen, or of a redesign.
- A look grounded in what the product is and who uses it.
- One part of a screen made bolder, quieter, simpler or more polished.
- An interface that looks generic and should look deliberate.
- Interface accessibility: focus, contrast, target sizes, motion, labels.
- The presentation of screens that exist: styles on your tokens, and copy.
- A critique of a screen, a flow or a page you already have running.
- The wording of buttons, errors, empty states and onboarding.

## Not for

- Backend or business logic: use `developer`.
- New component markup, logic, state, data, routing and motion wiring: use `frontend-developer`.
- Tokens, themes and the token block of `DESIGN.md`: use `design-system-engineer`.
- Illustrations, generated art and images: use `visual-designer`.
- Who the users are and what to build: use `product-manager`.
- A full WCAG 2.2 AA audit: use `accessibility-reviewer`; functional tests: `qa-engineer`.

## How it works

- **First move:** it looks for your design system (`DESIGN.md`, CSS custom properties, a theme or Tailwind config, a component library), names the subject, the audience and the screen's job, and says whether the work extends, refines or redesigns. An existing system is extended, not replaced; a redesign happens only on your word.
- **Discover:** the product before the look. It reads `PRODUCT.md` and asks only what it leaves open: at most three related questions a round, each with its likely reading first, and never for colours, fonts, spacing or any CSS value. It may ask once for up to three reference screenshots or sites.
- **Direction:** four options in one anatomy, side by side in one canvas preview: a name, a one-sentence thesis, 4-6 colours with the contrast of each text pair, type roles, the first viewport as a wireframe, and an honest risk. Option 1 is the Sophon design default applied to your product, marked Recommended; options 2 and 3 come from two different schools or open systems; option 4 is the plain standard for the category. You pick one in a "Direction" question, or ask for safer or bolder alternatives. Nothing is built or saved before you pick. With a design system of your own, no round runs unless you ask for options.
- **DESIGN.md:** after your pick it drafts the prose of `DESIGN.md` and saves it only on your yes (Save, Change something or Stop), then offers the AGENTS.md line `- Design rules: DESIGN.md`, added only on a second yes.
- **Refine:** one verb (bolder, quieter, distill or polish) and one named target. Only that target changes; anything else is a proposal.
- **Build:** the presentation of screens that exist, on your tokens, with real content. It asks before adding fonts, libraries or assets, and proposes a `DESIGN.md` change before building something the file does not allow. Before showing a screen it runs five self-tests (swap, squint, signature, token, name) and reports a line for each.
- **Critique:** evidence best first: images you attach, the DOM of a page you run, then the code. Findings are ordered by impact; a departure from `DESIGN.md` is a finding. At Medium and above, or on request, it scores Nielsen's ten heuristics from 0 to 4 and re-scores until nothing is under 3 or two rounds bring no gain.
- **Copy:** every string as before and after, with one line on why.
- **Judge:** a recommendation between directions a lead gathered; you pick.
- Work bigger than a small change gets discovery when something is open, a plan file in `docs/plans/` that you approve, a `sophon/<slug>` branch and one verified commit per task, then the Git menu: Push + open PR, Merge into `<base>` locally, or Keep local. Discard runs only when you ask, after one more confirmation.
- The model cannot see its own screenshots or previews. After showing one it asks what looks off: you are its eyes.
- Say "terse" or "caveman" for short replies and "normal" to switch back.

## The quality floor

Everything it builds or reviews is held to this, in light and dark:

- 360 px wide with no horizontal scroll; lines under about 80 characters; targets of 44×44 px, never under 24×24.
- A visible focus style at 3:1 or more, a logical focus order and no keyboard traps; reduced motion honoured, and a pause for anything playing alone over 5 seconds.
- Contrast of 4.5:1 for body text and 3:1 for large text and UI parts; native elements, landmarks, ordered headings, alt text and visible labels; errors tied to their fields; state never shown by colour alone.

## Tools and cards you'll see

| Action | Card |
|---|---|
| Reading and searching files, `code.git` status and log, `canvas.render` previews, `browser.screenshot`, `web.scrape`, `calculator.evaluate`, the todo list | none |
| A direction round | none: a question |
| Each file it creates or edits, `DESIGN.md` included | one per file |
| Adding the AGENTS.md line you accepted | one |
| Build and lint runs (`os.execute`), chained into one command where possible | one each |
| Each `browser.act` step on your running page (navigate, wait, evaluate) | one each |
| Approving a plan | a question, or the plan card in plan mode |

## After installing

- Install: `sophon agents install ui-ux-designer --allow-delegation-from lead-developer` (drop the flag if you do not use Lead Developer). Pick it with `/agent ui-ux-designer`.
- **Effort:** the default is fine.
- **Allowed Medium-risk calls for the session** never cover this agent's edits, commits or shell commands, nor any call it makes as a sub-agent.
- **Bind and trust the folder:** run `sophon` in the repository, then `/trust` so its AGENTS.md or CLAUDE.md conventions load.
- **Browser checks** need Playwright Chromium on the Gateway host, and `browser.act` opens a localhost page only when `Sophon:Browser:AllowPrivateNetwork` is on. It never starts a dev server: start yours first.

## Works best with

- `lead-developer` runs its direction round and uses it as a critique lens and a judge; `design-system-engineer` turns the pick into tokens; `frontend-developer` builds the components and motion behind it; `visual-designer` makes its art.

## Limits

- Only images you attach reach the model; screenshots and canvas previews are shown to you, not to it. As a sub-agent it receives no images, returns the four directions as text and saves nothing.
- Canvas previews, browser checks and screenshots are refused in plan mode; the direction round then runs as text.
- Narrow viewports, zoom, keyboard walk-throughs and screen readers are listed as checks for a person unless the code proves them.

## What it never does

- Pick a direction for you, or build or save anything before you pick.
- Claim to have seen an image it did not receive.
- Ship below the quality floor. If you ask it to, it states the cost and offers an alternative.
- Use dark patterns, or present claims about your users as facts.
- Start dev servers, or push without your choice in the Git menu.

## What's new in 3.0.0

- discover and refine; the round of four directions; a scored critique; `DESIGN.md` after your pick. Tokens moved to `design-system-engineer`, new component markup to `frontend-developer`.

## Upgrading from 2.x

- 3.0.0 is a major version, so Sophon never applies it unattended. Take it yourself, one agent at a time: `sophon agents update <id>`.
- Update every family agent you have installed in one sitting. In between, Lead Developer 3.0.0 gives a companion below 3.0.0 the brief that 2.x understands and tells you once which agents to update, and a 3.0.0 companion still accepts a 2.x brief. An agent you created locally from these files reports no version and counts as current.
- Four agents are new: `product-owner`, `product-manager`, `release-engineer` and `agent-engineer`. Install the ones you want with `--allow-delegation-from lead-developer`. Updating never changes delegation settings, so an existing allow list needs them added.
- The instructions are longer. Each new session of this agent, and each sub-agent run of it, reads about 4,400 more tokens than in 2.x.
- 3.0.0 lists the optional `craft-reference` skill, which returns long reference material on request. Sophon offers to install it; if you decline, the agent works from what it carries.
- Your own edits to an installed agent pause its updates. Add `--discard-local-changes` to replace them.

## Reference skill

This agent can read longer tables, checklists and templates from the optional `craft-reference` skill, which Sophon offers when you install the agent. The skill does not run in plan mode or on a Gateway without the Docker sandbox, and the agent then works from the summary it carries. The skill's own notices credit the sources of its topics.

## Credits and license

Ideas re-expressed in our own words also come from JuliusBrussee/caveman (Apache-2.0, © 2026 Julius Brussee); pbakaus/impeccable (Apache-2.0, © 2025 Paul Bakaus); google-labs-code/design.md (Apache-2.0); Dammyjay93/interface-design (MIT, © 2026 Damola Akinleye); emilkowalski/skills (MIT, © 2026 Emil Kowalski); web-design-engineer from ConardLi/garden-skills (MIT, © 2026); Leonxlnx/taste-skill (MIT, © 2026 Leonxlnx); and the names of Jakob Nielsen's ten usability heuristics (cited by name only). Material, Carbon, Primer, Fluent and Radix are their owners' marks, named only to identify public design systems. This agent stays MIT.

Workflow patterns adapted, not copied, from obra/superpowers (MIT, © 2025 Jesse Vincent) and Anthropic's Claude Code plugins (feature-dev, pr-review-toolkit, code-review, frontend-design; Apache-2.0).

Licensed under the MIT License; see LICENSE.
