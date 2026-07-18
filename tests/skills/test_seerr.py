"""Offline mock-HTTP integration tests for the seerr (Overseerr/Jellyseerr) skill."""
import json
import sys

from mockhttp import run_tool, resp, err, check

BASE = "http://192.168.1.50:5055"
KEY = "seerr-KEY-abc123-SECRET"


def creds(**extra):
    p = {"base_url": BASE, "api_key": KEY}
    p.update(extra)
    return p


ok = True

# ---------------------------------------------------------------------------
# 1. seerr.search_media — happy path + auth exactness
# ---------------------------------------------------------------------------
print("scenario: search_media happy path / auth exactness")
out, ex = run_tool("seerr", creds(tool="seerr.search_media", query="dune part two"), [
    resp(200, body={"page": 1, "totalPages": 1, "totalResults": 3, "results": [
        {"id": 693134, "mediaType": "movie", "title": "Dune: Part Two",
         "releaseDate": "2024-02-27", "overview": "Paul Atreides unites with Chani.",
         "posterPath": "/x.jpg", "voteAverage": 8.2,
         "mediaInfo": {"id": 5, "tmdbId": 693134, "status": 5,
                       "serviceUrl": "http://radarr.local"}},
        {"id": 90228, "mediaType": "tv", "name": "Dune: Prophecy",
         "firstAirDate": "2024-11-17", "overview": "Sisterhood origins."},
        {"id": 999, "mediaType": "person", "name": "Timothee Chalamet"},
    ]}),
])
ok &= check("one request made", len(ex) == 1, repr(ex))
ok &= check("method GET", ex[0].method == "GET", ex[0].method)
ok &= check("URL byte-exact",
            ex[0].url == f"{BASE}/api/v1/search?query=dune+part+two&page=1", ex[0].url)
ok &= check("X-Api-Key header exact (no Bearer/Authorization)",
            ex[0].headers.get("x-api-key") == KEY
            and "authorization" not in ex[0].headers, str(ex[0].headers))
ok &= check("Accept header", ex[0].headers.get("accept") == "application/json",
            str(ex[0].headers))
ok &= check("User-Agent set", ex[0].headers.get("user-agent") == "sophon-seerr-skill",
            str(ex[0].headers))
ok &= check("no request body", ex[0].body is None, str(ex[0].body))
ok &= check("person result filtered, count == 2", out.get("count") == 2, str(out)[:300])
r0, r1 = out["results"][0], out["results"][1]
ok &= check("movie shaped (title/releaseDate/status available)",
            r0["title"] == "Dune: Part Two" and r0["releaseDate"] == "2024-02-27"
            and r0["status"] == "available", str(r0))
ok &= check("tv name/firstAirDate mapped, no mediaInfo -> not_requested",
            r1["title"] == "Dune: Prophecy" and r1["releaseDate"] == "2024-11-17"
            and r1["status"] == "not_requested", str(r1))
ok &= check("raw fields absent (posterPath/mediaInfo/serviceUrl)",
            "posterPath" not in r0 and "mediaInfo" not in r0
            and "serviceUrl" not in json.dumps(out), str(r0))
ok &= check("api key not echoed in output", KEY not in json.dumps(out))

# ---------------------------------------------------------------------------
# 2. seerr.get_media_status — happy path (movie and tv paths)
# ---------------------------------------------------------------------------
print("scenario: get_media_status movie happy path")
out, ex = run_tool("seerr", creds(tool="seerr.get_media_status",
                                  mediaType="movie", tmdbId=603), [
    resp(200, body={"id": 603, "title": "The Matrix", "releaseDate": "1999-03-30",
                    "mediaInfo": {"id": 9, "tmdbId": 603, "status": 4, "status4k": 1,
                                  "requests": [
                                      {"id": 12, "status": 2, "is4k": False,
                                       "requestedBy": {"id": 1, "displayName": "enes",
                                                       "email": "should-not@leak.io"}}]}}),
])
ok &= check("URL byte-exact", ex[0].url == f"{BASE}/api/v1/movie/603", ex[0].url)
ok &= check("X-Api-Key on read", ex[0].headers.get("x-api-key") == KEY)
ok &= check("availability mapped", out.get("status") == "partially_available", str(out)[:300])
ok &= check("status4k mapped", out.get("status4k") == "unknown", str(out)[:300])
ok &= check("request status shaped",
            out["requests"] == [{"id": 12, "status": "approved", "is4k": False,
                                 "requestedBy": "enes"}], str(out.get("requests")))
ok &= check("requester email not leaked", "should-not@leak.io" not in json.dumps(out))

print("scenario: get_media_status tv uses /tv/ path, no mediaInfo -> not_requested")
out, ex = run_tool("seerr", creds(tool="seerr.get_media_status",
                                  mediaType="tv", tmdbId=1399), [
    resp(200, body={"id": 1399, "name": "Game of Thrones",
                    "firstAirDate": "2011-04-17"}),
])
ok &= check("tv URL byte-exact", ex[0].url == f"{BASE}/api/v1/tv/1399", ex[0].url)
ok &= check("tv title/date mapped, not_requested",
            out.get("title") == "Game of Thrones"
            and out.get("releaseDate") == "2011-04-17"
            and out.get("status") == "not_requested"
            and out.get("status4k") == "not_requested", str(out)[:300])

# ---------------------------------------------------------------------------
# 3. seerr.list_requests — happy path with filter
# ---------------------------------------------------------------------------
print("scenario: list_requests happy path")
out, ex = run_tool("seerr", creds(tool="seerr.list_requests", filter="pending"), [
    resp(200, body={"pageInfo": {"pages": 1, "results": 1}, "results": [
        {"id": 42, "type": "movie", "status": 1,
         "media": {"id": 7, "mediaType": "movie", "tmdbId": 603, "status": 3,
                   "ratingKey": "raw-plex-key"},
         "requestedBy": {"id": 2, "displayName": "ann",
                         "plexToken": "PLEX-TOKEN-should-not-leak"}}]}),
])
ok &= check("URL byte-exact",
            ex[0].url == f"{BASE}/api/v1/request?take=20&skip=0&filter=pending", ex[0].url)
ok &= check("count == 1", out.get("count") == 1, str(out)[:200])
ok &= check("request shaped",
            out["requests"][0] == {"id": 42, "type": "movie",
                                   "status": "pending_approval", "mediaType": "movie",
                                   "tmdbId": 603, "title": None,
                                   "mediaStatus": "processing", "requestedBy": "ann"},
            str(out["requests"][0]))
ok &= check("raw plexToken/ratingKey absent",
            "plexToken" not in json.dumps(out) and "raw-plex-key" not in json.dumps(out))

print("scenario: list_requests invalid filter -> friendly error, no HTTP call")
out, ex = run_tool("seerr", creds(tool="seerr.list_requests", filter="weird"), [])
ok &= check("filter enum error",
            "filter must be one of" in out.get("error", ""), str(out))
ok &= check("no HTTP request made", len(ex) == 0, repr(ex))

# ---------------------------------------------------------------------------
# 4. seerr.get_trending — feeds
# ---------------------------------------------------------------------------
print("scenario: get_trending default feed filters persons")
out, ex = run_tool("seerr", creds(tool="seerr.get_trending"), [
    resp(200, body={"page": 1, "results": [
        {"id": 1, "mediaType": "movie", "title": "M", "releaseDate": "2026-01-01"},
        {"id": 2, "mediaType": "person", "name": "Someone Famous"},
    ]}),
])
ok &= check("URL byte-exact",
            ex[0].url == f"{BASE}/api/v1/discover/trending?page=1", ex[0].url)
ok &= check("person filtered from trending", out.get("count") == 1
            and out["results"][0]["title"] == "M", str(out)[:300])

print("scenario: get_trending feed=movies hits /discover/movies")
out, ex = run_tool("seerr", creds(tool="seerr.get_trending", feed="movies", page=2), [
    resp(200, body={"page": 2, "results": [
        {"id": 3, "mediaType": "movie", "title": "N", "releaseDate": "2026-02-01",
         "mediaInfo": {"status": 2}}]}),
])
ok &= check("movies feed URL", ex[0].url == f"{BASE}/api/v1/discover/movies?page=2",
            ex[0].url)
ok &= check("status pending mapped", out["results"][0]["status"] == "pending",
            str(out)[:300])

# ---------------------------------------------------------------------------
# 5. WRITE PATHS — create_request, approve_request, decline_request
# ---------------------------------------------------------------------------
print("scenario: create_request tv with seasons list")
out, ex = run_tool("seerr", creds(tool="seerr.create_request", mediaType="tv",
                                  mediaId=1399, seasons=[1, 2]), [
    resp(201, body={"id": 77, "type": "tv", "status": 1,
                    "media": {"mediaType": "tv", "tmdbId": 1399, "status": 2},
                    "requestedBy": {"displayName": "enes"}}),
])
ok &= check("method POST", ex[0].method == "POST", ex[0].method)
ok &= check("URL byte-exact", ex[0].url == f"{BASE}/api/v1/request", ex[0].url)
ok &= check("Content-Type json",
            ex[0].headers.get("content-type") == "application/json", str(ex[0].headers))
ok &= check("body exact",
            ex[0].json == {"mediaType": "tv", "mediaId": 1399, "seasons": [1, 2]},
            str(ex[0].body))
ok &= check("X-Api-Key on write", ex[0].headers.get("x-api-key") == KEY)
ok &= check("created request shaped",
            out == {"id": 77, "type": "tv", "status": "pending_approval",
                    "mediaType": "tv", "tmdbId": 1399, "title": None,
                    "mediaStatus": "pending", "requestedBy": "enes"}, str(out))

print("scenario: create_request movie, seasons='all' only for tv")
out, ex = run_tool("seerr", creds(tool="seerr.create_request", mediaType="movie",
                                  mediaId=603), [
    resp(201, body={"id": 78, "type": "movie", "status": 2,
                    "media": {"mediaType": "movie", "tmdbId": 603, "status": 3}}),
])
ok &= check("movie body has no seasons",
            ex[0].json == {"mediaType": "movie", "mediaId": 603}, str(ex[0].body))
out, ex = run_tool("seerr", creds(tool="seerr.create_request", mediaType="movie",
                                  mediaId=603, seasons="all"), [])
ok &= check("seasons rejected for movie, no HTTP call",
            out.get("error") == "seasons only applies to mediaType 'tv'"
            and len(ex) == 0, str(out))
out, ex = run_tool("seerr", creds(tool="seerr.create_request", mediaType="tv",
                                  mediaId=1399, seasons="all"), [
    resp(201, body={"id": 79, "type": "tv", "status": 1,
                    "media": {"mediaType": "tv", "tmdbId": 1399, "status": 2}}),
])
ok &= check("seasons 'all' passed through",
            ex[0].json == {"mediaType": "tv", "mediaId": 1399, "seasons": "all"},
            str(ex[0].body))

print("scenario: approve_request POSTs to /request/{id}/approve")
out, ex = run_tool("seerr", creds(tool="seerr.approve_request", requestId=42), [
    resp(200, body={"id": 42, "status": 2}),
])
ok &= check("method POST", ex[0].method == "POST", ex[0].method)
ok &= check("URL byte-exact", ex[0].url == f"{BASE}/api/v1/request/42/approve", ex[0].url)
ok &= check("no body on approve POST", ex[0].body is None, str(ex[0].body))
ok &= check("success output",
            out == {"requestId": 42, "approved": True, "status": "approved"}, str(out))

print("scenario: decline_request POSTs to /request/{id}/decline")
out, ex = run_tool("seerr", creds(tool="seerr.decline_request", requestId="43"), [
    resp(200, body={"id": 43, "status": 3}),
])
ok &= check("string id coerced, URL byte-exact",
            ex[0].url == f"{BASE}/api/v1/request/43/decline", ex[0].url)
ok &= check("success output",
            out == {"requestId": 43, "declined": True, "status": "declined"}, str(out))

# ---------------------------------------------------------------------------
# 6. ERROR PATHS
# ---------------------------------------------------------------------------
print("scenario: 401 surfaces friendly error")
out, ex = run_tool("seerr", creds(tool="seerr.list_requests"), [
    err(401, body={"message": "You do not have permission to access this endpoint"}),
])
raw = json.dumps(out)
ok &= check("error key present", "error" in out and isinstance(out["error"], str), raw[:200])
ok &= check("includes HTTP status 401", "401" in out["error"], out.get("error", ""))
ok &= check("includes API message",
            "You do not have permission" in out["error"], out.get("error", ""))
ok &= check("no Python traceback leaked",
            "Traceback" not in raw and "urllib" not in raw and "HTTPError" not in raw,
            raw[:300])
ok &= check("api key not leaked in error", KEY not in raw, raw[:300])

print("scenario: 429 includes Retry-After and slow-down hint")
out, ex = run_tool("seerr", creds(tool="seerr.search_media", query="x"), [
    err(429, body={"message": "Too many requests"}, headers={"Retry-After": "30"}),
])
ok &= check("429 error surfaced", "error" in out and "429" in out["error"], str(out)[:300])
ok &= check("retry-after included", "30" in out["error"], out.get("error", ""))
ok &= check("rate-limit hint present", "rate limited, slow down" in out["error"],
            out.get("error", ""))

print("scenario: URLError -> self-hosted reachability hint")
import urllib.error as _ue
import mockhttp as _m


class _RefusingTransport(_m.MockTransport):
    def __call__(self, req, *a, **k):
        super().__call__(req, *a, **k)
        raise _ue.URLError("[Errno 111] Connection refused")


_t = _RefusingTransport([resp(200, body={})])
import io as _io
import contextlib as _ctx
_src = open(f"{_m.REPO}/skills/seerr/main.py", encoding="utf-8").read()
_buf = _io.StringIO()
with _m.patched(_t), _ctx.redirect_stdout(_buf):
    exec(compile(_src, "seerr/main.py", "exec"),
         {"params": creds(tool="seerr.get_trending")})
out = json.loads(_buf.getvalue().strip())
ok &= check("URLError handled as friendly error", "error" in out, str(out)[:300])
ok &= check("mentions sandbox reachability",
            "sandbox" in out["error"] and "Could not reach" in out["error"],
            out.get("error", ""))
ok &= check("no traceback on URLError", "Traceback" not in json.dumps(out))

print("scenario: non-JSON error body tolerated")
out, ex = run_tool("seerr", creds(tool="seerr.search_media", query="x"), [
    err(502, body="<html>bad gateway</html>"),
])
ok &= check("502 non-JSON body still friendly",
            "error" in out and "502" in out["error"]
            and "Traceback" not in json.dumps(out), str(out)[:300])

print("scenario: missing required param -> friendly error, no HTTP call")
out, ex = run_tool("seerr", creds(tool="seerr.search_media"), [])
ok &= check("query required error", out.get("error") == "query required", str(out))
ok &= check("no HTTP request made", len(ex) == 0, repr(ex))

print("scenario: missing credentials -> connect-first error, no HTTP call")
out, ex = run_tool("seerr", {"tool": "seerr.list_requests", "base_url": "",
                             "api_key": ""}, [])
ok &= check("connect-first message",
            "connect the Overseerr integration first" in out.get("error", ""), str(out))
ok &= check("names the fields", "base_url" in out["error"] and "api_key" in out["error"],
            out.get("error", ""))
ok &= check("no HTTP request made", len(ex) == 0, repr(ex))

print("scenario: unknown tool -> friendly error")
out, ex = run_tool("seerr", creds(tool="seerr.nope"), [])
ok &= check("unknown tool error", out.get("error") == "Unknown tool: seerr.nope", str(out))

# ---------------------------------------------------------------------------
# 7. SECURITY PROBES
# ---------------------------------------------------------------------------
print("scenario: path-injection ids rejected (must be integers), no HTTP call")
out, ex = run_tool("seerr", creds(tool="seerr.get_media_status", mediaType="movie",
                                  tmdbId="603/../../auth/me"), [])
ok &= check("tmdbId injection rejected", out.get("error") == "tmdbId must be an integer",
            str(out))
ok &= check("no HTTP request made", len(ex) == 0, repr(ex))
out, ex = run_tool("seerr", creds(tool="seerr.approve_request",
                                  requestId="42/approve/../../user"), [])
ok &= check("requestId injection rejected",
            out.get("error") == "requestId must be an integer", str(out))
ok &= check("no HTTP request made", len(ex) == 0, repr(ex))
out, ex = run_tool("seerr", creds(tool="seerr.get_media_status",
                                  mediaType="movie/../tv", tmdbId=1), [])
ok &= check("mediaType injection rejected",
            out.get("error") == "mediaType must be 'movie' or 'tv'", str(out))
ok &= check("no HTTP request made", len(ex) == 0, repr(ex))

print("scenario: secret never appears in any output (error path)")
out, ex = run_tool("seerr", creds(tool="seerr.get_trending"), [
    err(403, body={"message": "forbidden"}),
])
ok &= check("api_key absent from error output", KEY not in json.dumps(out),
            json.dumps(out)[:300])

print()
print("RESULT:", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
