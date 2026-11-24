---
id: product-acceptance
summary: Criteria patterns with weak and strong forms, what counts as evidence, and a filled true, exists, wired table.
reviewed: 2026-11
---
# Acceptance: criteria patterns and the evidence table

Examples are invented. A criterion states a rule, not one instance, and names its failure path; read together, the criteria of a story fail any wrong build.

## Criteria patterns

| Pattern | Form | Example |
|---|---|---|
| Rule with failure path | Given <state> / When <action> / Then <result>; and when it fails, <result> | Given room 2 is booked 9-10 / When a member books 9:30 / Then the booking is refused with the holder's name |
| Boundary | The edge value on each side | A booking of exactly 4 hours ahead is allowed; 4 hours and 1 minute is refused |
| Permission | Who may, and what others see | A member cannot cancel another member's booking; the cancel control is absent for them |
| Stays the same | Behaviour outside the story is unchanged | Existing invites still arrive with their original times |
| Empty and first use | The state with no data | With no rooms, the page says how to add one |
| Repeat | Doing it twice | Submitting the same booking twice creates one booking |
| Time | Behaviour that depends on the clock | A booking that has started can no longer be moved |
| Observable output | What a person or a caller can see | The API returns 409 with the clashing booking's id |

| Weak | Why it fails | Strong |
|---|---|---|
| Booking works | No state, no action, no observable result | Given room 2 is free / When Dana books 9-10 / Then room 2 shows busy 9-10 for every member |
| The code calls checkOverlap | Points at code; passes with a wrong rule | Overlapping bookings are refused; touching ones (10-11 after 9-10) are allowed |
| Errors are handled | Which errors, seen how? | When the calendar is unreachable, the booking is not saved and the member sees "Try again" |

Criteria of one story must agree with each other and with the requirements: two criteria that cannot both hold are a defect in the story, not in the build.

## Evidence table

Each requirement is judged on three columns, worked backward from the goal:
- True: what must now be observably true for the user.
- Exists: the parts that make it true, cited as path:line.
- Wired: how the entry point reaches them, cited as path:line.

Turning a goal into claims, for "members cannot double-book a room":

| Kind | Claim |
|---|---|
| True | A second booking that overlaps is refused and the member sees who holds the room |
| True | A booking that only touches another one is still saved |
| Exists | An overlap rule, a refusal message, a test for each case |
| Wired | The booking route calls the overlap rule before saving |

A finished task or a green unit test proves a part exists; only the True column proves the goal.

| R id | True | Exists | Wired | Rating |
|---|---|---|---|---|
| R1 | `npm test -- rooms` exit 0, 6 passed, run this turn | src/rooms/list.ts:12 | src/routes.ts:40 mounts /rooms | Met |
| R2 | Check run: booking 9:30 refused, message shows holder | src/booking/overlap.ts:8 | src/booking/create.ts:21 calls it | Met |
| R3 | Clash message shown; the time zone case is untested | src/booking/message.ts:5 | src/booking/create.ts:30 | Partial |
| R4 | No output; the story's Check was not run | src/reminders/send.ts:3 | Not found: nothing schedules it | Missing |
| R5 (later) | Not run; needs a staging calendar | -- | -- | Not verified |

| Counts as evidence | Is only a claim |
|---|---|
| A Check run in this session, with exit code and the proving line | A ticked task box |
| Command output the user pasted in this session | A commit subject or a PR title |
| Output quoted from a brief that says when it was run | Another agent's report or summary |
| A file read at a cited path:line | "Tests pass" with no output |

A claim shows where to look. A part that exists but that no entry point reaches is not wired, however complete it looks.
