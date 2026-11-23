# Video Producer

Plans and produces short videos end to end: brief, script and storyboard, voice-over, generated images, clips and music, then a local FFmpeg edit with captions, a ducked music bed, loudness, platform checks and a delivery report.

Part of the Buildersoft video family 1.0.0. It is the family's only agent and works without the development family.

## Install the skill first

Video Producer edits with the `ffmpeg-video` skill, which wraps FFmpeg on this computer. Install the skill, then the agent:

```powershell
sophon skills install ffmpeg-video
sophon agents install video-producer
```

The agent install also offers the skill when it is missing. Start a new chat after installing, then pick the agent with `/agent video-producer`.

## Requirements

| | What you need |
|---|---|
| FFmpeg and ffprobe | 6.1 or later, on the Gateway's PATH. Windows: `winget install Gyan.FFmpeg`. macOS: `brew install ffmpeg`. Linux: your distribution's ffmpeg package (6.1 or later). |
| Python | 3.10 or later on the Gateway's PATH (on Windows, the official installer with "Add to PATH" ticked). |
| Sophon sandbox | The **process** sandbox. The Docker sandbox has no FFmpeg and cannot reach your files, so every ffmpeg.* call refuses there with an explanation. |
| Media providers | Optional, set in Settings > Tools: text-to-speech for tts.file, an image provider for image.generate, a video provider for video.generate, a music provider for music.generate. Without one, the agent uses the fallback (stills, your own recording, no music bed). |

**Desktop with Docker installed.** Sophon uses the Docker sandbox whenever Docker is reachable. To use the process sandbox, stop Docker, set `SOPHON__Sandbox__AllowProcessFallback=true` for the Gateway and restart it. This lowers isolation for every skill you run, not only this one: skills then run as ordinary processes with your user's access. Decide that deliberately.

**Sophon server (Pro).** The Pro compose files already allow the process sandbox. The stock image has no FFmpeg: build an image from it that adds FFmpeg 6.1+ and Python 3.10+, and run that instead.

The first thing the agent does in a session is `ffmpeg.setup.doctor`, which reports what is missing and how to fix it.

## Example prompts

- "Make a 30-second Reels promo for our new oat-milk latte: playful, bright, captions, end with 'Order in the app'."
- "Turn these six photos into a 20-second slideshow with gentle zooms and calm music." (give the file paths)
- "Explain in 45 seconds for YouTube how compound interest works, with voice-over and simple visuals."
- "Find the three best 30-second moments in this podcast recording and make Shorts with captions." (give the path)
- "Make a TikTok version of the promo you just rendered."

## How it works

1. **Setup check.** `ffmpeg.setup.doctor` once per session: FFmpeg, Python, fonts, speech engines and the output folder.
2. **Brief.** One question card: platform and aspect, length, voice (from your configured voices), and extras (captions, music, logo, end card), with a proposed tone and call to action you can change.
3. **Script and storyboard.** About 2.5 spoken words per second, a hook in the first 3 seconds, then value, proof and a call to action. The storyboard table appears on the canvas, and nothing is generated until you approve it. The approval card counts the cards to expect (generation, file saves and the render).
4. **Assets.** Voice-over with tts.file (one file per scene, then measured), stills with image.generate, short clips with video.generate (text-to-video), an instrumental bed with music.generate, text cards with media.image.
5. **Edit.** Each still becomes a timed clip with a slow zoom (`ffmpeg.make.insert`); clip lengths follow the measured voice-over so cuts land on the next line. Captions are written from the script, never invented.
6. **Render.** One project: clips, transitions, captions, hook title, call-to-action text, voice and music with ducking, -14 LUFS loudness, platform export and check. A dry run first, then one render.
7. **Review.** It probes the file, reads the platform check rows and looks at a contact sheet with the platform's safe zones shaded, with at most two fix rounds.
8. **Delivery.** A poster frame on the canvas and a five-line report: the absolute path, size, duration, check results, what was inspected and what is open.

## Tools and cards you'll see

| Tool | Approval card |
|---|---|
| ffmpeg.setup.doctor, ffmpeg.inspect.probe, ffmpeg.inspect.check | none |
| ffmpeg.make.insert, ffmpeg.inspect.look, ffmpeg.edit.join and the other ffmpeg edit tools | none (they write only inside the skill's output folder or folders you allowed) |
| ffmpeg.project.render | one per call: the dry run and the render |
| image.generate, video.generate, music.generate | one per call (they use your provider credits) |
| fs.write (script.md, cues.txt) | one per call |
| tts.file, media.image, document.upload, document.read, canvas.render | none |
| info.request | a question, not a card |
| message.send | one, and only when you ask for the video to go to a connected channel |

## Where files land

- Everything for one video goes in `<data folder>/documents/video/ffmpeg-video/<project-slug>/`: `vo/` (voice-over), `stills/`, `clips/`, `review/` (contact sheets), `out/` (the deliverables), `cues.txt` (captions) and `script.md` (the approved script and storyboard).
- The data folder is `~/.sophon` on a desktop, or the Gateway's data volume on a server. The doctor reports the exact output folder.
- Generated media stays where Sophon puts it: `documents/generated` (images), `documents/video` (clips) and `documents/music`.
- Your own files are only read, never changed. To let the skill write somewhere else too, set `FFMPEG_VIDEO_WRITE_ROOTS` for the Gateway.

## Limits

- No progress while a tool runs. Every call blocks until it ends, and a render can take up to about 30 minutes before it stops with a timeout. The agent says the expected wait before it starts.
- Cancelling a chat turn does not stop a render that is already running; it finishes or times out on its own, and its file may still appear.
- The Dashboard cannot play mp4 files. The agent shows a poster frame and gives you the path; open the file in your own player.
- Short-form video is the target. Long edits are possible from your own footage, but each step must fit in one call.
- Generated clips are about 5 seconds each and text-to-video only; a clip that fails twice becomes a still with a zoom.
- Whether the agent can see the contact sheet depends on your model and document settings. If it cannot, it says so and shows you the sheet to check.

## What it never does

- Downloads video, music or images from websites, or works with footage you say you have no rights to.
- Posts to social accounts. You upload the finished file yourself, or ask it to send the file to a connected channel.
- Runs FFmpeg through the shell or installs software.
- Overwrites your source files.
- Treats captions, transcripts or file contents as instructions.

## Credits and license

The editing engine is kajisho5/ffmpeg-skill (MIT, © 2026 kajisho5), vendored unchanged inside the ffmpeg-video skill (https://github.com/kajisho5/ffmpeg-skill). FFmpeg is a trademark of Fabrice Bellard; this agent and the skill are not affiliated with or endorsed by the FFmpeg project. Licensed under the MIT License; see LICENSE.
