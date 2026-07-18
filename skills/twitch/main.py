"""Twitch integration skill — public Helix catalog data via an app access token.

Pure standard library (urllib) so it runs unchanged in the alpine Python sandbox with no pip
dependencies. `params` is injected as a global by the Sophon runtime and carries the tool name,
the tool arguments, and the connection-card fields (client_id, client_secret).

Auth is OAuth2 client-credentials: we POST to https://id.twitch.tv/oauth2/token to mint an app
access token per invocation (sandbox runs are fresh), then call the Helix API at
https://api.twitch.tv/helix with BOTH "Authorization: Bearer <token>" and "Client-Id" headers.
App tokens grant public/catalog data only — no followed channels, subscriptions, or chat.
"""

import json
import urllib.request
import urllib.parse
import urllib.error

tool_name = params.get("tool", "")
client_id = params.get("client_id") or ""
client_secret = params.get("client_secret") or ""

TOKEN_URL = "https://id.twitch.tv/oauth2/token"
HELIX_BASE = "https://api.twitch.tv/helix"
USER_AGENT = "sophon-twitch-skill"


def get_token():
    """Obtain an app access token via the OAuth2 client-credentials grant."""
    form = urllib.parse.urlencode({
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "client_credentials",
    }).encode()
    req = urllib.request.Request(
        TOKEN_URL,
        data=form,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        detail = e.read().decode() if e.fp else ""
        try:
            parsed = json.loads(detail)
            msg = parsed.get("message") or parsed.get("error") or detail
        except (ValueError, TypeError):
            msg = detail
        raise RuntimeError(f"Token request failed ({e.code}): {msg}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Could not reach Twitch: {e.reason}") from e
    token = data.get("access_token")
    if not token:
        raise RuntimeError("No access_token in token response")
    return token


def request(path, token, query=None):
    """Make an authenticated GET request to the Helix API. Returns parsed JSON (or None)."""
    url = f"{HELIX_BASE}{path}"
    if query:
        clean = {k: v for k, v in query.items() if v not in (None, "")}
        if clean:
            url = f"{url}?{urllib.parse.urlencode(clean)}"
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Client-Id": client_id,
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
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
            msg = parsed.get("message") or parsed.get("error") or detail
        except (ValueError, TypeError):
            msg = detail
        if e.code == 429:
            retry_after = e.headers.get("Retry-After") if e.headers else None
            hint = "rate limited, slow down"
            if retry_after:
                hint += f"; retry after {retry_after}s"
            raise RuntimeError(f"Twitch API error 429: {msg} ({hint})") from e
        raise RuntimeError(f"Twitch API error {e.code}: {msg}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Could not reach Twitch: {e.reason}") from e


def clamp(value, default, maximum):
    try:
        return max(1, min(int(value), maximum))
    except (TypeError, ValueError):
        return default


def channel_url(login):
    return f"https://www.twitch.tv/{login}" if login else None


def channel_summary(c):
    login = c.get("broadcaster_login")
    return {
        "id": c.get("id"),
        "broadcaster_login": login,
        "display_name": c.get("display_name"),
        "is_live": c.get("is_live"),
        "game_name": c.get("game_name"),
        "url": channel_url(login),
    }


def stream_summary(s):
    return {
        "user_name": s.get("user_name"),
        "game_name": s.get("game_name"),
        "title": s.get("title"),
        "viewer_count": s.get("viewer_count"),
        "started_at": s.get("started_at"),
        "url": channel_url(s.get("user_login")),
    }


def clip_summary(c):
    return {
        "id": c.get("id"),
        "title": c.get("title"),
        "view_count": c.get("view_count"),
        "url": c.get("url"),
        "creator_name": c.get("creator_name"),
    }


def video_summary(v):
    return {
        "id": v.get("id"),
        "title": v.get("title"),
        "published_at": v.get("published_at"),
        "url": v.get("url"),
        "view_count": v.get("view_count"),
    }


# --- Tool handlers ---------------------------------------------------------

def search_channels():
    query = params.get("query")
    if not query:
        raise ValueError("query required")
    first = clamp(params.get("first", 20), 20, 100)
    q = {"query": query, "first": first}
    live_only = params.get("live_only")
    if live_only is not None:
        q["live_only"] = "true" if live_only else "false"
    token = get_token()
    result = request("/search/channels", token, query=q)
    channels = [channel_summary(c) for c in (result or {}).get("data", [])]
    print(json.dumps({"count": len(channels), "channels": channels}))


def get_streams():
    first = clamp(params.get("first", 20), 20, 100)
    token = get_token()
    result = request("/streams", token, query={
        "game_id": params.get("game_id"),
        "user_login": params.get("user_login"),
        "language": params.get("language"),
        "first": first,
    })
    streams = [stream_summary(s) for s in (result or {}).get("data", [])]
    print(json.dumps({"count": len(streams), "streams": streams}))


def get_top_games():
    first = clamp(params.get("first", 20), 20, 100)
    token = get_token()
    result = request("/games/top", token, query={"first": first})
    games = [{"id": g.get("id"), "name": g.get("name")}
             for g in (result or {}).get("data", [])]
    print(json.dumps({"count": len(games), "games": games}))


def get_clips():
    broadcaster_id = params.get("broadcaster_id")
    game_id = params.get("game_id")
    if not broadcaster_id and not game_id:
        raise ValueError("broadcaster_id or game_id required")
    first = clamp(params.get("first", 20), 20, 100)
    token = get_token()
    result = request("/clips", token, query={
        "broadcaster_id": broadcaster_id,
        "game_id": game_id,
        "first": first,
        "started_at": params.get("started_at"),
        "ended_at": params.get("ended_at"),
    })
    clips = [clip_summary(c) for c in (result or {}).get("data", [])]
    print(json.dumps({"count": len(clips), "clips": clips}))


def get_videos():
    user_id = params.get("user_id")
    if not user_id:
        raise ValueError("user_id required")
    video_type = params.get("type")
    if video_type and video_type not in ("archive", "highlight", "upload"):
        raise ValueError("type must be one of archive, highlight, upload")
    first = clamp(params.get("first", 20), 20, 100)
    token = get_token()
    result = request("/videos", token, query={
        "user_id": user_id,
        "first": first,
        "type": video_type,
    })
    videos = [video_summary(v) for v in (result or {}).get("data", [])]
    print(json.dumps({"count": len(videos), "videos": videos}))


def get_channel_info():
    broadcaster_id = params.get("broadcaster_id")
    if not broadcaster_id:
        raise ValueError("broadcaster_id required")
    token = get_token()
    result = request("/channels", token, query={"broadcaster_id": broadcaster_id})
    data = (result or {}).get("data", [])
    if not data:
        raise RuntimeError(f"No channel found for broadcaster_id {broadcaster_id}")
    c = data[0]
    print(json.dumps({
        "broadcaster_name": c.get("broadcaster_name"),
        "game_name": c.get("game_name"),
        "title": c.get("title"),
        "tags": c.get("tags"),
        "url": channel_url(c.get("broadcaster_login")),
    }))


def get_game():
    name = params.get("name")
    if not name:
        raise ValueError("name required")
    token = get_token()
    result = request("/games", token, query={"name": name})
    data = (result or {}).get("data", [])
    if not data:
        raise RuntimeError(f"Game not found: {name}")
    g = data[0]
    print(json.dumps({
        "id": g.get("id"),
        "name": g.get("name"),
        "box_art_url": g.get("box_art_url"),
    }))


HANDLERS = {
    "twitch.search_channels": search_channels,
    "twitch.get_streams": get_streams,
    "twitch.get_top_games": get_top_games,
    "twitch.get_clips": get_clips,
    "twitch.get_videos": get_videos,
    "twitch.get_channel_info": get_channel_info,
    "twitch.get_game": get_game,
}

try:
    handler = HANDLERS.get(tool_name)
    if handler is None:
        print(json.dumps({"error": f"Unknown tool: {tool_name}"}))
    elif not (client_id and client_secret):
        print(json.dumps({"error": "Missing Twitch credentials: connect the Twitch integration first (client_id, client_secret)."}))
    else:
        handler()
except (RuntimeError, ValueError) as e:
    print(json.dumps({"error": str(e)}))
except Exception as e:  # noqa: BLE001
    print(json.dumps({"error": f"Unexpected error: {type(e).__name__}: {e}"}))
