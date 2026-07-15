# Notion

Interact with Notion from Sophon: search your workspace, read pages and their content blocks,
query databases, and create or update pages.

Implemented with the Notion REST API (`api.notion.com`, API version `2022-06-28`) over the Python
standard library (no dependencies), so it runs in the sandbox unchanged.

## Tools

| Tool | Risk | Description |
|------|------|-------------|
| `notion.search` | none | Search pages/databases shared with the integration (filter by page or database) |
| `notion.get_page` | none | Get a page's properties and metadata by id |
| `notion.get_block_children` | none | List the child blocks (content) of a page or block |
| `notion.query_database` | none | Query a database's rows with optional filter and sorts |
| `notion.create_page` | medium | Create a page under a database or a parent page |
| `notion.update_page` | medium | Update a page's properties, or archive/restore it |
| `notion.append_blocks` | medium | Append content blocks to the end of a page or block |

Reads return trimmed summaries (`id`, `title`/text, `url`); writes return `{id, url}`.

## Connection

Connect the **Notion** integration with:

- **Internal Integration Token** — create an
  [internal integration](https://www.notion.so/my-integrations) and copy its token. Share the target
  pages and databases with the integration so it can see them.

The token is stored in Sophon's credential vault and supplied to the skill at call time; it is never
written into the skill.

## Notes

- **You must share pages/databases with the integration.** An internal integration only sees content
  it has explicitly been shared with (open a page → **•••** → **Connections** → add your integration).
  Otherwise reads return nothing and writes fail with a permission error.
- `notion.create_page` needs either `parentDatabaseId` (creates a row) or `parentPageId` (creates a
  subpage). For a database row you can pass `title` as a convenience, which builds a minimal
  `{"Name": {"title": [...]}}` property — this assumes the database's title column is named **Name**.
  If it has a different title column, pass a raw `properties` object instead.
- `filter`/`sorts` on `notion.query_database` and `properties`/`children` on the write tools accept
  raw Notion API JSON objects; see the [Notion API reference](https://developers.notion.com/reference).
- Ids may be passed with or without dashes.

## Trademarks

Notion is a trademark of Notion Labs, Inc. This is an unofficial, independently built integration and
is not affiliated with or endorsed by Notion Labs.
