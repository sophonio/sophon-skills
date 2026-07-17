# Microsoft Entra ID Skill

Microsoft Entra ID (Azure AD) directory integration for Sophon via Microsoft Graph — search users and groups, inspect profiles and memberships, list admin-role members, review sign-in logs, and spot expiring app-registration secrets. All tools are read-only and use app-only (client-credentials) auth.

## Tools

| Tool | Risk | Description |
|------|------|-------------|
| `entra.search_users` | None | Search users by display name or email ($search or prefix filter) |
| `entra.get_user` | None | Get a user's profile including their manager |
| `entra.list_user_groups` | None | List the groups a user is a direct member of |
| `entra.search_groups` | None | Search groups by display name |
| `entra.list_group_members` | None | List a group's direct members (paginated, capped at 200) |
| `entra.list_role_members` | None | List members of an activated directory role (e.g. Global Administrator) |
| `entra.list_signin_logs` | None | List sign-in log entries since a given time (capped at 50) |
| `entra.list_applications` | None | List app registrations with client-secret expiry dates |

## Setup

1. In the [Microsoft Entra admin center](https://entra.microsoft.com) (or Azure portal), go to **Identity > Applications > App registrations** and click **New registration** (any name, no redirect URI needed)
2. On the app's **Overview** page, note the **Application (client) ID** and **Directory (tenant) ID**
3. Under **API permissions**, click **Add a permission > Microsoft Graph > Application permissions** and add **Directory.Read.All**; also add **AuditLog.Read.All** if you want sign-in logs
4. Click **Grant admin consent** for your tenant — this requires a Global Administrator or Privileged Role Administrator; without admin consent every call will fail with an authorization error
5. Under **Certificates & secrets**, create a **New client secret** and copy its value immediately (it is only shown once)
6. Note: sign-in logs (`entra.list_signin_logs`) additionally require the tenant to have a Microsoft Entra ID P1 or P2 license — on free tenants the API returns a license error
7. In Sophon, open **Settings > Connections**, click **Connect** on the Microsoft Entra ID card, and enter the Tenant ID, Client ID, and Client Secret, then test the connection

## Usage Examples

**Find a colleague:**
> "Look up Jane Doe in the directory and tell me her department and manager"

**Audit group membership:**
> "Who is in the 'Engineering' group in Entra?"

**Check admin roles:**
> "List everyone with the Global Administrator role"

**Investigate sign-ins:**
> "Show failed sign-ins for bob@contoso.com since yesterday"

**Flag expiring secrets:**
> "List our app registrations and flag any client secrets expiring this quarter"

## Requirements

- A Microsoft Entra ID (work/school) tenant — consumer Microsoft accounts are not supported
- An app registration with the **Directory.Read.All** application permission and admin consent granted
- **AuditLog.Read.All** application permission (with admin consent) and a **Microsoft Entra ID P1/P2** license for sign-in logs
- Granting admin consent requires a Global Administrator or Privileged Role Administrator

## Trademarks

Microsoft, Microsoft Entra, and Microsoft Graph are trademarks of the Microsoft group of companies. This project is not affiliated with or endorsed by Microsoft Corporation.

## License

MIT © 2026 Buildersoft LLC. See [LICENSE](LICENSE).
