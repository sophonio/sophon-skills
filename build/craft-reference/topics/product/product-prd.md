---
id: product-prd
summary: Lean PRD sections and what each holds, id forms with good and weak lines, counter-measure pairs, the unknown form.
reviewed: 2026-11
---
# Lean PRD: sections, id forms, examples

A lean PRD is 600 to 1,000 words. It is complete when no gap blocks a decision about the first version; padding to look thorough makes it worse. Keep a line only when the reader who builds from it would decide wrongly without it. Dashes are written `--`.

## Sections

| Section | Holds | Typical size |
|---|---|---|
| Purpose | The problem, who has it, why now; links the brief | 2 to 4 sentences |
| Journeys | Named people in real situations, start to finish | 1 to 3 journeys |
| Requirements | What an actor can do, under which condition | 5 to 15 lines |
| Rules | What must always or never hold, across requirements | 0 to 6 lines |
| Non-goals | Deliberate exclusions, each with its reason | 1 to 5 lines |
| Measures | Outcomes that show it works, each with a counter-measure | 1 to 4 pairs |
| First version | The smallest set of FR ids worth shipping | One line of ids |
| Open questions | What is unknown, and who can answer | As many as exist |
| Decisions | Dated choices, in the user's words | As many as exist |

## Id forms

| Id | Form | Good | Weak, and why |
|---|---|---|---|
| UJ-n | <named person>, <situation>: does, gets | UJ-1 Dana, office manager, Monday 8:50, sees room 2 is free and books it from her calendar | "The user books a room" -- nobody, no situation |
| FR-n | <actor> can <capability> <condition> | FR-3 A member can book a free room for up to 4 hours ahead of its start | "Fast booking" -- no actor, no capability |
| RULE-n | Always or never, testable | RULE-1 A room never holds two bookings that overlap | "Bookings should be sensible" |
| NG-n | Exclusion and reason | NG-1 No desk booking -- a different buyer | "Not everything" |
| SM-n | Outcome, measure, target or Unknown | SM-1 Clashes per month at the pilot firm, from 2 to 0 | "Users are happy" |
| OQ-n | Question -- who can answer | OQ-2 Do rooms need approval to book? -- the office manager | "TBD" |

A filled excerpt, to show the density:

```
## Requirements
- FR-1 A member can see every room with its free and busy times for today
- FR-2 A member can book a free room from the room list
- FR-3 A member can book a free room up to 4 hours ahead of its start
- FR-4 A member can cancel a booking they made, until it starts
## Rules
- RULE-1 A room never holds two bookings that overlap
## Non-goals
- NG-1 Desk booking -- a different buyer and budget
## First version
FR-1, FR-2, RULE-1
```

Requirements say what, never how: no screens, tables, libraries or endpoints. Measures name no technology. An id is never reused or renumbered; a removed line stays with `Dropped:` so the gap explains itself, and a new line takes the next free number.

## Counter-measures

A measure can be gamed or bought at a hidden cost; its counter-measure is the number that must not get worse.

| Measure | Counter-measure | What it catches |
|---|---|---|
| Bookings made per week | Bookings cancelled within an hour | Booking for its own sake |
| Time to complete sign-up | Accounts that finish their first task | A shorter form that drops a needed step |
| Support tickets closed per day | Tickets reopened within 7 days | Closing without solving |
| Conversion at checkout | Refunds and chargebacks | Pressure that buyers regret |
| Search response time | Searches with no result clicked | Faster but worse results |
| Alerts resolved | Incidents that had no alert | Alerts muted to look resolved |

## Unknowns

When a section has nothing known, it holds one line instead of an invented value:

```
Unknown: how many rooms a typical customer has -- the sales lead
```

Related note lines:

```
Open question: OQ-3 Can a guest book? -- the office manager; blocks FR-5
Assumption: bookings are in the firm's local time zone
Decision (2026-11-12): first version serves one firm -- the user, in chat
Source conflict: interview says weekly clashes, sheet history shows two a month
Dropped: SM-2 usage reports -- NG-3 covers it
```

A number appears only when the user or a cited source gave it. A target nobody gave reads `target Unknown -- <who can set it>`.
