# Inkling

Connect Inkling notes, todos, discussions and sourced answers to Sophon. This integration uses the Inkling API at `https://api.inkling.buildersoft.io/v1`.

## Connection

Pro users can create an API key in Inkling under **Settings > Integrations**. Connect the Inkling integration in Sophon with that key and grant the scopes required for the tools you intend to use. Requests use bearer authentication. See the [authentication reference](https://inkling.buildersoft.io/developers/authentication).

## Endpoint and risk matrix

Paths below are relative to the API base URL. Risk ratings reflect potential effects, not API scopes. Tool parameters use the names shown in the manifest.

| Tool | Endpoint | Required scope | Risk | Purpose |
|---|---|---|---|---|
| `inkling.usage` | `GET /usage` | any key | none | Read usage and key information |
| `inkling.list_notes` | `GET /notes` | `notes:read` | none | List and filter notes |
| `inkling.get_note` | `GET /notes/{id}` | `notes:read` | none | Read a note |
| `inkling.list_todos` | `GET /todos` | `todos:read` | none | List todos by view and tag |
| `inkling.ask` | `POST /ask` | `ask` | medium | Start an answer or continue a discussion |
| `inkling.get_answer` | `GET /answers/{id}` | `ask` | none | Read an answer's status and result |
| `inkling.list_discussions` | `GET /discussions` | `discussions:read` | none | List discussions |
| `inkling.get_discussion` | `GET /discussions/{id}` | `discussions:read` | none | Read a discussion |
| `inkling.create_note` | `POST /notes` | `notes:write` | high | Create a note; sharing can invite collaborators |
| `inkling.update_note` | `PATCH /notes/{id}` | `notes:write` | high | Update a note, potentially replacing its body |
| `inkling.append_note` | `POST /notes/{id}/append` | `notes:write` | medium | Append to a note |
| `inkling.archive_note` | `POST /notes/{id}/archive` | `notes:write` | medium | Archive a note |
| `inkling.create_todo` | `POST /todos` | `todos:write` | medium | Create a todo |
| `inkling.complete_todo` | `POST /todos/{id}/complete` | `todos:write` | medium | Complete a todo; a repeating todo may create its next occurrence |

## Usage examples

Call `inkling.list_notes` with `{"q":"project", "limit":20}`. To continue a page, pass the returned `next_cursor` as `cursor`. Call `inkling.ask` with `{"query":"What are the next steps?"}`, then pass the returned `id` to `inkling.get_answer`, optionally with `wait: 20`. For a body replacement, first read the note and call `inkling.update_note` with its `id`, new `body`, and `if_match` set to the returned `etag`.

To clear a note property, send it as an empty string: `{"id":"note_1","properties":{"due":""}}`. The skill sends it to the API as `null`. Members left out are kept.

For note creation, append, and todo creation, the optional `idempotency_key` parameter becomes the `Idempotency-Key` header. The key must be 1–255 printable ASCII characters. The server does not compare replayed bodies, so reuse a key only for the same intended operation. The skill returns response JSON, not HTTP response headers.

## Parameter contracts

The skill checks these rules locally and makes no request when one fails; the error names the field but never echoes your values. The API remains the authority for anything not listed here. Fields marked nullable accept `null`, which is sent to the API unchanged so a field can be cleared or reset; a field left out is not sent. The tool schema gives each parameter one type and no `null` (Gemini accepts a single type), so models normally leave a field out instead of sending `null`.

### Notes

- `create_note`: `title` is required and nonempty. `body`, `tags`, `properties`, `sources` and `share_with` are optional and nullable. `idempotency_key` is optional.
- `update_note`: `id` plus at least one of `title`, `body`, `tags`, `properties` and `sources`. `title` is nullable but cannot be an empty string. `body` replaces the whole text and needs `if_match`, even when it is `null`. For `properties`, a member left out is kept, and an empty string or `null` clears it.
- `append_note`: `id` and `body` (a string) are required; `sources` is nullable.
- `tags`: array of at most 50 nonempty strings, each without `#`.
- `properties`: an object with only `status`, `due` and `lead`, each nullable. `status` is `not_started`, `in_progress`, `waiting` or `done`. `due` is a real calendar date, `YYYY-MM-DD`. `lead` is `me` or `null` on creation; on update it is `me`, the key of a person on the note, or `null`. On update, an empty `status`, `due` or `lead` is sent as `null`.
- `sources`: array of at most 100 objects. `n` is required, an integer from 1 to 999, unique within the request. `url` is required, an `http` or `https` address of at most 2,048 characters. `title`, `snippet` and `published_date` are nullable strings. No other members are accepted.
- `share_with`: array of at most 9 objects with exactly `email` and `role` (`edit` or `view`). The API additionally requires each person to already be on one of the account's own notes.
- A create or update request can be at most 8 MiB once serialized as JSON. The developer reference states the limit for the body it takes; the skill applies it to the whole request.

### Todos

- `text` is required: 1–2,000 characters once whitespace is collapsed to single spaces. The text is sent as given; the API normalizes it.
- `note_id`, `due`, `priority` and `repeat` are optional and nullable. `note_id` is a nonempty string; omitted or `null` uses the Inbox. `due` is `YYYY-MM-DD`. `priority` is `1`, `2` or `null`. `repeat` is `daily`, `weekdays`, `weekly-1` to `weekly-7`, `monthly-1` to `monthly-31`, or `yearly-MM-DD`.
- `list_todos` takes `view` (`open`, `done` or `assigned`; default `open`), `tag` and `cursor`. `limit` is refused with an error rather than ignored.

### Ask and answers

- `ask`: `query` is required, 1–4,000 characters. `discussion_id` is a nonempty string or `null`; omitted or `null` starts a new discussion.
- `get_answer`: `id` is required; `wait` is an integer from 0 to 20.

## Pagination and asynchronous answers

Notes and discussions accept a `cursor` and an integer `limit`. The skill forwards `limit` as given and the API clamps it to 1–50; omitted, `null` or 0 and below means 20. Booleans, strings and decimals are rejected. Use the returned `next_cursor` to request the next page. Notes additionally support `q` (at most 200 characters), `tag`, `status` and `archived`; discussions support `archived`.

Todos accept `view` and `tag`, but not `limit`. Only the `done` view accepts a nonempty cursor. Omit `cursor` for the first page or for other views; an empty string is treated as omitted and is not sent to the API. For example, `{"view":"open","tag":"","cursor":""}` no longer fails local cursor validation. The `open` and `assigned` views return at most 1,000 items and indicate whether the result was truncated. Preserve and inspect the API's pagination and truncation fields.

Ask returns an answer ID immediately; its answer is written asynchronously, so read it with `get_answer`.

## Safe writes and availability

Note creation, note append and todo creation support `Idempotency-Key`; use the same key for a deliberate retry of the same operation. Replacing a note body requires `If-Match` with the note's etag, quoted or bare. The stored etag can lag an actively edited note, so it is not a guarantee that no live editing is underway. Creating a note with `share_with` can invite collaborators; check recipients before requesting the operation. Completing a repeating todo can create its next occurrence. Do not blindly retry mutations.

The published [developer route bundle](https://inkling.buildersoft.io/assets/developers-routes-lw5XUuSy.js) marks both write scopes as not offered, while the public [API information](https://inkling.buildersoft.io/api/public/api-info) has reported `write_enabled: true`. Whether users can currently issue write-scoped keys, and authenticated endpoint behavior, have not been verified. Live availability and quotas may change.

## Errors

Requests use a fixed API origin, path identifiers are encoded, redirects are refused, and mutations are never retried automatically. The API key is never included in any result.

- **Local validation** returns `{"error": "<message>"}` and sends nothing. An unknown tool and a missing connection return an error without a request.
- **HTTP errors** return `{"error": "Inkling API request failed", "status": <code>}`. When present and safe, the result also carries `retry_after` (a numeric `Retry-After` of at most 10 digits, in seconds), `code` and `correlation_id`.
  - `code` is the problem response's machine code, such as `insufficient_scope`, `if_match_required`, `etag_mismatch`, `note_live_busy`, `rate_limited` or `api_writes_disabled`. Switch on it rather than on the status. Quote `correlation_id` when contacting Inkling about a failed call.
  - These two members are returned only when they look like identifiers: `code` is lowercase letters, digits and underscores, at most 64 characters; `correlation_id` is letters, digits, hyphens and underscores, at most 128. A value containing the API key is dropped. The problem body is read up to 16 KiB; larger, non-JSON or unreadable bodies add nothing beyond the status. Human-readable text such as `title` and `detail`, and every other member, is not passed on.
  - Typical statuses: 401 and 403 for a bad key or missing scope, 409 `note_live_busy` (retry later), 412 `etag_mismatch` (read the note again), 428 `if_match_required`, 429 rate or allowance limits (`retry_after` when given), 503 when the API or writing is switched off.
- **Network failures and responses that are not valid JSON** return `{"error": "Inkling API request failed"}` without a status.

An empty successful response is returned as `null`. Calls have a 30-second request timeout inside a 45-second sandbox limit.

## License

MIT © Buildersoft LLC. See [LICENSE](LICENSE).
