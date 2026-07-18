"""Radarr integration skill — movie management on a self-hosted Radarr v3+ server.

Pure standard library (urllib) so it runs unchanged in the alpine Python sandbox with no pip
dependencies. `params` is injected as a global by the Sophon runtime and carries the tool name,
the tool arguments, and the connection-card fields (base_url, api_key).

Auth is Radarr's static per-instance API key sent as the `X-Api-Key` header on every request.
All endpoints live under {base_url}/api/v3. Radarr is self-hosted: the server must be reachable
from Sophon's sandbox (LAN-only or VPN-only instances need a reverse proxy or tunnel).
"""

import json
import urllib.request
import urllib.parse
import urllib.error

tool_name = params.get("tool", "")
base_url = (params.get("base_url") or "").rstrip("/")
api_key = params.get("api_key") or ""

API = "/api/v3"


def request(method, path, data=None, query=None):
    """Make an authenticated request to Radarr. Returns parsed JSON (or None for 204/empty)."""
    url = f"{base_url}{API}{path}"
    if query:
        clean = {k: v for k, v in query.items() if v not in (None, "")}
        if clean:
            url = f"{url}?{urllib.parse.urlencode(clean)}"
    body = json.dumps(data).encode() if data is not None else None
    headers = {
        "X-Api-Key": api_key,
        "Accept": "application/json",
        "User-Agent": "sophon-radarr-skill",
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
            if isinstance(parsed, list):
                # Radarr validation errors are a list of {propertyName, errorMessage}.
                msg = "; ".join(
                    str((p or {}).get("errorMessage") or p) for p in parsed
                ) or detail[:200]
            elif isinstance(parsed, dict):
                msg = parsed.get("message") or parsed.get("error") or detail[:200]
            else:
                msg = detail[:200]
        except (ValueError, TypeError):
            # Radarr error pages can be HTML — keep only a short hint.
            msg = detail[:200]
        if e.code == 401:
            msg = msg or "authentication failed — check the API key (Radarr Settings > General > Security)"
        elif e.code == 429:
            retry_after = e.headers.get("Retry-After")
            msg = f"{msg or 'too many requests'} — rate limited, slow down"
            if retry_after:
                msg += f" (retry after {retry_after}s)"
        raise RuntimeError(f"Radarr API error {e.code}: {msg}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(
            "Could not reach your Radarr server (it may not be reachable from Sophon's sandbox — "
            f"LAN-only or VPN-only instances need a reverse proxy or tunnel): {e.reason}"
        ) from e


def clamp(value, default, maximum):
    try:
        return max(1, min(int(value), maximum))
    except (TypeError, ValueError):
        return default


def path_id(value, label):
    """Validate and URL-quote a params-derived path segment."""
    s = str(value if value is not None else "").strip()
    if not s:
        raise ValueError(f"{label} required")
    if s in (".", ".."):
        raise ValueError(f"{label} must not be '.' or '..'")
    return urllib.parse.quote(s, safe="")


def movie_summary(m):
    return {
        "id": m.get("id"),
        "title": m.get("title"),
        "year": m.get("year"),
        "monitored": m.get("monitored"),
        "hasFile": m.get("hasFile"),
        "tmdbId": m.get("tmdbId"),
    }


# --- Tool handlers ---------------------------------------------------------

def search_movie_lookup():
    term = params.get("term")
    if not term:
        raise ValueError("term required")
    result = request("GET", "/movie/lookup", query={"term": term}) or []
    movies = [{
        "title": m.get("title"),
        "year": m.get("year"),
        "tmdbId": m.get("tmdbId"),
        "overview": (m.get("overview") or "")[:500],
    } for m in result]
    print(json.dumps({"count": len(movies), "movies": movies}))


def list_movies():
    result = request("GET", "/movie") or []
    movies = [movie_summary(m) for m in result]
    print(json.dumps({"count": len(movies), "movies": movies}))


def get_calendar():
    result = request("GET", "/calendar", query={
        "start": params.get("start"),
        "end": params.get("end"),
    }) or []
    movies = [{
        "title": m.get("title"),
        "year": m.get("year"),
        "inCinemas": m.get("inCinemas"),
        "digitalRelease": m.get("digitalRelease"),
        "physicalRelease": m.get("physicalRelease"),
        "monitored": m.get("monitored"),
    } for m in result]
    print(json.dumps({"count": len(movies), "movies": movies}))


def get_queue():
    result = request("GET", "/queue", query={"pageSize": 50}) or {}
    records = result.get("records") if isinstance(result, dict) else result
    items = []
    for r in records or []:
        size = r.get("size") or 0
        sizeleft = r.get("sizeleft")
        progress = None
        if size and sizeleft is not None:
            progress = round((size - sizeleft) / size * 100, 1)
        items.append({
            "title": r.get("title"),
            "status": r.get("status"),
            "timeleft": r.get("timeleft"),
            "progress": progress,
        })
    print(json.dumps({"count": len(items), "items": items}))


def get_history():
    page = clamp(params.get("page", 1), 1, 100000)
    page_size = clamp(params.get("pageSize", 20), 20, 100)
    result = request("GET", "/history", query={
        "page": page,
        "pageSize": page_size,
    }) or {}
    records = result.get("records") if isinstance(result, dict) else result
    events = [{
        "eventType": r.get("eventType"),
        "sourceTitle": r.get("sourceTitle"),
        "date": r.get("date"),
        "movieId": r.get("movieId"),
    } for r in records or []]
    print(json.dumps({
        "page": result.get("page") if isinstance(result, dict) else page,
        "totalRecords": result.get("totalRecords") if isinstance(result, dict) else None,
        "count": len(events),
        "events": events,
    }))


def add_movie():
    tmdb_id = params.get("tmdbId")
    title = params.get("title")
    quality_profile_id = params.get("qualityProfileId")
    root_folder_path = params.get("rootFolderPath")
    if tmdb_id in (None, ""):
        raise ValueError("tmdbId required")
    if not title:
        raise ValueError("title required")
    if quality_profile_id in (None, ""):
        raise ValueError("qualityProfileId required")
    if not root_folder_path:
        raise ValueError("rootFolderPath required")
    try:
        tmdb_id = int(tmdb_id)
        quality_profile_id = int(quality_profile_id)
    except (TypeError, ValueError):
        raise ValueError("tmdbId and qualityProfileId must be integers")
    payload = {
        "tmdbId": tmdb_id,
        "title": title,
        "qualityProfileId": quality_profile_id,
        "rootFolderPath": root_folder_path,
        "monitored": bool(params.get("monitored", True)),
        "minimumAvailability": params.get("minimumAvailability") or "released",
        "addOptions": {
            "searchForMovie": bool(params.get("searchForMovie", False)),
        },
    }
    result = request("POST", "/movie", data=payload) or {}
    print(json.dumps({
        "id": result.get("id"),
        "title": result.get("title"),
        "monitored": result.get("monitored"),
        "path": result.get("path"),
        "added": True,
    }))


def set_monitored():
    movie_id = path_id(params.get("movieId"), "movieId")
    monitored = params.get("monitored")
    if not isinstance(monitored, bool):
        raise ValueError("monitored required (true or false)")
    movie = request("GET", f"/movie/{movie_id}") or {}
    movie["monitored"] = monitored
    updated = request("PUT", f"/movie/{movie_id}", data=movie) or {}
    print(json.dumps({
        "id": updated.get("id") or movie.get("id"),
        "title": updated.get("title") or movie.get("title"),
        "monitored": monitored,
        "updated": True,
    }))


def list_quality_profiles():
    result = request("GET", "/qualityprofile") or []
    profiles = [{"id": p.get("id"), "name": p.get("name")} for p in result]
    print(json.dumps({"count": len(profiles), "profiles": profiles}))


def list_root_folders():
    result = request("GET", "/rootfolder") or []
    folders = [{
        "id": f.get("id"),
        "path": f.get("path"),
        "freeSpace": f.get("freeSpace"),
        "accessible": f.get("accessible"),
    } for f in result]
    print(json.dumps({"count": len(folders), "folders": folders}))


HANDLERS = {
    "radarr.search_movie_lookup": search_movie_lookup,
    "radarr.list_movies": list_movies,
    "radarr.get_calendar": get_calendar,
    "radarr.get_queue": get_queue,
    "radarr.get_history": get_history,
    "radarr.add_movie": add_movie,
    "radarr.set_monitored": set_monitored,
    "radarr.list_quality_profiles": list_quality_profiles,
    "radarr.list_root_folders": list_root_folders,
}

try:
    handler = HANDLERS.get(tool_name)
    if handler is None:
        print(json.dumps({"error": f"Unknown tool: {tool_name}"}))
    elif not (base_url and api_key):
        print(json.dumps({"error": "Missing Radarr credentials: connect the Radarr integration first (base_url, api_key)."}))
    else:
        handler()
except (RuntimeError, ValueError) as e:
    print(json.dumps({"error": str(e)}))
except Exception as e:  # noqa: BLE001
    print(json.dumps({"error": f"Unexpected error: {type(e).__name__}: {e}"}))
