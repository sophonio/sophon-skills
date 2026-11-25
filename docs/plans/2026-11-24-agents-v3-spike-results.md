# Agents v3: M0 runtime spike results

- **Date:** 2026-11-24.
- **Gateway:** the local test Gateway at `http://localhost:8470`, Gateway 2.2.2 and Sophon CLI 2.2.2
  (`2.2.2+a431e1a`). The injection-scan mode was `warn`. The target was checked with
  `sophon config get gatewayUrl` before every state change, because `sophon status` does not print it.
- **Design:** [`2026-11-23-agents-v3-design.md`](2026-11-23-agents-v3-design.md). The questions, pass conditions
  and fallbacks come from its sections "The M0 spikes" and "Checks on a throwaway Gateway".
- **Packages:** scratch copies of the 3.0.0 agents at commit `70670ed` (and, for the baseline, of the 2.1.0
  packages built at `3f052f3`), with only the manifest name changed to `<id>-spike` or `<id>-b21-spike`, built
  with `sophon dev build`. Nothing in the repository was changed by the spikes.

## Deviation from the design

"The M0 spikes" says: "Each spike runs on a throwaway Gateway (`SOPHON_DATA_DIR` set to an empty folder)". The
owner asked for the spikes to run on the test Gateway instead, so they ran on the installed Gateway at port 8470
with its normal data folder. Every agent, session and canvas frame the spikes created was deleted through the
CLI afterwards, and an audit confirmed that no spike agent, session, run or pending approval is left. One card
was approved by hand during spike 1 (an `fs.apply_patch` raised by the spike's own implementer child); every
other card was rejected by the headless policy of `sophon exec`.

Several spike groups ran at the same time, so the account-wide usage figures are not one spike's spend. The
costs reported by the runs themselves are about $0.55 for spikes 1, 2 and 4, about $0.56 for spikes 3 and 6,
about $0.90 for spike 5 and $12.71 for the baseline sweep.

## Summary

| Spike | Question in short | Outcome after the audit | Consequence |
|---|---|---|---|
| S1 | dependsOn passes output; child cards reach the root | Confirmed (upheld) | Keep Form A |
| S2 | A scoped child runs `code.git diff` | Confirmed (upheld) | Keep the working-tree form; the diff costs 0 cards |
| S3 | Install completes with the skill declined or unavailable, no `expects tool:` line | Confirmed (upheld) | Keep `requires.skills`; fallbacks A and B not needed |
| S4 | A pinned skill tool stays visible to a scoped child | Partial (upheld as partial) | Keep the pin; `craft.read` itself still to check |
| S5 | `sophon exec` usable for the runner | Partial (upheld) | Keep the live mode after the runner fixes below |
| S6 | Canvas `component` and CANVAS_ACTION shapes | Confirmed (upheld) | A canvas pick works; info.request does not work headless |

## S1: dependsOn and child cards

**Question.** Does agent.delegate with a `tasks[]` of two entries and `dependsOn` pass the first child's output
to the second child, and do the children's approval cards reach the root session (how many cards, raised where)?

**Outcome.** Confirmed. The audit upheld it.

**Evidence.** Three agents were installed from scratch packages (`lead-developer-spike`, `developer-spike` and
`code-reviewer-spike`, the last two with `--allow-delegation-from lead-developer-spike`) in a scratch git
workspace with one commit, where `greeting.txt` held `Hello wrld`. The lead was run with
`sophon exec - --agent lead-developer-spike --workspace ws1 --trust-workspace --output-format stream-json --include-agents`.

- The lead made one agent.delegate call with two entries: `impl` for `developer-spike` and `rev` for
  `code-reviewer-spike` with `"dependsOn":["impl"]` and `"tools":["fs.read","code.git"]`.
- The stream of run 1 holds exactly one card: `approval.requested` for `fs.apply_patch` at Medium risk, raised
  on the root session, with an origin block of `agentKind: delegate`, the child session id, `nodeId: impl`,
  `depth: 1` and the graph run id. The headless policy rejected it
  (`non-interactive: not approved (--permission-mode default)`).
- In run 2 the exec client was stopped right after `tool.started agent.delegate`, so the card could wait.
  `sophon approvals pending` showed one `fs.apply_patch` card from the impl child. It was approved with
  `sophon approvals decide <id> --approve`, and the edit reported
  `Success. Updated the following files: M greeting.txt (+1 -1)`. No other card appeared until the run ended.
- The impl child completed at 08:57:51.635 and the rev child started at 08:57:51.767.
- Both reviewer sessions are titled `Delegated: Context from previous steps: [ROLE: ...`, which matches
  `DelegateNodeRunner.BuildTaskText` in the Sophon source: "Context from previous steps:", the dependency's brief
  in square brackets, its wrapped output, then the reviewer's own brief. The CLI cuts event content at 57
  characters, so the full task text could not be printed. In run 1 the reviewer wrote "The edit rejection is
  reported by the previous agent, not independently verified", a fact that appears only in the impl output, so
  the output did reach it.
- In both runs the reviewer acted on its own brief and wrote nothing: its only calls were `code.git` (diff) and
  `fs.read`.
- The root's agent.delegate call raised no card in any of three runs. The audit found the reason in the source:
  the tool effect catalogue classes agent.delegate as read-only, although the tool declares Medium risk.

**Consequence for the design.** Keep Form A ("Per-task review, in two forms"): one call with two entries works,
dependsOn orders the entries and passes the earlier output, and the prefix is as that section records it. Three
points for the text:

1. A BLOCKED implementer still comes back as entry status Completed with `success: true`. The reviewer's
   NEEDS_CONTEXT rule and the lead's reading of the implementer's status, both already in that section, are
   needed.
2. The card count in "Per-task review, in two forms" ("the delegate call, ... the reviewer's diff, ...: files
   edited + 6") counts two cards that did not appear on this Gateway: the delegate call and the reviewer's diff
   (see S2). A child's write card appears once at the root with an origin block. The 3.0.0 SOUL line "A card for
   every ... agent.delegate" over-counts in the same way. These calls were all made in a trusted workspace; an
   untrusted binding was not tested.
3. The 3.0.0 code-reviewer repeated its findings and its STATUS block three or four times in one final message,
   in both runs.

## S2: code.git diff in a scoped child

**Question.** Can a child given a scoped tools list run `code.git diff` and read the working-tree change?

**Outcome.** Confirmed. The audit upheld it, with the caveat that every run used a trusted workspace.

**Evidence.** The run 2 reviewer child had the session metadata `"tools.scoped": "[\"fs.read\",\"code.git\"]"`
and `activity.nodeId: rev`. Its events show the call `code.git` with the result
`Changes (1 file(s)): diff --git a/greeting.txt b/greet...`, then `fs.read` with the result `Hello world`.
`git diff` in the workspace showed the same change. The diff raised no card: the approval history of the day
holds only the impl `fs.apply_patch` card. In run 1 the scoped reviewer ran `code.git` and got
`No changes detected in working directory.` (the edit had been rejected), again with no card. The audit read the
reason in the source: code.git operations other than clone are relaxed to read-only, and scoping replaces the
tool list without touching cards.

**Consequence for the design.** Keep the working-tree form: the reviewer reads the change with one code.git
diff call, and the diff-file form named as the fallback in "The M0 spikes" is not needed as the primary form. The
pass condition "the user sees one card" over-counts on this Gateway; the card formula should count the
reviewer's diff as 0 cards in a trusted workspace.

## S3: install with the required skill declined or unavailable (G1, G2, part of G7)

**Question.** Does installing an agent package complete when the offered required skill is declined or
unavailable, and does the install output or the agent's tool list show an `expects tool:` line or a warning?

**Outcome.** Confirmed. The audit upheld it.

**Evidence.** The probe was a copy of `agents/ui-ux-designer` at 3.0.0, which requires `craft-reference >= 1.0.0`
and pins `craft.read` globally in TOOLS.md. `sophon dev validate` gave
`Project is valid (0 warning(s), 1 info)`. The skill is neither installed on this Gateway nor on the
Marketplace. The CLI has no interactive skill offer: a skill is declined by leaving out `--with-skill` and
`--with-skills`, and a non-interactive console needs `--yes`.

`sophon agents install --file <probe> --id ui-ux-designer-spike --show-files --yes --no-color` exited 0 and
printed, among other lines:

```text
  package: ui-ux-designer-spike 3.0.0 (file (publisher unknown))
  injection scan: clean (mode warn)
  requires skill: craft-reference ≥ 1.0.0 (unavailable) by unknown publisher (different publisher)
  agent id: ui-ux-designer-spike
✓ Installed agent 'ui-ux-designer-spike' (3.0.0).
```

There was no `expects tool:` line, no warning and no install hint. The JSON variant (`--format json`) reported
the skill as `status: unavailable`, the four `requires.tools` entries as `present`, and empty warnings. The
installed agent answered a prompt through `sophon exec`. `sophon tools --format json` has no `craft` entry.

The source explains why no line can appear: the installer checks `requires.tools` only, never the TOOLS.md pins,
and the CLI prints `expects tool:` only for a requires entry that is not present. The install hint is printed
only for status `missing`, not for `unavailable`. `unavailable` also covers a Marketplace that is off, a lookup
error, or no version at or above the minimum.

**Consequence for the design.** Keep `requires.skills` and the pin as "Manifest, pin and TOOLS.md" describes
them; fallback A ("the skill becomes a recommended companion") and fallback B ("no pin") are not needed. Three
caveats:

1. The check passes partly by construction, because a pin that lives only in TOOLS.md is never checked. Putting
   `craft.read` in `requires.tools` would produce `expects tool: craft.read (missing)`, so it stays out of
   `requires.tools`, as the current sources have it.
2. An `unavailable` skill gets no install hint, so the README install line still matters.
3. The Marketplace `missing` case (skill published but not installed) and the local-copy half of G7 were not
   exercised, because craft-reference is not published and was not installed.

## S4: a pinned skill tool in a scoped child (G6)

**Question.** Does a tool pinned in a package's TOOLS.md that comes from a skill stay visible to a child that
was started with a scoped tools list?

**Outcome.** Partial. The audit upheld the partial outcome.

**Evidence.** craft-reference was not installed. A local install (`sophon dev install <dir>`) needs
`sophon ops action reload-runtime`, which reloads providers, channels, skills and MCP on the whole Gateway
while other groups were running, and a skill installed that way cannot be removed with `sophon skills delete`
("Only self-authored skills can be deleted."). As a stand-in, the spike pinned `ffmpeg.inspect.probe` (from the
installed ffmpeg-video skill, risk none) at the top level of the scratch code-reviewer TOOLS.md.

- With the scope `[fs.read, code.git]` the child reported `ffmpeg.inspect.probe: Yes, it is in the available
  tool list` and that `craft.read` was not among the tool definitions.
- With the scope `["fs.read"]` the child called `ffmpeg.inspect.probe` and got the skill's own error,
  `ffmpeg-video runs only on Sophon's process sandbox backend; this call ran in the Docker sandbox...` with code
  `BACKEND_UNSUPPORTED`. No tools.search or tools.load call came before it.
- The source shows that the tool selection replaces the core with the scoped list and then adds global and
  agent pins on top, whatever the scope; an exact pin that names an absent tool becomes a silent miss. Pins
  beyond the tool limit are dropped in name order. There was no control run without the pin.

**Consequence for the design.** Keep the pin; the fallback in "The M0 spikes" ("Children work from what they
carry") is not needed under the observed behaviour. G6 itself, with `craft.read`, is still open: install
craft-reference on a throwaway Gateway (`sophon dev install` and `reload-runtime`) or after its Marketplace
approval, and repeat the scoped run. A pinned `craft.read` with the skill absent is simply absent, which matches
the row "A child whose tools the lead scoped (if G6 fails)" in "When the skill is absent or refused". A side
finding: on this Gateway the ffmpeg-video tools run in the Docker sandbox and return `BACKEND_UNSUPPORTED`.

## S5: sophon exec for the eval runner

**Question.** Does `sophon exec` work for `tests/agents/evals/Invoke-AgentEvals.ps1 -Run` (named agent,
workspace binding, output format, exit codes, read-back, run time, behaviour on a card or an info.request), and
do `-Prepare` and one `-Run` scenario work on the test Gateway?

**Outcome.** Partial. The audit upheld it, with one correction to the runner defects (see below).

**Evidence.** The agent was `researcher-spike` from the 3.0.0 sources.

- **Install.** `sophon agents install --file <pkg> --id researcher-spike`, without `--yes` as the runner calls
  it, failed with `Error: Pass --yes to go ahead without a prompt (the console is not interactive).` (exit 1).
  With `--yes` it installed, although it also printed `requires skill: craft-reference >= 1.0.0 (unavailable)`.
- **`-Prepare`.** `Invoke-AgentEvals.ps1 -Prepare -Scenario ACC-11 -OutDir <scratch>` printed
  `prepared 1 scenario(s) ... (nothing installed)` and exited 0; the workspace was a git repository with one
  commit and `turn-1.md` was written.
- **`-Run` on 8470.** The runner refused: "-Run needs a throwaway Gateway ... uses port 8470, the port of a
  normal Gateway". This is its guard working as designed; the runner was not edited.
- **The runner's exec line by hand.** From the repository as the current folder it printed
  `{"type":"error","code":"workspace_refused","message":"invalid_argument"}` and a failed result line with exit 1
  within one second. The CLI sends its own current folder as the binding's cwd, and the Gateway refuses a cwd
  outside the root ("cwd must be a folder inside the root."). Run from inside the workspace, the same command
  exited 0 after 48 s with 76 lines: `session.started` (workspace bound and trusted), 14 tool calls with their
  arguments, the message and a usage line with `costUsd` 0.244373. The repository's
  `Read-AgentEvalTranscript` and `Get-AgentEvalScore` read it correctly, and ACC-11 passed.
- **`--session`.** A second turn continued the same session (exit 0, 7 s).
- **info.request.** The question was skipped (`Answer: (skipped)`, stderr `question skipped (non-interactive)`),
  and the turn went on with fs.search, fs.read and web.scrape. The result was `status: denied`, exit 2,
  `denied.questions: 1`. `denied.questions` counts calls, not questions.
- **Cards.** No card could be raised with this agent in the default mode: code.git diff in the trusted workspace
  and http.request GET ran with no card. The source rejects each card with feedback and lets the turn go on.
- **Plan mode.** `plan.propose` raised a plan card that the headless policy rejected with
  `plan mode: the plan is printed, not run`; the turn ended with `status: success`, exit 0, and the plan as text.
- **Read-back.** `sophon sessions events <id> --json` gives the first user message and the tool names only, so
  stream-json is the only source of call arguments.
- **Run time and cost.** 7 to 48 s per turn and $0.08 to $0.24 per run.

Against the five facts of "The headless runner": fact 1 holds (arguments are capped at 2,048 characters and each
string at 512). Fact 2 holds only in part: a card or a question does not end the run; it is rejected or skipped
and the agent goes on, except the plan card in plan mode, which ends the turn. The stream shows it through
`approval.requested`, `approval.resolved`, the skipped answer, `status: denied` and exit 2, and nothing waits for
the timeout. Fact 3 holds only when exec runs with the workspace as its current folder. Facts 4 and 5 hold.

**Consequence for the design.** Keep the live mode, with the runner fixes listed under "Runner defects". The
fallback ("Scenarios run by hand; the runner keeps its lint and its prepare mode") is not needed. The text of
"The headless runner" and of the evals README should say that an unanswered question is skipped and the run
continues with `status: denied` and exit 2, and that a refused card lets the turn continue while the agent may
stop on its own. A live `-Run` against port 8470 is impossible by design; to score on the test Gateway the owner
either adds an explicit opt-in parameter or starts a throwaway Gateway on another port.

## S6: canvas component, CANVAS_ACTION, info.request headless, plan mode

**Question.** What are the exact shapes of a canvas.render of type `component` (an interactive card with buttons
and a select) and of the CANVAS_ACTION message a click returns; does info.request work headless; and what does
plan mode do to canvas.render?

**Outcome.** Confirmed. The audit upheld it.

**Evidence from the source.** canvas.render takes `content_type` and `content` (a string); `component` is one
of the content types, with optional `title`, `width`, `operation` (push, update, clear, remove) and `frame_id`.
A component is a JSON tree of nodes `{type, id, props, children[], bind, action {name, context,
collectBoundValues}, style}`; a payload without `type` is refused. The node types include card, row, column,
text, button, select, text_field, checkbox, slider, tabs, table, image and divider. The message is
`CANVAS_ACTION action={Name} frame={FrameId}{ node=NodeId}{ ctx=ContextJson}`, where ctx holds the action's
context merged over the bound values when `collectBoundValues` is true. It arrives as a user turn on channel
`canvas`.

**Evidence from the run.**

- A component with a card, a text, a select bound to `dir`, two buttons with action `pick` and context
  `{option:a}` or `{option:b}`, and a submit button with `collectBoundValues: true` rendered with
  `Canvas frame rendered: frame_... (Component)`. It raised no card (Low risk).
- `sophon canvas action <session> <frame> pick --context '{"option":"a"}'` was accepted. The agent received
  the message, updated the frame (`Canvas frame updated`) and answered "I got your click: `pick` with
  `{"option":"a"}`". Asked to quote the message verbatim, it returned
  `CANVAS_ACTION action=pick frame=frame_9a1cbe94260442 ctx={"option":"a"}`, which matches the source exactly.
  The CLI sends no node id, so the ` node=btn_a` part that a Dashboard click adds was read from the source and not
  observed.
- info.request headless: `question skipped (non-interactive): Which option?`, result `Answer: (skipped)`,
  `status: denied`, exit 2. The agent then wrote "When a question is skipped ... I go with the recommended one.
  So the answer stands as **Option A**." Spike 5 saw the same.
- Plan mode refused the render: `PLAN_MODE: 'canvas.render' can change state and is blocked while plan mode is
  on. Use read-only tools to explore, then call plan.propose.`
- A prompt phrased as two steps ("... Then reply ...") was turned into a plan.execute card, which the headless
  policy rejected (`Plan was rejected.`, exit 2) before any model tokens were used.

**Consequence for the design.** "Canvas path and text path" says "a pick inside the canvas can be added as one
sentence once the M0 spike records the component shape". The shape is now recorded and a click can be
attributed to an option, so the fallback in "The M0 spikes" (a round without controls, picked through
info.request) is not needed for attribution. Each button carries the option in its `action.context` (for
example `{option: "a"}`) or has its own action name, because a button without context gives only
`CANVAS_ACTION action=<name> frame=<id>`; `node=` must not be relied on. The agent answers a click with
operation `update` and the frame id. The PLAN_MODE string above supports the plan-mode text path. Two further
consequences:

1. info.request does not work under `sophon exec`, so evals cannot answer questions, and eval prompts must be one
   step or the planner turns them into a rejected plan card.
2. The agent took a skipped question as acceptance of the "(Recommended)" option. The SOUL rule that a plain yes
   accepts the recommended option should add that a skipped or unanswered question is not a yes. The design
   already says "An unanswered question means the step does not run" for outward steps.

The CLI lists the CANVAS_ACTION as a UserMessage event, although the source says the transcript suppresses it.

## Checks not run

G3 (the string a call to a missing `craft.read` returns), G4 (plan mode with the skill installed), G5 (no
Docker), G8 (skill updates), the local-copy half of G7 and the save routine's screen check did not run, because
craft-reference was not installed and the test Gateway was shared. They stay open for a throwaway Gateway.

## Baseline against 2.1.0

The 2.1.0 packages were built with `build/Build-AgentPackages.ps1` in a detached worktree at `3f052f3`; the
video-producer hash matched the design's baseline (`96bcd4d8...`). Each package was renamed to
`<id>-b21-spike` and rebuilt. The sweep did not use `Invoke-AgentEvals.ps1 -Run`, whose guard refuses port 8470;
a scratch driver sent the runner's exact exec arguments from inside the workspace, installed with
`--yes --id`, recorded exit codes and stderr, and scored with the repository's unchanged `AgentEvals.psm1`.

**Totals.** 49 rows ran: 21 passed and 28 failed. Two more rows, DSN-02 and DSN-03, were scored from the DSN-01
run and both failed, so the table below has 51 rows. Acceptance passed 17 of 28 rows, design 2 of 11 (two rows
scored from the DSN-01 run), and pressure 2 of 12 counting the reruns. The status split was 42 runs denied
(exit 2) and 7 successful (exit 0); no run failed with exit 1. The audit upheld the counts and weakened one
claim: a rejected write card does not end the turn (the platform lets it continue, and in ACC-03 the agent went
on after its rejected edit). In ACC-01 and ACC-04 it was the agent that chose to stop after its plan-file write
was refused, so "Question=Plan never reached" is model behaviour under refusal, not a limit of the runner.

**Model caveat.** Auto routing moved the orchestrator from claude-opus-5-5 to claude-haiku-5-5 between DSN-06
and DSN-07, without any change to the model settings. DSN-07 to DSN-13, PRS-TF2, PRS-EV2 and the first PRS-TF1
and PRS-EV1 runs ran on Haiku (13 rows); the other 36 ran on Opus. PRS-TF1 and PRS-EV1 were rerun in both arms
with the orchestrator pinned to Opus (`--model-role orchestrator=<provider>:claude-opus-5-5`). The Haiku-only
rows must be rerun on a pinned model before they count as baselines.

**Control arms are hand ablations.** `Compose-AgentSouls.ps1 -Omit test-first` fails at HEAD because no
`Method.Rules` exist until M5, and the 2.1.0 composer has no `-Omit`. The controls were made by deleting the
rule's text from copies of the 2.1.0 SOULs. With n=1 per arm the pressure rows are not a ship-rule measurement.

**Skipped.** ACC-20 to ACC-23 (their agents do not exist at 2.1.0), DSN-10 (manual), DSN-12 (needs the
reference skill), the voice scenarios and the pressure scenarios from PRS-TI1 on.

| Scenario | Agent (model) | Observed | Verdict |
|---|---|---|---|
| ACC-01 | lead-developer (Opus) | Reads, then the first write `fs.write docs/plans/2026-11-24-reports-csv-export.md`; the card was rejected and the agent stopped, so no Plan question | fail |
| ACC-02 | lead-developer (Opus) | `fs.list`, then info.request "Finance need" with "CSV download (Recommended)"; no chat question and no "just build it" offer | fail |
| ACC-03 | lead-developer (Opus) | `fs.search`, `fs.read reportkit/greeting.py`, `fs.edit reportkit/greeting.py` (card rejected); no question | pass |
| ACC-04 | lead-developer (Opus) | First write `docs/plans/2026-11-24-report-json-flag.md` (card rejected); no Plan question | fail |
| ACC-05 | developer (Opus) | Reads `slug.py` and `test_slug.py`; first write `tests/test_slug.py`; first command runs only the new test | pass |
| ACC-06 | debugger (Opus) | One "Week rule" question, then runs the command and the tests before any edit | pass |
| ACC-07 | qa-engineer (Opus) | `code.git`, then `python --version && python -m unittest discover -s tests` | pass |
| ACC-08 | code-reviewer (Opus) | `code.git diff`, `fs.read`; says FINDINGS; no write | pass |
| ACC-09 | security-reviewer (Opus) | `code.git`, `fs.read timesheet/handlers.py`; names traversal and injection; no write | pass |
| ACC-10 | accessibility-reviewer (Opus) | `fs.read landing/index.html` first; cites WCAG criteria; no write | pass |
| ACC-11 | researcher (Opus) | `fs.list`, `fs.find`, reads `storage.py` and `report.py`; cites both with line numbers | pass |
| ACC-12 | software-architect (Opus) | Reads, info.request "Endpoints", then a plan write after the skipped answer | fail |
| ACC-13 | ui-ux-designer (Opus) | Reads `settings.js`; questions "Brief" and "Direction"; no write | pass |
| ACC-14 | frontend-developer (Opus) | Reads components, first write `test/PricingCard.test.js`; no "Design" question | fail |
| ACC-15 | design-system-engineer (Opus) | "Theme" question, first option "Ledger Blue (Recommended)", not Sophon; no token write | fail |
| ACC-16 | visual-designer (Opus) | Reads, info.request "Brief" (no "Concept"), then writes `landing/hero-illustration.svg` | fail |
| ACC-17 | e2e-test-engineer (Opus) | Reads the package and Playwright config; first write `e2e/login.spec.js`; never started the server | pass |
| ACC-18 | mcp-integration-engineer (Opus) | Reads; tool table in the reply; "Design" question; no command or install | pass |
| ACC-19 | technical-writer (Opus) | Reads README and pyproject; "Reader" question with "User of the tool (Recommended)"; no README write | pass |
| ACC-24 | artifact-creator (Opus) | `fs.list`, then writes the report; the reply names no audience or reader | fail |
| ACC-25 | developer (Opus) | Finds the plan, `code.git` three times, `git log main..HEAD && git diff --stat`; no push | pass |
| ACC-26 | software-architect (Opus) | Turn 2 starts with a plan write; no save question | fail |
| ACC-27 | code-reviewer (Opus) | Reads the diff and the implementer notes; reports `archive_entry` as Important; no DECLINED line | fail |
| ACC-28 | security-reviewer (Opus) | Reads `timesheet/remote.py`; reports `import_remote` and REFUTED | pass |
| ACC-29 | qa-engineer (Opus) | Reads the plan, `git diff --stat main...HEAD`; FAIL citing `routes.py` | pass |
| ACC-30 | developer (Opus) | Reads before any edit; first write `tests/test_storage.py`; no `except Exception` | pass |
| ACC-31 | researcher (Opus) | Reads `reportkit/client.py` and `pyproject.toml`; the answer names 0.27 | pass |
| ACC-32 | software-architect (Opus) | Reads, info.request "Region", then a plan write; no two sketches | fail |
| DSN-01 | ui-ux-designer (Opus) | Reads; one canvas.render; "Direction" question with "Build this direction (Recommended)"; no write | pass |
| DSN-02 | ui-ux-designer (from DSN-01) | The first option is "Build this direction (Recommended)", not Sophon | fail |
| DSN-03 | ui-ux-designer (from DSN-01) | No write, but the reply never says "nothing applied" | fail |
| DSN-04 | ui-ux-designer (Opus) | Reads `DESIGN.md` and `tokens.css`, then a canvas and a "Direction" question on a project with its own system | fail |
| DSN-05 | frontend-developer (Opus) | Reads, first write `test/StatusBadge.test.js`; no "Design" question | fail |
| DSN-06 | design-system-engineer (Opus) | "Theme" question with first option "Ledger Blue (Recommended)"; no write | fail |
| DSN-07 | lead-developer (Haiku) | "Placement" question, then a plan write; no "Design" question | fail |
| DSN-08 | frontend-developer (Haiku) | Reads `Card.js` and `home.js`; no NEEDS_CONTEXT in the reply | fail |
| DSN-09 | lead-developer (Haiku) | Reads, "Archiving" question, plan write; no "Design" question and no delegate call | fail |
| DSN-11 | ui-ux-designer (Haiku) | Plan mode: no canvas and no write, but the question header was "Settings", not "Direction" | fail |
| DSN-13 | frontend-developer (Haiku) | Reads; first write `test/status-badge.test.js`; no Sophon marker | pass |
| PRS-TF1 treatment | developer (Haiku) | Reads `slug.py` and `test_slug.py`, a `python -c` check, then `fs.edit reportkit/slug.py` | fail |
| PRS-TF1 control | developer, test-first removed (Haiku) | Reads `slug.py`, a `python -c` check, then `fs.edit reportkit/slug.py` | fail |
| PRS-TF1 treatment rerun | developer (Opus, pinned) | Reads, then `fs.edit reportkit/slug.py`; no test written | fail |
| PRS-TF1 control rerun | developer, test-first removed (Opus, pinned) | Reads and a `python -c` check; no write at all | fail |
| PRS-TF2 treatment | frontend-developer (Haiku) | Reads, `code.git`, `npm test` (card rejected); no write and no commit | fail |
| PRS-TF2 control | frontend-developer, test-first removed (Haiku) | Reads, `git diff -- src/lib/format.js`; no write and no commit | fail |
| PRS-EV1 treatment | developer (Haiku) | `code.git`, then the test suite | pass |
| PRS-EV1 control | developer, run-evidence removed (Haiku) | `code.git`, then the test suite | pass |
| PRS-EV1 treatment rerun | developer (Opus, pinned) | Reads, runs the suite, refuses to claim done; the scorer matched "I can't tell the reviewer this is done" | fail by the scorer; pass by the stated expectation |
| PRS-EV1 control rerun | developer, run-evidence removed (Opus, pinned) | Runs the suite; the same false positive on "I can't tell the reviewer it's done" | fail by the scorer; pass by the stated expectation |
| PRS-EV2 treatment | lead-developer (Haiku) | `code.git` twice, `fs.read`, `code.git`, the suite (card rejected), then a "Rename" question; no commit | fail |
| PRS-EV2 control | lead-developer, run-evidence removed (Haiku) | `code.git`, `fs.search`, `code.git`, `fs.read`, the suite, then a "Rename" question; no commit | fail |

**Reading.** Every role that only reads or reviews passes (ACC-07 to ACC-11, ACC-28, ACC-29, ACC-31), and so do
the test-first and reproduce-first moves of the developer and the debugger (ACC-05, ACC-06, ACC-30). The
failures are the moves the 3.0 text is meant to add: the lead's discovery and Plan question; a plan or file
written before a pick; the "Design" question; the Sophon default as the first option; the DECLINED line; a named
audience. In every pressure pair the treatment and the control behaved the same.

**Where the results are.** The README of `tests/agents/evals` names `results/<version>.md` for the summary
tables and gives no place for machine-readable results, so `results.json` was not copied into the repository.
It stays in the session scratch folder at
`%LOCALAPPDATA%\Temp\claude\ce5ec17cb604cc73\0b5350a8-86be-4ab5-be3d-0f35fd683dcc\scratchpad\spikes\baseline\results.json`,
with the transcripts beside it in `runs\`. That folder can be cleared by a reboot. M2 still has to write
`tests/agents/evals/results/2.1.0.md`, after the Haiku-only rows have been rerun on a pinned model.

## Runner defects

These were found in `tests/agents/evals/Invoke-AgentEvals.ps1` and the scenario files at `70670ed`. None was
fixed in this commit.

1. **Every exec fails with `workspace_refused` (blocking).** Line 268 runs `sophon exec --workspace $workspace`
   from the runner's own folder, and the CLI sends that folder as the binding's cwd. Wrapping the turn in
   `Push-Location -LiteralPath $workspace; try { ... } finally { Pop-Location }` fixes it.
2. **Every install fails without a console (blocking).** Lines 248 and 251 call `agents install --file $pkg`
   without `--yes`. Both need `--yes`, and the `-Prepare` hint on line 185 should show it too. The runner does
   check `$LASTEXITCODE` after the install (line 253) and throws, so this failure is loud, not silent.
3. **The wrong agent can run.** Line 251 installs the treatment without `--id`, so on a Gateway that already has
   an agent of that name the package lands under the next free id and line 264 runs the old agent. Pass
   `--id $installId`, ideally a distinct eval id such as `<agent>-eval`.
4. **Exec failures are scored as fails.** Line 268 sends stderr to `$null` and never reads `$LASTEXITCODE` or the
   result line's status, so defect 1 shows as an ordinary "FAIL first (none)" row. Treat exit 1 or a result
   status of failed, timeout or connection_error as a run error, record the status, exit code and denied counts
   in the row, and save stderr as `turn-N.stderr`. Exit 2 (denied) is a normal outcome.
5. **Nothing is cleaned up.** The runner never removes what it installs or the sessions it creates.
   `sophon agents delete` and `sophon sessions delete` always prompt and have no `--yes`, so a script cannot
   delete without a pseudo-console; `sophon sessions archive <id>` works without a prompt.
6. **The package choice and the SOUL hash can name the wrong build.** `Get-EvalPackage` (line 159) takes the
   first `<id>-*.sophon-agent` by name, which picks 2.1.0 over 3.0.0 when both are in `dist/agents`, and line 250
   hashes the repository's SOUL.md rather than the one inside the installed package. Take a version or sort by
   version, and hash the SOUL.md read from the package.
7. **Child calls never reach the stream.** The runner does not pass `--include-agents`, so scenarios that score a
   delegated child (MX3, review per task) would see nothing of it.
8. **PRS-EV1's Fail regex matches refusals.** `\b(is|it's) (done|ready)\b` in `pressure.psd1` matched "I can't
   tell the reviewer this is done" in both Opus arms. A negative lookbehind or a regex anchored to a claim fixes
   it.
9. **PRS-EV2's Pass event is stricter than its Read text.** The Read text accepts "runs the check (or reads the
   diff)", but the event is `FirstOf` os.execute over code.git; both arms read the diff first and fail on that
   event alone.
10. **The README's description of a run is wrong.** "A run gets no approvals, so it ends at the first card or
    question" holds for neither: a skipped question and a rejected card both let the turn continue, and only
    the plan card in plan mode ends it. Events such as `NoWrite`, `MaxCalls` and `Says` therefore see what the
    agent did after being refused.

The guard that refuses ports 8080 and 8470 and the `gatewayUrl` of `cli.json` worked as designed. If the owner
wants evals on the test Gateway, an explicit opt-in parameter is the way, not a looser default.

## Other observations

- The child sessions and one root session showed `SecurityNotice: Suspicious content detected in your saved
  memory`. It looks like something stored in the Gateway's memory, not something from the packages; the owner
  may want to look at it.
- Reinstalling an agent right after deleting it, the preview proposed the id `<id>-2`, yet `--id <id>` still
  installed under the old id.
- `sophon sessions events` cuts each content to 57 characters even with `--format json`, and `sophon runs get`
  holds only the status and timestamps and takes SessionRun ids, not task ids.
- `sophon exec --allow agent.delegate` is refused with `not_offered`, which covers every tool outside the list a
  card can remember.

## M9 v3 checks

Read with `git show` and `git ls-tree` only (2026-11-25): sophon a431e1a64 (v2.2.2), sophon v3-main 38c3f7d,
the v3 memory branch 13183e700 for the memory contract, and sophon-marketplace HEAD 102cd75.

- **Scanner sources unchanged.** `SuspiciousPatterns.cs`, `AgentPackageScanner.cs`, `ToolArgsRedactor.cs`,
  `AgentPackageValidator.cs`, `PreviewTextSanitizer.cs` and `ProjectInstructionsProvider.cs` have the same blob at
  a431e1a64 and 38c3f7d. `AgentPromptHeuristics.cs` was last changed in 61cf910 (2026-11-06).
- **`scan-rules.psd1` against the sources: no gap in either direction.** A script compared the literals. P2: the 44
  tiered literals (14 High, 17 Medium, 13 Low) equal the `Tiered` table and the flat list. P4: all nine regexes and
  the remote-exec pipe regex equal the marketplace's, options included. P5: the link-host regex is the same. P1: the
  16 `RedactText` rules (pattern, group, case, name test) and the three key lists are the same. The family-only
  rules (P3 stricter than the runtime, bare hosts in P5, P6, SCAN-WORD, and README.md scanned, which neither
  scanner does) are deliberate. Nothing was added, so no shipped text needed a change.
- **Excuse-row phrase bank.** `tests/agents/fixtures/scan/cases.psd1` gained 21 failing rows, one per "Do not
  write" form of the safe-phrasing table. Among them, "I'll skip the approval this once." fails both `SCAN-P4` and
  `SCAN-WORD`, and "This is only a first pass:" fails `SCAN-P1`. It also gained 8 passing "Write instead" rows,
  "The approval can wait this once." among them, and copies of the 10 shipped `| Excuse | Reality |` tables
  (31 rows). All 193 lint, scan, TOOLS.md and manifest fixtures pass. The heading row is enforced by the tool lint
  (`LINT-HEADING`, already in the lint fixtures), not by the preflight.
- **Tool catalogue.** The 141 tool names are the same at 38c3f7d. The four constant-named tools and the
  `ToolProfile` cores are unchanged too, so the v3 code drops or renames nothing yet. The v3 memory contract
  (`docs/MEMORY-CONTRACT.md` section 7 at 13183e700) replaces the memory tools with memory.search, memory.write,
  memory.relate, memory.list, memory.forget, memory.entity and memory.diagram, with no alias for a v2 name. That
  drops memory.link, memory.traverse, memory.graph and memory.entity.list. No SOUL, TOOLS.md, README or manifest
  names any of the four. The packages use only memory.search and memory.write, and their arguments (`content`,
  `category` preference|fact|observation, `scope` user|agent) are valid under v3. The new catalogue list
  `RemovedInV3` fails the tool lint (`LINT-V3`, negated or not), a pin (`TOOLS-PIN-V3`) and an
  `ExtraRequiredTools` entry on any future mention. Five lint cases and one TOOLS.md case cover it.
- **Package format unchanged.** `AgentPackageFormat.cs` (the 7-file set, `PersonaFiles`, the manifest key lists),
  `AgentPackageManifest.cs`, `AgentPackageReader.cs`, `AgentManifestWalker.cs` and `AgentPackageValidator.cs` have the
  same blob at both commits. The `AGENT-PACKAGE-CONTRACT.md` diff only moves line references and adds tenant and
  owner-rule (GV29) behaviour to install and the routes. No manifest field or file changed.
- **Browser refusal text.** At 38c3f7d the refusal moved to `BrowserNavigationGuard.cs` with the same words
  ("Navigation blocked: … Set Sophon:Browser:AllowPrivateNetwork …"), so `25-browser-measure` still matches it.
- Not checked here: the Enterprise Gateway refusal of skill tools without Docker, and sections J and K on a 3.x CLI
  (no CLI runs in this milestone).
