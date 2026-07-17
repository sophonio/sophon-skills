# Bitbucket Skill

Bitbucket Cloud integration for Sophon — list repositories, review pull requests (details, approvals, diffs), read files, check Pipelines runs, and comment on pull requests in a workspace.

## Tools

| Tool | Risk | Description |
|------|------|-------------|
| `bitbucket.list_repos` | None | List repositories in the workspace, most recently updated first |
| `bitbucket.list_pull_requests` | None | List pull requests in a repository, optionally by state |
| `bitbucket.get_pull_request` | None | Get pull request details with reviewers and approval summary |
| `bitbucket.get_pr_diff` | None | Get the unified diff of a pull request (plain text, ~100 KB cap) |
| `bitbucket.get_file` | None | Read a file's raw contents at a branch, tag, or commit (~256 KB cap) |
| `bitbucket.list_pipeline_runs` | None | List Pipelines runs with state, result, and target branch |
| `bitbucket.add_pr_comment` | Low | Add a comment to a pull request |

## Setup

1. Go to https://id.atlassian.com/manage-profile/security/api-tokens (Atlassian account **Security** page) and click **Create API token with scopes**. Plain API tokens without scopes do not work for Bitbucket, and Bitbucket app passwords were retired on 2026-07-28.
2. Choose the **Bitbucket** app and select these scopes: `read:account`, `read:repository:bitbucket`, `read:pullrequest:bitbucket`, `write:pullrequest:bitbucket`, `read:pipeline:bitbucket`.
3. Pick an expiry (tokens always expire — maximum 1 year) and copy the token; it is shown only once.
4. Find your workspace ID: it is the slug in your repository URLs, `bitbucket.org/{workspace}/...`.
5. In Sophon, open **Settings > Connections**, click **Connect** on the Bitbucket card, and enter:
   - **Atlassian Account Email** — the email you sign in to Atlassian with (this is the Basic auth username, **not** your Bitbucket username)
   - **API Token** — the scoped token from step 3
   - **Workspace** — the workspace ID from step 4
6. Test the connection.

## Usage Examples

> "List my most recently updated Bitbucket repos"

> "Show open pull requests in the backend-api repo"

> "Who has approved PR 42 in backend-api? Show me the diff too"

> "Read bitbucket-pipelines.yml from the main branch of backend-api and tell me why the last pipeline run failed"

> "Leave a comment on PR 42 in backend-api saying the migration script needs a rollback step"

## Requirements

- A Bitbucket Cloud account (an Atlassian account with access to the target workspace)
- A scoped Atlassian API token with the Bitbucket scopes listed in Setup; token expiry is enforced by Atlassian (max 1 year), so the connection must be refreshed when the token expires
- Your account needs at least read access to the target repositories, and write access to pull requests to add comments
- `bitbucket.list_pipeline_runs` requires Bitbucket Pipelines to be enabled on the repository
- Bitbucket rate-limits API access (about 1000 requests/hour); 429 responses are surfaced with retry information

## Trademarks

Bitbucket is a trademark of Atlassian Pty Ltd. This project is not affiliated with or endorsed by Atlassian Pty Ltd.

## License

MIT © 2026 Buildersoft LLC. See [LICENSE](LICENSE).
