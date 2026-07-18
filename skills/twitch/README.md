# Twitch Skill

Twitch integration for Sophon — search channels, browse live streams, top games, clips, and videos via the Helix API. Uses an OAuth2 client-credentials app access token, so it covers public catalog data only (no followed channels, subscriptions, or chat).

## Tools

| Tool | Risk | Description |
|------|------|-------------|
| `twitch.search_channels` | None | Search channels by name (optionally live-only) |
| `twitch.get_streams` | None | List live streams by game, broadcaster, or language |
| `twitch.get_top_games` | None | List the most-watched games/categories right now |
| `twitch.get_clips` | None | List clips for a broadcaster or game, optionally in a time window |
| `twitch.get_videos` | None | List a broadcaster's videos (VODs) |
| `twitch.get_channel_info` | None | Get a channel's name, current game, title, and tags |
| `twitch.get_game` | None | Resolve a game name to its Twitch id and box art |

## Setup

1. Sign in at the [Twitch Developer Console](https://dev.twitch.tv/console) (your Twitch account must have two-factor authentication enabled)
2. Go to **Applications > Register Your Application**
3. Give it a name, set the OAuth Redirect URL to `https://localhost` (not used by this skill), and pick a category
4. On the application's **Manage** page, copy the **Client ID** and generate a **New Secret** (copy it immediately — it is shown once)
5. Go to **Settings > Connections** in the Sophon Dashboard
6. Click **Connect** on the Twitch card, enter the Client ID and Client Secret, and test the connection

## Usage Examples

**Search channels:**
> "Search Twitch for channels named 'chess' that are live right now"

**Browse streams:**
> "Show me the top live Twitch streams in English"

**Top games:**
> "What are the most-watched games on Twitch right now?"

**Clips:**
> "Find the Twitch game id for Hades, then show me its top clips from the last week"

**Videos:**
> "List the latest highlight videos for Twitch broadcaster id 141981764"

## Requirements

- A registered Twitch application (free) — requires a Twitch account with 2FA enabled
- App access tokens expose **public data only**: no followed channels, subscriptions, chat, or other user-scoped endpoints
- Helix rate limits apply per Client ID (token-bucket, ~800 points/minute); on HTTP 429 the skill surfaces the `Retry-After` value — slow down and retry
- Per the Twitch Developer Services Agreement, data retrieved from the API may be cached for a maximum of 24 hours

## Attribution & Trademarks

Content data returned by this skill originates from Twitch, and tool output includes `twitch.tv` URLs linking back to the source channels, clips, and videos — keep these links when presenting results, as Twitch requires attribution linking to the relevant Twitch content. Twitch, the Twitch logo, and Glitch are trademarks or registered trademarks of Twitch Interactive, Inc. This skill is an independent integration developed by Buildersoft LLC and is not affiliated with, endorsed by, or sponsored by Twitch Interactive, Inc.

## License

MIT © 2026 Buildersoft LLC. See [LICENSE](LICENSE).
