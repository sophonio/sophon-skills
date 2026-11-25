# E2E Test Engineer

Writes browser end-to-end and visual tests in your repository's own runner, proves each one red then green, and makes flaky tests deterministic.

Part of the Buildersoft development family {{= FamilyVersion}}.

{{# roster}}

## When to use

- End-to-end tests for a user flow: sign-in, checkout, a form, a multi-page journey.
- Screenshot or visual regression tests for pages and components.
- A failed visual comparison you want reviewed before any baseline changes.
- A flaky end-to-end test that passes locally and fails in CI, or fails only in a full run.

## Not for

- Unit and integration tests, or the verification gate before a merge: `qa-engineer`.
- Root-causing a product bug a test exposed: `debugger`.
- Changing product code: `developer` or `frontend-developer`.
- Accessibility audits: `accessibility-reviewer`. Judging visual design: `ui-ux-designer`.

## How it works

- It finds your e2e runner and command first: project instructions, package scripts such as `test:e2e`, the runner config, then CI. Your configured command always wins. It reads two neighbouring specs and copies their fixtures, helpers and naming.
- **The app.** It never starts a server, because Sophon's shell cannot run background processes. It tests the app you already run, or lets the runner's own `webServer` setting start and stop the server inside one test command, after you confirm that. Your running app alongside a `webServer` block needs `reuseExistingServer` on and a matching base URL; otherwise it tells you the runner will start its own server.
- **Recon before acting.** It opens the page, waits for the main content, then lists buttons, links, inputs and headings with their roles, names and test ids, so selectors come from the rendered page. For static HTML it reads the file.
- **Write, in four steps.** Plan: it names the scenarios, failure cases included, and with more than three asks which to write first. Walk it live: it does each scenario once in the browser, one card per step, and tells you the count first; it writes only steps it watched work (with no reachable app it writes from the source and says so). Write: selectors by role and name first, then label or text, then test id, then CSS; one behaviour per test; condition waits, never fixed sleeps; every new test red first, failing for the right reason, then green. Heal: one failure at a time, its cause named (locator, timing, data or environment, or the app is wrong). Healing changes locators, waits and test data, never what is asserted; a test that fails on an app defect stays red and is reported.
- **Visual.** Screenshot assertions on stable state: fonts loaded, animations off, dynamic regions masked. When a comparison fails it quotes the difference and lists the expected, actual and diff images for you to open, then asks whether to keep or update the baseline; no answer keeps it. It updates only the tests you approved. A new baseline is run again until the comparison succeeds three times. Baseline names carry the operating system, so it never commits one as the CI baseline without asking.
- **Flake.** It reproduces with repeat runs, classifies the failure (timing, shared state or environment), replaces sleeps with condition waits, and, when the test fails only in a full run, finds the polluter by halving the list of earlier spec files, repeating each half so one lucky run cannot clear it. The fix is proven with the same repeat run.
- A skipped or `fixme` test, an added retry or a longer timeout counts as weakening a test: that is your decision, with the reason written in the test.
- Work bigger than a small change gets a plan file in `docs/plans/` that you approve, a `sophon/<slug>` branch and one verified commit per task, then the finish menu: Push + open PR, Merge into `<base>` locally, or Keep local. Discard runs only when you ask, after a second confirmation.
- Replies are plain sentences; say "terse" or "caveman" for short ones and "normal" to switch back.

## Tools and cards you'll see

| Action | Card |
|---|---|
| Reading and searching files, `code.git` status and log, `browser.screenshot`, `web.scrape`, the todo list | none |
| Each test file it creates or edits | one per file |
| Each test run (`os.execute`), including every repeat and bisection run | one each |
| Each `browser.act` step on your running page (navigate, wait, evaluate, and each step of a live walk) | one each |
| `code.git` diff | may raise one; none in a trusted workspace on the Gateway we tested |
| Letting the runner start your server, or updating a visual baseline | a question first |

## After installing

- **Install:** `sophon agents install e2e-test-engineer`, with `--allow-delegation-from lead-developer` if Lead Developer should brief it. The default effort is fine.
- **Allowed Medium-risk calls for the session** never cover this agent's edits, commits or shell commands, nor any call it makes as a sub-agent.
- **Bind and trust the folder.** Run `sophon` in the repository so the session is bound, then `/trust` the folder so its AGENTS.md conventions load.
- **Browser recon** needs Playwright Chromium on the Gateway host, and `browser.act` opens a localhost page only when `Sophon:Browser:AllowPrivateNetwork` is on. Start your app first.
- **Your runner** needs its browsers installed in the project; it asks before adding Playwright or downloading browsers.

## Works best with

- `qa-engineer`: owns the verification gate and the unit and integration suites; this agent owns the browser layer.
- `debugger`: takes a product bug an end-to-end test exposed and finds its cause.
- `frontend-developer`: builds the UI these tests drive, and adds a test id when one is needed.
- `lead-developer`: can hand it the end-to-end part of a larger plan.

## Limits

- The model cannot see screenshots or diff images; you open them and decide.
- As a sub-agent it cannot ask you, so it never updates a baseline there; it lists the decision for you.
- Without a running app or a confirmed `webServer` setting it cannot run end-to-end tests, and it writes tests from the source.
- Each repeat, bisection run or live step is its own card, so a flake hunt or a live walk asks for several approvals.

## What it never does

- Start dev servers or anything else in the background.
- Update a visual baseline you have not approved, or update the whole suite at once.
- Make a test pass by weakening it: no added retries, longer timeouts or skips unless you ask.
- Fix product code; a product bug is reported with the failing test.
- Write test-user secrets into tests; it names the environment variable instead.
- Push without your choice in the Git menu.

## What's new in 3.0.0

- write runs plan, walk it live, write, then heal one failure at a time.
- The finish menu adds Merge into `<base>` locally; Discard only on request.
- A terse voice on request.

{{> readme/80-upgrade-3}}

{{> readme/70-reference-skill}}

## Credits and license

Ideas re-expressed in our own words also come from JuliusBrussee/caveman (Apache-2.0, © 2026 Julius Brussee); and microsoft/playwright (Apache-2.0, portions © Microsoft Corporation and © 2017 Google Inc.).

Portions adapted from Anthropic's agent skills, anthropics/skills (Apache-2.0, © 2026 Anthropic, PBC), changed by Buildersoft LLC: rewritten for Sophon tools, with scripts and branding removed (webapp-testing).

Workflow patterns adapted, not copied, from obra/superpowers (MIT, © 2025 Jesse Vincent) and Anthropic's Claude Code plugins (feature-dev, pr-review-toolkit, code-review, frontend-design; Apache-2.0).

Licensed under the Apache-2.0 License; see LICENSE.
