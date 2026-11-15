# FFmpeg Video

Edit, assemble, caption, mix, check and render video on the computer that runs Sophon, with the
FFmpeg already installed there. The skill brings the 42 tools of the MIT-licensed
[ffmpeg-skill](https://github.com/kajisho5/ffmpeg-skill) by kajisho5 into Sophon, plus a setup
check (`ffmpeg.setup.doctor`) and a machine-readable rule book (`ffmpeg.setup.contract`):

- inspect media (probe, compliance checks, scene detection, contact sheets, HTML reports);
- make clips from stills, colour backgrounds, image sequences and audio waveforms;
- cut, join, remove silence, cut away to b-roll, switch multicam angles, sync, pad, freeze, loop;
- fit to an aspect ratio, crop, grade, change speed, reverse, stabilize, denoise, redact;
- burn or mux captions, add titles and overlays, mix music under voice, normalise loudness;
- export for a platform (YouTube, Shorts, Reels, TikTok, ...) and make editing proxies;
- render a whole declarative `project.json` in one call, or run one recipe over a folder.

No network and no credentials. Nothing is downloaded: inputs are local files only.

## Requirements

| | Needed |
|---|---|
| Sophon sandbox backend | **the process backend** (see below). The Docker sandbox is refused. |
| Python | 3.10 or later on the Gateway's PATH (as `python` or `python3`). If Sophon picks an older one, the skill looks for a newer one itself: `FFMPEG_VIDEO_PYTHON`, then `py -3` on Windows, then `python3.14` ... `python3.10`. |
| FFmpeg | 6.1 or later, `ffmpeg` and `ffprobe` both, on the Gateway's PATH or in a well-known install folder |

Install FFmpeg, then **restart the Sophon Gateway** so it sees the new PATH:

| OS | Install | Notes |
|---|---|---|
| Windows | `winget install Gyan.FFmpeg` (or `choco install ffmpeg`) | Python from python.org with "Add to PATH" ticked; the Microsoft Store `python.exe` alias alone is not enough. WinGet, Chocolatey, Scoop and `%ProgramFiles%\ffmpeg\bin` are found even when they are missing from the Gateway's PATH. |
| macOS | `brew install ffmpeg` (or `ffmpeg-full` for every caption feature) | A launchd Gateway has a minimal PATH: `/opt/homebrew/bin` and `/usr/local/bin` are searched anyway, for FFmpeg and for `python3.1x`. Apple's `/usr/bin/python3` is 3.9, too old, and is skipped. |
| Linux | `sudo apt install ffmpeg` | Ubuntu 24.04 and Debian 13 ship 6.1+; Ubuntu 22.04 (4.4) and Debian 12 (5.1) are too old: use a newer release or a static build. |

`FFMPEG_VIDEO_FFMPEG_DIR` (a folder holding `ffmpeg` and `ffprobe`) puts a specific build first.

Then ask Sophon to run **`ffmpeg.setup.doctor`**. It reports `ready`, the output folder, the
Python and FFmpeg it found, the time limit, and for every problem a `fix` line.

### The process backend, and what it means for isolation

Sophon runs a skill either in a Docker container (`python:3.13-alpine`, no FFmpeg, no access to
your files) or, when Docker is not available, as a plain child process of the Gateway. This skill
needs the second: there is no FFmpeg in the container and no way to reach your media from it.
Every call made under Docker returns `BACKEND_UNSUPPORTED` with these steps:

- **Desktop (Windows, macOS, Linux):** make Docker unreachable for Sophon (stop Docker Desktop),
  set `SOPHON__Sandbox__AllowProcessFallback=true` in the Gateway's environment and restart the
  Gateway; its log then says it uses the process sandbox.
- **Server (Sophon Pro):** run `docker-compose.pro.prebuilt.yml`, which has no Docker socket and so
  uses the process backend inside the Gateway container, with a Gateway image that adds FFmpeg
  6.1+ (for example `FROM` the Gateway image plus
  `apt-get install -y --no-install-recommends ffmpeg fontconfig fonts-dejavu-core`).

> **Warning.** The process fallback lowers isolation for **every** skill, not only this one:
> skills then run as the Gateway's user, with its environment and its access to files and the
> network, and without the container's memory and CPU limits. Turn it on only on a computer
> where you trust every installed skill. This skill confines its own writes (below), which is a
> safety measure inside the skill, not a sandbox.

## Where files go

Every call works under the **output root**:

```
<Sophon data folder>/documents/video/ffmpeg-video/
```

That is `%USERPROFILE%\.sophon\documents\video\ffmpeg-video` on a default Windows install and
`~/.sophon/documents/video/ffmpeg-video` elsewhere; `ffmpeg.setup.doctor` prints the exact path.

- A **relative** path (input or output) is relative to the output root, so `"output": "promo/final.mp4"`
  writes `<output root>/promo/final.mp4` and creates `promo/` if needed.
- Inside it the skill keeps `projects/` (the checked copy of each render project and batch recipe),
  `reports/` (results too large to return), `verify/`, `previews/` (`stop_after` renders),
  `.cache/render` (`use_cache`) and `.tmp/` (each call's own temp folder, removed after the call).
- `FFMPEG_VIDEO_WRITE_ROOTS` (in the Gateway's environment, separated like PATH) adds more folders
  the skill may write into, for example an exports folder on another drive.

## Path policy

The skill checks every path before anything runs, including the paths inside render projects,
batch recipes and brand files:

- **Inputs** are local files that exist: an absolute path, `~/...`, or a path relative to the
  output root. URLs (`https:`, `file:`, ...) and paths holding NUL or line breaks are refused, and
  so are network and device paths (`\\host\share`, `//host/share`, `\\?\`, `\\.\`) unless they are
  inside a write root: they are refused before the skill looks at them, so no network connection
  is made.
- **Sophon's own data is off limits**: nothing under the data folder may be read or written except
  inside `documents/` (so `vault/`, `config/`, `skills/`, `sessions/` and the rest are refused),
  and no file of the skill itself.
- **Outputs** must land inside a write root (the output root, plus `FFMPEG_VIDEO_WRITE_ROOTS`), need
  an extension, and may not climb out with `..` or through a symbolic link. Folders are created
  only inside the output root.
- **Overwriting** an existing file needs `overwrite: true` and is honoured only inside the output
  root; elsewhere the call is refused. Without it, an existing output is refused (`output_exists`).
- Inputs are never modified: every tool writes a new file.
- **Batch recipes** are read the way the tools' own argument parsers read them: each step may use
  only its tool's options, spelled in full (`--output`, not `--out` or `-oPATH`), with a value
  that starts with `-` joined to its option (`--start=-1`). Every file a step writes is `{out}`;
  every path it reads is checked like any input; `{in}` and `{out}` stand alone; `--overwrite`
  belongs to the batch, not to a step. `glob` matches inside the batch folder (no `..`, drive,
  root, backslash or `:`), and `suffix` and `ext` are parts of a file name.
- **A failed call** removes only its own partial outputs. A file upstream reports as written is
  kept and listed in the failure's `kept`: a render whose `check` stage fails is finished and
  stays on disk. A file another call wrote meanwhile is never removed.
- Path checks compare case-insensitively on Windows and macOS.
- The wrapper sets what upstream uses as its working files (`render` intermediates, the `batch`
  output folder, `verify` outputs) and refuses the parameters that would point elsewhere
  (`render.work`/`keep`/`cache`/`audit_log`, `batch.watch`/`work`, `verify.out`/`keep`). Raw CLI
  arguments (`argv`), plan files (`plan`) and GPU switching (`hw`/`no_hw`) are not offered.
- Transcription runs offline (`HF_HUB_OFFLINE=1`); model downloads are allowed only when the
  operator sets `FFMPEG_VIDEO_ALLOW_MODEL_DOWNLOAD=1`.

## Tools

Parameter names are upstream's own (argparse names). Extra parameters added by the wrapper:
`detail` (`brief`, the default, or `full`), `project_json` and `use_cache` (render),
`recipe_json` (batch) and `tool_name` (contract). Every writing tool needs an explicit `output`;
`dry_run: true` plans a call (and returns the commands with `detail: full`) without writing.

<!-- tools:begin -->

| Tool | Risk | What it does |
|---|---|---|
| `ffmpeg.inspect.probe` | none | Inspect a media file and print a compact JSON summary. |
| `ffmpeg.inspect.cropdetect` | none | Measure black letterbox/pillarbox bars and report the crop rectangle that removes them. |
| `ffmpeg.inspect.check` | none | Pre-delivery compliance check: does this file meet the platform's spec? |
| `ffmpeg.inspect.scenes` | low | Find scene changes and loud moments, and propose highlight candidates so the agent can plan an edit or a digest without watching the whole file. |
| `ffmpeg.inspect.look` | low | Give the agent eyes: pull frames or a contact sheet out of a video as PNG so the result can be inspected (caption placement, logo position, crop, colour). |
| `ffmpeg.inspect.report` | low | Build a single-file HTML delivery report: what went in, what came out, before/after contact sheets, loudness, compliance and the exact commands. |
| `ffmpeg.make.insert` | low | Turn a still image into a silent, timed video clip. |
| `ffmpeg.make.background` | low | Generate a solid-colour or two-colour gradient background clip. |
| `ffmpeg.make.sequence` | low | Turn a numbered image sequence into a video. |
| `ffmpeg.make.waveform` | low | Render an audio track as a waveform or spectrum visualization video. |
| `ffmpeg.edit.cut` | low | Cut a clip or several segments out of a video and (optionally) join them. |
| `ffmpeg.edit.join` | low | Join clips with transitions, normalising resolution, frame rate and audio layout so mismatched sources (phone + camera + screen recording) cut together. |
| `ffmpeg.edit.silence` | low | Remove silences / dead air (jump-cut editing) or just list them. |
| `ffmpeg.edit.broll` | low | Cut away to clip B over clip A for a while, then come back -- A's timeline unchanged. |
| `ffmpeg.edit.multicam` | low | Multicam: align two or more cameras (and an optional external recorder) by audio, then cut between them from a simple switch list. |
| `ffmpeg.edit.sync` | low | Detect the time offset between two recordings by audio cross-correlation and (optionally) write a synced output, with optional clock-drift correction. |
| `ffmpeg.edit.grid` | low | Composite several video clips into one COLSxROWS grid, e.g. a 4x2 wall of takes, angles, or A/B renders side by side. |
| `ffmpeg.edit.pad` | low | Add black video / silent audio at the start and/or end of a clip. |
| `ffmpeg.edit.freeze` | low | Freeze on one frame for a number of seconds -- an end-card hold, a comedic beat, a pause. |
| `ffmpeg.edit.loop` | low | Loop a clip a number of times, or to a target duration. |
| `ffmpeg.edit.metadata` | low | Write container chapters and title/artist/comment tags without touching the streams. |
| `ffmpeg.adjust.fit` | low | Fit a video to a target duration and/or aspect ratio. |
| `ffmpeg.adjust.crop` | low | Crop a video to an exact pixel rectangle. |
| `ffmpeg.adjust.color` | low | Colour management: HDR (PQ, HLG) to SDR BT.709 with real tone mapping, a .cube LUT, colour-tag fixes without re-encoding, or typed primary correction (exposure, contrast, saturation, gamma, white... |
| `ffmpeg.adjust.speedramp` | low | Step through different constant speeds across a clip's timeline (a speed ramp). |
| `ffmpeg.adjust.reverse` | low | Reverse a video (and its audio, unless dropped). |
| `ffmpeg.adjust.straighten` | low | Rotate a video by an arbitrary angle (horizon correction, not a 90/180/270 turn). |
| `ffmpeg.adjust.sphere` | low | Extract a flat (rectilinear) viewport from a 360/spherical video. |
| `ffmpeg.adjust.stabilize` | low | Stabilize shaky video (FFmpeg's vidstab, two-pass). |
| `ffmpeg.adjust.deinterlace` | low | Deinterlace interlaced source footage (old broadcast masters, DV, some camcorders). |
| `ffmpeg.adjust.denoise` | low | Reduce video noise/grain with FFmpeg's hqdn3d filter. |
| `ffmpeg.adjust.redact` | low | Blur, pixelate, or interpolate away an exact pixel rectangle for the whole clip. |
| `ffmpeg.layer.caption` | low | Burn SRT/ASS subtitles into a video, or mux one in as a soft (toggleable) subtitle stream, or generate an SRT from plain text. |
| `ffmpeg.layer.graphics` | low | Motion-graphics templates rendered with drawbox/drawtext expressions — no After Effects, no image assets, brand colours from brand.json. |
| `ffmpeg.layer.overlay` | low | Composite a logo/image or a text title onto a video with position, timing, opacity and fade in/out. |
| `ffmpeg.mix.audio` | low | Audio post: denoise, voice clean-up, typed dynamics (compressor, limiter, gate), background music with auto-ducking, fades and stereo/mono handling. |
| `ffmpeg.mix.loudness` | low | Two-pass EBU R128 loudness normalisation (ffmpeg loudnorm). |
| `ffmpeg.deliver.export` | low | Export with delivery presets. |
| `ffmpeg.deliver.proxy` | low | Generate a small, low-bitrate proxy of a video: cheap for a machine to decode, not meant for delivery. |
| `ffmpeg.project.render` | medium | Declarative edits: describe the whole edit in one project.json and render it in one command. |
| `ffmpeg.project.batch` | medium | Apply the same recipe to every file in a folder, with a content-hash cache so re-runs only process what changed. |
| `ffmpeg.setup.verify` | low | Real-footage verification kit: run the whole toolchain against your own files (phone HDR, GoPro, OBS screen captures, Log footage, Zoom recordings) and get a pass/fail table. |
| `ffmpeg.setup.doctor` | none | Check this computer: Python, FFmpeg and ffprobe versions, the filters, encoders, fonts and speech engines each tool needs, and where the skill writes (outputRoot). |
| `ffmpeg.setup.contract` | none | Describe the tools: every parameter of one tool with its flags, defaults and accepted values, or a one-line summary of all of them. |

44 tools. Tools at risk `none` or `low` show no approval card; `medium` tools ask once per call.
<!-- tools:end -->

Tool names have three parts so that every group has at most 15 tools and Sophon's tool index can
list each one by name. `ffmpeg.setup.contract` with `tool_name` returns one tool's full rules
(choices, exclusions, path roles) and upstream's examples.

### Rendering a project

`ffmpeg.project.render` takes a `project.json` path, or the same document inline as
`project_json` (at most 64 KB; write larger ones to a file with `fs.write` first):

```json
{"output": "promo/final.mp4",
 "frame": {"aspect": "9:16", "width": 1080, "height": 1920, "fps": 30, "fit": "crop"},
 "clips": [{"src": "C:/Users/me/Videos/talk.mp4", "in": 12, "out": 27}, {"src": "promo/still.mp4"}],
 "captions": {"text": "promo/cues.txt"},
 "audio": {"music": "promo/bed.mp3", "duck": true},
 "export": {"preset": "reels"}}
```

Relative paths in `project_json` are relative to the output root; in a project file, relative to
that file's folder (upstream's rule). Plan documents are refused; use `dry_run` to preview. Set
`use_cache: true` so a re-render after a small change reuses the finished stages. Template mode
(`template` plus the footage as `project`) renders a platform preset in one call; `template: all`
or a list writes a whole social pack into the `output` folder.

## Results

Every call prints one JSON object (exit code 0). A success:

```json
{"ok": true, "tool": "ffmpeg.edit.cut", "status": "completed", "output": "<path>", "outputs": ["<path>"],
 "verified": true, "dryRun": false, "summary": {"duration_s": 2.0, "width": 640, "height": 360},
 "result": {}, "diagnostics": {"warnings": []}, "truncated": false, "fullResultPath": null,
 "elapsedSeconds": 3.1, "skill": {"version": "1.0.0", "upstream": "3.9.2"}}
```

`detail: brief` (the default) returns upstream's brief document: command lines are counted,
probes summarised, and caption or transcript text is never echoed back. Lists longer than 50
items keep the first 40 and the last 10. A result over 40,000 characters (120,000 with
`detail: full`) is written whole to `<output root>/reports/` and returned as `fullResultPath`.

A failure:

```json
{"ok": false, "tool": "ffmpeg.edit.cut", "error": "<one line>", "errorKind": "path_not_allowed",
 "code": "PATH_NOT_ALLOWED", "retryable": false, "hint": "<what to do>", "upstream": null, "stderrTail": ""}
```

| code | When | Retry? |
|---|---|---|
| `BACKEND_UNSUPPORTED` | the call ran in the Docker sandbox (or in a folder that is not a Sophon workspace) | no: switch backend |
| `PYTHON_UNSUPPORTED` | Sophon's Python is older than 3.10 and no newer one was found | no: install Python 3.10+ |
| `DEPENDENCY_MISSING` | ffmpeg or ffprobe missing, or older than 6.1 (also upstream's own exit 127) | no: install or upgrade FFmpeg |
| `VENDOR_NOT_FOUND` | the installed skill folder was not found, or is another release | no: reinstall the skill |
| `VENDOR_CORRUPT` | a vendored file changed, or an extra one appeared | yes, after a reinstall |
| `INVALID_ARGUMENT` | unknown, removed, missing or malformed parameters; an input that does not exist | no: fix the call |
| `ARGUMENT_REJECTED` | the tool itself refused a value (see `stderrTail`) | no: fix the call |
| `PATH_NOT_ALLOWED` | a path outside the rules above; `reason` says which rule | no |
| `INSUFFICIENT_DISK` | less than 2048 MB free on the output volume (`FFMPEG_VIDEO_MIN_FREE_MB`) | after freeing space |
| `TIMEOUT` | the call reached its deadline or a `timeout` | try `use_cache`, `fast`, a proxy or a shorter section |
| `TOOL_FAILED` | the tool ran and failed (a failed `check` included); `upstream.error` keeps its kind, code and reason | depends |
| `INTERNAL_ERROR` | anything else | run `ffmpeg.setup.doctor` |

## Limits

- **One call, one process.** A call blocks until it finishes; there is no progress report.
- **Time.** The manifest gives each call 30 minutes (`timeoutSeconds: 1800`). The skill stops
  its own work 60 seconds before that (the deadline), so a long job ends with a structured
  `TIMEOUT` and its partial output removed rather than being cut off. `probe` (2 minutes),
  `cropdetect` and `look` (5), `check` (15), `doctor` (2) and `contract` (1) have shorter limits.
  Each ffmpeg command gets a `timeout` of 28 minutes by default (the deadline less 30 seconds, in
  whole minutes; shorter for the tools with shorter limits), and a larger one is lowered to that.
  It is the same on every call, so `use_cache` re-renders match their cached stages.
- **Cancelling** a call in Sophon does not stop the process (a Sophon limitation); the run ends by
  itself at the deadline and cleans up.
- `batch` runs at most 2 jobs at a time. `jobs` above that is lowered.
- Results are text only: Sophon skills cannot attach files, and the Dashboard has no video player.
  The tools report absolute paths; `ffmpeg.inspect.look` writes PNG contact sheets you can open.

## Upstream

`vendor/ffmpeg-skill/` holds byte-identical copies of ffmpeg-skill v3.9.2 (commit
`3f8ba63cc8eb991c1730d57b0215e6127765399a`): the 42 tool scripts, their shared `_common` package,
the contract, the platform templates, the MCP server module whose argument mapping the wrapper
reuses, the upstream `SKILL.md` and its `LICENSE`. Each file is pinned by sha256 in
`vendor.lock.json` and checked on every call. Nothing in it is patched: the wrapper
(`main.py` and `lib/bridge.py`) adds the Sophon bootstrap, the path policy and the result
envelope around it. `lib/tool-map.json` and this file's tool table are generated from the
upstream contract by `build/ffmpeg-video/generate.py` in the sophon-skills repository; new
upstream releases are taken in deliberately, as a new skill version. See `THIRD_PARTY_NOTICES.md`
for the upstream license.

## Trademark

FFmpeg is a trademark of Fabrice Bellard, originator of the FFmpeg project. This skill and
ffmpeg-skill are independent projects, not affiliated with, sponsored by or endorsed by the FFmpeg
project or its developers; the name only says which program the skill runs. FFmpeg itself is not
included: the skill runs the `ffmpeg` and `ffprobe` already installed on the computer, under
their own licenses.

## License

MIT, Buildersoft LLC (see `LICENSE`). Vendored code: MIT, © 2026 kajisho5 (see `THIRD_PARTY_NOTICES.md`).
