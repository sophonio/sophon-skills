"""DeepL translation skill — talks to the DeepL REST API v2 with an auth key.

Pure standard library (urllib) so it runs unchanged in the alpine Python sandbox with no pip
dependencies. `params` is injected as a global by the Sophon runtime and carries the tool name,
the tool arguments, and the connection-card credential field (authKey).

Host selection: free-tier keys (ending in ':fx') use api-free.deepl.com; paid keys use
api.deepl.com. Requests are authenticated with the `Authorization: DeepL-Auth-Key <key>` header.
"""

import json
import urllib.request
import urllib.parse
import urllib.error

tool_name = params.get("tool", "")
auth_key = params.get("authKey", "")

api_base = "https://api-free.deepl.com" if auth_key.endswith(":fx") else "https://api.deepl.com"

HEADERS = {
    "Authorization": f"DeepL-Auth-Key {auth_key}",
    "User-Agent": "sophon-translate-text-skill",
    "Content-Type": "application/json",
}


def request(method, path, data=None, query=None):
    """Make an authenticated request to the DeepL API. Returns parsed JSON (or None for empty)."""
    url = f"{api_base}{path}"
    if query:
        clean = {k: v for k, v in query.items() if v not in (None, "")}
        if clean:
            url = f"{url}?{urllib.parse.urlencode(clean)}"
    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(url, data=body, headers=HEADERS, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read().decode()
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        detail = e.read().decode() if e.fp else ""
        raise RuntimeError(f"DeepL API error {e.code}: {detail}") from e


# --- Tool handlers ---------------------------------------------------------

def translate_text():
    text = params.get("text")
    if text is None or text == "":
        raise ValueError("text is required")
    if isinstance(text, str):
        text = [text]
    elif not isinstance(text, list):
        raise ValueError("text must be a string or an array of strings")

    target = (params.get("targetLang") or "").upper()
    if not target:
        raise ValueError("targetLang is required")

    payload = {"text": text, "target_lang": target}
    source = params.get("sourceLang")
    if source:
        payload["source_lang"] = source.upper()
    formality = params.get("formality")
    if formality:
        payload["formality"] = formality

    result = request("POST", "/v2/translate", data=payload)
    translations = [
        {
            "detectedSourceLang": t.get("detected_source_language"),
            "text": t.get("text"),
        }
        for t in (result or {}).get("translations", [])
    ]
    print(json.dumps({"translations": translations}))


def list_languages():
    result = request("GET", "/v2/languages", query={"type": params.get("type", "target")})
    languages = [
        {
            "language": lang.get("language"),
            "name": lang.get("name"),
            "supportsFormality": lang.get("supports_formality"),
        }
        for lang in (result or [])
    ]
    print(json.dumps({"count": len(languages), "languages": languages}))


def usage():
    result = request("GET", "/v2/usage") or {}
    print(json.dumps({
        "characterCount": result.get("character_count"),
        "characterLimit": result.get("character_limit"),
    }))


HANDLERS = {
    "translate.text": translate_text,
    "translate.list_languages": list_languages,
    "translate.usage": usage,
}

try:
    handler = HANDLERS.get(tool_name)
    if handler is None:
        print(json.dumps({"error": f"Unknown tool: {tool_name}"}))
    elif not auth_key:
        print(json.dumps({"error": "Missing DeepL credential: connect the DeepL integration first."}))
    else:
        handler()
except (RuntimeError, ValueError) as e:
    print(json.dumps({"error": str(e)}))
except Exception as e:  # noqa: BLE001
    print(json.dumps({"error": f"Unexpected error: {type(e).__name__}: {e}"}))
