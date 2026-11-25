# Visual Designer

Makes the imagery a product uses: visual concepts, SVG and HTML art, seeded generative pieces, generated images cut to web sizes, and motion specs.

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
| **visual-designer** (this one) | concept / art / generative / image / motion | no | asset files | yes |
| e2e-test-engineer | browser end-to-end tests: write / visual / flake | no | e2e tests | yes |
| accessibility-reviewer | WCAG 2.2 AA: audit / review | no | no | no |
| mcp-integration-engineer | MCP servers: design / build / evals | no | yes | yes |
| technical-writer | documentation: draft / edit / reader-test | no | documentation files | yes |
| product-manager | discover / analyst / brief / PRD / prioritise / pre-mortem | no | its product documents only | no |
| product-owner | spec / slice / refine / validate / accept / replan / triage | no | its requirements and story files only | no |
| release-engineer | check / ship / deploy / watch / upgrade / rollback | no | version, changelog and dependency files | yes |
| agent-engineer | agent instructions: design / rule / test / review / diagnose | no | agent and skill instruction files | yes |

## When to use

- Hero, poster or Open Graph art for a site or a launch.
- An illustration, a mark or an icon as SVG.
- A seeded generative background or artwork you can tune and reproduce.
- A generated image, resized and cropped to the sizes a site needs, and favicons.
- A motion spec for one orchestrated moment, with a reduced-motion fallback.

## Not for

- Interface layout and copy: use `ui-ux-designer`.
- Design tokens and themes: use `design-system-engineer`.
- Components, app code and motion wiring: use `frontend-developer`.

## How it works

- It starts by reading your project's visual sources: a `DESIGN.md` or brand file, CSS custom properties, the theme config and the assets already in the target folder. Their colours, fonts and motion values bind it, and an accent means what your Colors section says.
- If the mode or the target size is missing, it asks one question with a proposed brief you can accept as it is. When nothing decides the look, it asks the family's "Design" question in the same call.
- **Concept:** a named visual philosophy in a few lines (space and form, colour and material, scale and rhythm, composition), with a quiet reference to the subject rather than literal clip art. The concept comes first and waits for your answer in a "Concept" question: Make this, Change something, or Another concept. No file is written before it, and no answer writes nothing.
- **Art:** a static SVG or HTML composition from a limited palette. Nothing overlaps, nothing touches the edge, margins are real, and one refinement round tightens what exists instead of adding more.
- **Generative:** one self-contained HTML file with a seeded generator, so the same seed always gives the same picture. Every parameter has a control, alongside seed navigation, Regenerate, Reset and Download PNG. It uses a library only if your project already has it or you approve a pinned build, inlined into the HTML file; it never loads scripts from a CDN.
- **Image:** opt-in. It writes an `image.generate` prompt from the concept and your palette, then uses `media.image` to resize, crop and strip metadata, writing only the final files into the asset folder, at target sizes such as Open Graph 1200×630 and favicons at 512, 192, 180 and 32 px.
- **Motion:** easing chosen by purpose (ease-out to enter, ease-in to leave), durations and stagger from your motion tokens where you have them, transform and opacity only, delivered as a spec for CSS or your project's animation library, always with a `prefers-reduced-motion` fallback. It writes a standalone keyframes file only when asked; wiring motion into components or app styles is always `frontend-developer`'s.
- Before it shows a new asset it runs five self-tests (swap, squint, signature, token, name) and reports a line for each.
- The model cannot see its own previews, screenshots or generated images. After delivering it asks you what looks off: you are its eyes.
- Work bigger than a small change gets discovery when something is open, a plan file in `docs/plans/` that you approve, a `sophon/<slug>` branch and one verified commit per task, then the Git menu: Push + open PR, Merge into `<base>` locally, or Keep local. Discard runs only when you ask, after one more confirmation.
- Say "terse" or "caveman" for short replies and "normal" to switch back.

## Tools and cards you'll see

| Action | Card |
|---|---|
| Reading and searching files, `code.git` status and log, `canvas.render` previews, `browser.screenshot`, `web.scrape`, `media.image` reads (`info`), the todo list | none |
| Each `image.generate` call | one each |
| Each asset file it creates or edits with `fs.write` or `fs.edit`, and each `fs.move` rename | one per file |
| `media.image` outputs (resized, cropped, stripped files) | none: it asks first when a target already exists |
| Build or check runs (`os.execute`), chained into one command where possible | one each |
| The concept, a proposed brief, a library or font to add, an asset to replace | a question |
| Approving a plan | a question, or the plan card in plan mode |

## After installing

- Install: `sophon agents install visual-designer --allow-delegation-from lead-developer` (drop the flag if you do not use Lead Developer). Pick it with `/agent visual-designer`.
- **Effort:** the default is fine.
- **Allowed Medium-risk calls for the session** never cover this agent's edits, commits, shell commands or image generation, nor any call it makes as a sub-agent.
- **Bind and trust the folder:** run `sophon` in the repository, then `/trust` so its AGENTS.md or CLAUDE.md conventions load.
- **Image mode** needs an image provider configured in Settings > Tools (DALL-E, Fal, Stability, Imagen, Replicate or Together). It uses the provider you name, else DALL-E; if that one has no key it asks which to use, and stops and names the setting if none is configured.
- **Screenshots** of a page need a dev server you started yourself; it never starts one.

## Works best with

- `ui-ux-designer`: sets the screen's direction; this agent makes the art that fills it.
- `design-system-engineer`: owns the tokens this agent's palettes draw from.
- `frontend-developer`: wires the assets and motion specs into components and app styles.

## Limits

- Only images you attach reach the model; previews, screenshots and generated images are shown to you, not to it.
- As a sub-agent it delivers files only, takes no screenshots, renders no previews, and flags every file as unseen.
- It checks geometry from the file itself (coordinates against the viewBox); how a piece looks is your call.
- Canvas previews are not available in plan mode.
- `media.image` resizes by stretching, so it computes the crop to keep the source ratio; it cannot write `.ico` files.

## What it never does

- Write a file before you answered the concept question.
- Claim a visual looks right, or describe an image it did not receive.
- Write assets outside the folder you allowed, or replace an existing asset without asking.
- Load scripts from a CDN, or add fonts or libraries without asking.
- Imitate a named artist's style, or use real people, logos or trademarks you did not supply; it never draws Sophon's logo or mark.
- Start dev servers, or push without your choice in the Git menu.

## What's new in 3.0.0

- The concept comes first and waits for your answer; motion wiring is `frontend-developer`'s alone; the five self-tests run before an asset is shown.

## Upgrading from 2.x

- 3.0.0 is a major version, so Sophon never applies it unattended. Take it yourself, one agent at a time: `sophon agents update <id>`.
- Update every family agent you have installed in one sitting. In between, Lead Developer 3.0.0 gives a companion below 3.0.0 the brief that 2.x understands and tells you once which agents to update, and a 3.0.0 companion still accepts a 2.x brief. An agent you created locally from these files reports no version and counts as current.
- Four agents are new: `product-owner`, `product-manager`, `release-engineer` and `agent-engineer`. Install the ones you want with `--allow-delegation-from lead-developer`. Updating never changes delegation settings, so an existing allow list needs them added.
- The instructions are longer. Each new session of this agent, and each sub-agent run of it, reads about 3,400 more tokens than in 2.x.
- 3.0.0 lists the optional `craft-reference` skill, which returns long reference material on request. Sophon offers to install it; if you decline, the agent works from what it carries.
- Your own edits to an installed agent pause its updates. Add `--discard-local-changes` to replace them.

## Reference skill

This agent can read longer tables, checklists and templates from the optional `craft-reference` skill, which Sophon offers when you install the agent. The skill does not run in plan mode or on a Gateway without the Docker sandbox, and the agent then works from the summary it carries. The skill's own notices credit the sources of its topics.

## Credits and license

Ideas re-expressed in our own words also come from JuliusBrussee/caveman (Apache-2.0, © 2026 Julius Brussee); Dammyjay93/interface-design (MIT, © 2026 Damola Akinleye); emilkowalski/skills (MIT, © 2026 Emil Kowalski); web-design-engineer from ConardLi/garden-skills (MIT, © 2026); and Leonxlnx/taste-skill (MIT, © 2026 Leonxlnx). Material, Carbon, Primer, Fluent and Radix are their owners' marks, named only to identify public design systems.

Portions adapted from Anthropic's agent skills, anthropics/skills (Apache-2.0, © 2026 Anthropic, PBC), changed by Buildersoft LLC: rewritten for Sophon tools, with scripts and branding removed (canvas-design, algorithmic-art, slack-gif-creator, frontend-design).

Workflow patterns adapted, not copied, from obra/superpowers (MIT, © 2025 Jesse Vincent) and Anthropic's Claude Code plugins (feature-dev, pr-review-toolkit, code-review, security-review, frontend-design; Apache-2.0).

Licensed under the Apache-2.0 License; see LICENSE.
