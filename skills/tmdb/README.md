# TMDB Skill

The Movie Database (TMDB) integration for Sophon — search movies, TV shows, and people; fetch
detailed movie/TV metadata; discover titles by genre, year, rating, or streaming service; check
what's trending; find where to watch (JustWatch data); and get recommendations.

## Tools

| Tool | Risk | Description |
|------|------|-------------|
| `tmdb.search_media` | None | Multi search across movies, TV shows, and people |
| `tmdb.get_movie_details` | None | Movie details: genres, runtime, certification, directors, cast, keywords |
| `tmdb.get_tv_details` | None | TV show details, or a season's episode list |
| `tmdb.discover_titles` | None | Discover movies/TV by genre, year, rating, watch provider, sort |
| `tmdb.get_trending` | None | Trending movies/TV/all for the day or week |
| `tmdb.get_watch_providers` | None | Where to stream/rent/buy in a region (JustWatch data) |
| `tmdb.get_recommendations` | None | Titles similar to a given movie or TV show |

## Setup

1. Create a free account at [themoviedb.org](https://www.themoviedb.org/signup) and verify your email.
2. Go to [Settings > API](https://www.themoviedb.org/settings/api) and register for an API key
   (choose "Developer"; free for non-commercial use).
3. On that page you will see both an **API Key** (v3, a 32-character hex string) and an
   **API Read Access Token** (v4, a long JWT starting with `eyJ`). Copy **either one** — the
   skill detects which you pasted and authenticates accordingly.
4. In the Sophon Dashboard, go to **Settings > Connections**, click **Connect** on the TMDB card,
   and paste the key/token. Optionally set a default **Region** (ISO 3166-1, e.g. `US`, `DE`)
   used for watch providers and certifications.
5. Test the connection.

## Usage Examples

**Search:**
> "Search TMDB for Dune"

**Movie details:**
> "Get the TMDB details for movie 693134 — who directed it and what's it rated?"

**Discover:**
> "Find highly rated sci-fi movies from 2024 on TMDB, sorted by rating"

**Where to watch:**
> "Where can I stream The Bear (TV id 136315) in Germany?"

**Trending:**
> "What movies are trending on TMDB this week?"

## Requirements

- A free TMDB account with an API key or Read Access Token (non-commercial use only on the free tier).
- Rate limit: TMDB enforces a soft cap of roughly 40 requests/second — well above normal skill usage.
- All tools are read-only; no data on your TMDB account is modified.

## Attribution & Trademarks

This product uses the TMDB API but is not endorsed or certified by TMDB.

TMDB's API is free for **non-commercial use only**; commercial use requires a separate license
from TMDB. Watch provider data is provided by [JustWatch](https://www.justwatch.com/), and the
`tmdb.get_watch_providers` tool includes the required JustWatch attribution in its output.

TMDB and The Movie Database are trademarks of TiVo Brands, LLC. JustWatch is a trademark of
JustWatch GmbH. This skill is an independent integration developed by Buildersoft LLC and is not
affiliated with, endorsed by, or sponsored by TMDB or JustWatch.

## License

MIT © 2026 Buildersoft LLC. See [LICENSE](LICENSE).
