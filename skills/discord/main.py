"""Discord integration skill — sends messages/embeds and reads channels via the Discord API v10.

Two auth modes, both optional: an incoming WEBHOOK URL (send-only) or a BOT token (read + send).
Pure standard library (urllib) so it runs unchanged in the alpine Python sandbox with no pip
dependencies. `params` is injected as a global by the Sophon runtime and carries the tool name,
the tool arguments, and the connection-card credential fields (webhookUrl, botToken).
"""

import json
import urllib.request
import urllib.parse
import urllib.error

API_BASE = "https://discord.com/api/v10"

tool_name = params.get("tool", "")
webhook_url = params.get("webhookUrl") or ""
bot_token = params.get("botToken") or ""


def request(method, url, data=None, headers=None):
    """Make an HTTP request. Returns parsed JSON (or None for empty/204 responses)."""
    body = json.dumps(data).encode() if data is not None else None
    hdrs = {
        "User-Agent": "sophon-discord-skill",
        "Content-Type": "application/json",
    }
    if headers:
        hdrs.update(headers)
    req = urllib.request.Request(url, data=body, headers=hdrs, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read().decode()
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        detail = e.read().decode() if e.fp else ""
        raise RuntimeError(f"Discord API error {e.code}: {detail}") from e


def bot_headers():
    return {"Authorization": f"Bot {bot_token}"}


def clamp(value, default, maximum):
    try:
        return max(1, min(int(value), maximum))
    except (TypeError, ValueError):
        return default


def send_via_webhook(url, payload):
    """POST to a webhook URL; wait=true so Discord returns the created message."""
    sep = "&" if "?" in url else "?"
    result = request("POST", f"{url}{sep}wait=true", data=payload)
    return {
        "status": "sent",
        "via": "webhook",
        "id": (result or {}).get("id"),
        "channelId": (result or {}).get("channel_id"),
    }


def send_via_bot(channel_id, payload):
    """POST a message to a channel using the bot token."""
    result = request(
        "POST",
        f"{API_BASE}/channels/{channel_id}/messages",
        data=payload,
        headers=bot_headers(),
    )
    return {
        "status": "sent",
        "via": "bot",
        "id": (result or {}).get("id"),
        "channelId": (result or {}).get("channel_id"),
    }


def message_summary(msg):
    return {
        "id": msg.get("id"),
        "content": msg.get("content"),
        "author": (msg.get("author") or {}).get("username"),
        "authorId": (msg.get("author") or {}).get("id"),
        "timestamp": msg.get("timestamp"),
        "embeds": len(msg.get("embeds", [])),
        "attachments": len(msg.get("attachments", [])),
    }


# --- Tool handlers ---------------------------------------------------------

def send_message():
    content = params.get("content")
    if not content:
        raise ValueError("content is required")
    hook = params.get("webhookUrl") or webhook_url
    if hook:
        payload = {"content": content}
        if params.get("username"):
            payload["username"] = params["username"]
        print(json.dumps(send_via_webhook(hook, payload)))
        return
    channel_id = params.get("channelId")
    if bot_token and channel_id:
        print(json.dumps(send_via_bot(channel_id, {"content": content})))
        return
    raise ValueError(
        "Provide a webhookUrl (arg or configured), or a botToken plus channelId, to send."
    )


def send_embed():
    title = params.get("title")
    if not title:
        raise ValueError("title is required")
    embed = {"title": title}
    if params.get("description"):
        embed["description"] = params["description"]
    if params.get("url"):
        embed["url"] = params["url"]
    if params.get("color") is not None:
        try:
            embed["color"] = int(params["color"])
        except (TypeError, ValueError):
            raise ValueError("color must be an integer")
    payload = {"embeds": [embed]}
    hook = params.get("webhookUrl") or webhook_url
    if hook:
        if params.get("username"):
            payload["username"] = params["username"]
        print(json.dumps(send_via_webhook(hook, payload)))
        return
    channel_id = params.get("channelId")
    if bot_token and channel_id:
        print(json.dumps(send_via_bot(channel_id, payload)))
        return
    raise ValueError(
        "Provide a webhookUrl (arg or configured), or a botToken plus channelId, to send."
    )


def list_messages():
    if not bot_token:
        raise ValueError("botToken required for this tool")
    channel_id = params.get("channelId")
    if not channel_id:
        raise ValueError("channelId is required")
    limit = clamp(params.get("limit", 20), 20, 100)
    url = f"{API_BASE}/channels/{channel_id}/messages?{urllib.parse.urlencode({'limit': limit})}"
    result = request("GET", url, headers=bot_headers())
    messages = [message_summary(m) for m in (result or [])]
    print(json.dumps({"count": len(messages), "messages": messages}))


def get_channel():
    if not bot_token:
        raise ValueError("botToken required for this tool")
    channel_id = params.get("channelId")
    if not channel_id:
        raise ValueError("channelId is required")
    channel = request("GET", f"{API_BASE}/channels/{channel_id}", headers=bot_headers())
    channel = channel or {}
    print(json.dumps({
        "id": channel.get("id"),
        "name": channel.get("name"),
        "type": channel.get("type"),
        "guildId": channel.get("guild_id"),
        "topic": channel.get("topic"),
        "parentId": channel.get("parent_id"),
        "nsfw": channel.get("nsfw"),
        "position": channel.get("position"),
    }))


HANDLERS = {
    "discord.send_message": send_message,
    "discord.send_embed": send_embed,
    "discord.list_messages": list_messages,
    "discord.get_channel": get_channel,
}

try:
    handler = HANDLERS.get(tool_name)
    if handler is None:
        print(json.dumps({"error": f"Unknown tool: {tool_name}"}))
    else:
        handler()
except (RuntimeError, ValueError) as e:
    print(json.dumps({"error": str(e)}))
except Exception as e:  # noqa: BLE001
    print(json.dumps({"error": f"Unexpected error: {type(e).__name__}: {e}"}))
