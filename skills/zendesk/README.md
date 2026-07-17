# Zendesk Skill

Zendesk Support integration for Sophon — search tickets, users, and Help Center articles, read ticket threads, and create or update tickets and comments.

## Tools

| Tool | Risk | Description |
|------|------|-------------|
| `zendesk.search` | None | Universal search across tickets, users, and organizations |
| `zendesk.list_tickets` | None | List tickets with status and sort filters |
| `zendesk.get_ticket` | None | Get a ticket's details plus its comment thread |
| `zendesk.search_help_center` | None | Search Help Center (Zendesk Guide) articles |
| `zendesk.get_user` | None | Look up a user by id or search by email |
| `zendesk.create_ticket` | Medium | Create a new support ticket |
| `zendesk.update_ticket` | Medium | Update a ticket's status, priority, assignee, or tags |
| `zendesk.add_comment` | Medium | Add a public reply or internal note to a ticket |

## Setup

1. A Zendesk **admin** must create a confidential OAuth client: in **Admin Center**, go to **Apps and integrations > APIs > OAuth clients** and click **Add OAuth client**.
2. Give it a name (e.g. "Sophon"), set the client kind to **Confidential**, and save. Note the **unique identifier** (the client ID) and copy the **secret** — Zendesk shows the full secret only once, at creation time.
3. This skill authenticates with the OAuth2 **client-credentials** grant (`POST /oauth/tokens` with `scope: read write`). Tokens live at most 48 hours and are not refreshable; the skill mints a fresh token on each invocation, so nothing needs rotating manually.
4. Be aware that **writes are attributed to the OAuth client's associated user** — tickets and comments created through this skill appear as authored by that user, so associate the client with a suitable agent/service account.
5. This skill does **not** use API-token basic auth: Zendesk is sunsetting API tokens starting 2026-07-28.
6. In Sophon, open **Settings > Connections**, click **Connect** on the Zendesk card, and fill in:
   - **Zendesk Subdomain** — just the subdomain (e.g. `yourcompany` for `yourcompany.zendesk.com`), not the full URL
   - **OAuth Client ID** — the client's unique identifier
   - **OAuth Client Secret** — the secret from step 2
7. Test the connection.

## Usage Examples

> "Search Zendesk for open high-priority tickets about login errors"

> "Show me ticket 4521 with its full comment thread"

> "Look up the Zendesk user with email jane@acme.com"

> "Create a Zendesk ticket for jane@acme.com titled 'Cannot export invoices' with priority high"

> "Add an internal note to ticket 4521 saying engineering is investigating"

## Requirements

- A Zendesk Support account with admin access to create a confidential OAuth client in Admin Center
- Help Center search requires Zendesk Guide to be enabled on the account (the tool reports a clear error if it is not)
- API rate limits are plan-dependent (as low as 200 requests/minute on lower tiers); when a limit is hit the skill surfaces the 429 with the `Retry-After` value

## Trademarks

Zendesk is a trademark of Zendesk, Inc. This project is not affiliated with or endorsed by Zendesk, Inc.

## License

MIT © 2026 Buildersoft LLC. See [LICENSE](LICENSE).
