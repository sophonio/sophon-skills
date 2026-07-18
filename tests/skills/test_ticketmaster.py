"""Offline mock-HTTP integration tests for the ticketmaster skill."""
import json
import sys

from mockhttp import run_tool, resp, err, check

BASE = "https://app.ticketmaster.com/discovery/v2"
KEY = "tmkey-SECRET-VALUE-9f2"


def creds(**extra):
    p = {"apiKey": KEY}
    p.update(extra)
    return p


ok = True

# ---------------------------------------------------------------------------
# 1. ticketmaster.search_events — happy path + auth exactness (apikey query param)
# ---------------------------------------------------------------------------
print("scenario: search_events happy path / auth exactness")
out, ex = run_tool("ticketmaster", creds(tool="ticketmaster.search_events",
                                         keyword="rock", city="Boston"), [
    resp(200, body={
        "_embedded": {"events": [
            {"id": "ev1", "name": "Rock Night",
             "url": "https://www.ticketmaster.com/e/ev1",
             "dates": {"start": {"localDate": "2026-08-01",
                                 "dateTime": "2026-08-01T23:00:00Z"}},
             "priceRanges": [{"type": "standard", "currency": "USD",
                              "min": 39.5, "max": 129.5, "raw-noise": True}],
             "_embedded": {"venues": [{"name": "TD Garden",
                                       "city": {"name": "Boston"},
                                       "country": {"name": "United States Of America"},
                                       "boxOfficeInfo": {"deep": "stuff"}}]},
             "seatmap": {"staticUrl": "x"}, "sales": {"public": {}}},
            {"id": "ev2", "name": "Rock Fest", "dates": {}, "url": "u2"},
        ]},
        "page": {"size": 20, "totalElements": 2, "totalPages": 1, "number": 0},
    }),
])
ok &= check("one request made", len(ex) == 1, repr(ex))
ok &= check("method GET", ex[0].method == "GET", ex[0].method)
ok &= check("URL byte-exact: apikey as query param, no page when 0",
            ex[0].url == f"{BASE}/events.json?keyword=rock&city=Boston&size=20&apikey={KEY}",
            ex[0].url)
ok &= check("no Authorization header (key is a query param)",
            "authorization" not in ex[0].headers, str(ex[0].headers))
ok &= check("Accept header", ex[0].headers.get("accept") == "application/json",
            str(ex[0].headers))
ok &= check("descriptive User-Agent",
            ex[0].headers.get("user-agent") == "sophon-ticketmaster-skill",
            str(ex[0].headers))
ok &= check("no request body", ex[0].body is None, str(ex[0].body))
ok &= check("count == 2, total surfaced", out.get("count") == 2 and out.get("total") == 2,
            str(out)[:200])
e0 = out["events"][0]
ok &= check("event shaped (name/date/venue/priceRanges/url)",
            e0["name"] == "Rock Night" and e0["localDate"] == "2026-08-01"
            and e0["venue"] == "TD Garden" and e0["city"] == "Boston"
            and e0["priceRanges"] == [{"type": "standard", "currency": "USD",
                                       "min": 39.5, "max": 129.5}]
            and e0["url"] == "https://www.ticketmaster.com/e/ev1", str(e0))
ok &= check("raw HAL fields absent (_embedded/dates/seatmap/sales)",
            "_embedded" not in e0 and "dates" not in e0 and "seatmap" not in e0
            and "sales" not in e0, str(e0))
ok &= check("key not echoed in output", KEY not in json.dumps(out))

print("scenario: search_events full filters + size clamp + page")
out, ex = run_tool("ticketmaster", creds(tool="ticketmaster.search_events",
                                         keyword="jazz", countryCode="US",
                                         startDateTime="2026-08-01T00:00:00Z",
                                         endDateTime="2026-09-01T00:00:00Z",
                                         classificationName="Music",
                                         size=500, page=2), [
    resp(200, body={"_embedded": {"events": []}, "page": {"totalElements": 0}}),
])
ok &= check("size clamped to 100, page passed, empties dropped",
            ex[0].url == f"{BASE}/events.json?keyword=jazz&countryCode=US"
                         "&startDateTime=2026-08-01T00%3A00%3A00Z"
                         "&endDateTime=2026-09-01T00%3A00%3A00Z"
                         f"&classificationName=Music&size=100&page=2&apikey={KEY}",
            ex[0].url)
ok &= check("empty result count 0", out.get("count") == 0, str(out))

print("scenario: search_events deep-paging cap -> friendly error, no HTTP call")
out, ex = run_tool("ticketmaster", creds(tool="ticketmaster.search_events",
                                         size=100, page=10), [])
ok &= check("deep paging rejected with 1000 hint",
            "error" in out and "1000" in out["error"], str(out))
ok &= check("no HTTP request made", len(ex) == 0, repr(ex))

# ---------------------------------------------------------------------------
# 2. ticketmaster.get_event — happy path incl. onsale dates
# ---------------------------------------------------------------------------
print("scenario: get_event happy path")
out, ex = run_tool("ticketmaster", creds(tool="ticketmaster.get_event",
                                         eventId="G5vYZ4x1sVo-1"), [
    resp(200, body={
        "id": "G5vYZ4x1sVo-1", "name": "Big Show",
        "url": "https://www.ticketmaster.com/e/G5vYZ4x1sVo-1",
        "info": "Doors at 7", "pleaseNote": "No cameras",
        "dates": {"start": {"localDate": "2026-09-10", "localTime": "20:00:00",
                            "dateTime": "2026-09-11T00:00:00Z"},
                  "status": {"code": "onsale"}, "timezone": "America/New_York"},
        "sales": {"public": {"startDateTime": "2026-07-01T14:00:00Z",
                             "endDateTime": "2026-09-11T00:00:00Z"}},
        "priceRanges": [{"type": "standard", "currency": "USD", "min": 25, "max": 250}],
        "classifications": [{"segment": {"name": "Music"}, "genre": {"name": "Rock"},
                             "subGenre": {"name": "Undefined"}}],
        "seatmap": {"staticUrl": "https://maps.tm.com/x.png"},
        "_embedded": {"venues": [{"id": "v1", "name": "MSG",
                                  "city": {"name": "New York"},
                                  "country": {"name": "United States Of America"}}],
                      "attractions": [{"id": "a1", "name": "The Band",
                                       "images": [{"big": "blob"}]}]},
        "_links": {"self": {"href": "x"}},
    }),
])
ok &= check("URL byte-exact (id in path, apikey query)",
            ex[0].url == f"{BASE}/events/G5vYZ4x1sVo-1.json?apikey={KEY}", ex[0].url)
ok &= check("onsale window surfaced",
            out.get("onsaleStart") == "2026-07-01T14:00:00Z"
            and out.get("onsaleEnd") == "2026-09-11T00:00:00Z", str(out)[:300])
ok &= check("status/timezone/start surfaced",
            out.get("status") == "onsale" and out.get("timezone") == "America/New_York"
            and out.get("start", {}).get("localDate") == "2026-09-10", str(out)[:300])
ok &= check("venue and attractions trimmed",
            out.get("venue") == {"id": "v1", "name": "MSG", "city": "New York",
                                 "country": "United States Of America"}
            and out.get("attractions") == [{"id": "a1", "name": "The Band"}], str(out)[:400])
ok &= check("classifications flattened, Undefined dropped",
            out.get("classifications") == ["Music / Rock"], str(out.get("classifications")))
ok &= check("raw _embedded/_links absent",
            "_embedded" not in out and "_links" not in out, str(out)[:300])

# ---------------------------------------------------------------------------
# 3. ticketmaster.search_attractions + get_attraction_events + search_venues
# ---------------------------------------------------------------------------
print("scenario: search_attractions happy path")
out, ex = run_tool("ticketmaster", creds(tool="ticketmaster.search_attractions",
                                         keyword="Coldplay", size=5), [
    resp(200, body={"_embedded": {"attractions": [
        {"id": "K8vZ917Gku7", "name": "Coldplay",
         "url": "https://www.ticketmaster.com/coldplay",
         "classifications": [{"segment": {"name": "Music"}, "genre": {"name": "Rock"}}],
         "images": [{"url": "huge-blob"}], "externalLinks": {"deep": "stuff"}}]}}),
])
ok &= check("URL byte-exact",
            ex[0].url == f"{BASE}/attractions.json?keyword=Coldplay&size=5&apikey={KEY}",
            ex[0].url)
ok &= check("attraction shaped, raw images/externalLinks absent",
            out == {"count": 1, "attractions": [
                {"id": "K8vZ917Gku7", "name": "Coldplay",
                 "classifications": ["Music / Rock"],
                 "url": "https://www.ticketmaster.com/coldplay"}]}, str(out))

print("scenario: get_attraction_events happy path")
out, ex = run_tool("ticketmaster", creds(tool="ticketmaster.get_attraction_events",
                                         attractionId="K8vZ917Gku7"), [
    resp(200, body={"_embedded": {"events": [
        {"id": "ev9", "name": "Coldplay Live", "url": "u",
         "dates": {"start": {"localDate": "2026-10-01"}},
         "_embedded": {"venues": [{"name": "Wembley", "city": {"name": "London"},
                                   "country": {"name": "Great Britain"}}]}}]}}),
])
ok &= check("URL byte-exact (attractionId as query param)",
            ex[0].url == f"{BASE}/events.json?attractionId=K8vZ917Gku7&size=20&apikey={KEY}",
            ex[0].url)
ok &= check("events shaped",
            out["count"] == 1 and out["events"][0]["name"] == "Coldplay Live"
            and out["events"][0]["venue"] == "Wembley"
            and out["events"][0]["city"] == "London", str(out)[:300])

print("scenario: search_venues happy path")
out, ex = run_tool("ticketmaster", creds(tool="ticketmaster.search_venues",
                                         keyword="Garden"), [
    resp(200, body={"_embedded": {"venues": [
        {"id": "v1", "name": "TD Garden", "url": "vu",
         "city": {"name": "Boston"}, "state": {"name": "Massachusetts"},
         "country": {"name": "United States Of America"},
         "boxOfficeInfo": {"phone": "x"}, "markets": [{"id": "m"}]}]}}),
])
ok &= check("URL byte-exact",
            ex[0].url == f"{BASE}/venues.json?keyword=Garden&size=20&apikey={KEY}", ex[0].url)
ok &= check("venue shaped",
            out == {"count": 1, "venues": [
                {"id": "v1", "name": "TD Garden", "city": "Boston",
                 "state": "Massachusetts", "country": "United States Of America",
                 "url": "vu"}]}, str(out))

# ---------------------------------------------------------------------------
# 4. list_classifications + suggest
# ---------------------------------------------------------------------------
print("scenario: list_classifications happy path")
out, ex = run_tool("ticketmaster", creds(tool="ticketmaster.list_classifications"), [
    resp(200, body={"_embedded": {"classifications": [
        {"segment": {"id": "KZFzniwnSyZfZ7v7nJ", "name": "Music",
                     "_embedded": {"genres": [{"id": "g1", "name": "Rock"},
                                              {"id": "g2", "name": "Jazz"}]}}},
        {"type": {"id": "t1", "name": "Donation"}},
    ]}}),
])
ok &= check("URL byte-exact", ex[0].url == f"{BASE}/classifications.json?apikey={KEY}",
            ex[0].url)
ok &= check("segments shaped, type-only rows skipped",
            out == {"count": 1, "segments": [
                {"id": "KZFzniwnSyZfZ7v7nJ", "segment": "Music",
                 "genres": ["Rock", "Jazz"]}]}, str(out))

print("scenario: suggest happy path")
out, ex = run_tool("ticketmaster", creds(tool="ticketmaster.suggest", keyword="cold"), [
    resp(200, body={"_embedded": {
        "attractions": [{"id": "a1", "name": "Coldplay", "images": ["x"]}],
        "venues": [{"id": "v1", "name": "Coliseum", "city": {"name": "Oakland"}}],
        "events": [{"id": "e1", "name": "Coldplay Live", "url": "eu",
                    "dates": {"start": {"localDate": "2026-10-01"}}}],
    }}),
])
ok &= check("URL byte-exact", ex[0].url == f"{BASE}/suggest.json?keyword=cold&apikey={KEY}",
            ex[0].url)
ok &= check("suggest shaped",
            out == {"attractions": [{"id": "a1", "name": "Coldplay"}],
                    "venues": [{"id": "v1", "name": "Coliseum", "city": "Oakland"}],
                    "events": [{"id": "e1", "name": "Coldplay Live",
                                "localDate": "2026-10-01", "url": "eu"}]}, str(out))

# ---------------------------------------------------------------------------
# 5. ERROR PATHS
# ---------------------------------------------------------------------------
print("scenario: 401 invalid key -> friendly error, fault body parsed")
out, ex = run_tool("ticketmaster", creds(tool="ticketmaster.get_event", eventId="ev1"), [
    err(401, body={"fault": {"faultstring": "Invalid ApiKey",
                             "detail": {"errorcode": "oauth.v2.InvalidApiKey"}}}),
])
raw = json.dumps(out)
ok &= check("error key present", "error" in out and isinstance(out["error"], str), raw[:200])
ok &= check("includes HTTP status 401", "401" in out["error"], out.get("error", ""))
ok &= check("includes faultstring", "Invalid ApiKey" in out["error"], out.get("error", ""))
ok &= check("no Python traceback leaked",
            "Traceback" not in raw and "urllib" not in raw and "HTTPError" not in raw,
            raw[:300])
ok &= check("key not leaked in error output", KEY not in raw, raw[:300])

print("scenario: 429 includes Retry-After and slow-down hint")
out, ex = run_tool("ticketmaster", creds(tool="ticketmaster.search_events", keyword="x"), [
    err(429, body={"fault": {"faultstring": "Rate limit quota violation"}},
        headers={"Retry-After": "2"}),
])
ok &= check("429 error surfaced", "error" in out and "429" in out["error"], str(out)[:300])
ok &= check("Retry-After included", "retry after 2s" in out["error"], out.get("error", ""))
ok &= check("slow-down hint", "rate limited, slow down" in out["error"],
            out.get("error", ""))

print("scenario: errors[] body form and non-JSON body tolerated")
out, ex = run_tool("ticketmaster", creds(tool="ticketmaster.get_event", eventId="nope"), [
    err(404, body={"errors": [{"code": "DIS1004", "detail": "Resource not found",
                               "status": "404"}]}),
])
ok &= check("404 detail parsed", "404" in out["error"] and "Resource not found" in out["error"],
            out.get("error", ""))
out, ex = run_tool("ticketmaster", creds(tool="ticketmaster.get_event", eventId="ev1"), [
    err(502, body="<html>bad gateway</html>"),
])
ok &= check("502 non-JSON body still friendly",
            "error" in out and "502" in out["error"] and "Traceback" not in json.dumps(out),
            str(out)[:300])

print("scenario: missing required param -> friendly error, no HTTP call")
out, ex = run_tool("ticketmaster", creds(tool="ticketmaster.search_attractions"), [])
ok &= check("keyword required error", out.get("error") == "keyword required", str(out))
ok &= check("no HTTP request made", len(ex) == 0, repr(ex))
out, ex = run_tool("ticketmaster", creds(tool="ticketmaster.get_attraction_events"), [])
ok &= check("attractionId required error", out.get("error") == "attractionId required",
            str(out))

print("scenario: missing credentials -> friendly connect-first error, no HTTP call")
out, ex = run_tool("ticketmaster", {"tool": "ticketmaster.search_events"}, [])
ok &= check("missing-credentials message names apiKey and connect-first",
            "error" in out and "apiKey" in out["error"]
            and "connect the Ticketmaster integration" in out["error"], str(out))
ok &= check("no HTTP request made", len(ex) == 0, repr(ex))

print("scenario: unknown tool -> friendly error")
out, ex = run_tool("ticketmaster", creds(tool="ticketmaster.nope"), [])
ok &= check("unknown tool error", out.get("error") == "Unknown tool: ticketmaster.nope",
            str(out))

# ---------------------------------------------------------------------------
# 6. SECURITY PROBES
# ---------------------------------------------------------------------------
print("scenario: path-traversal eventId is percent-encoded")
evil = "abc/../def?x=1"
out, ex = run_tool("ticketmaster", creds(tool="ticketmaster.get_event", eventId=evil), [
    resp(200, body={"id": "x"}),
])
ok &= check("id fully quoted in path (no path escape)",
            ex[0].url == f"{BASE}/events/abc%2F..%2Fdef%3Fx%3D1.json?apikey={KEY}",
            ex[0].url)
ok &= check("no raw '../' in URL", "../" not in ex[0].url, ex[0].url)

print("scenario: bare dot segments rejected before any HTTP call")
out, ex = run_tool("ticketmaster", creds(tool="ticketmaster.get_event", eventId=".."), [])
ok &= check("'..' rejected", "error" in out and "Invalid eventId" in out["error"], str(out))
ok &= check("no HTTP request made", len(ex) == 0, repr(ex))
out, ex = run_tool("ticketmaster", creds(tool="ticketmaster.get_event", eventId="."), [])
ok &= check("'.' rejected", "error" in out and "Invalid eventId" in out["error"], str(out))

print("scenario: secret never appears in any output (error path)")
out, ex = run_tool("ticketmaster", creds(tool="ticketmaster.search_venues", keyword="x"), [
    err(403, body={"fault": {"faultstring": f"forbidden for key {KEY}"}}),
])
ok &= check("apiKey scrubbed even when echoed by the API",
            KEY not in json.dumps(out) and "[redacted]" in out.get("error", ""),
            json.dumps(out)[:300])

print()
print("RESULT:", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
