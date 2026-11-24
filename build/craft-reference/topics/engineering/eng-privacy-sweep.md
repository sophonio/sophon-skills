---
id: eng-privacy-sweep
summary: Kinds of personal data; a field sheet (purpose, flow, retention, deletion, access) with where to look; leak points.
reviewed: 2026-11
---
# Privacy sweep: personal data fields and flows

Personal data is any value that identifies a person or can be tied back to one. A sheet cell the code cannot fill stays open.

## Kinds of personal data {#kinds}

- Direct identifiers: name, email address, phone number, postal address, government or customer number, photo.
- Account data: user id, username, password hash, sign-in history, roles.
- Device and network: IP address, device id, advertising id, cookie ids, user agent with a stable fingerprint.
- Location: GPS coordinates, a city derived from IP, addresses in deliveries.
- Behaviour: page views, searches, clicks, purchases, messages sent.
- Special care: health, biometrics, religion, political views, sexual life, union membership, children's data, precise location, financial account numbers.
- Free text: notes, support tickets, chat messages, file names, prompts. Any of it can hold any of the above.
- Derived: scores, segments, inferred interests, model embeddings of a person's text.

## Field sheet

| Field | Purpose | Flows | Retention | Deletion | Access |
|---|---|---|---|---|---|
| `email` | sign-in and receipts (`AuthService`, `ReceiptMailer`) | users table; mail provider; error tracker breadcrumbs | while the account exists | account delete removes the row; mail provider copy not handled | support role through the admin screen |

Where the code answers each question:

| Question | Where to look |
|---|---|
| Purpose | the features that read the field; a field written but never read has no purpose in the code |
| Flows | ORM models and migrations; log and analytics calls; outbound HTTP clients and SDK setup; export jobs; caches and search indexes |
| Retention | TTL settings, cleanup jobs, partition drops, backup schedules; no job means kept forever |
| Deletion | the delete handler and what it cascades to; soft-delete flags; copies in caches, indexes, backups and third parties |
| Access | route guards, roles and row filters on queries that return the field; admin and support tools; database users |

## Leak points

| Leak point | Sign in the code |
|---|---|
| logs and traces | a whole request, user or order object logged; personal fields in span attributes |
| error trackers | request bodies and local variables attached to error events by default |
| analytics events | email or name as a property or user key; full URLs that carry personal values |
| URLs | personal values in query strings, which land in server logs, proxies and browser history |
| caches and CDNs | personal responses cached without a per-user key or a private cache rule |
| exports and reports | CSV or spreadsheet jobs with more columns than the reader needs |
| search indexes and copies | data indexed or replicated with no matching delete path |
| test fixtures and seed data | copies of real records in the repository |
| third-party SDKs and model calls | personal text passed to an outside API with no note of what the provider keeps |
| soft delete | a flag set, the row and its personal fields kept |
