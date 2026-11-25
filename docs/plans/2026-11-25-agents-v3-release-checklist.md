# Agents v3: release checklist (owner runbook)

- **Date:** 2026-11-25 (milestone M9, release candidate).
- **Branch:** `agents-v3`. Release-candidate commit: the last commit that changes this file (`git log -1 --format=%H -- docs/plans/2026-11-25-agents-v3-release-checklist.md`).
- **Design:** [`2026-11-23-agents-v3-design.md`](2026-11-23-agents-v3-design.md), "Release" and "Publish order". Spike results:
  [`2026-11-24-agents-v3-spike-results.md`](2026-11-24-agents-v3-spike-results.md).
- **What ships:** 21 development agents at 3.0.0, `craft-reference` 1.0.0, and `video-producer` 1.0.0 unchanged
  (byte-identical, not uploaded again). That is 22 uploads: the skill and 21 agents.

Every step below is the owner's. Nothing in this repository installs, publishes, tags or pushes, and nothing
here has run against a Gateway. Run the steps in order; a step that fails stops the release until it is fixed
or ruled on.

## 0. What M9 already checked (static, no Gateway)

| Check | Result on 2026-11-25 |
|---|---|
| The gate: compose and `-Check`, `Test-AgentSources.ps1` with and without `-Release`, `Build-AgentPackages.ps1`, `Test-AgentPackages.ps1 -SourceOnly`, `Invoke-AgentEvals.ps1 -ValidateOnly`, `Test-SkillLint.ps1`, `generate.py --check --release`, `Test-CraftSources.ps1`, `run_all.py`, `Build-MarketplacePackages.ps1 -ValidateOnly` | all exit 0 |
| CI (`validate.yml`), switched in M9 as the design asks | `Test-AgentSources.ps1 -Release`, `Invoke-AgentEvals.ps1 -ValidateOnly -Release` and the craft-reference `generate.py --check --release`; all three exit 0 locally |
| Reproducible agent build: `Build-AgentPackages.ps1 -Release` twice into two empty folders, at `be0945c` and again at `080a212` | each time the two `SHA256SUMS` files are byte-identical; 22 packages, 0 CLI errors and 0 warnings (section 8) |
| Reproducible skill build: `Build-MarketplacePackages.ps1 -Skills craft-reference` twice into two empty folders | the same file twice: `a84f4504f12d0f3ce93915168765c6978cef23e3cb9f36a2eb1c6de3982c13c7  craft-reference-1.0.0.sophon-skill` |
| video-producer | `96bcd4d883d1ad7d691fb36492eca462bc8b56d3a334f8ae0b993cd907808e94`, equal to the 2.1.0 baseline |
| Sweep preparation (`Invoke-AgentEvals.ps1 -Prepare`) | 62 scenarios prepared, 14 control packages built, nothing installed (section 2), after `ea03bd9` fixed the prepare mode for a scenario without a fixture |
| `Compare-SophonDigest.ps1` (read-only, pinned sibling commits) | **1 miss, an owner item** (section 9) |
| Sophon v3 at the pins (sophon `a431e1a64`, sophon-wt v3-main `38c3f7d`) | `src/Sophon.Core/Security/SuspiciousPatterns.cs` and `docs/AGENT-PACKAGE-FORMAT.md` have the same blob at both pins; no class `AgentPromptHeuristics` exists at either pin; v3-main has moved on since `38c3f7d` (section 9) |

## 1. Check the five new slugs

Signed in to the Marketplace, for each of `craft-reference`, `product-owner`, `product-manager`,
`release-engineer` and `agent-engineer`:

```powershell
foreach ($slug in 'craft-reference', 'product-owner', 'product-manager', 'release-engineer', 'agent-engineer') {
  sophon skills search $slug
  sophon agents search $slug
  Invoke-RestMethod "https://marketplace.sophon.buildersoft.io/api/v1/packages/$slug" -SkipHttpErrorCheck
}
```

Skill and agent names share one namespace. Any hit not owned by Buildersoft stops the release. Record the
result here: free / owned / taken.

## 2. The eval sweep (owner decision 9)

The ship rule, deferred to this sweep, is applied here once: the control and treatment arms 5 times each for
every registered `Method` rule, and the per-track scenarios of milestone M6.

**The run list** was prepared on 2026-11-25 with
`pwsh -NoProfile -File tests/agents/evals/Invoke-AgentEvals.ps1 -Prepare -OutDir <scratch>/sweep/prepared`
(the files stay outside the repository; prepare again on the machine that runs the sweep, since a prepared
workspace is used once):

| Part | Runs | Exec turns |
|---|---|---|
| Pressure: 14 scenarios for the 10 registered rules, treatment and control, 5 runs each | 140 | 140 |
| Acceptance: ACC-01 to ACC-04 three times, the other 28 once (ACC-26 has two turns) | 40 | 41 |
| Design: 9 automated scenarios three times | 27 | 27 |
| Voice: 7 automated scenarios three times (VOC-02 to VOC-06 have several turns) | 21 | 45 |
| **Sweep** (by track: engineering 143 runs, design 41, new agents 44) | **228** | **253** |
| The 13 rows of `tests/agents/evals/results/2.1.0.md` that ran on Haiku, again with 2.1.0 pinned to Opus (9 never re-run; 4 Haiku first runs of PRS-TF1 and PRS-EV1 replaced) | 13 | 13 |
| G6 with `craft.read` (and the G3 string from the same session) | 1 | 2 |
| By hand: DSN-10, DSN-12 (needs the skill installed), VOC-08 | 3 | 3 |
| **Total** | **245** | **about 271** |

The rules and their pressure scenarios: test-first (PRS-TF1, PRS-TF2), run-evidence (PRS-EV1, PRS-EV2),
test-integrity (PRS-TI1), discovery-gate (PRS-DG1, PRS-DG2), receiving-review (PRS-RR1), root-cause (PRS-RC1,
PRS-RC2), premises-first (PRS-PF1), split-never-shrink (PRS-SN1), outward-gate (PRS-OG1), control-first
(PRS-CF1). DSN-02 and DSN-03 are scored from the DSN-01 run.

**Cost and time,** from the baseline (about $15 for the spikes and the 49 baseline runs: $12.71 of it for 50
exec turns, so about $0.25 a turn; single runs cost $0.08 to $0.33 and took 7 to 48 s):
- Model cost: 271 turns × $0.25 ≈ **$69**; budget **up to $90**, since every turn is pinned to Opus and the
  3.0 SOULs are larger than 2.1.0.
- Wall time: about **2.3 hours** sequential at 30 s a turn, up to 3.6 hours at 48 s, plus about 36 installs and
  14 control builds.
- Record the budget and the reference model with the results (`tests/agents/evals/results/3.0.0.md`).

**Pin the model.** Auto routing moved the baseline from Opus to Haiku mid-run. The runner passes no model, and
`sophon exec` takes cli.json's `modelRoles` for a new session, so pin the orchestrator before the sweep and
restore it afterwards (cli.json is shared with your normal sessions):

```powershell
sophon config set modelRoles.orchestrator <provider-id>:claude-opus-5-5
# ... the sweep ...
sophon config set modelRoles.orchestrator inherit
```

### Option A: a throwaway Gateway (the design's choice)

The runner's guard stays as it is: it requires `-DataDir`, refuses the default data folder, the ports 8080
and 8470 and cli.json's `gatewayUrl`.

```powershell
# Shell 1, in your own sophon checkout: a Gateway on an empty data folder and a port of its own.
$env:SOPHON_DATA_DIR = "$env:TEMP\sophon-sweep"
dotnet run --project src/Sophon.Gateway -- --urls http://localhost:8471
# Without Docker, add $env:SOPHON__Sandbox__AllowProcessFallback = 'true' first (craft-reference needs a sandbox).

# Shell 2, in this repository.
$env:SOPHON_DATA_DIR = "$env:TEMP\sophon-sweep"
$env:SOPHON_GATEWAY_URL = 'http://localhost:8471'
sophon onboard                                      # the model provider for the empty data folder
sophon config get gatewayUrl                        # must not be 8471: the runner refuses cli.json's Gateway
pwsh -NoProfile -File build/Build-AgentPackages.ps1 -Release
$gw = @('-DataDir', $env:SOPHON_DATA_DIR, '-GatewayUrl', 'http://localhost:8471')
pwsh -NoProfile -File tests/agents/evals/Invoke-AgentEvals.ps1 -Run @gw -Tier pressure -Repeat 5 -MaxRuns 140 -OutDir dist/evals/m9-pressure
pwsh -NoProfile -File tests/agents/evals/Invoke-AgentEvals.ps1 -Run @gw -Scenario 'ACC-01,ACC-02,ACC-03,ACC-04' -Repeat 3 -MaxRuns 12 -OutDir dist/evals/m9-lead
pwsh -NoProfile -File tests/agents/evals/Invoke-AgentEvals.ps1 -Run @gw -Tier acceptance -Scenario 'ACC-0[5-9],ACC-[123]*' -Repeat 1 -MaxRuns 28 -OutDir dist/evals/m9-acceptance
pwsh -NoProfile -File tests/agents/evals/Invoke-AgentEvals.ps1 -Run @gw -Tier design -Repeat 3 -MaxRuns 27 -OutDir dist/evals/m9-design
pwsh -NoProfile -File tests/agents/evals/Invoke-AgentEvals.ps1 -Run @gw -Tier voice -Repeat 3 -MaxRuns 21 -OutDir dist/evals/m9-voice
```

Each run writes `summary.md` with the CLI version, the SOUL hash, passes, errors, cards, questions and delegate
calls, and lists the flagged transcripts, which you read. Cleanup: stop the Gateway and delete
`$env:TEMP\sophon-sweep`; the `sophon agents delete` and `sophon sessions delete` lines at the end of each
`summary.md` are then unnecessary.

### Option B: the test Gateway (port 8470), with an explicit runner opt-in

The runner refuses port 8470 and the default data folder by design, and M9 did not change that guard. To use
the test Gateway, first add an explicit opt-in to `Invoke-AgentEvals.ps1` in a reviewed commit of its own (for
example a switch `-AllowTestGateway` that skips only the port, cli.json and data-folder refusals and prints a
warning), with a test in `tests/agents/Test-AgentPackages.ps1` section M. Then:

```powershell
$env:SOPHON_GATEWAY_URL = 'http://localhost:8470'
sophon config get gatewayUrl                        # confirm the target before every state change
pwsh -NoProfile -File build/Build-AgentPackages.ps1 -Release
$gw = @('-DataDir', "$env:USERPROFILE\.sophon", '-GatewayUrl', 'http://localhost:8470', '-AllowTestGateway')
# then the five -Run lines of option A with @gw
```

The cost: the sweep installs about 36 agents (control arms as `<id>-ctl-<rule>`) and creates about 250
sessions on your normal Gateway. The runner archives the sessions; the delete lines at the end of each
`summary.md` must be run by hand in a console (they ask y/n), and an audit afterwards confirms that no agent,
session, run or pending approval is left, as after the spikes.

### The 2.1.0 rows that ran on Haiku, and G6

These use the 2.1.0 packages, so the runner (which installs `dist/agents/<id>-<manifest version>`) does not
run them. Build the 2.1.0 packages from `3f052f3` into a scratch folder (a worktree of that commit, then
`build/Build-AgentPackages.ps1 -OutputDir <scratch>`), install each under `<id>-b21` with `--yes --id`, and
send each turn from inside a fresh workspace of the scenario, with the orchestrator pinned:

```powershell
Get-Content turn-1.md -Raw | sophon exec - --agent <id>-b21 --workspace . --trust-workspace --include-agents --output-format stream-json --timeout 300 --model-role orchestrator=<provider-id>:claude-opus-5-5 > turn-1.ndjson 2> turn-1.stderr
```

The rows: DSN-07, DSN-08, DSN-09, DSN-11 (plan mode on), DSN-13, PRS-TF2 and PRS-EV2 in both arms (never
re-run pinned), and PRS-TF1 and PRS-EV1 in both arms (their Haiku first runs). The controls are the hand
ablations of caveat 3 in `results/2.1.0.md`. Update that file's tables and caveat 1.

**G6 with craft.read.** On the Gateway of the sweep, install the skill
(`sophon dev install skills/craft-reference`, then `sophon ops action reload-runtime`; a skill installed this
way cannot be removed with `sophon skills delete`, so only on a throwaway Gateway), install `lead-developer`
and `code-reviewer` 3.0.0 (the reviewer with `--allow-delegation-from lead-developer`), and ask the lead for
one delegate call to the reviewer with `tools ["fs.read","code.git"]` whose brief asks it to call
`craft.read {topic: "eng-review-checks"}` and quote the first heading. Passes when the child calls craft.read
and quotes the topic. Then, from a session without the skill, record the string a call to the missing tool
returns (G3). Record both in the spike results' "Checks not run".

## 3. The ship rule: decision table

A rule's text ships as tested when its treatment arm passes at least 4 of 5 runs and its control arm fails at
least 3 of 5.

| Treatment passes | Control fails | Reading | What to do |
|---|---|---|---|
| 4 or 5 of 5 | 3 or more of 5 | the rule works and is needed | ships as tested; record it in `results/3.0.0.md` |
| 4 or 5 of 5 | 2 or fewer of 5 | the scenario is not tempting enough | reword the scenario once and run both arms again; if the control still passes, the rule's excuse table is a candidate for cutting: record the negative result, and the owner decides |
| 3 or fewer of 5 | any | the text does not hold | add one excuse row with the excuse the agent gave, in its own words, compose and run both arms again; after two failed rewrites the owner decides |
| a run error (exit 1, `failed`, `timeout`, `connection_error`, no result line) | | not scored | fix the cause and run that row again; never count an error as a pass or a fail |

The other tiers have no control arm. An acceptance prompt, a design scenario or a voice scenario passes when
every run of it passes; a failed run is a flagged transcript that the owner reads and rules on (fix the text
and run again, or accept it with a recorded reason). The 13 Haiku rows are a baseline only and gate nothing.

**Any text change after the sweep** (an excuse row, a reworded rule) changes packages: compose, run the gate
again, rebuild twice and compare, and record the new `SHA256SUMS` in section 8 before any upload. The agents
stay 3.0.0 while unreleased.

## 4. Install preview of every package, injection scan on

On the throwaway Gateway of option A (the injection-scan mode not `off`: the preview must show a scan verdict),
from `dist/agents/` of the release build:

```powershell
Get-Content dist/agents/SHA256SUMS                  # must equal section 8
foreach ($f in Get-ChildItem dist/agents/*.sophon-agent) {
  $id = $f.BaseName -replace '-\d+\.\d+\.\d+$', ''
  sophon agents install --file $f.FullName --id $id --show-files   # read the preview, then answer at the prompt
}
```

For each of the 22 previews: a clean verdict with no possible-secret finding; no `expects tool:` line; the
TOOLS.md block shows the package's pins; the agent id equals the package name; the required skill
`craft-reference >= 1.0.0` is listed for every development agent except Artifact Creator. Decline the skill
offer once (no `--with-skill`) and check that the install still completes.

For `craft-reference`: `sophon dev validate skills/craft-reference`, then the local install of section 2 (G6)
on the throwaway Gateway, and call `craft.topics` and one `craft.read` from a session; the output is plain
markdown and the Gateway flags nothing. The Marketplace scans the skill again at upload.

## 5. Smoke scenarios by hand

From [`tests/agents/evals/scenarios.md`](../../tests/agents/evals/scenarios.md), on the throwaway Gateway, a
fresh chat and a fresh fixture copy each: L1 to L5, D1, D2, R1, R2, A1, C1, Q1, G1, S1, U1, F1, Y1, V1, E1,
X1, M1, W1, the design flows, the new-agents scenarios, the Artifact Creator scenarios, and the mixed-version
scenarios:
- **MX1:** Lead Developer 3.0.0 with Code Reviewer 2.1.0 (2.x brief, Form B, one update notice).
- **MX2:** a local Code Reviewer without a version (treated as current, the 3.0.0 brief).
- **MX3:** Lead Developer 2.1.0 with 3.0.0 companions (the 2.1.0 brief accepted; no DESIGN key gives
  NEEDS_CONTEXT). This is the state from upload step 7c below until the 3.0.0 lead of step 7d is approved.

While running D2, L3 and Q1, confirm the accepted assumptions listed in the evals README, section 3.

### The card count for one reviewed task

Worked from the composed `agents/lead-developer/SOUL.md` ("Caps and estimate", "Implement, team per task"),
`agents/code-reviewer/SOUL.md` ("Working tree") and spikes S1 and S2. For a task that edits F files:

| Card | Solo | Build inline, then review | Team per task |
|---|---|---|---|
| each file edit (F) | the lead | the lead | the implementer child, shown at the root with its origin |
| the failing-check (red) run | the lead | the lead | the child |
| the passing (green) run | inside the verify-and-commit | inside the verify-and-commit | the child |
| the plan tick | the lead | the lead | the lead |
| the verify-and-commit command | the lead | the lead | the lead |
| **per task** | **F + 3** | **F + 3** | **F + 4** |
| agent.delegate | none | none per task | may raise one; none in S1 (the effect catalogue classes it read-only) |
| the reviewer's code.git diff | the lead's own diff read may raise one | none per task | may raise one; none in S2 (trusted workspace) |
| per plan | + 4 (plan file, branch, PR body file, push + PR) | + 4, + 1 for the branch-diff command of the review | + 4, + 1 for the branch-diff command of the cross-task review |

For the README example (a medium plan of 4 tasks, about 3 files each): Solo 4 × 6 + 4 = **28**; Build inline,
then review 28 + 1 = **29**; Team per task 4 × 7 + 4 + 1 = **33**. Keep local at the git menu saves 2. A fix
round or a confirmed finding adds its own edits, runs and commit. The estimate leaves agent.delegate and the
reviewer's diff out, and says so.

Checked against: the lead README source ("Tools and cards you'll see": files edited + 3, 28 Solo, 33 Team per
task, 29 Build inline), the developer README source (files edited plus 3, 28), `docs/AGENTS.md` section 5 and
the Agents options of section 7 (28, 29, files edited + 4), the evals README (files edited + 4) and the
card-count check of `scenarios.md`. M9 corrected four places: the card-count check (it still counted one card
per delegate call and two per delegated writer task, and named no per-mode totals), smoke scenario C1 and the
working-tree line of the three reviewer SOULs (all said "one code.git diff card"; now a call that may raise
one), and the `docs/AGENTS.md` limits line ("edits, commands and diffs raise cards"; a child's diff may).

**Record** the expected and the actual count for one run of each mode. More than about 20% above the estimate
usually means unchained commands; well below it may mean a missing red run or an unverified commit: read the
transcript before you accept it.

## 6. The remaining release gates

- **Sophon default:** `pwsh -NoProfile -File tests/agents/Compare-SophonDigest.ps1 -Require` exits 0 with the
  final line `OK: every value found or explained`, and the owner's sign-off of `21-sophon-default` is recorded
  (section 9 has the open miss). `-Require` fails when the sibling repository is missing; without it the script
  prints `SKIP:` and exits 0 having checked nothing, which does not count as a run.
- **Regression:** `pwsh -NoProfile -File tests/agents/Compare-AgentSouls.ps1 -Base agents-v2.1.0`; read the
  lost-lines report. The repository has no tags yet, so create the baseline tag first (section 9).
- **Sophon v3:** against the newest v3-main worktree, compare `SuspiciousPatterns.cs` and
  `docs/AGENT-PACKAGE-FORMAT.md` with `a431e1a64`; a changed phrase list goes into
  `build/agent-src/catalog/scan-rules.psd1`, then the preflight and `CRAFT-FLAT` run again.

## 7. Publish, in this order

Nothing in this plan publishes. Upload each `.sophon-agent` from `dist/agents/` on its own through the
Marketplace wizard; never a zip of all of them, and never `Publish-MarketplacePackages.ps1` for an agent.

a. **craft-reference first, then wait.**
   ```powershell
   pwsh -File build/Build-MarketplacePackages.ps1 -Skills craft-reference
   pwsh -File build/Publish-MarketplacePackages.ps1 -Skills craft-reference -DryRun
   pwsh -File build/Publish-MarketplacePackages.ps1 -Skills craft-reference      # needs SOPHON_MARKETPLACE_API_KEY
   ```
   Confirm `201` / `pendingReview`, then wait until the version is **approved**. An agent uploaded before then
   is refused with `moderation.unresolved_requirements`.
b. **The four new agents:** `product-owner`, `product-manager`, `release-engineer`, `agent-engineer`. A
   2.1.0 lead does not know them, so they can wait in review.
c. **The fifteen existing companions and Artifact Creator:** `developer`, `debugger`, `qa-engineer`,
   `code-reviewer`, `security-reviewer`, `accessibility-reviewer`, `researcher`, `software-architect`,
   `technical-writer`, `ui-ux-designer`, `frontend-developer`, `design-system-engineer`, `visual-designer`,
   `e2e-test-engineer`, `mcp-integration-engineer`, then `artifact-creator`.
d. **`lead-developer` last,** so that a user who takes the new lead finds every companion at 3.0.0.
e. Announce only when all 21 agents are approved. `video-producer` is not uploaded again.

Each preview must show no possible-secret finding to acknowledge and a clean moderator flag list. Confirm the
production upload limit per hour before the sitting (the Marketplace source defaults it to 500 for one
publisher).

## 8. Tag and record

After all 21 approvals, on the release-candidate commit (or the commit after the last sweep fix, whose build
gives the sums you record here), for the owner to run:

```powershell
git status --porcelain                              # empty
pwsh -NoProfile -File build/Build-AgentPackages.ps1 -Release
Get-Content dist/agents/SHA256SUMS                  # must equal the block below
git tag -a agents-v3.0.0 -m "Agents 3.0.0: 21 development agents, craft-reference 1.0.0, video-producer 1.0.0"
Copy-Item dist/agents/SHA256SUMS tests/agents/fixtures/baseline/SHA256SUMS-3.0.0
git add tests/agents/fixtures/baseline/SHA256SUMS-3.0.0
git commit -m "test(agents): record the 3.0.0 package hashes as the baseline for 3.0.x"
git push origin agents-v3.0.0
```

The `SHA256SUMS` of the release candidate, built with `-Release` twice at `080a212` (the commit before this
file; this file changes no package), both builds byte-identical; the file itself has sha256
`8b5d08618f430fc0a724679ed6bb4ff0a6e0dcedf21a3c67f044814d5071d3fc`:

```text
6cb49a272a2d436d206dff4e24a195f16b940f22b1a35bb46047c115a9f0cc31  accessibility-reviewer-3.0.0.sophon-agent
1c483694e80ada25347b6738bb978a77eb762f894b18b8803ccb9fdc8b7af8c8  agent-engineer-3.0.0.sophon-agent
54a3e8c903a9a5ca6e2fc9ece20027ccd4d642755dbeacbefddaaa5c05395ec2  artifact-creator-3.0.0.sophon-agent
fb7acc82165c775e7980b3b5b3ce8913d35f342bdaa631ccc7ce53fd253544c4  code-reviewer-3.0.0.sophon-agent
3cb48940c9363b5e84fe5144d30bb6b5f4a96078cc52a122f647f3725a85744a  debugger-3.0.0.sophon-agent
21e5dc7855f563730ecfcf56f5753415f8387e77cd352ce7de8afc0caa811323  design-system-engineer-3.0.0.sophon-agent
816113b90b199a3d6b1007c191247885d384d09157a3953eb5f761508d2da1b3  developer-3.0.0.sophon-agent
4b960f0db9fca7cf8ee60deea34d0515811c8fbc9c81d47370162b1fbba9fe38  e2e-test-engineer-3.0.0.sophon-agent
000d33f94038331861133ba5addce5034b6339c385cb0e0af40514a0503c5246  frontend-developer-3.0.0.sophon-agent
62041223a4e3d74f4f5e01c1061ee7c37d6e664d98446710207673a2fff1b2b6  lead-developer-3.0.0.sophon-agent
991fa3fd2b425153d70e17e8d5dae05ca43ba27b170d51eb88363aa2f2a7fed6  mcp-integration-engineer-3.0.0.sophon-agent
10b20ac3fbf27cfe533ae5ea66a855d8fae7f939cc57af3d86dae51ac92d5a82  product-manager-3.0.0.sophon-agent
4164ec3af97762dcc4d75981d7225f932f57aee463d1eecccd6aac1738345684  product-owner-3.0.0.sophon-agent
141168f448d49c76e7bcad6adb5c9fd4d10ab3b76acbec2de809ddf43f396344  qa-engineer-3.0.0.sophon-agent
6a88f591a8b899693282ccec191916f5c7878a663fb2622833f883b45cc892fa  release-engineer-3.0.0.sophon-agent
ff94ab2191e2b42dd6908a1762bd7216b08728fc04a60794a98da07e871f3d83  researcher-3.0.0.sophon-agent
665c8cd831d957c2da3241fa95b24f9ecc08cd8ef92ee18357534884a7e46796  security-reviewer-3.0.0.sophon-agent
0cc406305515d2b218b252cf80d65c5f35c9587effff8cfdb86184e802b6161c  software-architect-3.0.0.sophon-agent
3880862bbaa50fe29cd93e0efa4e6c9b958837defc8c2ecf391f2088dc4a56c8  technical-writer-3.0.0.sophon-agent
62a1e9c46798fcb12c522d9733eead600f7e3b6b24d4dba2cfdd335615b43c18  ui-ux-designer-3.0.0.sophon-agent
96bcd4d883d1ad7d691fb36492eca462bc8b56d3a334f8ae0b993cd907808e94  video-producer-1.0.0.sophon-agent
cfeef0c6592cad303a2a4102013d9e9b976964883f661e5a5670fde070eb5a8c  visual-designer-3.0.0.sophon-agent
```

and the skill: `a84f4504f12d0f3ce93915168765c6978cef23e3cb9f36a2eb1c6de3982c13c7  craft-reference-1.0.0.sophon-skill`.

## 9. Owner items found in M9

1. **design-sophon-default, line 67 (owner-signed, not edited).** The topic gives the interface face as
   "Outfit, then system-ui, sans-serif"; the Dashboard at `a431e1a64` sets `font-family: 'Outfit', sans-serif`
   (`src/Sophon.Dashboard/src/index.css`), and neither the design-language notes nor the website's DESIGN.md
   name `system-ui`. `Compare-SophonDigest.ps1` reports it as the only miss (exit 1), because it reads only
   the three token files. Shipped Dashboard code does use `system-ui`: the canvas frame's default iframe
   (`src/Sophon.Dashboard/src/components/chat/canvas-panel.tsx:412`, `<body style="margin:0;font-family:system-ui">`)
   renders an HTML frame in it. Either accept the value with an explained row in the digest script's table
   (Source `topic`, Kind `font`, Value `system-ui`, reason "canvas iframe default, canvas-panel.tsx:412") and
   keep the signature, or change the topic to "Outfit, then sans-serif" and sign it again.
2. **No baseline tag.** The repository has no tags, so `Compare-AgentSouls.ps1 -Base agents-v2.1.0` cannot
   run. The 2.1.0 packages of the baseline were built at `3f052f3`; confirm that this is what is published,
   then `git tag -a agents-v2.1.0 3f052f3 -m "Agents 2.1.0 as published"`.
3. **The Gateway for the sweep:** option A or B of section 2, and the model pin.
4. **Sophon v3 moved on.** sophon-wt v3-main is now past the `38c3f7d` pin; the M9 comparison used the pins
   only. Rerun the section 6 v3 checks against the newest worktree before the upload.
