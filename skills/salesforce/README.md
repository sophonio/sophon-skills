# Salesforce Skill

Salesforce CRM integration for Sophon — run SOQL queries and SOSL searches, read, create, and update records, describe objects, and log Task activities via the Salesforce REST API (v62.0).

## Tools

| Tool | Risk | Description |
|------|------|-------------|
| `sf.soql_query` | None | Run a SOQL query (follows pagination, capped) |
| `sf.search` | None | SOSL full-text search across objects |
| `sf.get_record` | None | Fetch a record by object type and Id |
| `sf.describe_object` | None | List an object's fields, types, and picklist values |
| `sf.create_record` | Medium | Create a record of any object type |
| `sf.update_record` | Medium | Update fields on an existing record |
| `sf.add_task` | Low | Create a Task activity linked to a record |

## Setup

1. In Salesforce Setup, create an **External Client App** (Setup > App Manager > New External Client App) with **OAuth** enabled.
2. Under the app's OAuth settings, check **Enable Client Credentials Flow** and add at least the `api` OAuth scope ("Manage user data via APIs").
3. Assign a **run-as user** for the client credentials flow — use a dedicated, least-privilege integration user; all API calls execute as this user, so its profile/permission sets define what the skill can see and change.
4. Copy the app's **Consumer Key** and **Consumer Secret** (Settings > OAuth Settings > Consumer Key and Secret).
5. Find your org's **My Domain URL** (Setup > My Domain), e.g. `https://acme.my.salesforce.com`. This is required — the client credentials flow does not work against `login.salesforce.com`.
6. In Sophon, open **Settings > Connections**, click **Connect** on the Salesforce card, and enter the My Domain URL, Consumer Key, and Consumer Secret.
7. Test the connection.

Salesforce docs: https://help.salesforce.com/s/articleView?id=sf.connected_app_client_credentials_setup.htm&type=5

## Usage Examples

> "Show me all open opportunities closing this quarter with amount over $50k"

> "Search Salesforce for anything matching 'Acme'"

> "What picklist values does the Opportunity StageName field have?"

> "Create a contact named Jane Doe at Acme Corp with email jane@acme.com"

> "Add a task on the Acme account to follow up on the renewal next Friday"

## Requirements

- Salesforce **Enterprise**, **Unlimited**, **Performance**, or **Developer** edition — API access is included. **Professional** edition requires the paid API access add-on.
- A My Domain configured for the org (default on modern orgs).
- An External Client App with the Client Credentials Flow enabled and a run-as integration user whose permissions cover the objects you want to query and modify.
- API calls count against the org's rolling 24-hour API request limit; the skill reports a clear error when `REQUEST_LIMIT_EXCEEDED` is hit.

## Trademarks

Salesforce is a trademark of Salesforce, Inc. This project is not affiliated with or endorsed by Salesforce, Inc.

## License

MIT © 2026 Buildersoft LLC. See [LICENSE](LICENSE).
