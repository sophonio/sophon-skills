# Confluence Skill

Atlassian Confluence integration for Sophon — search pages, manage content and spaces.

## Tools

| Tool | Risk | Description |
|------|------|-------------|
| `confluence.search` | None | Search pages and content using CQL |
| `confluence.get_page` | None | Get a page by ID with full content |
| `confluence.create_page` | Medium | Create a new page in a space |
| `confluence.update_page` | Medium | Update an existing page (auto-fetches version) |
| `confluence.list_spaces` | None | List all accessible spaces |
| `confluence.add_comment` | Low | Add a footer comment to a page |

## Setup

1. Go to **Settings > Connections** in the Sophon Dashboard
2. Click **Connect** on the Confluence card
3. Enter your Atlassian Cloud URL (e.g. `https://yourorg.atlassian.net`)
4. Enter your email and API token
5. Test the connection

Generate an API token at: https://id.atlassian.com/manage-profile/security/api-tokens

## Usage Examples

**Search for pages:**
> "Search Confluence for pages about deployment procedures"

**Read a page:**
> "Get the contents of Confluence page 12345"

**Create a page:**
> "Create a new Confluence page in the Engineering space titled 'Release Notes v2.0'"

**Update a page:**
> "Update Confluence page 12345 with the new API documentation"

**List spaces:**
> "Show me all available Confluence spaces"

**Add a comment:**
> "Add a comment to Confluence page 12345 saying 'Reviewed and approved'"

## Requirements

- Atlassian Cloud instance with Confluence
- API token with read/write access to Confluence

## Trademarks

Confluence is a trademark of Atlassian Pty Ltd. This skill is an independent integration developed by Buildersoft LLC and is not affiliated with, endorsed by, or sponsored by Atlassian.

## License

MIT © 2026 Buildersoft LLC. See [LICENSE](LICENSE).
