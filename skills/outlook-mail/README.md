# Outlook Mail Skill

Microsoft 365 (Outlook) mailbox integration for Sophon via Microsoft Graph — list, search, and read messages, browse folders, move messages, create drafts, and send mail. Uses app-only (client-credentials) auth against a single, explicitly configured mailbox.

## Tools

| Tool | Risk | Description |
|------|------|-------------|
| `mail.list_messages` | None | List recent messages in a folder (default inbox), newest first |
| `mail.search_messages` | None | Search the mailbox with a free-text phrase or an OData filter |
| `mail.get_message` | None | Read one message: plain-text body, recipients, attachment names/sizes/types |
| `mail.list_folders` | None | List mail folders with total and unread counts |
| `mail.move_message` | Medium | Move a message to another folder |
| `mail.create_draft` | Medium | Create a new or reply draft (never sends) |
| `mail.send_mail` | High | Send an email immediately (saved to Sent Items) |

List and search tools cap results at 50 per call and request only a trimmed field set (`$select`) to avoid Graph timeouts on large mailboxes.

## Setup

1. In the [Microsoft Entra admin center](https://entra.microsoft.com), create an **App registration** (single tenant). Note the **Directory (tenant) ID** and **Application (client) ID**.
2. Under **Certificates & secrets**, create a **client secret** and copy its value.
3. Under **API permissions**, add Microsoft Graph **Application** permissions: **Mail.Read** (read tools), **Mail.ReadWrite** (move and draft tools), and **Mail.Send** (sending). Then click **Grant admin consent** — an Entra admin must consent; without it every call fails with 403.
4. **Scope the app to specific mailboxes (strongly recommended and effectively mandatory for production):** app-only mail permissions are **tenant-wide by default** — the app can read and send mail as *every* mailbox in the organization. Use Exchange Online **RBAC for Applications** (which replaces the older `New-ApplicationAccessPolicy` approach) to restrict the app: create a management scope covering only the allowed mailbox(es) and assign the app a role like `Application Mail.Read` or `Application Mail.ReadWrite` against that scope, e.g. `New-ManagementRoleAssignment -App <clientId> -Role "Application Mail.ReadWrite" -CustomResourceScope <scope>`. See [Role Based Access Control for Applications in Exchange Online](https://learn.microsoft.com/en-us/exchange/permissions-exo/application-rbac).
5. In Sophon, open **Settings > Connections**, click **Connect** on the Outlook Mail card, and fill in the **Directory (Tenant) ID**, **Application (Client) ID**, **Client Secret**, and the **Mailbox (UPN/email)** the skill should operate on (app-only requires an explicit mailbox).
6. Test the connection.

## Usage Examples

> "Show me my 10 most recent unread emails"

> "Search my mailbox for messages about the Q3 invoice"

> "Open the latest email from anna@contoso.com and summarize it"

> "Archive that message"

> "Draft a reply thanking them and asking for the updated contract — don't send it yet"

## Requirements

- Microsoft 365 work/school tenant (app-only auth does not work with consumer outlook.com accounts)
- An Entra app registration with Mail.Read / Mail.ReadWrite / Mail.Send **application** permissions and admin consent
- Exchange Online admin access to configure RBAC for Applications mailbox scoping (see Setup)

## Trademarks

Outlook, Microsoft 365, and Microsoft Graph are trademarks of Microsoft Corporation. This project is not affiliated with or endorsed by Microsoft Corporation.

## License

MIT © 2026 Buildersoft LLC. See [LICENSE](LICENSE).
