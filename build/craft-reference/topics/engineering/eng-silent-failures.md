---
id: eng-silent-failures
summary: Idioms that hide errors, per language, with what each hides and the visible form; when a fallback is fine.
reviewed: 2026-11
---
# Silent failures: catches, defaults and fallbacks

A silent failure turns "it broke" into "it worked, with less". The caller, the user and the logs all see success.

## Patterns by idiom

| Idiom | What it hides | Visible form |
|---|---|---|
| `catch {}`, `except: pass`, `rescue nil` | every error, bugs in our own code included | catch the one named error; let the rest propagate |
| catch, log, continue | a partial result passed on as complete | log and rethrow, or return an error value the caller has to handle |
| `except Exception` or `catch (Exception)` around a long block | typos, null access and logic bugs inside the block | narrow the try to the one call that can fail and catch its specific type |
| `return []`, `return null`, `return 0` on error | "failed" looks the same as "nothing there" | raise, or return a result type with a distinct failure case |
| `a?.b?.run()` on a value that must exist | the call never happens and nobody hears | check presence and fail with a message naming the missing value |
| a logical-or fallback in JavaScript | a valid 0, "" or false replaced | `x ?? fallback`, or an explicit undefined check |
| a promise or task never awaited; `.catch(() => {})` | a rejection nobody receives | await it, or attach a handler that reports the failure |
| Go `v, _ := f()` | the error value | `if err != nil { return fmt.Errorf("load %s: %w", id, err) }` |
| Rust `.ok()`, `.unwrap_or_default()` on a fallible call | why it failed | `?` with context, or match on the error |
| shell without `set -euo pipefail`; an or-true suffix; a pipe into `tee` | a failed step in the middle of a script or pipeline | strict mode; test the exit code of the command that matters |
| a child process whose exit code is unread | the tool failed and the output is partial | check the code; treat non-zero as failure |
| retry with no limit, or on every error | a permanent error retried forever, load on a sick service | a bounded count with backoff, on transient errors only |
| a stub, mock or sample value returned when the real call fails | the outage, and where it started | the error, outside tests |
| a missing config value read as a permissive default | a gate that is open by accident | fail at startup and name the missing key |
| a longer timeout added to stop an error | the slow or hung dependency | find why it is slow; keep the timeout honest |
| a log line at debug level for a real failure | the failure, in every production log level | log at warning or error with the id involved |

## When a fallback is fine {#fine}

- The condition is expected and named: a cache miss, an optional file that may be absent, a feature the platform lacks.
- The fallback is visible: the user sees "showing cached data", or a metric or warning counts each use.
- The catch lists the error types it handles, and a comment says why each is safe to absorb.

## One question per catch {#question}

For each catch, default or retry, list the errors that could reach it. Any error on that list that the code does not name is one it hides.
