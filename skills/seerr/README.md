# Seerr Skill

Overseerr / Jellyseerr integration for Sophon — search movies and TV shows, check availability, browse trending titles, and create, approve, or decline media requests on your self-hosted request server.

## Tools

| Tool | Risk | Description |
|------|------|-------------|
| `seerr.search_media` | None | Search movies and TV shows by title, with availability status |
| `seerr.get_media_status` | None | Get availability and request status for a title by TMDB id |
| `seerr.list_requests` | None | List media requests (filter by pending/approved/available/processing) |
| `seerr.get_trending` | None | Browse trending titles, popular movies, or popular TV shows |
| `seerr.create_request` | Medium | Create a media request (admin key — may auto-approve) |
| `seerr.approve_request` | Medium | Approve a pending request (admin action, starts the download) |
| `seerr.decline_request` | Medium | Decline a pending request (admin action) |

## Setup

1. Open your Overseerr or Jellyseerr web UI as an admin
2. Go to **Settings > General** and copy the **API Key**
3. In the Sophon Dashboard, go to **Settings > Connections**
4. Click **Connect** on the Overseerr card
5. Enter your server URL (e.g. `http://192.168.1.50:5055`) and the API key
6. Test the connection (calls `/api/v1/auth/me`)

The server is self-hosted, so it must be reachable from Sophon's sandbox. A server that only listens on your LAN or behind a VPN usually needs a reverse proxy or tunnel before Sophon can reach it.

## Usage Examples

**Search for a title:**
> "Search seerr for Dune and tell me if it's available"

**Check availability:**
> "What's the status of the TV show with TMDB id 1399?"

**Review the queue:**
> "List the pending media requests and who asked for them"

**Request media:**
> "Request seasons 1 and 2 of The Last of Us on seerr"

**Moderate requests:**
> "Approve request 42 and decline request 43"

## Requirements

- A running Overseerr or Jellyseerr server (the same API works for both)
- The instance API key from **Settings > General** — note this key is **admin-scoped**, so `create_request`, `approve_request`, and `decline_request` act with admin rights (created requests may be auto-approved)
- The server must be reachable from Sophon's sandbox (public HTTPS or a reverse proxy/tunnel; plain-HTTP LAN addresses generally are not reachable)
- No fixed API rate limit, but be considerate — search and discover calls proxy through your server to TMDB

## Attribution & Trademarks

Media titles, artwork, and metadata surfaced by this skill come from The Movie Database (TMDB) via your Overseerr/Jellyseerr server; TMDB attribution is handled by the Seerr server itself, not by this skill. This product uses the TMDB API but is not endorsed or certified by TMDB.

Overseerr and Jellyseerr are open-source projects of their respective authors; Plex, Jellyfin, and TMDB are trademarks of their respective owners. This skill is an independent integration developed by Buildersoft LLC and is not affiliated with, endorsed by, or sponsored by the Overseerr or Jellyseerr projects, Plex, Inc., the Jellyfin project, or TMDB.

## License

MIT © 2026 Buildersoft LLC. See [LICENSE](LICENSE).
