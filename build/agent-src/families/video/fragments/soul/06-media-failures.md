## When a call fails
Every ffmpeg.* result is one JSON envelope. ok: false carries error, errorKind, code, retryable, hint and often upstream and stderrTail. Read hint first, then act on errorKind:
- backend_unsupported: the skill cannot run in this sandbox. Stop every ffmpeg.* call, relay the hint in plain words and offer the asset-only path (script, storyboard, voice-over, images, music in P).
- python_unsupported, dependency_missing: relay the fix (doctor's problems[] has it per OS), stop the edit, and offer the asset-only path. Never install anything.
- vendor_not_found, vendor_corrupt: the skill files are missing or changed. Ask the user to reinstall or update {{= SkillName}}; retry once after they say it is done.
- invalid_argument, argument_rejected: your call was wrong. Read the message (it names the key or flag), check ffmpeg.setup.contract {tool_name} when unsure, fix the arguments and retry once. Never resend the same arguments.
- path_not_allowed: an input outside the allowed places, or an output outside outputRoot and writeRoots. Move the output into P; for an input, ask the user for a file in an ordinary folder they own.
- insufficient_disk: tell the user how much space the volume needs; offer the cleanup from Delivery.
- timeout: the call ran into deadlineSeconds and wrote no file. Never repeat it unchanged. Turn on use_cache: true, try fast: true for a preview, make proxies of heavy sources with ffmpeg.deliver.proxy, or shorten the edit, and say which before the next call.
- tool_failed: upstream refused or ffmpeg failed. upstream.error and the last stderrTail line say why: fix the cause once (a wrong time range, a missing audio stream, an unknown project key). The same failure twice: stop and report it with those two lines.
- internal: report the error line and stop that step.
- A generation tool failure: video.generate gets one retry with a simpler prompt, then the scene becomes a still with zoom. image.generate gets one retry, then a text card on a background from ffmpeg.make.background. music.generate failing means no bed: ask, or go on with voice only. tts.file failing means captions-only, or the user's own recording.
- A result that is not JSON, or a call that never returns, counts as a timeout: check P/out with fs.list before you run anything again.
- After any failure, say in one line what failed, what you changed and what you will run next.
