# GitHub

Interact with GitHub from Sophon: triage and create issues, review and open pull requests, inspect
GitHub Actions workflow runs, and — via a raw API passthrough — reach anything else in the REST API.

Implemented with the GitHub REST API v3 over the Python standard library (no dependencies), so it
runs in the sandbox unchanged.

## Tools

| Tool | Risk | Description |
|------|------|-------------|
| `github.list_issues` | none | List issues in a repo (filter by state/labels) |
| `github.get_issue` | none | Get one issue or PR by number |
| `github.create_issue` | medium | Open a new issue |
| `github.comment` | medium | Comment on an issue or PR |
| `github.list_pull_requests` | none | List pull requests |
| `github.get_pull_request` | none | Get one PR with merge state and diff stats |
| `github.create_pull_request` | medium | Open a pull request |
| `github.merge_pull_request` | high | Merge a pull request (not easily reversible) |
| `github.list_workflow_runs` | none | List recent Actions runs |
| `github.get_workflow_run` | none | Get one run and its jobs' conclusions |
| `github.api` | high | Raw authenticated REST request (`gh api`-style escape hatch) |

Repositories are addressed as `owner/name` (e.g. `octocat/hello-world`).

## Connection

Connect the **GitHub** integration with:

- **Personal Access Token** — a [fine-grained or classic PAT](https://github.com/settings/tokens)
  with `repo` scope (add `workflow` to read Actions runs). Grant only the repositories and
  permissions you need.
- **API Base URL** *(optional)* — set only for GitHub Enterprise Server, e.g.
  `https://ghe.example.com/api/v3`. Defaults to `https://api.github.com`.

The token is stored in Sophon's credential vault and supplied to the skill at call time; it is never
written into the skill.

## Notes

- `github.list_issues` returns only true issues; pull requests are available via the pull-request
  tools (GitHub's issues API otherwise includes PRs).
- `github.api` and `github.merge_pull_request` can make irreversible changes — they are marked
  high-risk so Sophon can gate them behind approval.

## Trademarks

GitHub is a trademark of GitHub, Inc. / Microsoft. This is an unofficial, independently built
integration and is not affiliated with or endorsed by GitHub.
