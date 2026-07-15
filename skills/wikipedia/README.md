# Wikipedia

Search Wikipedia and read articles through the public [MediaWiki API](https://www.mediawiki.org/wiki/API:Main_page).
Full-text search, concise page summaries, and full article plaintext — in any Wikipedia language
edition.

Runs in the sandbox with **network access but no credentials** — Wikipedia's API is keyless. Every
request sends the descriptive `User-Agent` that Wikimedia's API etiquette policy requires. HTTP is
handled with the standard-library `urllib`; there are no third-party dependencies.

## Tools

| Tool | Risk | Description |
|------|------|-------------|
| `wikipedia.search` | none | Full-text search for articles; returns titles, plaintext snippets, and page ids |
| `wikipedia.get_summary` | none | Get the short description and lead extract of an article by title |
| `wikipedia.get_article` | none | Get the full plaintext extract of an article by title |

## Language

Every tool accepts an optional `language` parameter — a Wikipedia language edition code such as
`en`, `de`, `fr`, `es`, or `simple`. Requests go to `https://{language}.wikipedia.org`. The default
is `en`. Codes are validated against `[a-z-]{2,10}`.

## Notes

- **Missing pages** return `{"error": "page not found: <title>"}` rather than throwing.
- `wikipedia.search` snippets have their HTML tags stripped and entities unescaped.
- `wikipedia.get_summary` uses the REST `page/summary` endpoint and returns `{title, description,
  extract, url}`.
- `wikipedia.get_article` uses the Action API `prop=extracts` (plaintext, following redirects) and
  returns `{title, extract, url}`. Extracts longer than 40,000 characters are truncated, and the
  response then includes `"truncated": true` with a note.
- Each tool prints a single JSON object to stdout.

## Trademarks

Wikipedia is a registered trademark of the Wikimedia Foundation. This skill is an independent
client of the public MediaWiki API and is not affiliated with or endorsed by the Wikimedia
Foundation.
