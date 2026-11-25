## Receiving review
Findings from a reviewer, a brief's FINDINGS or the user are claims: check each against the code before you change anything.
- Unclear: ask before you fix any (as a child: OPEN_QUESTIONS); findings are often linked.
- Wrong: answer with evidence, `F2: not changed — <path:line or test output>`, never a silent change. One that conflicts with a decision the user made goes to the user.
- The rest: fix one at a time, blocking ones first, with a test that fails before the fix where behaviour changes.
- Reply with what changed, `F1: fixed — <what>, <path:line>`, and nothing about the reviewer or yourself.
| Excuse | Reality |
|---|---|
| "The reviewer knows best." | A finding is a claim about this code. Check it here. |
| "All at once is faster." | One fix at a time shows which change broke the check. |
| "Pushing back looks defensive." | A wrong fix costs more than a line of evidence. |
