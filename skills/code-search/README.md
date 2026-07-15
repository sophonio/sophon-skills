# Code Search

Search GitHub for source code, repositories, and commits through the GitHub search API. Uses only
the Python standard library (`urllib`) — no third-party dependencies.

## Tools

| Name | Risk | Description |
| --- | --- | --- |
| `code.search_code` | none | Search source code across repositories. **Requires a GitHub token.** Returns `[{repo, path, url}]`. |
| `code.search_repositories` | none | Search repositories by keyword and qualifiers, optionally sorted by `stars`, `forks`, or `updated`. Returns `[{fullName, description, stars, language, url}]`. |
| `code.search_commits` | none | Search commits by message and qualifiers. Returns `[{repo, sha, message, author, url}]`. |

GitHub search qualifiers (e.g. `language:python`, `repo:owner/name`, `stars:>1000`, `in:file`) can be
embedded directly in the `query`. Results are capped at 50 per call.

## Connection / Authentication

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `token` | secret | No | GitHub personal access token. Required for `code.search_code` and to reach private repos; also raises the search rate limit for all tools. Create one at https://github.com/settings/tokens |

Requests are sent to `api.github.com` with headers `Accept: application/vnd.github+json`,
`X-GitHub-Api-Version: 2022-11-28`, and a `User-Agent`. When a token is present it is sent as
`Authorization: Bearer <token>`. Repository and commit search work anonymously (subject to lower rate
limits); code search returns `{"error": "code search requires a GitHub token"}` when no token is set.

## Trademarks

GitHub is a trademark of GitHub, Inc. / Microsoft Corporation. This skill is an independent
integration and is not affiliated with or endorsed by GitHub.
