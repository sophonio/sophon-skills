# Airtable

Interact with an Airtable base from Sophon: list and read records, and create, update, or delete
them.

Implemented with the Airtable REST API v0 (`api.airtable.com/v0`) over the Python standard library
(no dependencies), so it runs in the sandbox unchanged.

## Tools

| Tool | Risk | Description |
|------|------|-------------|
| `airtable.list_records` | none | List records from a table, with optional formula filter, view, and paging |
| `airtable.get_record` | none | Get a single record by id |
| `airtable.create_record` | medium | Create a new record from a fields object |
| `airtable.update_record` | medium | Partially update a record's fields |
| `airtable.delete_record` | high | Delete a record (irreversible) |

Reads and writes return `{id, fields, createdTime}` per record. `airtable.list_records` returns
`{records: [...], offset?}` — pass the `offset` back in to fetch the next page.

## Connection

Connect the **Airtable** integration with:

- **Personal Access Token** — create a scoped
  [personal access token](https://airtable.com/create/tokens) with `data.records:read` and
  `data.records:write` access to the base you want to use.
- **Base ID** — the id of your base (starts with `app`), shown in the base's API documentation.

The token and base id are stored in Sophon's credential vault and supplied to the skill at call
time; they are never written into the skill.

## Notes

- `table` accepts either a table name (e.g. `Tasks`) or a table id (e.g. `tblXXXXXXXXXXXXXX`); the
  value is URL-encoded into the request path, so names with spaces work.
- `filterByFormula` takes an Airtable formula string, e.g. `{Status}='Done'`.
- `pageSize` is capped at 100 records per page; use the returned `offset` to page through more.
- `airtable.update_record` is a partial PATCH — only the fields you pass are changed; others are
  left untouched.

## Trademarks

Airtable is a trademark of Formagrid, Inc. This is an unofficial, independently built integration
and is not affiliated with or endorsed by Airtable.
