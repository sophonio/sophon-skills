---
id: eng-adr
summary: The three-part test with decisions that pass and fail it, the short record form, optional fields, two worked records.
reviewed: 2026-11
---
# Decision records: the gate, the short form, worked examples

A decision record earns its place when all three hold: the decision is hard to reverse, a newcomer would be surprised by it without the context, and it came from a real trade-off between workable options.

## Three-part gate

| Decision | Hard to reverse | Surprising | Trade-off | Record |
|---|---|---|---|---|
| Store money as integer minor units, not decimals | yes: every column and API | yes | yes: precision against convenience | yes |
| Use PostgreSQL row-level security for tenant isolation | yes | yes | yes: safety against query flexibility | yes |
| Call the payment provider synchronously, no queue | medium | yes | yes: simplicity against resilience | yes |
| Use the HTTP client the project already uses | no | no | no | no: a line in Approach |
| Rename a private helper | no | no | no | no |
| Adopt a formatter with default settings | no | no | barely | no |
| Pick library A over B for PDFs, both fine, easy to swap | no | no | yes | no: a line in Approach |

## Short form

```
# NNNN Title in plain words: the decision, not the question
Status: accepted
<1-3 sentences: the context that forced a choice, what was decided, and why this option over the strongest other one.>
```

Optional, only when they carry weight: Considered options (one line each); Consequences (what gets harder); Confirmation (how compliance is checked: a test, a lint rule, a review question). A record holds no implementation plan and no task list.

Superseding: the old record keeps its text and gets `Status: superseded by NNNN`; the new one names the record it replaces in its first sentence.

## Worked records

```
# 0007 Store money as integer minor units
Status: accepted
Floating-point totals drifted by a cent in refunds, and decimals are handled differently by each driver we use. We store and pass every amount as an integer count of the currency's minor unit with an ISO 4217 code beside it, because integer arithmetic is exact in every language we run and the conversion happens only at display.
```

```
# 0012 Call the payment provider synchronously
Status: accepted
Checkout needs the payment result before it can show the order page, and our volume is under ten payments a minute. We call the provider inside the request with a 10 s timeout and an idempotency key, instead of a queue and a polling page, because one code path is easier to run than a worker; we revisit this when volume passes a hundred a minute or the provider's latency exceeds the timeout.
```
