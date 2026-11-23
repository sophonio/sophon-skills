# Third-party notices

The `ffmpeg-video` skill is published by Buildersoft LLC under the MIT License (see `LICENSE`). It
ships third-party code, listed below with its own license.

## ffmpeg-skill

- Project: ffmpeg-skill by kajisho5
- Source: https://github.com/kajisho5/ffmpeg-skill
- Version: 3.9.2 (tag `v3.9.2`, commit `3f8ba63cc8eb991c1730d57b0215e6127765399a`)
- Location in this package: `vendor/ffmpeg-skill/` (byte-identical copies of the upstream files,
  each pinned by sha256 in `vendor.lock.json`; the upstream `LICENSE` is included there unchanged)
- Changes: none. The files are not modified; `lib/bridge.py` and `main.py` call them.

License text, as shipped in `vendor/ffmpeg-skill/LICENSE`:

```text
MIT License

Copyright (c) 2026 kajisho5

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## FFmpeg

FFmpeg is not included in this package. The skill runs the `ffmpeg` and `ffprobe` programs that
are already installed on the computer, under their own licenses (LGPL or GPL, depending on the
build).

FFmpeg is a trademark of Fabrice Bellard, originator of the FFmpeg project. This skill and
ffmpeg-skill are independent projects: neither is affiliated with, sponsored by or endorsed by the
FFmpeg project or its developers. The name is used only to say which program the skill runs.
