"""Offline mock-HTTP integration tests for the radarr skill."""
import json
import sys

from mockhttp import run_tool, resp, err, check

BASE = "http://192.168.1.50:7878"
KEY = "abc123-RADARR-SECRET"


def creds(**extra):
    p = {"base_url": BASE, "api_key": KEY}
    p.update(extra)
    return p


ok = True

# ---------------------------------------------------------------------------
# 1. radarr.search_movie_lookup — happy path + auth exactness
# ---------------------------------------------------------------------------
print("scenario: search_movie_lookup happy path / auth exactness")
out, ex = run_tool("radarr", creds(tool="radarr.search_movie_lookup", term="dune part two"), [
    resp(200, body=[
        {"title": "Dune: Part Two", "year": 2024, "tmdbId": 693134,
         "overview": "Paul Atreides unites with the Fremen.",
         "images": [{"coverType": "poster"}], "remotePoster": "http://x/y.jpg"},
        {"title": "Dune", "year": 2021, "tmdbId": 438631, "overview": None},
    ]),
])
ok &= check("one request made", len(ex) == 1, repr(ex))
ok &= check("method GET", ex[0].method == "GET", ex[0].method)
ok &= check("URL byte-exact", ex[0].url == f"{BASE}/api/v3/movie/lookup?term=dune+part+two",
            ex[0].url)
ok &= check("X-Api-Key header exact", ex[0].headers.get("x-api-key") == KEY, str(ex[0].headers))
ok &= check("no Authorization header", "authorization" not in ex[0].headers, str(ex[0].headers))
ok &= check("Accept header", ex[0].headers.get("accept") == "application/json", str(ex[0].headers))
ok &= check("User-Agent set", ex[0].headers.get("user-agent") == "sophon-radarr-skill",
            str(ex[0].headers))
ok &= check("no request body", ex[0].body is None, str(ex[0].body))
ok &= check("count == 2", out.get("count") == 2, str(out)[:200])
ok &= check("lookup shaped (title/year/tmdbId/overview)",
            out["movies"][0] == {"title": "Dune: Part Two", "year": 2024, "tmdbId": 693134,
                                 "overview": "Paul Atreides unites with the Fremen."},
            str(out["movies"][0]))
ok &= check("raw fields absent (images/remotePoster)",
            "images" not in out["movies"][0] and "remotePoster" not in out["movies"][0],
            str(out["movies"][0]))
ok &= check("None overview becomes empty string", out["movies"][1]["overview"] == "",
            str(out["movies"][1]))
ok &= check("key not echoed in output", KEY not in json.dumps(out))

# ---------------------------------------------------------------------------
# 2. radarr.list_movies — happy path with shaping
# ---------------------------------------------------------------------------
print("scenario: list_movies happy path")
out, ex = run_tool("radarr", creds(tool="radarr.list_movies"), [
    resp(200, body=[
        {"id": 5, "title": "Sicario", "year": 2015, "monitored": True, "hasFile": True,
         "tmdbId": 273481, "path": "/movies/Sicario", "sizeOnDisk": 123456789},
        {"id": 7, "title": "Arrival", "year": 2016, "monitored": False, "hasFile": False,
         "tmdbId": 329865},
    ]),
])
ok &= check("URL byte-exact", ex[0].url == f"{BASE}/api/v3/movie", ex[0].url)
ok &= check("count == 2", out.get("count") == 2, str(out)[:200])
ok &= check("movie shaped",
            out["movies"][0] == {"id": 5, "title": "Sicario", "year": 2015, "monitored": True,
                                 "hasFile": True, "tmdbId": 273481}, str(out["movies"][0]))
ok &= check("raw path/sizeOnDisk absent",
            "path" not in out["movies"][0] and "sizeOnDisk" not in out["movies"][0],
            str(out["movies"][0]))

# ---------------------------------------------------------------------------
# 3. radarr.get_calendar — happy path with date window
# ---------------------------------------------------------------------------
print("scenario: get_calendar happy path")
out, ex = run_tool("radarr", creds(tool="radarr.get_calendar",
                                   start="2026-07-18", end="2026-08-18"), [
    resp(200, body=[
        {"title": "Some Film", "year": 2026, "inCinemas": "2026-07-20T00:00:00Z",
         "digitalRelease": "2026-08-01T00:00:00Z", "physicalRelease": None,
         "monitored": True, "overview": "spoilers"},
    ]),
])
ok &= check("URL byte-exact (start, end)",
            ex[0].url == f"{BASE}/api/v3/calendar?start=2026-07-18&end=2026-08-18", ex[0].url)
ok &= check("count == 1", out.get("count") == 1, str(out)[:200])
ok &= check("calendar entry shaped",
            out["movies"][0] == {"title": "Some Film", "year": 2026,
                                 "inCinemas": "2026-07-20T00:00:00Z",
                                 "digitalRelease": "2026-08-01T00:00:00Z",
                                 "physicalRelease": None, "monitored": True},
            str(out["movies"][0]))

print("scenario: get_calendar without window omits empty params")
out, ex = run_tool("radarr", creds(tool="radarr.get_calendar"), [resp(200, body=[])])
ok &= check("URL has no query", ex[0].url == f"{BASE}/api/v3/calendar", ex[0].url)
ok &= check("empty result count 0", out == {"count": 0, "movies": []}, str(out))

# ---------------------------------------------------------------------------
# 4. radarr.get_queue — progress computed from size/sizeleft
# ---------------------------------------------------------------------------
print("scenario: get_queue happy path with progress")
out, ex = run_tool("radarr", creds(tool="radarr.get_queue"), [
    resp(200, body={"page": 1, "records": [
        {"title": "Dune.2021.1080p", "status": "downloading", "timeleft": "00:12:34",
         "size": 4000, "sizeleft": 1000, "downloadId": "abc"},
        {"title": "Arrival.2016", "status": "queued", "timeleft": None},
    ]}),
])
ok &= check("URL byte-exact", ex[0].url == f"{BASE}/api/v3/queue?pageSize=50", ex[0].url)
ok &= check("count == 2", out.get("count") == 2, str(out)[:200])
ok &= check("queue item shaped with computed progress",
            out["items"][0] == {"title": "Dune.2021.1080p", "status": "downloading",
                                "timeleft": "00:12:34", "progress": 75.0}, str(out["items"][0]))
ok &= check("missing size -> progress None", out["items"][1]["progress"] is None,
            str(out["items"][1]))
ok &= check("raw downloadId absent", "downloadId" not in out["items"][0], str(out["items"][0]))

# ---------------------------------------------------------------------------
# 5. radarr.get_history — pagination clamp + shaping
# ---------------------------------------------------------------------------
print("scenario: get_history clamps pageSize and shapes records")
out, ex = run_tool("radarr", creds(tool="radarr.get_history", page=2, pageSize=5000), [
    resp(200, body={"page": 2, "pageSize": 100, "totalRecords": 250, "records": [
        {"eventType": "grabbed", "sourceTitle": "Dune.2021.1080p", "date": "2026-07-01T00:00:00Z",
         "movieId": 5, "data": {"noise": True}},
    ]}),
])
ok &= check("URL byte-exact with clamped pageSize=100",
            ex[0].url == f"{BASE}/api/v3/history?page=2&pageSize=100", ex[0].url)
ok &= check("page/totalRecords surfaced", out.get("page") == 2 and out.get("totalRecords") == 250,
            str(out)[:200])
ok &= check("history record shaped",
            out["events"][0] == {"eventType": "grabbed", "sourceTitle": "Dune.2021.1080p",
                                 "date": "2026-07-01T00:00:00Z", "movieId": 5},
            str(out["events"][0]))
ok &= check("raw data field absent", "data" not in out["events"][0], str(out["events"][0]))

# ---------------------------------------------------------------------------
# 6. radarr.list_quality_profiles / radarr.list_root_folders
# ---------------------------------------------------------------------------
print("scenario: list_quality_profiles + list_root_folders")
out, ex = run_tool("radarr", creds(tool="radarr.list_quality_profiles"), [
    resp(200, body=[{"id": 4, "name": "HD-1080p", "items": [{"deep": "stuff"}]}]),
])
ok &= check("qualityprofile URL", ex[0].url == f"{BASE}/api/v3/qualityprofile", ex[0].url)
ok &= check("profile shaped to id/name",
            out == {"count": 1, "profiles": [{"id": 4, "name": "HD-1080p"}]}, str(out))
out, ex = run_tool("radarr", creds(tool="radarr.list_root_folders"), [
    resp(200, body=[{"id": 1, "path": "/movies", "accessible": True, "freeSpace": 500,
                     "unmappedFolders": [{"name": "x"}]}]),
])
ok &= check("rootfolder URL", ex[0].url == f"{BASE}/api/v3/rootfolder", ex[0].url)
ok &= check("folder shaped",
            out == {"count": 1, "folders": [{"id": 1, "path": "/movies", "freeSpace": 500,
                                             "accessible": True}]}, str(out))

# ---------------------------------------------------------------------------
# 7. WRITE PATHS — add_movie (POST) and set_monitored (GET + PUT)
# ---------------------------------------------------------------------------
print("scenario: add_movie POST body exactness")
out, ex = run_tool("radarr", creds(tool="radarr.add_movie", tmdbId=693134,
                                   title="Dune: Part Two", qualityProfileId=4,
                                   rootFolderPath="/movies", monitored=True,
                                   searchForMovie=True), [
    resp(201, body={"id": 12, "title": "Dune: Part Two", "monitored": True,
                    "path": "/movies/Dune Part Two", "tmdbId": 693134}),
])
ok &= check("method POST", ex[0].method == "POST", ex[0].method)
ok &= check("URL byte-exact", ex[0].url == f"{BASE}/api/v3/movie", ex[0].url)
ok &= check("Content-Type json", ex[0].headers.get("content-type") == "application/json",
            str(ex[0].headers))
ok &= check("X-Api-Key on write", ex[0].headers.get("x-api-key") == KEY)
ok &= check("body exact (with minimumAvailability default)",
            ex[0].json == {"tmdbId": 693134, "title": "Dune: Part Two", "qualityProfileId": 4,
                           "rootFolderPath": "/movies", "monitored": True,
                           "minimumAvailability": "released",
                           "addOptions": {"searchForMovie": True}}, str(ex[0].body))
ok &= check("result shaped",
            out == {"id": 12, "title": "Dune: Part Two", "monitored": True,
                    "path": "/movies/Dune Part Two", "added": True}, str(out))

print("scenario: add_movie missing required field -> no HTTP")
out, ex = run_tool("radarr", creds(tool="radarr.add_movie", title="X"), [])
ok &= check("tmdbId required error", out.get("error") == "tmdbId required", str(out))
ok &= check("no HTTP request made", len(ex) == 0, repr(ex))

print("scenario: set_monitored flips monitoring via GET + PUT")
out, ex = run_tool("radarr", creds(tool="radarr.set_monitored", movieId=5, monitored=False), [
    resp(200, body={"id": 5, "title": "Sicario", "monitored": True, "path": "/movies/Sicario"}),
    resp(200, body={"id": 5, "title": "Sicario", "monitored": False, "path": "/movies/Sicario"}),
])
ok &= check("two requests (GET then PUT)",
            len(ex) == 2 and ex[0].method == "GET" and ex[1].method == "PUT", repr(ex))
ok &= check("GET URL byte-exact", ex[0].url == f"{BASE}/api/v3/movie/5", ex[0].url)
ok &= check("PUT URL byte-exact", ex[1].url == f"{BASE}/api/v3/movie/5", ex[1].url)
ok &= check("PUT body has monitored flipped, full object preserved",
            ex[1].json["monitored"] is False and ex[1].json["title"] == "Sicario"
            and ex[1].json["path"] == "/movies/Sicario", str(ex[1].body))
ok &= check("result shaped",
            out == {"id": 5, "title": "Sicario", "monitored": False, "updated": True}, str(out))

print("scenario: set_monitored missing monitored -> no HTTP")
out, ex = run_tool("radarr", creds(tool="radarr.set_monitored", movieId=5), [])
ok &= check("monitored required error", out.get("error") == "monitored required (true or false)",
            str(out))
ok &= check("no HTTP request made", len(ex) == 0, repr(ex))

# ---------------------------------------------------------------------------
# 8. ERROR PATHS
# ---------------------------------------------------------------------------
print("scenario: 401 surfaces friendly error")
out, ex = run_tool("radarr", creds(tool="radarr.list_movies"), [err(401, body="")])
raw = json.dumps(out)
ok &= check("error key present", "error" in out and isinstance(out["error"], str), raw[:200])
ok &= check("includes HTTP status 401", "401" in out["error"], out.get("error", ""))
ok &= check("hints at API key location", "Settings > General > Security" in out["error"],
            out.get("error", ""))
ok &= check("no Python traceback leaked",
            "Traceback" not in raw and "urllib" not in raw and "HTTPError" not in raw, raw[:300])
ok &= check("key not leaked in error output", KEY not in raw, raw[:300])

print("scenario: validation error list body parsed")
out, ex = run_tool("radarr", creds(tool="radarr.add_movie", tmdbId=1, title="X",
                                   qualityProfileId=2, rootFolderPath="/movies"), [
    err(400, body=[{"propertyName": "RootFolderPath",
                    "errorMessage": "Root folder path '/movies' does not exist"}]),
])
ok &= check("400 with Radarr errorMessage",
            "400" in out["error"] and "Root folder path '/movies' does not exist" in out["error"],
            out.get("error", ""))

print("scenario: 429 includes Retry-After and slow-down hint")
out, ex = run_tool("radarr", creds(tool="radarr.get_queue"), [
    err(429, body="", headers={"Retry-After": "13"}),
])
ok &= check("429 error surfaced", "error" in out and "429" in out["error"], str(out)[:300])
ok &= check("rate-limit hint present", "rate limited, slow down" in out["error"],
            out.get("error", ""))
ok &= check("Retry-After included", "retry after 13s" in out["error"], out.get("error", ""))

print("scenario: non-JSON (HTML) error body tolerated")
out, ex = run_tool("radarr", creds(tool="radarr.list_movies"), [
    err(502, body="<html>bad gateway</html>"),
])
ok &= check("502 non-JSON body still friendly",
            "error" in out and "502" in out["error"] and "Traceback" not in json.dumps(out),
            str(out)[:300])

print("scenario: missing credentials -> friendly connect-first error, no HTTP call")
out, ex = run_tool("radarr", {"tool": "radarr.list_movies", "base_url": "", "api_key": ""}, [])
ok &= check("connect-first message names fields",
            out.get("error") == "Missing Radarr credentials: connect the Radarr integration "
                                "first (base_url, api_key).", str(out))
ok &= check("no HTTP request made", len(ex) == 0, repr(ex))

print("scenario: unknown tool -> friendly error")
out, ex = run_tool("radarr", creds(tool="radarr.nope"), [])
ok &= check("unknown tool error", out.get("error") == "Unknown tool: radarr.nope", str(out))

print("scenario: missing term -> friendly error, no HTTP call")
out, ex = run_tool("radarr", creds(tool="radarr.search_movie_lookup"), [])
ok &= check("term required error", out.get("error") == "term required", str(out))
ok &= check("no HTTP request made", len(ex) == 0, repr(ex))

# ---------------------------------------------------------------------------
# 9. SECURITY PROBES
# ---------------------------------------------------------------------------
print("scenario: path-traversal movieId is percent-encoded")
out, ex = run_tool("radarr", creds(tool="radarr.set_monitored",
                                   movieId="5/../6?x=1", monitored=True), [
    resp(200, body={"id": 5, "title": "S", "monitored": False}),
    resp(200, body={"id": 5, "title": "S", "monitored": True}),
])
ok &= check("id fully quoted in GET URL (no path escape)",
            ex[0].url == f"{BASE}/api/v3/movie/5%2F..%2F6%3Fx%3D1", ex[0].url)
ok &= check("no raw '../' or '?' in path", "../" not in ex[0].url and "?" not in ex[0].url,
            ex[0].url)
ok &= check("PUT uses the same quoted id", ex[1].url == f"{BASE}/api/v3/movie/5%2F..%2F6%3Fx%3D1",
            ex[1].url)

print("scenario: bare '..' movieId rejected before any HTTP")
out, ex = run_tool("radarr", creds(tool="radarr.set_monitored", movieId="..", monitored=True), [])
ok &= check("dot-dot rejected", out.get("error") == "movieId must not be '.' or '..'", str(out))
ok &= check("no HTTP request made", len(ex) == 0, repr(ex))

print("scenario: secret never appears in any output (error path)")
out, ex = run_tool("radarr", creds(tool="radarr.list_root_folders"), [
    err(403, body={"message": "forbidden"}),
])
ok &= check("api_key absent from error output", KEY not in json.dumps(out), json.dumps(out)[:300])

print()
print("RESULT:", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
