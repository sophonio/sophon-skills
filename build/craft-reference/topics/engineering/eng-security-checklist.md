---
id: eng-security-checklist
summary: Ten vulnerability classes with sources, sinks and the defences that count, plus the high-miss patterns.
reviewed: 2026-11
---
# Security checklist by class, with the high-miss patterns

A finding names a source an attacker controls, a sink that does harm with it, and the missing defence on the path between them. The rows follow the security reviewer's ten classes.

## Checklist by class

| Class | Sources | Sinks | Defences that count |
|---|---|---|---|
| 1 Injection | request fields, headers, file contents, queue messages, model output | string-built SQL or NoSQL queries; a shell string (`exec`, `system`, `shell=True`); `eval`, `Function`, template compilation of input | bound parameters; an argument array with no shell; a fixed allowlist of values; no evaluation of input |
| 2 Paths and files | file names, archive entries, URL path segments | file open, write, delete; archive extraction; static file serving | resolve the real path, then require it inside the base folder; reject absolute paths and `..`; refuse symlinks in archives |
| 3 Access control | object ids in the URL or body, tenant ids, role claims from the client | a fetch or update by id; an admin route; a list query | an owner or tenant filter in the query itself; a role check on the server for every route, read from the session |
| 4 Mass assignment | the whole request body | ORM create or update from a spread or a bound model | an explicit list of writable fields; a separate input type without role, owner or price fields |
| 5 Server-side fetch | a URL, host or webhook target from the caller | an HTTP client, image fetcher, PDF renderer, XML loader | an allowlist of schemes and hosts; private, loopback and link-local addresses refused after DNS resolution and after each redirect |
| 6 Deserialisation and XML | uploaded files, cookies, cached blobs | `pickle`, `yaml.load` without the safe loader, Java or .NET binary formatters, XML parsers with external entities on | data-only formats (JSON) into typed models; safe loaders; entity resolution off |
| 7 Transport and crypto | n/a: the code itself | TLS checks turned off; MD5, SHA-1 or a plain fast hash for passwords; ECB mode; a fixed IV; `Math.random` for ids or reset codes; a key in source | platform TLS defaults; bcrypt, scrypt or Argon2 for passwords; an AEAD mode; the platform's secure random source; keys from a secret store |
| 8 Sensitive data exposure | passwords, keys, session values, personal data | log calls, URLs and query strings, error bodies, analytics events, client bundles | redaction at the logger; values kept out of URLs; generic error bodies; server-only config kept out of the bundle |
| 9 Web | user text shown in pages; cookie-authenticated state changes; cross-origin requests | `innerHTML`, `dangerouslySetInnerHTML`, `v-html`, unescaped template output; state changes with no CSRF check; CORS that echoes the Origin with credentials | framework escaping; a sanitiser with an allowlist; SameSite cookies plus a CSRF check; a fixed list of allowed origins |
| 10 Agent and LLM flows | web pages, files, issues, emails, tool results read by a model | a tool that writes, deletes, pays, runs commands or calls out | a person approves side effects; tool scope limited to the task; untrusted text kept apart from the instructions; output encoded before display |

## High miss

These patterns sit outside the hunk that introduced them, so a line-by-line read passes over them.

| Pattern | Sign | Example | Defence |
|---|---|---|---|
| Parser differential | two components read one input | the validator parses a URL with one library and the fetcher with another; one sees the host before `@`, the other after | one parser for check and use; pass the parsed value on, not the raw string |
| Gate and action mismatch | the check and the act use different fields | the check reads `body.accountId`, the update uses `params.id` | read the id once; check and act on that same value |
| Fail-open | an error path that continues | `except Exception: allowed = True`; a missing policy treated as allow | deny on error; a missing rule denies |
| Control regression | a deleted or loosened check | a validator removed in a refactor; a regex anchor dropped | find what the old check stopped; keep a test for it |
| Allowlist escape | a match on text, not meaning | `host.startswith("good")` accepts any longer host with that prefix; an unanchored regex | compare the exact parsed host; anchor the whole pattern |
| Argument smuggling | input placed in a command's argument list | a branch name of `--upload-pack=<cmd>` given to git | a `--` separator before user values; reject values that start with `-` |
| Environment injection | caller-set environment for a child process | `NODE_OPTIONS`, `LD_PRELOAD`, `PATH` or `PYTHONPATH` taken from the request | a fixed environment; an allowlist of variable names |
| Lexical path check | prefix test on an unresolved path | `path.startswith(base)` before symlinks are resolved | resolve the real path first, then compare |
| Redirect and DNS tricks | a fetch checked once | the first host is public, a redirect or second DNS answer points inside the network | check the address on every hop; pin the resolved address for the connection |
| Sibling parity | one handler fixed, its twin not | the update route gains an owner check, the delete route does not | list every sibling route and branch; each gets the same check |
| Logging-only control | a guard that records and continues | "suspicious request" written to the log, then served | block, or document why monitoring is enough |
| Time of check, time of use | a check, then a later act on a name | `exists(path)` then `open(path)` | open once and check the handle; use database constraints over prior reads |

After a confirmed finding, search the codebase for the same shape: the exact call first, then one element generalised at a time.
