# OneDrive Skill

OneDrive for Business integration for Sophon via Microsoft Graph — browse folders, search and read files, create folders, upload text files, and create organization-scoped sharing links on a user's drive. Uses app-only (client-credentials) auth; works with Microsoft 365 work/school accounts only, not consumer OneDrive personal.

## Tools

| Tool | Risk | Description |
|------|------|-------------|
| `onedrive.list_folder` | None | List the files and folders in a folder (root by default) |
| `onedrive.search_files` | None | Search the drive for files and folders matching a text query |
| `onedrive.get_item` | None | Get metadata for a file or folder by item id or path |
| `onedrive.read_file` | None | Download a file's content as UTF-8 text (max 512 KB; text files only) |
| `onedrive.create_folder` | Low | Create a new folder (fails on name conflict instead of overwriting) |
| `onedrive.upload_file` | Medium | Upload text content as a file, creating or replacing it (max 1 MB) |
| `onedrive.create_share_link` | Medium | Create an organization-scoped view-only sharing link for an item |

## Setup

1. In the [Azure Portal](https://portal.azure.com), open **Microsoft Entra ID > App registrations** and create a new app registration (single tenant is fine). Note the **Directory (tenant) ID** and **Application (client) ID**.
2. Under **API permissions**, add **Microsoft Graph > Application permissions**:
   - `Files.Read.All` — required for the read tools (`list_folder`, `search_files`, `get_item`, `read_file`)
   - `Files.ReadWrite.All` — additionally required for the write tools (`create_folder`, `upload_file`, `create_share_link`)
3. Click **Grant admin consent** for your tenant — application permissions do not work without an administrator's consent.
   > **Warning:** `Files.Read.All` / `Files.ReadWrite.All` application permissions grant the app access to **every user's OneDrive in the tenant**, not just the configured user. Treat the client secret accordingly, and consider scoping access down with [Sites.Selected selected permissions](https://learn.microsoft.com/en-us/graph/permissions-selected-overview) if your organization requires it.
4. Under **Certificates & secrets**, create a **client secret** and copy its value immediately (it is shown only once).
5. In Sophon, open **Settings > Connections**, click **Connect** on the OneDrive card, and fill in:
   - **Directory (Tenant) ID** — from step 1
   - **Application (Client) ID** — from step 1
   - **Client Secret** — from step 4
   - **User (UPN/email)** — the OneDrive owner to operate on (e.g. `jane@contoso.com`); app-only auth always targets an explicit user's drive
6. Test the connection — the test calls the drive root (`/users/{userId}/drive`) to verify the credentials and the user's drive are reachable.

## Usage Examples

> "List the files in the Documents folder of my OneDrive"

> "Search OneDrive for the Q3 budget spreadsheet"

> "Read the contents of meeting-notes.txt from OneDrive and summarize it"

> "Upload this summary to OneDrive as Reports/summary-2026-07.txt"

> "Create an organization view link for that file so I can share it with the team"

## Requirements

- Microsoft 365 work/school tenant with OneDrive for Business — consumer OneDrive personal accounts are **not** supported by app-only auth
- An Azure app registration with `Files.Read.All` (read) and `Files.ReadWrite.All` (write) **application** permissions and admin consent; these grant tenant-wide drive access to every user's OneDrive, so an administrator must approve them
- The target user must be licensed for OneDrive and have a provisioned drive (they need to have accessed OneDrive at least once)
- `read_file` returns text files up to 512 KB; `upload_file` accepts up to 1 MB of text (Graph's simple upload allows up to 250 MB, but the sandbox does not)
- Microsoft Graph may throttle heavy usage with HTTP 429; the skill surfaces the `Retry-After` interval when Graph provides one

## Trademarks

OneDrive is a trademark of Microsoft Corporation. This project is not affiliated with or endorsed by Microsoft Corporation.

## License

MIT © 2026 Buildersoft LLC. See [LICENSE](LICENSE).
