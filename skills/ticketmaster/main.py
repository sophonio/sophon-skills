"""Ticketmaster Discovery API skill — search events, attractions, venues, and classifications.

Pure standard library (urllib) so it runs unchanged in the alpine Python sandbox with no pip
dependencies. `params` is injected as a global by the Sophon runtime and carries the tool name,
the tool arguments, and the connection-card fields (apiKey).

Auth is a static Consumer Key passed as the `apikey` query parameter on
https://app.ticketmaster.com/discovery/v2. Be polite with the default quota (throttle to about
2 requests/second) and note deep paging is capped: size * page must stay under 1000 results.
Responses are HAL+JSON — results live under `_embedded` and are shaped to trimmed summaries.
"""

import json
import urllib.request
import urllib.parse
import urllib.error

tool_name = params.get("tool", "")
api_key = params.get("apiKey") or ""

API_BASE = "https://app.ticketmaster.com/discovery/v2"


def scrub(text):
    """Never echo the API key in errors or results."""
    text = str(text)
    if api_key and api_key in text:
        text = text.replace(api_key, "[redacted]")
    return text


def request(path, query=None):
    """GET a Discovery API path. Returns parsed JSON (or None for 204/empty)."""
    clean = {k: v for k, v in (query or {}).items() if v not in (None, "")}
    clean["apikey"] = api_key
    url = f"{API_BASE}{path}?{urllib.parse.urlencode(clean)}"
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "sophon-ticketmaster-skill",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read().decode()
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        detail = e.read().decode() if e.fp else ""
        try:
            parsed = json.loads(detail)
            msg = detail
            if isinstance(parsed, dict):
                fault = parsed.get("fault") or {}
                errors = parsed.get("errors") or []
                first = errors[0] if errors and isinstance(errors[0], dict) else {}
                msg = fault.get("faultstring") or first.get("detail") or detail
        except (ValueError, TypeError):
            msg = detail
        msg = scrub(msg)
        if e.code == 429:
            retry_after = e.headers.get("Retry-After") if e.headers else None
            hint = "rate limited, slow down"
            if retry_after:
                hint += f"; retry after {retry_after}s"
            raise RuntimeError(f"Ticketmaster API error 429: {msg} ({hint})") from e
        raise RuntimeError(f"Ticketmaster API error {e.code}: {msg}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Could not reach Ticketmaster: {scrub(e.reason)}") from e


def clamp(value, default, maximum):
    try:
        return max(1, min(int(value), maximum))
    except (TypeError, ValueError):
        return default


def page_number():
    try:
        return max(0, int(params.get("page", 0)))
    except (TypeError, ValueError):
        return 0


def safe_segment(value, label):
    """URL-quote a params-derived path segment; reject empty and dot segments."""
    s = str(value or "").strip()
    if not s:
        raise ValueError(f"{label} required")
    if s in (".", ".."):
        raise ValueError(f"Invalid {label}: {s}")
    return urllib.parse.quote(s, safe="")


def embedded(result, key):
    return ((result or {}).get("_embedded") or {}).get(key) or []


def price_summary(pr):
    return {"type": pr.get("type"), "currency": pr.get("currency"),
            "min": pr.get("min"), "max": pr.get("max")}


def classification_names(item):
    names = []
    for c in item.get("classifications") or []:
        seg = (c.get("segment") or {}).get("name")
        gen = (c.get("genre") or {}).get("name")
        sub = (c.get("subGenre") or {}).get("name")
        parts = [p for p in (seg, gen, sub) if p and p != "Undefined"]
        if parts:
            names.append(" / ".join(parts))
    return names


def event_summary(ev):
    start = ((ev.get("dates") or {}).get("start")) or {}
    venues = embedded(ev, "venues")
    v = venues[0] if venues else {}
    return {
        "id": ev.get("id"),
        "name": ev.get("name"),
        "localDate": start.get("localDate"),
        "dateTime": start.get("dateTime"),
        "venue": v.get("name"),
        "city": ((v.get("city") or {}).get("name")),
        "country": ((v.get("country") or {}).get("name")),
        "priceRanges": [price_summary(p) for p in ev.get("priceRanges") or []],
        "url": ev.get("url"),
    }


def venue_summary(v):
    return {
        "id": v.get("id"),
        "name": v.get("name"),
        "city": ((v.get("city") or {}).get("name")),
        "state": ((v.get("state") or {}).get("name")),
        "country": ((v.get("country") or {}).get("name")),
        "url": v.get("url"),
    }


def attraction_summary(a):
    return {
        "id": a.get("id"),
        "name": a.get("name"),
        "classifications": classification_names(a),
        "url": a.get("url"),
    }


# --- Tool handlers ---------------------------------------------------------

def search_events():
    size = clamp(params.get("size", 20), 20, 100)
    page = page_number()
    if size * (page + 1) > 1000:
        raise ValueError(
            "Ticketmaster caps paging at the first 1000 results "
            "(size * (page + 1) must be <= 1000); reduce size or page.")
    result = request("/events.json", {
        "keyword": params.get("keyword"),
        "city": params.get("city"),
        "countryCode": params.get("countryCode"),
        "startDateTime": params.get("startDateTime"),
        "endDateTime": params.get("endDateTime"),
        "classificationName": params.get("classificationName"),
        "size": size,
        "page": page if page > 0 else None,
    })
    events = [event_summary(e) for e in embedded(result, "events")]
    total = ((result or {}).get("page") or {}).get("totalElements")
    print(json.dumps({"count": len(events), "total": total, "events": events}))


def get_event():
    event_id = safe_segment(params.get("eventId"), "eventId")
    ev = request(f"/events/{event_id}.json") or {}
    dates = ev.get("dates") or {}
    sales = (ev.get("sales") or {}).get("public") or {}
    venues = embedded(ev, "venues")
    v = venues[0] if venues else {}
    attractions = embedded(ev, "attractions")
    print(json.dumps({
        "id": ev.get("id"),
        "name": ev.get("name"),
        "info": ev.get("info"),
        "pleaseNote": ev.get("pleaseNote"),
        "start": dates.get("start"),
        "status": ((dates.get("status") or {}).get("code")),
        "timezone": dates.get("timezone"),
        "onsaleStart": sales.get("startDateTime"),
        "onsaleEnd": sales.get("endDateTime"),
        "venue": ({"id": v.get("id"), "name": v.get("name"),
                   "city": ((v.get("city") or {}).get("name")),
                   "country": ((v.get("country") or {}).get("name"))} if v else None),
        "attractions": [{"id": a.get("id"), "name": a.get("name")} for a in attractions],
        "classifications": classification_names(ev),
        "priceRanges": [price_summary(p) for p in ev.get("priceRanges") or []],
        "seatmap": ((ev.get("seatmap") or {}).get("staticUrl")),
        "url": ev.get("url"),
    }))


def search_attractions():
    keyword = params.get("keyword")
    if not keyword:
        raise ValueError("keyword required")
    size = clamp(params.get("size", 20), 20, 100)
    result = request("/attractions.json", {"keyword": keyword, "size": size})
    attractions = [attraction_summary(a) for a in embedded(result, "attractions")]
    print(json.dumps({"count": len(attractions), "attractions": attractions}))


def get_attraction_events():
    attraction_id = params.get("attractionId")
    if not attraction_id:
        raise ValueError("attractionId required")
    size = clamp(params.get("size", 20), 20, 100)
    result = request("/events.json", {"attractionId": str(attraction_id), "size": size})
    events = [event_summary(e) for e in embedded(result, "events")]
    print(json.dumps({"count": len(events), "events": events}))


def search_venues():
    keyword = params.get("keyword")
    if not keyword:
        raise ValueError("keyword required")
    size = clamp(params.get("size", 20), 20, 100)
    result = request("/venues.json", {"keyword": keyword, "size": size})
    venues = [venue_summary(v) for v in embedded(result, "venues")]
    print(json.dumps({"count": len(venues), "venues": venues}))


def list_classifications():
    result = request("/classifications.json")
    segments = []
    for c in embedded(result, "classifications"):
        seg = c.get("segment") or {}
        if not seg:
            continue  # classification rows may also carry types/subtypes only
        genres = embedded(seg, "genres")
        segments.append({
            "id": seg.get("id"),
            "segment": seg.get("name"),
            "genres": [g.get("name") for g in genres],
        })
    print(json.dumps({"count": len(segments), "segments": segments}))


def suggest():
    keyword = params.get("keyword")
    if not keyword:
        raise ValueError("keyword required")
    result = request("/suggest.json", {"keyword": keyword})
    emb = (result or {}).get("_embedded") or {}
    print(json.dumps({
        "attractions": [{"id": a.get("id"), "name": a.get("name")}
                        for a in emb.get("attractions") or []],
        "venues": [{"id": v.get("id"), "name": v.get("name"),
                    "city": ((v.get("city") or {}).get("name"))}
                   for v in emb.get("venues") or []],
        "events": [{"id": e.get("id"), "name": e.get("name"),
                    "localDate": ((((e.get("dates") or {}).get("start")) or {}).get("localDate")),
                    "url": e.get("url")}
                   for e in emb.get("events") or []],
    }))


HANDLERS = {
    "ticketmaster.search_events": search_events,
    "ticketmaster.get_event": get_event,
    "ticketmaster.search_attractions": search_attractions,
    "ticketmaster.get_attraction_events": get_attraction_events,
    "ticketmaster.search_venues": search_venues,
    "ticketmaster.list_classifications": list_classifications,
    "ticketmaster.suggest": suggest,
}

try:
    handler = HANDLERS.get(tool_name)
    if handler is None:
        print(json.dumps({"error": f"Unknown tool: {tool_name}"}))
    elif not api_key:
        print(json.dumps({"error": "Missing Ticketmaster credentials: connect the Ticketmaster integration first (apiKey)."}))
    else:
        handler()
except (RuntimeError, ValueError) as e:
    print(json.dumps({"error": str(e)}))
except Exception as e:  # noqa: BLE001
    print(json.dumps({"error": f"Unexpected error: {type(e).__name__}: {e}"}))
