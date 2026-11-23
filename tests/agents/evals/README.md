# Agent smoke evals (manual)

Twenty-two scenarios that exercise the behaviour the static tests cannot: sizing, plan approval,
consent, sub-agent waves, verification, commits, the git menu and each specialist's core move. The
owner runs them once per release, after a clean build and a green
`tests/agents/Test-AgentPackages.ps1`, and before uploading anything. They are in
[`scenarios.md`](scenarios.md), with the card-count check at the end.

In 2.1.0 they are still run by hand in an interactive CLI. A headless runner is deferred to a later
release (see the last section).

## 1. Prepare a throwaway Sophon

- Use a throwaway Gateway, or a separate data folder (`SOPHON_DATA_DIR`), so the evals never touch
  your real agents, memory or approvals.
- Make sure the injection-scan mode is **not off**. The install preview must show a scan verdict.
- Sophon CLI 2.2.x on PATH (`sophon --version`).

## 2. Build and install from the package files

Install exactly what will be uploaded: the built `.sophon-agent` files, not the source folders.

```powershell
pwsh -NoProfile -File build/Build-AgentPackages.ps1
Get-Content dist/agents/SHA256SUMS

sophon agents install --file dist/agents/lead-developer-2.1.0.sophon-agent --show-files
# Now turn on Restrict to allow list for Lead Developer (Dashboard → Agents → Lead Developer →
# Delegation) and save: --allow-delegation-from adds to the list only while it is on.
sophon agents install --file dist/agents/developer-2.1.0.sophon-agent --allow-delegation-from lead-developer --show-files
# ... the same at 2.1.0 for researcher, software-architect, code-reviewer, qa-engineer, debugger,
#     security-reviewer and ui-ux-designer
sophon agents install --file dist/agents/frontend-developer-2.0.0.sophon-agent --allow-delegation-from lead-developer --show-files
# ... the same at 2.0.0 for design-system-engineer, visual-designer, e2e-test-engineer,
#     accessibility-reviewer, mcp-integration-engineer and technical-writer
```

For each install preview:
- the verdict is clean, with no possible-secret finding;
- no `expects tool:` line appears, and the TOOLS.md block shows the package's pins;
- the agent id equals the package name.

Then:
- Check that **Effective targets** for Lead Developer (Dashboard → Agents → Lead Developer → Delegation) lists every companion.
- Set effort high for lead-developer, software-architect, code-reviewer, security-reviewer, debugger and accessibility-reviewer: `sophon agents models <id> --effort high`.
- Leave allowed Medium-risk calls for the session at the default (off) unless a scenario says otherwise, so the card counts are comparable.

## 3. Prepare a small repository

One small git repository is enough for all scenarios:
- a handful of source files;
- a test suite that passes;
- a test command written in its AGENTS.md (see the starter in [`docs/AGENTS.md`](../../../docs/AGENTS.md), section 11).

Each scenario in `scenarios.md` lists the extra setup it needs: a planted bug, an insecure handler, a landing page, a small web app with a component folder and an end-to-end runner, a README with planted mistakes.

- Give it a remote. A GitHub fork lets you see the full menu, but answer **Keep local** everywhere except the one push in section 4.
- Commit the baseline on `main` and note its sha, so you can return to it between scenarios.
- Run `sophon` in the repository, then `/trust`, so the session is bound and trusted. Check that the first turn shows the "Git state of the workspace" block.
- Pick the agent with `/agent <id>`.

**Between scenarios:**
- Start a new chat, so consent words such as "ultracode" do not carry over.
- Return the repository to the baseline yourself: switch back to `main`, delete any `sophon/<slug>` branch, and remove new plan files under `docs/plans/`.
- The agents never reset or delete branches unless asked, so do this in your own terminal.

## 4. What to record

For each scenario, write down:
- pass or fail;
- the number of approval cards you saw;
- the number of agent.delegate calls;
- anything that surprised you.

A copy of this table in the release notes is enough:

| Id | Agent | Result | Cards | Delegations | Notes |
|---|---|---|---|---|---|
| L1 | lead-developer | | | | |

While you run D2, L3 and Q1, also confirm the assumptions that were accepted without a run:
- a pathspec commit keeps files you staged yourself out of the agent's commit;
- PowerShell 5.1 quote stripping does not break a commit message (the agents prefer cmd);
- cmd `( … & git stash pop)` grouping restores a stash under the bound shell;
- gh and Git Credential Manager authenticate from the bound shell (with `gh auth setup-git` done first);
- an SSH remote on Windows. For these two, repeat L3's git menu once with **Push + open PR (Recommended)** against a scratch remote, never a shared one.

## 5. Headless runner (deferred)

`Invoke-AgentEvals.ps1` and eval fixtures are planned for a later release. Notes for it, from the review:

- Pipe the prompt on stdin instead of quoting it on the command line: `Get-Content -Raw prompt.md | sophon exec … -`.
- Headless runs skip every question (`Answer: (skipped)`), so the agents take the non-acting option. Plan approval, consent and the git menu must therefore be scripted or checked as "did not start".
- Allow `os.execute:git checkout` for branch creation, not `git switch`: the agents branch with `git checkout -b`.
- Install the companions through the agent.json form, so each whenToUse carries its `Family role: <id>.` marker.
- The code.git commit, branch and checkout flows stay manual checks.
