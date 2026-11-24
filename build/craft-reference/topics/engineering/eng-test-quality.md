---
id: eng-test-quality
summary: Tests that cannot fail, with repairs; where expected values come from; what to mock; boundary value tables.
reviewed: 2026-11
---
# Test quality: tautology, vacuity, boundaries, examples

A test is worth keeping when a plausible change to the code under test would turn it red. The examples below fail that bar, and each has a repair.

## Tautology and vacuity

A tautology recomputes the answer the same way the code does, so code and test are wrong together. A vacuous test runs, passes and checks nothing that matters.

| Test | Why it cannot fail | Repair |
|---|---|---|
| `expect(price(item)).toBe(item.base * (1 + TAX))` | the formula is copied from the implementation | a literal from a worked example: `price({base: 100})` is `120` |
| `expect(sorted(xs)).toEqual(xs.slice().sort())` | the oracle is the same library sort the code calls | a hand-written input and its known sorted output |
| a mock returns `42`, then the test asserts the result is `42` | it tests the mock | assert what the code does with the value: the label, the total, the call it makes next |
| `expect(result).toBeDefined()` | almost any return passes | assert the fields and values the caller relies on |
| a loop of assertions over `filter(items, rule)` where the rule matches nothing | zero iterations, zero assertions | assert the count first, then the contents |
| `try { run(); } catch (e) { expect(e).toBeTruthy(); }` | passes when `run()` throws nothing | the runner's "expect to throw" form with the error type and message |
| a snapshot of a whole page accepted on first run | the snapshot is whatever the code produced | small snapshots of a reviewed output, or explicit assertions |
| an async test with no `await` on the assertion | finishes before the check runs | await the promise; many runners can require a minimum assertion count |
| a property test whose generator yields only valid, small inputs | the interesting inputs never appear | widen the generator to edges: empty, maximum, Unicode, negatives |

Where an expected value comes from, strongest first: a specification or standard; a worked example a person checked by hand; a second, independent implementation; a previous release's output that someone reviewed. The code under test is never the source.

## Naming the break {#naming}

A good test name says what breaks when it fails: `rejects an expired coupon`, `keeps the cart when the session renews`. A name like `test_coupon_2` hides which behaviour went missing. If no break can be named for a test, it is a candidate for deletion.

Quick check for a new test: invert one condition it is meant to cover (drop a `!`, swap `<` and `<=`). The test should go red. If it stays green, it does not cover that condition.

## What to mock

| Dependency | Mock it? | Why |
|---|---|---|
| a third-party HTTP API, payment provider, email or SMS gateway | yes | slow, costly or not under our control; record the request and assert on it |
| the clock and random numbers | yes, through an injected source | results must repeat run after run |
| the file system | usually no; use a temporary directory | real paths catch real encoding and permission bugs |
| our own database | prefer a real instance (container or in-memory engine of the same kind) | query and constraint bugs live there |
| our own classes and modules | no | a mock of our own code freezes its current design and hides the bugs between the parts |
| a message queue we own | a fake with the same interface, or a real local broker | ordering and redelivery matter |

Mock at the edge of the system, through the same interface production uses. A test that needs many mocks to run points at a design problem, not a testing one.

## Boundary values

| Input kind | Values to try |
|---|---|
| integer range [min, max] | min - 1, min, min + 1, a typical value, max - 1, max, max + 1 |
| count or length | 0, 1, 2, the limit, limit + 1 |
| string | empty, one character, whitespace only, the maximum length, multi-byte characters, a combining accent, an emoji |
| collection | empty, one item, duplicates, unsorted, the page size, page size + 1 |
| optional value | absent, null, present but empty, present |
| date and time | month end, 29 February, a DST change, midnight, two time zones, a far-future year |
| money and decimals | 0, the smallest unit, a value that does not round cleanly (0.1 + 0.2), negative, very large |
| identifiers | unknown id, an id of another user or tenant, malformed id |
| concurrency | two writes to the same record, a retry of the same request |

One behaviour per test: when a boundary table yields many cases, use the runner's parameterised form so each case reports on its own.
