# SharePoint Skill

SharePoint Online integration for Sophon via Microsoft Graph — search and resolve sites, browse lists and document libraries, query and read list items, search files, and create or update list items using app-only (client-credentials) authentication.

## Tools

| Tool | Risk | Description |
|------|------|-------------|
| `sp.search_sites` | None | Search sites across the tenant by keyword |
| `sp.get_site` | None | Resolve a site by hostname + server-relative path |
| `sp.list_lists` | None | List a site's lists and document libraries |
| `sp.query_list_items` | None | Query list items (optional OData filter, paged) |
| `sp.get_list_item` | None | Get a single list item with all its fields |
| `sp.search_files` | None | Search the site's default document library for files |
| `sp.create_list_item` | Medium | Create a new list item |
| `sp.update_list_item` | Medium | Update fields of an existing list item |

## Setup

1. In the [Azure Portal](https://portal.azure.com), go to **Microsoft Entra ID > App registrations** and create a new app registration (single tenant is fine).
2. Note the **Application (client) ID** and **Directory (tenant) ID** from the app's Overview page.
3. Under **API permissions**, add **Microsoft Graph > Application permissions > Sites.Read.All**. To enable the write tools (`sp.create_list_item`, `sp.update_list_item`), also add **Sites.ReadWrite.All**. Note that these are tenant-wide grants — `Sites.ReadWrite.All` allows the app to write to every site in the tenant.
4. Click **Grant admin consent** — a tenant administrator must approve these application permissions before tokens will work.
5. Under **Certificates & secrets**, create a **client secret** and copy its value immediately (it is shown only once).
6. In Sophon, open **Settings > Connections**, click **Connect** on the SharePoint card, and enter the Directory (Tenant) ID, Application (Client) ID, and Client Secret, then test the connection.

Note: the connection test and `sp.search_sites` use `GET /sites?search=...`, which does **not** work with `Sites.Selected`-only grants — those tenants should resolve sites with `sp.get_site` (hostname + path) instead.

## Usage Examples

**Find a site:**
> "Find our Marketing SharePoint site"

**Browse a site's lists:**
> "What lists are on the site contoso.sharepoint.com/sites/Marketing?"

**Query list items:**
> "Show me the items in the Vacation Requests list where Status is Pending"

**Search for files:**
> "Search the Marketing site's documents for the Q3 campaign brief"

**Create an item:**
> "Add an item titled 'Renew hosting contract' to the Tasks list on the Ops site"

## Requirements

- SharePoint Online (Microsoft 365 work/school tenant) — app-only auth does not work with personal accounts
- An Azure AD app registration with a client secret and **Sites.Read.All** application permission granted with **admin consent**
- Tenant-wide **Sites.ReadWrite.All** application permission for the write tools (`sp.create_list_item`, `sp.update_list_item`)
- `Sites.Selected`-only grants are not sufficient for `sp.search_sites` (site search is locked down); use `sp.get_site` to resolve sites by URL instead
- OData `$filter` on list item fields generally requires the filtered column to be indexed in SharePoint; Graph's error message is surfaced as-is when it is not

## Trademarks

SharePoint is a trademark of Microsoft Corporation. This project is not affiliated with or endorsed by Microsoft Corporation.

## License

MIT © 2026 Buildersoft LLC. See [LICENSE](LICENSE).
