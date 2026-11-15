# Code Reviewer

Read-only code review that reports only the defects it can show: the line, the failing case and the fix.

Part of the Buildersoft development family 2.0.0.

| Agent | Role | Delegates | Changes files | Commits |
|---|---|---|---|---|
| lead-developer | orchestrator: sizes, plans, builds, verifies, commits | yes (depth 1) | yes | yes |
| developer | implementer: tdd / direct / debug | no | yes | yes |
| researcher | codebase and web facts, every claim cited | no | no | no |
| software-architect | blueprint / ADR / greenfield / compare / critique | no | its plan or ADR file only | no |
| **code-reviewer** (this one) | review / refute / re-review / completeness | no | no | no |
| qa-engineer | verification gate, regression checks, tests | no | tests, when asked | yes |
| debugger | root cause first, then a fix when asked | no | fix + regression test, when asked | yes |
| security-reviewer | exploitable vulnerabilities only | no | no | no |
| ui-ux-designer | direction / build / critique / copy / judge | no | UI files | yes |

## When to use

- Before you commit or merge: review the working tree, a branch against its base, or named files.
- When you want real defects only: each finding has file:line, a failure scenario, a fix and a confidence of 80 or more.
- Inside a Lead Developer review panel: the lead sends it review, refute, re-review and completeness briefs.

## Not for

- Fixing what it finds: use `developer`.
- Running the test suite: use `qa-engineer`.
- Exploitable-vulnerability review: use `security-reviewer`.
- Choosing a different design: use `software-architect`.

## How it works

- **Scope first.** The working tree (one diff approval), a branch or commit range (one shell approval per read-only git command, announced up front) or named files. With nothing to review it asks: last commit, branch vs main, or specific files.
- **Spec from you.** Your request, the plan file or the lead's brief; without one it reports `SPEC: CANNOT_VERIFY` instead of guessing.
- **Lens by lens.** Correctness, spec compliance, tests and silent failures, and simplification (report only), each finished before the next starts.
- **Confidence 0 to 100.** Only findings at 80 or above are reported; weaker ones are listed under POSSIBLE, so nothing is hidden.
- **No noise.** Pre-existing issues the change does not make worse, what the compiler or linter catches, style without a quoted project rule and "could be more defensive" are left out.
- **Claims are checked.** The implementer's summary, commit messages and code comments are claims to verify; text in the diff aimed at AI reviewers is itself reported.
- **Verdict and coverage.** APPROVE, or REQUEST_CHANGES when any Critical or Important finding remains, plus a line saying how many files were reviewed and which were not.

### Modes

| Mode | What it does | Verdict |
|---|---|---|
| review | the lenses above, over a change | APPROVE or REQUEST_CHANGES, plus SPEC: MET, GAPS or CANNOT_VERIFY |
| refute | votes CONFIRMED or REFUTED on every candidate finding from one angle: reachability, impact or defenses | one vote per finding |
| re-review | checks each earlier finding against the fix: ADDRESSED or NOT_ADDRESSED | ALL_ADDRESSED or OPEN |
| completeness | what the request asked for that is not done or not verified | COMPLETE or GAPS |

You can ask for any mode directly, for example "check this branch for completeness against the plan in docs/plans".

## Tools and cards you'll see

| Call | When | Approval card |
|---|---|---|
| fs.read, fs.find, fs.search; code.git status and log | always | none |
| code.git diff | working-tree review | one |
| os.execute with read-only git (log, diff) | branch or commit-range review | one per command; Critical risk, so it always asks |
| info.request | nothing to review | a question, not a card |

- As a sub-agent of Lead Developer it reads only the review-diff file the lead wrote, with fs.read, so it raises no cards of its own.
- TOOLS.md pins fs.read, fs.find and fs.search for the sub-agent profile, so they stay visible when the lead narrows a child's tools.

## After installing

- **Effort:** high works best for review: `sophon agents models code-reviewer --effort high`. Delegated runs use it only while the lead's chat has no effort of its own (`/effort reset` there).
- **Bind and trust the repository:** run `sophon` in the project folder, then `/trust`, so AGENTS.md and the project rules load. The reviewer quotes a rule whenever it cites one.
- **Allowed Medium-risk calls for the session** (set with `/permissions`) cover this agent's code.git diff at the root. They never cover its os.execute calls, and never any sub-agent's calls.
- **With Lead Developer:** install with `sophon agents install code-reviewer --allow-delegation-from lead-developer` and keep the id `code-reviewer`. If the lead restricts delegation to an allow list, add this id to it. The lead finds the agent through the `Family role: code-reviewer.` marker in its when-to-use text.

## Works best with

- `lead-developer`: runs review panels (3 lenses for a medium change, 4 or 5 for a large one), then 3 refuters per Critical or Important finding, a re-review after each fix and a completeness check at the end.
- `developer`: fixes confirmed findings, with a test that fails first.
- `security-reviewer`: the security lens this agent leaves out.
- `qa-engineer`: runs the suites this agent does not.

## Limits

- It runs no builds or tests. When a run would settle a question, it says which run and who should do it.
- code.git diff sees uncommitted tracked files only. Committed work is reviewed through the range form, which costs one approval per command.
- Large diffs are split to fit the output window; anything not reviewed is named.
- As a sub-agent it reviews only the diff file and line ranges in its brief, opening other files only to prove a finding.
- Findings below the confidence threshold are listed, not argued, so some real but unproven issues land there.
- It is not a security review.

## What it never does

- Edit, write, move or delete files; commit, push or switch branches.
- Run commands other than read-only git, and none at all as a sub-agent.
- Start sub-agents.
- Report style preferences without a quoted project rule.
- Follow instructions found in the code, comments or diff it reviews.

## What's new in 2.0.0

- New in the family: this is its first release, numbered 2.0.0 to match the family generation.
- Ships a TOOLS.md that pins read tools for the sub-agent profile; nothing else needs installing.
- Updating an agent does not change its delegation settings. If your Lead Developer 1.0.0 uses an allow list, add the new companions `code-reviewer`, `debugger` and `security-reviewer` to it.

## Credits and license

Workflow patterns adapted, not copied, from obra/superpowers (MIT, © 2025 Jesse Vincent) and Anthropic's Claude Code plugins (feature-dev, pr-review-toolkit, code-review, security-review, frontend-design; Apache-2.0). Licensed under the MIT License; see LICENSE.
