"""PDF toolkit skill — local PDF operations with no network access.

Uses pypdf for structural operations (merge/split/rotate/encrypt/decrypt/metadata/text)
and pdfplumber for table extraction. `params` is injected as a global by the Sophon runtime
and carries the tool name and the tool's call arguments. File paths are resolved against the
current working directory; outputs are written into the cwd. The single stdout line is a
json.dumps of the result.
"""

import json
import os

tool_name = params.get("tool", "")


def resolve(path):
    """Resolve a possibly-relative path against the current working directory."""
    if not path:
        raise ValueError("a file path is required")
    return path if os.path.isabs(path) else os.path.abspath(os.path.join(os.getcwd(), path))


def require_input(path):
    """Resolve an input path and ensure it exists, else raise NotFound."""
    resolved = resolve(path)
    if not os.path.isfile(resolved):
        raise FileNotFoundError(f"input not found: {path}")
    return resolved


def parse_ranges(spec, page_count):
    """Parse a '1-3,5,8-10' style spec into a list of (start, end) 0-based inclusive tuples."""
    ranges = []
    for chunk in str(spec).split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        if "-" in chunk:
            lo_s, hi_s = chunk.split("-", 1)
            lo, hi = int(lo_s), int(hi_s)
        else:
            lo = hi = int(chunk)
        if lo < 1 or hi < 1 or lo > hi:
            raise ValueError(f"invalid range: {chunk}")
        if hi > page_count:
            raise ValueError(f"range {chunk} exceeds page count {page_count}")
        ranges.append((lo - 1, hi - 1))
    if not ranges:
        raise ValueError("no valid ranges provided")
    return ranges


def page_indices(pages, page_count):
    """Convert an optional list of 1-based page numbers to sorted 0-based indices (all if None)."""
    if not pages:
        return list(range(page_count))
    indices = []
    for p in pages:
        idx = int(p)
        if idx < 1 or idx > page_count:
            raise ValueError(f"page {idx} out of range (1..{page_count})")
        indices.append(idx - 1)
    return indices


# --- Tool handlers ---------------------------------------------------------

def merge():
    inputs = params.get("inputs") or []
    if not isinstance(inputs, list) or not inputs:
        raise ValueError("inputs must be a non-empty array of PDF paths")
    output = resolve(params.get("output"))
    sources = [require_input(item) for item in inputs]

    from pypdf import PdfWriter

    writer = PdfWriter()
    try:
        for src in sources:
            writer.append(src)
        with open(output, "wb") as fh:
            writer.write(fh)
    finally:
        writer.close()
    print(json.dumps({"output": output, "merged": len(inputs)}))


def split():
    src = require_input(params.get("input"))

    from pypdf import PdfReader, PdfWriter

    out_dir = resolve(params.get("outputDir")) if params.get("outputDir") else os.getcwd()
    os.makedirs(out_dir, exist_ok=True)

    reader = PdfReader(src)
    page_count = len(reader.pages)
    stem = os.path.splitext(os.path.basename(src))[0]
    outputs = []

    ranges_spec = params.get("ranges")
    if ranges_spec:
        for (lo, hi) in parse_ranges(ranges_spec, page_count):
            writer = PdfWriter()
            for i in range(lo, hi + 1):
                writer.add_page(reader.pages[i])
            label = f"{lo + 1}" if lo == hi else f"{lo + 1}-{hi + 1}"
            out_path = os.path.join(out_dir, f"{stem}_pages_{label}.pdf")
            with open(out_path, "wb") as fh:
                writer.write(fh)
            writer.close()
            outputs.append(out_path)
    else:
        width = len(str(page_count))
        for i in range(page_count):
            writer = PdfWriter()
            writer.add_page(reader.pages[i])
            out_path = os.path.join(out_dir, f"{stem}_page_{str(i + 1).zfill(width)}.pdf")
            with open(out_path, "wb") as fh:
                writer.write(fh)
            writer.close()
            outputs.append(out_path)

    print(json.dumps({"outputs": outputs, "count": len(outputs)}))


def rotate():
    src = require_input(params.get("input"))
    output = resolve(params.get("output"))
    degrees = int(params.get("degrees"))
    if degrees not in (90, 180, 270):
        raise ValueError("degrees must be one of 90, 180, 270")

    from pypdf import PdfReader, PdfWriter

    reader = PdfReader(src)
    page_count = len(reader.pages)
    targets = set(page_indices(params.get("pages"), page_count))

    writer = PdfWriter()
    for i, page in enumerate(reader.pages):
        if i in targets:
            page.rotate(degrees)
        writer.add_page(page)
    with open(output, "wb") as fh:
        writer.write(fh)
    writer.close()
    print(json.dumps({"output": output, "rotated": sorted(t + 1 for t in targets), "degrees": degrees}))


def extract_text():
    src = require_input(params.get("input"))

    from pypdf import PdfReader

    reader = PdfReader(src)
    page_count = len(reader.pages)
    indices = page_indices(params.get("pages"), page_count)

    per_page = []
    for i in indices:
        text = reader.pages[i].extract_text() or ""
        per_page.append({"page": i + 1, "text": text})
    full = "\n\n".join(p["text"] for p in per_page)
    print(json.dumps({"text": full, "pages": per_page, "pageCount": page_count}))


def extract_tables():
    src = require_input(params.get("input"))

    import pdfplumber

    result = []
    with pdfplumber.open(src) as pdf:
        page_count = len(pdf.pages)
        indices = page_indices(params.get("pages"), page_count)
        for i in indices:
            tables = pdf.pages[i].extract_tables() or []
            result.append({"page": i + 1, "tables": tables})
    print(json.dumps({"pages": result, "pageCount": page_count}))


def metadata():
    src = require_input(params.get("input"))

    from pypdf import PdfReader

    reader = PdfReader(src)
    meta = reader.metadata or {}
    info = {}
    for key, value in dict(meta).items():
        k = key[1:] if isinstance(key, str) and key.startswith("/") else str(key)
        info[k] = str(value) if value is not None else None
    print(json.dumps({
        "pageCount": len(reader.pages),
        "encrypted": bool(getattr(reader, "is_encrypted", False)),
        "metadata": info,
    }))


def encrypt():
    src = require_input(params.get("input"))
    output = resolve(params.get("output"))
    password = params.get("password")
    if not password:
        raise ValueError("password is required")

    from pypdf import PdfReader, PdfWriter

    reader = PdfReader(src)
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    writer.encrypt(str(password))
    with open(output, "wb") as fh:
        writer.write(fh)
    writer.close()
    print(json.dumps({"output": output, "encrypted": True}))


def decrypt():
    src = require_input(params.get("input"))
    output = resolve(params.get("output"))
    password = params.get("password")
    if password is None:
        raise ValueError("password is required")

    from pypdf import PdfReader, PdfWriter

    reader = PdfReader(src)
    if reader.is_encrypted:
        result = reader.decrypt(str(password))
        if result == 0:
            raise ValueError("incorrect password: could not decrypt the PDF")
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    with open(output, "wb") as fh:
        writer.write(fh)
    writer.close()
    print(json.dumps({"output": output, "decrypted": True}))


HANDLERS = {
    "pdf.merge": merge,
    "pdf.split": split,
    "pdf.rotate": rotate,
    "pdf.extract_text": extract_text,
    "pdf.extract_tables": extract_tables,
    "pdf.metadata": metadata,
    "pdf.encrypt": encrypt,
    "pdf.decrypt": decrypt,
}

try:
    handler = HANDLERS.get(tool_name)
    if handler is None:
        print(json.dumps({"error": f"Unknown tool: {tool_name}"}))
    else:
        handler()
except FileNotFoundError as e:
    print(json.dumps({"error": str(e)}))
except (ValueError, TypeError) as e:
    print(json.dumps({"error": str(e)}))
except Exception as e:  # noqa: BLE001
    print(json.dumps({"error": f"{type(e).__name__}: {e}"}))
