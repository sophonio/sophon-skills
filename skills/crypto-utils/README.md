# Crypto Utils

Offline cryptographic and encoding helpers built entirely on the Python standard library
(`hashlib`, `hmac`, `secrets`, `base64`, `binascii`, `urllib.parse`). No dependencies, no network,
and no credentials — every tool is pure local compute and runs in the sandbox unchanged.

## Tools

| Tool | Risk | Description |
|------|------|-------------|
| `crypto.hash` | none | Hex digest of text (UTF-8) or base64 bytes with md5/sha1/sha256/sha384/sha512 |
| `crypto.hmac` | none | Hex HMAC of a message with a secret key |
| `crypto.jwt_decode` | none | Decode a JWT header + payload; optionally verify an HS256/384/512 signature |
| `crypto.generate_token` | low | Cryptographically secure random token (hex, urlsafe, or base64) |
| `crypto.generate_password` | low | Secure random password with mixed character classes |
| `crypto.encode` | none | Encode UTF-8 text to base64, base64url, hex, or URL (percent) encoding |
| `crypto.decode` | none | Decode base64, base64url, hex, or URL text back to a UTF-8 string |

## Details

- **`crypto.hash`** — pass `text` (hashed as UTF-8) or `dataBase64` (raw bytes as base64).
  `algorithm` defaults to `sha256`. Returns `{ "algorithm", "hex", "bytes" }`.
- **`crypto.hmac`** — requires `text` and `key`. `algorithm` defaults to `sha256`.
- **`crypto.jwt_decode`** — splits the token, base64url-decodes (padding is added automatically)
  the header and payload, and returns them. If `secret` is provided and the algorithm is
  `HS256`/`HS384`/`HS512`, the signature is verified with a constant-time compare and `valid`
  is `true`/`false`. Asymmetric algorithms (`RS*`/`ES*`/`PS*`) are decoded but reported as
  `"valid": null` with an explanatory `note` — no asymmetric key libraries are available.
- **`crypto.generate_token`** — `length` is the number of random bytes of entropy (default 32);
  `format` is `hex`, `urlsafe`, or `base64`.
- **`crypto.generate_password`** — `length` defaults to 20 (minimum equals the number of character
  classes). Always includes at least one lowercase, uppercase, and digit; add `symbols: true`
  (the default) to also require a punctuation character.
- **`crypto.encode` / `crypto.decode`** — symmetric text transforms over base64, base64url, hex,
  and URL percent-encoding.

## Notes

- No authentication and no network access — `sandbox.network` is `false`.
- These are general-purpose utilities. Generated tokens and passwords use the OS CSPRNG via
  Python's `secrets` module; still store any secret you generate securely.
