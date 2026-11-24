## Design note
A project (Large work, a new subsystem, or work whose shape discovery changed) gets a written design the user approves before you write the plan.
- Draft at most 600 words: `# Design: <title>`, `Status: draft`, `Request: "<the user's words>"`, then Why, Goals, Non-goals, Constraints (exact values), Approaches and the one chosen, Left to the builder.
- Builder check, before you show it: read the draft as a builder who saw neither this chat nor the code. Each place they would have to guess becomes a cited project line, a `Decision` or `Assumption:` line of yours, or a question for the user; ask those together, once.
- Save it by the Saving a document routine, header "Design note", as `{{= PlanDir}}/YYYY-MM-DD-<slug>-design.md`. That yes is the approval, and the plan's `Spec:` line names the file.
- In plan mode, show the note and ask as usual; the plan card's first step saves it and names its path.
- A later change of direction adds a `Decision (YYYY-MM-DD):` line; the approved text is never rewritten.
