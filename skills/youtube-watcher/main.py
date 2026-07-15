"""YouTube Watcher skill — fetch and read transcripts from YouTube videos.

Uses the pure-python `youtube-transcript-api` (no API key, no native deps) so it runs unchanged in
the alpine Python sandbox. Video metadata uses YouTube's keyless oEmbed endpoint over the standard
library. `params` is injected as a global by the Sophon runtime and carries the tool name and the
tool's call arguments; this skill needs no credentials.
"""

import json
import re
import urllib.request
import urllib.parse
import urllib.error

from youtube_transcript_api import YouTubeTranscriptApi

tool_name = params.get("tool", "")

VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")


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


def fetch_transcript(api, video_id, languages, translate_to):
    """Return a FetchedTranscript, honoring language preference, fallback, and translation."""
    if translate_to:
        transcripts = api.list(video_id)
        base = None
        try:
            base = transcripts.find_transcript(languages)
        except Exception:
            for transcript in transcripts:
                if transcript.is_translatable:
                    base = transcript
                    break
        if base is None:
            raise ValueError("No translatable transcript is available for this video.")
        return base.translate(translate_to).fetch()

    try:
        return api.fetch(video_id, languages=languages)
    except Exception:
        # Requested language(s) not found — fall back to whatever the video has.
        transcripts = api.list(video_id)
        for transcript in transcripts:
            return transcript.fetch()
        raise


# --- Tool handlers ---------------------------------------------------------

def get_transcript():
    video_id = extract_video_id(params.get("video"))
    languages = params.get("languages") or ["en"]
    if not isinstance(languages, list):
        languages = [str(languages)]
    fmt = (params.get("format") or "text").lower()
    translate_to = params.get("translateTo") or None

    api = YouTubeTranscriptApi()
    fetched = fetch_transcript(api, video_id, languages, translate_to)
    raw = fetched.to_raw_data()  # list of {"text", "start", "duration"}
    duration = round(raw[-1]["start"] + raw[-1]["duration"], 2) if raw else 0

    result = {
        "videoId": video_id,
        "language": fetched.language,
        "languageCode": fetched.language_code,
        "isGenerated": fetched.is_generated,
        "snippetCount": len(raw),
        "durationSeconds": duration,
    }
    if fmt == "segments":
        result["segments"] = raw
    else:
        result["text"] = " ".join(s["text"].replace("\n", " ").strip() for s in raw).strip()
    print(json.dumps(result))


def list_transcripts():
    video_id = extract_video_id(params.get("video"))
    api = YouTubeTranscriptApi()
    transcripts = api.list(video_id)
    tracks = []
    for transcript in transcripts:
        tracks.append({
            "languageCode": transcript.language_code,
            "language": transcript.language,
            "isGenerated": transcript.is_generated,
            "isTranslatable": transcript.is_translatable,
        })
    print(json.dumps({"videoId": video_id, "count": len(tracks), "transcripts": tracks}))


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
    print(json.dumps({"error": str(e)}))
except Exception as e:  # noqa: BLE001
    # youtube-transcript-api raises descriptive multi-line messages; keep the first line.
    first_line = (str(e).strip().splitlines() or [type(e).__name__])[0]
    print(json.dumps({"error": f"{type(e).__name__}: {first_line}"}))
