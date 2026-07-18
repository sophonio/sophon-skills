# Radarr Skill

Manage a self-hosted [Radarr](https://radarr.video/) movie PVR from Sophon — search TMDB for
films, add movies, browse your library and release calendar, watch the download queue and
history, and toggle monitoring.

## Tools

| Tool | Risk | Description |
|------|------|-------------|
| `radarr.search_movie_lookup` | none | Search TMDB (via Radarr) for movies to add |
| `radarr.list_movies` | none | List library movies with monitoring/file status |
| `radarr.get_calendar` | none | Upcoming/recent releases (cinema, digital, physical) |
| `radarr.get_queue` | none | Current download queue with progress |
| `radarr.get_history` | none | Recent grab/import/failure events |
| `radarr.add_movie` | medium | Add a movie by TMDB id with quality profile + root folder |
| `radarr.set_monitored` | low | Turn monitoring on/off for a movie |
| `radarr.list_quality_profiles` | none | Quality profile ids/names (for add_movie) |
| `radarr.list_root_folders` | none | Root folders with free space (for add_movie) |

## Setup

1. In Radarr, open **Settings > General > Security** and copy the **API Key** (Radarr generates
   one automatically on install).
2. Note your Radarr server URL including port, e.g. `http://192.168.1.50:7878`. The server must
   be reachable from Sophon's sandbox — a LAN-only or VPN-only instance needs a reverse proxy or
   tunnel (same as any self-hosted skill).
3. In Sophon, open **Settings > Connections**, add the **Radarr** integration, and paste the
   server URL (`base_url`) and **API Key** (`api_key`).

To add a movie, first call `radarr.list_quality_profiles` and `radarr.list_root_folders` to get
the ids/paths, then pass them to `radarr.add_movie`.

## Usage Examples

> What's in my Radarr download queue right now?

> Add the movie Dune Part Two to Radarr in my 1080p profile and search for it.

> Which monitored movies released this month but aren't downloaded yet?

> Show me the last 20 grab and import events from Radarr.

## Requirements

- A running **Radarr v3+** instance (the v3 API is stable on current v4/v5 builds).
- The instance must be reachable from Sophon's sandbox (LAN, VPN, reverse proxy, or tunnel).
- The API key grants full control of your Radarr instance; the write tools (`add_movie`,
  `set_monitored`) are marked medium/low risk accordingly.

## Attribution & Trademarks

Radarr is free, open-source software (GPL-3.0). "Radarr" and the Radarr logo are the property of
their respective owners. This project is an independent connector and is not affiliated with or
endorsed by the Radarr project. Movie metadata surfaced via Radarr originates from TMDB.

## License

MIT © 2026 Buildersoft LLC. See [LICENSE](LICENSE).
