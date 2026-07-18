"""Offline mock-HTTP integration tests for the twitch skill."""
import json
import sys

from mockhttp import run_tool, resp, err, check

TOKEN_URL = "https://id.twitch.tv/oauth2/token"
HELIX = "https://api.twitch.tv/helix"
CID = "cid123abc"
SECRET = "sec-SECRET-789"
APP_TOKEN = "app-tok-XYZ"


def creds(**extra):
    p = {"client_id": CID, "client_secret": SECRET}
    p.update(extra)
    return p


def token_resp():
    return resp(200, body={"access_token": APP_TOKEN, "expires_in": 5011271,
                           "token_type": "bearer"})


ok = True

# ---------------------------------------------------------------------------
# 1. Token flow + auth exactness (search_channels happy path)
# ---------------------------------------------------------------------------
print("scenario: search_channels — token flow + auth exactness")
out, ex = run_tool("twitch", creds(tool="twitch.search_channels", query="ann"), [
    token_resp(),
    resp(200, body={"data": [
        {"id": "12345", "broadcaster_login": "annchannel", "display_name": "AnnChannel",
         "is_live": True, "game_name": "Hades", "game_id": "512980",
         "thumbnail_url": "https://x/thumb.png", "tag_ids": ["t1"],
         "broadcaster_language": "en", "started_at": "2026-07-18T10:00:00Z"},
        {"id": "67890", "broadcaster_login": "annika", "display_name": "Annika",
         "is_live": False, "game_name": "", "game_id": ""},
    ]}),
])
ok &= check("two requests made (token then helix)", len(ex) == 2, repr(ex))
ok &= check("token request is POST to id.twitch.tv",
            ex[0].method == "POST" and ex[0].url == TOKEN_URL, repr(ex[0]))
ok &= check("token form body byte-exact (client-credentials grant)",
            ex[0].body == f"client_id={CID}&client_secret={SECRET}"
                          "&grant_type=client_credentials", str(ex[0].body))
ok &= check("token request form content-type",
            ex[0].headers.get("content-type") == "application/x-www-form-urlencoded",
            str(ex[0].headers))
ok &= check("helix method GET", ex[1].method == "GET", ex[1].method)
ok &= check("helix URL byte-exact",
            ex[1].url == f"{HELIX}/search/channels?query=ann&first=20", ex[1].url)
ok &= check("helix sends Authorization: Bearer <app token>",
            ex[1].headers.get("authorization") == f"Bearer {APP_TOKEN}", str(ex[1].headers))
ok &= check("helix sends Client-Id header too",
            ex[1].headers.get("client-id") == CID, str(ex[1].headers))
ok &= check("no body on helix GET", ex[1].body is None, str(ex[1].body))
ok &= check("count == 2", out.get("count") == 2, str(out)[:200])
ok &= check("channel summary shaped with twitch.tv url",
            out["channels"][0] == {"id": "12345", "broadcaster_login": "annchannel",
                                   "display_name": "AnnChannel", "is_live": True,
                                   "game_name": "Hades",
                                   "url": "https://www.twitch.tv/annchannel"},
            str(out["channels"][0]))
ok &= check("raw fields absent (thumbnail_url/tag_ids)",
            "thumbnail_url" not in out["channels"][0] and "tag_ids" not in out["channels"][0],
            str(out["channels"][0]))
ok &= check("client_secret not echoed in output", SECRET not in json.dumps(out))

print("scenario: search_channels live_only + first clamp <= 100")
out, ex = run_tool("twitch", creds(tool="twitch.search_channels", query="chess",
                                   live_only=True, first=500), [
    token_resp(),
    resp(200, body={"data": []}),
])
ok &= check("first clamped to 100 and live_only=true",
            ex[1].url == f"{HELIX}/search/channels?query=chess&first=100&live_only=true",
            ex[1].url)
ok &= check("empty result count 0", out == {"count": 0, "channels": []}, str(out))

# ---------------------------------------------------------------------------
# 2. twitch.get_streams — happy path
# ---------------------------------------------------------------------------
print("scenario: get_streams happy path")
out, ex = run_tool("twitch", creds(tool="twitch.get_streams", game_id="512980",
                                   language="en", first=5), [
    token_resp(),
    resp(200, body={"data": [
        {"id": "s1", "user_id": "111", "user_login": "speedster",
         "user_name": "Speedster", "game_id": "512980", "game_name": "Hades",
         "type": "live", "title": "1BC any% runs", "viewer_count": 4321,
         "started_at": "2026-07-18T09:00:00Z", "language": "en",
         "thumbnail_url": "https://x/t.png", "tags": ["Speedrun"]},
    ]}),
])
ok &= check("URL byte-exact (empty user_login dropped)",
            ex[1].url == f"{HELIX}/streams?game_id=512980&language=en&first=5", ex[1].url)
ok &= check("stream summary shaped",
            out == {"count": 1, "streams": [{"user_name": "Speedster", "game_name": "Hades",
                                             "title": "1BC any% runs", "viewer_count": 4321,
                                             "started_at": "2026-07-18T09:00:00Z",
                                             "url": "https://www.twitch.tv/speedster"}]},
            str(out))

# ---------------------------------------------------------------------------
# 3. twitch.get_top_games — happy path
# ---------------------------------------------------------------------------
print("scenario: get_top_games happy path")
out, ex = run_tool("twitch", creds(tool="twitch.get_top_games"), [
    token_resp(),
    resp(200, body={"data": [
        {"id": "509658", "name": "Just Chatting",
         "box_art_url": "https://x/jc.jpg", "igdb_id": ""},
        {"id": "512980", "name": "Hades", "box_art_url": "https://x/h.jpg"},
    ]}),
])
ok &= check("URL byte-exact with default first",
            ex[1].url == f"{HELIX}/games/top?first=20", ex[1].url)
ok &= check("games shaped to id+name only",
            out == {"count": 2, "games": [{"id": "509658", "name": "Just Chatting"},
                                          {"id": "512980", "name": "Hades"}]},
            str(out))

# ---------------------------------------------------------------------------
# 4. twitch.get_game — name resolution
# ---------------------------------------------------------------------------
print("scenario: get_game resolves name to id + box art")
out, ex = run_tool("twitch", creds(tool="twitch.get_game", name="Sea of Stars"), [
    token_resp(),
    resp(200, body={"data": [{"id": "271304", "name": "Sea of Stars",
                              "box_art_url": "https://x/sos-{width}x{height}.jpg",
                              "igdb_id": "119171"}]}),
])
ok &= check("URL byte-exact (name encoded)",
            ex[1].url == f"{HELIX}/games?name=Sea+of+Stars", ex[1].url)
ok &= check("game shaped",
            out == {"id": "271304", "name": "Sea of Stars",
                    "box_art_url": "https://x/sos-{width}x{height}.jpg"}, str(out))

print("scenario: get_game not found -> friendly error")
out, ex = run_tool("twitch", creds(tool="twitch.get_game", name="Nope Game"), [
    token_resp(),
    resp(200, body={"data": []}),
])
ok &= check("not-found error", out.get("error") == "Game not found: Nope Game", str(out))

# ---------------------------------------------------------------------------
# 5. twitch.get_clips — window + required-one-of
# ---------------------------------------------------------------------------
print("scenario: get_clips happy path with time window")
out, ex = run_tool("twitch", creds(tool="twitch.get_clips", broadcaster_id="141981764",
                                   started_at="2026-07-01T00:00:00Z"), [
    token_resp(),
    resp(200, body={"data": [
        {"id": "ClipSlug", "url": "https://clips.twitch.tv/ClipSlug",
         "embed_url": "https://clips.twitch.tv/embed?clip=ClipSlug",
         "broadcaster_id": "141981764", "creator_name": "fanperson",
         "title": "Insane play", "view_count": 999,
         "created_at": "2026-07-02T12:00:00Z", "duration": 28.5}]}),
])
ok &= check("URL byte-exact (started_at encoded, ended_at dropped)",
            ex[1].url == f"{HELIX}/clips?broadcaster_id=141981764&first=20"
                         "&started_at=2026-07-01T00%3A00%3A00Z", ex[1].url)
ok &= check("clip summary shaped with url",
            out == {"count": 1, "clips": [{"id": "ClipSlug", "title": "Insane play",
                                           "view_count": 999,
                                           "url": "https://clips.twitch.tv/ClipSlug",
                                           "creator_name": "fanperson"}]},
            str(out))

print("scenario: get_clips without broadcaster_id or game_id -> no HTTP call")
out, ex = run_tool("twitch", creds(tool="twitch.get_clips"), [])
ok &= check("one-of error", out.get("error") == "broadcaster_id or game_id required", str(out))
ok &= check("no HTTP request made (not even token)", len(ex) == 0, repr(ex))

# ---------------------------------------------------------------------------
# 6. twitch.get_videos — type filter
# ---------------------------------------------------------------------------
print("scenario: get_videos happy path with type filter")
out, ex = run_tool("twitch", creds(tool="twitch.get_videos", user_id="141981764",
                                   type="highlight", first=2), [
    token_resp(),
    resp(200, body={"data": [
        {"id": "v100", "user_id": "141981764", "title": "Finals highlight",
         "published_at": "2026-07-10T00:00:00Z",
         "url": "https://www.twitch.tv/videos/100", "view_count": 555,
         "type": "highlight", "duration": "1h2m3s", "muted_segments": None}]}),
])
ok &= check("URL byte-exact",
            ex[1].url == f"{HELIX}/videos?user_id=141981764&first=2&type=highlight",
            ex[1].url)
ok &= check("video summary shaped",
            out == {"count": 1, "videos": [{"id": "v100", "title": "Finals highlight",
                                            "published_at": "2026-07-10T00:00:00Z",
                                            "url": "https://www.twitch.tv/videos/100",
                                            "view_count": 555}]},
            str(out))

print("scenario: get_videos invalid type -> no HTTP call")
out, ex = run_tool("twitch", creds(tool="twitch.get_videos", user_id="1", type="clip"), [])
ok &= check("invalid type rejected",
            out.get("error") == "type must be one of archive, highlight, upload", str(out))
ok &= check("no HTTP request made", len(ex) == 0, repr(ex))

print("scenario: get_videos missing user_id -> no HTTP call")
out, ex = run_tool("twitch", creds(tool="twitch.get_videos"), [])
ok &= check("user_id required error", out.get("error") == "user_id required", str(out))
ok &= check("no HTTP request made", len(ex) == 0, repr(ex))

# ---------------------------------------------------------------------------
# 7. twitch.get_channel_info — single-object shaping
# ---------------------------------------------------------------------------
print("scenario: get_channel_info happy path")
out, ex = run_tool("twitch", creds(tool="twitch.get_channel_info",
                                   broadcaster_id="141981764"), [
    token_resp(),
    resp(200, body={"data": [
        {"broadcaster_id": "141981764", "broadcaster_login": "twitchdev",
         "broadcaster_name": "TwitchDev", "broadcaster_language": "en",
         "game_id": "509670", "game_name": "Science & Technology",
         "title": "Building with the Helix API",
         "delay": 0, "tags": ["DevsInTheKnow", "English"],
         "content_classification_labels": [], "is_branded_content": False}]}),
])
ok &= check("URL byte-exact",
            ex[1].url == f"{HELIX}/channels?broadcaster_id=141981764", ex[1].url)
ok &= check("channel info shaped with twitch.tv url",
            out == {"broadcaster_name": "TwitchDev", "game_name": "Science & Technology",
                    "title": "Building with the Helix API",
                    "tags": ["DevsInTheKnow", "English"],
                    "url": "https://www.twitch.tv/twitchdev"}, str(out))

# ---------------------------------------------------------------------------
# 8. ERROR PATHS
# ---------------------------------------------------------------------------
print("scenario: 401 on helix call surfaces friendly error")
out, ex = run_tool("twitch", creds(tool="twitch.get_top_games"), [
    token_resp(),
    err(401, body={"error": "Unauthorized", "status": 401,
                   "message": "Invalid OAuth token"}),
])
raw = json.dumps(out)
ok &= check("error key present", "error" in out and isinstance(out["error"], str), raw[:200])
ok &= check("includes HTTP status 401", "401" in out["error"], out.get("error", ""))
ok &= check("includes API message", "Invalid OAuth token" in out["error"],
            out.get("error", ""))
ok &= check("no Python traceback leaked",
            "Traceback" not in raw and "urllib" not in raw and "HTTPError" not in raw,
            raw[:300])
ok &= check("client_secret not leaked in error output", SECRET not in raw, raw[:300])

print("scenario: token endpoint 403 surfaces friendly error, secret not echoed")
out, ex = run_tool("twitch", creds(tool="twitch.search_channels", query="x"), [
    err(403, body={"status": 403, "message": "invalid client secret"}),
])
raw = json.dumps(out)
ok &= check("only the token request was made", len(ex) == 1 and ex[0].url == TOKEN_URL,
            repr(ex))
ok &= check("token failure friendly",
            "Token request failed (403)" in out.get("error", "")
            and "invalid client secret" in out.get("error", ""), out.get("error", ""))
ok &= check("secret absent from token error", SECRET not in raw, raw[:300])
ok &= check("no traceback on token failure", "Traceback" not in raw, raw[:300])

print("scenario: 429 includes Retry-After and slow-down hint")
out, ex = run_tool("twitch", creds(tool="twitch.get_streams"), [
    token_resp(),
    err(429, body={"error": "Too Many Requests", "status": 429,
                   "message": "Too Many Requests"},
        headers={"Retry-After": "27", "Ratelimit-Remaining": "0"}),
])
ok &= check("429 surfaced", "error" in out and "429" in out["error"], str(out)[:300])
ok &= check("rate-limit hint present", "rate limited, slow down" in out["error"],
            out.get("error", ""))
ok &= check("Retry-After value included", "27" in out["error"], out.get("error", ""))

print("scenario: non-JSON error body tolerated")
out, ex = run_tool("twitch", creds(tool="twitch.get_top_games"), [
    token_resp(),
    err(502, body="<html>bad gateway</html>"),
])
ok &= check("502 non-JSON body still friendly",
            "error" in out and "502" in out["error"]
            and "Traceback" not in json.dumps(out), str(out)[:300])

print("scenario: missing credentials -> friendly connect-first error, no HTTP call")
out, ex = run_tool("twitch", {"tool": "twitch.get_top_games",
                              "client_id": "", "client_secret": ""}, [])
ok &= check("connect-first message",
            "error" in out and "connect the twitch integration" in out["error"].lower(),
            str(out))
ok &= check("names the fields", "client_id" in out["error"]
            and "client_secret" in out["error"], out.get("error", ""))
ok &= check("no HTTP request made", len(ex) == 0, repr(ex))

print("scenario: unknown tool -> friendly error")
out, ex = run_tool("twitch", creds(tool="twitch.nope"), [])
ok &= check("unknown tool error", out.get("error") == "Unknown tool: twitch.nope", str(out))

# ---------------------------------------------------------------------------
# 9. SECURITY PROBES
# ---------------------------------------------------------------------------
print("scenario: path-traversal broadcaster_id is percent-encoded into the query string")
evil = "123/../users?x=1"
out, ex = run_tool("twitch", creds(tool="twitch.get_channel_info", broadcaster_id=evil), [
    token_resp(),
    resp(200, body={"data": [{"broadcaster_name": "X", "broadcaster_login": "x",
                              "game_name": "", "title": "", "tags": []}]}),
])
ok &= check("id fully encoded (no path escape, no extra query)",
            ex[1].url == f"{HELIX}/channels?broadcaster_id=123%2F..%2Fusers%3Fx%3D1",
            ex[1].url)
ok &= check("no raw '../' in URL", "../" not in ex[1].url, ex[1].url)

print("scenario: injection attempt in get_clips game_id encoded")
out, ex = run_tool("twitch", creds(tool="twitch.get_clips", game_id="1&first=100#x"), [
    token_resp(),
    resp(200, body={"data": []}),
])
ok &= check("game_id value encoded (no query injection)",
            ex[1].url == f"{HELIX}/clips?game_id=1%26first%3D100%23x&first=20", ex[1].url)

print("scenario: secret never appears in any output (happy path)")
out, ex = run_tool("twitch", creds(tool="twitch.get_top_games"), [
    token_resp(),
    resp(200, body={"data": [{"id": "1", "name": "G"}]}),
])
ok &= check("client_secret absent from output", SECRET not in json.dumps(out),
            json.dumps(out)[:300])
ok &= check("app token absent from output", APP_TOKEN not in json.dumps(out),
            json.dumps(out)[:300])

print()
print("RESULT:", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
