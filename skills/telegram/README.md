# Telegram

Drive a Telegram bot from Sophon: send text messages, photos, and documents to chats and channels,
and read the updates people send back to the bot.

Implemented with the Telegram Bot API over the Python standard library (no dependencies), so it runs
in the sandbox unchanged.

## Tools

| Tool | Risk | Description |
|------|------|-------------|
| `telegram.get_me` | none | Get basic info about the bot (verifies the token) |
| `telegram.send_message` | high | Send a text message to a chat |
| `telegram.send_photo` | high | Send a photo to a chat by URL |
| `telegram.send_document` | high | Send a document/file to a chat by URL |
| `telegram.get_updates` | none | Get recent messages and events sent to the bot |

Chats are addressed by numeric `chatId` or by `@channelusername`. Photos and documents are supplied
as HTTP URLs, which Telegram fetches and delivers.

## Connection

Connect the **Telegram** integration with:

- **Bot Token** — create a bot by messaging [@BotFather](https://core.telegram.org/bots#botfather)
  and paste the token it gives you (looks like `123456:ABC-DEF...`).

The token is stored in Sophon's credential vault and supplied to the skill at call time; it is never
written into the skill.

## Notes

- Sending tools (`send_message`, `send_photo`, `send_document`) produce outbound messages to real
  users and are marked high-risk so Sophon can gate them behind approval.
- `telegram.get_updates` uses long-polling semantics: pass `offset` = the last `update_id` + 1 to
  acknowledge previous updates and avoid re-fetching them. It does not work while a webhook is set.
- Telegram wraps responses in `{ok, result}`; this skill surfaces `result` directly, and turns
  `ok:false` responses into an `{ "error": ... }` result.

## Trademarks

Telegram is a trademark of Telegram FZ-LLC / Telegram Messenger Inc. This is an unofficial,
independently built integration and is not affiliated with or endorsed by Telegram.
