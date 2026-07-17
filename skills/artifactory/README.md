# Artifactory Skill

JFrog Artifactory integration for Sophon — browse repositories, search artifacts (quick search or safely-constructed AQL), inspect storage info, checksums, and download stats, read and set item properties, list builds, and view storage usage. Authenticates with a static JFrog access token (Bearer) against `{baseUrl}/artifactory/api`.

## Tools

| Tool | Risk | Description |
|------|------|-------------|
| `artifactory.list_repositories` | None | List repositories, optionally filtered by type (local/remote/virtual/federated) |
| `artifactory.search_artifacts` | None | Search artifacts by name (quick search; local/remote repos only) or by structured AQL criteria (repo, path/name patterns, created date) |
| `artifactory.get_artifact_info` | None | Get size, checksums (sha256), timestamps, and optionally download stats for an artifact |
| `artifactory.get_item_properties` | None | Get the properties (key/value metadata) on a repository item |
| `artifactory.list_builds` | None | List all builds, or the numbers/dates of a specific build |
| `artifactory.get_storage_summary` | None | Per-repository storage usage (used space, item counts, package type) |
| `artifactory.set_item_properties` | Medium | Set properties on a repository item (Artifactory Pro, local repos only) |

## Setup

1. Note your JFrog Platform base URL, e.g. `https://mycompany.jfrog.io` (no trailing path — the skill appends `/artifactory/api` itself). Self-hosted instances work the same way.
2. Generate an access token. Any user can self-generate an **identity token** from their profile: click your avatar > **Access Tokens** (or **Edit Profile** > **Generate an Identity Token**). An identity token carries your own permissions, which is all the read tools need.
3. Scoped-token caveats:
   - `artifactory.get_storage_summary` calls `/api/storageinfo`, which requires an **admin token** or a scoped token granting **system:info** (storage read, `storage:r`). With a plain identity token of a non-admin user it returns a friendly "storage summary requires an admin or system:info-scoped token" error.
   - AQL search results are filtered by your read permissions; the skill always includes `repo`, `path`, and `name` in the AQL `.include()` clause, which is required for non-admin tokens to get results at all. AQL over the *builds* domain requires admin — this skill only queries the *items* domain.
   - `artifactory.set_item_properties` requires **Artifactory Pro** (or higher) and works on **local repositories only**. It applies properties to the given item only by default (`recursive=0`); pass `recursive: true` to deliberately stamp a folder's properties onto everything beneath it.
   - Quick search (`search_artifacts` with `name`) covers **local and remote** repositories only — virtual repositories are not searched; use AQL mode with `repo` instead.
4. In the Sophon Dashboard, go to **Settings > Connections**, click **Connect** on the Artifactory card, enter the base URL and access token, and test the connection (the test calls `/artifactory/api/repositories`).

## Usage Examples

**List repositories:**
> "List all local Artifactory repositories"

**Search artifacts:**
> "Search Artifactory for jars matching `guava*` in libs-release created after 2026-01-01"

**Inspect an artifact:**
> "Show me the sha256 and download count of org/acme/app/1.0/app-1.0.jar in libs-release"

**Builds:**
> "What builds does Artifactory know about, and when did my-app last build?"

**Tag an artifact:**
> "Set qa=passed on org/acme/app/1.0/app-1.0.jar in libs-release"

## Requirements

- JFrog Artifactory (cloud or self-hosted); an account able to self-generate an identity token
- Admin or `system:info`-scoped token for the storage summary tool
- Artifactory Pro (or higher) tier for `set_item_properties`, which also only works on local repositories

## Trademarks

JFrog and Artifactory are trademarks of JFrog Ltd. This skill is an independent integration developed by Buildersoft LLC and is not affiliated with, endorsed by, or sponsored by JFrog.

## License

MIT © 2026 Buildersoft LLC. See [LICENSE](LICENSE).
