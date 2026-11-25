---
id: product-tickets
summary: Requirements and story file fields with examples, status words, the id chain from PRD to check, the out-of-scope file.
reviewed: 2026-11
---
# Tickets: requirements and story files, status words, id chain

Examples are invented and written in plain ASCII; use the separators the template in use gives.

## Requirements file

| Field | Holds | Example |
|---|---|---|
| Title | The goal in a few words | `# Room booking for one firm` |
| Status | One status word | `Status: approved` |
| Source | Where the goal came from | `Source: docs/product/room-booking/prd.md` |
| Approved | `pending` or the date of the user's yes | `Approved: 2026-11-14` |
| Intent | Two to four sentences in the user's words | "Managers stop finding clashes at the door." |
| Requirements | `R<n> (covers <source id>): <actor> can <capability> <condition>` | `R2 (covers FR-3): a member can book a free room up to 4 hours ahead` |
| Later | A requirement marked `(later)` is not a must | `R5 (later): a member can repeat a booking weekly` |
| Boundaries | What stays the same, and at least one thing out | `Stays the same: existing calendar invites` / `Out: desk booking` |
| Stories | Table of number, story, covers, status | Row: 01, Book a free room, R1 and R2, built |
| Notes | Dated decisions and marked note lines | `Decision (2026-11-13): times are local` |

## Story file

| Field | Holds | Example |
|---|---|---|
| Title | `# NN <title>`; NN is build order | `# 02 Warn before a clash` |
| Covers | R ids, and risk with its reason | `Covers: R3`, `Risk: medium -- touches calendar sync` |
| Now | Today's behaviour, as found in the code | A second booking for a taken slot is saved |
| After | Behaviour once built | The second booking is refused with the name of the holder |
| Acceptance | `A<n> Given / When / Then` | See topic product-acceptance |
| Check | One command or manual step, with the expected result | `npm test -- booking` exits 0 with the clash test listed |
| Out | What this story leaves for another | Clashes across time zones |
| Acceptance record | Dated table written when the story is judged | Empty until then |

A filled story:

```
# 02 Warn before a clash
Status: approved
Covers: R2, R3 -- Risk: medium -- changes how bookings are saved

## Behaviour
Now: a booking that overlaps another is saved, and both groups arrive.
After: an overlapping booking is refused and the member sees who holds the room.
## Acceptance
- A1 Given room 2 is booked 9:00-10:00 / When a member books 9:30-10:30 / Then the booking is refused with "Taken by Ops until 10:00"
- A2 Given room 2 is booked 9:00-10:00 / When a member books 10:00-11:00 / Then the booking is saved
## Check
npm test -- booking: exit 0, the overlap and touching tests both listed
## Out
Clashes across time zones (story 04).
## Acceptance record
```

A bug story adds Steps to reproduce, Expected, Actual and a line `Hypothesis: <cause>` labelled as a guess. It never names a fix.

## Status words

| Word | Means |
|---|---|
| draft | Written, not yet agreed by the user |
| approved | The user said yes to this text |
| in-progress | A plan is building it |
| built | The builder finished; not yet judged |
| accepted | Judged against its criteria and met |
| rejected | Judged, and a must is not met; goes back to the builder |
| dropped | Will not be built; a `Dropped:` line says why |

`rejected` applies to stories only; a requirements file is never rejected, it is replanned.

## Id chain

Each step cites the one before it, so any line can be traced to the decision behind it.

```
PRD     FR-3  A member can book a free room up to 4 hours ahead
Spec    R2 (covers FR-3)
Story   02 Warn before a clash -- Covers: R2, R3
Crit    A1 Given room 2 is booked 9:00-10:00 / When Dana books 9:30 / Then she sees "Taken by Ops until 10:00"
Plan    Task 3 -- Covers: R2 (02 A1)
Check   the story's Check, run and quoted in the Acceptance record
```

Ids are never reused or renumbered. A story added between 02 and 03 is `02a`. An R id with no story, or a story with no R id, is a gap in the chain.

## Out of scope

`docs/product/out-of-scope.md` holds one line per declined request, newest last:

```
- 2026-11-20 -- Desk booking -- declined: a different buyer (NG-1) -- from issue 41
- 2026-11-22 -- Export bookings to a sheet -- declined: the calendar already exports
```

Triage outcomes: needs-info (the one question to ask), ready (becomes a story), declined (a line here). A request that matches a line here is answered by quoting it.
