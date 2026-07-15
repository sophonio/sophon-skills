# Dependency Audit

Scan a project's dependency lockfile for known vulnerabilities using [OSV.dev](https://osv.dev),
Google's open-source vulnerability database. Paste the lockfile contents in and get back the packages
that have known advisories, with their OSV IDs.

Implemented over the Python standard library (`json`, `tomllib`, `re`, `urllib`) — no dependencies,
no API key, and it runs in the sandbox unchanged. The only network calls are to `api.osv.dev`.

## Supported lockfiles

| Filename | Ecosystem | Parser |
|----------|-----------|--------|
| `requirements.txt` | PyPI | pinned `name==version` lines (comments, `-e`, options, and URLs are skipped) |
| `package-lock.json` | npm | v2/v3 `packages` map or v1 `dependencies` tree |
| `Cargo.lock` | crates.io | `[[package]]` entries |
| `go.mod` | Go | `require` block and single-line `require` directives |

## Tools

| Tool | Risk | Description |
|------|------|-------------|
| `deps.audit` | low | Parse a lockfile and report every package that has a known vulnerability |
| `deps.query_package` | none | Look up vulnerabilities for a single `ecosystem` / `name` / `version` |

`deps.audit` takes `content` (the lockfile text) and `filename` (used to select the parser), with an
optional `ecosystem` override. It queries OSV in a single batch and returns:

```json
{
  "ecosystem": "PyPI",
  "scanned": 42,
  "vulnerable": 1,
  "packages": [
    { "name": "requests", "version": "2.19.0", "vulns": [{ "id": "GHSA-...", "modified": "..." }] }
  ],
  "truncated": false
}
```

At most 200 packages are queried per call; if the lockfile has more, `truncated` is `true` and a
`note` explains the cap.

## Notes

- The batch endpoint (`/v1/querybatch`) returns vulnerability IDs only. Use `deps.query_package` to
  get the human-readable `summary` and `aliases` (CVE numbers) for a specific package/version.
- Look up any returned ID at `https://osv.dev/vulnerability/<id>`.
- No authentication is required. OSV.dev is a free public service.

## Trademarks

OSV and OSV.dev are projects of Google LLC. This is an unofficial, independently built integration
and is not affiliated with or endorsed by Google.
