---
id: product-prioritisation
summary: Risk-first, RICE and opportunity-score lenses with worked rows, and a pre-mortem sheet with sweep areas.
reviewed: 2026-11
---
# Prioritisation lenses and the pre-mortem sheet

Each lens ranks problems, not features. Worked rows below are invented; a cell nobody gave a figure for reads `Unknown`.

## Risk first

Order by what would hurt most if the team is wrong about it, so the first work proves the riskiest assumption. Dependencies break ties.

| Item | Risk if wrong | Cheapest test | Rank |
|---|---|---|---|
| Clashes in shared room sheets | Nobody needs it | Two interviews about the last clash | 1 |
| Calendar sync for rooms | Cannot be built on the target calendar | One-day spike against its API | 2 |
| Booking from mobile | Low: same flow, smaller screen | None needed yet | 3 |

## RICE

Score = Reach x Impact x Confidence / Effort, from the method Intercom published.
- Reach: people or events per period (say per quarter).
- Impact per person: 3 massive, 2 high, 1 medium, 0.5 low, 0.25 minimal.
- Confidence: 100% high, 80% medium, 50% low; below 50% is a guess.
- Effort: person-months, from the people who will build it.

| Item | Reach | Impact | Confidence | Effort | Score | Rank |
|---|---|---|---|---|---|---|
| Clash warning | 400 | 2 | 80% | 1 | 640 | 1 |
| Recurring bookings | 250 | 1 | 50% | 2 | 62.5 | 2 |
| Room photos | Unknown | 0.5 | 50% | 0.5 | Unknown | -- |

A row with an Unknown factor has no score; it is ranked by reason or left out, and the table says which.

## Opportunity

Users rate each outcome 1 to 10 for importance and for how well today's tools serve it. Score = importance + max(importance - satisfaction, 0), after Anthony Ulwick's outcome-driven method. Above 10 is underserved; below 6 is served well enough.

| Outcome | Importance | Satisfaction | Score |
|---|---|---|---|
| Know a room is free before walking there | 9 | 3 | 15 |
| See who booked a room | 6 | 5 | 7 |
| Book a room weeks ahead | 4 | 7 | 4 |

## Pre-mortem

Assume the release failed six months from now, then write why.

| # | Cause | Earliest warning sign | Tag |
|---|---|---|---|
| 1 | Calendar sync drops bookings | Bookings missing from the calendar in the first week | launch-blocking |
| 2 | Managers keep the old sheet | Sheet edits continue after launch | fix soon after |
| 3 | Larger firms find it slow | Page time grows with room count | watch |

Areas to sweep for causes: value (nobody needs it), usability (people cannot work it out), feasibility (it cannot be built or run as planned), viability (cost, pricing, legal, support load), operations (deploys, data, on-call), adoption (the old way stays easier), and dependencies on other teams or vendors. A cause the team avoids saying out loud belongs on the sheet too.
