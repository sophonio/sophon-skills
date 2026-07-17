"""YouTube Watcher skill — fetch and read transcripts from YouTube videos.

The primary path uses the pure-python `youtube-transcript-api` (no API key, no native deps).
YouTube intermittently blocks automated transcript requests by IP reputation and request-rate
heuristics (`RequestBlocked`); when the fetch mechanism fails that way, this skill retries the
whole operation through `yt-dlp`, which emulates real player clients and survives most blocks.
Both paths honor an optional `proxy` tool parameter (the Sophon sandbox injects no environment
variables, so a parameter is the only way to route through a proxy). Video metadata uses
YouTube's keyless oEmbed endpoint over the standard library. `params` is injected as a global by
the Sophon runtime and carries the tool name and the tool's call arguments; this skill needs no
credentials.
"""

import json
import re
import time
import urllib.request
import urllib.parse
import urllib.error

from youtube_transcript_api import (
    YouTubeTranscriptApi,
    NoTranscriptFound,
    NotTranslatable,
    RequestBlocked,
    TranslationLanguageNotAvailable,
    YouTubeRequestFailed,
    YouTubeDataUnparsable,
    PoTokenRequired,
    FailedToCreateConsentCookie,
)

tool_name = params.get("tool", "")

VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")

# Failures of the fetch *mechanism* (IP blocks, bans, consent walls, page-format changes) — worth
# retrying via yt-dlp. Semantic failures (no such transcript, captions disabled, bad video id,
# age restriction) are terminal either way and are not in this set. RequestBlocked covers its
# IpBlocked subclass.
MECHANISM_ERRORS = (
    RequestBlocked,
    YouTubeRequestFailed,
    YouTubeDataUnparsable,
    PoTokenRequired,
    FailedToCreateConsentCookie,
)

# YouTube's watch-page data often omits translation targets that the player API still serves, so
# yt-dlp can frequently translate tracks the primary library reports as non-translatable.
TRANSCRIPT_FALLBACK_ERRORS = MECHANISM_ERRORS + (
    NotTranslatable,
    TranslationLanguageNotAvailable,
)

BLOCK_HINT = (
    "YouTube rate-limits and IP-blocks automated transcript requests (common on datacenter/VPN "
    "IPs, or after a burst of requests; residential IPs usually recover within minutes). Wait and "
    "retry, or pass the optional 'proxy' parameter (\"http://user:pass@host:port\" — ideally a "
    "rotating residential proxy)."
)


def extract_video_id(value):
    """Accept a raw 11-char video ID or any common YouTube URL and return the video ID."""
    value = (value or "").strip()
    if not value:
        raise ValueError("Missing 'video': provide a YouTube video ID or URL.")
    if VIDEO_ID_RE.match(value):
        return value
    parsed = urllib.parse.urlparse(value)
    host = (parsed.hostname or "").lower()
    if host.endswith("youtu.be"):
        candidate = parsed.path.lstrip("/").split("/")[0]
        if VIDEO_ID_RE.match(candidate):
            return candidate
    if "youtube.com" in host or "youtube-nocookie.com" in host:
        query = urllib.parse.parse_qs(parsed.query)
        if "v" in query and VIDEO_ID_RE.match(query["v"][0]):
            return query["v"][0]
        path_match = re.search(r"/(?:shorts|embed|v|live)/([A-Za-z0-9_-]{11})", parsed.path)
        if path_match:
            return path_match.group(1)
    fallback = re.search(r"([A-Za-z0-9_-]{11})", value)
    if fallback:
        return fallback.group(1)
    raise ValueError(f"Could not extract a YouTube video ID from: {value}")


def _proxy_url():
    proxy = params.get("proxy")
    proxy = proxy.strip() if isinstance(proxy, str) else ""
    return proxy or None


def _make_api():
    proxy = _proxy_url()
    if proxy:
        from youtube_transcript_api.proxies import GenericProxyConfig

        return YouTubeTranscriptApi(
            proxy_config=GenericProxyConfig(http_url=proxy, https_url=proxy)
        )
    return YouTubeTranscriptApi()


def _both_failed(primary_error, fallback_error):
    primary = str(primary_error).strip()
    fallback = str(fallback_error).strip() or type(fallback_error).__name__
    return (
        "The primary transcript fetch failed and the yt-dlp fallback also failed.\n\n"
        f"Primary ({type(primary_error).__name__}): {primary[:1200]}\n\n"
        f"Fallback ({type(fallback_error).__name__}): {fallback[:600]}\n\n"
        f"Hint: {BLOCK_HINT}"
    )


def fetch_transcript(api, video_id, languages, translate_to):
    """Return (FetchedTranscript, note) honoring language preference, fallback, and translation."""
    if translate_to:
        transcripts = api.list(video_id)
        try:
            base = transcripts.find_transcript(languages)
        except NoTranscriptFound:
            base = next((t for t in transcripts if t.is_translatable), None)
        if base is None:
            raise ValueError("No translatable transcript is available for this video.")
        return base.translate(translate_to).fetch(), None

    try:
        return api.fetch(video_id, languages=languages), None
    except NoTranscriptFound:
        # Requested language(s) not found — fall back to whatever the video has, and say so.
        transcripts = api.list(video_id)
        available = [t.language_code for t in transcripts]
        for transcript in transcripts:
            note = (
                f"None of the requested languages {languages} exist for this video; returning "
                f"'{transcript.language_code}' instead (available: {available}). Use "
                "'translateTo' for a translation."
            )
            return transcript.fetch(), note
        raise


# --- yt-dlp fallback --------------------------------------------------------

def _ytdlp_extract(video_id):
    import yt_dlp  # deferred: only paid for when the primary path fails

    opts = {"quiet": True, "no_warnings": True, "skip_download": True}
    proxy = _proxy_url()
    if proxy:
        opts["proxy"] = proxy
    with yt_dlp.YoutubeDL(opts) as ydl:
        return ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)


def _track_name(fmts, code):
    for fmt in fmts:
        if fmt.get("name"):
            return fmt["name"]
    return code


def _ytdlp_tracks(info):
    """Map yt-dlp caption dicts to a list of (code, name, is_generated, formats) actual tracks.

    `automatic_captions` lists every translation *target* (150+ languages); the real ASR track(s)
    are the ones YouTube keys as '<code>-orig'. Manual uploads live in `subtitles`.
    """
    manual = info.get("subtitles") or {}
    autos = info.get("automatic_captions") or {}
    tracks = []
    for code, fmts in manual.items():
        tracks.append((code, _track_name(fmts, code), False, fmts))
    originals = [(key[:-5], autos[key]) for key in autos if key.endswith("-orig")]
    if not originals and autos:
        guess = info.get("language")
        key = guess if guess in autos else next(iter(autos))
        originals = [(key, autos[key])]
    for code, fmts in originals:
        tracks.append((code, _track_name(fmts, code), True, fmts))
    return tracks, autos


def _fetch_caption_json3(fmts, what):
    fmt = next((f for f in fmts if f.get("ext") == "json3"), None)
    if fmt is None:
        raise RuntimeError(f"No json3 caption format available for {what}.")
    request = urllib.request.Request(fmt["url"], headers={"User-Agent": "Mozilla/5.0"})
    proxy = _proxy_url()
    opener = (
        urllib.request.build_opener(urllib.request.ProxyHandler({"http": proxy, "https": proxy}))
        if proxy
        else urllib.request.build_opener()
    )
    raw = None
    rate_limited = None
    for delay in (0, 3, 6):
        if delay:
            time.sleep(delay)  # the timedtext endpoint rate-limits bursts; back off and retry
        try:
            with opener.open(request, timeout=30) as resp:
                raw = resp.read().decode("utf-8")
            break
        except urllib.error.HTTPError as e:
            if e.code != 429:
                raise
            rate_limited = e
    else:
        raise rate_limited
    segments = []
    for event in json.loads(raw).get("events") or []:
        text = "".join(seg.get("utf8", "") for seg in event.get("segs") or []).strip()
        if not text:
            continue  # skips the newline-only spacer events ASR tracks interleave
        segments.append({
            "text": text,
            "start": round((event.get("tStartMs") or 0) / 1000.0, 3),
            "duration": round((event.get("dDurationMs") or 0) / 1000.0, 3),
        })
    return segments


def _ytdlp_get_transcript(video_id, languages, translate_to):
    """Fetch (code, name, is_generated, segments, note) via yt-dlp, mirroring primary semantics."""
    info = _ytdlp_extract(video_id)
    tracks, autos = _ytdlp_tracks(info)
    if not tracks:
        raise ValueError(f"No captions of any kind are available for video {video_id}.")

    targets = [translate_to] if translate_to else list(languages)
    chosen = note = None
    is_translation = False
    for lang in targets:
        exact = [t for t in tracks if t[0] == lang]  # manual tracks are listed before ASR ones
        if exact:
            chosen = exact[0]
            break
        if translate_to and lang in autos:
            # Any code in automatic_captions is a valid auto-translation target.
            chosen = (lang, _track_name(autos[lang], lang), True, autos[lang])
            is_translation = True
            break
    if chosen is None:
        if translate_to:
            raise ValueError(
                f"Translation to '{translate_to}' is not available for video {video_id}."
            )
        chosen = tracks[0]
        available = sorted({t[0] for t in tracks})
        note = (
            f"None of the requested languages {targets} exist for this video; returning "
            f"'{chosen[0]}' instead (available: {available}). Use 'translateTo' for a translation."
        )

    code, name, is_generated, fmts = chosen
    try:
        segments = _fetch_caption_json3(fmts, f"'{code}' captions of {video_id}")
    except urllib.error.HTTPError as e:
        if not (is_translation and e.code == 429 and tracks):
            raise
        # YouTube throttles caption *translations* much harder than plain caption fetches —
        # degrade to the original track rather than failing the whole call.
        code, name, is_generated, fmts = tracks[0]
        segments = _fetch_caption_json3(fmts, f"'{code}' captions of {video_id}")
        note = (
            f"YouTube is rate-limiting caption translations right now (HTTP 429); returning the "
            f"original '{code}' track untranslated. Retry later for '{translate_to}'."
        )
    return code, name, is_generated, segments, note


# --- Tool handlers ---------------------------------------------------------

def get_transcript():
    video_id = extract_video_id(params.get("video"))
    languages = params.get("languages") or ["en"]
    if not isinstance(languages, list):
        languages = [str(languages)]
    fmt = (params.get("format") or "text").lower()
    translate_to = params.get("translateTo") or None

    try:
        fetched, note = fetch_transcript(_make_api(), video_id, languages, translate_to)
        raw = fetched.to_raw_data()  # list of {"text", "start", "duration"}
        language = fetched.language
        language_code = fetched.language_code
        is_generated = fetched.is_generated
        source = "youtube-transcript-api"
    except TRANSCRIPT_FALLBACK_ERRORS as primary_error:
        try:
            language_code, language, is_generated, raw, note = _ytdlp_get_transcript(
                video_id, languages, translate_to
            )
            source = "yt-dlp"
        except Exception as fallback_error:  # noqa: BLE001
            raise RuntimeError(_both_failed(primary_error, fallback_error)) from fallback_error

    duration = round(raw[-1]["start"] + raw[-1]["duration"], 2) if raw else 0
    result = {
        "videoId": video_id,
        "language": language,
        "languageCode": language_code,
        "isGenerated": is_generated,
        "snippetCount": len(raw),
        "durationSeconds": duration,
        "source": source,
    }
    if note:
        result["note"] = note
    if fmt == "segments":
        result["segments"] = raw
    else:
        result["text"] = " ".join(s["text"].replace("\n", " ").strip() for s in raw).strip()
    print(json.dumps(result))


def list_transcripts():
    video_id = extract_video_id(params.get("video"))
    try:
        tracks = [
            {
                "languageCode": t.language_code,
                "language": t.language,
                "isGenerated": t.is_generated,
                "isTranslatable": t.is_translatable,
            }
            for t in _make_api().list(video_id)
        ]
        source = "youtube-transcript-api"
    except MECHANISM_ERRORS as primary_error:
        try:
            ytdlp_tracks, autos = _ytdlp_tracks(_ytdlp_extract(video_id))
            tracks = [
                {
                    "languageCode": code,
                    "language": name,
                    "isGenerated": is_generated,
                    "isTranslatable": bool(autos) or not is_generated,
                }
                for code, name, is_generated, _fmts in ytdlp_tracks
            ]
            source = "yt-dlp"
        except Exception as fallback_error:  # noqa: BLE001
            raise RuntimeError(_both_failed(primary_error, fallback_error)) from fallback_error
    print(json.dumps(
        {"videoId": video_id, "count": len(tracks), "transcripts": tracks, "source": source}
    ))


def get_video_info():
    video_id = extract_video_id(params.get("video"))
    watch_url = f"https://www.youtube.com/watch?v={video_id}"
    oembed = "https://www.youtube.com/oembed?" + urllib.parse.urlencode(
        {"url": watch_url, "format": "json"}
    )
    req = urllib.request.Request(oembed, headers={"User-Agent": "sophon-youtube-watcher"})
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise ValueError(f"Video not found or is private: {video_id}")
        raise RuntimeError(f"oEmbed error {e.code}")
    print(json.dumps({
        "videoId": video_id,
        "title": data.get("title"),
        "author": data.get("author_name"),
        "authorUrl": data.get("author_url"),
        "thumbnail": data.get("thumbnail_url"),
        "url": watch_url,
    }))


HANDLERS = {
    "youtube.get_transcript": get_transcript,
    "youtube.list_transcripts": list_transcripts,
    "youtube.get_video_info": get_video_info,
}

try:
    handler = HANDLERS.get(tool_name)
    if handler is None:
        print(json.dumps({"error": f"Unknown tool: {tool_name}"}))
    else:
        handler()
except (ValueError, RuntimeError) as e:
    print(json.dumps({"error": str(e)[:2400]}))
except Exception as e:  # noqa: BLE001
    # Surface the library's full multi-line diagnostics — truncating them hides the remedy.
    message = str(e).strip() or type(e).__name__
    print(json.dumps({"error": f"{type(e).__name__}: {message[:2400]}"}))
