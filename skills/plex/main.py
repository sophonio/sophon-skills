"""Plex Media Server integration skill — libraries, search, item details, recently added,
On Deck, active sessions, and library scans via the Plex HTTP API.

Pure standard library (urllib) so it runs unchanged in the alpine Python sandbox with no pip
dependencies. `params` is injected as a global by the Sophon runtime and carries the tool name,
the tool arguments, and the connection-card fields (base_url, plex_token).

Auth is a static owner/admin X-Plex-Token sent as the X-Plex-Token header on every request,
together with Accept: application/json (Plex defaults to XML otherwise) and a fixed
X-Plex-Client-Identifier. The base URL is the user's own server (usually a LAN address like
http://192.168.1.50:32400), so the server must be reachable from Sophon's sandbox — LAN-only
servers need a VPN, tunnel, or reverse proxy. All responses arrive wrapped in a MediaContainer
envelope; handlers shape trimmed summaries from it and never return raw payloads.
"""

import json
import urllib.request
import urllib.parse
import urllib.error

tool_name = params.get("tool", "")
base_url = (params.get("base_url") or "").rstrip("/")
plex_token = params.get("plex_token") or ""

CLIENT_IDENTIFIER = "sophon-plex-skill"


def request(method, path, query=None, extra_headers=None):
    """Make an authenticated request to the Plex server. Returns parsed JSON (or None for empty)."""
    url = f"{base_url}{path}"
    if query:
        clean = {k: v for k, v in query.items() if v not in (None, "")}
        if clean:
            url = f"{url}?{urllib.parse.urlencode(clean)}"
    headers = {
        "X-Plex-Token": plex_token,
        "Accept": "application/json",
        "X-Plex-Client-Identifier": CLIENT_IDENTIFIER,
        "User-Agent": "sophon-plex-skill",
    }
    if extra_headers:
        headers.update(extra_headers)
    req = urllib.request.Request(url, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            text = resp.read().decode(errors="replace")
            if not text:
                return None
            try:
                return json.loads(text)
            except ValueError:
                # Refresh/scan endpoints and error pages can return XML/plain text.
                return None
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace") if e.fp else ""
        try:
            parsed = json.loads(detail)
            msg = ((parsed.get("errors") or [{}])[0].get("message")
                   if isinstance(parsed.get("errors"), list) else None) or detail
        except (ValueError, TypeError):
            # Plex error bodies are usually XML/HTML — keep only a short hint.
            msg = detail[:200]
        if e.code == 401:
            msg = msg or "unauthorized — check your plex_token (X-Plex-Token)"
        elif e.code == 404:
            msg = msg or "not found — check the ratingKey / section id"
        elif e.code == 429:
            retry_after = e.headers.get("Retry-After")
            hint = "rate limited, slow down"
            if retry_after:
                hint = f"{hint} (retry after {retry_after}s)"
            msg = f"{msg or ''} {hint}".strip()
        raise RuntimeError(f"Plex API error {e.code}: {msg}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(
            "Could not reach your Plex server (is it reachable from Sophon's sandbox? "
            f"LAN-only servers need a VPN, tunnel, or reverse proxy): {e.reason}"
        ) from e


def clamp(value, default, maximum):
    try:
        return max(1, min(int(value), maximum))
    except (TypeError, ValueError):
        return default


def safe_segment(value, name):
    """Validate and URL-quote a params-derived path segment (ratingKey / section id)."""
    s = str(value if value is not None else "").strip()
    if not s:
        raise ValueError(f"{name} required")
    if s in (".", ".."):
        raise ValueError(f"{name} must not be '.' or '..'")
    return urllib.parse.quote(s, safe="")


def media_container(result):
    return (result or {}).get("MediaContainer") or {}


def item_summary(m):
    return {
        "ratingKey": m.get("ratingKey"),
        "title": m.get("title"),
        "type": m.get("type"),
        "year": m.get("year"),
        "librarySectionTitle": m.get("librarySectionTitle"),
    }


def library_summary(d):
    return {
        "key": d.get("key"),
        "title": d.get("title"),
        "type": d.get("type"),
        "agent": d.get("agent"),
    }


def media_summary(m):
    return {
        "videoResolution": m.get("videoResolution"),
        "videoCodec": m.get("videoCodec"),
        "audioCodec": m.get("audioCodec"),
        "audioChannels": m.get("audioChannels"),
        "container": m.get("container"),
        "bitrate": m.get("bitrate"),
    }


def session_summary(m):
    duration = m.get("duration")
    view_offset = m.get("viewOffset")
    progress = None
    if isinstance(duration, int) and duration > 0 and isinstance(view_offset, int):
        progress = round(min(view_offset, duration) / duration * 100, 1)
    player = m.get("Player") or {}
    return {
        "user": (m.get("User") or {}).get("title"),
        "title": m.get("title"),
        "grandparentTitle": m.get("grandparentTitle"),
        "type": m.get("type"),
        "player": {"product": player.get("product"), "state": player.get("state")},
        "progressPercent": progress,
    }


# --- Tool handlers ---------------------------------------------------------

def search_library():
    query = params.get("query")
    if not query:
        raise ValueError("query required")
    section_id = params.get("sectionId")
    limit = clamp(params.get("limit", 25), 25, 100)
    if section_id not in (None, ""):
        path = f"/library/sections/{safe_segment(section_id, 'sectionId')}/search"
    else:
        path = "/search"
    result = request("GET", path, query={"query": query, "limit": limit})
    items = [item_summary(m) for m in (media_container(result).get("Metadata") or [])][:limit]
    print(json.dumps({"count": len(items), "results": items}))


def get_item_details():
    rating_key = safe_segment(params.get("ratingKey"), "ratingKey")
    result = request("GET", f"/library/metadata/{rating_key}")
    metadata = media_container(result).get("Metadata") or []
    if not metadata:
        raise RuntimeError("Item not found — check the ratingKey")
    m = metadata[0]
    print(json.dumps({
        "ratingKey": m.get("ratingKey"),
        "title": m.get("title"),
        "type": m.get("type"),
        "year": m.get("year"),
        "summary": m.get("summary"),
        "duration": m.get("duration"),
        "rating": m.get("rating"),
        "contentRating": m.get("contentRating"),
        "librarySectionTitle": m.get("librarySectionTitle"),
        "media": [media_summary(md) for md in (m.get("Media") or [])],
    }))


def list_libraries():
    result = request("GET", "/library/sections")
    libraries = [library_summary(d) for d in (media_container(result).get("Directory") or [])]
    print(json.dumps({"count": len(libraries), "libraries": libraries}))


def get_recently_added():
    section_id = params.get("sectionId")
    limit = clamp(params.get("limit", 25), 25, 100)
    if section_id not in (None, ""):
        path = f"/library/sections/{safe_segment(section_id, 'sectionId')}/recentlyAdded"
    else:
        path = "/library/recentlyAdded"
    result = request("GET", path, extra_headers={
        "X-Plex-Container-Start": "0",
        "X-Plex-Container-Size": str(limit),
    })
    items = []
    for m in (media_container(result).get("Metadata") or [])[:limit]:
        entry = item_summary(m)
        entry["addedAt"] = m.get("addedAt")
        items.append(entry)
    print(json.dumps({"count": len(items), "items": items}))


def get_active_sessions():
    result = request("GET", "/status/sessions")
    sessions = [session_summary(m) for m in (media_container(result).get("Metadata") or [])]
    print(json.dumps({"count": len(sessions), "sessions": sessions}))


def get_on_deck():
    result = request("GET", "/library/onDeck")
    items = []
    for m in media_container(result).get("Metadata") or []:
        entry = item_summary(m)
        entry["grandparentTitle"] = m.get("grandparentTitle")
        entry["viewOffset"] = m.get("viewOffset")
        items.append(entry)
    print(json.dumps({"count": len(items), "items": items}))


def scan_library_section():
    raw_id = params.get("sectionId")
    section_id = safe_segment(raw_id, "sectionId")
    request("GET", f"/library/sections/{section_id}/refresh")
    print(json.dumps({"scanning": True, "sectionKey": str(raw_id).strip()}))


HANDLERS = {
    "plex.search_library": search_library,
    "plex.get_item_details": get_item_details,
    "plex.list_libraries": list_libraries,
    "plex.get_recently_added": get_recently_added,
    "plex.get_active_sessions": get_active_sessions,
    "plex.get_on_deck": get_on_deck,
    "plex.scan_library_section": scan_library_section,
}

try:
    handler = HANDLERS.get(tool_name)
    if handler is None:
        print(json.dumps({"error": f"Unknown tool: {tool_name}"}))
    elif not (base_url and plex_token):
        print(json.dumps({"error": "Missing Plex credentials: connect the Plex integration first (base_url, plex_token)."}))
    else:
        handler()
except (RuntimeError, ValueError) as e:
    print(json.dumps({"error": str(e)}))
except Exception as e:  # noqa: BLE001
    print(json.dumps({"error": f"Unexpected error: {type(e).__name__}: {e}"}))
