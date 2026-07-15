"""Image processing skill — local still-image operations with Pillow (+ piexif for EXIF).

No network, no credentials. `params` is injected as a global by the Sophon runtime and carries the
tool name plus the tool's call arguments. File inputs/outputs are path strings; relative paths are
resolved against the current working directory (/workspace in the sandbox) and outputs are written
there. Each tool prints a single JSON object to stdout; on error it prints {"error": ...}.
"""

import json
import os

import piexif
from PIL import Image, ImageDraw, ImageFont

tool_name = params.get("tool", "")

JPEG_FORMATS = {"jpeg", "jpg"}
FORMAT_ALIASES = {"jpg": "JPEG", "jpeg": "JPEG", "png": "PNG", "webp": "WEBP"}
EXT_TO_FORMAT = {
    ".jpg": "JPEG", ".jpeg": "JPEG", ".png": "PNG", ".webp": "WEBP",
    ".gif": "GIF", ".bmp": "BMP", ".tiff": "TIFF", ".tif": "TIFF",
}


def resolve_input(key="input"):
    """Return an absolute path to an existing input file, or raise ValueError."""
    value = params.get(key)
    if not value:
        raise ValueError(f"Missing required parameter: {key}")
    path = os.path.abspath(value)
    if not os.path.isfile(path):
        raise ValueError(f"Input file not found: {value}")
    return path


def resolve_output(key="output"):
    value = params.get(key)
    if not value:
        raise ValueError(f"Missing required parameter: {key}")
    path = os.path.abspath(value)
    parent = os.path.dirname(path)
    if parent and not os.path.isdir(parent):
        os.makedirs(parent, exist_ok=True)
    return path


def infer_format(output_path, explicit=None):
    """Pick a Pillow format name from an explicit format arg or the output extension."""
    if explicit:
        key = str(explicit).lower()
        if key not in FORMAT_ALIASES:
            raise ValueError(f"Unsupported format: {explicit} (use png, jpeg, or webp)")
        return FORMAT_ALIASES[key]
    ext = os.path.splitext(output_path)[1].lower()
    if ext in EXT_TO_FORMAT:
        return EXT_TO_FORMAT[ext]
    raise ValueError(f"Cannot infer image format from output extension '{ext}'; pass a format")


def flatten_for_jpeg(img):
    """JPEG has no alpha channel — composite onto white and drop transparency/palette."""
    if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
        rgba = img.convert("RGBA")
        background = Image.new("RGB", rgba.size, (255, 255, 255))
        background.paste(rgba, mask=rgba.split()[-1])
        return background
    if img.mode != "RGB":
        return img.convert("RGB")
    return img


def save_image(img, output_path, fmt, quality=None):
    """Save img as fmt, handling JPEG's lack of alpha and optional quality."""
    save_kwargs = {}
    if fmt == "JPEG":
        img = flatten_for_jpeg(img)
        save_kwargs["quality"] = quality if quality is not None else 90
        save_kwargs["optimize"] = True
    elif fmt == "WEBP":
        if quality is not None:
            save_kwargs["quality"] = quality
    elif fmt == "PNG":
        save_kwargs["optimize"] = True
    img.save(output_path, format=fmt, **save_kwargs)


def clamp_int(value, default, minimum, maximum):
    try:
        return max(minimum, min(int(value), maximum))
    except (TypeError, ValueError):
        return default


# --- Tool handlers ---------------------------------------------------------

def info():
    path = resolve_input()
    with Image.open(path) as img:
        exif = img.info.get("exif")
        has_exif = bool(exif) or bool(getattr(img, "_getexif", lambda: None)())
        result = {
            "path": path,
            "width": img.width,
            "height": img.height,
            "format": img.format,
            "mode": img.mode,
            "hasExif": bool(has_exif),
        }
    print(json.dumps(result))


def resize():
    path = resolve_input()
    output = resolve_output()
    keep_aspect = params.get("keepAspect", True)
    if keep_aspect in ("false", "False", 0, "0"):
        keep_aspect = False
    width = params.get("width")
    height = params.get("height")
    if not width and not height:
        raise ValueError("resize requires at least one of: width, height")
    with Image.open(path) as img:
        orig_w, orig_h = img.width, img.height
        target_w = int(width) if width else None
        target_h = int(height) if height else None
        if keep_aspect:
            if target_w and target_h:
                ratio = min(target_w / orig_w, target_h / orig_h)
            elif target_w:
                ratio = target_w / orig_w
            else:
                ratio = target_h / orig_h
            new_w = max(1, round(orig_w * ratio))
            new_h = max(1, round(orig_h * ratio))
        else:
            new_w = target_w if target_w else orig_w
            new_h = target_h if target_h else orig_h
            new_w = max(1, new_w)
            new_h = max(1, new_h)
        resized = img.resize((new_w, new_h), Image.LANCZOS)
        fmt = infer_format(output, params.get("format"))
        save_image(resized, output, fmt)
    print(json.dumps({"output": output, "width": new_w, "height": new_h}))


def convert():
    path = resolve_input()
    output = resolve_output()
    fmt = infer_format(output, params.get("format"))
    with Image.open(path) as img:
        save_image(img, output, fmt)
    print(json.dumps({"output": output, "format": fmt}))


def crop():
    path = resolve_input()
    output = resolve_output()
    try:
        left = int(params["left"])
        top = int(params["top"])
        right = int(params["right"])
        bottom = int(params["bottom"])
    except (KeyError, TypeError, ValueError):
        raise ValueError("crop requires integer left, top, right, bottom")
    if right <= left or bottom <= top:
        raise ValueError("crop box must have right > left and bottom > top")
    with Image.open(path) as img:
        if left < 0 or top < 0 or right > img.width or bottom > img.height:
            raise ValueError(
                f"crop box ({left},{top},{right},{bottom}) exceeds image bounds "
                f"({img.width}x{img.height})"
            )
        cropped = img.crop((left, top, right, bottom))
        fmt = infer_format(output, params.get("format"))
        save_image(cropped, output, fmt)
    print(json.dumps({"output": output, "width": cropped.width, "height": cropped.height}))


def rotate():
    path = resolve_input()
    output = resolve_output()
    try:
        degrees = float(params["degrees"])
    except (KeyError, TypeError, ValueError):
        raise ValueError("rotate requires a numeric 'degrees'")
    expand = params.get("expand", True)
    if expand in ("false", "False", 0, "0"):
        expand = False
    with Image.open(path) as img:
        # PIL rotates counter-clockwise; negate so positive degrees is clockwise (intuitive).
        rotated = img.rotate(-degrees, expand=bool(expand))
        fmt = infer_format(output, params.get("format"))
        save_image(rotated, output, fmt)
    print(json.dumps({"output": output, "width": rotated.width, "height": rotated.height}))


def compress():
    path = resolve_input()
    output = resolve_output()
    quality = clamp_int(params.get("quality", 80), 80, 1, 95)
    with Image.open(path) as img:
        fmt = infer_format(output, params.get("format"))
        if fmt == "PNG":
            # PNG is lossless; quality doesn't apply. Re-save optimized.
            save_image(img, output, fmt)
        else:
            save_image(img, output, fmt, quality=quality)
    size = os.path.getsize(output)
    print(json.dumps({"output": output, "quality": quality, "format": fmt, "bytes": size}))


def thumbnail():
    path = resolve_input()
    output = resolve_output()
    size = clamp_int(params.get("size", 256), 256, 1, 10000)
    with Image.open(path) as img:
        thumb = img.copy()
        thumb.thumbnail((size, size), Image.LANCZOS)
        fmt = infer_format(output, params.get("format"))
        save_image(thumb, output, fmt)
    print(json.dumps({"output": output, "width": thumb.width, "height": thumb.height}))


def strip_exif():
    path = resolve_input()
    output = resolve_output()
    fmt = infer_format(output, params.get("format"))
    with Image.open(path) as img:
        # Re-save WITHOUT passing through img.info (so no exif bytes are written).
        save_image(img, output, fmt)
    # For JPEG, piexif.remove guarantees every EXIF/thumbnail segment is gone from the file.
    if fmt == "JPEG":
        try:
            piexif.remove(output)
        except Exception:  # noqa: BLE001 — nothing to remove is fine
            pass
    print(json.dumps({"output": output, "exifStripped": True}))


POSITIONS = {"top-left", "top-right", "bottom-left", "bottom-right", "center"}


def watermark():
    path = resolve_input()
    output = resolve_output()
    text = params.get("text")
    if not text:
        raise ValueError("watermark requires 'text'")
    position = params.get("position", "bottom-right")
    if position not in POSITIONS:
        raise ValueError(f"Invalid position '{position}' (use one of: {', '.join(sorted(POSITIONS))})")
    try:
        opacity = float(params.get("opacity", 0.5))
    except (TypeError, ValueError):
        opacity = 0.5
    opacity = max(0.0, min(opacity, 1.0))
    alpha = int(round(opacity * 255))

    with Image.open(path) as src:
        base = src.convert("RGBA")
        overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        # Scale font to the image; fall back to Pillow's built-in bitmap font.
        font_size = max(12, base.width // 20)
        try:
            font = ImageFont.truetype("DejaVuSans.ttf", font_size)
        except OSError:
            font = ImageFont.load_default()

        try:
            bbox = draw.textbbox((0, 0), text, font=font)
            text_w = bbox[2] - bbox[0]
            text_h = bbox[3] - bbox[1]
        except AttributeError:
            text_w, text_h = draw.textsize(text, font=font)

        margin = max(8, base.width // 50)
        if position == "top-left":
            xy = (margin, margin)
        elif position == "top-right":
            xy = (base.width - text_w - margin, margin)
        elif position == "bottom-left":
            xy = (margin, base.height - text_h - margin)
        elif position == "center":
            xy = ((base.width - text_w) // 2, (base.height - text_h) // 2)
        else:  # bottom-right
            xy = (base.width - text_w - margin, base.height - text_h - margin)

        draw.text(xy, text, fill=(255, 255, 255, alpha), font=font)
        combined = Image.alpha_composite(base, overlay)

        fmt = infer_format(output, params.get("format"))
        save_image(combined, output, fmt)
    print(json.dumps({"output": output, "text": text, "position": position}))


HANDLERS = {
    "image.info": info,
    "image.resize": resize,
    "image.convert": convert,
    "image.crop": crop,
    "image.rotate": rotate,
    "image.compress": compress,
    "image.thumbnail": thumbnail,
    "image.strip_exif": strip_exif,
    "image.watermark": watermark,
}

try:
    handler = HANDLERS.get(tool_name)
    if handler is None:
        print(json.dumps({"error": f"Unknown tool: {tool_name}"}))
    else:
        handler()
except (ValueError, OSError) as e:
    print(json.dumps({"error": str(e)}))
except Exception as e:  # noqa: BLE001
    print(json.dumps({"error": f"Unexpected error: {type(e).__name__}: {e}"}))
