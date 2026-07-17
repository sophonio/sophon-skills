# Azure DevOps Skill

Azure DevOps integration for Sophon — query and manage work items, inspect builds and their failing jobs, list pull requests, and run pipelines against the Azure DevOps REST API v7.1.

## Tools

| Tool | Risk | Description |
|------|------|-------------|
| `devops.query_work_items` | None | Run a WIQL query and return matching work items |
| `devops.get_work_item` | None | Get a work item with relations and recent comments |
| `devops.create_work_item` | Medium | Create a work item (Bug, Task, User Story, ...) |
| `devops.update_work_item` | Medium | Update state, assignee, title, or arbitrary fields |
| `devops.list_builds` | None | List recent builds, filtered by status/result |
| `devops.get_build` | None | Get a build plus its failing jobs/stages and errors |
| `devops.list_pull_requests` | None | List pull requests in a repo or across a project |
| `devops.run_pipeline` | High | Queue a pipeline run (starts real CI/CD jobs) |

## Setup

1. Sign in to your Azure DevOps organization (e.g. `https://dev.azure.com/acme`).
2. Open **User settings** (top-right avatar) **> Personal access tokens > New Token**.
3. Set the token's **Organization** to your specific organization — the token must be **org-scoped**. Global ("All accessible organizations") PATs are being retired on 2026-12-01.
4. Under **Scopes**, select: **Work Items — Read & Write** (`vso.work_write`), **Build — Read & Execute** (`vso.build_execute`), and **Code — Read** (`vso.code`).
5. Create the token and copy it immediately (it is shown only once).
6. Admin caveats:
   - The **"Restrict personal access token creation"** organization policy is ON by default for new organizations — an organization admin may need to allow PAT creation (or add you to the allow-list) before you can create one.
   - PATs can become **inactive** if their owner does not sign in to Azure DevOps for an extended period. If calls start failing with 401, sign in to Azure DevOps and check/regenerate your PAT.
7. In Sophon, open **Settings > Connections**, click **Connect** on the Azure DevOps card, then:
   - **Organization URL**: your org URL, e.g. `https://dev.azure.com/acme` (on-premises Azure DevOps Server collection URLs also work, e.g. `https://tfs.example.com/DefaultCollection`).
   - **Personal Access Token**: the token you created above.
8. Test the connection.

## Usage Examples

> "Query Azure DevOps for all active bugs in the Contoso project assigned to me"

> "Show me work item 4321 with its latest comments"

> "Create a bug in Contoso titled 'Checkout page returns 500' assigned to jane@acme.com, tagged 'checkout; urgent'"

> "Why did the last build in Contoso fail? Show me the failing jobs"

> "Run pipeline 12 in Contoso on the release/2026-07 branch"

## Requirements

- An Azure DevOps organization (`dev.azure.com`) or an on-premises Azure DevOps Server collection reachable from the sandbox.
- An **org-scoped** Personal Access Token with **Work Items (Read & Write)**, **Build (Read & Execute)**, and **Code (Read)** scopes. Your organization's PAT-creation policy must allow you to create tokens (default-restricted for new orgs).
- Your account needs project-level permissions for the operations you use (e.g. queueing builds requires the Queue builds permission).
- Azure DevOps rate-limits usage (roughly 200 TSTUs per 5-minute sliding window per user); when throttled, the skill surfaces the `Retry-After` delay in the error message.

## Trademarks

Azure DevOps is a trademark of Microsoft Corporation. This project is not affiliated with or endorsed by Microsoft Corporation.

## License

MIT © 2026 Buildersoft LLC. See [LICENSE](LICENSE).
