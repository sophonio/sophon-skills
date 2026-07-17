# Tableau Skill

Tableau integration for Sophon — browse workbooks, views, and published data sources, pull view data as structured rows, search content by name, watch background jobs, and trigger full extract refreshes via the Tableau REST API (v3.23, PAT auth).

## Tools

| Tool | Risk | Description |
|------|------|-------------|
| `tableau.list_workbooks` | None | List workbooks with project, owner, update time, and web URL |
| `tableau.list_views` | None | List views on the site or within one workbook |
| `tableau.list_datasources` | None | List published data sources |
| `tableau.get_view_data` | None | Get a view's underlying data as columns/rows (capped, with truncated flag) |
| `tableau.search_content` | None | Search workbooks, views, and data sources by name (case-insensitive substring, matched client-side over the first 100 items of each type) |
| `tableau.list_jobs` | None | List background jobs for refresh-failure triage |
| `tableau.refresh_datasource` | Medium | Trigger a FULL extract refresh of a data source (queues a background job) |

## Setup

1. Sign in to Tableau Cloud or Tableau Server as the user the skill should act as (its permissions decide what content is visible and refreshable).
2. On Tableau Server, an administrator must have Personal Access Tokens enabled (they are on by default; check **Server Settings** if token creation is unavailable). On Tableau Cloud, PATs are always available unless your site admin has disabled them.
3. Go to **My Account Settings > Personal Access Tokens**, enter a token name, and click **Create Token**. Copy the secret immediately — it is shown only once. Note: PATs expire if unused for 15 consecutive days (up to 1 year with use, configurable on Server).
4. Find your site content URL: it is the value after `/site/` in your Tableau browser URL (e.g. `mysite` in `https://10ax.online.tableau.com/#/site/mysite/home`). On Tableau Server, leave it empty for the default site; on Tableau Cloud it is always required.
5. This skill pins REST API version 3.23, so your server must be Tableau Server 2024.2 or later (Tableau Cloud always qualifies).
6. In Sophon, go to **Settings > Connections**, click **Connect** on the Tableau card, and enter the Tableau URL, site content URL (or leave empty), PAT name, and PAT secret, then test the connection (the test performs the sign-in exchange itself).

## Usage Examples

**Browse content:**
> "List my Tableau workbooks and who owns them"

**Pull data:**
> "Get the data behind the Sales Overview view in Tableau"

**Find content:**
> "Search Tableau for anything named 'churn'"

**Triage refreshes:**
> "Show recent Tableau background jobs — did any extract refreshes fail?"

**Refresh:**
> "Kick off a full refresh of the Orders data source in Tableau"

## Requirements

- Tableau Cloud, or Tableau Server 2024.2+ (REST API 3.23)
- A Personal Access Token for a user with access to the relevant site content
- `tableau.refresh_datasource` requires the data source to have an extract and the PAT user to have refresh permissions; it always performs a full refresh
- `tableau.get_view_data` returns the view's summary data as CSV parsed into rows; large views are truncated at the row cap

## Trademarks

Tableau is a trademark of Salesforce, Inc. and/or its affiliates. This skill is an independent integration developed by Buildersoft LLC and is not affiliated with, endorsed by, or sponsored by Salesforce or Tableau.

## License

MIT © 2026 Buildersoft LLC. See [LICENSE](LICENSE).
