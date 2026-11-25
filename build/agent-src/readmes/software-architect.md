# Software Architect

Read-only software design: one decisive blueprint grounded in your code, and a plan file Lead Developer can run.

Part of the Buildersoft development family {{= FamilyVersion}}.

{{# roster}}

## When to use

- A blueprint for a feature or subsystem, before any code is written.
- An architecture decision record (ADR).
- A comparison of two or three competing designs against a written rubric.
- A gap check on an existing plan: missing tasks, weak verification, ordering, unsafe steps.
- A greenfield system: requirements with numbers, estimates, a data model, an API sketch, failure modes and an evolution path.

## Not for

- Implementing the plan: `lead-developer`, `developer`.
- Open fact-finding: `researcher`.
- Reviewing a finished diff: `code-reviewer`.
- Requirements and acceptance criteria: `product-owner`.

## How it works

- **Discovery first.** It reads before it asks, and asks only what changes the design and your request leaves open, one question per message, then plays its understanding back. With nothing open it asks nothing. Say "just build it" or "no questions" and it designs from its assumptions, written down as `Assumption:` lines.
- **Design it twice.** With no perspective given, it sketches two designs under opposing constraints (the smallest interface against the commonest caller made trivial, or the smallest change against the cleanest structure), four lines each, its recommendation first. You pick before any plan is drafted.
- Reads one to three analogous features in your code first and cites them with `file:line`. It writes down constraints, invariants and non-goals, and never invents a requirement.
- Commits to one approach and names the strongest alternative and why it lost. Perspectives: minimal, clean, or pragmatic (the default).
- Blueprints carry a depth check on each new module (picture it deleted; one implementation is a guessed seam), a trade-off table (choice, solves, worsens, revisit when) and, for backend work, a failure-mode table (failure, detect, surface, recover). New infrastructure must first answer four questions: what the current stack cannot do, who runs it, what leaving it costs, and the simplest version for the next year. When the requirements carry ids, a coverage table maps each to its task and its check.
- Modes: blueprint, adr, greenfield, compare (scores 2-3 blueprints 1-5 on fit, size, risk, testability and reversibility) and critique (numbers the requirements, flags each one with no task or no check; verdict READY or NEEDS_DECISION).
- **ADR:** it offers a record only when the decision is hard to reverse, surprising without its context and a real trade-off; otherwise the decision stays a line in the plan. The record is short: a title, a status and one to three sentences of context, decision and reason. Your repository's existing ADR folder, numbering and headings win.
- **Design note:** a project (Large work, a new subsystem, or work whose shape discovery changed) first gets a design note of at most 600 words in `docs/plans/`, checked as a builder who saw neither the chat nor the code would read it, which you approve before the plan.
- Ends with an implementation map, a build sequence, an end-to-end check, a plan file in the family format, and a ready plan.propose input of at most four linear steps, so the plan card recommends Inline.
- **Saving:** it shows the whole draft in chat, then asks Save, Change something or Stop. It saves only on a yes, one card per file; Stop or no answer saves nothing. Ask for a draft file and it writes one marked `Status: draft`.
- Hands off: "To execute: tell Lead Developer 'execute docs/plans/<file>'."
- Documents get a prose check before saving: the specific claim, the number, no filler. Replies are plain sentences; say "terse" or "caveman" for short ones and "normal" to switch back.

## Tools and cards you'll see

| Tool | Approval card |
|---|---|
| fs.list, fs.find, fs.search, fs.read | none |
| web.search, web.scrape | none |
| code.git status and log | none |
| code.git diff and blame | may raise one; none in a trusted workspace on the Gateway we tested |
| fs.write (a design note, plan or ADR you said Save to) | one per file |
| info.request | a question, not a card |

A typical design costs one card, the plan; a project adds one for its design note. TOOLS.md pins web.scrape in every profile and keeps fs.read, fs.find and fs.search visible when Lead Developer narrows a sub-agent's tools.

## After installing

- Install: `sophon agents install software-architect`, with `--allow-delegation-from lead-developer` if Lead Developer should brief it.
- Effort: set it to high with `sophon agents models software-architect --effort high`. When Lead Developer delegates to it, that setting reaches the delegated run only while the lead's chat has no effort of its own (`/effort reset`).
- Start `sophon` in the project folder so the session is bound, then run `/trust` so the project's AGENTS.md loads. Unbound, it can read and design, but paths are host-wide and project instructions are not loaded.
- Allowing Medium-risk calls for the session (run `/permissions` and choose Medium) never covers this agent's file writes: a package agent's edits always raise a card, and so does every sub-agent's call.

## Plan mode

In plan mode the architect cannot save files. It returns the draft and the plan.propose input in its reply, then tells you to leave plan mode and say "save", or to give the plan to Lead Developer. It never calls plan.propose itself: the agent that executes the plan proposes it, because graph steps would otherwise run as the architect.

## Works best with

- `lead-developer`: executes the plan file task by task, with a verified commit per task; in large work it runs two or three architects as a judge panel.
- `researcher`: gathers the facts first, with sources.
- `code-reviewer`: reviews the finished change against the plan.
- `debugger`: recommends it for a critique of the design behind a bug after three failed fixes.

## Limits

- It designs only from what it read; open fact-finding belongs to `researcher`.
- It runs no builds, tests or commands, so the plan's Run and Expected lines are proposals until `lead-developer` or `qa-engineer` runs them.
- In plan mode it cannot save its file. On the Personal edition the Dashboard cannot approve plan cards; Lead Developer then offers the chat route ("Choose Keep planning and type GO").
- One decisive design per run; ask again for an alternative.

## What it never does

- Edits source code, runs shell commands, commits or pushes.
- Calls plan.propose.
- Starts sub-agents.
- Writes any file other than its own plan, ADR or design note, and that only after your Save.

## What's new in 3.0.0

- Discovery, then two sketches under opposing constraints; you pick before any plan.
- The draft is shown in chat and saved on your Save, one card per file; a draft file only on request.
- A design note for projects; ADRs only past a three-part gate, in a short form that follows your repository's convention.
- Requirement coverage tables and a depth check on new modules.
- A terse voice on request.

{{> readme/80-upgrade-3}}

{{> readme/70-reference-skill}}

## Credits and license

Ideas re-expressed in our own words also come from JuliusBrussee/caveman (Apache-2.0, © 2026 Julius Brussee); blader/humanizer (MIT, © 2025 Siqi Chen); mattpocock/skills (MIT, © 2026 Matt Pocock); and github/spec-kit (MIT, © GitHub, Inc.).

Design patterns also draw on sheitabrk/backend-design (MIT, © sheitabrk and contributors) and proyecto26/system-design-skills (MIT, © 2026 Proyecto 26), adapted in original wording.

Workflow patterns adapted, not copied, from obra/superpowers (MIT, © 2025 Jesse Vincent) and Anthropic's Claude Code plugins (feature-dev, pr-review-toolkit, code-review, security-review, frontend-design; Apache-2.0). Licensed under the MIT License; see LICENSE.
