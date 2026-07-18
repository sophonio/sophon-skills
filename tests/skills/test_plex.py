"""Offline mock-HTTP integration tests for the plex skill."""
import json
import sys

from mockhttp import run_tool, resp, err, check

BASE = "http://192.168.1.50:32400"
TOK = "plexTok-SECRET-VALUE"


def creds(**extra):
    p = {"base_url": BASE, "plex_token": TOK}
    p.update(extra)
    return p


ok = True

# ---------------------------------------------------------------------------
# 1. plex.search_library — happy path + auth exactness
# ---------------------------------------------------------------------------
print("scenario: search_library happy path / auth exactness")
out, ex = run_tool("plex", creds(tool="plex.search_library", query="blade runner"), [
    resp(200, body={"MediaContainer": {"size": 2, "Metadata": [
        {"ratingKey": "101", "title": "Blade Runner", "type": "movie", "year": 1982,
         "librarySectionTitle": "Movies", "summary": "raw-should-not-leak",
         "Media": [{"deep": "raw"}], "guid": "plex://movie/xyz"},
        {"ratingKey": "102", "title": "Blade Runner 2049", "type": "movie", "year": 2017,
         "librarySectionTitle": "Movies"},
    ]}}),
])
ok &= check("one request made", len(ex) == 1, repr(ex))
ok &= check("method GET", ex[0].method == "GET", ex[0].method)
ok &= check("URL byte-exact", ex[0].url == f"{BASE}/search?query=blade+runner&limit=25", ex[0].url)
ok &= check("X-Plex-Token header exact (not query param, not Bearer)",
            ex[0].headers.get("x-plex-token") == TOK and "authorization" not in ex[0].headers
            and "x-plex-token" not in ex[0].url.lower(), str(ex[0].headers))
ok &= check("Accept: application/json", ex[0].headers.get("accept") == "application/json",
            str(ex[0].headers))
ok &= check("X-Plex-Client-Identifier fixed",
            ex[0].headers.get("x-plex-client-identifier") == "sophon-plex-skill",
            str(ex[0].headers))
ok &= check("no request body", ex[0].body is None, str(ex[0].body))
ok &= check("count == 2", out.get("count") == 2, str(out)[:200])
ok &= check("results shaped",
            out["results"][0] == {"ratingKey": "101", "title": "Blade Runner", "type": "movie",
                                  "year": 1982, "librarySectionTitle": "Movies"},
            str(out["results"][0]))
ok &= check("raw fields absent (summary/Media/guid)",
            "summary" not in out["results"][0] and "Media" not in out["results"][0]
            and "guid" not in out["results"][0], str(out["results"][0]))
ok &= check("token not echoed in output", TOK not in json.dumps(out))

# section-scoped search
print("scenario: search_library scoped to a section")
out, ex = run_tool("plex", creds(tool="plex.search_library", query="dogs", sectionId="3",
                                 limit=5), [
    resp(200, body={"MediaContainer": {"Metadata": []}}),
])
ok &= check("section search URL byte-exact",
            ex[0].url == f"{BASE}/library/sections/3/search?query=dogs&limit=5", ex[0].url)
ok &= check("empty result count 0", out == {"count": 0, "results": []}, str(out))

# ---------------------------------------------------------------------------
# 2. plex.list_libraries — happy path
# ---------------------------------------------------------------------------
print("scenario: list_libraries happy path")
out, ex = run_tool("plex", creds(tool="plex.list_libraries"), [
    resp(200, body={"MediaContainer": {"Directory": [
        {"key": "1", "title": "Movies", "type": "movie", "agent": "tv.plex.agents.movie",
         "scanner": "Plex Movie", "uuid": "raw-uuid", "Location": [{"path": "/data/movies"}]},
        {"key": "2", "title": "TV Shows", "type": "show", "agent": "tv.plex.agents.series"},
    ]}}),
])
ok &= check("URL byte-exact", ex[0].url == f"{BASE}/library/sections", ex[0].url)
ok &= check("X-Plex-Token header", ex[0].headers.get("x-plex-token") == TOK)
ok &= check("count == 2", out.get("count") == 2, str(out)[:200])
ok &= check("library shaped",
            out["libraries"][0] == {"key": "1", "title": "Movies", "type": "movie",
                                    "agent": "tv.plex.agents.movie"},
            str(out["libraries"][0]))
ok &= check("raw scanner/uuid/Location absent",
            all(k not in out["libraries"][0] for k in ("scanner", "uuid", "Location")),
            str(out["libraries"][0]))

# ---------------------------------------------------------------------------
# 3. plex.get_item_details — happy path
# ---------------------------------------------------------------------------
print("scenario: get_item_details happy path")
out, ex = run_tool("plex", creds(tool="plex.get_item_details", ratingKey="101"), [
    resp(200, body={"MediaContainer": {"Metadata": [
        {"ratingKey": "101", "title": "Blade Runner", "type": "movie", "year": 1982,
         "summary": "A blade runner must pursue replicants.", "duration": 7017000,
         "rating": 8.9, "contentRating": "R", "librarySectionTitle": "Movies",
         "guid": "plex://movie/xyz",
         "Media": [{"id": 55, "videoResolution": "1080", "videoCodec": "hevc",
                    "audioCodec": "eac3", "audioChannels": 6, "container": "mkv",
                    "bitrate": 8000,
                    "Part": [{"file": "/data/movies/BladeRunner.mkv", "size": 1}]}]}
    ]}}),
])
ok &= check("URL byte-exact", ex[0].url == f"{BASE}/library/metadata/101", ex[0].url)
ok &= check("summary/rating/duration surfaced",
            out.get("summary") == "A blade runner must pursue replicants."
            and out.get("rating") == 8.9 and out.get("duration") == 7017000
            and out.get("year") == 1982, str(out)[:300])
ok &= check("media streams trimmed",
            out["media"] == [{"videoResolution": "1080", "videoCodec": "hevc",
                              "audioCodec": "eac3", "audioChannels": 6,
                              "container": "mkv", "bitrate": 8000}],
            str(out.get("media")))
ok &= check("raw Part/file paths/guid absent",
            "Part" not in json.dumps(out) and "/data/movies" not in json.dumps(out)
            and "guid" not in out, str(out)[:300])

# ---------------------------------------------------------------------------
# 4. plex.get_recently_added — limit clamp via container headers
# ---------------------------------------------------------------------------
print("scenario: get_recently_added uses X-Plex-Container-Size/Start headers")
out, ex = run_tool("plex", creds(tool="plex.get_recently_added", limit=2), [
    resp(200, body={"MediaContainer": {"Metadata": [
        {"ratingKey": "201", "title": "New Movie", "type": "movie", "year": 2026,
         "librarySectionTitle": "Movies", "addedAt": 1789000000},
        {"ratingKey": "202", "title": "New Episode", "type": "episode",
         "librarySectionTitle": "TV Shows", "addedAt": 1788999000},
    ]}}),
])
ok &= check("URL byte-exact", ex[0].url == f"{BASE}/library/recentlyAdded", ex[0].url)
ok &= check("X-Plex-Container-Size == 2",
            ex[0].headers.get("x-plex-container-size") == "2", str(ex[0].headers))
ok &= check("X-Plex-Container-Start == 0",
            ex[0].headers.get("x-plex-container-start") == "0", str(ex[0].headers))
ok &= check("count == 2 with addedAt",
            out.get("count") == 2 and out["items"][0]["addedAt"] == 1789000000,
            str(out)[:300])

print("scenario: get_recently_added section-scoped, limit clamped to max 100")
out, ex = run_tool("plex", creds(tool="plex.get_recently_added", sectionId="1", limit=5000), [
    resp(200, body={"MediaContainer": {"Metadata": []}}),
])
ok &= check("section URL byte-exact",
            ex[0].url == f"{BASE}/library/sections/1/recentlyAdded", ex[0].url)
ok &= check("container size clamped to 100",
            ex[0].headers.get("x-plex-container-size") == "100", str(ex[0].headers))

# ---------------------------------------------------------------------------
# 5. plex.get_active_sessions — happy path
# ---------------------------------------------------------------------------
print("scenario: get_active_sessions happy path")
out, ex = run_tool("plex", creds(tool="plex.get_active_sessions"), [
    resp(200, body={"MediaContainer": {"size": 1, "Metadata": [
        {"title": "Ozymandias", "grandparentTitle": "Breaking Bad", "type": "episode",
         "duration": 2820000, "viewOffset": 1410000,
         "User": {"id": "1", "title": "enes", "thumb": "raw"},
         "Player": {"product": "Plex for Apple TV", "state": "playing",
                    "address": "192.168.1.7", "machineIdentifier": "raw-machine"},
         "Session": {"id": "raw-session", "bandwidth": 999}}
    ]}}),
])
ok &= check("URL byte-exact", ex[0].url == f"{BASE}/status/sessions", ex[0].url)
ok &= check("count == 1", out.get("count") == 1, str(out)[:200])
sess = out["sessions"][0]
ok &= check("session shaped (user/title/player/progress)",
            sess == {"user": "enes", "title": "Ozymandias",
                     "grandparentTitle": "Breaking Bad", "type": "episode",
                     "player": {"product": "Plex for Apple TV", "state": "playing"},
                     "progressPercent": 50.0},
            str(sess))
ok &= check("raw address/machineIdentifier/Session absent",
            "192.168.1.7" not in json.dumps(out) and "raw-machine" not in json.dumps(out)
            and "raw-session" not in json.dumps(out), str(out)[:300])

# ---------------------------------------------------------------------------
# 6. plex.get_on_deck — happy path
# ---------------------------------------------------------------------------
print("scenario: get_on_deck happy path")
out, ex = run_tool("plex", creds(tool="plex.get_on_deck"), [
    resp(200, body={"MediaContainer": {"Metadata": [
        {"ratingKey": "301", "title": "Felina", "grandparentTitle": "Breaking Bad",
         "type": "episode", "year": 2013, "librarySectionTitle": "TV Shows",
         "viewOffset": 60000}
    ]}}),
])
ok &= check("URL byte-exact", ex[0].url == f"{BASE}/library/onDeck", ex[0].url)
ok &= check("on-deck item shaped",
            out == {"count": 1, "items": [{"ratingKey": "301", "title": "Felina",
                                           "type": "episode", "year": 2013,
                                           "librarySectionTitle": "TV Shows",
                                           "grandparentTitle": "Breaking Bad",
                                           "viewOffset": 60000}]},
            str(out))

# ---------------------------------------------------------------------------
# 7. plex.scan_library_section — low-risk write path
# ---------------------------------------------------------------------------
print("scenario: scan_library_section triggers refresh")
out, ex = run_tool("plex", creds(tool="plex.scan_library_section", sectionId="2"), [
    resp(200, body=""),
])
ok &= check("method GET (Plex refresh is a GET)", ex[0].method == "GET", ex[0].method)
ok &= check("URL byte-exact", ex[0].url == f"{BASE}/library/sections/2/refresh", ex[0].url)
ok &= check("no request body", ex[0].body is None, str(ex[0].body))
ok &= check("X-Plex-Token on write", ex[0].headers.get("x-plex-token") == TOK)
ok &= check("output shape", out == {"scanning": True, "sectionKey": "2"}, str(out))

# ---------------------------------------------------------------------------
# 8. ERROR PATHS
# ---------------------------------------------------------------------------
print("scenario: 401 surfaces friendly error")
out, ex = run_tool("plex", creds(tool="plex.list_libraries"), [
    err(401, body="<html><body>401 Unauthorized</body></html>"),
])
raw = json.dumps(out)
ok &= check("error key present", "error" in out and isinstance(out["error"], str), raw[:200])
ok &= check("includes HTTP status 401", "401" in out["error"], out.get("error", ""))
ok &= check("no Python traceback leaked",
            "Traceback" not in raw and "urllib" not in raw and "HTTPError" not in raw, raw[:300])
ok &= check("token not leaked in error output", TOK not in raw, raw[:300])

print("scenario: 429 includes Retry-After and slow-down hint")
out, ex = run_tool("plex", creds(tool="plex.get_active_sessions"), [
    err(429, body="", headers={"Retry-After": "30"}),
])
ok &= check("429 error surfaced", "error" in out and "429" in out["error"], str(out)[:300])
ok &= check("Retry-After included", "30" in out["error"], out.get("error", ""))
ok &= check("rate-limit hint included", "rate limited" in out["error"].lower(),
            out.get("error", ""))

print("scenario: unreachable server hints at sandbox reachability")
# The mock transport cannot raise URLError mid-flight, so assert the URLError handler's
# message text directly from the source (jenkins-style private-network framing).
from mockhttp import REPO
src = open(f"{REPO}/skills/plex/main.py", encoding="utf-8").read()
ok &= check("URLError message hints sandbox/VPN/tunnel/reverse proxy",
            "reachable from Sophon's sandbox" in src and "reverse proxy" in src)

print("scenario: missing required param -> friendly error, no HTTP call")
out, ex = run_tool("plex", creds(tool="plex.get_item_details"), [])
ok &= check("ratingKey required error", out.get("error") == "ratingKey required", str(out))
ok &= check("no HTTP request made", len(ex) == 0, repr(ex))

print("scenario: missing credentials -> friendly connect-first error, no HTTP call")
out, ex = run_tool("plex", {"tool": "plex.list_libraries", "base_url": "", "plex_token": ""}, [])
ok &= check("missing-credentials message",
            "error" in out and "connect the plex integration" in out["error"].lower()
            and "plex_token" in out["error"], str(out))
ok &= check("no HTTP request made", len(ex) == 0, repr(ex))

print("scenario: unknown tool -> friendly error")
out, ex = run_tool("plex", creds(tool="plex.nope"), [])
ok &= check("unknown tool error", out.get("error") == "Unknown tool: plex.nope", str(out))

# ---------------------------------------------------------------------------
# 9. SECURITY PROBES
# ---------------------------------------------------------------------------
print("scenario: path-traversal ratingKey is percent-encoded")
evil = "abc/../def?x=1"
out, ex = run_tool("plex", creds(tool="plex.get_item_details", ratingKey=evil), [
    resp(200, body={"MediaContainer": {"Metadata": [{"ratingKey": "x"}]}}),
])
ok &= check("ratingKey fully quoted in URL (no path escape)",
            ex[0].url == f"{BASE}/library/metadata/abc%2F..%2Fdef%3Fx%3D1", ex[0].url)
ok &= check("no raw '../' or '?' in path", "../" not in ex[0].url and "?" not in ex[0].url,
            ex[0].url)

print("scenario: bare '..' segment rejected before any HTTP")
out, ex = run_tool("plex", creds(tool="plex.scan_library_section", sectionId=".."), [])
ok &= check("'..' rejected", "error" in out and "'.'" in out["error"], str(out))
ok &= check("no HTTP request made", len(ex) == 0, repr(ex))
out, ex = run_tool("plex", creds(tool="plex.get_item_details", ratingKey="."), [])
ok &= check("'.' rejected on ratingKey", "error" in out and "must not" in out["error"], str(out))
ok &= check("no HTTP request made", len(ex) == 0, repr(ex))

print("scenario: path-traversal sectionId quoted on scan + search")
out, ex = run_tool("plex", creds(tool="plex.scan_library_section", sectionId="2/../1"), [
    resp(200, body=""),
])
ok &= check("scan sectionId quoted",
            ex[0].url == f"{BASE}/library/sections/2%2F..%2F1/refresh", ex[0].url)
out, ex = run_tool("plex", creds(tool="plex.search_library", query="x", sectionId="a b/c"), [
    resp(200, body={"MediaContainer": {"Metadata": []}}),
])
ok &= check("search sectionId quoted",
            ex[0].url == f"{BASE}/library/sections/a%20b%2Fc/search?query=x&limit=25",
            ex[0].url)

print("scenario: secret never appears in any output (error path)")
out, ex = run_tool("plex", creds(tool="plex.get_on_deck"), [
    err(403, body="forbidden"),
])
ok &= check("plex_token absent from error output", TOK not in json.dumps(out),
            json.dumps(out)[:300])

print()
print("RESULT:", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
