# Sonarr Skill

Sonarr integration for Sophon — manage your self-hosted TV series PVR. Search TheTVDB for shows,
add series with a quality profile and root folder, browse your library, the airing calendar,
missing episodes, and the download queue, and flip season monitoring — all against your own
Sonarr v3+ server via its API key.

## Tools

| Tool | Risk | Description |
|------|------|-------------|
| `sonarr.search_series_lookup` | None | Search TheTVDB (via Sonarr) for series to add |
| `sonarr.list_series` | None | List library series with status and episode counts |
| `sonarr.get_calendar` | None | Upcoming/recently aired episodes, optional date window |
| `sonarr.get_missing` | None | Monitored episodes that aired but are missing from disk |
| `sonarr.get_queue` | None | Current download queue with progress and time left |
| `sonarr.add_series` | Medium | Add a series by TVDB id (optionally search immediately) |
| `sonarr.set_season_monitored` | Low | Monitor/unmonitor a season (or the whole series) |
| `sonarr.list_quality_profiles` | None | List quality profiles (ids for `add_series`) |
| `sonarr.list_root_folders` | None | List root folders and free space (paths for `add_series`) |

## Setup

1. Open your Sonarr web UI and go to **Settings > General > Security**.
2. Copy the **API Key** (regenerate it there if you ever need to rotate it).
3. Make sure the Sonarr server is reachable from Sophon's sandbox. A LAN-only address like
   `http://192.168.1.10:8989` works only if Sophon runs on the same network — otherwise expose
   Sonarr through a reverse proxy or tunnel (HTTPS recommended).
4. In the Sophon Dashboard, go to **Settings > Connections** and click **Connect** on the
   Sonarr card.
5. Enter your Sonarr URL (e.g. `http://192.168.1.10:8989`, no trailing slash) and the API key.
6. Test the connection — Sophon calls `/api/v3/system/status` to verify it.

## Usage Examples

**Find and add a show:**
> "Search Sonarr for 'Severance' and add it with the HD-1080p profile to my TV root folder"

**Check what's airing:**
> "What episodes are coming up on my Sonarr calendar this week?"

**Chase missing episodes:**
> "List the monitored episodes Sonarr is still missing"

**Watch the queue:**
> "How far along are my Sonarr downloads?"

**Tune monitoring:**
> "Stop monitoring season 1 of series 42 in Sonarr"

## Requirements

- A self-hosted Sonarr **v3 or newer** instance (this skill uses API v3 under `/api/v3`).
- The Sonarr API key from **Settings > General > Security**.
- Network reachability: Sophon's sandbox must be able to reach the server. Private/LAN-only or
  VPN-only instances need a reverse proxy or tunnel; plain-HTTP LAN URLs are supported, HTTPS
  URLs are honored as-is.
- No third-party rate limits apply — the skill talks only to your own Sonarr server.

## Attribution & Trademarks

Sonarr is a free and open-source project (GPL-3.0) developed by the Sonarr team
(https://sonarr.tv). Series metadata shown by Sonarr is provided by TheTVDB (https://thetvdb.com).
The Sonarr name and logo are trademarks of their respective owners. This skill is an independent
integration developed by Buildersoft LLC and is not affiliated with, endorsed by, or sponsored by
the Sonarr project or TheTVDB. It communicates exclusively with the Sonarr instance you configure.

## License

MIT © 2026 Buildersoft LLC. See [LICENSE](LICENSE).
