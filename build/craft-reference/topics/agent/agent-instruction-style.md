---
id: agent-instruction-style
summary: Instruction forms by observed failure, the Excuse and Reality row format, positive recipes, wording rules.
reviewed: 2026-11
---
# Instruction forms: which form fits which failure

## Instruction forms {#forms}

| Observed failure | Form | Shape |
|---|---|---|
| Knows the rule, breaks it under pressure | firm rule, its reason, excuse rows | "<Rule>. <What goes wrong without it>." then the table |
| Complies, but the output has the wrong shape | positive recipe | what the output is, its parts in order |
| Leaves one element out | required slot in the template | `<NAME: what goes here; what breaks when empty>` |
| Right only in some cases | conditional | "If <something observable>, then <action>." |
| The control already behaves | nothing | no text |

- A prohibition on a concrete, checkable act holds when nothing pulls the other way.
- A prohibition on how to compose output tends to backfire. Upstream micro-tests found a "do not restate the brief" line did worse than no guidance, while a numbered list of the parts did best with no spread.
- Removing the reasons behind a discipline rule lowered compliance under pressure in upstream evals; the reasons work best as table rows.

## Excuse-table format {#excuse-table}

- Two columns, Excuse and Reality, placed where the rule applies, never in a recap.
- Excuse: the agent's own recorded words, quoted. A row with no recorded excuse behind it is a guess.
- Reality: one or two sentences. The consequence or the check, then what to do instead.
- Two to four rows per rule; one row per distinct excuse.

Worked example, for a "fresh evidence before saying done" rule:

| Excuse | Reality |
|---|---|
| "The change is too small to break anything." | Small changes break builds too. The check takes a minute; run it. |
| "The tests passed earlier." | Earlier is before this edit. Only a run after the last change counts. |
| "The sub-agent said it works." | A report is a claim. Read the diff and the output yourself. |

Weak reality cells say "Not allowed" or repeat the rule louder. Strong ones name what breaks and the allowed alternative.

## Positive recipes {#recipes}

| Before | After |
|---|---|
| "Do not write long reports." | "The report has three parts, in order: the result in one line; each changed file with one sentence; each command run with its exit code." |
| "Remember the version." | Template slot: `Version: <the SemVer you set; the build refuses an empty one>` |
| "Be careful with migrations." | "If the diff touches a migrations folder, then list each migration with its down step." |
| "Do not ask too many questions." | "Ask a question when its answer would change the result and the project files cannot supply it." |

## Wording rules {#wording}

- A trigger line (description, when-to-use) says when to pick the package and what it is not for. A summary of the steps there gets followed in place of the body.
- Define a judgment word by a test: "A finding is Major when the work cannot ship until it is fixed."
- Attach the consequence to the rule in the same sentence.
- No caveat clauses such as "unless it matters": they reopen the rule. Write a real exception as its own conditional on an observable fact.
- Capitals and "always" fade; placement at the point of use holds.
- Address a capable reader; cut recap, benefit and persuasion prose.
- Write tool names exactly as the platform spells them, and only names that exist.
- Phrase each rule positively, which also keeps it clear of the scanner patterns (topic agent-package-facts, section scanners).
- Ties go to the shorter wording. Five runs giving five readings means the form is loose: change the form, do not add words.
