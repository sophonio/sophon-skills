# ServiceNow Skill

ServiceNow integration for Sophon — search and read records in any Table API table (incidents, changes, requests, CMDB CIs), search published knowledge articles, look up users and groups, create incidents, update records, and add work notes on your own ServiceNow instance.

## Tools

| Tool | Risk | Description |
|------|------|-------------|
| `snow.search_records` | None | Search any table (incident, change_request, sc_request, cmdb_ci, ...) with an encoded query |
| `snow.get_record` | None | Get a single record by table and sys_id, with display values |
| `snow.search_knowledge` | None | Search published knowledge base articles by text |
| `snow.get_user` | None | Look up a user or group by name/email for routing (caller_id, assignment_group) |
| `snow.create_incident` | Medium | Create a new incident |
| `snow.update_record` | Medium | Update fields of an existing record in any table |
| `snow.add_work_note` | Medium | Add a work note to an incident (journal entries are immutable once written) |

## Setup

The skill supports two authentication paths. Set up **one** of them, then fill in the connection card.

### Option A — OAuth2 client credentials (recommended)

1. Have a ServiceNow admin enable the client-credentials grant: set the system property `glide.oauth.inbound.client.credential.grant_type.enabled` to `true` (**sys_properties.list**; create the property if it does not exist).
2. In **System OAuth > Application Registry**, click **New** and choose **"OAuth API endpoint for external clients"**. Give it a name, keep it **confidential** (public unchecked), and leave the redirect URL empty (client-credentials needs no redirect). Note the generated **Client ID** and **Client Secret**.
3. On the registry record, set the linked **OAuth Application User** — a dedicated service account under whose identity (roles and ACLs) all API calls will run.
4. In Sophon, open **Settings > Connections**, click **Connect** on the ServiceNow card, enter your **Instance URL** (e.g. `https://acme.service-now.com`) plus the **OAuth Client ID** and **OAuth Client Secret**, leave username/password empty, and test the connection.

### Option B — Basic auth with a service account

1. Have a ServiceNow admin create a dedicated service account (**User Administration > Users**) with **Web service access only** checked, and grant it the roles/ACLs it needs (e.g. `itil` for incident work). On instances where Basic Auth restrictions are enforced, the account also needs the `snc_basic_auth_api_access` role.
2. In Sophon, open **Settings > Connections**, click **Connect** on the ServiceNow card, enter your **Instance URL**, the service account **Username** and **Password**, leave the OAuth fields empty, and test the connection.

If both credential pairs are filled in, OAuth client credentials take precedence.

## Usage Examples

> "Search ServiceNow for open P1 incidents assigned to the Network group"

> "Show me the details of incident record 9d385017c611228701d22104cc95c371"

> "Search the knowledge base for articles about VPN setup"

> "Create a ServiceNow incident: email is down for the finance team, urgency high, assign it to the Service Desk group"

> "Add a work note to that incident saying the mail relay was restarted at 14:30"

## Requirements

- A ServiceNow instance (any current release with the Table API and, for OAuth, inbound client-credentials support — Vancouver or later).
- A service account (basic auth) or OAuth Application User (client credentials) with roles/ACLs covering the tables you use — e.g. `itil` for incidents/changes, knowledge access for `kb_knowledge`.
- **ACLs**: ServiceNow access control silently omits fields and rows the account cannot read — empty or partial results may mean missing roles, not missing data.
- **Rate limits**: instances can enforce configurable inbound REST rate limits; the skill surfaces HTTP 429 responses as errors — retry later or ask an admin to adjust the rate limit rules.
- **Licensing**: ServiceNow "indirect access" licensing may meter integration/API usage on your instance; check your subscription terms before rolling out broadly.

## Trademarks

ServiceNow is a trademark of ServiceNow, Inc. This project is not affiliated with or endorsed by ServiceNow, Inc.

## License

MIT © 2026 Buildersoft LLC. See [LICENSE](LICENSE).
