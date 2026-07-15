# Discord

Send messages and rich embeds to Discord, and — with a bot token — read channels and post anywhere
the bot can reach. Works with either an incoming **webhook URL** (send-only, no bot required) or a
**bot token** (read + send).

Implemented with the Discord API v10 over the Python standard library (no dependencies), so it runs
in the sandbox unchanged.

## Tools

| Tool | Risk | Description |
|------|------|-------------|
| `discord.send_message` | high | Send a text message via webhook or bot |
| `discord.send_embed` | high | Send a rich embed (title, description, color, link) |
| `discord.list_messages` | none | List recent messages in a channel (bot token) |
| `discord.get_channel` | none | Get channel metadata (bot token) |

Sends are outbound and marked high-risk so Sophon can gate them behind approval.

## Connection

Connect the **Discord** integration with either (or both):

- **Webhook URL** — an [incoming webhook](https://support.discord.com/hc/en-us/articles/228383668)
  for a single channel. Enough for `discord.send_message` and `discord.send_embed`; no bot needed.
- **Bot Token** — a [bot token](https://discord.com/developers/applications) for a Discord
  application. Required to read channels (`discord.list_messages`, `discord.get_channel`) and to
  send to any channel the bot can access (pass `channelId`).

Send tools prefer a webhook when one is supplied (per-message `webhookUrl` argument or the configured
field); otherwise they use the bot token with `channelId`. Read tools always require a bot token.

Credentials are stored in Sophon's credential vault and supplied to the skill at call time; they are
never written into the skill.

## Trademarks

Discord is a trademark of Discord Inc. This is an unofficial, independently built integration and is
not affiliated with or endorsed by Discord.
