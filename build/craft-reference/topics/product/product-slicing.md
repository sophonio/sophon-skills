---
id: product-slicing
summary: The thinnest end-to-end path by kind of system, ten split patterns with examples, and the signs that a story is two.
reviewed: 2026-11
---
# Slicing patterns: thin paths and story splits

A slice is a narrow path that is complete: it runs through every layer it touches and can be checked from the outside. A layer done alone (all the tables, then all the screens) is not a slice.

## Thin paths

| Kind of system | Thinnest end-to-end path | Example |
|---|---|---|
| Web app with storage | One input saved and shown back on a page | Type a room name, save, see it in the list after reload |
| HTTP API | One endpoint, one rule, stored, one real caller | POST a booking, reject an overlap, GET returns it |
| Command-line tool | One command, one flag, real input to real output | `tool book --room 2` writes the booking file |
| Data pipeline | One record from source to sink with one transform | One calendar event lands as one row in the report table |
| Mobile app | One screen reading live data from the backend | The room list shows real rooms on a device |
| Integration | One event from the outside system handled and visible | A calendar change appears in the app within a minute |
| Library | One public function with its doc and a test that uses it as a caller would | `isFree(room, slot)` with two examples |
| Agent or skill | One request answered with one real tool call and its result | "Is room 2 free at 9?" answered from the calendar |

Very little behaviour is fine; a stub layer is not. A hard-coded rule is acceptable in the first slice when the next story replaces it, and says so in Out.

## Split patterns

| Pattern | Split along | Example |
|---|---|---|
| Workflow steps | Each step, or the first and last with the middle done by hand | Book now; reminders later |
| Rule variations | One business rule per story | Overlap rule; then the 4-hour limit |
| Happy, then failure paths | Success first, each failure case after | Booking works; then the taken-slot message |
| Data variations | One kind of input at a time | One room; then rooms with sub-rooms |
| Input methods | The simplest way of entering data first | A typed time; then a time picker |
| Operations | Create and read; then update; then delete | Book and view; then move; then cancel |
| Simple, then complex | The core case, then the elaborate one | Single booking; then recurring |
| Quality later | Correct first, then fast, scalable or polished | Works for 10 rooms; then 500 |
| Roles | One kind of user at a time | Members book; then admins release holds |
| Spike first | A time-boxed question before the build | One day to learn the calendar API, then the story |

Wide internal changes split as expand and contract: add the new form beside the old, move callers over in small stories, then remove the old form.

## Two stories

A story is probably two when one of these holds:

| Sign | Example |
|---|---|
| "And" or "or" joins two outcomes in the title | "Book rooms and send reminders" |
| More than one actor gets something | Members and admins in one story |
| Its criteria have different When actions | One When books, another cancels |
| A word like "for now", "placeholder", "simplified" or "wired later" | "Simplified rules for now" |
| It needs two Checks to prove | A unit test and a separate manual step for another flow |
| Its R ids could ship separately | R2 alone would already be useful |
| An open decision blocks part of it | Half waits on OQ-3 |
| It will not fit one session | It touches every module of the system |

The repair is the same each time: split out the second part as its own numbered story, and keep the first one whole.
