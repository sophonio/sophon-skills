# Outlook Calendar

Manage a Microsoft 365 (Outlook) mailbox calendar through the [Microsoft Graph](https://learn.microsoft.com/graph/) API. List, create, update, and delete calendar events and list calendars. Uses **app-only** (OAuth2 client-credentials) authentication and pure Python standard library — no dependencies.

## Tools

| Name | Risk | Description |
| --- | --- | --- |
| `outlook.list_events` | none | List events. With `start` + `end`, returns events in that window (calendar view, expanding recurrences); otherwise upcoming events. |
| `outlook.create_event` | medium | Create a new event in the default calendar. |
| `outlook.update_event` | medium | Update an existing event's subject, start, and/or end. |
| `outlook.delete_event` | high | Delete an event (not easily reversible). |
| `outlook.list_calendars` | none | List the calendars in the mailbox. |

Event fields returned by `list_events`: `subject`, `start`, `end`, `organizer`, `location`, `id`.

## Connection / authentication

Configure the integration with an Azure AD app registration:

| Field | Description |
| --- | --- |
| **Directory (Tenant) ID** (`tenantId`) | The Azure AD tenant ID (GUID) of your Microsoft 365 organization. |
| **Application (Client) ID** (`clientId`) | The app registration's Application (client) ID. |
| **Client Secret** (`clientSecret`) | A client secret for the app registration. |
| **User (UPN/email)** (`userId`) | The mailbox to operate on. App-only auth requires an explicit user. |

The skill exchanges these for an access token at
`https://login.microsoftonline.com/{tenantId}/oauth2/v2.0/token` (grant `client_credentials`, scope
`https://graph.microsoft.com/.default`) and calls
`https://graph.microsoft.com/v1.0/users/{userId}` with a Bearer token.

### Requirements

- **App-only works for Microsoft 365 work/school accounts only** — it does **not** work with consumer `outlook.com` / personal Microsoft accounts.
- The app registration needs the **`Calendars.ReadWrite` application permission** with **admin consent** granted.

## Trademarks

Microsoft, Microsoft 365, Outlook, and Microsoft Graph are trademarks of Microsoft Corporation. This skill is an independent integration and is not affiliated with or endorsed by Microsoft.
