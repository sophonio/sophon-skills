---
profiles:
  chat:
    pins:
      - ffmpeg.inspect.check
      - ffmpeg.inspect.look
      - ffmpeg.inspect.probe
      - ffmpeg.make.insert
      - ffmpeg.project.render
      - ffmpeg.setup.doctor
      - image.generate
      - tts.file
---
ffmpeg.* tools come from the ffmpeg-video skill and run only on Sophon's process sandbox with FFmpeg on this computer.
The other ffmpeg tools are listed by name in the tool index; load the ones a step needs with tools.search and tools.load.
music.generate, video.generate, media.image, media.video, document.upload, document.read and canvas.render load the same way.
