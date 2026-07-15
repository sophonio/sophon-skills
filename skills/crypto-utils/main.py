"""Offline cryptographic and encoding utilities.

Runs fully local in the alpine Python sandbox: no network, no credentials. `params` is injected
as a global by the Sophon runtime and carries the tool name and the tool's call arguments.

Everything here is pure compute over the Python standard library (hashlib, hmac, secrets, base64,
binascii, string, urllib.parse). No file I/O, no outbound requests.
"""

import json
import hashlib
import hmac
import secrets
import base64
import binascii
import string
import urllib.parse

tool_name = params.get("tool", "")

HASH_ALGOS = {"md5", "sha1", "sha256", "sha384", "sha512"}


def resolve_algo(name, default="sha256"):
    algo = (name or default).lower()
    if algo not in HASH_ALGOS:
        raise ValueError(f"algorithm must be one of: {', '.join(sorted(HASH_ALGOS))}")
    return algo


def b64url_decode(segment):
    """Base64url-decode a string, adding the padding JWT segments omit."""
    if isinstance(segment, str):
        segment = segment.encode("ascii")
    padding = b"=" * (-len(segment) % 4)
    return base64.urlsafe_b64decode(segment + padding)


def b64url_encode(raw):
    """Base64url-encode bytes without padding (JWT style)."""
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


# --- Tool handlers ---------------------------------------------------------

def do_hash():
    algo = resolve_algo(params.get("algorithm"))
    data_b64 = params.get("dataBase64")
    if data_b64 not in (None, ""):
        try:
            data = base64.b64decode(data_b64, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise ValueError(f"dataBase64 is not valid base64: {exc}") from exc
    else:
        data = (params.get("text") or "").encode("utf-8")
    digest = hashlib.new(algo, data).hexdigest()
    print(json.dumps({"algorithm": algo, "hex": digest, "bytes": len(data)}))


def do_hmac():
    algo = resolve_algo(params.get("algorithm"))
    text = params.get("text")
    key = params.get("key")
    if not isinstance(text, str):
        raise ValueError("missing 'text'")
    if not isinstance(key, str) or key == "":
        raise ValueError("missing 'key'")
    mac = hmac.new(key.encode("utf-8"), text.encode("utf-8"), algo).hexdigest()
    print(json.dumps({"algorithm": algo, "hex": mac}))


def jwt_decode():
    token = params.get("token")
    if not isinstance(token, str) or token == "":
        raise ValueError("missing 'token'")
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("token is not a well-formed JWT (expected header.payload.signature)")
    header_raw, payload_raw, signature_raw = parts
    try:
        header = json.loads(b64url_decode(header_raw))
        payload = json.loads(b64url_decode(payload_raw))
    except (binascii.Error, ValueError, UnicodeDecodeError) as exc:
        raise ValueError(f"could not base64url-decode JWT segments: {exc}") from exc

    result = {"header": header, "payload": payload}

    secret = params.get("secret")
    if secret in (None, ""):
        result["valid"] = None
        result["note"] = "signature not verified (no secret provided)"
        print(json.dumps(result))
        return

    alg = (params.get("algorithm") or header.get("alg") or "HS256").upper()
    if alg[:2] in ("RS", "ES", "PS"):
        result["valid"] = None
        result["note"] = "signature not verified (asymmetric alg)"
        print(json.dumps(result))
        return

    hs_map = {"HS256": "sha256", "HS384": "sha384", "HS512": "sha512"}
    if alg not in hs_map:
        result["valid"] = None
        result["note"] = f"signature not verified (unsupported alg: {alg})"
        print(json.dumps(result))
        return

    signing_input = f"{header_raw}.{payload_raw}".encode("ascii")
    expected = hmac.new(secret.encode("utf-8"), signing_input, hs_map[alg]).digest()
    try:
        actual = b64url_decode(signature_raw)
    except (binascii.Error, ValueError) as exc:
        raise ValueError(f"could not base64url-decode signature: {exc}") from exc
    result["valid"] = hmac.compare_digest(expected, actual)
    print(json.dumps(result))


def generate_token():
    try:
        length = int(params.get("length", 32))
    except (TypeError, ValueError):
        raise ValueError("length must be an integer")
    if length < 1:
        raise ValueError("length must be at least 1")
    fmt = (params.get("format") or "hex").lower()
    if fmt == "hex":
        token = secrets.token_hex(length)
    elif fmt == "urlsafe":
        token = secrets.token_urlsafe(length)
    elif fmt == "base64":
        token = base64.b64encode(secrets.token_bytes(length)).decode("ascii")
    else:
        raise ValueError("format must be one of: hex, urlsafe, base64")
    print(json.dumps({"format": fmt, "bytes": length, "token": token}))


def generate_password():
    try:
        length = int(params.get("length", 20))
    except (TypeError, ValueError):
        raise ValueError("length must be an integer")
    use_symbols = params.get("symbols", True)
    if isinstance(use_symbols, str):
        use_symbols = use_symbols.strip().lower() not in ("false", "0", "no", "")
    else:
        use_symbols = bool(use_symbols)

    classes = [string.ascii_lowercase, string.ascii_uppercase, string.digits]
    if use_symbols:
        classes.append(string.punctuation)

    min_length = len(classes)
    if length < min_length:
        raise ValueError(f"length must be at least {min_length} to include each character class")

    alphabet = "".join(classes)
    # Guarantee at least one character from each selected class.
    chars = [secrets.choice(cls) for cls in classes]
    chars += [secrets.choice(alphabet) for _ in range(length - min_length)]
    # Shuffle so the guaranteed characters are not always at the front.
    for i in range(len(chars) - 1, 0, -1):
        j = secrets.randbelow(i + 1)
        chars[i], chars[j] = chars[j], chars[i]
    password = "".join(chars)
    print(json.dumps({"length": length, "symbols": use_symbols, "password": password}))


def encode():
    text = params.get("text")
    if not isinstance(text, str):
        raise ValueError("missing 'text'")
    encoding = (params.get("encoding") or "").lower()
    raw = text.encode("utf-8")
    if encoding == "base64":
        out = base64.b64encode(raw).decode("ascii")
    elif encoding == "base64url":
        out = base64.urlsafe_b64encode(raw).decode("ascii")
    elif encoding == "hex":
        out = raw.hex()
    elif encoding == "url":
        out = urllib.parse.quote(text, safe="")
    else:
        raise ValueError("encoding must be one of: base64, base64url, hex, url")
    print(json.dumps({"encoding": encoding, "output": out}))


def decode():
    text = params.get("text")
    if not isinstance(text, str):
        raise ValueError("missing 'text'")
    encoding = (params.get("encoding") or "").lower()
    try:
        if encoding == "base64":
            raw = base64.b64decode(text, validate=True)
        elif encoding == "base64url":
            data = text.encode("ascii")
            data += b"=" * (-len(data) % 4)
            raw = base64.urlsafe_b64decode(data)
        elif encoding == "hex":
            raw = bytes.fromhex(text)
        elif encoding == "url":
            print(json.dumps({"encoding": encoding, "output": urllib.parse.unquote(text)}))
            return
        else:
            raise ValueError("encoding must be one of: base64, base64url, hex, url")
    except (binascii.Error, ValueError) as exc:
        raise ValueError(f"could not decode {encoding}: {exc}") from exc
    try:
        out = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"decoded bytes are not valid UTF-8: {exc}") from exc
    print(json.dumps({"encoding": encoding, "output": out}))


HANDLERS = {
    "crypto.hash": do_hash,
    "crypto.hmac": do_hmac,
    "crypto.jwt_decode": jwt_decode,
    "crypto.generate_token": generate_token,
    "crypto.generate_password": generate_password,
    "crypto.encode": encode,
    "crypto.decode": decode,
}

try:
    handler = HANDLERS.get(tool_name)
    if handler is None:
        print(json.dumps({"error": f"Unknown tool: {tool_name}"}))
    else:
        handler()
except ValueError as e:
    print(json.dumps({"error": str(e)}))
except Exception as e:  # noqa: BLE001
    print(json.dumps({"error": f"Unexpected error: {type(e).__name__}: {e}"}))
