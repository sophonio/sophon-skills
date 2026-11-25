# Frontend Developer

Builds and changes UI code in your repository's own stack, test-first through the public UI, held to an accessibility quality floor.

Part of the Buildersoft development family {{= FamilyVersion}}.

{{# roster}}

## When to use

- A new or changed component, page or form in a web frontend: all new component markup is its job.
- Client state, routing, data fetching, and their loading, empty and error states.
- Turning a chosen design into working code that follows your `DESIGN.md` and tokens.
- Wiring motion into components and app styles, including `visual-designer`'s motion specs.
- Three to five variants of a screen on named axes, to compare before you choose.
- A self-contained HTML prototype you can open or share as one file.
- Measuring and reducing bundle or route size, one change at a time.

## Not for

- Choosing the look or writing interface copy: use `ui-ux-designer`.
- Token systems, light or dark themes and creating `DESIGN.md`: use `design-system-engineer`.
- Imagery, generated art and motion specs: use `visual-designer`.
- Backend or API code: use `developer`.
- Verification gates and unit or integration suites: use `qa-engineer`; browser end-to-end specs: `e2e-test-engineer`.
- WCAG audits: use `accessibility-reviewer`.

## How it works

- **First move:** it detects the stack (framework and version, router, styling, component library, tokens, test runner) and settles the look first. `DESIGN.md` binds it, mapped to the code tokens. With no design system at all, it asks once, header "Design": Sophon design default (Recommended), Plain standard, or a direction round with `ui-ux-designer`, and applies no look before you answer.
- **Use what exists:** each part comes from the first that fits: your own component, a native element, a headless primitive you already install, then its own build with the whole contract (roles, names, keyboard, focus, every state). A missing token is a question for `design-system-engineer`, never a literal.
- **Component** (the default): one failing test that drives the public UI, querying by role or label, run red first; then the minimal code to make it green. Each loading, empty, error and success state gets its own failing test the same way.
- **Direct:** wiring, config and styles no test can drive, proved by build, type check and lint runs.
- **Variant:** 3 variants (5 at most), each on a named axis (layout, density, hierarchy or interaction model), behind one switcher. You choose; the variant file is then deleted and the choice built.
- **Artifact:** one self-contained HTML prototype; a framework scaffold is asked first, because it installs packages. You see it as a canvas preview first.
- **Perf:** measure, change one thing, measure again, with numbers only from build output or tools you already have installed.
- **States and breakage:** at Medium and above, or on request, it lists every state before coding and runs a break check afterwards (a long word; 0, 1 and 1,000 items; a missing image; a slow and a failed request; 360 px; 200% text).
- **Motion and interaction floor:** a control used many times a day does not animate; other motion is ease-out under 300 ms on transform and opacity, from your motion tokens, with a reduced-motion path. Shareable state lives in the URL, paste is never blocked, focus returns to the trigger.
- **Code rules:** explicit prop types, discriminated-union variant props, no nested ternaries in JSX, tokens instead of literals, fetch errors shown to the user, and a written justification for any script-injection sink. It reads the installed version of a library and its types or docs before using its API.
- Work bigger than a small change gets discovery when something is open, a plan file in `docs/plans/` that you approve, a `sophon/<slug>` branch and one verified commit per task, then the Git menu: Push + open PR, Merge into `<base>` locally, or Keep local. Discard runs only when you ask, after one more confirmation.
- Say "terse" or "caveman" for short replies and "normal" to switch back.

## The quality floor

The same floor as `ui-ux-designer`, in light and dark:

- 360 px wide with no horizontal scroll; lines under about 80 characters; targets of 44×44 px, never under 24×24.
- A visible focus style at 3:1 or more, a logical focus order and no keyboard traps; reduced motion honoured, and a pause for anything playing alone over 5 seconds.
- Contrast of 4.5:1 for body text and 3:1 for large text and UI parts; native elements, landmarks, ordered headings, alt text and visible labels; errors tied to their fields; state never shown by colour alone.

## Tools and cards you'll see

| Action | Card |
|---|---|
| Reading and searching files, `code.git` status and log, `canvas.render` previews, `browser.screenshot`, `web.scrape`, the todo list | none |
| Each file it creates or edits | one per file |
| Test, build, type check and lint runs (`os.execute`), chained into one command where possible | one each |
| Scaffolding an artifact project | a question first, then one command card |
| Each `browser.act` step on your running page (navigate, wait, evaluate, click, type) | one each |
| Choosing a look or a variant, approving a plan | a question, or the plan card in plan mode |

## After installing

- Install: `sophon agents install frontend-developer --allow-delegation-from lead-developer` (drop the flag if you do not use Lead Developer). Pick it with `/agent frontend-developer`.
- **Effort:** the default is fine.
- **Allowed Medium-risk calls for the session** never cover this agent's edits, commits or shell commands, nor any call it makes as a sub-agent.
- **Bind and trust the folder:** run `sophon` in the repository, then `/trust` so its AGENTS.md or CLAUDE.md conventions load.
- **Browser checks** need Playwright Chromium on the Gateway host, and `browser.act` opens a localhost page only when `Sophon:Browser:AllowPrivateNetwork` is on. It never starts a dev server: start yours first.

## Works best with

- `lead-developer` delegates UI tasks to it; `ui-ux-designer` sets the direction it builds to; `design-system-engineer` owns its tokens; `qa-engineer` and `e2e-test-engineer` run the gate and the end-to-end tests.

## Limits

- Screenshots and canvas previews are shown to you, not to the model; after taking one it asks you what looks off. As a sub-agent it receives no images and works from DOM and code.
- Delegated with no design source and no project system, it builds nothing and returns the look options for you to choose.
- Performance numbers come only from build output or tools already installed.
- Narrow viewports, zoom, keyboard walk-throughs and screen readers are listed as checks for a person unless the code proves them.
- Canvas previews and browser checks are refused in plan mode.

## What it never does

- Start dev servers or watchers.
- Apply a look you have not chosen, or write `DESIGN.md`.
- Add a dependency, font or asset without asking; as a sub-agent, only when the brief names it.
- Ship below the quality floor. If you ask it to, it states the cost and offers an alternative.
- Claim to have seen a screenshot or preview, or push without your choice in the Git menu.

## What's new in 3.0.0

- variant mode, the use-what-exists order, states and breakage, the motion and interaction floor, `DESIGN.md`, and the "Design" question.

## Credits and license

Ideas re-expressed in our own words also come from JuliusBrussee/caveman (Apache-2.0, © 2026 Julius Brussee); Dammyjay93/interface-design (MIT, © 2026 Damola Akinleye); emilkowalski/skills (MIT, © 2026 Emil Kowalski); web-design-engineer from ConardLi/garden-skills (MIT, © 2026); Leonxlnx/taste-skill (MIT, © 2026 Leonxlnx); and vercel-labs/web-interface-guidelines (MIT, © 2025 Vercel Labs). Material, Carbon, Primer, Fluent and Radix are their owners' marks, named only to identify public design systems.

Portions adapted from Anthropic's agent skills, anthropics/skills (Apache-2.0, © 2026 Anthropic, PBC), changed by Buildersoft LLC: rewritten for Sophon tools, with scripts and branding removed (frontend-design, web-artifacts-builder, webapp-testing).

Workflow patterns adapted, not copied, from obra/superpowers (MIT, © 2025 Jesse Vincent) and Anthropic's Claude Code plugins (feature-dev, pr-review-toolkit, code-review, security-review, frontend-design; Apache-2.0).

Licensed under the Apache-2.0 License; see LICENSE.
