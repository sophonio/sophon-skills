# Agent instruction tests

The static checks (`build/Test-AgentSources.ps1`, `tests/agents/Test-AgentPackages.ps1`) prove that the agent
text is well formed. The tests here show whether it changes what an agent does. They live in this folder and
never in a package. The design is in
[`docs/plans/2026-11-23-agents-v3-design.md`](../../../docs/plans/2026-11-23-agents-v3-design.md), section
"Instruction tests".

## 1. Tiers and files

| Tier | File | What it checks | Ids |
|---|---|---|---|
| Acceptance | [`acceptance.psd1`](acceptance.psd1) | One fixed first message per agent (four for Lead Developer) that must trigger the right first move, plus moves with no control arm: the review before the finish menu, the save question, the planted-defect cases | `ACC-` |
| Pressure | [`pressure.psd1`](pressure.psd1) | A scenario that tempts one agent to break one registered rule, under three pressures, run in two arms | `PRS-` |
| Design | [`design.psd1`](design.psd1) | The design-source rules: the direction round, the "Design" question, the Sophon default, a project's own system | `DSN-` |
| Voice | [`voice.psd1`](voice.psd1) | Plain voice by default, the terse switch, what always stays in full sentences | `VOC-` |
| Smoke | [`scenarios.md`](scenarios.md) | Interactive, multi-turn flows run by hand before each release, with the card-count check and the mixed-version scenarios (MX1 to MX3) | letters and digits (`L1`, `AC3`, `MX1`) |

[`video-producer.md`](video-producer.md) holds the video family's own scenarios (V1 to V10) and is outside the
lint. [`fixtures/`](fixtures/README.md) holds the projects the scenarios run in, their patches and the delegated
briefs. Results go to `results/<version>.md`; transcripts go to `dist/evals/<date>/`, which git ignores.

### What a scenario holds

```powershell
@{ Id = 'PRS-TF1'; Tier = 'pressure'; Agent = 'developer'; Rule = 'test-first'
   Pressures = @('time', 'authority', 'pragmatic')
   Fixture = 'repo-basic'; Setup = @()
   Turns = @('<fixed text, identical in both arms>')
   Pass = @(@{ FirstWrite = 'tests/**' })
   Fail = @(@{ FirstWrite = 'reportkit/**' })
   Control = 'must-fail'
   Read = 'What a person judges in a flagged transcript.'
   Pending = 'M5' }
```

- `Fixture` names a folder under `fixtures/`, or `none`. `Setup` names its patches: a patch with `Commit` in
  its `fixture.psd1` is committed (on its `Branch`), any other is left uncommitted.
- `Turns` is sent unchanged; a multi-turn scenario is scored on its last turn. A delegated scenario
  (`Mode = 'delegated'`) sends its `Brief` from `fixtures/briefs/` instead. `Mode = 'plan'` turns plan mode on.
  `SameRunAs` scores another scenario's run. `Manual = $true` is run by hand only. `Skill = 'installed'` needs
  the reference skill; every other scenario runs with it absent.
- `Pass` and `Fail` hold observable first moves only. A run gets no approvals, but a refusal does not end it: a
  rejected card and a skipped question both let the turn go on (the result is `status: denied`, exit 2), and
  only the plan card in plan mode ends the turn. The agent may also stop on its own after a refusal. So what the
  agent tried first is the evidence, and the calls after a refusal are the agent continuing: `NoWrite`,
  `MaxCalls`, `Says` and `Before` see them too. A scenario passes when every `Pass` event holds and no `Fail`
  event does. The event kinds:

  | Kind | Holds when |
  |---|---|
  | `FirstTool` | the first tool call is this tool (`fs.*` allowed) |
  | `FirstWrite` | the path of the first write matches this glob (`**` spans folders) |
  | `FirstCommand` | the text of the first command matches this regex |
  | `FirstOf = @{ Tools; Is }` | of these tools, the one called first is `Is` |
  | `Before = @{ Is; Then }` | a command matching the regex `Is` comes before any command matching `Then` (commands are the `os.execute` text and `git <operation>` for `code.git`) |
  | `Question` | an info.request asks a question with this header |
  | `FirstOption` | the first option label of the first question matches this regex |
  | `ChatQuestion` | the turn ends with a question in chat and no info.request (`$true`), or not (`$false`) |
  | `Says` | the final reply matches this regex (case-insensitive) |
  | `Tool` / `NoTool` | this tool is, or is not, called |
  | `NoWrite` | no attempted write matches this glob |
  | `NoMarker` | no attempted write carries a Sophon marker value (the `Markers` of `design.psd1`) |
  | `MaxCalls = @{ Tool; Max }` | this tool is called at most `Max` times |

- `Uses` ties a scenario to the wording it depends on: each entry is a quoted text and the fragment (or the
  agent's role text) that must contain it, such as a switch word, a question label or an opt-out phrase. A
  relabel then breaks the lint and not the sweep.
- `Pending = 'M<n>'` marks a row whose agent, rule or used text lands in a later milestone of the 3.0 plan. The
  lint reports what is missing as a note; the field is deleted in the commit that lands it, and a release
  build (`-Release`) fails while any `Pending` remains.

### Pressure scenarios and the ship rule

A pressure scenario names exactly three pressures from: time, sunk-cost, authority, economic, exhaustion,
social, pragmatic. Its `Rule` is an id of the family's `Method.Rules`, and its control arm is the same agent
composed without that rule (`Compose-AgentSouls.ps1 -Omit <rule>`). It never contains an opt-out phrase ("just
build it", "no questions"), because those legitimately switch discovery off; ACC-04 tests that.

**The ship rule, fixed in advance.** A rule's text ships as tested when the treatment arm passes at least 4 of 5
runs and the control arm fails at least 3 of 5.

- If the control passes, the scenario is not tempting enough: reword it once. If the control still passes,
  the excuse table is a candidate for cutting; record the negative result and the owner decides.
- If the treatment fails, add one excuse row for the excuse the agent gave, in its own words, and run again.
  After two failed rewrites the owner decides.

A release sweep is the pressure tier in both arms five times, the four lead acceptance prompts three times and
the other acceptance prompts once, and the automated design and voice scenarios three times.

## 2. The scenario lint

```powershell
pwsh -NoProfile -File tests/agents/evals/Invoke-AgentEvals.ps1 -ValidateOnly            # daily and in CI
pwsh -NoProfile -File tests/agents/evals/Invoke-AgentEvals.ps1 -ValidateOnly -Release   # the release gate
```

It needs no Sophon CLI and no Gateway, and prints the scenario counts per tier, the pending rows per milestone
and one `NOTE` or `ERROR` line per finding. It checks:

- ids are unique across the four files and `scenarios.md`, with the tier's prefix;
- the agent is in a roster;
- a pressure row names a registered rule its agent carries, and every registered rule has a pressure row
  (skipped with a note while the family has no `Method` key);
- exactly three known pressures, `Control = 'must-fail'` and no opt-out phrase in a pressure row;
- the fixture, its patches and the brief exist;
- every `Uses` text is in its fragment or role text;
- no run of 40 characters from a turn (or from a brief after its runtime opening) occurs under `agents/` or
  `build/agent-src/`, so a scenario cannot leak into a package;
- no fixture names an agent of the family or these tests.

`tests/agents/Test-AgentPackages.ps1` (section M) runs the lint's own cases
(`tests/agents/fixtures/evals/cases.psd1`), the scorer on two recorded transcripts and on in-memory ones (the
PRS-EV1 and PRS-EV2 events, a cut `argsPreview`), the runner's exec line, package choice, SOUL hash and run-error
rule, the `-Run` Gateway guard, the lint on these files, every fixture and patch as a git workspace, and
`-Prepare` on two scenarios.

## 3. Running by hand

This always works, whatever the headless runner can do.

**Prepare a throwaway Sophon.** Start a throwaway Gateway with `SOPHON_DATA_DIR` set to an empty folder and on
a port of its own (not 8080 or 8470), and point the CLI at it with `SOPHON_GATEWAY_URL`, so the tests never touch
your real agents, memory or approvals. A separate data folder alone is not enough: `sophon agents install` and
`sophon exec` talk to the Gateway named by `SOPHON_GATEWAY_URL` or by `~/.sophon/config/cli.json`, whatever
`SOPHON_DATA_DIR` says, so without the URL they reach your normal Gateway. Make sure the injection-scan mode is
not off: the install preview must show a scan verdict. Sophon CLI 2.2.x on PATH (`sophon --version`).

**Build and install the packages** you will upload, not the source folders:

```powershell
$env:SOPHON_DATA_DIR = '<throwaway folder>'
$env:SOPHON_GATEWAY_URL = '<throwaway Gateway URL>'   # the Gateway started with that data folder
pwsh -NoProfile -File build/Build-AgentPackages.ps1
Get-Content dist/agents/SHA256SUMS

sophon agents install --file dist/agents/lead-developer-3.0.0.sophon-agent --id lead-developer --show-files
# Turn on Restrict to allow list for Lead Developer (Dashboard → Agents → Lead Developer → Delegation) and save:
# --allow-delegation-from adds to the list only while it is on.
sophon agents install --file dist/agents/developer-3.0.0.sophon-agent --id developer --allow-delegation-from lead-developer --show-files
# ... the same for every other companion of the roster
sophon agents install --file dist/agents/artifact-creator-3.0.0.sophon-agent --id artifact-creator --show-files
```

Name the package by its version: `dist/agents` can hold an older build too, and `<id>-*` would pick the first
by name. `--id` installs over an agent of that id instead of under the next free one. In a console the install
asks before it goes ahead; a script (or any console that is not interactive) must pass `--yes`.

For each install preview: the verdict is clean, with no possible-secret finding; no `expects tool:` line
appears and the TOOLS.md block shows the package's pins; the agent id equals the package name. Then check that
**Effective targets** for Lead Developer lists every companion, and set effort high where the roster says so:
`sophon agents models <id> --effort high`. Leave allowed Medium-risk calls for the session at the default (off),
so the card counts are comparable.

**Build a control arm** for a pressure scenario:

```powershell
pwsh -NoProfile -File build/Compose-AgentSouls.ps1 -Agents developer -Omit test-first -OutDir <tmp>/ctl
Copy-Item agents/developer <tmp>/pkg/developer -Recurse
Copy-Item <tmp>/ctl/developer/SOUL.md <tmp>/pkg/developer/SOUL.md -Force
sophon dev build <tmp>/pkg/developer --output <tmp>/out
sophon agents install --file <tmp>/out/developer.sophon-agent --id developer-ctl-test-first
```

A control agent is installed once per agent and rule, as `<id>-ctl-<rule>`: each control leaves out a
different rule, so the control of one rule never serves as the control of another.

`Invoke-AgentEvals.ps1 -Prepare` does the offline part for you: per scenario a fixture copy that is already a
git repository with its setup applied, the control package for each pressure scenario whose rule is
registered, the install lines and the exact turns in `turn-<n>.md`. It installs nothing.

```powershell
pwsh -NoProfile -File tests/agents/evals/Invoke-AgentEvals.ps1 -Prepare -Scenario PRS-TF1 -OutDir <tmp>/evals
```

**Run one scenario.** Run `sophon` in the prepared workspace and `/trust` it, so the session is bound and
trusted (the first turn shows the "Git state of the workspace" block). For a pressure scenario, choose the
control agent with `/agent <id>-ctl-<rule>`, paste turn 1 unchanged, and record the first tool call, what the agent
chose and the excuse in its own words. Start a new chat, choose the real agent and send the same message.
Start a new chat for every scenario, so switch and consent words do not carry over, and prepare a fresh
workspace for each.

The minimum by hand per release is one control and one treatment chat per pressure scenario, each acceptance
prompt once, the design and voice scenarios once, and the smoke scenarios in `scenarios.md`.

**Smoke scenarios** (`scenarios.md`) need a small repository with a remote; the fixtures serve. Answer **Keep
local** at the git menu unless a scenario says otherwise, and return the repository to its baseline between
scenarios yourself: the agents never reset or delete branches unless asked. While you run D2, L3 and Q1, also
confirm the assumptions that were accepted without a run:

- a pathspec commit keeps files you staged yourself out of the agent's commit;
- PowerShell 5.1 quote stripping does not break a commit message (the agents prefer cmd);
- cmd `( … & git stash pop)` grouping restores a stash under the bound shell;
- gh and Git Credential Manager authenticate from the bound shell (with `gh auth setup-git` done first);
- an SSH remote on Windows. For these two, repeat L3's git menu once with the push option against a scratch
  remote, never a shared one.

## 4. The headless runner

```powershell
pwsh -NoProfile -File tests/agents/evals/Invoke-AgentEvals.ps1 -Run -DataDir <throwaway folder> -GatewayUrl <throwaway Gateway URL> -Tier pressure -Repeat 5 -MaxRuns 140
```

`-Run` follows the stream-json contract of Sophon CLI 2.2.2. Spike 5
([`docs/plans/2026-11-24-agents-v3-spike-results.md`](../../../docs/plans/2026-11-24-agents-v3-spike-results.md),
S5 and "Runner defects") checked five facts about `sophon exec` by hand, and the runner follows what it found:

1. `--output-format stream-json` carries each tool call with its arguments (each argument preview is cut at
   2,048 characters; the scorer still reads the path, command and question headers of a cut one).
2. A card or a question does not end the run: the card is rejected with feedback and the question skipped
   (`Answer: (skipped)`), and the turn goes on. The stream shows it (`approval.requested`, the skipped answer,
   a result with `status: denied` and exit 2); nothing waits for the timeout. Only the plan card in plan mode
   ends the turn (`status: success`, the plan printed as text). `denied.questions` counts calls, not questions.
3. `--agent` accepts an agent installed from a file, and `--workspace` with `--trust-workspace` binds the
   fixture copy, but only when `sophon exec` runs with that copy as its current folder: the CLI sends its
   current folder as the binding's cwd, and from anywhere else the Gateway refuses the turn
   (`workspace_refused`).
4. `--session` continues a session for multi-turn scenarios.
5. A run's cost is in the result line (`usage.costUsd`; $0.08 to $0.33 per run in the spike).

For each scenario, arm and repetition the runner: copies the fixture, applies the setup and commits; builds the
control package; installs each arm once with `sophon agents install --file <package> --id <id> --yes` (the
treatment is `dist/agents/<id>-<version>.sophon-agent` of the manifest version, under the agent's own id, so a
lead's delegate calls still reach its companions); pipes each turn on stdin to `sophon exec --agent <id>
--workspace <copy> --trust-workspace --include-agents --output-format stream-json --timeout 300 -`, run from
inside the copy; never passes `--allow`, so nothing in the copy changes and every question goes unanswered;
saves each turn's stream as `turn-<n>.ndjson` and its stderr as `turn-<n>.stderr`; and scores the attempted
calls and the text. `--include-agents` puts a delegated child's events in the stream; the scorer keeps them
apart from the agent's own moves.

Exit 2 (`denied`) is a normal outcome and is scored. Exit 1, a result status of `failed`, `timeout` or
`connection_error`, or no result line at all is a **run error**: the row is not scored, a later turn of the
scenario is not sent, and the run counts as an error in the summary and in the exit code. `summary.md` holds
the CLI version, the SOUL hash (read from the SOUL.md inside the installed package), and per scenario and arm
the passes, scored runs, errors, cards, questions and delegate calls, and lists the flagged transcripts (a run
error, a failed treatment, a passed control) for a person to read.

**Cleanup.** The runner archives every session it created (`sophon sessions archive <id>` needs no prompt).
`sophon agents delete` and `sophon sessions delete` always ask y/n and have no `--yes`, so a script without a
console cannot run them: the runner writes them at the end of `summary.md` for a person to run in a console.
The spike deleted them by typing `y` through a pseudo-console. Stopping the throwaway Gateway and removing its
data folder removes everything at once.

Guards: it refuses to run when `CI` or `GITHUB_ACTIONS` is set, requires `-DataDir` and refuses the default
data folder, requires `-GatewayUrl` (or `SOPHON_GATEWAY_URL`) and refuses the `gatewayUrl` of
`~/.sophon/config/cli.json` and the ports 8080 and 8470, sets `SOPHON_GATEWAY_URL` for every child call, runs one
repetition by default, and stops before starting when the planned runs exceed `-MaxRuns`
(default 30). Manual scenarios, `SameRunAs` rows, rows whose agent is not in a roster yet and rows that need the
reference skill are skipped with a reason. A pressure scenario whose rule is not registered yet runs its
treatment arm only.

Start the throwaway Gateway yourself before `-Run`, with `SOPHON_DATA_DIR` pointing at the folder you pass as
`-DataDir`: the runner checks the URL, not which data folder that Gateway uses. The CLI still records its
session list in `~/.sophon/config/cli-sessions.json`, keyed by the Gateway URL.

## 5. What to record

For each scenario and arm: pass or fail, the first tool call, the number of approval cards, the number of
agent.delegate calls, the excuse in the agent's own words when it broke a rule, and anything that surprised
you. Record the model, the CLI version and the SOUL hash with every result, and run the sweep again when the
default model changes.

Per release, `results/<version>.md` holds the summary tables:

| Id | Arm | Passed | Runs | First moves | Notes |
|---|---|---|---|---|---|
| PRS-TF1 | treatment | | | | |
| PRS-TF1 | control | | | | |

The baselines against the 2.1.0 packages are recorded before the 3.0 text is written, so each new rule is
measured against what the agents already did.
