"""Jellyfin integration skill — search and inspect a self-hosted Jellyfin media server.

Pure standard library (urllib) so it runs unchanged in the alpine Python sandbox with no pip
dependencies. `params` is injected as a global by the Sophon runtime and carries the tool name,
the tool arguments, and the connection-card fields (base_url, api_key, default_user_id).

Auth is a static Jellyfin API key sent in the modern header form
`Authorization: MediaBrowser Token="<key>", Client="sophon", ...` (the legacy X-Emby-Token /
api_key query forms are being removed in Jellyfin 12). API keys are admin-scoped, so this skill
stays read-only plus low-risk metadata/library refreshes. Jellyfin is self-hosted: the server
must be reachable from Sophon's sandbox (LAN-only or VPN-only instances need a proxy or tunnel).
"""

import json
import urllib.request
import urllib.parse
import urllib.error

tool_name = params.get("tool", "")
base_url = (params.get("base_url") or "").rstrip("/")
api_key = params.get("api_key") or ""
default_user_id = params.get("default_user_id") or ""

AUTH_HEADER = (
    f'MediaBrowser Token="{api_key}", Client="sophon", Device="sophon", '
    f'DeviceId="sophon-jellyfin", Version="1.0"'
)


def request(method, path, data=None, query=None):
    """Make an authenticated request to Jellyfin. Returns parsed JSON (or None for 204/empty)."""
    url = f"{base_url}{path}"
    if query:
        clean = {k: v for k, v in query.items() if v not in (None, "")}
        if clean:
            url = f"{url}?{urllib.parse.urlencode(clean)}"
    body = json.dumps(data).encode() if data is not None else None
    headers = {
        "Authorization": AUTH_HEADER,
        "Accept": "application/json",
        "User-Agent": "sophon-jellyfin-skill",
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
            msg = (parsed.get("message") or parsed.get("error") or detail[:200]) \
                if isinstance(parsed, dict) else detail[:200]
        except (ValueError, TypeError):
            msg = detail[:200]
        if e.code in (401, 403):
            msg = msg or "authentication failed — check the API key (Dashboard > API Keys)"
        elif e.code == 429:
            retry_after = e.headers.get("Retry-After")
            msg = f"{msg or 'too many requests'} — rate limited, slow down"
            if retry_after:
                msg += f" (retry after {retry_after}s)"
        raise RuntimeError(f"Jellyfin API error {e.code}: {msg}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(
            "Could not reach your Jellyfin server (it may not be reachable from Sophon's sandbox — "
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


def item_summary(it):
    return {
        "id": it.get("Id"),
        "name": it.get("Name"),
        "type": it.get("Type"),
        "year": it.get("ProductionYear"),
        "seriesName": it.get("SeriesName"),
    }


# --- Tool handlers ---------------------------------------------------------

def search_library():
    term = params.get("searchTerm")
    if not term:
        raise ValueError("searchTerm required")
    limit = clamp(params.get("limit", 25), 25, 100)
    query = {
        "searchTerm": term,
        "recursive": "true",
        "limit": limit,
    }
    include = params.get("includeItemTypes")
    if include:
        query["includeItemTypes"] = include
    result = request("GET", "/Items", query=query) or {}
    items = [item_summary(it) for it in result.get("Items") or []]
    print(json.dumps({"count": len(items), "items": items}))


def get_item():
    item_id = path_id(params.get("itemId"), "itemId")
    user_id = params.get("userId") or default_user_id
    if user_id:
        path = f"/Users/{path_id(user_id, 'userId')}/Items/{item_id}"
    else:
        path = f"/Items/{item_id}"
    it = request("GET", path) or {}
    people = [{
        "name": p.get("Name"),
        "role": p.get("Role"),
        "type": p.get("Type"),
    } for p in (it.get("People") or [])[:20]]
    streams = [{
        "type": s.get("Type"),
        "codec": s.get("Codec"),
        "language": s.get("Language"),
        "displayTitle": s.get("DisplayTitle"),
    } for s in (it.get("MediaStreams") or [])]
    print(json.dumps({
        "id": it.get("Id"),
        "name": it.get("Name"),
        "type": it.get("Type"),
        "year": it.get("ProductionYear"),
        "overview": it.get("Overview"),
        "genres": it.get("Genres"),
        "runTimeTicks": it.get("RunTimeTicks"),
        "people": people,
        "mediaStreams": streams,
    }))


def list_libraries():
    result = request("GET", "/Library/VirtualFolders") or []
    libraries = [{
        "name": lib.get("Name"),
        "itemId": lib.get("ItemId"),
        "collectionType": lib.get("CollectionType"),
        "locations": lib.get("Locations"),
    } for lib in result]
    counts = request("GET", "/Items/Counts") or {}
    print(json.dumps({"count": len(libraries), "libraries": libraries, "totals": counts}))


def get_recently_added():
    limit = clamp(params.get("limit", 20), 20, 100)
    query = {"limit": limit}
    if params.get("parentId"):
        query["parentId"] = params["parentId"]
    result = request("GET", "/Items/Latest", query=query) or []
    items = [item_summary(it) for it in result]
    print(json.dumps({"count": len(items), "items": items}))


def get_active_sessions():
    result = request("GET", "/Sessions") or []
    sessions = []
    for s in result:
        now = s.get("NowPlayingItem") or {}
        play = s.get("PlayState") or {}
        sessions.append({
            "userName": s.get("UserName"),
            "client": s.get("Client"),
            "deviceName": s.get("DeviceName"),
            "nowPlaying": now.get("Name"),
            "isPaused": play.get("IsPaused"),
        })
    print(json.dumps({"count": len(sessions), "sessions": sessions}))


def get_next_up():
    user_id = params.get("userId") or default_user_id
    if not user_id:
        raise ValueError(
            "userId required (set default_user_id on the connection card or pass userId; "
            "find ids via jellyfin session data or the Jellyfin dashboard)"
        )
    limit = clamp(params.get("limit", 20), 20, 100)
    result = request("GET", "/Shows/NextUp", query={
        "userId": user_id,
        "limit": limit,
    }) or {}
    items = []
    for it in result.get("Items") or []:
        items.append({
            "id": it.get("Id"),
            "seriesName": it.get("SeriesName"),
            "name": it.get("Name"),
            "seasonNumber": it.get("ParentIndexNumber"),
            "episodeNumber": it.get("IndexNumber"),
        })
    print(json.dumps({"count": len(items), "items": items}))


def refresh_item_metadata():
    item_id = path_id(params.get("itemId"), "itemId")
    request("POST", f"/Items/{item_id}/Refresh")
    print(json.dumps({"itemId": params.get("itemId"), "refreshTriggered": True}))


def scan_library():
    request("POST", "/Library/Refresh")
    print(json.dumps({"scanTriggered": True}))


HANDLERS = {
    "jellyfin.search_library": search_library,
    "jellyfin.get_item": get_item,
    "jellyfin.list_libraries": list_libraries,
    "jellyfin.get_recently_added": get_recently_added,
    "jellyfin.get_active_sessions": get_active_sessions,
    "jellyfin.get_next_up": get_next_up,
    "jellyfin.refresh_item_metadata": refresh_item_metadata,
    "jellyfin.scan_library": scan_library,
}

try:
    handler = HANDLERS.get(tool_name)
    if handler is None:
        print(json.dumps({"error": f"Unknown tool: {tool_name}"}))
    elif not (base_url and api_key):
        print(json.dumps({"error": "Missing Jellyfin credentials: connect the Jellyfin integration first (base_url, api_key)."}))
    else:
        handler()
except (RuntimeError, ValueError) as e:
    print(json.dumps({"error": str(e)}))
except Exception as e:  # noqa: BLE001
    print(json.dumps({"error": f"Unexpected error: {type(e).__name__}: {e}"}))
