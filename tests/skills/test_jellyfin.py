"""Offline mock-HTTP integration tests for the jellyfin skill."""
import json
import sys

from mockhttp import run_tool, resp, err, check

BASE = "http://192.168.1.10:8096"
KEY = "JELLYFIN-ADMIN-KEY-9f9f"
UID = "user-abc-123"


def creds(**extra):
    p = {"base_url": BASE, "api_key": KEY}
    p.update(extra)
    return p


ok = True

# ---------------------------------------------------------------------------
# 1. search_library — happy path + MediaBrowser auth header exactness
# ---------------------------------------------------------------------------
print("scenario: search_library happy path / auth header exactness")
out, ex = run_tool("jellyfin", creds(tool="jellyfin.search_library", searchTerm="blade runner"), [
    resp(200, body={"Items": [
        {"Id": "i1", "Name": "Blade Runner", "Type": "Movie", "ProductionYear": 1982,
         "Overview": "long text", "MediaSources": [{"x": 1}]},
        {"Id": "i2", "Name": "Blade Runner 2049", "Type": "Movie", "ProductionYear": 2017},
    ], "TotalRecordCount": 2}),
])
ok &= check("one request made", len(ex) == 1, repr(ex))
ok &= check("method GET", ex[0].method == "GET", ex[0].method)
ok &= check("URL byte-exact (searchTerm/recursive/limit)",
            ex[0].url == f"{BASE}/Items?searchTerm=blade+runner&recursive=true&limit=25",
            ex[0].url)
auth = ex[0].headers.get("authorization", "")
ok &= check("Authorization is MediaBrowser scheme with token",
            auth.startswith('MediaBrowser ') and f'Token="{KEY}"' in auth, auth)
ok &= check("auth header carries Client/Device/DeviceId/Version",
            'Client="sophon"' in auth and 'Device="sophon"' in auth
            and 'DeviceId="sophon-jellyfin"' in auth and 'Version="1.0"' in auth, auth)
ok &= check("no legacy X-Emby-Token header",
            "x-emby-token" not in ex[0].headers and "x-mediabrowser-token" not in ex[0].headers,
            str(ex[0].headers))
ok &= check("no api_key query param", "api_key" not in ex[0].url and "ApiKey" not in ex[0].url,
            ex[0].url)
ok &= check("Accept json", ex[0].headers.get("accept") == "application/json", str(ex[0].headers))
ok &= check("User-Agent set", ex[0].headers.get("user-agent") == "sophon-jellyfin-skill",
            str(ex[0].headers))
ok &= check("count == 2", out.get("count") == 2, str(out)[:200])
ok &= check("item shaped", out["items"][0] == {"id": "i1", "name": "Blade Runner", "type": "Movie",
                                               "year": 1982, "seriesName": None},
            str(out["items"][0]))
ok &= check("raw Overview/MediaSources absent from list item",
            "overview" not in out["items"][0] and "MediaSources" not in out["items"][0],
            str(out["items"][0]))
ok &= check("key not echoed in output", KEY not in json.dumps(out))

print("scenario: search_library includeItemTypes + limit clamp")
out, ex = run_tool("jellyfin", creds(tool="jellyfin.search_library", searchTerm="x",
                                     includeItemTypes="Movie,Series", limit=9000), [
    resp(200, body={"Items": []}),
])
ok &= check("URL has includeItemTypes and clamped limit=100",
            ex[0].url == f"{BASE}/Items?searchTerm=x&recursive=true&limit=100&includeItemTypes=Movie%2CSeries",
            ex[0].url)

# ---------------------------------------------------------------------------
# 2. get_item — user-scoped path via default_user_id + shaping
# ---------------------------------------------------------------------------
print("scenario: get_item uses /Users/{uid}/Items/{id} when default user set")
out, ex = run_tool("jellyfin", creds(tool="jellyfin.get_item", itemId="i1",
                                     default_user_id=UID), [
    resp(200, body={"Id": "i1", "Name": "Blade Runner", "Type": "Movie", "ProductionYear": 1982,
                    "Overview": "A blade runner must pursue replicants.",
                    "Genres": ["Sci-Fi"], "RunTimeTicks": 100,
                    "People": [{"Name": "Harrison Ford", "Role": "Deckard", "Type": "Actor",
                                "Id": "p1", "PrimaryImageTag": "t"}],
                    "MediaStreams": [{"Type": "Video", "Codec": "h264", "Language": "eng",
                                      "DisplayTitle": "1080p", "Extra": "noise"}]}),
])
ok &= check("URL uses user-scoped path", ex[0].url == f"{BASE}/Users/{UID}/Items/i1", ex[0].url)
ok &= check("overview present", out.get("overview") == "A blade runner must pursue replicants.",
            str(out)[:200])
ok &= check("people trimmed to name/role/type",
            out["people"][0] == {"name": "Harrison Ford", "role": "Deckard", "type": "Actor"},
            str(out.get("people")))
ok &= check("media streams trimmed",
            out["mediaStreams"][0] == {"type": "Video", "codec": "h264", "language": "eng",
                                       "displayTitle": "1080p"}, str(out.get("mediaStreams")))

print("scenario: get_item uses /Items/{id} when no user configured")
out, ex = run_tool("jellyfin", creds(tool="jellyfin.get_item", itemId="i9"), [
    resp(200, body={"Id": "i9", "Name": "X", "Type": "Movie"}),
])
ok &= check("URL uses non-user path", ex[0].url == f"{BASE}/Items/i9", ex[0].url)

# ---------------------------------------------------------------------------
# 3. list_libraries — two calls (folders + counts)
# ---------------------------------------------------------------------------
print("scenario: list_libraries folders + counts")
out, ex = run_tool("jellyfin", creds(tool="jellyfin.list_libraries"), [
    resp(200, body=[
        {"Name": "Movies", "ItemId": "lib1", "CollectionType": "movies",
         "Locations": ["/media/movies"], "RefreshStatus": "Idle"},
    ]),
    resp(200, body={"MovieCount": 500, "SeriesCount": 80, "EpisodeCount": 4000}),
])
ok &= check("two requests (VirtualFolders + Counts)",
            len(ex) == 2 and ex[0].url == f"{BASE}/Library/VirtualFolders"
            and ex[1].url == f"{BASE}/Items/Counts", repr(ex))
ok &= check("library shaped",
            out["libraries"][0] == {"name": "Movies", "itemId": "lib1",
                                    "collectionType": "movies", "locations": ["/media/movies"]},
            str(out["libraries"][0]))
ok &= check("totals surfaced", out["totals"].get("MovieCount") == 500, str(out.get("totals")))

# ---------------------------------------------------------------------------
# 4. get_active_sessions — nested NowPlaying/PlayState flattening
# ---------------------------------------------------------------------------
print("scenario: get_active_sessions")
out, ex = run_tool("jellyfin", creds(tool="jellyfin.get_active_sessions"), [
    resp(200, body=[
        {"UserName": "alice", "Client": "Jellyfin Web", "DeviceName": "Chrome",
         "NowPlayingItem": {"Name": "Blade Runner"}, "PlayState": {"IsPaused": False}},
        {"UserName": "bob", "Client": "Android", "DeviceName": "Pixel"},
    ]),
])
ok &= check("URL", ex[0].url == f"{BASE}/Sessions", ex[0].url)
ok &= check("session shaped",
            out["sessions"][0] == {"userName": "alice", "client": "Jellyfin Web",
                                   "deviceName": "Chrome", "nowPlaying": "Blade Runner",
                                   "isPaused": False}, str(out["sessions"][0]))
ok &= check("idle session tolerated (nowPlaying None)", out["sessions"][1]["nowPlaying"] is None,
            str(out["sessions"][1]))

# ---------------------------------------------------------------------------
# 5. get_next_up — userId default + requirement
# ---------------------------------------------------------------------------
print("scenario: get_next_up uses default user id")
out, ex = run_tool("jellyfin", creds(tool="jellyfin.get_next_up", default_user_id=UID), [
    resp(200, body={"Items": [
        {"Id": "e1", "SeriesName": "Severance", "Name": "Cold Harbor",
         "ParentIndexNumber": 2, "IndexNumber": 10},
    ]}),
])
ok &= check("URL byte-exact with userId + limit",
            ex[0].url == f"{BASE}/Shows/NextUp?userId={UID}&limit=20", ex[0].url)
ok &= check("next-up shaped",
            out["items"][0] == {"id": "e1", "seriesName": "Severance", "name": "Cold Harbor",
                                "seasonNumber": 2, "episodeNumber": 10}, str(out["items"][0]))

print("scenario: get_next_up without any user id -> friendly error, no HTTP")
out, ex = run_tool("jellyfin", creds(tool="jellyfin.get_next_up"), [])
ok &= check("userId required error", "userId required" in out.get("error", ""), str(out))
ok &= check("no HTTP request made", len(ex) == 0, repr(ex))

# ---------------------------------------------------------------------------
# 6. WRITE (low-risk) PATHS — refresh + scan
# ---------------------------------------------------------------------------
print("scenario: refresh_item_metadata POST")
out, ex = run_tool("jellyfin", creds(tool="jellyfin.refresh_item_metadata", itemId="i1"), [
    resp(204, body=""),
])
ok &= check("method POST", ex[0].method == "POST", ex[0].method)
ok &= check("URL byte-exact", ex[0].url == f"{BASE}/Items/i1/Refresh", ex[0].url)
ok &= check("result", out == {"itemId": "i1", "refreshTriggered": True}, str(out))

print("scenario: scan_library POST")
out, ex = run_tool("jellyfin", creds(tool="jellyfin.scan_library"), [resp(204, body="")])
ok &= check("method POST + URL", ex[0].method == "POST" and ex[0].url == f"{BASE}/Library/Refresh",
            ex[0].url)
ok &= check("result", out == {"scanTriggered": True}, str(out))

# ---------------------------------------------------------------------------
# 7. ERROR PATHS
# ---------------------------------------------------------------------------
print("scenario: 401 surfaces friendly error, no traceback, no key leak")
out, ex = run_tool("jellyfin", creds(tool="jellyfin.list_libraries"), [err(401, body="")])
raw = json.dumps(out)
ok &= check("error with 401", "error" in out and "401" in out["error"], raw[:200])
ok &= check("hints at API key", "API Keys" in out["error"], out.get("error", ""))
ok &= check("no traceback", "Traceback" not in raw and "urllib" not in raw, raw[:300])
ok &= check("key not leaked", KEY not in raw, raw[:300])

print("scenario: 429 includes Retry-After")
out, ex = run_tool("jellyfin", creds(tool="jellyfin.get_active_sessions"), [
    err(429, body="", headers={"Retry-After": "7"}),
])
ok &= check("429 rate-limit hint + retry", "rate limited, slow down" in out.get("error", "")
            and "retry after 7s" in out.get("error", ""), out.get("error", ""))

print("scenario: URLError self-hosted-unreachable branch present in source")
# mockhttp only injects HTTPError, so assert the URLError branch exists in the skill source.
import os
_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
src = open(os.path.join(_root, "skills", "jellyfin", "main.py"), encoding="utf-8").read()
ok &= check("URLError branch hints at sandbox reachability",
            "reachable from Sophon's sandbox" in src and "urllib.error.URLError" in src,
            "missing URLError handling")

print("scenario: missing credentials -> connect-first, no HTTP")
out, ex = run_tool("jellyfin", {"tool": "jellyfin.list_libraries", "base_url": "", "api_key": ""}, [])
ok &= check("connect-first names fields",
            out.get("error") == "Missing Jellyfin credentials: connect the Jellyfin integration "
                                "first (base_url, api_key).", str(out))
ok &= check("no HTTP", len(ex) == 0, repr(ex))

print("scenario: unknown tool")
out, ex = run_tool("jellyfin", creds(tool="jellyfin.nope"), [])
ok &= check("unknown tool error", out.get("error") == "Unknown tool: jellyfin.nope", str(out))

print("scenario: missing searchTerm -> friendly error, no HTTP")
out, ex = run_tool("jellyfin", creds(tool="jellyfin.search_library"), [])
ok &= check("searchTerm required", out.get("error") == "searchTerm required", str(out))
ok &= check("no HTTP", len(ex) == 0, repr(ex))

# ---------------------------------------------------------------------------
# 8. SECURITY PROBES
# ---------------------------------------------------------------------------
print("scenario: path-traversal itemId is percent-encoded")
out, ex = run_tool("jellyfin", creds(tool="jellyfin.refresh_item_metadata",
                                     itemId="i1/../System"), [resp(204, body="")])
ok &= check("itemId fully quoted (no path escape)",
            ex[0].url == f"{BASE}/Items/i1%2F..%2FSystem/Refresh", ex[0].url)
ok &= check("no raw '../' in path", "../" not in ex[0].url, ex[0].url)

print("scenario: bare '..' itemId rejected before HTTP")
out, ex = run_tool("jellyfin", creds(tool="jellyfin.get_item", itemId=".."), [])
ok &= check("dot-dot rejected", out.get("error") == "itemId must not be '.' or '..'", str(out))
ok &= check("no HTTP", len(ex) == 0, repr(ex))

print("scenario: secret never appears in output (error path)")
out, ex = run_tool("jellyfin", creds(tool="jellyfin.get_active_sessions"), [
    err(403, body={"message": "forbidden"}),
])
ok &= check("api_key absent from error output", KEY not in json.dumps(out), json.dumps(out)[:300])

print()
print("RESULT:", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
