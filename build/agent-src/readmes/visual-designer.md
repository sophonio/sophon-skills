# Visual Designer

Makes the imagery a product uses: visual concepts, SVG and HTML art, seeded generative pieces, generated images cut to web sizes, and motion specs.

Part of the Buildersoft development family {{= FamilyVersion}}.

{{# roster}}

## When to use

- Hero, poster or Open Graph art for a site or a launch.
- An illustration, a mark or an icon as SVG.
- A seeded generative background or artwork you can tune and reproduce.
- A generated image, resized and cropped to the sizes a site needs, and favicons.
- A motion spec for one orchestrated moment, with a reduced-motion fallback.

## Not for

- Interface layout and copy: use `ui-ux-designer`.
- Design tokens and themes: use `design-system-engineer`.
- Components and app code: use `frontend-developer`.

## How it works

- It starts by reading your project's visual sources: a DESIGN.md or brand file, CSS custom properties, the theme config and the assets already in the target folder. Their colours, fonts and motion values bind it.
- If the mode or the target size is missing, it asks one question with a proposed brief you can accept as it is.
- **Concept:** a named visual philosophy in a few lines (space and form, colour and material, scale and rhythm, composition), with a quiet reference to the subject rather than literal clip art.
- **Art:** a static SVG or HTML composition from a limited palette. Nothing overlaps, nothing touches the edge, margins are real, and one refinement round tightens what exists instead of adding more.
- **Generative:** one self-contained HTML file with a seeded generator, so the same seed always gives the same picture. Every parameter has a control, alongside seed navigation, Regenerate, Reset and Download PNG. It uses a library only if your project already has it or you approve a pinned build, inlined into the HTML file so it stays self-contained; it never loads scripts from a CDN.
- **Image:** opt-in. It writes an `image.generate` prompt from the concept and your palette, then uses `media.image` to resize, crop and strip metadata, writing only the final files into the asset folder, at target sizes such as Open Graph 1200×630 and favicons at 512, 192, 180 and 32 px.
- **Motion:** easing chosen by purpose (ease-out to enter, ease-in to leave), durations and stagger, transform and opacity only, delivered as a spec for CSS or your project's animation library, always with a `prefers-reduced-motion` fallback. It writes a standalone keyframes file only when asked; wiring motion into components or app styles is for `frontend-developer` (or `ui-ux-designer` for presentation CSS).
- The model cannot see its own previews, screenshots or generated images. After delivering it asks you what looks off: you are its eyes.
- Work bigger than a small change gets a plan file in `docs/plans/` that you approve, a `sophon/<slug>` branch and one verified commit per task, then a Push + PR / Keep local / Discard menu.

## Tools and cards you'll see

| Action | Card |
|---|---|
| Reading and searching files, `code.git` status and log, `canvas.render` previews, `browser.screenshot`, `web.scrape`, `media.image` reads (`info`), the todo list | none |
| Each `image.generate` call | one each |
| Each asset file it creates or edits with `fs.write` or `fs.edit`, and each `fs.move` rename | one per file |
| `media.image` outputs (resized, cropped, stripped files) | none: it asks first when a target already exists |
| Build or check runs (`os.execute`), chained into one command where possible | one each |
| A proposed brief, a library or font to add, an asset to replace | a question |
| Approving a plan | a question, or the plan card in plan mode |

## After installing

- **Effort:** the default is fine.
- **Allowed Medium-risk calls for the session** never cover this agent's edits, commits, shell commands or image generation, nor any call it makes as a sub-agent: as a Marketplace agent it always asks for those.
- **Bind and trust the folder.** Run `sophon` in the repository so the session is bound, then `/trust` the folder so its AGENTS.md or CLAUDE.md conventions load.
- **Image mode** needs an image provider configured in Settings > Tools (DALL-E, Fal, Stability, Imagen, Replicate or Together). It uses the provider you name, else DALL-E; if that one has no key it asks which to use, and stops and names the setting if none is configured.
- **Screenshots** of a page need a dev server you started yourself; it never starts one.
- Pick it with `/agent visual-designer` or `--agent visual-designer`.

## Works best with

- `ui-ux-designer`: sets the screen's direction; this agent makes the art that fills it.
- `design-system-engineer`: owns the tokens this agent's palettes draw from.
- `frontend-developer`: wires the assets and motion specs into components and app styles; `ui-ux-designer` takes presentation CSS.

## Limits

- Only images you attach reach the model; previews, screenshots and generated images are shown to you, not to it.
- As a sub-agent it delivers files only, takes no screenshots, renders no previews, and flags every file as unseen.
- It checks geometry from the file itself (coordinates against the viewBox); how a piece looks is your call.
- Canvas previews are not available in plan mode.
- `media.image` resizes by stretching, so it computes the crop to keep the source ratio; it cannot write `.ico` files.

## What it never does

- Claim a visual looks right, or describe an image it did not receive.
- Write assets outside the folder you allowed, or replace an existing asset without asking.
- Load scripts from a CDN, or add fonts or libraries without asking.
- Imitate a named artist's style, or use real people, logos or trademarks you did not supply.
- Start dev servers, or push without your choice in the Git menu.

## What's new in 2.0.0

- First release in the family: concept, art, generative, image and motion modes.
- A TOOLS.md file pins `canvas.render`, `image.generate`, `media.image`, `browser.screenshot`, `web.scrape` and `fs.move` in coding sessions, and `canvas.render`, `image.generate`, `media.image` and `web.scrape` in chat.
- Plan files, one commit per verified task and the Git menu, shared with the family's other writers.

## Credits and license

Ideas re-expressed in our own words also come from JuliusBrussee/caveman (Apache-2.0, © 2026 Julius Brussee); Dammyjay93/interface-design (MIT, © 2026 Damola Akinleye); emilkowalski/skills (MIT, © 2026 Emil Kowalski); web-design-engineer from ConardLi/garden-skills (MIT, © 2026); and Leonxlnx/taste-skill (MIT, © 2026 Leonxlnx).

Portions adapted from Anthropic's agent skills, anthropics/skills (Apache-2.0, © 2026 Anthropic, PBC), changed by Buildersoft LLC: rewritten for Sophon tools, with scripts and branding removed (canvas-design, algorithmic-art, slack-gif-creator, frontend-design).

Workflow patterns adapted, not copied, from obra/superpowers (MIT, © 2025 Jesse Vincent) and Anthropic's Claude Code plugins (feature-dev, pr-review-toolkit, code-review, security-review, frontend-design; Apache-2.0).

Licensed under the Apache-2.0 License; see LICENSE.
