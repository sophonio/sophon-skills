# Intercom Skill

Intercom customer-messaging integration for Sophon — search and read conversations and contacts, list Help Center articles, add internal notes, reply to customers, and close/snooze/assign conversations.

## Tools

| Tool | Risk | Description |
|------|------|-------------|
| `intercom.search_conversations` | None | Search conversations by state, assignee, and/or last-updated time (paged) |
| `intercom.get_conversation` | None | Get a conversation with its most recent parts (HTML stripped) |
| `intercom.search_contacts` | None | Search contacts by email or any searchable attribute |
| `intercom.get_contact` | None | Get a contact profile with companies and custom attributes |
| `intercom.list_articles` | None | List Help Center articles (listing, not full-text search) |
| `intercom.add_note` | Low | Add an internal note to a conversation (invisible to the customer) |
| `intercom.reply_customer` | High | Send a customer-facing reply — this messages the real customer |
| `intercom.update_conversation` | Medium | Close, snooze, or assign a conversation |

## Setup

1. A workspace admin signs in to Intercom and opens the **Developer Hub** (https://app.intercom.com > Settings > Integrations > Developer Hub, or https://developers.intercom.com).
2. Click **New app** and create an **internal** app for your workspace.
3. Open the app's **Configure > Authentication** page — the workspace **Access Token** is shown there. Copy it.
4. Important: **each user must create their own internal app and use their own token.** Intercom's Terms of Service forbid sharing internal-app access tokens or using them for hosted multi-tenant access on behalf of other workspaces.
5. Note your workspace's data-hosting region — the API host must match: `https://api.intercom.io` (US), `https://api.eu.intercom.io` (EU), or `https://api.au.intercom.io` (Australia).
6. In Sophon, open **Settings > Connections**, click **Connect** on the Intercom card, enter the API Base URL for your region and the Access Token, then test the connection.

## Usage Examples

> "Show me all open Intercom conversations updated in the last 24 hours"

> "Pull up conversation 12345 and summarize what the customer is asking for"

> "Find the Intercom contact with email jane@acme.com and show her custom attributes"

> "Add an internal note to conversation 12345 saying engineering is investigating"

> "Snooze conversation 12345 until Monday morning and assign it to the billing team"

## Requirements

- An Intercom workspace with permission to create internal apps in the Developer Hub (workspace admin).
- Your own internal-app Access Token — one per user; tokens must not be shared (Intercom ToS).
- The token inherits the creating admin's workspace permissions; conversation management and replies require Inbox access (an Inbox seat on plans that meter seats).
- Calls are pinned to Intercom API version 2.15.

## Trademarks

Intercom is a trademark of Intercom, Inc. This project is not affiliated with or endorsed by Intercom, Inc.

## License

MIT © 2026 Buildersoft LLC. See [LICENSE](LICENSE).
