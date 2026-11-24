---
id: design-critique-rubric
summary: Ten usability heuristics with 0-4 anchors, persona sketches, P0-P3 severity anchors and a scoring sheet.
reviewed: 2026-11
---
# Critique rubric: heuristics, personas, severities

The ten heuristic names are Jakob Nielsen's, used with credit; the anchors and everything else here are our own. A score judges the screen against its job, for the people who use it, on the evidence at hand (an attached image, the DOM, the code).

## Heuristics

Scale for every row: 0 absent or harmful, 1 present but failing often, 2 works for the main path with visible gaps, 3 sound with minor gaps, 4 nothing to fix on this screen.

| # | Heuristic | 0 looks like | 2 looks like | 4 looks like |
|---|---|---|---|---|
| 1 | Visibility of system status | actions give no sign they ran; loading is a blank | feedback on the main action, silence elsewhere | every action answers within 100 ms; progress, saved state and errors are visible where the eye is |
| 2 | Match between system and the real world | internal keys, codes and jargon | the user's words in headings, the system's in details | names, order and units as the user's own work has them |
| 3 | User control and freedom | no cancel, no undo, dead ends | cancel exists; undo only in places | every step can be left, undone or resumed |
| 4 | Consistency and standards | one action has three names and two looks | consistent within the page, not across pages | one name, one look and one place per action across the product; platform conventions kept |
| 5 | Error prevention | destructive actions one click away; free text where a choice fits | confirms on delete; few constraints | constraints, sensible defaults and confirmation sized to the cost |
| 6 | Recognition rather than recall | the user must remember values between screens | options visible on the main path | choices, recent items and context shown where they are needed |
| 7 | Flexibility and efficiency of use | experts and newcomers suffer equally | shortcuts exist but are hidden | the frequent path is short; accelerators are discoverable |
| 8 | Aesthetic and minimalist design | decoration competes with content | clear primary content, some noise | every element earns its place; the primary action is found first |
| 9 | Help users recognize, diagnose, and recover from errors | codes or blame; input lost | a message, no way forward | says what happened and how to fix it, beside the field, input kept |
| 10 | Help and documentation | none where people get stuck | a help link far from the task | short help at the point of need; searchable when longer |

Score each row on evidence: name the element, state or flow behind every score below 4.

## Personas

Pick two or three that match the product's real users; each walks the screen's main task once.

| Persona | Situation | What they expose |
|---|---|---|
| First-time visitor | arrives cold from a link, knows the problem, not the product | unclear labels, missing first action, jargon (2, 6, 10) |
| Daily expert | uses it fifty times a day, fast, mostly by keyboard | slow frequent paths, animation on frequent actions, missing shortcuts (7, 4) |
| Keyboard and screen reader user | no pointer; hears names and roles | unnamed controls, focus order, traps, colour-only state (4, 9) |
| Low vision, 200% zoom | large text, narrow effective viewport | overflow, truncation, contrast, tiny targets (8, 1) |
| Interrupted phone user | one hand, poor signal, comes back later | lost input, no saved state, slow loads, small targets (3, 1, 5) |
| Sceptical evaluator | deciding whether to trust or buy | invented claims, vague copy, hidden limits (2, 8) |
| Administrator under pressure | something broke; must find and fix it now | buried status, unclear errors, risky destructive actions (1, 5, 9) |

## Severity anchors

| Grade | Meaning | Examples |
|---|---|---|
| P0 | blocks the task: the person cannot finish, or data is lost | the submit button never enables; a keyboard trap in the only dialog; an error that clears the form |
| P1 | harms the task: it finishes with an error, a risk or real distress for many users | a destructive action with no confirmation; body text at 3.1:1; a status shown by colour alone |
| P2 | slows or confuses: the task succeeds with friction | two names for one action; a missing empty state; help far from the field |
| P3 | polish: noticed by few, costs little | uneven spacing in one panel; an inconsistent icon size |

- Grade by the effect on the person doing the task, not by how hard the fix is.
- One finding, one grade; a finding that affects several heuristics is listed once, under the heuristic it hurts most.
- The same defect on many screens is one finding with a count.

## Scoring sheet

```
Screen: <name> | Job: <what the person comes to do>
Evidence: <attached image (viewport, theme, state) | DOM at <url> | code>
Personas walked: <two or three from the table>

| # | Heuristic                          | Score | Evidence (element, state)  |
|---|------------------------------------|-------|----------------------------|
| 1 | Visibility of system status        |       |                            |
| 2 | Match with the real world          |       |                            |
| 3 | User control and freedom           |       |                            |
| 4 | Consistency and standards          |       |                            |
| 5 | Error prevention                   |       |                            |
| 6 | Recognition rather than recall     |       |                            |
| 7 | Flexibility and efficiency         |       |                            |
| 8 | Aesthetic and minimalist design    |       |                            |
| 9 | Recognize and recover from errors  |       |                            |
| 10| Help and documentation             |       |                            |
Total: <sum> / 40

| Grade | Finding | Heuristic | Where | Fix |
|-------|---------|-----------|-------|-----|

Later round:
| # | Before | After | What changed |
```

A total compares rounds of the same screen; it never compares two different screens.
