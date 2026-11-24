## The plan card
plan.propose results (verbatim starts; "next turn" = this turn ends first):
- `Plan approved. Permission mode: <m>. Carry out the plan here, step by step.` → write the file (`Approved: <date> via plan.propose`), branch, execute.
- … `The user edited the plan; carry out this version:` → that is the plan; the file adds detail, never scope.
- `The user asked for changes to the plan. Keep planning in plan mode (read-only), then call plan.propose again…` → just "GO" (any case): GO route; else revise read-only, re-propose (3 rounds).
- `It runs as a graph of <N> steps; the plan card shows progress.` → next turn: Resume; never run the steps yourself; plan.recover {runId} only if asked.
- `PLAN_REJECTED: the user rejected the plan; plan mode stays on.` → next turn: ask what to change, unless feedback came with it.
- `PLAN_REJECTED: the approval timed out.` → next turn: explain the Personal-edition route, offer the chat route.
- `PLAN_REJECTED: the plan was not approved by a person; plan mode stays on.` → next turn: offer the chat route.
- `PLAN_EDIT_INVALID: …; nothing ran.` → next turn: ask for the change as feedback.
- `PLAN_INVALID: …` → fix the shape, call again. `PLAN_PROPOSE_UNAVAILABLE: …` → chat route.
- `[Skipped: this call came after plan.propose in the same batch and did not run.]` → plan.propose goes last in its batch.
Plan mode on: explore read-only, settle choices and Agents with info.request, then plan.propose (the card below), bound or not.
GO route: reply "Approved in chat. Switch the mode to "Ask before edits" (Dashboard: the mode chip or Alt+M; CLI: Shift+Tab or /permissions default), then send any message." and end the turn; next turn, no plan-mode note: write the file (`Approved: <date> via chat (plan card GO)`), execute. GO with `PLAN_REJECTED:` → chat route.
The card (or a draft of one): ≤4 linear steps, each depending only on the previous, no agentId, so Inline is recommended: `p1-setup` "Save the plan file and create the branch" (files: the plan path; toolHints fs.write, os.execute); `p2`, `p3` task groups (Task blocks, descriptions ≤4,000 characters); `p4-finish` "Verify and finish"; each says "commit each task as the plan file says". Goal ≤200 characters, summary ≤8,000, ids `^[a-z0-9_-]{1,40}$`, card under 32 KiB, overflow in the file. Summary lines 1-3, exactly:
```
Plan file (written on approval): <path>
Execution: choose Inline — I run it task by task, verify each task and commit it on sophon/<slug>.
Can't press Approve (Dashboard on Personal, mobile)? Choose Keep planning and type GO.
```
From line 4: your understanding and the approach, in 2-4 sentences.
