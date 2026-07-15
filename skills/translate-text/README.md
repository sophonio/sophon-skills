# DeepL Translate

Machine translation from Sophon using the [DeepL API](https://www.deepl.com/pro-api): translate text
into 30+ languages with optional formality control, list supported source/target languages, and check
your account's character usage.

Implemented with the DeepL REST API v2 over the Python standard library (no dependencies), so it runs
in the sandbox unchanged.

## Tools

| Tool | Risk | Description |
|------|------|-------------|
| `translate.text` | low | Translate one string or an array of strings into a target language |
| `translate.list_languages` | none | List supported source or target languages |
| `translate.usage` | none | Get character usage and the plan limit |

Language codes are uppercased automatically (e.g. `en` → `EN`). Use regional codes where DeepL
supports them, e.g. `EN-GB`, `EN-US`, `PT-BR`. Formality (`more` / `less`) applies only to the
target languages that support it.

## Connection

Connect the **DeepL** integration with:

- **DeepL Auth Key** — your [DeepL API auth key](https://www.deepl.com/pro-api). Free-tier keys end
  in `:fx` and are routed to `api-free.deepl.com`; paid keys use `api.deepl.com`.

The auth key is stored in Sophon's credential vault and supplied to the skill at call time; it is
never written into the skill.

## Trademarks

DeepL is a trademark of DeepL SE. This is an unofficial, independently built integration and is not
affiliated with or endorsed by DeepL.
