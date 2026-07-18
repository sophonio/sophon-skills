"""Sonarr integration skill — TV series management on a self-hosted Sonarr v3+ server.

Pure standard library (urllib) so it runs unchanged in the alpine Python sandbox with no pip
dependencies. `params` is injected as a global by the Sophon runtime and carries the tool name,
the tool arguments, and the connection-card fields (base_url, api_key).

Auth is Sonarr's static per-instance API key sent as the `X-Api-Key` header on every request.
All endpoints live under {base_url}/api/v3. Sonarr is self-hosted: the server must be reachable
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
    """Make an authenticated request to Sonarr. Returns parsed JSON (or None for 204/empty)."""
    url = f"{base_url}{API}{path}"
    if query:
        clean = {k: v for k, v in query.items() if v not in (None, "")}
        if clean:
            url = f"{url}?{urllib.parse.urlencode(clean)}"
    body = json.dumps(data).encode() if data is not None else None
    headers = {
        "X-Api-Key": api_key,
        "Accept": "application/json",
        "User-Agent": "sophon-sonarr-skill",
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
                # Sonarr validation errors are a list of {propertyName, errorMessage}.
                msg = "; ".join(
                    str((p or {}).get("errorMessage") or p) for p in parsed
                ) or detail[:200]
            elif isinstance(parsed, dict):
                msg = parsed.get("message") or parsed.get("error") or detail[:200]
            else:
                msg = detail[:200]
        except (ValueError, TypeError):
            # Sonarr error pages can be HTML — keep only a short hint.
            msg = detail[:200]
        if e.code == 401:
            msg = msg or "authentication failed — check the API key (Sonarr Settings > General > Security)"
        elif e.code == 429:
            retry_after = e.headers.get("Retry-After")
            msg = f"{msg or 'too many requests'} — rate limited, slow down"
            if retry_after:
                msg += f" (retry after {retry_after}s)"
        raise RuntimeError(f"Sonarr API error {e.code}: {msg}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(
            "Could not reach your Sonarr server (it may not be reachable from Sophon's sandbox — "
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


def series_summary(s):
    stats = s.get("statistics") or {}
    return {
        "id": s.get("id"),
        "title": s.get("title"),
        "monitored": s.get("monitored"),
        "status": s.get("status"),
        "tvdbId": s.get("tvdbId"),
        "episodeCount": stats.get("episodeCount"),
        "episodeFileCount": stats.get("episodeFileCount"),
    }


def episode_summary(ep):
    return {
        "series": (ep.get("series") or {}).get("title"),
        "title": ep.get("title"),
        "seasonNumber": ep.get("seasonNumber"),
        "episodeNumber": ep.get("episodeNumber"),
        "airDate": ep.get("airDateUtc") or ep.get("airDate"),
    }


# --- Tool handlers ---------------------------------------------------------

def search_series_lookup():
    term = params.get("term")
    if not term:
        raise ValueError("term required")
    result = request("GET", "/series/lookup", query={"term": term}) or []
    series = [{
        "title": s.get("title"),
        "year": s.get("year"),
        "tvdbId": s.get("tvdbId"),
        "overview": (s.get("overview") or "")[:500],
    } for s in result]
    print(json.dumps({"count": len(series), "series": series}))


def list_series():
    result = request("GET", "/series") or []
    series = [series_summary(s) for s in result]
    print(json.dumps({"count": len(series), "series": series}))


def get_calendar():
    result = request("GET", "/calendar", query={
        "start": params.get("start"),
        "end": params.get("end"),
        "includeSeries": "true",
    }) or []
    episodes = []
    for ep in result:
        item = episode_summary(ep)
        item["monitored"] = ep.get("monitored")
        episodes.append(item)
    print(json.dumps({"count": len(episodes), "episodes": episodes}))


def get_missing():
    page = clamp(params.get("page", 1), 1, 100000)
    page_size = clamp(params.get("pageSize", 20), 20, 100)
    result = request("GET", "/wanted/missing", query={
        "page": page,
        "pageSize": page_size,
        "includeSeries": "true",
    }) or {}
    episodes = [episode_summary(r) for r in result.get("records") or []]
    print(json.dumps({
        "page": result.get("page"),
        "totalRecords": result.get("totalRecords"),
        "count": len(episodes),
        "episodes": episodes,
    }))


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


def add_series():
    tvdb_id = params.get("tvdbId")
    title = params.get("title")
    quality_profile_id = params.get("qualityProfileId")
    root_folder_path = params.get("rootFolderPath")
    if tvdb_id in (None, ""):
        raise ValueError("tvdbId required")
    if not title:
        raise ValueError("title required")
    if quality_profile_id in (None, ""):
        raise ValueError("qualityProfileId required")
    if not root_folder_path:
        raise ValueError("rootFolderPath required")
    try:
        tvdb_id = int(tvdb_id)
        quality_profile_id = int(quality_profile_id)
    except (TypeError, ValueError):
        raise ValueError("tvdbId and qualityProfileId must be integers")
    payload = {
        "tvdbId": tvdb_id,
        "title": title,
        "qualityProfileId": quality_profile_id,
        "rootFolderPath": root_folder_path,
        "monitored": bool(params.get("monitored", True)),
        "addOptions": {
            "searchForMissingEpisodes": bool(params.get("searchForMissingEpisodes", False)),
        },
    }
    if params.get("languageProfileId") is not None:
        try:
            payload["languageProfileId"] = int(params["languageProfileId"])
        except (TypeError, ValueError):
            raise ValueError("languageProfileId must be an integer")
    if params.get("seasons"):
        if not isinstance(params["seasons"], list):
            raise ValueError("seasons must be an array of {seasonNumber, monitored} objects")
        payload["seasons"] = params["seasons"]
    result = request("POST", "/series", data=payload) or {}
    print(json.dumps({
        "id": result.get("id"),
        "title": result.get("title"),
        "monitored": result.get("monitored"),
        "path": result.get("path"),
        "added": True,
    }))


def set_season_monitored():
    series_id = path_id(params.get("seriesId"), "seriesId")
    monitored = params.get("monitored")
    if not isinstance(monitored, bool):
        raise ValueError("monitored required (true or false)")
    series = request("GET", f"/series/{series_id}") or {}
    season_number = params.get("seasonNumber")
    if season_number is None:
        series["monitored"] = monitored
        scope = "series"
    else:
        try:
            season_number = int(season_number)
        except (TypeError, ValueError):
            raise ValueError("seasonNumber must be an integer")
        target = next(
            (s for s in series.get("seasons") or [] if s.get("seasonNumber") == season_number),
            None,
        )
        if target is None:
            raise ValueError(f"season {season_number} not found on series {params.get('seriesId')}")
        target["monitored"] = monitored
        scope = f"season {season_number}"
    updated = request("PUT", f"/series/{series_id}", data=series) or {}
    print(json.dumps({
        "id": updated.get("id") or series.get("id"),
        "title": updated.get("title") or series.get("title"),
        "scope": scope,
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
    "sonarr.search_series_lookup": search_series_lookup,
    "sonarr.list_series": list_series,
    "sonarr.get_calendar": get_calendar,
    "sonarr.get_missing": get_missing,
    "sonarr.get_queue": get_queue,
    "sonarr.add_series": add_series,
    "sonarr.set_season_monitored": set_season_monitored,
    "sonarr.list_quality_profiles": list_quality_profiles,
    "sonarr.list_root_folders": list_root_folders,
}

try:
    handler = HANDLERS.get(tool_name)
    if handler is None:
        print(json.dumps({"error": f"Unknown tool: {tool_name}"}))
    elif not (base_url and api_key):
        print(json.dumps({"error": "Missing Sonarr credentials: connect the Sonarr integration first (base_url, api_key)."}))
    else:
        handler()
except (RuntimeError, ValueError) as e:
    print(json.dumps({"error": str(e)}))
except Exception as e:  # noqa: BLE001
    print(json.dumps({"error": f"Unexpected error: {type(e).__name__}: {e}"}))
