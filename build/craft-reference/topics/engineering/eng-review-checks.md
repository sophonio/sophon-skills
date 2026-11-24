---
id: eng-review-checks
summary: Review questions by defect class, each with the sign in the code that points to it, and three worked readings.
reviewed: 2026-11
---
# Review checks by defect class

Each row pairs a question for a changed hunk with the sign in the code that makes a "yes" likely. A sign is a lead, not a defect: it becomes one only with a concrete input and the wrong result it produces.

## Logic and boundaries {#logic}

| Question | Sign to look for |
|---|---|
| Is a condition inverted or incomplete? | a `!` added or dropped; logical and swapped for or; a new branch with no `else` where the old code had one |
| Off by one? | `<` against `<=`; `length - 1`; a range end that one API treats as inclusive and another as exclusive |
| What does empty input do? | `items[0]` or `first()` with no guard; a division by a count; the maximum of an empty list |
| What does the largest input do? | a fixed-size buffer or integer width; a page size taken from the caller with no cap |
| Is it the right kind of equality? | reference against value comparison; `==` on floats; strings compared without case or Unicode normalisation |
| Is an order assumed? | a map or set iterated as if sorted; a query with no ORDER BY whose first row is used |
| Is absence told apart from zero? | `if (x)` or a logical-or fallback where 0, "" or false are valid values |

## State, time and concurrency {#state}

| Question | Sign to look for |
|---|---|
| Can two callers interleave? | read, modify, write on shared state with no lock or transaction; check then act on a file or row |
| Is every async call awaited? | a returned promise or task dropped; work started in a loop and never joined |
| Does a cache still match its source? | a write path with no invalidation; a cache key missing an input that changes the result (user, tenant, locale) |
| Is anything registered twice? | a listener, timer or subscription added on each render or retry with no removal |
| Is every resource released on every path? | open, then an early return or throw before close; no `finally`, `using`, `with` or `defer` |
| Does time behave? | local time stored where UTC was meant; day arithmetic across a DST change; month-end and leap-day dates |
| Does encoding survive? | bytes and text mixed; a length counted in bytes where characters were meant; integers above 2^53 in JSON |

## Contracts and compatibility {#contracts}

| Question | Sign to look for |
|---|---|
| Who else calls what changed? | a changed signature, return shape or thrown type; callers outside the diff not updated |
| Does stored or sent data still read back? | a renamed field in a serialised form, event or column; a migration with no backfill; an enum value reordered |
| Did a default change? | a new default value, timeout or flag; existing users get it without asking |
| What did the deleted lines do? | a removed check, log, metric, cleanup or test with no replacement named in the change |
| Does an error still reach its handler? | a new exception type a caller's catch does not match; an error code now returned as success |

## Tests, comments, types and structure {#structure}

| Question | Sign to look for |
|---|---|
| Would a test fail if this broke? | changed logic with no test touched; an expected value edited to match new output with no reason given |
| Is each comment still true? | a comment describing behaviour the code no longer has; words like "for now" or "new version" naming a temporary state |
| Can the type hold an illegal state? | two booleans that must never both be true; a status string beside fields that are only valid for one status; a cast or `any` |
| Does the change remove complexity or move it? | the same number of concepts spread over more files; a wrapper whose methods only forward |
| Does it duplicate what exists? | a new helper with the same job as one already in the codebase; copied blocks that differ in one literal |
| Is a flag doing two jobs? | a boolean parameter that switches between two behaviours; callers passing `true` with no name |

## Worked readings {#worked}

1. Sign: `if (user.role == "admin" || user.id == order.ownerId)` gains `|| order.public` in a hunk. Question: inverted or incomplete. Reading: public orders become editable by anyone, since the same check guards the edit handler. A defect, with the trigger "any signed-in user edits a public order".
2. Sign: `return cache.get(key) ?? load(id)` where `key` is built from `id` only and `load` filters by tenant. Question: does the cache match its source. Reading: the second tenant to ask receives the first tenant's row. A defect.
3. Sign: `items.sort()` added before a loop. Question: is an order assumed. Reading: the loop sums values, so the order does not change the result. Not a defect; at most a wasted sort.
