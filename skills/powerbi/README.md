# Power BI Skill

Power BI integration for Sophon — browse workspaces, datasets, reports, and dashboards, run DAX queries, trigger dataset refreshes, and inspect refresh history through the Power BI REST API using a Microsoft Entra service principal.

## Tools

| Tool | Risk | Description |
|------|------|-------------|
| `powerbi.list_workspaces` | None | List workspaces the service principal can access |
| `powerbi.list_datasets` | None | List the datasets (semantic models) in a workspace |
| `powerbi.list_reports` | None | List the reports in a workspace |
| `powerbi.list_dashboards` | None | List dashboards in a workspace, or a dashboard's tiles |
| `powerbi.execute_dax` | Low | Run a single DAX query against a dataset |
| `powerbi.get_refresh_history` | None | Get a dataset's refresh history |
| `powerbi.refresh_dataset` | Medium | Trigger an asynchronous dataset refresh |

## Setup

1. In the [Microsoft Entra admin center](https://entra.microsoft.com), create an **app registration** (single tenant). Note the **Application (client) ID** and **Directory (tenant) ID**.
2. Under **Certificates & secrets**, create a **client secret** and copy its value.
3. **Do NOT add any API permissions** to the app registration. Microsoft's documentation warns that API permissions are unused for Power BI service principal access and adding them causes errors.
4. Have a **Fabric administrator** open the Fabric admin portal (**Tenant settings > Developer settings**) and enable **"Service principals can call Fabric public APIs"** for a security group that contains the app. For the DAX query tool, also enable the **"Dataset Execute Queries REST API"** tenant setting.
5. Add the service principal as a **Member** or **Admin** on each workspace you want it to access (**Workspace > Manage access**). Note: service principals cannot access **My Workspace**, and cannot query datasets that use **RLS** (row-level security) or **SSO**.
6. In Sophon, open **Settings > Connections**, click **Connect** on the Power BI card, and enter the **Directory (Tenant) ID**, **Application (Client) ID**, and **Client Secret**, then test the connection.

## Usage Examples

> "List my Power BI workspaces"

> "Show the datasets in the Finance workspace and whether they are refreshable"

> "Run a DAX query on the Sales dataset: EVALUATE TOPN(10, 'Orders')"

> "Refresh the Revenue dataset and then show me its refresh history"

> "What tiles are on the Executive Overview dashboard?"

## Requirements

- A Power BI (Fabric) tenant with a Microsoft Entra app registration (service principal) and client secret
- Tenant setting **"Service principals can call Fabric public APIs"** enabled by a Fabric admin (plus **"Dataset Execute Queries REST API"** for `powerbi.execute_dax`)
- The service principal added as Member/Admin on each target workspace (new workspace experience)
- Service principals cannot access My Workspace or RLS/SSO-enabled datasets
- On shared capacity, datasets are limited to 8 API/scheduled refreshes per day; Execute Queries is limited to one query per call and at most 100,000 rows / 15 MB per query result

## Trademarks

Power BI is a trademark of Microsoft Corporation. This project is not affiliated with or endorsed by Microsoft Corporation.

## License

MIT © 2026 Buildersoft LLC. See [LICENSE](LICENSE).
