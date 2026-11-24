# E2E Test Engineer

Writes browser end-to-end and visual tests in your repository's own runner, proves each one red then green, and makes flaky tests deterministic.

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
| **e2e-test-engineer** (this one) | browser end-to-end tests: write / visual / flake | no | e2e tests | yes |
| accessibility-reviewer | WCAG 2.2 AA: audit / review | no | no | no |
| mcp-integration-engineer | MCP servers: design / build / evals | no | yes | yes |
| technical-writer | documentation: draft / edit / reader-test | no | documentation files | yes |
| product-manager | discover / analyst / brief / PRD / prioritise / pre-mortem | no | its product documents only | no |
| product-owner | spec / slice / refine / validate / accept / replan / triage | no | its requirements and story files only | no |
| release-engineer | check / ship / deploy / watch / upgrade / rollback | no | version, changelog and dependency files | yes |
| agent-engineer | agent instructions: design / rule / test / review / diagnose | no | agent and skill instruction files | yes |

## When to use

- End-to-end tests for a user flow: sign-in, checkout, a form, a multi-page journey.
- Screenshot or visual regression tests for pages and components.
- A failed visual comparison you want reviewed before any baseline changes.
- A flaky end-to-end test that passes locally and fails in CI, or fails only in a full run.

## Not for

- Unit and integration tests, or the verification gate before a merge: use `qa-engineer`.
- Root-causing a product bug a test exposed: use `debugger`.
- Changing product code: use `developer` or `frontend-developer`.
- Accessibility audits: use `accessibility-reviewer`.
- Judging visual design: use `ui-ux-designer`.

## How it works

- It finds your e2e runner and command first: project instructions, package scripts such as `test:e2e`, the runner config, then CI. Your configured command always wins. It reads two neighbouring specs and copies their fixtures, helpers and naming.
- **The app.** It never starts a server, because Sophon's shell cannot run background processes. It tests the app you already run, or lets the runner's own `webServer` setting start and stop the server inside one test command, after you confirm that. Using your running app alongside a `webServer` block needs `reuseExistingServer` on and a matching base URL; otherwise it tells you the runner will start its own server.
- **Recon before acting.** It opens the page, waits for the main content, then lists buttons, links, inputs and headings with their roles, names and test ids, so selectors come from the rendered page. For static HTML it reads the file.
- **Write.** Selectors by role and name first, then label or text, then test id, then CSS. One behaviour per test, each test independent. Waits are web-first assertions or conditions, never fixed sleeps. Every new test is run red first and must fail for the right reason, then green.
- **Visual.** Screenshot assertions on stable state: fonts loaded, animations off, dynamic regions masked. When a comparison fails it quotes the difference and lists the expected, actual and diff images for you to open, then asks whether to keep or update the baseline. It updates only the tests you approved. A new baseline's first run fails while it is written, so it runs again until the comparison succeeds three times. Baseline names carry the operating system, so a baseline made on your machine does not cover CI on another OS; it says so and never commits one as the CI baseline without asking.
- **Flake.** It reproduces with repeat runs, classifies the failure (timing, shared state or environment), replaces sleeps with condition waits, and, when the test fails only in a full run, finds the polluter by halving the list of earlier spec files, repeating each half so one lucky run cannot clear it. When no single file is to blame it reports the smallest failing set. The fix is proven with the same repeat run.
- Work bigger than a small change gets a plan file in `docs/plans/` that you approve, a `sophon/<slug>` branch and one verified commit per task, then a Push + PR / Keep local / Discard menu.

## Tools and cards you'll see

| Action | Card |
|---|---|
| Reading and searching files, `code.git` status and log, `browser.screenshot`, `web.scrape`, the todo list | none |
| Each test file it creates or edits | one per file |
| Each test run (`os.execute`), including every repeat and bisection run | one each |
| Each `browser.act` step on your running page (navigate, wait, evaluate) | one each |
| Letting the runner start your server, or updating a visual baseline | a question first |

## After installing

- **Effort:** the default is fine.
- **Allowed Medium-risk calls for the session** never cover this agent's edits, commits or shell commands, nor any call it makes as a sub-agent: as a Marketplace agent it always asks for those.
- **Bind and trust the folder.** Run `sophon` in the repository so the session is bound, then `/trust` the folder so its AGENTS.md or CLAUDE.md conventions load.
- **Browser recon** needs Playwright Chromium on the Gateway host, and `browser.act` opens a localhost page only when `Sophon:Browser:AllowPrivateNetwork` is on. Start your app first.
- **Your runner** needs its browsers installed in the project; it asks before adding Playwright or downloading browsers.
- Pick it with `/agent e2e-test-engineer` or `--agent e2e-test-engineer`.

## Works best with

- `qa-engineer`: owns the verification gate and the unit and integration suites; this agent owns the browser layer.
- `debugger`: takes a product bug an end-to-end test exposed and finds its cause.
- `frontend-developer`: builds the UI these tests drive, and adds a test id when one is needed.
- `lead-developer`: can hand it the end-to-end part of a larger plan.

## Limits

- The model cannot see screenshots or diff images; you open them and decide.
- As a sub-agent it cannot ask you, so it never updates a baseline there; it lists the decision for you.
- Without a running app or a confirmed `webServer` setting it cannot run end-to-end tests at all.
- Each repeat or bisection run is its own card, so a flake hunt asks for several approvals.

## What it never does

- Start dev servers or anything else in the background.
- Update a visual baseline you have not approved, or update the whole suite at once.
- Make a test pass by weakening it: no added retries, longer timeouts or skips unless you ask.
- Fix product code; a product bug is reported with the failing test.
- Write test-user secrets into tests; it names the environment variable instead.
- Push without your choice in the Git menu.

## What's new in 2.0.0

- First release in the family: write, visual and flake modes, recon before acting, red-then-green proof for every test, and baseline updates only with your approval.
- A TOOLS.md file pins `browser.act`, `browser.screenshot` and `web.scrape` in coding sessions, and `web.scrape` in chat.

## Credits and license

Ideas re-expressed in our own words also come from JuliusBrussee/caveman (Apache-2.0, © 2026 Julius Brussee); and microsoft/playwright (Apache-2.0, portions © Microsoft Corporation and © 2017 Google Inc.).

Portions adapted from Anthropic's agent skills, anthropics/skills (Apache-2.0, © 2026 Anthropic, PBC), changed by Buildersoft LLC: rewritten for Sophon tools, with scripts and branding removed (webapp-testing).

Workflow patterns adapted, not copied, from obra/superpowers (MIT, © 2025 Jesse Vincent) and Anthropic's Claude Code plugins (feature-dev, pr-review-toolkit, code-review, security-review, frontend-design; Apache-2.0).

Licensed under the Apache-2.0 License; see LICENSE.
