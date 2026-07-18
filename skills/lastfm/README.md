# Last.fm Skill

Last.fm integration for Sophon — look up artists, similar artists and top tracks, search tracks, browse tag and global charts, and read a user's recent plays and top artists via the Last.fm API. Read-only public methods only (no scrobbling).

## Tools

| Tool | Risk | Description |
|------|------|-------------|
| `lastfm.get_artist_info` | None | Artist bio summary, listeners, playcount, and tags |
| `lastfm.get_similar_artists` | None | Artists similar to a given artist |
| `lastfm.get_artist_top_tracks` | None | An artist's most popular tracks |
| `lastfm.search_tracks` | None | Search tracks by name |
| `lastfm.get_tag_top_artists` | None | Top artists for a genre tag |
| `lastfm.get_chart_top_artists` | None | Current global top-chart artists |
| `lastfm.get_user_recent_tracks` | None | A user's recently played tracks |
| `lastfm.get_user_top_artists` | None | A user's top artists for a period |

## Setup

1. Create a (free) Last.fm API account at https://www.last.fm/api/account/create — you get an **API key** immediately (no approval wait for non-commercial use)
2. Go to **Settings > Connections** in the Sophon Dashboard
3. Click **Connect** on the Last.fm card
4. Paste your API key; optionally set a **Default Username** so the `user.*` tools work without naming a user each time
5. Test the connection

## Usage Examples

**Look up an artist:**
> "Tell me about the artist Boards of Canada on Last.fm"

**Find similar artists:**
> "Who are 10 artists similar to Radiohead?"

**Search tracks:**
> "Search Last.fm for tracks called 'Everlong'"

**Check listening history:**
> "What have I been listening to recently on Last.fm?"

**Top artists by period:**
> "Show my top Last.fm artists for the last 7 days"

## Requirements

- A free Last.fm API key ([create one here](https://www.last.fm/api/account/create))
- The Last.fm API is offered for **non-commercial use**; commercial use requires prior written permission from Last.fm
- Anonymous public data only — the `user.*` tools read public listening history and need no session auth
- Be mindful of Last.fm's rate limits; the skill surfaces rate-limit (429) responses with a slow-down hint

## Attribution & Trademarks

Music data provided by [Last.fm](https://www.last.fm/). This product uses the Last.fm API but is not endorsed, certified or otherwise approved by Last.fm. Tool results include Last.fm URLs — keep them when presenting data so results link back to Last.fm as its API terms require.

Last.fm and Audioscrobbler are trademarks of Last.fm Limited. This skill is an independent integration developed by Buildersoft LLC and is not affiliated with, endorsed by, or sponsored by Last.fm.

## License

MIT © 2026 Buildersoft LLC. See [LICENSE](LICENSE).
