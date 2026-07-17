# Dynamics 365 Skill

Microsoft Dynamics 365 (Dataverse) integration for Sophon — query, read, create, and update
records via the Dataverse Web API, inspect entity metadata, and attach notes. Uses app-only
OAuth2 client-credentials auth: tokens are minted per invocation with scope
`{environmentUrl}/.default` (the Dataverse environment, not Microsoft Graph), and all calls go to
`{environmentUrl}/api/data/v9.2`. Reads request formatted display values, so lookups, option-sets,
money, and dates come back human-readable alongside the raw values.

## Tools

| Tool | Risk | Description |
|------|------|-------------|
| `dynamics.query_records` | None | Query an entity set with OData `$filter`/`$select`/`$orderby` (max 50 records) |
| `dynamics.get_record` | None | Get a single record by GUID |
| `dynamics.whoami` | None | Verify the connection (UserId, BusinessUnitId, OrganizationId) |
| `dynamics.list_entity_fields` | None | List an entity's readable attributes for query construction |
| `dynamics.create_record` | Medium | Create a record (lookups via `@odata.bind`, option-sets as integers) |
| `dynamics.update_record` | Medium | Update a record (`If-Match: *` prevents accidental create) |
| `dynamics.add_annotation` | Low | Attach a note (annotation) to a record |

## Setup

Setup spans two portals — the Microsoft Entra admin center and the Power Platform admin center:

1. **Register an app in Microsoft Entra** ([entra.microsoft.com](https://entra.microsoft.com)):
   go to **App registrations > New registration**, note the **Application (client) ID** and
   **Directory (tenant) ID**, then create a **client secret** under **Certificates & secrets**.
   You do **not** need to add any API permissions — Microsoft's docs are explicit that
   server-to-server Dataverse access is authorized by the Application User's security role, not
   by API permissions on the app registration.
2. **Create an Application User in the Power Platform admin center**
   ([admin.powerplatform.microsoft.com](https://admin.powerplatform.microsoft.com)): open your
   environment, go to **Settings > Users + permissions > Application users > + New app user**,
   and bind it to the client ID from step 1.
3. **Assign a Dataverse security role** to that Application User (e.g. a custom role, or a
   built-in role broad enough for the records you want the skill to reach). The skill can only do
   what this role allows.
4. In Sophon, go to **Settings > Connections**, click **Connect** on the Dynamics 365 card, and
   enter the **Tenant ID**, **Client ID**, **Client Secret**, and your **Environment URL**
   (e.g. `https://org12345.crm.dynamics.com` — find it in the Power Platform admin center under
   the environment's details). Test the connection (it calls `WhoAmI`).

Access tokens last about 60 minutes; the skill mints a fresh one on every invocation, so no token
management is needed. Dataverse service-protection limits may return HTTP 429 — the skill
surfaces the `Retry-After` interval when that happens.

## Usage Examples

**Query records:**
> "Find the top 10 Dynamics accounts with revenue over $100k, ordered by name"

**Inspect a record:**
> "Show me the Dynamics account 3f2504e0-4f89-41d3-9a0c-0305e82c3301"

**Discover fields:**
> "What fields can I query on the opportunity entity in Dynamics?"

**Create a record:**
> "Create a Dynamics contact named Jane Doe at Contoso with email jane@contoso.com"

**Attach a note:**
> "Add a note to that account: 'Renewal call scheduled for Friday'"

## Requirements

- A Microsoft Dataverse environment (Dynamics 365 Sales/Service/etc., or a Power Platform
  environment with Dataverse) — consumer accounts are not supported
- Permission to register an app in Microsoft Entra and to administer the Power Platform
  environment (create Application Users, assign security roles)
- Appropriate Dynamics 365 / Power Apps licensing for your tenant; API calls are subject to
  Microsoft's Dataverse service-protection and request limits

## Trademarks

Microsoft, Dynamics 365, Dataverse, and Microsoft Entra are trademarks of the Microsoft group of
companies. This skill is an independent integration developed by Buildersoft LLC and is not
affiliated with, endorsed by, or sponsored by Microsoft Corporation.

## License

MIT © 2026 Buildersoft LLC. See [LICENSE](LICENSE).
