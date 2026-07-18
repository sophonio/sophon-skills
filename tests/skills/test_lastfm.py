"""Offline mock-HTTP integration tests for the lastfm skill."""
import json
import sys

from mockhttp import run_tool, resp, err, check

BASE = "https://ws.audioscrobbler.com/2.0/"
KEY = "k3ySECRETvalue9f8e7d"


def creds(**extra):
    p = {"api_key": KEY}
    p.update(extra)
    return p


ok = True

# ---------------------------------------------------------------------------
# 1. lastfm.get_artist_info — happy path + auth exactness (api_key query param)
# ---------------------------------------------------------------------------
print("scenario: get_artist_info happy path / auth exactness")
out, ex = run_tool("lastfm", creds(tool="lastfm.get_artist_info", artist="The Cure"), [
    resp(200, body={"artist": {
        "name": "The Cure",
        "url": "https://www.last.fm/music/The+Cure",
        "stats": {"listeners": "2600000", "playcount": "180000000"},
        "tags": {"tag": [{"name": "post-punk", "url": "x"}, {"name": "new wave", "url": "y"}]},
        "bio": {"summary": "  The Cure are an English rock band. <a href=\"https://www.last.fm/music/The+Cure\">Read more on Last.fm</a>  ",
                "content": "very long full bio that should not be returned"},
        "similar": {"artist": [{"name": "should-not-leak"}]},
    }}),
])
ok &= check("one request made", len(ex) == 1, repr(ex))
ok &= check("method GET", ex[0].method == "GET", ex[0].method)
ok &= check("URL byte-exact (api_key + format=json in query)",
            ex[0].url == f"{BASE}?method=artist.getinfo&artist=The+Cure&api_key={KEY}&format=json",
            ex[0].url)
ok &= check("no Authorization header (auth is query-param only)",
            "authorization" not in ex[0].headers, str(ex[0].headers))
ok &= check("descriptive User-Agent", ex[0].headers.get("user-agent") == "sophon-lastfm-skill",
            str(ex[0].headers))
ok &= check("Accept header", ex[0].headers.get("accept") == "application/json", str(ex[0].headers))
ok &= check("no request body", ex[0].body is None, str(ex[0].body))
ok &= check("name/url/listeners/playcount shaped",
            out.get("name") == "The Cure" and out.get("url") == "https://www.last.fm/music/The+Cure"
            and out.get("listeners") == "2600000" and out.get("playcount") == "180000000",
            str(out)[:300])
ok &= check("tags flattened to names", out.get("tags") == ["post-punk", "new wave"], str(out)[:300])
ok &= check("bio summary stripped", out.get("bio", "").startswith("The Cure are an English"),
            str(out.get("bio"))[:200])
ok &= check("raw payload not echoed (similar/full bio absent)",
            "should-not-leak" not in json.dumps(out) and "very long full bio" not in json.dumps(out),
            str(out)[:300])
ok &= check("api key not echoed in output", KEY not in json.dumps(out))

# ---------------------------------------------------------------------------
# 2. lastfm.get_similar_artists — limit clamp + single-item dict coercion
# ---------------------------------------------------------------------------
print("scenario: get_similar_artists clamps limit and coerces single dict to list")
out, ex = run_tool("lastfm", creds(tool="lastfm.get_similar_artists",
                                   artist="Radiohead", limit=999), [
    resp(200, body={"similarartists": {"artist": {"name": "Thom Yorke", "match": "1.0",
                                                  "url": "https://www.last.fm/music/Thom+Yorke",
                                                  "image": [{"#text": "img"}]}}}),
])
ok &= check("URL byte-exact with clamped limit=50",
            ex[0].url == f"{BASE}?method=artist.getsimilar&artist=Radiohead&limit=50&api_key={KEY}&format=json",
            ex[0].url)
ok &= check("single dict coerced: count == 1", out.get("count") == 1, str(out))
ok &= check("artist shaped (name/match/url only)",
            out["artists"][0] == {"name": "Thom Yorke", "match": "1.0",
                                  "url": "https://www.last.fm/music/Thom+Yorke"},
            str(out["artists"][0]))

# ---------------------------------------------------------------------------
# 3. lastfm.get_artist_top_tracks — happy path
# ---------------------------------------------------------------------------
print("scenario: get_artist_top_tracks happy path")
out, ex = run_tool("lastfm", creds(tool="lastfm.get_artist_top_tracks", artist="Nirvana"), [
    resp(200, body={"toptracks": {"track": [
        {"name": "Smells Like Teen Spirit", "playcount": "9000000", "listeners": "2000000",
         "url": "https://www.last.fm/music/Nirvana/_/Smells+Like+Teen+Spirit",
         "streamable": "0", "image": []},
        {"name": "Come as You Are", "playcount": "7000000", "listeners": "1800000",
         "url": "https://www.last.fm/music/Nirvana/_/Come+as+You+Are"},
    ]}}),
])
ok &= check("URL byte-exact with default limit=10",
            ex[0].url == f"{BASE}?method=artist.gettoptracks&artist=Nirvana&limit=10&api_key={KEY}&format=json",
            ex[0].url)
ok &= check("count == 2", out.get("count") == 2, str(out)[:200])
ok &= check("track shaped with Last.fm url",
            out["tracks"][0] == {"name": "Smells Like Teen Spirit", "playcount": "9000000",
                                 "listeners": "2000000",
                                 "url": "https://www.last.fm/music/Nirvana/_/Smells+Like+Teen+Spirit"},
            str(out["tracks"][0]))
ok &= check("raw streamable/image absent", "streamable" not in out["tracks"][0]
            and "image" not in out["tracks"][0], str(out["tracks"][0]))

# ---------------------------------------------------------------------------
# 4. lastfm.search_tracks — parses results.trackmatches.track
# ---------------------------------------------------------------------------
print("scenario: search_tracks parses results.trackmatches.track")
out, ex = run_tool("lastfm", creds(tool="lastfm.search_tracks", track="Believe", limit=2), [
    resp(200, body={"results": {
        "opensearch:totalResults": "12345",
        "trackmatches": {"track": [
            {"name": "Believe", "artist": "Cher", "listeners": "500000",
             "url": "https://www.last.fm/music/Cher/_/Believe", "mbid": "raw-mbid"},
            {"name": "Believe", "artist": "Elton John", "listeners": "90000",
             "url": "https://www.last.fm/music/Elton+John/_/Believe"},
        ]},
    }}),
])
ok &= check("URL byte-exact",
            ex[0].url == f"{BASE}?method=track.search&track=Believe&limit=2&api_key={KEY}&format=json",
            ex[0].url)
ok &= check("count == 2", out.get("count") == 2, str(out)[:200])
ok &= check("track shaped (name/artist/listeners/url)",
            out["tracks"][0] == {"name": "Believe", "artist": "Cher", "listeners": "500000",
                                 "url": "https://www.last.fm/music/Cher/_/Believe"},
            str(out["tracks"][0]))
ok &= check("raw mbid absent", "mbid" not in out["tracks"][0], str(out["tracks"][0]))

# ---------------------------------------------------------------------------
# 5. lastfm.get_tag_top_artists + lastfm.get_chart_top_artists
# ---------------------------------------------------------------------------
print("scenario: get_tag_top_artists happy path")
out, ex = run_tool("lastfm", creds(tool="lastfm.get_tag_top_artists", tag="shoegaze"), [
    resp(200, body={"topartists": {"artist": [
        {"name": "Slowdive", "url": "https://www.last.fm/music/Slowdive",
         "@attr": {"rank": "1"}}]}}),
])
ok &= check("URL byte-exact",
            ex[0].url == f"{BASE}?method=tag.gettopartists&tag=shoegaze&limit=10&api_key={KEY}&format=json",
            ex[0].url)
ok &= check("tag echoed + shaped artist",
            out == {"tag": "shoegaze", "count": 1,
                    "artists": [{"name": "Slowdive", "url": "https://www.last.fm/music/Slowdive"}]},
            str(out))

print("scenario: get_chart_top_artists happy path")
out, ex = run_tool("lastfm", creds(tool="lastfm.get_chart_top_artists", limit=1), [
    resp(200, body={"artists": {"artist": [
        {"name": "Taylor Swift", "playcount": "999", "listeners": "888",
         "url": "https://www.last.fm/music/Taylor+Swift"}]}}),
])
ok &= check("URL byte-exact",
            ex[0].url == f"{BASE}?method=chart.gettopartists&limit=1&api_key={KEY}&format=json",
            ex[0].url)
ok &= check("chart shaped",
            out == {"count": 1, "artists": [{"name": "Taylor Swift", "playcount": "999",
                                             "listeners": "888",
                                             "url": "https://www.last.fm/music/Taylor+Swift"}]},
            str(out))

# ---------------------------------------------------------------------------
# 6. lastfm.get_user_recent_tracks — nowplaying + default_username fallback
# ---------------------------------------------------------------------------
print("scenario: get_user_recent_tracks with explicit username, nowplaying handling")
out, ex = run_tool("lastfm", creds(tool="lastfm.get_user_recent_tracks", username="musicfan"), [
    resp(200, body={"recenttracks": {"track": [
        {"name": "Weird Fishes", "artist": {"#text": "Radiohead", "mbid": ""},
         "@attr": {"nowplaying": "true"},
         "url": "https://www.last.fm/music/Radiohead/_/Weird+Fishes"},
        {"name": "Alameda", "artist": {"#text": "Elliott Smith", "mbid": ""},
         "date": {"uts": "1789000000", "#text": "17 Jul 2026, 12:00"},
         "url": "https://www.last.fm/music/Elliott+Smith/_/Alameda"},
    ]}}),
])
ok &= check("URL byte-exact",
            ex[0].url == f"{BASE}?method=user.getrecenttracks&user=musicfan&limit=10&api_key={KEY}&format=json",
            ex[0].url)
ok &= check("count == 2", out.get("count") == 2, str(out)[:200])
ok &= check("nowplaying track flagged, no date",
            out["tracks"][0]["nowplaying"] is True and out["tracks"][0]["date"] is None
            and out["tracks"][0]["artist"] == "Radiohead", str(out["tracks"][0]))
ok &= check("dated track has date text and not nowplaying",
            out["tracks"][1]["nowplaying"] is False
            and out["tracks"][1]["date"] == "17 Jul 2026, 12:00", str(out["tracks"][1]))

print("scenario: get_user_recent_tracks falls back to default_username")
out, ex = run_tool("lastfm", creds(tool="lastfm.get_user_recent_tracks",
                                   default_username="defaultfan"), [
    resp(200, body={"recenttracks": {"track": []}}),
])
ok &= check("default_username used in URL",
            ex[0].url == f"{BASE}?method=user.getrecenttracks&user=defaultfan&limit=10&api_key={KEY}&format=json",
            ex[0].url)
ok &= check("user echoed + empty count", out.get("user") == "defaultfan" and out.get("count") == 0,
            str(out))

print("scenario: user tool with no username and no default -> friendly error, no HTTP")
out, ex = run_tool("lastfm", creds(tool="lastfm.get_user_recent_tracks"), [])
ok &= check("username-required error",
            "username required" in out.get("error", "") and "default_username" in out["error"],
            str(out))
ok &= check("no HTTP request made", len(ex) == 0, repr(ex))

# ---------------------------------------------------------------------------
# 7. lastfm.get_user_top_artists — period validation
# ---------------------------------------------------------------------------
print("scenario: get_user_top_artists with period=7day")
out, ex = run_tool("lastfm", creds(tool="lastfm.get_user_top_artists",
                                   username="musicfan", period="7day", limit=2), [
    resp(200, body={"topartists": {"artist": [
        {"name": "Radiohead", "playcount": "42",
         "url": "https://www.last.fm/music/Radiohead", "@attr": {"rank": "1"}}]}}),
])
ok &= check("URL byte-exact with period",
            ex[0].url == f"{BASE}?method=user.gettopartists&user=musicfan&period=7day&limit=2&api_key={KEY}&format=json",
            ex[0].url)
ok &= check("shaped output with user/period",
            out == {"user": "musicfan", "period": "7day", "count": 1,
                    "artists": [{"name": "Radiohead", "playcount": "42",
                                 "url": "https://www.last.fm/music/Radiohead"}]},
            str(out))

print("scenario: invalid period rejected before any HTTP call")
out, ex = run_tool("lastfm", creds(tool="lastfm.get_user_top_artists",
                                   username="musicfan", period="2weeks"), [])
ok &= check("period validation error", "period must be one of" in out.get("error", ""), str(out))
ok &= check("no HTTP request made", len(ex) == 0, repr(ex))

# ---------------------------------------------------------------------------
# 8. ERROR PATHS
# ---------------------------------------------------------------------------
print("scenario: HTTP-200 JSON error envelope {error, message} is detected")
out, ex = run_tool("lastfm", creds(tool="lastfm.get_user_recent_tracks", username="ghost"), [
    resp(200, body={"error": 6, "message": "User not found"}),
])
raw = json.dumps(out)
ok &= check("error surfaced from 200 body",
            "error" in out and "User not found" in out["error"] and "6" in out["error"], raw[:200])
ok &= check("no traceback leaked", "Traceback" not in raw and "urllib" not in raw, raw[:300])

print("scenario: HTTP 403 surfaces friendly error, no secret echoed")
out, ex = run_tool("lastfm", creds(tool="lastfm.get_artist_info", artist="Cher"), [
    err(403, body={"error": 26, "message": "Suspended API key - Access for your account has been suspended"}),
])
raw = json.dumps(out)
ok &= check("403 error surfaced with API message",
            "403" in out.get("error", "") and "Suspended API key" in out["error"], raw[:300])
ok &= check("no traceback leaked",
            "Traceback" not in raw and "HTTPError" not in raw and "urllib" not in raw, raw[:300])
ok &= check("api key value not leaked in error", KEY not in raw, raw[:300])

print("scenario: 429 includes Retry-After and slow-down hint")
out, ex = run_tool("lastfm", creds(tool="lastfm.search_tracks", track="x"), [
    err(429, body={"error": 29, "message": "Rate limit exceeded"},
        headers={"Retry-After": "30"}),
])
ok &= check("429 surfaced", "429" in out.get("error", ""), str(out)[:300])
ok &= check("slow-down hint present", "rate limited, slow down" in out["error"], out["error"])
ok &= check("Retry-After included", "30" in out["error"], out["error"])

print("scenario: non-JSON error body tolerated")
out, ex = run_tool("lastfm", creds(tool="lastfm.get_artist_info", artist="Cher"), [
    err(502, body="<html>bad gateway</html>"),
])
ok &= check("502 non-JSON body still friendly",
            "error" in out and "502" in out["error"] and "Traceback" not in json.dumps(out),
            str(out)[:300])

print("scenario: missing credentials -> connect-first error, no HTTP call")
out, ex = run_tool("lastfm", {"tool": "lastfm.get_chart_top_artists", "api_key": ""}, [])
ok &= check("missing-credentials message names api_key",
            "connect the Last.fm integration first" in out.get("error", "")
            and "api_key" in out["error"], str(out))
ok &= check("no HTTP request made", len(ex) == 0, repr(ex))

print("scenario: missing required param -> friendly error, no HTTP call")
out, ex = run_tool("lastfm", creds(tool="lastfm.get_artist_info"), [])
ok &= check("artist required error", out.get("error") == "artist required", str(out))
ok &= check("no HTTP request made", len(ex) == 0, repr(ex))

print("scenario: unknown tool -> friendly error")
out, ex = run_tool("lastfm", creds(tool="lastfm.nope"), [])
ok &= check("unknown tool error", out.get("error") == "Unknown tool: lastfm.nope", str(out))

# ---------------------------------------------------------------------------
# 9. SECURITY PROBES
# ---------------------------------------------------------------------------
print("scenario: injection-shaped artist value is fully percent-encoded in the query")
evil = "a/../b&api_key=stolen"
out, ex = run_tool("lastfm", creds(tool="lastfm.get_artist_info", artist=evil), [
    resp(200, body={"artist": {"name": "x", "stats": {}, "tags": {}, "bio": {}}}),
])
ok &= check("evil value urlencoded (no raw '../', '&', '=')",
            "artist=a%2F..%2Fb%26api_key%3Dstolen" in ex[0].url and "../" not in ex[0].url,
            ex[0].url)
ok &= check("no injected duplicate api_key param",
            ex[0].url.count("&api_key=") == 1, ex[0].url)
ok &= check("request stays on the Last.fm API host",
            ex[0].url.startswith(BASE), ex[0].url)

print("scenario: secret never appears in any output (error path)")
out, ex = run_tool("lastfm", creds(tool="lastfm.get_tag_top_artists", tag="jazz"), [
    err(500, body={"error": 16, "message": "temporary error"}),
])
ok &= check("api_key absent from error output", KEY not in json.dumps(out),
            json.dumps(out)[:300])

print()
print("RESULT:", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
