"""Offline mock-HTTP integration tests for the steam skill."""
import json
import sys

from mockhttp import run_tool, resp, err, check

BASE = "https://api.steampowered.com"
KEY = "AAAA1111BBBB2222SECRETKEY"
SID = "76561197960287930"


def creds(**extra):
    p = {"api_key": KEY, "default_steam_id": SID}
    p.update(extra)
    return p


def keyless(**extra):
    p = {"api_key": "", "default_steam_id": ""}
    p.update(extra)
    return p


ok = True

# ---------------------------------------------------------------------------
# 1. steam.get_player_summary — happy path + auth exactness (key as query param)
# ---------------------------------------------------------------------------
print("scenario: get_player_summary happy path / auth exactness")
out, ex = run_tool("steam", creds(tool="steam.get_player_summary"), [
    resp(200, body={"response": {"players": [
        {"steamid": SID, "personaname": "Robin", "profileurl": f"https://steamcommunity.com/id/robin/",
         "personastate": 1, "gameextrainfo": "Half-Life 3",
         "communityvisibilitystate": 3, "avatarfull": "https://a/b.jpg",
         "lastlogoff": 1789000000, "primaryclanid": "raw"}]}}),
])
ok &= check("one request made", len(ex) == 1, repr(ex))
ok &= check("method GET", ex[0].method == "GET", ex[0].method)
ok &= check("URL byte-exact: key is a query param, first, no Authorization scheme",
            ex[0].url == f"{BASE}/ISteamUser/GetPlayerSummaries/v2/?key={KEY}&steamids={SID}",
            ex[0].url)
ok &= check("no Authorization header (Steam auth is query-param only)",
            "authorization" not in ex[0].headers, str(ex[0].headers))
ok &= check("User-Agent is sophon-steam-skill",
            ex[0].headers.get("user-agent") == "sophon-steam-skill", str(ex[0].headers))
ok &= check("Accept header", ex[0].headers.get("accept") == "application/json", str(ex[0].headers))
ok &= check("no request body", ex[0].body is None, str(ex[0].body))
ok &= check("count == 1", out.get("count") == 1, str(out)[:200])
p = out["players"][0]
ok &= check("shaped fields: personaname/profileurl/gameextrainfo",
            p["personaname"] == "Robin" and p["gameextrainfo"] == "Half-Life 3"
            and p["profileurl"].endswith("/robin/"), str(p))
ok &= check("personastate mapped to label", p["personastate"] == "Online", str(p))
ok &= check("raw fields absent (avatarfull/communityvisibilitystate/primaryclanid)",
            "avatarfull" not in p and "communityvisibilitystate" not in p
            and "primaryclanid" not in p, str(p))
ok &= check("api key not echoed in output", KEY not in json.dumps(out))

# comma list of explicit steamIds
print("scenario: get_player_summary accepts comma list")
out, ex = run_tool("steam", creds(tool="steam.get_player_summary",
                                  steamIds="111, 222 ,333"), [
    resp(200, body={"response": {"players": []}}),
])
ok &= check("comma list normalized and encoded",
            ex[0].url == f"{BASE}/ISteamUser/GetPlayerSummaries/v2/?key={KEY}&steamids=111%2C222%2C333",
            ex[0].url)
ok &= check("empty result count 0", out.get("count") == 0, str(out))

# ---------------------------------------------------------------------------
# 2. steam.get_owned_games — happy path + private-profile note
# ---------------------------------------------------------------------------
print("scenario: get_owned_games happy path")
out, ex = run_tool("steam", creds(tool="steam.get_owned_games"), [
    resp(200, body={"response": {"game_count": 2, "games": [
        {"appid": 440, "name": "Team Fortress 2", "playtime_forever": 60,
         "img_icon_url": "abc", "playtime_windows_forever": 60},
        {"appid": 570, "name": "Dota 2", "playtime_forever": 6000,
         "playtime_2weeks": 120, "img_icon_url": "def"}]}}),
])
ok &= check("URL byte-exact incl include_appinfo/include_played_free_games",
            ex[0].url == f"{BASE}/IPlayerService/GetOwnedGames/v1/?key={KEY}&steamid={SID}"
                         "&include_appinfo=1&include_played_free_games=1", ex[0].url)
ok &= check("count from game_count", out.get("count") == 2, str(out)[:200])
ok &= check("sorted by playtime desc", out["games"][0]["appid"] == 570, str(out)[:300])
g = out["games"][0]
ok &= check("game shaped: appid/name/playtime_forever/hours/2weeks",
            g["name"] == "Dota 2" and g["playtime_forever"] == 6000
            and g["playtime_hours"] == 100.0 and g["playtime_2weeks"] == 120, str(g))
ok &= check("raw fields absent (img_icon_url/platform playtimes)",
            "img_icon_url" not in g and "playtime_windows_forever" not in json.dumps(out),
            str(g))

print("scenario: get_owned_games private profile -> empty + note")
out, ex = run_tool("steam", creds(tool="steam.get_owned_games"), [
    resp(200, body={"response": {}}),
])
ok &= check("count 0 and games empty", out.get("count") == 0 and out.get("games") == [],
            str(out))
ok &= check("private-profile note present", "private" in out.get("note", "").lower(), str(out))

# ---------------------------------------------------------------------------
# 3. steam.get_recently_played — happy path (explicit steamId overrides default)
# ---------------------------------------------------------------------------
print("scenario: get_recently_played happy path")
out, ex = run_tool("steam", creds(tool="steam.get_recently_played", steamId="76561198000000001",
                                  count=2), [
    resp(200, body={"response": {"total_count": 1, "games": [
        {"appid": 730, "name": "Counter-Strike 2", "playtime_2weeks": 90,
         "playtime_forever": 3000, "img_icon_url": "xyz"}]}}),
])
ok &= check("URL byte-exact with explicit steamId and count",
            ex[0].url == f"{BASE}/IPlayerService/GetRecentlyPlayedGames/v1/?key={KEY}"
                         "&steamid=76561198000000001&count=2", ex[0].url)
ok &= check("shaped game with 2-week playtime",
            out["games"][0]["playtime_2weeks"] == 90
            and out["games"][0]["name"] == "Counter-Strike 2", str(out)[:300])

# ---------------------------------------------------------------------------
# 4. steam.get_player_achievements — happy path
# ---------------------------------------------------------------------------
print("scenario: get_player_achievements happy path")
out, ex = run_tool("steam", creds(tool="steam.get_player_achievements", appId=440), [
    resp(200, body={"playerstats": {"steamID": SID, "gameName": "Team Fortress 2",
                                    "success": True, "achievements": [
        {"apiname": "TF_GET_HEADSHOTS", "achieved": 1, "unlocktime": 1700000000},
        {"apiname": "TF_KILL_NEMESIS", "achieved": 0, "unlocktime": 0},
        {"apiname": "TF_BURN_PLAYERS", "achieved": 1, "unlocktime": 1700000001}]}}),
])
ok &= check("URL byte-exact",
            ex[0].url == f"{BASE}/ISteamUserStats/GetPlayerAchievements/v1/?key={KEY}"
                         f"&steamid={SID}&appid=440", ex[0].url)
ok &= check("counts computed",
            out.get("totalAchievements") == 3 and out.get("achievedCount") == 2, str(out))
ok &= check("achieved list trimmed to unlocked apinames",
            out.get("achieved") == ["TF_GET_HEADSHOTS", "TF_BURN_PLAYERS"], str(out))
ok &= check("game name surfaced", out.get("game") == "Team Fortress 2", str(out))
ok &= check("raw unlocktime/achieved flags absent", "unlocktime" not in json.dumps(out),
            str(out)[:300])

# ---------------------------------------------------------------------------
# 5. steam.resolve_vanity_url — happy path + no-match
# ---------------------------------------------------------------------------
print("scenario: resolve_vanity_url happy path")
out, ex = run_tool("steam", creds(tool="steam.resolve_vanity_url", vanityUrl="gabelogannewell"), [
    resp(200, body={"response": {"steamid": "76561197960287930", "success": 1}}),
])
ok &= check("URL byte-exact",
            ex[0].url == f"{BASE}/ISteamUser/ResolveVanityURL/v1/?key={KEY}"
                         "&vanityurl=gabelogannewell", ex[0].url)
ok &= check("steamid returned",
            out == {"vanityUrl": "gabelogannewell", "steamid": "76561197960287930"}, str(out))

print("scenario: resolve_vanity_url no match -> friendly error")
out, ex = run_tool("steam", creds(tool="steam.resolve_vanity_url", vanityUrl="nobody-here"), [
    resp(200, body={"response": {"success": 42, "message": "No match"}}),
])
ok &= check("no-match friendly error",
            "No Steam account found" in out.get("error", ""), str(out))
ok &= check("no traceback", "Traceback" not in json.dumps(out), str(out))

# ---------------------------------------------------------------------------
# 6. KEYLESS TOOLS — work with no key, and never send the key even when present
# ---------------------------------------------------------------------------
print("scenario: get_app_news keyless (no key configured)")
long_contents = "patch notes " * 100  # > 500 chars
out, ex = run_tool("steam", keyless(tool="steam.get_app_news", appId=730, count=2), [
    resp(200, body={"appnews": {"appid": 730, "newsitems": [
        {"gid": "g1", "title": "CS2 Update", "url": "https://steamcommunity.com/news/1",
         "author": "Valve", "date": 1789000000, "feedlabel": "Product Update",
         "contents": long_contents, "feed_type": 1}]}}),
])
ok &= check("URL byte-exact, no key param",
            ex[0].url == f"{BASE}/ISteamNews/GetNewsForApp/v2/?appid=730&count=2", ex[0].url)
ok &= check("news item shaped", out["news"][0]["title"] == "CS2 Update"
            and out["news"][0]["feedlabel"] == "Product Update"
            and out["news"][0]["author"] == "Valve", str(out)[:300])
ok &= check("contents trimmed to 500 chars + ellipsis",
            len(out["news"][0]["contents"]) == 503
            and out["news"][0]["contents"].endswith("..."), str(len(out["news"][0]["contents"])))
ok &= check("raw gid/feed_type absent", "gid" not in out["news"][0]
            and "feed_type" not in out["news"][0], str(out["news"][0]))

print("scenario: get_app_news does NOT leak the key even when configured")
out, ex = run_tool("steam", creds(tool="steam.get_app_news", appId=730), [
    resp(200, body={"appnews": {"appid": 730, "newsitems": []}}),
])
ok &= check("key absent from keyless endpoint URL", KEY not in ex[0].url, ex[0].url)
ok &= check("default count is 5",
            ex[0].url == f"{BASE}/ISteamNews/GetNewsForApp/v2/?appid=730&count=5", ex[0].url)

print("scenario: get_current_players keyless")
out, ex = run_tool("steam", keyless(tool="steam.get_current_players", appId=570), [
    resp(200, body={"response": {"player_count": 654321, "result": 1}}),
])
ok &= check("URL byte-exact", ex[0].url == f"{BASE}/ISteamUserStats/GetNumberOfCurrentPlayers/v1/"
            "?appid=570", ex[0].url)
ok &= check("player count shaped", out == {"appid": 570, "playerCount": 654321}, str(out))

# ---------------------------------------------------------------------------
# 7. CREDENTIAL GATE — key-required tools without a key; steamId fallback missing
# ---------------------------------------------------------------------------
print("scenario: key-required tool with no key -> connect-first error, no HTTP")
out, ex = run_tool("steam", keyless(tool="steam.get_owned_games", steamId=SID), [])
ok &= check("connect-first message",
            "connect the Steam integration first" in out.get("error", "")
            and "api_key" in out.get("error", ""), str(out))
ok &= check("no HTTP request made", len(ex) == 0, repr(ex))

print("scenario: missing steamId and no default -> friendly error, no HTTP")
out, ex = run_tool("steam", {"api_key": KEY, "default_steam_id": "",
                             "tool": "steam.get_owned_games"}, [])
ok &= check("steamId-required error mentions default_steam_id",
            "steamId required" in out.get("error", "")
            and "default_steam_id" in out.get("error", ""), str(out))
ok &= check("no HTTP request made", len(ex) == 0, repr(ex))

print("scenario: unknown tool -> friendly error")
out, ex = run_tool("steam", creds(tool="steam.nope"), [])
ok &= check("unknown tool error", out.get("error") == "Unknown tool: steam.nope", str(out))

# ---------------------------------------------------------------------------
# 8. ERROR PATHS — 403 HTML body, playerstats error body, 429 with Retry-After
# ---------------------------------------------------------------------------
print("scenario: 403 with HTML body -> friendly error, no traceback, no secret")
out, ex = run_tool("steam", creds(tool="steam.get_owned_games"), [
    err(403, body="<html><head><title>Forbidden</title></head></html>"),
])
raw = json.dumps(out)
ok &= check("error key present", "error" in out and isinstance(out["error"], str), raw[:200])
ok &= check("includes HTTP status 403", "403" in out["error"], out.get("error", ""))
ok &= check("hints at key/profile validity", "Web API key" in out["error"], out.get("error", ""))
ok &= check("no Python traceback leaked",
            "Traceback" not in raw and "urllib" not in raw and "HTTPError" not in raw, raw[:300])
ok &= check("api key not leaked in error output", KEY not in raw, raw[:300])

print("scenario: playerstats JSON error body surfaced (private profile)")
out, ex = run_tool("steam", creds(tool="steam.get_player_achievements", appId=440), [
    err(403, body={"playerstats": {"error": "Profile is not public", "success": False}}),
])
ok &= check("playerstats.error parsed into message",
            "403" in out.get("error", "") and "Profile is not public" in out.get("error", ""),
            str(out))

print("scenario: 429 includes Retry-After and slow-down hint")
out, ex = run_tool("steam", creds(tool="steam.get_player_summary"), [
    err(429, body="Too Many Requests", headers={"Retry-After": "120"}),
])
ok &= check("429 surfaced", "429" in out.get("error", ""), str(out))
ok &= check("rate-limit hint present", "rate limited, slow down" in out.get("error", ""),
            out.get("error", ""))
ok &= check("Retry-After value included", "120" in out.get("error", ""), out.get("error", ""))

# ---------------------------------------------------------------------------
# 9. SECURITY PROBES
# ---------------------------------------------------------------------------
print("scenario: injection-shaped steamId is percent-encoded into the query")
evil = "123/../ISteamUser/Evil?x=1&y=2"
out, ex = run_tool("steam", creds(tool="steam.get_owned_games", steamId=evil), [
    resp(200, body={"response": {}}),
])
ok &= check("steamId fully urlencoded (no path escape, no extra query params)",
            ex[0].url == f"{BASE}/IPlayerService/GetOwnedGames/v1/?key={KEY}"
                         "&steamid=123%2F..%2FISteamUser%2FEvil%3Fx%3D1%26y%3D2"
                         "&include_appinfo=1&include_played_free_games=1", ex[0].url)
ok &= check("no raw '/../' or '&y=' injected", "/../" not in ex[0].url and "&y=" not in ex[0].url,
            ex[0].url)

print("scenario: non-numeric appId rejected before any HTTP")
out, ex = run_tool("steam", keyless(tool="steam.get_current_players",
                                    appId="570/../../admin"), [])
ok &= check("appId must be a number", out.get("error") == "appId must be a number", str(out))
ok &= check("no HTTP request made", len(ex) == 0, repr(ex))

print("scenario: secret never appears in any output (happy + error paths)")
out, ex = run_tool("steam", creds(tool="steam.resolve_vanity_url", vanityUrl="x"), [
    err(500, body="Internal Server Error"),
])
ok &= check("500 friendly and key absent", "500" in out.get("error", "")
            and KEY not in json.dumps(out), str(out)[:300])

print()
print("RESULT:", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
