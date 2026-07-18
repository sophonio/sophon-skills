# Plex Skill

Plex Media Server integration for Sophon — search your libraries, inspect items, browse recently added and On Deck, see who is watching what, and trigger library scans on your own server.

## Tools

| Tool | Risk | Description |
|------|------|-------------|
| `plex.search_library` | None | Search all libraries (or one section) for matching items |
| `plex.get_item_details` | None | Get an item's summary, rating, duration, and media stream info |
| `plex.list_libraries` | None | List library sections (key, title, type, agent) |
| `plex.get_recently_added` | None | List recently added items, server-wide or per section |
| `plex.get_active_sessions` | None | List active playback sessions with user, player, and progress |
| `plex.get_on_deck` | None | List On Deck (continue-watching) items |
| `plex.scan_library_section` | Low | Trigger a scan/refresh of a library section |

## Setup

1. Find your Plex server's base URL — usually a LAN address like `http://192.168.1.50:32400` (Plex servers typically speak plain HTTP on the LAN; HTTPS URLs work too).
2. Get your owner/admin **X-Plex-Token**: open Plex Web, click any library item, choose **Get Info > View XML**, and copy the `X-Plex-Token` value from the opened URL. See [Plex's guide](https://support.plex.tv/articles/204059436-finding-an-authentication-token-x-plex-token/).
   - **Warning:** this token is admin-powerful — it grants full control of your server. Treat it like a password.
3. Go to **Settings > Connections** in the Sophon Dashboard.
4. Click **Connect** on the Plex card, enter the server URL and token, and test the connection.

**Self-hosted note:** Sophon's sandbox must be able to reach your Plex server. A server that is only reachable on your LAN will not work without a VPN, tunnel, or reverse proxy exposing it to Sophon.

## Usage Examples

**Search a library:**
> "Search Plex for Blade Runner"

**Check what's playing:**
> "Who is watching Plex right now?"

**Browse new arrivals:**
> "What was recently added to my Plex movie library?"

**Continue watching:**
> "What's on deck in Plex?"

**Refresh a library:**
> "Scan my Plex TV Shows library for new episodes"

## Requirements

- A self-hosted Plex Media Server reachable from Sophon's sandbox (LAN-only servers need a VPN, tunnel, or reverse proxy).
- An owner/admin X-Plex-Token. Plex classifies static-token auth as **"Legacy"** — it still works and has no announced sunset date, but Plex is steering integrations toward OAuth-style flows, so there is a medium-term risk this auth method is eventually retired. Expect to migrate if Plex deprecates it.
- No documented rate limits for a personal server, but heavy polling of a low-power server (e.g. a NAS) can slow playback for viewers.

## Attribution & Trademarks

Plex is a trademark of Plex, Inc. This skill is an independent integration developed by Buildersoft LLC and is not affiliated with, endorsed by, or sponsored by Plex, Inc. It talks only to your own Plex Media Server using your own token; no data is sent to Plex, Inc. by this skill beyond what your server itself does.

## License

MIT © 2026 Buildersoft LLC. See [LICENSE](LICENSE).
