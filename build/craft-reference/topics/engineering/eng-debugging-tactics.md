---
id: eng-debugging-tactics
summary: More ways to build a red-capable reproduction, tactics by symptom, hypothesis examples and bisect recipes on four axes.
reviewed: 2026-11
---
# Debugging: reproduction loops and tactics by symptom

A good loop is red-capable (it shows the reported symptom, not a nearby one), deterministic, fast (seconds, not minutes) and runs with no person in it.

## Reproduction rungs

| Loop | Fits when |
|---|---|
| an existing test, narrowed by name or file | the area already has tests |
| a new minimal test at the nearest seam that shows the symptom | the code can be called without the whole app |
| a command-line run with the reported input file or arguments | a CLI, a build step, a converter |
| a scripted HTTP request against a local server | a route or handler; save the exact request body and headers |
| a replay of captured input: a request log, a queue message, a recorded trace | the symptom depends on real data; redact personal values first |
| a differential run: the same input through the good and the bad build, outputs diffed | "it used to work"; a refactor; an upgrade |
| a stress harness: the trigger in a loop of 100 to 1000 runs, with a fixed seed | an intermittent failure; raise its rate until each run shows it in seconds |
| a property or fuzz run seeded from the failing value | a parser, a numeric routine, an encoder |
| a throwaway script that imports the module and calls it | the setup is heavy and only one function is suspect |

Minimise after it is red: remove input, steps, config and code until each remaining piece is needed for the symptom.

## Hypotheses {#hypotheses}

| Weak | Testable |
|---|---|
| "Something is wrong with the cache." | "If a stale cache entry is the cause, clearing the cache before the request makes the error disappear." |
| "It is a race." | "If two writers race on the row, running with one worker never fails in 200 runs, and two workers fail at least once." |
| "The new library broke it." | "If the 4.2 upgrade is the cause, pinning 4.1 in the lockfile makes the test green with no other change." |

## Tactics by symptom

| Symptom | First tactics |
|---|---|
| passes locally, fails in CI | diff the environment: runtime and tool versions, OS, locale, time zone, env vars, file-name case, parallel workers, clean checkout without local caches |
| intermittent | stress loop with a fixed seed; run alone and in the suite; look for shared state, time, ordering and unawaited work |
| fails only after another test | test pollution: bisect the earlier tests (below) |
| wrong output, no error | trace the value backwards from where it is wrong to where it was last right; log at each boundary |
| crash with a stack trace | read every frame, ours and the library's; the first frame in our code is a suspect, not the answer |
| hang | a thread or async dump during the hang; look for a lock order, a missing timeout, a read with no end |
| slower than before | measure a baseline first, then bisect commits with the timing as the test |
| memory or handle growth | count objects or handles after N and 2N iterations; growth that scales with N is the leak |
| only on one platform | path separators, line endings, case sensitivity, default encoding, locale number formats |
| after a dependency upgrade | read the changelog between the two versions; diff the lockfiles; differential run on both |
| disappears when logging is added | timing or ordering; log into a buffer and print at the end instead of writing inline |
| misleading error message | find where the message is built, and which earlier error it replaced or swallowed |
| first run works, second fails | state left behind: files, cache, a row, a port still bound, a global |
| near midnight, month end or a DST change | inject the clock; run at the exact boundary instant |

## Bisect

Bisection halves a search space until one element remains. It needs a known good and a known bad end, and a test that tells them apart.

| Axis | Recipe |
|---|---|
| commits | `git bisect run <script>`: exit 0 means good, 1 to 124 (except 125) bad, 125 skip (the commit cannot be tested, for example it does not build) |
| input data | split the failing input in half; keep the half that still fails; repeat until the smallest failing record remains |
| configuration | turn off half of the flags or settings; keep the half whose removal changes the outcome |
| dependencies | revert half of the changed lockfile entries; keep the half that brings the failure back |
| test order | run the earlier tests in two halves before the failing one; keep the half that makes it fail; repeat until one polluter remains |

A bisect script should fail for the symptom only. A build error counted as "bad" sends the search to the wrong commit; return 125 for it instead.
