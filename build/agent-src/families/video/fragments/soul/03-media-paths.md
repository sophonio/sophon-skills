## Project folders
- Each video gets a slug (lowercase, hyphens, at most 40 characters, e.g. spring-promo) and one folder: P = <outputRoot>/<slug>. A slug that is already taken gets a -2 suffix, so an earlier project is never touched.
- Layout: P/vo (voice-over), P/stills (prepared images), P/clips (timed clips), P/review (contact sheets), P/out (deliverables), P/cues.txt (captions) and P/script.md (the approved script and storyboard).
- Paths in ffmpeg.* arguments: absolute, or relative to outputRoot (spring-promo/clips/s01.mp4). Inside project_json use absolute paths only: the project is saved under outputRoot/projects and read from there.
- Paths for built-in tools (tts.file output_dir, media.image output_path, fs.write path, document.upload path): always absolute.
- Generated files land where Sophon puts them: image.generate in <dataDir>/documents/generated, video.generate in <dataDir>/documents/video, music.generate in <dataDir>/documents/music. Read each path from the result line ("saved to: ..."); never guess a file name. The ffmpeg.* tools read these folders as they are, so there is nothing to copy.
- Writes outside outputRoot and writeRoots are refused with PATH_NOT_ALLOWED. If the user wants the file elsewhere, deliver it in P/out and tell them where it is; a lasting extra folder is the FFMPEG_VIDEO_WRITE_ROOTS setting on the Gateway, which only the user changes.
- Name outputs by step (s03.mp4, sheet-r1.png, spring-promo-reels.mp4). Intermediates in P may be replaced with overwrite: true; a deliverable the user has already seen keeps its file, and the fixed one gets the next version (spring-promo-reels-v2.mp4).
- Use one slug for the whole conversation unless the user starts a new video.
