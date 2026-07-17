# HubSpot Skill

HubSpot CRM integration for Sophon — search and read contacts, companies, deals, and tickets, list pipelines and owners, create and update records, and log notes, all via the CRM v3 API using a private-app access token.

## Tools

| Tool | Risk | Description |
|------|------|-------------|
| `hubspot.search_objects` | None | Search CRM records with a property filter and/or free-text query (paged via cursor) |
| `hubspot.get_object` | None | Get a single record by id, with optional properties and associations |
| `hubspot.list_pipelines` | None | List deal or ticket pipelines and their stages |
| `hubspot.list_owners` | None | List CRM owners (id, email, name) |
| `hubspot.create_object` | Medium | Create a contact, company, deal, or ticket |
| `hubspot.update_object` | Medium | Update properties of an existing record |
| `hubspot.add_note` | Low | Log a note on a record (requires an ISO 8601 timestamp) |

## Setup

1. A HubSpot **super admin** signs in to your HubSpot account.
2. Go to **Settings > Development > Legacy apps > Create private app**. Private apps are HubSpot's "legacy" track, but they remain fully supported with no announced sunset.
3. On the **Scopes** tab, select the scopes this skill uses:
   - `crm.objects.contacts.read` and `crm.objects.contacts.write`
   - `crm.objects.companies.read` and `crm.objects.companies.write`
   - `crm.objects.deals.read` and `crm.objects.deals.write`
   - `tickets`
   - `crm.objects.owners.read`
   - `crm.objects.notes.write`
4. Create the app and copy its **access token** (shown once per rotation; you can view it again from the app's Auth tab).
5. In the Sophon Dashboard, go to **Settings > Connections**, click **Connect** on the HubSpot card, paste the access token, and test the connection.

If calls fail with a 403, the private app is almost always missing one of the scopes above — edit the app's scopes and retry.

## Usage Examples

**Search contacts:**
> "Find HubSpot contacts with the email domain acme.com"

**Inspect a deal:**
> "Show me HubSpot deal 9871234, including its associated contacts"

**Pipelines:**
> "List our HubSpot deal pipelines and stages"

**Create a record:**
> "Create a HubSpot contact for Ann Lee, ann@acme.com"

**Log a note:**
> "Add a note to HubSpot contact 512 saying we agreed to a follow-up call, timestamped now"

## Requirements

- A HubSpot account (any tier that includes the CRM; free CRM works for contacts/companies/deals/tickets).
- A private app created by a super admin, with the scopes listed above.
- Search calls are rate-limited by HubSpot (about 5 requests/second per token) and each search query returns at most 10,000 total results.

## Trademarks

HubSpot is a trademark of HubSpot, Inc. This skill is an independent integration developed by Buildersoft LLC and is not affiliated with, endorsed by, or sponsored by HubSpot.

## License

MIT © 2026 Buildersoft LLC. See [LICENSE](LICENSE).
