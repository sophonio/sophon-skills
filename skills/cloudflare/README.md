# Cloudflare

Manage Cloudflare zones, DNS records, and cache through the [Cloudflare API v4](https://developers.cloudflare.com/api/), using a scoped API token. Pure Python standard library — no dependencies.

## Tools

| Name | Risk | Description |
| --- | --- | --- |
| `cloudflare.list_zones` | none | List the zones (domains) the token can access. |
| `cloudflare.list_dns_records` | none | List DNS records in a zone, optionally filtered by type and name. |
| `cloudflare.create_dns_record` | medium | Create a DNS record in a zone. |
| `cloudflare.update_dns_record` | medium | Update an existing DNS record (only the fields you pass). |
| `cloudflare.delete_dns_record` | high | Delete a DNS record. Not easily reversible. |
| `cloudflare.purge_cache` | medium | Purge a zone's cache — everything, or a list of file URLs. |

Any tool that operates on a zone accepts a `zoneId` argument and falls back to the default zone configured on the connection. If neither is set, the call returns `{"error": "zoneId required (pass it or configure it on the connection)"}`.

## Connection

Authenticate with a Cloudflare API token (Bearer auth).

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `apiToken` | secret | yes | A scoped API token. [Create one](https://dash.cloudflare.com/profile/api-tokens) with the permissions you need (e.g. Zone:Read, DNS:Edit, Cache Purge). |
| `zoneId` | text | no | Default zone id used when a tool call omits one. |
| `accountId` | text | no | Optional Cloudflare account id for account-scoped operations. |

The token is verified against `/user/tokens/verify`. Requests go to `https://api.cloudflare.com/client/v4` with `Authorization: Bearer <apiToken>`.

## Trademarks

Cloudflare is a trademark of Cloudflare, Inc. This skill is an independent integration and is not affiliated with, endorsed by, or sponsored by Cloudflare, Inc.
