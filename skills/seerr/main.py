"""Seerr integration skill — media requests via the Overseerr / Jellyseerr API.

Pure standard library (urllib) so it runs unchanged in the alpine Python sandbox with no pip
dependencies. `params` is injected as a global by the Sophon runtime and carries the tool name,
the tool arguments, and the connection-card fields (base_url, api_key).

Auth is the instance's static API key (Settings > General > API Key) sent as the `X-Api-Key`
header on every call. The key is admin-scoped, so create/approve/decline act with admin rights.
All endpoints live under {base_url}/api/v1 and the same API surface works against both Overseerr
and Jellyseerr. The server is self-hosted: it must be reachable from Sophon's sandbox (LAN/VPN
only hosts usually are not without a reverse proxy or tunnel).
"""

import json
import urllib.request
import urllib.parse
import urllib.error

tool_name = params.get("tool", "")
base_url = (params.get("base_url") or "").rstrip("/")
api_key = params.get("api_key") or ""

API_PREFIX = "/api/v1"

MEDIA_STATUS = {
    1: "unknown",
    2: "pending",
    3: "processing",
    4: "partially_available",
    5: "available",
    6: "deleted",
}

REQUEST_STATUS = {
    1: "pending_approval",
    2: "approved",
    3: "declined",
    4: "failed",
}

REQUEST_FILTERS = ("all", "pending", "approved", "available", "processing")

DISCOVER_FEEDS = {
    "trending": "/discover/trending",
    "movies": "/discover/movies",
    "tv": "/discover/tv",
}


def request(method, path, data=None, query=None):
    """Make an authenticated request to the Seerr server. Returns parsed JSON (or None for 204)."""
    url = f"{base_url}{API_PREFIX}{path}"
    if query:
        clean = {k: v for k, v in query.items() if v not in (None, "")}
        if clean:
            url = f"{url}?{urllib.parse.urlencode(clean)}"
    body = json.dumps(data).encode() if data is not None else None
    headers = {
        "X-Api-Key": api_key,
        "Accept": "application/json",
        "User-Agent": "sophon-seerr-skill",
    }
    if body is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read().decode(errors="replace")
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace") if e.fp else ""
        try:
            parsed = json.loads(detail)
            msg = parsed.get("message") or parsed.get("error") or detail[:200]
        except (ValueError, TypeError, AttributeError):
            msg = detail[:200]
        if e.code in (401, 403):
            msg = msg or "authentication failed — check the API key (Settings > General)"
        elif e.code == 404:
            msg = msg or "not found — check the id and mediaType"
        elif e.code == 429:
            retry_after = e.headers.get("Retry-After")
            hint = "rate limited, slow down"
            if retry_after:
                hint = f"{hint}; retry after {retry_after}s"
            msg = f"{msg} ({hint})" if msg else hint
        raise RuntimeError(f"Seerr API error {e.code}: {msg}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(
            "Could not reach your Overseerr/Jellyseerr server — it may not be reachable "
            "from Sophon's sandbox (LAN/VPN-only hosts usually need a reverse proxy or "
            f"tunnel): {e.reason}"
        ) from e


def clamp(value, default, maximum):
    try:
        return max(1, min(int(value), maximum))
    except (TypeError, ValueError):
        return default


def require_int(value, name):
    """Coerce a params-derived id to int; rejects path-injection strings outright."""
    if isinstance(value, bool):
        raise ValueError(f"{name} must be an integer")
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        raise ValueError(f"{name} must be an integer")


def require_media_type():
    media_type = str(params.get("mediaType") or "").strip().lower()
    if media_type not in ("movie", "tv"):
        raise ValueError("mediaType must be 'movie' or 'tv'")
    return media_type


def media_status(info):
    if not info:
        return "not_requested"
    return MEDIA_STATUS.get(info.get("status"), "unknown")


def media_summary(item):
    info = item.get("mediaInfo")
    return {
        "id": item.get("id"),
        "mediaType": item.get("mediaType"),
        "title": item.get("title") or item.get("name"),
        "releaseDate": item.get("releaseDate") or item.get("firstAirDate"),
        "overview": (item.get("overview") or "")[:280] or None,
        "status": media_status(info),
    }


def request_summary(r):
    media = r.get("media") or {}
    return {
        "id": r.get("id"),
        "type": r.get("type"),
        "status": REQUEST_STATUS.get(r.get("status"), "unknown"),
        "mediaType": media.get("mediaType"),
        "tmdbId": media.get("tmdbId"),
        "title": media.get("title") or media.get("name"),
        "mediaStatus": MEDIA_STATUS.get(media.get("status"), "unknown"),
        "requestedBy": (r.get("requestedBy") or {}).get("displayName"),
    }


# --- Tool handlers ---------------------------------------------------------

def search_media():
    query = params.get("query")
    if not query:
        raise ValueError("query required")
    page = clamp(params.get("page", 1), 1, 1000)
    result = request("GET", "/search", query={"query": query, "page": page}) or {}
    results = [media_summary(i) for i in result.get("results") or []
               if i.get("mediaType") in ("movie", "tv")]
    print(json.dumps({
        "count": len(results),
        "page": result.get("page"),
        "totalResults": result.get("totalResults"),
        "results": results,
    }))


def get_media_status():
    media_type = require_media_type()
    tmdb_id = require_int(params.get("tmdbId"), "tmdbId")
    path = f"/{media_type}/{urllib.parse.quote(str(tmdb_id), safe='')}"
    result = request("GET", path) or {}
    info = result.get("mediaInfo")
    requests_list = [{
        "id": r.get("id"),
        "status": REQUEST_STATUS.get(r.get("status"), "unknown"),
        "is4k": r.get("is4k"),
        "requestedBy": (r.get("requestedBy") or {}).get("displayName"),
    } for r in (info or {}).get("requests") or []]
    print(json.dumps({
        "tmdbId": tmdb_id,
        "mediaType": media_type,
        "title": result.get("title") or result.get("name"),
        "releaseDate": result.get("releaseDate") or result.get("firstAirDate"),
        "status": media_status(info),
        "status4k": MEDIA_STATUS.get((info or {}).get("status4k"), "unknown") if info else "not_requested",
        "requests": requests_list,
    }))


def list_requests():
    take = clamp(params.get("take", 20), 20, 100)
    try:
        skip = max(0, int(params.get("skip", 0)))
    except (TypeError, ValueError):
        skip = 0
    filter_ = params.get("filter")
    if filter_ is not None:
        filter_ = str(filter_).strip().lower()
        if filter_ not in REQUEST_FILTERS:
            raise ValueError(f"filter must be one of: {', '.join(REQUEST_FILTERS)}")
    result = request("GET", "/request",
                     query={"take": take, "skip": skip, "filter": filter_}) or {}
    requests_list = [request_summary(r) for r in result.get("results") or []]
    print(json.dumps({"count": len(requests_list), "requests": requests_list}))


def get_trending():
    feed = str(params.get("feed") or "trending").strip().lower()
    if feed not in DISCOVER_FEEDS:
        raise ValueError(f"feed must be one of: {', '.join(DISCOVER_FEEDS)}")
    page = clamp(params.get("page", 1), 1, 1000)
    result = request("GET", DISCOVER_FEEDS[feed], query={"page": page}) or {}
    items = result.get("results") or []
    if feed == "trending":
        # the trending feed mixes in person results — keep movies and tv only
        items = [i for i in items if i.get("mediaType") in ("movie", "tv")]
    results = [media_summary(i) for i in items]
    print(json.dumps({"count": len(results), "feed": feed, "results": results}))


def create_request():
    media_type = require_media_type()
    media_id = require_int(params.get("mediaId"), "mediaId")
    payload = {"mediaType": media_type, "mediaId": media_id}
    seasons = params.get("seasons")
    if seasons is not None:
        if media_type != "tv":
            raise ValueError("seasons only applies to mediaType 'tv'")
        if seasons == "all":
            payload["seasons"] = "all"
        elif isinstance(seasons, list):
            payload["seasons"] = [require_int(s, "seasons") for s in seasons]
        else:
            raise ValueError("seasons must be 'all' or a list of season numbers")
    result = request("POST", "/request", data=payload) or {}
    print(json.dumps(request_summary(result)))


def approve_request():
    request_id = require_int(params.get("requestId"), "requestId")
    path = f"/request/{urllib.parse.quote(str(request_id), safe='')}/approve"
    result = request("POST", path) or {}
    print(json.dumps({
        "requestId": request_id,
        "approved": True,
        "status": REQUEST_STATUS.get(result.get("status"), "unknown"),
    }))


def decline_request():
    request_id = require_int(params.get("requestId"), "requestId")
    path = f"/request/{urllib.parse.quote(str(request_id), safe='')}/decline"
    result = request("POST", path) or {}
    print(json.dumps({
        "requestId": request_id,
        "declined": True,
        "status": REQUEST_STATUS.get(result.get("status"), "unknown"),
    }))


HANDLERS = {
    "seerr.search_media": search_media,
    "seerr.get_media_status": get_media_status,
    "seerr.list_requests": list_requests,
    "seerr.get_trending": get_trending,
    "seerr.create_request": create_request,
    "seerr.approve_request": approve_request,
    "seerr.decline_request": decline_request,
}

try:
    handler = HANDLERS.get(tool_name)
    if handler is None:
        print(json.dumps({"error": f"Unknown tool: {tool_name}"}))
    elif not (base_url and api_key):
        print(json.dumps({"error": "Missing Overseerr/Jellyseerr credentials: connect the Overseerr integration first (base_url, api_key)."}))
    else:
        handler()
except (RuntimeError, ValueError) as e:
    print(json.dumps({"error": str(e)}))
except Exception as e:  # noqa: BLE001
    print(json.dumps({"error": f"Unexpected error: {type(e).__name__}: {e}"}))
