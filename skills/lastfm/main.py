"""Last.fm integration skill — music metadata and listening history via the Last.fm API.

Pure standard library (urllib) so it runs unchanged in the alpine Python sandbox with no pip
dependencies. `params` is injected as a global by the Sophon runtime and carries the tool name,
the tool arguments, and the connection-card fields (api_key, default_username).

Auth is a static API key sent as ?api_key={api_key}&format=json query parameters on
https://ws.audioscrobbler.com/2.0/. Read-only public methods only — no scrobbling or session
auth. Last.fm reports many failures as HTTP 200 with a JSON body shaped
{"error": N, "message": "..."} — we detect that envelope and surface it as an error.

Music data provided by Last.fm (https://www.last.fm).
"""

import json
import urllib.request
import urllib.parse
import urllib.error

tool_name = params.get("tool", "")
api_key = params.get("api_key") or ""
default_username = params.get("default_username") or ""

API_BASE = "https://ws.audioscrobbler.com/2.0/"

PERIODS = ("7day", "1month", "3month", "6month", "12month", "overall")


def request(api_method, query=None):
    """GET a Last.fm API method. Returns parsed JSON; raises RuntimeError on any API error."""
    q = {"method": api_method}
    for key, value in (query or {}).items():
        if value not in (None, ""):
            q[key] = value
    q["api_key"] = api_key
    q["format"] = "json"
    url = f"{API_BASE}?{urllib.parse.urlencode(q)}"
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "sophon-lastfm-skill",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read().decode()
    except urllib.error.HTTPError as e:
        detail = e.read().decode() if e.fp else ""
        try:
            parsed = json.loads(detail)
            msg = parsed.get("message") or detail
        except (ValueError, TypeError, AttributeError):
            msg = detail
        if e.code == 429:
            retry_after = e.headers.get("Retry-After")
            hint = " (rate limited, slow down"
            hint += f"; retry after {retry_after}s)" if retry_after else ")"
            raise RuntimeError(f"Last.fm API error 429: {msg}{hint}") from e
        raise RuntimeError(f"Last.fm API error {e.code}: {msg}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Could not reach Last.fm: {e.reason}") from e
    if not raw:
        return None
    try:
        data = json.loads(raw)
    except ValueError:
        raise RuntimeError("Last.fm returned a non-JSON response")
    # Last.fm signals errors as HTTP 200 with {"error": N, "message": "..."}.
    if isinstance(data, dict) and data.get("error") is not None:
        raise RuntimeError(
            f"Last.fm API error {data.get('error')}: {data.get('message') or 'unknown error'}")
    return data


def clamp(value, default, maximum):
    try:
        return max(1, min(int(value), maximum))
    except (TypeError, ValueError):
        return default


def as_list(value):
    """Last.fm collapses single-item lists to a bare object; normalize to a list."""
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def require_username():
    username = params.get("username") or default_username
    if not username:
        raise ValueError(
            "username required: pass a username or set default_username on the Last.fm connection")
    return username


def artist_name(value):
    """Artist field may be a plain string, {'#text': ...}, or {'name': ...}."""
    if isinstance(value, dict):
        return value.get("name") or value.get("#text")
    return value


# --- Tool handlers ---------------------------------------------------------

def get_artist_info():
    artist = params.get("artist")
    if not artist:
        raise ValueError("artist required")
    data = request("artist.getinfo", {"artist": artist}) or {}
    a = data.get("artist") or {}
    stats = a.get("stats") or {}
    tags = [t.get("name") for t in as_list((a.get("tags") or {}).get("tag"))
            if isinstance(t, dict) and t.get("name")]
    bio = ((a.get("bio") or {}).get("summary") or "").strip()
    print(json.dumps({
        "name": a.get("name"),
        "url": a.get("url"),
        "listeners": stats.get("listeners"),
        "playcount": stats.get("playcount"),
        "tags": tags,
        "bio": bio,
    }))


def get_similar_artists():
    artist = params.get("artist")
    if not artist:
        raise ValueError("artist required")
    limit = clamp(params.get("limit", 10), 10, 50)
    data = request("artist.getsimilar", {"artist": artist, "limit": limit}) or {}
    artists = [{
        "name": a.get("name"),
        "match": a.get("match"),
        "url": a.get("url"),
    } for a in as_list((data.get("similarartists") or {}).get("artist"))]
    print(json.dumps({"artist": artist, "count": len(artists), "artists": artists}))


def get_artist_top_tracks():
    artist = params.get("artist")
    if not artist:
        raise ValueError("artist required")
    limit = clamp(params.get("limit", 10), 10, 50)
    data = request("artist.gettoptracks", {"artist": artist, "limit": limit}) or {}
    tracks = [{
        "name": t.get("name"),
        "playcount": t.get("playcount"),
        "listeners": t.get("listeners"),
        "url": t.get("url"),
    } for t in as_list((data.get("toptracks") or {}).get("track"))]
    print(json.dumps({"artist": artist, "count": len(tracks), "tracks": tracks}))


def search_tracks():
    track = params.get("track")
    if not track:
        raise ValueError("track required")
    limit = clamp(params.get("limit", 10), 10, 50)
    data = request("track.search", {"track": track, "limit": limit}) or {}
    matches = ((data.get("results") or {}).get("trackmatches") or {}).get("track")
    tracks = [{
        "name": t.get("name"),
        "artist": artist_name(t.get("artist")),
        "listeners": t.get("listeners"),
        "url": t.get("url"),
    } for t in as_list(matches)]
    print(json.dumps({"count": len(tracks), "tracks": tracks}))


def get_tag_top_artists():
    tag = params.get("tag")
    if not tag:
        raise ValueError("tag required")
    limit = clamp(params.get("limit", 10), 10, 50)
    data = request("tag.gettopartists", {"tag": tag, "limit": limit}) or {}
    artists = [{
        "name": a.get("name"),
        "url": a.get("url"),
    } for a in as_list((data.get("topartists") or {}).get("artist"))]
    print(json.dumps({"tag": tag, "count": len(artists), "artists": artists}))


def get_chart_top_artists():
    limit = clamp(params.get("limit", 10), 10, 50)
    data = request("chart.gettopartists", {"limit": limit}) or {}
    artists = [{
        "name": a.get("name"),
        "playcount": a.get("playcount"),
        "listeners": a.get("listeners"),
        "url": a.get("url"),
    } for a in as_list((data.get("artists") or {}).get("artist"))]
    print(json.dumps({"count": len(artists), "artists": artists}))


def get_user_recent_tracks():
    username = require_username()
    limit = clamp(params.get("limit", 10), 10, 50)
    data = request("user.getrecenttracks", {"user": username, "limit": limit}) or {}
    tracks = []
    for t in as_list((data.get("recenttracks") or {}).get("track")):
        nowplaying = ((t.get("@attr") or {}).get("nowplaying")) == "true"
        tracks.append({
            "name": t.get("name"),
            "artist": artist_name(t.get("artist")),
            "date": (t.get("date") or {}).get("#text"),
            "nowplaying": nowplaying,
            "url": t.get("url"),
        })
    print(json.dumps({"user": username, "count": len(tracks), "tracks": tracks}))


def get_user_top_artists():
    username = require_username()
    period = params.get("period") or "overall"
    if period not in PERIODS:
        raise ValueError(f"period must be one of: {', '.join(PERIODS)}")
    limit = clamp(params.get("limit", 10), 10, 50)
    data = request("user.gettopartists", {"user": username, "period": period,
                                          "limit": limit}) or {}
    artists = [{
        "name": a.get("name"),
        "playcount": a.get("playcount"),
        "url": a.get("url"),
    } for a in as_list((data.get("topartists") or {}).get("artist"))]
    print(json.dumps({"user": username, "period": period, "count": len(artists),
                      "artists": artists}))


HANDLERS = {
    "lastfm.get_artist_info": get_artist_info,
    "lastfm.get_similar_artists": get_similar_artists,
    "lastfm.get_artist_top_tracks": get_artist_top_tracks,
    "lastfm.search_tracks": search_tracks,
    "lastfm.get_tag_top_artists": get_tag_top_artists,
    "lastfm.get_chart_top_artists": get_chart_top_artists,
    "lastfm.get_user_recent_tracks": get_user_recent_tracks,
    "lastfm.get_user_top_artists": get_user_top_artists,
}

try:
    handler = HANDLERS.get(tool_name)
    if handler is None:
        print(json.dumps({"error": f"Unknown tool: {tool_name}"}))
    elif not api_key:
        print(json.dumps({"error": "Missing Last.fm credentials: connect the Last.fm integration first (api_key)."}))
    else:
        handler()
except (RuntimeError, ValueError) as e:
    print(json.dumps({"error": str(e)}))
except Exception as e:  # noqa: BLE001
    print(json.dumps({"error": f"Unexpected error: {type(e).__name__}: {e}"}))
