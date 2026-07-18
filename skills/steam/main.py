"""Steam integration skill — official Steam Web API (api.steampowered.com).

Pure standard library (urllib) so it runs unchanged in the alpine Python sandbox with no pip
dependencies. `params` is injected as a global by the Sophon runtime and carries the tool name,
the tool arguments, and the connection-card fields (api_key, default_steam_id).

Auth is a static Steam Web API key passed as the `key` query parameter on api.steampowered.com.
Two tools (steam.get_app_news, steam.get_current_players) hit keyless endpoints and run without
a key; the key is never sent on those calls. Only the official Web API is used — no
store.steampowered.com storefront endpoints. Private/friends-only profiles return empty results.
"""

import json
import urllib.request
import urllib.parse
import urllib.error

tool_name = params.get("tool", "")
api_key = params.get("api_key") or ""
default_steam_id = str(params.get("default_steam_id") or "").strip()

API_BASE = "https://api.steampowered.com"

PERSONA_STATES = {0: "Offline", 1: "Online", 2: "Busy", 3: "Away", 4: "Snooze",
                  5: "Looking to trade", 6: "Looking to play"}


def request(path, query=None):
    """GET a Steam Web API path. Returns parsed JSON (or None for 204/empty)."""
    clean = {k: v for k, v in (query or {}).items() if v not in (None, "")}
    url = f"{API_BASE}{path}"
    if clean:
        url = f"{url}?{urllib.parse.urlencode(clean)}"
    req = urllib.request.Request(url, headers={
        "Accept": "application/json",
        "User-Agent": "sophon-steam-skill",
    }, method="GET")
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read().decode()
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        detail = e.read().decode() if e.fp else ""
        try:
            parsed = json.loads(detail)
            msg = ((parsed.get("playerstats") or {}).get("error")
                   or parsed.get("error") or parsed.get("errmsg") or detail)
            if not isinstance(msg, str):
                msg = detail
        except (ValueError, TypeError, AttributeError):
            msg = detail
        msg = (msg or f"HTTP {e.code}").strip()
        if len(msg) > 300:
            msg = msg[:300] + "..."
        if e.code == 429:
            retry_after = e.headers.get("Retry-After") if e.headers else None
            hint = " (rate limited, slow down"
            hint += f"; retry after {retry_after}s)" if retry_after else ")"
            raise RuntimeError(f"Steam API error 429: {msg}{hint}") from e
        if e.code in (401, 403):
            msg = f"{msg} — check that your Steam Web API key is valid and the profile is public"
        raise RuntimeError(f"Steam API error {e.code}: {msg}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Could not reach Steam: {e.reason}") from e


def clamp(value, default, maximum):
    try:
        return max(1, min(int(value), maximum))
    except (TypeError, ValueError):
        return default


def require_steam_id():
    sid = str(params.get("steamId") or default_steam_id or "").strip()
    if not sid:
        raise ValueError("steamId required: pass steamId or set default_steam_id in the Steam connection")
    return sid


def require_app_id():
    appid = params.get("appId")
    if appid in (None, ""):
        raise ValueError("appId required")
    try:
        return int(str(appid))
    except (TypeError, ValueError):
        raise ValueError("appId must be a number")


def player_summary(p):
    state = p.get("personastate")
    return {
        "steamid": p.get("steamid"),
        "personaname": p.get("personaname"),
        "profileurl": p.get("profileurl"),
        "personastate": PERSONA_STATES.get(state, state),
        "gameextrainfo": p.get("gameextrainfo"),
    }


def game_summary(g):
    minutes = g.get("playtime_forever") or 0
    out = {
        "appid": g.get("appid"),
        "name": g.get("name"),
        "playtime_forever": minutes,
        "playtime_hours": round(minutes / 60, 1),
    }
    if g.get("playtime_2weeks"):
        out["playtime_2weeks"] = g.get("playtime_2weeks")
    return out


def news_summary(item):
    contents = item.get("contents") or ""
    if len(contents) > 500:
        contents = contents[:500] + "..."
    return {
        "title": item.get("title"),
        "url": item.get("url"),
        "author": item.get("author"),
        "date": item.get("date"),
        "feedlabel": item.get("feedlabel"),
        "contents": contents,
    }


# --- Tool handlers ---------------------------------------------------------

def resolve_vanity_url():
    vanity = str(params.get("vanityUrl") or "").strip()
    if not vanity:
        raise ValueError("vanityUrl required")
    data = request("/ISteamUser/ResolveVanityURL/v1/",
                   {"key": api_key, "vanityurl": vanity})
    result = (data or {}).get("response") or {}
    if result.get("success") != 1 or not result.get("steamid"):
        raise ValueError(f"No Steam account found for vanity URL '{vanity}'")
    print(json.dumps({"vanityUrl": vanity, "steamid": result["steamid"]}))


def get_player_summary():
    ids = str(params.get("steamIds") or params.get("steamId") or default_steam_id or "").strip()
    if not ids:
        raise ValueError("steamIds required: pass steamIds or set default_steam_id in the Steam connection")
    ids = ",".join(part.strip() for part in ids.split(",") if part.strip())
    data = request("/ISteamUser/GetPlayerSummaries/v2/",
                   {"key": api_key, "steamids": ids})
    players = [player_summary(p) for p in ((data or {}).get("response") or {}).get("players", [])]
    print(json.dumps({"count": len(players), "players": players}))


def get_owned_games():
    sid = require_steam_id()
    limit = clamp(params.get("limit", 50), 50, 500)
    data = request("/IPlayerService/GetOwnedGames/v1/",
                   {"key": api_key, "steamid": sid,
                    "include_appinfo": 1, "include_played_free_games": 1})
    result = ((data or {}).get("response") or {})
    games = sorted(result.get("games") or [],
                   key=lambda g: g.get("playtime_forever") or 0, reverse=True)
    out = {"count": result.get("game_count", len(games)),
           "games": [game_summary(g) for g in games[:limit]]}
    if not games:
        out["note"] = ("No games returned — the profile may be private or friends-only "
                       "(Steam returns empty results for non-public game details).")
    print(json.dumps(out))


def get_recently_played():
    sid = require_steam_id()
    count = params.get("count")
    query = {"key": api_key, "steamid": sid}
    if count not in (None, ""):
        query["count"] = clamp(count, 10, 50)
    data = request("/IPlayerService/GetRecentlyPlayedGames/v1/", query)
    result = ((data or {}).get("response") or {})
    games = [game_summary(g) for g in result.get("games") or []]
    out = {"count": result.get("total_count", len(games)), "games": games}
    if not games:
        out["note"] = ("No recently played games returned — the profile may be private or "
                       "friends-only, or nothing was played in the last two weeks.")
    print(json.dumps(out))


def get_player_achievements():
    sid = require_steam_id()
    appid = require_app_id()
    data = request("/ISteamUserStats/GetPlayerAchievements/v1/",
                   {"key": api_key, "steamid": sid, "appid": appid})
    stats = ((data or {}).get("playerstats") or {})
    if stats.get("success") is False:
        raise RuntimeError(f"Steam could not return achievements: {stats.get('error', 'unknown error')}")
    achievements = stats.get("achievements") or []
    achieved = [a.get("apiname") for a in achievements if a.get("achieved")]
    print(json.dumps({
        "game": stats.get("gameName"),
        "appid": appid,
        "totalAchievements": len(achievements),
        "achievedCount": len(achieved),
        "achieved": achieved[:500],
    }))


def get_app_news():
    appid = require_app_id()
    count = clamp(params.get("count", 5), 5, 20)
    data = request("/ISteamNews/GetNewsForApp/v2/",
                   {"appid": appid, "count": count})
    items = [news_summary(i) for i in ((data or {}).get("appnews") or {}).get("newsitems", [])]
    print(json.dumps({"appid": appid, "count": len(items), "news": items}))


def get_current_players():
    appid = require_app_id()
    data = request("/ISteamUserStats/GetNumberOfCurrentPlayers/v1/",
                   {"appid": appid})
    result = ((data or {}).get("response") or {})
    print(json.dumps({"appid": appid, "playerCount": result.get("player_count")}))


HANDLERS = {
    "steam.resolve_vanity_url": resolve_vanity_url,
    "steam.get_player_summary": get_player_summary,
    "steam.get_owned_games": get_owned_games,
    "steam.get_recently_played": get_recently_played,
    "steam.get_player_achievements": get_player_achievements,
    "steam.get_app_news": get_app_news,
    "steam.get_current_players": get_current_players,
}

KEYLESS_TOOLS = {"steam.get_app_news", "steam.get_current_players"}

try:
    handler = HANDLERS.get(tool_name)
    if handler is None:
        print(json.dumps({"error": f"Unknown tool: {tool_name}"}))
    elif tool_name not in KEYLESS_TOOLS and not api_key:
        print(json.dumps({"error": "Missing Steam Web API key: connect the Steam integration first (api_key). Get a key at https://steamcommunity.com/dev/apikey."}))
    else:
        handler()
except (RuntimeError, ValueError) as e:
    print(json.dumps({"error": str(e)}))
except Exception as e:  # noqa: BLE001
    print(json.dumps({"error": f"Unexpected error: {type(e).__name__}: {e}"}))
