# Image Processing

Local still-image processing for Sophon: inspect, resize, convert, crop, rotate, compress, generate
thumbnails, strip EXIF metadata, and add text watermarks. Fills the gap left by the media-audio and
media-video skills for still images.

Built on [Pillow](https://python-pillow.org/) (with [piexif](https://pypi.org/project/piexif/) for
EXIF handling). Runs fully offline — **no network and no credentials required**.

## Tools

| Tool | Risk | Description |
|------|------|-------------|
| `image.info` | none | Report width, height, format, mode, and whether the image has EXIF |
| `image.resize` | low | Resize to a width/height (aspect ratio preserved by default) |
| `image.convert` | low | Convert between PNG, JPEG, and WebP |
| `image.crop` | low | Crop to a `left, top, right, bottom` box |
| `image.rotate` | low | Rotate clockwise by N degrees (canvas expands by default) |
| `image.compress` | low | Re-encode at a target quality to reduce file size |
| `image.thumbnail` | low | Fit the image within a square box (default 256 px) |
| `image.strip_exif` | low | Save a copy with all EXIF/metadata removed |
| `image.watermark` | low | Overlay semi-transparent text at a corner or the center |

## Files

Input and output paths are plain path strings. Relative paths resolve against the current working
directory (`/workspace` in the sandbox); output directories are created if they don't exist. Every
tool returns the output path in its JSON result.

Output format is inferred from the output file extension (e.g. `.png`, `.jpg`, `.webp`), or set
explicitly with the `format` parameter on `resize`/`convert`. When saving to JPEG, images with an
alpha channel are flattened onto a white background (JPEG has no transparency).

## Notes

- `image.rotate` uses clockwise degrees (positive rotates clockwise).
- `image.compress` quality is clamped to 1–95; PNG is lossless, so quality is ignored and the file
  is simply re-optimized.
- `image.watermark` scales the font to the image and falls back to Pillow's built-in font if no
  TrueType font is available in the sandbox.

## Trademarks

Pillow is a fork of PIL maintained by the Python imaging community. This skill is an independent
integration and is not affiliated with or endorsed by the Pillow project.
