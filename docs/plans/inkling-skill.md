# Inkling skill implementation notes

## Approach

Create a first-party Python skill under `skills/inkling/` with a manifest, entrypoint, README and MIT license. Follow the Todoist injected-credential pattern: declare matching integration and credential services, use `access: injected`, read the exact camelCase credential key at module scope, and read tool arguments inside handlers. Use the standard library for HTTP and JSON. Implement the documented API contracts rather than guessing additional operations; preserve response fields, pagination cursors, and truncation indicators.

## Endpoint coverage and risk

The manifest and runtime declare the following routes. Paths are relative to `https://api.inkling.buildersoft.io/v1`; authenticated service behavior remains unverified.

| Method and path | Scope | Risk |
|---|---|---|
| GET /usage | any key | none |
| GET /notes | notes:read | none |
| GET /notes/{id} | notes:read | none |
| GET /todos | todos:read | none |
| POST /ask | ask | medium |
| GET /answers/{id} | ask | none |
| GET /discussions | discussions:read | none |
| GET /discussions/{id} | discussions:read | none |
| POST /notes | notes:write | high: sharing can invite collaborators |
| PATCH /notes/{id} | notes:write | high: can replace note body |
| POST /notes/{id}/append | notes:write | medium |
| POST /notes/{id}/archive | notes:write | medium |
| POST /todos | todos:write | medium |
| POST /todos/{id}/complete | todos:write | medium |

Notes and discussions use cursor pagination. The API clamps an integer `limit` to 1–50 and treats a missing value or 0 and below as 20; the skill forwards integers unchanged and rejects non-integers, including booleans. Notes support q (at most 200 characters), tag, status and archived filters; discussions support archived. Todos use view and tag, have no limit parameter (the skill rejects one explicitly), and only the done view accepts a cursor; open and assigned views can report truncation at 1,000. Ask accepts a query of 1–4,000 characters and a nullable discussion_id, and returns an answer ID asynchronously; answer reads accept wait of 0–20 seconds. Support Idempotency-Key for note creation, append and todo creation; require If-Match for note-body replacement. An etag can lag live editing. Completing a repeating todo can create its next occurrence.

## Write-field contracts

Extracted from the developer bundle (`CreateNoteRequest`, `UpdateNoteRequest`, `AppendNoteRequest`, `ApiPropertiesRequest`, `ApiPropertiesUpdateRequest`, `ApiSourceRequest`, `ApiShareRequest`, `CreateTodoRequest`, `AskRequest`) and enforced locally, with the same shapes declared in the manifest.

| Field | Contract |
|---|---|
| note `title` | create: required, nonempty. update: nullable, an empty string is refused. The bundle states no length limit. |
| note `body` | create and update: nullable string. Update needs `If-Match` whenever `body` is sent. Append: required string. |
| `tags` | nullable array of at most 50 nonempty strings without `#`. |
| `properties` | nullable object with only `status` (not_started, in_progress, waiting, done), `due` (YYYY-MM-DD, a real date) and `lead`, each nullable. `lead`: `me` or null on create; `me`, a person key or null on update. On update a missing member keeps its value and null clears it. |
| `sources` | nullable array of at most 100 objects: `n` integer 1–999 required and unique, `url` http or https at most 2,048 characters required, nullable string `title`, `snippet`, `published_date`. |
| `share_with` | nullable array of at most 9 objects with `email` and `role` (edit or view), both required. Create only. |
| note request size | At most 8 MiB. The bundle words this for the body taken; the skill applies it to the serialized create or update request. |
| todo `text` | Required, 1–2,000 characters after whitespace normalization. |
| todo `note_id`, `due`, `priority`, `repeat` | Nullable. `priority` is 1 or 2. `repeat` is daily, weekdays, weekly-1 to weekly-7, monthly-1 to monthly-31 or yearly-MM-DD. |
| `discussion_id` | Nullable string. |

Rulings: a null update `title` is allowed because the bundle marks it nullable; `If-Match` is required whenever `body` is present, even when null; unknown extra tool parameters are ignored as before.

## Security and verification

Use a fixed trusted API origin, URL-encode path identifiers, prevent redirects from forwarding the bearer key, never log it, and do not automatically retry mutations. HTTP errors return the status, a numeric Retry-After, and the problem response's `code` and `correlation_id` only when they match bounded identifier patterns (code: lowercase letters, digits and underscores, at most 64 characters; correlation_id: letters, digits, hyphens and underscores, at most 128) and do not contain the API key. The problem body is read up to 16 KiB; larger, non-JSON or unreadable bodies add nothing. Server text is never returned. The sandbox timeout is 45 seconds, above the 30-second request timeout. No authenticated live calls or mutations are authorized for verification.

Add offline request-mocked tests covering the 14 routes, nested schemas, nullable fields, argument and header handling, limit handling, pagination, response preservation, error handling and redirect protection. Run the offline tests, `pwsh -File build/Build-MarketplacePackages.ps1 -ValidateOnly`, and `pwsh -File build/Build-MarketplacePackages.ps1 -Skills inkling` if practical. The build overwrites an existing artifact of the same name; inspect the target first. Do not publish, commit, or change branches.

The mocked suite in `tests/inkling/test_inkling.py` covers the 14 route mappings, manifest and handler parity, nested schemas, null clearing, about 90 invalid-field cases that make no request, limit semantics, the 8 MiB boundary, header errors, HTTP 401, 403, 409, 412, 428, 429 and 503 with code and correlation members, key redaction and bounds, non-JSON and oversized error bodies, invalid success bodies, unknown tools, a missing key, and the absence of retries. `python -W error::ResourceWarning -m unittest discover -s tests/inkling -p test_inkling.py` reported 25 tests, OK. Targeted validation with `pwsh -NoProfile -File build/Build-MarketplacePackages.ps1 -Skills inkling -ValidateOnly` reported OK. Rebuilding the package and the full validator are recorded below once run; live service verification remains a separate step.

## Known gaps and sources

The version stays 1.0.0 to match the scoped artifact `dist/inkling-1.0.0.sophon-skill`. `CONTRIBUTING.md` asks for a patch bump when a skill file changes, so bump it before publishing if 1.0.0 was already uploaded.

The [developer route bundle](https://inkling.buildersoft.io/assets/developers-routes-lw5XUuSy.js) marks `notes:write` and `todos:write` as not offered, while the public [API information](https://inkling.buildersoft.io/api/public/api-info) reported `write_enabled: true`. Actual issuance of write-scoped keys and authenticated behavior remain unverified. The [authentication page](https://inkling.buildersoft.io/developers/authentication) is a JavaScript-rendered application; the prior research report identifies Pro key creation under Settings > Integrations and bearer authentication. The bundle and live information may change; offline tests cannot prove live availability or service behavior.

## Final verification

- `python -W error::ResourceWarning -m unittest discover -s tests/inkling -p test_inkling.py` → exit 0, 25 tests, OK.
- `pwsh -NoProfile -File build/Build-MarketplacePackages.ps1 -Skills inkling` → exit 0, rebuilt `dist/inkling-1.0.0.sophon-skill` (SHA-256 `3ee3f47ce7d7d6dd99e318970cb63b6b0f8d3670c1a1c9d4a0985d5f4b488f72`; `LICENSE`, `main.py`, `manifest.json` and `README.md` at the archive root).
- `pwsh -NoProfile -File build/Build-MarketplacePackages.ps1 -ValidateOnly` (every skill) → exit 0; the warnings seen in its tail belong to other skills (`oracle`, `postgres` unused connection fields).
- Nothing was committed or published. Live authenticated behavior is unverified.
