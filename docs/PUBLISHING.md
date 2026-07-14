# Publishing Guide

How to build, validate, and publish the skills in this repo to the
[Sophon Marketplace](https://marketplace.sophon.buildersoft.io), under the **Buildersoft LLC**
publisher account. Artifacts are built locally and uploaded manually — there is no CI job that
publishes on merge.

## 1. Build artifacts

```bash
# Validate only (what CI runs) — no output written, exits non-zero on any violation
pwsh -File build/Build-MarketplacePackages.ps1 -ValidateOnly

# Build .sophon-skill zips into dist/
pwsh -File build/Build-MarketplacePackages.ps1
```

For each skill under `skills/`, the script validates `manifest.json` against the
[manifest contract](../CONTRIBUTING.md#manifest-contract) — collecting **all** errors per skill
rather than stopping at the first — and, for skills that validate clean, writes
`dist/<name>-<version>.sophon-skill`: a zip of the skill folder's **contents** (`manifest.json` at
the zip root, no wrapping folder), excluding `__pycache__/`, `dist/`, `.DS_Store`, `Thumbs.db`, and
`*.pyc`. The run exits `1` if any skill failed validation (packages that did validate are still
written). Each artifact's SHA256 is printed — use it to verify the upload against the registry's
recorded hash and the download endpoint's `X-Checksum-Sha256` header.

`dist/` is git-ignored — artifacts are build output, not checked in.

Options: `-Skills jira,confluence` (build only the named skills); `-OutputDir <path>` (write
artifacts elsewhere).

## 2. Get a publisher API key

Publishing uses an `smk_`-prefixed API key tied to the **Buildersoft LLC** account with a verified
email. Mint one **once** from an interactive JWT session (API keys can't mint other API keys):

```bash
ACCESS_TOKEN=$(curl -sS -X POST https://marketplace.sophon.buildersoft.io/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"you@buildersoft.io","password":"..."}' | jq -r .accessToken)

curl -sS -X POST https://marketplace.sophon.buildersoft.io/api/v1/me/api-keys \
  -H "Authorization: Bearer $ACCESS_TOKEN" -H 'Content-Type: application/json' \
  -d '{"name":"ci-publish-key"}'
```

The response's `key` (`smk_...`) is shown **exactly once** — save it as a secret. API keys are
publish-scoped only.

## 3. Publish

```bash
export SOPHON_MARKETPLACE_API_KEY='smk_...'
pwsh -File build/Publish-MarketplacePackages.ps1            # all of dist/
pwsh -File build/Publish-MarketplacePackages.ps1 -DryRun    # preview, no upload
pwsh -File build/Publish-MarketplacePackages.ps1 -Skills jira
```

The script POSTs each artifact to `<MarketplaceUrl>/api/v1/publish` as multipart field `package`
with the Bearer key. `-MarketplaceUrl` (or `$env:SOPHON_MARKETPLACE_URL`) overrides the target
(e.g. a local `http://localhost:5100`). Equivalent raw call:

```bash
curl -X POST https://marketplace.sophon.buildersoft.io/api/v1/publish \
  -H "Authorization: Bearer $SOPHON_MARKETPLACE_API_KEY" \
  -F "package=@dist/jira-1.0.0.sophon-skill;type=application/zip"
```

A successful publish returns `201 Created` with `{ name, version, status: "pendingReview", sha256 }`.

## 4. Review & versioning

- Every new version — including the first for a new name — starts in **`pendingReview`** and is
  invisible to browse/search/download until a super-admin approves it. Publishing a new, strictly
  greater version on an already-approved skill keeps the previous approved version live while the
  new one waits.
- **Versions must be strictly increasing SemVer.** Bump `manifest.version` before re-publishing any
  change. Re-uploading byte-identical content returns `409 duplicate-content`.
- There is no separate "edit metadata" endpoint — description, tags, category, etc. all come from
  whatever `manifest.json` you publish next.

## Common failures

| HTTP | Cause |
|------|-------|
| `413` | package exceeds 100 MB |
| `403` | you don't own an existing skill with this name |
| `409` | name used by a different package type; version not strictly greater than your highest; or identical content already published |
| `422` | zip-safety violation (zip-slip / bomb / entry-count) or manifest schema failure — the response lists every failing field |

Rate limit: 10 uploads/hour per publisher.
