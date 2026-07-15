"""Telegram integration skill — talks to the Telegram Bot API with a bot token.

Pure standard library (urllib) so it runs unchanged in the alpine Python sandbox with no pip
dependencies. `params` is injected as a global by the Sophon runtime and carries the tool name,
the tool arguments, and the connection-card credential field (botToken).
"""

import json
import urllib.request
import urllib.parse
import urllib.error

tool_name = params.get("tool", "")
bot_token = params.get("botToken", "")

API_BASE = "https://api.telegram.org"

HEADERS = {
    "Content-Type": "application/json",
    "User-Agent": "sophon-telegram-skill",
}


def request(method, http_method="POST", data=None, query=None):
    """Call a Telegram Bot API method. Returns the `result` payload, or raises on error.

    Telegram wraps every response in {ok, result} (or {ok:false, description}); this unwraps it.
    """
    url = f"{API_BASE}/bot{bot_token}/{method}"
    if query:
        clean = {k: v for k, v in query.items() if v not in (None, "")}
        if clean:
            url = f"{url}?{urllib.parse.urlencode(clean)}"
    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(url, data=body, headers=HEADERS, method=http_method)
    try:
        with urllib.request.urlopen(req) as resp:
            payload = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        detail = e.read().decode() if e.fp else ""
        try:
            parsed = json.loads(detail)
            description = parsed.get("description") or detail
        except (ValueError, AttributeError):
            description = detail
        raise RuntimeError(f"Telegram API error {e.code}: {description}") from e
    if not payload.get("ok", False):
        raise RuntimeError(payload.get("description", "Telegram API returned ok=false"))
    return payload.get("result")


def clamp(value, default, maximum):
    try:
        return max(1, min(int(value), maximum))
    except (TypeError, ValueError):
        return default


# --- Tool handlers ---------------------------------------------------------

def get_me():
    result = request("getMe", http_method="GET")
    print(json.dumps(result))


def send_message():
    payload = {
        "chat_id": params.get("chatId", ""),
        "text": params.get("text", ""),
    }
    if params.get("parseMode"):
        payload["parse_mode"] = params["parseMode"]
    if params.get("disableNotification") is not None:
        payload["disable_notification"] = bool(params["disableNotification"])
    result = request("sendMessage", data=payload)
    print(json.dumps(result))


def send_photo():
    payload = {
        "chat_id": params.get("chatId", ""),
        "photo": params.get("photo", ""),
    }
    if params.get("caption"):
        payload["caption"] = params["caption"]
    result = request("sendPhoto", data=payload)
    print(json.dumps(result))


def send_document():
    payload = {
        "chat_id": params.get("chatId", ""),
        "document": params.get("document", ""),
    }
    if params.get("caption"):
        payload["caption"] = params["caption"]
    result = request("sendDocument", data=payload)
    print(json.dumps(result))


def get_updates():
    result = request("getUpdates", http_method="GET", query={
        "offset": params.get("offset"),
        "limit": clamp(params.get("limit", 100), 100, 100),
    })
    updates = result if isinstance(result, list) else []
    print(json.dumps({"count": len(updates), "updates": updates}))


HANDLERS = {
    "telegram.get_me": get_me,
    "telegram.send_message": send_message,
    "telegram.send_photo": send_photo,
    "telegram.send_document": send_document,
    "telegram.get_updates": get_updates,
}

try:
    handler = HANDLERS.get(tool_name)
    if handler is None:
        print(json.dumps({"error": f"Unknown tool: {tool_name}"}))
    elif not bot_token:
        print(json.dumps({"error": "Missing Telegram credential: connect the Telegram integration first."}))
    else:
        handler()
except (RuntimeError, ValueError) as e:
    print(json.dumps({"error": str(e)}))
except Exception as e:  # noqa: BLE001
    print(json.dumps({"error": f"Unexpected error: {type(e).__name__}: {e}"}))
