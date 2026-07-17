# Freshservice Skill

Freshservice IT service management integration for Sophon — list, inspect, create, and update service desk tickets, add notes, review change requests, and search CMDB assets via the Freshservice REST API v2.

## Tools

| Tool | Risk | Description |
|------|------|-------------|
| `freshservice.list_tickets` | None | List tickets, optionally by predefined filter or updated-since timestamp |
| `freshservice.get_ticket` | None | Get a ticket's details plus its conversation thread |
| `freshservice.list_changes` | None | List change requests with status, risk, and planned dates |
| `freshservice.search_assets` | None | Search CMDB assets by name, asset tag, or serial number |
| `freshservice.create_ticket` | Medium | Create a new incident ticket for a requester |
| `freshservice.update_ticket` | Medium | Update a ticket's status, priority, or group |
| `freshservice.add_note` | Low | Add a private (default) or public note to a ticket |

## Setup

1. Ask a Freshservice admin to make sure **API access is enabled** for your agent account (Admin > Agents > your agent). Without it, the profile page will not show an API key.
2. Sign in to your Freshservice instance (`https://yourcompany.freshservice.com`), click your profile picture, and open **Profile Settings**.
3. Copy **Your API Key** from the right-hand panel. See: https://support.freshservice.com/en/support/solutions/articles/50000000306-where-do-i-find-my-api-key-
4. In Sophon, open **Settings > Connections** and click **Connect** on the Freshservice card.
5. Enter your Freshservice URL (e.g. `https://yourcompany.freshservice.com`) and paste the API key.
6. Test the connection (it performs a one-ticket list call against `/api/v2/tickets`).

The skill authenticates every request with HTTP Basic auth using the API key as the username and the literal `X` as the password — the same mechanism as Freshdesk. All actions run with the permissions of the agent whose key you use.

## Usage Examples

> "Show me my open Freshservice tickets"

> "What's the latest on ticket 4312, including the conversation?"

> "Create a Freshservice ticket for jane@company.com: laptop won't boot, priority high"

> "Add a private note to ticket 4312 saying the replacement SSD has been ordered"

> "Search our assets for serial number 5CG1234XYZ"

## Requirements

- A Freshservice instance (any plan) with an agent account whose API access is enabled by an admin
- API rate limits are plan-dependent (per-minute limits with per-endpoint sub-limits); on HTTP 429 the skill surfaces the `Retry-After` value so you know when to retry
- The **asset management (CMDB)** and **change management** modules vary by plan tier — `freshservice.search_assets` returns a clear plan-module error if your plan or role does not include the CMDB, while `freshservice.list_changes` surfaces the raw API error (e.g. HTTP 403) if change management is unavailable
- Write tools (create/update/note) require the agent to have the corresponding ticket permissions

## Trademarks

Freshservice is a trademark of Freshworks Inc. This project is not affiliated with or endorsed by Freshworks Inc.

## License

MIT © 2026 Buildersoft LLC. See [LICENSE](LICENSE).
