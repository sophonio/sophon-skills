"""Offline mock-HTTP integration tests for the sonarr skill."""
import json
import sys

from mockhttp import run_tool, resp, err, check

BASE = "http://192.168.1.10:8989"
KEY = "abc123-SONARR-SECRET"


def creds(**extra):
    p = {"base_url": BASE, "api_key": KEY}
    p.update(extra)
    return p


ok = True

# ---------------------------------------------------------------------------
# 1. sonarr.search_series_lookup — happy path + auth exactness
# ---------------------------------------------------------------------------
print("scenario: search_series_lookup happy path / auth exactness")
out, ex = run_tool("sonarr", creds(tool="sonarr.search_series_lookup", term="breaking bad"), [
    resp(200, body=[
        {"title": "Breaking Bad", "year": 2008, "tvdbId": 81189,
         "overview": "A chemistry teacher turns to cooking meth.",
         "seasons": [{"seasonNumber": 1}], "images": [{"coverType": "poster"}],
         "remotePoster": "http://x/y.jpg"},
        {"title": "Breaking Bad: The Movie", "year": 2019, "tvdbId": 99999,
         "overview": None},
    ]),
])
ok &= check("one request made", len(ex) == 1, repr(ex))
ok &= check("method GET", ex[0].method == "GET", ex[0].method)
ok &= check("URL byte-exact", ex[0].url == f"{BASE}/api/v3/series/lookup?term=breaking+bad",
            ex[0].url)
ok &= check("X-Api-Key header exact", ex[0].headers.get("x-api-key") == KEY,
            str(ex[0].headers))
ok &= check("no Authorization header", "authorization" not in ex[0].headers,
            str(ex[0].headers))
ok &= check("Accept header", ex[0].headers.get("accept") == "application/json",
            str(ex[0].headers))
ok &= check("User-Agent set", ex[0].headers.get("user-agent") == "sophon-sonarr-skill",
            str(ex[0].headers))
ok &= check("no request body", ex[0].body is None, str(ex[0].body))
ok &= check("count == 2", out.get("count") == 2, str(out)[:200])
ok &= check("lookup shaped (title/year/tvdbId/overview)",
            out["series"][0] == {"title": "Breaking Bad", "year": 2008, "tvdbId": 81189,
                                 "overview": "A chemistry teacher turns to cooking meth."},
            str(out["series"][0]))
ok &= check("raw fields absent (seasons/images/remotePoster)",
            "seasons" not in out["series"][0] and "images" not in out["series"][0]
            and "remotePoster" not in out["series"][0], str(out["series"][0]))
ok &= check("None overview becomes empty string", out["series"][1]["overview"] == "",
            str(out["series"][1]))
ok &= check("key not echoed in output", KEY not in json.dumps(out))

# ---------------------------------------------------------------------------
# 2. sonarr.list_series — happy path with statistics flattening
# ---------------------------------------------------------------------------
print("scenario: list_series happy path")
out, ex = run_tool("sonarr", creds(tool="sonarr.list_series"), [
    resp(200, body=[
        {"id": 5, "title": "Severance", "monitored": True, "status": "continuing",
         "tvdbId": 371980, "path": "/tv/Severance", "qualityProfileId": 6,
         "statistics": {"seasonCount": 2, "episodeCount": 19, "episodeFileCount": 18,
                        "sizeOnDisk": 123456789}},
        {"id": 7, "title": "The Wire", "monitored": False, "status": "ended",
         "tvdbId": 79126},
    ]),
])
ok &= check("URL byte-exact", ex[0].url == f"{BASE}/api/v3/series", ex[0].url)
ok &= check("X-Api-Key on read", ex[0].headers.get("x-api-key") == KEY)
ok &= check("count == 2", out.get("count") == 2, str(out)[:200])
ok &= check("series shaped with flattened statistics",
            out["series"][0] == {"id": 5, "title": "Severance", "monitored": True,
                                 "status": "continuing", "tvdbId": 371980,
                                 "episodeCount": 19, "episodeFileCount": 18},
            str(out["series"][0]))
ok &= check("missing statistics tolerated",
            out["series"][1]["episodeCount"] is None
            and out["series"][1]["episodeFileCount"] is None, str(out["series"][1]))
ok &= check("raw path/sizeOnDisk absent",
            "path" not in out["series"][0] and "sizeOnDisk" not in out["series"][0]
            and "statistics" not in out["series"][0], str(out["series"][0]))

# ---------------------------------------------------------------------------
# 3. sonarr.get_calendar — happy path with date window
# ---------------------------------------------------------------------------
print("scenario: get_calendar happy path")
out, ex = run_tool("sonarr", creds(tool="sonarr.get_calendar",
                                   start="2026-07-18", end="2026-07-25"), [
    resp(200, body=[
        {"seriesId": 5, "title": "Cold Harbor", "seasonNumber": 2, "episodeNumber": 10,
         "airDate": "2026-07-20", "airDateUtc": "2026-07-21T01:00:00Z", "monitored": True,
         "series": {"id": 5, "title": "Severance", "network": "Apple TV+"},
         "overview": "long spoiler text"},
    ]),
])
ok &= check("URL byte-exact (start, end, includeSeries)",
            ex[0].url == f"{BASE}/api/v3/calendar?start=2026-07-18&end=2026-07-25&includeSeries=true",
            ex[0].url)
ok &= check("count == 1", out.get("count") == 1, str(out)[:200])
ok &= check("calendar entry shaped",
            out["episodes"][0] == {"series": "Severance", "title": "Cold Harbor",
                                   "seasonNumber": 2, "episodeNumber": 10,
                                   "airDate": "2026-07-21T01:00:00Z", "monitored": True},
            str(out["episodes"][0]))

print("scenario: get_calendar without window omits empty params")
out, ex = run_tool("sonarr", creds(tool="sonarr.get_calendar"), [resp(200, body=[])])
ok &= check("URL has only includeSeries",
            ex[0].url == f"{BASE}/api/v3/calendar?includeSeries=true", ex[0].url)
ok &= check("empty result count 0", out == {"count": 0, "episodes": []}, str(out))

# ---------------------------------------------------------------------------
# 4. sonarr.get_missing — pagination params clamped
# ---------------------------------------------------------------------------
print("scenario: get_missing clamps pageSize and shapes records")
out, ex = run_tool("sonarr", creds(tool="sonarr.get_missing", page=2, pageSize=5000), [
    resp(200, body={"page": 2, "pageSize": 100, "totalRecords": 250, "records": [
        {"title": "Pilot", "seasonNumber": 1, "episodeNumber": 1,
         "airDate": "2020-01-01", "airDateUtc": "2020-01-02T01:00:00Z",
         "series": {"title": "The Wire"}, "episodeFileId": 0},
    ]}),
])
ok &= check("URL byte-exact with clamped pageSize=100",
            ex[0].url == f"{BASE}/api/v3/wanted/missing?page=2&pageSize=100&includeSeries=true",
            ex[0].url)
ok &= check("page/totalRecords surfaced", out.get("page") == 2 and out.get("totalRecords") == 250,
            str(out)[:200])
ok &= check("missing record shaped",
            out["episodes"][0] == {"series": "The Wire", "title": "Pilot", "seasonNumber": 1,
                                   "episodeNumber": 1, "airDate": "2020-01-02T01:00:00Z"},
            str(out["episodes"][0]))

# ---------------------------------------------------------------------------
# 5. sonarr.get_queue — progress computed from size/sizeleft
# ---------------------------------------------------------------------------
print("scenario: get_queue happy path with progress")
out, ex = run_tool("sonarr", creds(tool="sonarr.get_queue"), [
    resp(200, body={"page": 1, "records": [
        {"title": "Severance.S02E10.1080p", "status": "downloading",
         "timeleft": "00:12:34", "size": 4000, "sizeleft": 1000,
         "downloadId": "abc", "protocol": "torrent"},
        {"title": "The.Wire.S01E01", "status": "queued", "timeleft": None},
    ]}),
])
ok &= check("URL byte-exact", ex[0].url == f"{BASE}/api/v3/queue?pageSize=50", ex[0].url)
ok &= check("count == 2", out.get("count") == 2, str(out)[:200])
ok &= check("queue item shaped with computed progress",
            out["items"][0] == {"title": "Severance.S02E10.1080p", "status": "downloading",
                                "timeleft": "00:12:34", "progress": 75.0},
            str(out["items"][0]))
ok &= check("missing size -> progress None", out["items"][1]["progress"] is None,
            str(out["items"][1]))
ok &= check("raw downloadId absent", "downloadId" not in out["items"][0], str(out["items"][0]))

# ---------------------------------------------------------------------------
# 6. sonarr.list_quality_profiles / sonarr.list_root_folders
# ---------------------------------------------------------------------------
print("scenario: list_quality_profiles + list_root_folders")
out, ex = run_tool("sonarr", creds(tool="sonarr.list_quality_profiles"), [
    resp(200, body=[{"id": 6, "name": "HD-1080p", "upgradeAllowed": True,
                     "items": [{"deep": "stuff"}]}]),
])
ok &= check("qualityprofile URL", ex[0].url == f"{BASE}/api/v3/qualityprofile", ex[0].url)
ok &= check("profile shaped to id/name",
            out == {"count": 1, "profiles": [{"id": 6, "name": "HD-1080p"}]}, str(out))
out, ex = run_tool("sonarr", creds(tool="sonarr.list_root_folders"), [
    resp(200, body=[{"id": 1, "path": "/tv", "accessible": True, "freeSpace": 500,
                     "unmappedFolders": [{"name": "x"}]}]),
])
ok &= check("rootfolder URL", ex[0].url == f"{BASE}/api/v3/rootfolder", ex[0].url)
ok &= check("folder shaped",
            out == {"count": 1, "folders": [{"id": 1, "path": "/tv", "freeSpace": 500,
                                             "accessible": True}]}, str(out))

# ---------------------------------------------------------------------------
# 7. WRITE PATHS — add_series (POST) and set_season_monitored (GET + PUT)
# ---------------------------------------------------------------------------
print("scenario: add_series POST body exactness")
out, ex = run_tool("sonarr", creds(tool="sonarr.add_series", tvdbId=81189,
                                   title="Breaking Bad", qualityProfileId=6,
                                   rootFolderPath="/tv", monitored=True,
                                   searchForMissingEpisodes=True), [
    resp(201, body={"id": 12, "title": "Breaking Bad", "monitored": True,
                    "path": "/tv/Breaking Bad", "tvdbId": 81189}),
])
ok &= check("method POST", ex[0].method == "POST", ex[0].method)
ok &= check("URL byte-exact", ex[0].url == f"{BASE}/api/v3/series", ex[0].url)
ok &= check("Content-Type json", ex[0].headers.get("content-type") == "application/json",
            str(ex[0].headers))
ok &= check("X-Api-Key on write", ex[0].headers.get("x-api-key") == KEY)
ok &= check("body exact",
            ex[0].json == {"tvdbId": 81189, "title": "Breaking Bad", "qualityProfileId": 6,
                           "rootFolderPath": "/tv", "monitored": True,
                           "addOptions": {"searchForMissingEpisodes": True}},
            str(ex[0].body))
ok &= check("result shaped",
            out == {"id": 12, "title": "Breaking Bad", "monitored": True,
                    "path": "/tv/Breaking Bad", "added": True}, str(out))

print("scenario: add_series optional seasons/languageProfileId included")
out, ex = run_tool("sonarr", creds(tool="sonarr.add_series", tvdbId=1, title="X",
                                   qualityProfileId=2, rootFolderPath="/tv",
                                   languageProfileId=1,
                                   seasons=[{"seasonNumber": 1, "monitored": False}]), [
    resp(201, body={"id": 13, "title": "X", "monitored": True, "path": "/tv/X"}),
])
ok &= check("seasons + languageProfileId in body, monitored defaults true",
            ex[0].json["seasons"] == [{"seasonNumber": 1, "monitored": False}]
            and ex[0].json["languageProfileId"] == 1 and ex[0].json["monitored"] is True
            and ex[0].json["addOptions"] == {"searchForMissingEpisodes": False},
            str(ex[0].body))

print("scenario: add_series missing required field -> no HTTP")
out, ex = run_tool("sonarr", creds(tool="sonarr.add_series", title="X"), [])
ok &= check("tvdbId required error", out.get("error") == "tvdbId required", str(out))
ok &= check("no HTTP request made", len(ex) == 0, repr(ex))

print("scenario: set_season_monitored flips one season via GET + PUT")
out, ex = run_tool("sonarr", creds(tool="sonarr.set_season_monitored", seriesId=5,
                                   seasonNumber=2, monitored=False), [
    resp(200, body={"id": 5, "title": "Severance", "monitored": True,
                    "seasons": [{"seasonNumber": 1, "monitored": True},
                                {"seasonNumber": 2, "monitored": True}]}),
    resp(200, body={"id": 5, "title": "Severance", "monitored": True,
                    "seasons": [{"seasonNumber": 1, "monitored": True},
                                {"seasonNumber": 2, "monitored": False}]}),
])
ok &= check("two requests (GET then PUT)",
            len(ex) == 2 and ex[0].method == "GET" and ex[1].method == "PUT",
            repr(ex))
ok &= check("GET URL byte-exact", ex[0].url == f"{BASE}/api/v3/series/5", ex[0].url)
ok &= check("PUT URL byte-exact", ex[1].url == f"{BASE}/api/v3/series/5", ex[1].url)
ok &= check("PUT body: target season flipped, sibling untouched, series flag untouched",
            ex[1].json["seasons"] == [{"seasonNumber": 1, "monitored": True},
                                      {"seasonNumber": 2, "monitored": False}]
            and ex[1].json["monitored"] is True, str(ex[1].body))
ok &= check("result shaped", out == {"id": 5, "title": "Severance", "scope": "season 2",
                                     "monitored": False, "updated": True}, str(out))

print("scenario: set_season_monitored without seasonNumber flips whole series")
out, ex = run_tool("sonarr", creds(tool="sonarr.set_season_monitored", seriesId=5,
                                   monitored=True), [
    resp(200, body={"id": 5, "title": "Severance", "monitored": False,
                    "seasons": [{"seasonNumber": 1, "monitored": False}]}),
    resp(200, body={"id": 5, "title": "Severance", "monitored": True,
                    "seasons": [{"seasonNumber": 1, "monitored": False}]}),
])
ok &= check("series-level monitored flipped in PUT, seasons untouched",
            ex[1].json["monitored"] is True
            and ex[1].json["seasons"] == [{"seasonNumber": 1, "monitored": False}],
            str(ex[1].body))
ok &= check("scope is series", out.get("scope") == "series" and out.get("monitored") is True,
            str(out))

print("scenario: set_season_monitored unknown season -> friendly error, no PUT")
out, ex = run_tool("sonarr", creds(tool="sonarr.set_season_monitored", seriesId=5,
                                   seasonNumber=9, monitored=False), [
    resp(200, body={"id": 5, "title": "Severance",
                    "seasons": [{"seasonNumber": 1, "monitored": True}]}),
])
ok &= check("season-not-found error", out.get("error") == "season 9 not found on series 5",
            str(out))
ok &= check("only the GET was made", len(ex) == 1 and ex[0].method == "GET", repr(ex))

print("scenario: set_season_monitored missing monitored -> no HTTP")
out, ex = run_tool("sonarr", creds(tool="sonarr.set_season_monitored", seriesId=5), [])
ok &= check("monitored required error", out.get("error") == "monitored required (true or false)",
            str(out))
ok &= check("no HTTP request made", len(ex) == 0, repr(ex))

# ---------------------------------------------------------------------------
# 8. ERROR PATHS
# ---------------------------------------------------------------------------
print("scenario: 401 surfaces friendly error")
out, ex = run_tool("sonarr", creds(tool="sonarr.list_series"), [
    err(401, body=""),
])
raw = json.dumps(out)
ok &= check("error key present", "error" in out and isinstance(out["error"], str), raw[:200])
ok &= check("includes HTTP status 401", "401" in out["error"], out.get("error", ""))
ok &= check("hints at API key location", "Settings > General > Security" in out["error"],
            out.get("error", ""))
ok &= check("no Python traceback leaked",
            "Traceback" not in raw and "urllib" not in raw and "HTTPError" not in raw, raw[:300])
ok &= check("key not leaked in error output", KEY not in raw, raw[:300])

print("scenario: validation error list body parsed")
out, ex = run_tool("sonarr", creds(tool="sonarr.add_series", tvdbId=1, title="X",
                                   qualityProfileId=2, rootFolderPath="/tv"), [
    err(400, body=[{"propertyName": "RootFolderPath",
                    "errorMessage": "Root folder path '/tv' does not exist"}]),
])
ok &= check("400 with Sonarr errorMessage",
            "400" in out["error"] and "Root folder path '/tv' does not exist" in out["error"],
            out.get("error", ""))

print("scenario: 429 includes Retry-After and slow-down hint")
out, ex = run_tool("sonarr", creds(tool="sonarr.get_queue"), [
    err(429, body="", headers={"Retry-After": "13"}),
])
ok &= check("429 error surfaced", "error" in out and "429" in out["error"], str(out)[:300])
ok &= check("rate-limit hint present", "rate limited, slow down" in out["error"],
            out.get("error", ""))
ok &= check("Retry-After included", "retry after 13s" in out["error"], out.get("error", ""))

print("scenario: non-JSON (HTML) error body tolerated")
out, ex = run_tool("sonarr", creds(tool="sonarr.list_series"), [
    err(502, body="<html>bad gateway</html>"),
])
ok &= check("502 non-JSON body still friendly",
            "error" in out and "502" in out["error"] and "Traceback" not in json.dumps(out),
            str(out)[:300])

print("scenario: missing credentials -> friendly connect-first error, no HTTP call")
out, ex = run_tool("sonarr", {"tool": "sonarr.list_series", "base_url": "", "api_key": ""}, [])
ok &= check("connect-first message names fields",
            out.get("error") == "Missing Sonarr credentials: connect the Sonarr integration "
                                "first (base_url, api_key).", str(out))
ok &= check("no HTTP request made", len(ex) == 0, repr(ex))

print("scenario: unknown tool -> friendly error")
out, ex = run_tool("sonarr", creds(tool="sonarr.nope"), [])
ok &= check("unknown tool error", out.get("error") == "Unknown tool: sonarr.nope", str(out))

print("scenario: missing term -> friendly error, no HTTP call")
out, ex = run_tool("sonarr", creds(tool="sonarr.search_series_lookup"), [])
ok &= check("term required error", out.get("error") == "term required", str(out))
ok &= check("no HTTP request made", len(ex) == 0, repr(ex))

# ---------------------------------------------------------------------------
# 9. SECURITY PROBES
# ---------------------------------------------------------------------------
print("scenario: path-traversal seriesId is percent-encoded")
out, ex = run_tool("sonarr", creds(tool="sonarr.set_season_monitored",
                                   seriesId="5/../6?x=1", monitored=True), [
    resp(200, body={"id": 5, "title": "S", "monitored": False, "seasons": []}),
    resp(200, body={"id": 5, "title": "S", "monitored": True, "seasons": []}),
])
ok &= check("id fully quoted in GET URL (no path escape)",
            ex[0].url == f"{BASE}/api/v3/series/5%2F..%2F6%3Fx%3D1", ex[0].url)
ok &= check("no raw '../' or '?' in path", "../" not in ex[0].url and "?" not in ex[0].url,
            ex[0].url)
ok &= check("PUT uses the same quoted id", ex[1].url == f"{BASE}/api/v3/series/5%2F..%2F6%3Fx%3D1",
            ex[1].url)

print("scenario: bare '..' seriesId rejected before any HTTP")
out, ex = run_tool("sonarr", creds(tool="sonarr.set_season_monitored", seriesId="..",
                                   monitored=True), [])
ok &= check("dot-dot rejected", out.get("error") == "seriesId must not be '.' or '..'", str(out))
ok &= check("no HTTP request made", len(ex) == 0, repr(ex))

print("scenario: secret never appears in any output (error path)")
out, ex = run_tool("sonarr", creds(tool="sonarr.list_root_folders"), [
    err(403, body={"message": "forbidden"}),
])
ok &= check("api_key absent from error output", KEY not in json.dumps(out),
            json.dumps(out)[:300])

print()
print("RESULT:", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
