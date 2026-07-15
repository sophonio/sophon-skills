# Uptime Check

Endpoint availability checks with **no dependencies and no authentication**. It probes HTTP(S)
endpoints, raw TCP ports, and TLS certificates using only the Python standard library
(`urllib`, `socket`, `ssl`), so it runs unchanged in the sandbox with an empty `requirements` list.

All checks are failure-tolerant: connection refusals, timeouts, and handshake errors are returned
as structured JSON (`ok:false` / `open:false` with an `error` string) rather than raised.

## Tools

| Name | Risk | Description |
| --- | --- | --- |
| `uptime.http` | none | Perform an HTTP(S) GET/HEAD request, measure latency, follow redirects, and check the status code against 2xx (or an expected status). |
| `uptime.tcp` | none | Check whether a raw TCP port is open and accepting connections, measuring connect latency. |
| `uptime.tls_cert` | none | Inspect a host's TLS certificate: subject, issuer, validity window, and days until expiry. |

### `uptime.http`

Parameters: `url` (required), `method` (`GET`|`HEAD`, default `GET`), `timeoutSeconds` (default 10),
`expectStatus` (optional exact status code), `header` (optional object of request headers).

Returns `{ url, status, ok, latencyMs, finalUrl, error? }`. `ok` is true for a 2xx response, or an
exact match against `expectStatus` when provided.

### `uptime.tcp`

Parameters: `host` (required), `port` (required), `timeoutSeconds` (default 10).

Returns `{ host, port, open, latencyMs, error? }`.

### `uptime.tls_cert`

Parameters: `host` (required), `port` (default 443), `timeoutSeconds` (default 10).

Returns `{ host, port, subject, issuer, notBefore, notAfter, daysUntilExpiry, error? }`.
`daysUntilExpiry` is computed from the certificate's `notAfter` field.

## Authentication

None. This skill needs no connection card or credentials. It does require outbound network access
(`sandbox.network: true`) to reach the targets you ask it to check.
