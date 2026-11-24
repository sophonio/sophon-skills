---
id: eng-api-contract
summary: Contract questions for operations and shapes, one error shape, paging, idempotent writes, auth, versioning.
reviewed: 2026-11
---
# API contract checklist

Each line is a question the contract answers before code exists. An unanswered line is an open decision.

## Operations and shapes

- Which jobs do callers have, and which operation serves each? One operation per job, named for it.
- For each field: type, unit (ms or s, cents or units), format (ISO 8601 with offset), whether it can be null, absent or empty, and its limits.
- Ids: opaque strings, never row numbers; stable for the life of the object.
- What does the response include, and what must the caller fetch separately? No field exists only because the database has it.
- Collections: is the order defined? Default and allowed sort keys.
- Reads never change state; a read that has a side effect is a write.

## Errors

One error shape for every operation, for example:

```
{"error": {"code": "card_declined", "message": "The card was declined.", "field": "card_number", "retryable": false, "request_id": "..."}}
```

- `code` is stable and documented; `message` is for people and may change.
- The status or category tells apart: bad input, not signed in, not allowed, not found, conflict, rate limited, server fault.
- Not found and not allowed: the same answer when existence itself is private.
- No stack traces, SQL or internal names in an error body.

## Paging

- Cursor (an opaque token from the last page) for large or changing sets; offset only for small, stable ones.
- A default and a maximum page size; the server enforces the maximum.
- The response says whether more items exist and how to get them.
- Items added or deleted between pages: the cursor neither repeats nor skips them.

## Idempotent writes

- A create or charge accepts a client-chosen idempotency key; a repeat with the same key and body returns the first result.
- A repeat with the same key and a different body is an error.
- How long keys are kept, and what a retry after that window does.
- Updates: full replace or partial; concurrent edits detected by a version or ETag, with conflict as the answer.

## Auth

- Who may call each operation, and on whose data? The check happens on the server for every call.
- Scopes or roles per operation; the narrowest one that does the job.
- Object-level checks: an id from the caller is always matched to the caller's tenant or ownership.

## Versioning

- Additive changes (a new optional field, a new operation, a new enum value) keep the version; callers must ignore unknown fields.
- Breaking changes (a removed or renamed field, a new required input, a changed type, meaning or default) get a new version or a new operation.
- Is a new enum value breaking for existing callers? Say so in the contract.
- Deprecation: a notice in responses or docs, a date, and usage measured before removal.
