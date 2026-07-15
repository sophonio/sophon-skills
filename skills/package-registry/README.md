# Package Registry

Query package metadata from the public [npm](https://registry.npmjs.org) and
[PyPI](https://pypi.org) registries. Look up the latest version, description, license,
homepage, and deprecation/yanked status of a package, or list its published versions.

Keyless — no credentials or connection setup required. Uses only the Python standard
library (`urllib`) and talks to the registry JSON APIs directly.

## Tools

| Name | Risk | Description |
|------|------|-------------|
| `pkg.npm_info` | none | npm package metadata: latest version, description, license, homepage, deprecation, maintainer count. |
| `pkg.npm_versions` | none | List an npm package's versions (oldest→newest), returning the most recent N. |
| `pkg.pypi_info` | none | PyPI package metadata: latest version, summary, license, homepage, required Python, yanked status. |
| `pkg.pypi_versions` | none | List a PyPI package's released versions (with files), returning the most recent N. |

### Parameters

- `name` (required) — the package name. npm scoped names such as `@scope/pkg` are supported
  and URL-encoded automatically.
- `limit` (optional, `*_versions` only) — max recent versions to return (default 20, max 100).

A request for a package that does not exist returns `{"error": "package not found: <name>"}`.

## Connection / auth

None. Both registries are queried anonymously over HTTPS.

## Trademarks

npm is a trademark of npm, Inc. PyPI and the Python Package Index are trademarks of the
Python Software Foundation. This skill is an independent client of their public APIs and is
not affiliated with or endorsed by either.
