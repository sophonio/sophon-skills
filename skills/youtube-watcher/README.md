# YouTube Watcher

Fetch and read transcripts from YouTube videos so Sophon can summarize a video, answer questions
about its content, or extract information from it — without watching it.

Built on the pure-Python [`youtube-transcript-api`](https://pypi.org/project/youtube-transcript-api/)
(no API key required), with an automatic [`yt-dlp`](https://pypi.org/project/yt-dlp/) fallback for
when YouTube blocks automated transcript requests, plus YouTube's keyless oEmbed endpoint for basic
metadata. No credentials to configure.

## Tools

| Tool | Risk | Description |
|------|------|-------------|
| `youtube.get_transcript` | none | Fetch a video's transcript as plain text (default) or timed segments; optional translation |
| `youtube.list_transcripts` | none | List available caption tracks (language, auto-generated?, translatable?) |
| `youtube.get_video_info` | none | Basic public metadata — title, channel, thumbnail (via oEmbed) |

## Inputs

`video` accepts either a raw video ID (`dQw4w9WgXcQ`) or any YouTube URL form:
`https://www.youtube.com/watch?v=…`, `https://youtu.be/…`, `…/shorts/…`, `…/embed/…`.

`youtube.get_transcript` options:
- `languages` — preferred caption language codes in priority order (default `["en"]`). If none of
  the preferred languages exist, it falls back to any available transcript.
- `format` — `text` (one joined string, default) or `segments` (list of `{text, start, duration}`
  with timestamps in seconds).
- `translateTo` — a target language code (e.g. `es`, `fr`) to translate the transcript into, when
  the source track is translatable. If the primary library reports the track as non-translatable
  (increasingly common for auto-generated tracks), the yt-dlp fallback still tries YouTube's
  auto-translation.
- `proxy` — an optional HTTP(S) proxy URL (`http://user:pass@host:port`) routing the transcript
  request through that proxy; use a rotating residential proxy if YouTube blocks your IP.
  `youtube.list_transcripts` accepts the same option.

Results include a `source` field (`youtube-transcript-api` or `yt-dlp`, showing which path served
the request) and, when the requested languages weren't available, a `note` explaining which
language was returned instead.

## Notes

- Works with both manually uploaded and auto-generated captions. A video with captions completely
  disabled returns a clear error.
- `get_video_info` uses oEmbed, which returns title/author/thumbnail but not duration or description
  (those require the YouTube Data API and a key, which this skill deliberately avoids).
- YouTube rate-limits and IP-blocks automated transcript requests (`RequestBlocked`), especially
  from datacenter/VPN IPs or after bursts of requests; residential IPs usually recover within
  minutes. When the primary library is blocked, the skill automatically retries the whole fetch
  through `yt-dlp`, which emulates real player clients and survives most blocks. If both paths
  fail, the full error text (including remediation guidance) is returned — pass the `proxy` option
  to route around a persistent block.
- Transcripts of long videos can be large; use `format: "segments"` when you need timestamps to cite
  or jump to specific moments.

## Trademarks

YouTube is a trademark of Google LLC. This is an unofficial, independently built skill and is not
affiliated with or endorsed by YouTube or Google.
