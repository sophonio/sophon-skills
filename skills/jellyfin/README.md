# Jellyfin Skill

Search and inspect a self-hosted [Jellyfin](https://jellyfin.org/) media server from Sophon —
find titles across your libraries, read item metadata, see what's playing, get next-up episodes,
and trigger metadata or library refreshes.

## Tools

| Tool | Risk | Description |
|------|------|-------------|
| `jellyfin.search_library` | none | Search movies/shows/episodes/music across libraries |
| `jellyfin.get_item` | none | Full metadata for an item (overview, cast, streams) |
| `jellyfin.list_libraries` | none | List libraries with counts |
| `jellyfin.get_recently_added` | none | Recently added items (optionally per library) |
| `jellyfin.get_active_sessions` | none | Who is watching what right now |
| `jellyfin.get_next_up` | none | Continue-watching / next-up episodes for a user |
| `jellyfin.refresh_item_metadata` | low | Trigger a metadata refresh for one item |
| `jellyfin.scan_library` | low | Trigger a full library scan |

## Setup

1. In Jellyfin, open **Dashboard > Advanced > API Keys** and create a new API key.
   **Note:** Jellyfin API keys are admin-scoped (full server privileges) — this skill only reads
   data and triggers refreshes, but treat the key like any admin credential.
2. Note your server URL including port, e.g. `http://192.168.1.10:8096`. It must be reachable
   from Sophon's sandbox — a LAN-only or VPN-only server needs a reverse proxy or tunnel.
3. (Optional) For `get_next_up`, find your Jellyfin **user id** (Dashboard > Users, the id in the
   URL) to set as the default.
4. In Sophon, open **Settings > Connections**, add the **Jellyfin** integration, and paste the
   server URL (`base_url`), **API Key** (`api_key`), and optional default user id.

## Usage Examples

> Search my Jellyfin server for anything with "Blade Runner" in the title.

> What's currently playing on my Jellyfin server?

> What should I watch next — show my next-up episodes.

> What was added to Jellyfin most recently?

## Requirements

- A running **Jellyfin** server (uses the modern `Authorization: MediaBrowser` header; the legacy
  `X-Emby-Token` / `api_key` query forms are being removed in Jellyfin 12).
- The server must be reachable from Sophon's sandbox (LAN, VPN, reverse proxy, or tunnel).
- An admin API key. `get_next_up` also needs a user id (default or per-call).

## Attribution & Trademarks

Jellyfin is free, open-source software (GPL-2.0). "Jellyfin" and the Jellyfin logo are trademarks
of the Jellyfin project. This project is an independent connector and is not affiliated with or
endorsed by the Jellyfin project.

## License

MIT © 2026 Buildersoft LLC. See [LICENSE](LICENSE).
