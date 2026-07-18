# Steam Skill

Steam integration for Sophon via the official Steam Web API — look up player profiles, browse game libraries and playtime, check achievement progress, read game news, and see live player counts. Only the documented Web API on `api.steampowered.com` is used (no storefront endpoints).

## Tools

| Tool | Risk | Description |
|------|------|-------------|
| `steam.resolve_vanity_url` | None | Resolve a steamcommunity.com/id/ vanity name to a SteamID64 |
| `steam.get_player_summary` | None | Profile summaries (name, URL, online state, current game) for one or more players |
| `steam.get_owned_games` | None | Owned games with total playtime, sorted by most played |
| `steam.get_recently_played` | None | Games played in the last two weeks |
| `steam.get_player_achievements` | None | Achievement totals and unlocked achievements for one game |
| `steam.get_app_news` | None | Latest news/patch notes for a game (keyless) |
| `steam.get_current_players` | None | Live in-game player count for a game (keyless) |

## Setup

1. Sign in to Steam and open https://steamcommunity.com/dev/apikey
2. Enter any domain name (it is not verified) and click **Register** to get your Web API key. Your account must be non-limited (at least $5 spent on Steam).
3. (Optional) Find your 64-bit SteamID: open your Steam profile, and if it uses a custom URL, resolve it later with `steam.resolve_vanity_url` — or look it up at your profile's **Edit Profile** page.
4. Go to **Settings > Connections** in the Sophon Dashboard
5. Click **Connect** on the Steam card
6. Paste the API key, optionally set a **Default SteamID64**, and test the connection

The `steam.get_app_news` and `steam.get_current_players` tools work without any key, so you can skip the key if that is all you need.

## Usage Examples

**Find a SteamID:**
> "What's the SteamID for the Steam vanity URL 'gabelogannewell'?"

**Check who's online:**
> "Is my Steam friend 76561197960287930 online, and what are they playing?"

**Browse a library:**
> "Show my 10 most played Steam games"

**Achievements:**
> "How many achievements have I unlocked in Team Fortress 2 (app 440)?"

**News and player counts:**
> "Get the latest Counter-Strike 2 patch notes and how many people are playing right now"

## Requirements

- A Steam Web API key from a **non-limited** Steam account (accounts must have spent at least $5 on Steam) — except for the two keyless tools
- Player-data tools (`get_owned_games`, `get_recently_played`, `get_player_achievements`, and parts of `get_player_summary`) only return data for **public** profiles; private or friends-only profiles return empty results
- Steam Web API rate limits apply (100,000 calls/day per key); the skill surfaces a "rate limited, slow down" hint on HTTP 429

## Attribution & Trademarks

Powered by Steam. This product uses data provided by the Steam Web API but is not endorsed or certified by Valve.

Steam and the Steam logo are trademarks and/or registered trademarks of Valve Corporation in the U.S. and/or other countries. This skill is an independent integration developed by Buildersoft LLC and is not affiliated with, endorsed by, or sponsored by Valve Corporation.

## License

MIT © 2026 Buildersoft LLC. See [LICENSE](LICENSE).
